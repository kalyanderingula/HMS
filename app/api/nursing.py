import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.inpatient_emergency_models import NursingRound, NursingMedicationLog
from app.models.pharmacy_models import Prescription, PrescriptionItem, Drug
from app.schemas.inpatient_emergency import (
    NursingRoundCreate, NursingRoundResponse,
    MARItemResponse, MedicationAdministrationCreate, MedicationAdministrationResponse
)

router = APIRouter(prefix="/nursing", tags=["Nursing Care & MAR"])

@router.post("/rounds", response_model=NursingRoundResponse, status_code=201)
async def record_nursing_round(
    req: NursingRoundCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["icu_staff", "nurse", "doctor", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    round_entry = NursingRound(
        patient_id=patient.patient_id,
        nurse_id=cu.user_id,
        round_time=datetime.utcnow(),
        round_notes=f"{req.round_notes} | Vitals: {req.vital_signs_summary or 'Not recorded'}"
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

@router.get("/patients/{patient_id}/mar")
async def get_patient_mar(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["icu_staff", "nurse", "doctor", "admin"]))
):
    admitted=await db.scalar(text("SELECT 1 FROM admission.admissions WHERE patient_id=:p AND actual_discharge_date IS NULL"),{"p":patient_id})
    if not admitted: raise HTTPException(409,"MAR is available only for an active admission")
    await db.execute(text("""INSERT INTO nursing.medication_administration_records(patient_id,prescription_item_id,scheduled_time,administration_status)
        SELECT pr.patient_id,pi.prescription_item_id,date_trunc('hour',CURRENT_TIMESTAMP),'Due'
        FROM pharmacy.prescriptions pr JOIN pharmacy.prescription_items pi USING(prescription_id)
        WHERE pr.patient_id=:p AND COALESCE(pi.item_status,'Pending')<>'Cancelled'
        ON CONFLICT(patient_id,prescription_item_id,scheduled_time) DO NOTHING"""),{"p":patient_id})
    rows=await db.execute(text("""SELECT mar.mar_id,mar.patient_id,mar.prescription_item_id,mar.scheduled_time,
        CASE WHEN mar.administration_status='Due' AND mar.scheduled_time<CURRENT_TIMESTAMP-interval '1 hour' THEN 'Overdue' ELSE mar.administration_status END administration_status,
        d.generic_name medicine_name,pi.dosage,pi.frequency,pi.route,pi.instructions,
        EXISTS(SELECT 1 FROM electronic_medical_records.allergy_records a WHERE a.patient_id=mar.patient_id AND lower(a.allergen_name)=lower(d.generic_name)) allergy_warning,
        l.administered_at,l.administration_notes,l.exception_reason
        FROM nursing.medication_administration_records mar JOIN pharmacy.prescription_items pi USING(prescription_item_id)
        JOIN pharmacy.drugs d USING(drug_id) LEFT JOIN nursing.medication_administration_logs l USING(mar_id)
        WHERE mar.patient_id=:p ORDER BY mar.scheduled_time DESC"""),{"p":patient_id})
    await db.commit();return [dict(r) for r in rows.mappings()]

@router.post("/administer-medication", response_model=MedicationAdministrationResponse, status_code=201)
async def administer_medication(
    req: MedicationAdministrationCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["icu_staff", "nurse", "doctor", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    allowed={"Administered","Missed","Refused","Withheld","Unavailable"}
    if req.administration_status not in allowed: raise HTTPException(422,"Invalid administration status")
    if req.administration_status!="Administered" and not (req.exception_reason or "").strip():
        raise HTTPException(422,"A reason is required for an unadministered dose")
    if not req.mar_id: raise HTTPException(422,"Select a scheduled MAR dose")
    mar=(await db.execute(text("SELECT * FROM nursing.medication_administration_records WHERE mar_id=:id FOR UPDATE"),{"id":req.mar_id})).mappings().first()
    if not mar or mar["patient_id"]!=req.patient_id: raise HTTPException(422,"MAR dose does not belong to this patient")
    if mar["administration_status"] not in ("Due","Overdue"): raise HTTPException(409,"This dose was already recorded")

    if req.prescription_item_id:
        item = await db.get(PrescriptionItem, req.prescription_item_id)
        prescription = await db.get(Prescription, item.prescription_id) if item else None
        if not prescription or prescription.patient_id != req.patient_id:
            raise HTTPException(422, "Prescription does not belong to this patient")
        drug = await db.get(Drug, item.drug_id)
        if req.administration_status == "Administered" and drug and await db.scalar(text("""SELECT 1 FROM electronic_medical_records.allergy_records
            WHERE patient_id=:patient AND lower(allergen_name)=lower(:drug) LIMIT 1"""),
            {"patient": req.patient_id, "drug": drug.generic_name}):
            raise HTTPException(409, f"Allergy alert: {drug.generic_name} cannot be administered")
        if drug: req.medicine_name=drug.generic_name
    log_entry = NursingMedicationLog(
        patient_id=patient.patient_id,
        prescription_item_id=req.prescription_item_id,
        mar_id=req.mar_id,
        medicine_name=req.medicine_name,
        dosage_given=req.dosage_given,
        route=req.route,
        administered_by=cu.user_id,
        administered_at=datetime.utcnow(),
        administration_notes=req.notes, administration_status=req.administration_status,
        exception_reason=req.exception_reason
    )
    db.add(log_entry)
    await db.execute(text("UPDATE nursing.medication_administration_records SET administration_status=:s WHERE mar_id=:id"),{"s":req.administration_status,"id":req.mar_id})
    if req.administration_status!="Administered":
        await db.execute(text("INSERT INTO core.notifications(recipient_type,source_module,source_reference_id,subject,body,status) VALUES('Role','Nursing',:src,:subject,:body,'pending')"),{"src":req.mar_id,"subject":f"Medication dose {req.administration_status.lower()}","body":req.exception_reason})
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
        notes=log_entry.administration_notes, administration_status=log_entry.administration_status,
        exception_reason=log_entry.exception_reason
    )
