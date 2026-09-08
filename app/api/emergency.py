import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.inpatient_emergency_models import (
    EmergencyArrival, EmergencyTriageLevel, EmergencyTriageAssessment
)
from app.schemas.inpatient_emergency import (
    EmergencyArrivalCreate, EmergencyArrivalResponse,
    TriageAssessmentCreate, TriageAssessmentResponse
)

router = APIRouter(prefix="/emergency", tags=["Emergency & Trauma Care"])

async def ensure_emergency_masters(db: AsyncSession):
    esi_levels = [
        ("Level 1 - Resuscitation", 1, 0),
        ("Level 2 - Emergent", 2, 10),
        ("Level 3 - Urgent", 3, 30),
        ("Level 4 - Less Urgent", 4, 60),
        ("Level 5 - Non-urgent", 5, 120),
    ]
    for name, rank, resp in esi_levels:
        res = await db.execute(select(EmergencyTriageLevel).where(EmergencyTriageLevel.severity_rank == rank))
        if not res.scalars().first():
            db.add(EmergencyTriageLevel(level_name=name, severity_rank=rank, response_time_minutes=resp))
    await db.commit()

@router.post("/arrivals", response_model=EmergencyArrivalResponse, status_code=201)
async def register_emergency_arrival(
    req: EmergencyArrivalCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["receptionist", "nurse", "doctor", "admin", "super_admin"]))
):
    await ensure_emergency_masters(db)
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    arrival = EmergencyArrival(
        patient_id=patient.patient_id,
        arrival_mode=req.arrival_mode,
        arrival_time=datetime.utcnow(),
        brought_by=req.brought_by,
        arrival_condition=req.arrival_condition
    )
    db.add(arrival)
    await db.commit()
    await db.refresh(arrival)

    return EmergencyArrivalResponse(
        emergency_arrival_id=arrival.emergency_arrival_id,
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn,
        arrival_mode=arrival.arrival_mode,
        arrival_time=arrival.arrival_time,
        arrival_condition=arrival.arrival_condition
    )

@router.post("/triage", response_model=TriageAssessmentResponse, status_code=201)
async def perform_triage(
    req: TriageAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    await ensure_emergency_masters(db)
    arr_res = await db.execute(select(EmergencyArrival).where(EmergencyArrival.emergency_arrival_id == req.emergency_arrival_id))
    arrival = arr_res.scalars().first()
    if not arrival: raise HTTPException(404, "Emergency arrival record not found")

    p_res = await db.execute(select(Patient).where(Patient.patient_id == arrival.patient_id))
    patient = p_res.scalars().first()

    lvl_res = await db.execute(select(EmergencyTriageLevel).where(EmergencyTriageLevel.severity_rank == req.esi_level))
    level = lvl_res.scalars().first()
    if not level: raise HTTPException(400, "Invalid ESI triage level (Must be 1 to 5)")

    trauma_bay = req.trauma_bay_code or (f"Trauma Bay {req.esi_level}" if req.esi_level <= 2 else "ER Cubicle")

    triage = EmergencyTriageAssessment(
        emergency_arrival_id=arrival.emergency_arrival_id,
        triage_level_id=level.triage_level_id,
        chief_complaint=req.chief_complaint,
        vital_signs_summary=req.vital_signs_summary,
        trauma_bay_code=trauma_bay,
        assessed_by=cu.user_id,
        assessed_at=datetime.utcnow()
    )
    db.add(triage)
    await db.commit()
    await db.refresh(triage)

    return TriageAssessmentResponse(
        triage_id=triage.triage_id,
        emergency_arrival_id=arrival.emergency_arrival_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn,
        esi_level=level.severity_rank,
        triage_category=level.level_name,
        response_time_minutes=level.response_time_minutes,
        trauma_bay_code=triage.trauma_bay_code,
        assessed_at=triage.assessed_at
    )
