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
from app.models.inpatient_emergency_models import SurgeryRequest, SurgerySchedule
from app.schemas.inpatient_emergency import (
    SurgeryRequestCreate, SurgeryScheduleCreate, SurgeryScheduleResponse, SurgeryCompleteRequest
)

router = APIRouter(prefix="/surgery", tags=["Surgery & Operation Theatre (OT)"])

@router.post("/requests", status_code=201)
async def create_surgery_request(
    req: SurgeryRequestCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    sr = SurgeryRequest(
        patient_id=patient.patient_id,
        requested_by=cu.user_id,
        procedure_name=req.procedure_name,
        procedure_code=req.procedure_code,
        request_priority=req.urgency,
        request_reason=req.clinical_indication,
        request_status="Requested"
    )
    db.add(sr)
    await db.commit()
    await db.refresh(sr)

    return {"message": "Surgery request submitted", "surgery_request_id": str(sr.surgery_request_id), "status": "Requested"}

@router.post("/schedule", response_model=SurgeryScheduleResponse, status_code=201)
async def schedule_surgery(
    req: SurgeryScheduleCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "nurse", "admin", "super_admin"]))
):
    sr_res = await db.execute(select(SurgeryRequest).where(SurgeryRequest.surgery_request_id == req.surgery_request_id))
    sr = sr_res.scalars().first()
    if not sr: raise HTTPException(404, "Surgery request not found")

    p_res = await db.execute(select(Patient).where(Patient.patient_id == sr.patient_id))
    patient = p_res.scalars().first()

    doc_res = await db.execute(select(Doctor).where(Doctor.doctor_id == req.primary_surgeon_id))
    doc = doc_res.scalars().first()
    doc_name = f"Dr. {doc.first_name} {doc.last_name}" if doc else "Lead Surgeon"

    sched = SurgerySchedule(
        surgery_request_id=sr.surgery_request_id,
        ot_room_number=req.ot_room_number,
        primary_surgeon_id=req.primary_surgeon_id,
        anesthesiologist_name=req.anesthesiologist_name,
        scheduled_start=req.scheduled_start,
        scheduled_end=req.scheduled_end,
        schedule_status="Scheduled"
    )
    db.add(sched)
    sr.request_status = "Scheduled"

    await db.commit()
    await db.refresh(sched)

    return SurgeryScheduleResponse(
        surgery_schedule_id=sched.surgery_schedule_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        procedure_name=sr.procedure_name,
        ot_room_number=sched.ot_room_number,
        scheduled_start=sched.scheduled_start,
        scheduled_end=sched.scheduled_end,
        primary_surgeon_name=doc_name,
        schedule_status=sched.schedule_status
    )

@router.post("/cases/{schedule_id}/complete")
async def complete_surgery(
    schedule_id: uuid.UUID,
    req: SurgeryCompleteRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"]))
):
    sc_res = await db.execute(select(SurgerySchedule).where(SurgerySchedule.surgery_schedule_id == schedule_id))
    sched = sc_res.scalars().first()
    if not sched: raise HTTPException(404, "Surgery schedule not found")

    sched.schedule_status = "Completed"
    sched.surgical_findings = req.surgical_findings
    sched.outcome = req.outcome

    sr_res = await db.execute(select(SurgeryRequest).where(SurgeryRequest.surgery_request_id == sched.surgery_request_id))
    sr = sr_res.scalars().first()
    if sr: sr.request_status = "Completed"

    await db.commit()
    return {"message": "Surgical case successfully documented and completed", "outcome": req.outcome}
