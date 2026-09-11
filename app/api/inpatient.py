import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.api.doctor import Doctor
from app.models.receptionist_models import Ward, Room, Bed, BedStatus, Admission, InpatientRound
from app.schemas.inpatient_emergency import (
    BedStatusResponse, AdmissionCreate, AdmissionResponse,
    BedTransferRequest, DischargeRequest, DischargeClearanceRequest,
    DischargeClearanceStatusResponse, InpatientRoundCreate, InpatientRoundResponse
)

router = APIRouter(prefix="/inpatient", tags=["Inpatient & Bed Management"])

@router.get("/beds", response_model=List[BedStatusResponse])
async def list_beds(
    ward_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    query = select(Bed)
    if ward_id:
        query = query.join(Room).where(Room.ward_id == ward_id)
    res = await db.execute(query.limit(100))
    beds = res.scalars().all()
    results = []
    for b in beds:
        r_res = await db.execute(select(Room).where(Room.room_id == b.room_id))
        room = r_res.scalars().first()
        ward_name = "General Ward"
        if room:
            w_res = await db.execute(select(Ward).where(Ward.ward_id == room.ward_id))
            ward = w_res.scalars().first()
            if ward: ward_name = ward.ward_name

        occupied = await db.scalar(select(Admission).where(Admission.bed_id == b.bed_id, Admission.actual_discharge_date.is_(None)))
        master = await db.get(BedStatus, b.bed_status_id) if b.bed_status_id else None
        bed_status = "Occupied" if occupied else (master.status_name if master else "Available")
        if status_filter and status_filter.lower() != bed_status.lower():
            continue
        results.append(BedStatusResponse(
            bed_id=b.bed_id, bed_number=b.bed_number, ward_name=ward_name,
            room_number=room.room_number if room else "Room", bed_type=b.bed_type or "Standard",
            status=bed_status
        ))
    return results

@router.post("/admissions", response_model=AdmissionResponse, status_code=201)
async def admit_patient(
    req: AdmissionCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["receptionist", "doctor", "nurse", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id).with_for_update())
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    if await db.scalar(select(Admission).where(Admission.patient_id == req.patient_id, Admission.actual_discharge_date.is_(None))):
        raise HTTPException(409, "Patient already has an active admission")
    b_res = await db.execute(select(Bed).where(Bed.bed_id == req.bed_id).with_for_update())
    bed = b_res.scalars().first()
    if not bed: raise HTTPException(404, "Bed not found")
    await ensure_bed_available(db, bed)

    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id))
    doctor = d_res.scalars().first()
    if not doctor: raise HTTPException(404, "Doctor not found")
    doc_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Attending Doctor"

    room_res = await db.execute(select(Room).where(Room.room_id == bed.room_id))
    room = room_res.scalars().first()
    ward_name = "Inpatient Ward"
    if room:
        w_res = await db.execute(select(Ward).where(Ward.ward_id == room.ward_id))
        ward = w_res.scalars().first()
        if ward: ward_name = ward.ward_name

    adm_num = f"ADM-{datetime.utcnow().year}-{str(uuid.uuid4())[:6].upper()}"
    admission = Admission(
        admission_number=adm_num,
        patient_id=patient.patient_id,
        bed_id=bed.bed_id,
        admitting_doctor_id=req.doctor_id,
        room_id=bed.room_id,
        ward_id=room.ward_id if room else None,
        admission_date=datetime.utcnow(),
        notes=f"Admission type: {req.admission_type}",
        admission_reason=req.admission_reason
    )
    db.add(admission)

    await db.commit()
    await db.refresh(admission)

    return AdmissionResponse(
        admission_id=admission.admission_id, admission_number=admission.admission_number,
        patient_id=patient.patient_id, patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn, doctor_name=doc_name, ward_name=ward_name,
        room_number=room.room_number if room else "Room", bed_number=bed.bed_number,
        admission_date=admission.admission_date, status="Admitted"
    )

@router.post("/transfers")
async def transfer_bed(
    req: BedTransferRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["icu_staff", "nurse", "doctor", "admin", "super_admin"]))
):
    adm_res = await db.execute(select(Admission).where(Admission.admission_id == req.admission_id).with_for_update())
    admission = adm_res.scalars().first()
    if not admission: raise HTTPException(404, "Admission record not found")
    if admission.actual_discharge_date: raise HTTPException(409, "Admission already discharged")

    new_bed_res = await db.execute(select(Bed).where(Bed.bed_id == req.new_bed_id).with_for_update())
    new_bed = new_bed_res.scalars().first()
    if not new_bed: raise HTTPException(404, "Target bed not found")
    await ensure_bed_available(db, new_bed)

    # Assign new bed
    admission.bed_id = new_bed.bed_id
    room = await db.get(Room, new_bed.room_id)
    admission.room_id = new_bed.room_id
    admission.ward_id = room.ward_id
    admission.notes = (admission.notes or "") + f"\nTransfer: {req.transfer_reason}"

    await db.commit()
    return {"message": "Patient transferred successfully", "new_bed_number": new_bed.bed_number}

@router.get("/admissions/{admission_id}/clearance", response_model=DischargeClearanceStatusResponse)
async def get_discharge_clearance(
    admission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "pharmacist", "accountant", "admin", "super_admin"]))
):
    admission = await db.get(Admission, admission_id)
    if not admission:
        raise HTTPException(404, "Admission record not found")
    all_cleared = bool(
        admission.discharge_summary_signed and
        admission.pharmacy_cleared and
        admission.nursing_cleared and
        admission.billing_cleared
    )
    return DischargeClearanceStatusResponse(
        admission_id=admission.admission_id,
        discharge_summary_signed=bool(admission.discharge_summary_signed),
        pharmacy_cleared=bool(admission.pharmacy_cleared),
        nursing_cleared=bool(admission.nursing_cleared),
        billing_cleared=bool(admission.billing_cleared),
        all_cleared=all_cleared,
        clearance_notes=admission.clearance_notes
    )


@router.post("/admissions/{admission_id}/clearance", response_model=DischargeClearanceStatusResponse)
async def update_discharge_clearance(
    admission_id: uuid.UUID,
    req: DischargeClearanceRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    adm_res = await db.execute(select(Admission).where(Admission.admission_id == admission_id).with_for_update())
    admission = adm_res.scalars().first()
    if not admission:
        raise HTTPException(404, "Admission record not found")
    if admission.actual_discharge_date:
        raise HTTPException(409, "Admission has already been discharged")

    c_type = req.clearance_type.lower()
    user_roles = set(cu.roles)
    is_admin = bool({"admin", "super_admin"}.intersection(user_roles))

    if c_type == "doctor":
        if not (is_admin or "doctor" in user_roles):
            raise HTTPException(403, "Only a doctor or admin can sign the clinical discharge summary")
        if not req.doctor_discharge_summary or len(req.doctor_discharge_summary.strip()) < 5:
            raise HTTPException(422, "Doctor clinical discharge summary is required (min 5 characters)")
        admission.discharge_summary_signed = True
        admission.discharge_summary = req.doctor_discharge_summary
        if req.discharge_disposition:
            admission.discharge_condition = req.discharge_disposition
    elif c_type == "pharmacy":
        if not (is_admin or "pharmacist" in user_roles):
            raise HTTPException(403, "Only a pharmacist or admin can issue pharmacy clearance")
        admission.pharmacy_cleared = True
    elif c_type == "nursing":
        if not (is_admin or "nurse" in user_roles):
            raise HTTPException(403, "Only a nurse or admin can issue nursing discharge clearance")
        admission.nursing_cleared = True
    elif c_type == "billing":
        if not (is_admin or "accountant" in user_roles):
            raise HTTPException(403, "Only an accountant or admin can issue billing discharge clearance")
        admission.billing_cleared = True
    else:
        raise HTTPException(422, f"Invalid clearance type: '{req.clearance_type}'. Must be doctor, pharmacy, nursing, or billing.")

    if req.notes:
        existing_notes = admission.clearance_notes or ""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        admission.clearance_notes = f"{existing_notes}\n[{timestamp} - {c_type.upper()}] {req.notes}".strip()

    await db.commit()
    await db.refresh(admission)

    all_cleared = bool(
        admission.discharge_summary_signed and
        admission.pharmacy_cleared and
        admission.nursing_cleared and
        admission.billing_cleared
    )
    return DischargeClearanceStatusResponse(
        admission_id=admission.admission_id,
        discharge_summary_signed=bool(admission.discharge_summary_signed),
        pharmacy_cleared=bool(admission.pharmacy_cleared),
        nursing_cleared=bool(admission.nursing_cleared),
        billing_cleared=bool(admission.billing_cleared),
        all_cleared=all_cleared,
        clearance_notes=admission.clearance_notes
    )


@router.post("/discharges")
async def discharge_patient(
    req: DischargeRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["icu_staff", "doctor", "nurse", "admin", "super_admin"]))
):
    adm_res = await db.execute(select(Admission).where(Admission.admission_id == req.admission_id).with_for_update())
    admission = adm_res.scalars().first()
    if not admission:
        raise HTTPException(404, "Admission record not found")
    if admission.actual_discharge_date:
        raise HTTPException(409, "Admission already discharged")

    # Multi-Department Clearance Gate Check
    missing = []
    if not admission.discharge_summary_signed:
        missing.append("Doctor Clinical Summary")
    if not admission.pharmacy_cleared:
        missing.append("Pharmacy Reconciliation")
    if not admission.nursing_cleared:
        missing.append("Nursing Discharge Assessment")
    if not admission.billing_cleared:
        missing.append("Billing & Ledger Settlement")

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Discharge rejected by Multi-Department Gate. Missing clearance from: {', '.join(missing)}"
        )

    admission.actual_discharge_date = datetime.utcnow()
    if req.discharge_summary:
        admission.discharge_summary = req.discharge_summary
    if req.discharge_disposition:
        admission.discharge_condition = req.discharge_disposition
    admission.discharged_by = cu.user_id

    # If bed was occupied, clear status
    if admission.bed_id:
        bed = await db.get(Bed, admission.bed_id)
        if bed:
            # Bed remains in room, no active admission will link to it
            pass

    await db.commit()
    return {
        "message": "Patient discharged successfully following all 4 departmental clearances",
        "discharge_disposition": admission.discharge_condition or req.discharge_disposition,
        "discharged_at": admission.actual_discharge_date
    }


@router.get("/admissions/{admission_id}/discharge-summary")
async def get_discharge_summary_slip(
    admission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "receptionist", "admin", "super_admin"]))
):
    admission = await db.get(Admission, admission_id)
    if not admission:
        raise HTTPException(404, "Admission record not found")
    patient = await db.get(Patient, admission.patient_id)
    doctor = await db.get(Doctor, admission.admitting_doctor_id) if admission.admitting_doctor_id else None

    rounds_res = await db.execute(
        select(InpatientRound).where(InpatientRound.admission_id == admission_id).order_by(InpatientRound.round_datetime.desc()).limit(1)
    )
    latest_round = rounds_res.scalars().first()

    return {
        "admission_number": admission.admission_number,
        "patient": {
            "name": f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Unknown",
            "mrn": patient.mrn if patient else None,
            "dob": str(patient.date_of_birth) if patient and patient.date_of_birth else None,
            "gender": patient.gender if patient else None
        },
        "admitting_doctor": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Attending Physician",
        "admission_date": admission.admission_date,
        "discharge_date": admission.actual_discharge_date,
        "status": "Discharged" if admission.actual_discharge_date else "Admitted",
        "clinical_discharge_summary": admission.discharge_summary or "Discharge summary pending",
        "discharge_condition": admission.discharge_condition or "Stable",
        "clearances": {
            "doctor_signed": bool(admission.discharge_summary_signed),
            "pharmacy_cleared": bool(admission.pharmacy_cleared),
            "nursing_cleared": bool(admission.nursing_cleared),
            "billing_cleared": bool(admission.billing_cleared)
        },
        "latest_vitals": {
            "temperature": float(latest_round.temperature) if latest_round and latest_round.temperature else None,
            "bp": f"{latest_round.systolic_bp}/{latest_round.diastolic_bp}" if latest_round and latest_round.systolic_bp else None,
            "heart_rate": latest_round.heart_rate if latest_round else None,
            "respiratory_rate": latest_round.respiratory_rate if latest_round else None,
            "oxygen_saturation": float(latest_round.oxygen_saturation) if latest_round and latest_round.oxygen_saturation else None
        } if latest_round else None,
        "notes": admission.clearance_notes
    }


# Inpatient Clinical Rounds
@router.post("/admissions/{admission_id}/rounds", response_model=InpatientRoundResponse, status_code=201)
async def create_inpatient_round(
    admission_id: uuid.UUID,
    req: InpatientRoundCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "nurse", "admin", "super_admin"]))
):
    admission = await db.get(Admission, admission_id)
    if not admission:
        raise HTTPException(404, "Admission record not found")
    if admission.actual_discharge_date:
        raise HTTPException(409, "Cannot record rounds for a discharged admission")

    doctor_id = None
    if "doctor" in cu.roles:
        # Link doctor if doctor role
        d_res = await db.execute(select(Doctor.doctor_id).where(Doctor.doctor_id == cu.user_id))
        doctor_id = d_res.scalars().first()

    round_record = InpatientRound(
        admission_id=admission_id,
        round_datetime=datetime.utcnow(),
        doctor_id=doctor_id,
        nurse_id=cu.user_id if "nurse" in cu.roles else None,
        chief_complaint_today=req.chief_complaint_today,
        clinical_progress_notes=req.clinical_progress_notes,
        temperature=req.temperature,
        systolic_bp=req.systolic_bp,
        diastolic_bp=req.diastolic_bp,
        heart_rate=req.heart_rate,
        respiratory_rate=req.respiratory_rate,
        oxygen_saturation=req.oxygen_saturation
    )
    db.add(round_record)
    await db.commit()
    await db.refresh(round_record)

    return InpatientRoundResponse(
        round_id=round_record.round_id,
        admission_id=round_record.admission_id,
        round_datetime=round_record.round_datetime,
        doctor_id=round_record.doctor_id,
        nurse_id=round_record.nurse_id,
        chief_complaint_today=round_record.chief_complaint_today,
        clinical_progress_notes=round_record.clinical_progress_notes,
        temperature=float(round_record.temperature) if round_record.temperature is not None else None,
        systolic_bp=round_record.systolic_bp,
        diastolic_bp=round_record.diastolic_bp,
        heart_rate=round_record.heart_rate,
        respiratory_rate=round_record.respiratory_rate,
        oxygen_saturation=float(round_record.oxygen_saturation) if round_record.oxygen_saturation is not None else None
    )


@router.get("/admissions/{admission_id}/rounds", response_model=List[InpatientRoundResponse])
async def list_inpatient_rounds(
    admission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    admission = await db.get(Admission, admission_id)
    if not admission:
        raise HTTPException(404, "Admission record not found")

    res = await db.execute(
        select(InpatientRound).where(InpatientRound.admission_id == admission_id).order_by(InpatientRound.round_datetime.desc())
    )
    rounds = res.scalars().all()
    return [
        InpatientRoundResponse(
            round_id=r.round_id,
            admission_id=r.admission_id,
            round_datetime=r.round_datetime,
            doctor_id=r.doctor_id,
            nurse_id=r.nurse_id,
            chief_complaint_today=r.chief_complaint_today,
            clinical_progress_notes=r.clinical_progress_notes,
            temperature=float(r.temperature) if r.temperature is not None else None,
            systolic_bp=r.systolic_bp,
            diastolic_bp=r.diastolic_bp,
            heart_rate=r.heart_rate,
            respiratory_rate=r.respiratory_rate,
            oxygen_saturation=float(r.oxygen_saturation) if r.oxygen_saturation is not None else None
        )
        for r in rounds
    ]


async def ensure_bed_available(db, bed):
    occupied = await db.scalar(select(Admission).where(Admission.bed_id == bed.bed_id, Admission.actual_discharge_date.is_(None)))
    master = await db.get(BedStatus, bed.bed_status_id) if bed.bed_status_id else None
    if occupied or (master and master.status_name.lower() != "available"):
        raise HTTPException(409, "Bed is not available")


@router.get("/admissions")
async def list_admissions(active_only: bool = True, db: AsyncSession = Depends(get_db),
                          cu: CurrentUser = Depends(require_roles(["icu_staff", "nurse", "doctor", "receptionist", "admin"]))):
    query = select(Admission, Patient, Bed.bed_number).join(Patient).outerjoin(Bed)
    if active_only:
        query = query.where(Admission.actual_discharge_date.is_(None))
    rows = (await db.execute(query.order_by(Admission.admission_date.desc()).limit(200))).all()
    return [dict(
        admission_id=a.admission_id,
        admission_number=a.admission_number,
        patient_id=p.patient_id,
        patient_name=f"{p.first_name} {p.last_name or ''}".strip(),
        mrn=p.mrn,
        bed_number=bed,
        admission_date=a.admission_date,
        status="Discharged" if a.actual_discharge_date else "Admitted",
        discharge_summary=a.discharge_summary,
        discharge_summary_signed=bool(a.discharge_summary_signed),
        pharmacy_cleared=bool(a.pharmacy_cleared),
        nursing_cleared=bool(a.nursing_cleared),
        billing_cleared=bool(a.billing_cleared),
        all_cleared=bool(a.discharge_summary_signed and a.pharmacy_cleared and a.nursing_cleared and a.billing_cleared)
    ) for a, p, bed in rows]
