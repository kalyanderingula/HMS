import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.inpatient_emergency_models import NursingRound, NursingMedicationLog
from app.models.pharmacy_models import Prescription, PrescriptionItem
from app.schemas.inpatient_emergency import (
    NursingRoundCreate, NursingRoundResponse,
    MARItemResponse, MedicationAdministrationCreate, MedicationAdministrationResponse
)

router = APIRouter(prefix="/nursing", tags=["Nursing Care & MAR"])

@router.post("/rounds", response_model=NursingRoundResponse, status_code=201)
async def record_nursing_round(
    req: NursingRoundCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    round_entry = NursingRound(
        patient_id=patient.patient_id,
        nurse_id=cu.user_id,
        round_time=datetime.utcnow(),
        round_notes=f"{req.round_notes} | Vitals: {req.vital_signs_summary or 'Stable'}"
    )
    db.add(round_entry)
    await db.commit()
    await db.refresh(round_entry)

    return NursingRoundResponse(
        round_id=round_entry.round_id,
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        nurse_name=cu.name or "Ward Nurse",
        round_time=round_entry.round_time,
        round_notes=round_entry.round_notes
    )

@router.get("/patients/{patient_id}/mar", response_model=List[MARItemResponse])
async def get_patient_mar(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    p_res = await db.execute(select(Prescription).where(Prescription.patient_id == patient_id))
    prescriptions = p_res.scalars().all()
    results = []
    for pr in prescriptions:
        items_res = await db.execute(select(PrescriptionItem).where(PrescriptionItem.prescription_id == pr.prescription_id))
        items = items_res.scalars().all()
        for it in items:
            results.append(MARItemResponse(
                prescription_item_id=it.prescription_item_id,
                medicine_name="Prescribed Medication",
                dosage=it.dosage or "Standard Dose",
                frequency=it.frequency or "Daily",
                route=it.route or "Oral",
                instructions=it.instructions
            ))
    return results

@router.post("/administer-medication", response_model=MedicationAdministrationResponse, status_code=201)
async def administer_medication(
    req: MedicationAdministrationCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    log_entry = NursingMedicationLog(
        patient_id=patient.patient_id,
        prescription_item_id=req.prescription_item_id,
        medicine_name=req.medicine_name,
        dosage_given=req.dosage_given,
        route=req.route,
        administered_by=cu.user_id,
        administered_at=datetime.utcnow(),
        administration_notes=req.notes
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    return MedicationAdministrationResponse(
        administration_id=log_entry.administration_log_id,
        patient_id=patient.patient_id,
        medicine_name=log_entry.medicine_name,
        dosage_given=log_entry.dosage_given,
        route=log_entry.route,
        administered_by_name=cu.name or "Staff Nurse",
        administered_at=log_entry.administered_at,
        notes=log_entry.administration_notes
    )
