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
from app.models.receptionist_models import Ward, Room, Bed, Admission
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
    if status_filter:
        query = query.where(Bed.status == status_filter)
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

        results.append(BedStatusResponse(
            bed_id=b.bed_id, bed_number=b.bed_number, ward_name=ward_name,
            room_number=room.room_number if room else "Room", bed_type=b.bed_type or "Standard",
            status=b.status or "Available"
        ))
    return results

@router.post("/admissions", response_model=AdmissionResponse, status_code=201)
async def admit_patient(
    req: AdmissionCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["receptionist", "doctor", "nurse", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    b_res = await db.execute(select(Bed).where(Bed.bed_id == req.bed_id))
    bed = b_res.scalars().first()
    if not bed: raise HTTPException(404, "Bed not found")
    if bed.status == "Occupied": raise HTTPException(400, "Bed is already occupied")

    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id))
    doctor = d_res.scalars().first()
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
        doctor_id=req.doctor_id,
        admission_date=datetime.utcnow(),
        status="admitted",
        reason=req.admission_reason
    )
    db.add(admission)
    bed.status = "Occupied"

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
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    adm_res = await db.execute(select(Admission).where(Admission.admission_id == req.admission_id))
    admission = adm_res.scalars().first()
    if not admission: raise HTTPException(404, "Admission record not found")

    new_bed_res = await db.execute(select(Bed).where(Bed.bed_id == req.new_bed_id))
    new_bed = new_bed_res.scalars().first()
    if not new_bed: raise HTTPException(404, "Target bed not found")
    if new_bed.status == "Occupied": raise HTTPException(400, "Target bed is already occupied")

    # Release old bed
    old_bed_res = await db.execute(select(Bed).where(Bed.bed_id == admission.bed_id))
    old_bed = old_bed_res.scalars().first()
    if old_bed: old_bed.status = "Available"

    # Assign new bed
    admission.bed_id = new_bed.bed_id
    new_bed.status = "Occupied"

    await db.commit()
    return {"message": "Patient transferred successfully", "new_bed_number": new_bed.bed_number}

@router.post("/discharges")
async def discharge_patient(
    req: DischargeRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "nurse", "admin", "super_admin"]))
):
    adm_res = await db.execute(select(Admission).where(Admission.admission_id == req.admission_id))
    admission = adm_res.scalars().first()
    if not admission: raise HTTPException(404, "Admission record not found")

    admission.status = "discharged"
    admission.discharge_date = datetime.utcnow()

    # Free up bed
    bed_res = await db.execute(select(Bed).where(Bed.bed_id == admission.bed_id))
    bed = bed_res.scalars().first()
    if bed: bed.status = "Available"

    await db.commit()
    return {"message": "Patient discharged successfully", "discharge_disposition": req.discharge_disposition}
