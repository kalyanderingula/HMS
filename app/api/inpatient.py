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
from app.models.receptionist_models import Ward, Room, Bed, BedStatus, Admission
from app.schemas.inpatient_emergency import (
    BedStatusResponse, AdmissionCreate, AdmissionResponse,
    BedTransferRequest, DischargeRequest
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

@router.post("/discharges")
async def discharge_patient(
    req: DischargeRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["icu_staff", "doctor", "nurse", "admin", "super_admin"]))
):
    adm_res = await db.execute(select(Admission).where(Admission.admission_id == req.admission_id).with_for_update())
    admission = adm_res.scalars().first()
    if not admission: raise HTTPException(404, "Admission record not found")
    if admission.actual_discharge_date: raise HTTPException(409, "Admission already discharged")

    admission.actual_discharge_date = datetime.utcnow()
    admission.discharge_summary = req.discharge_summary
    admission.discharge_condition = req.discharge_disposition

    await db.commit()
    return {"message": "Patient discharged successfully", "discharge_disposition": req.discharge_disposition}


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
    return [dict(admission_id=a.admission_id, admission_number=a.admission_number,
                 patient_id=p.patient_id, patient_name=f"{p.first_name} {p.last_name or ''}", mrn=p.mrn,
                 bed_number=bed, admission_date=a.admission_date,
                 status="Discharged" if a.actual_discharge_date else "Admitted",
                 discharge_summary=a.discharge_summary) for a,p,bed in rows]
