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
    rows = await db.execute(text("""SELECT mar.mar_id, mar.patient_id, mar.prescription_item_id, mar.scheduled_time,
        mar.frequency_code, mar.scheduled_hour, mar.pre_admin_vitals_required, mar.vitals_recorded,
        CASE WHEN mar.administration_status='Due' AND mar.scheduled_time<CURRENT_TIMESTAMP-interval '1 hour' THEN 'Overdue' ELSE mar.administration_status END administration_status,
        d.generic_name medicine_name, pi.dosage, pi.frequency, pi.route, pi.instructions,
        EXISTS(SELECT 1 FROM electronic_medical_records.allergy_records a WHERE a.patient_id=mar.patient_id AND lower(a.allergen_name)=lower(d.generic_name)) allergy_warning,
        l.administered_at, l.administration_notes, l.exception_reason
        FROM nursing.medication_administration_records mar
        JOIN pharmacy.prescription_items pi USING(prescription_item_id)
        JOIN pharmacy.drugs d USING(drug_id)
        LEFT JOIN nursing.medication_administration_logs l USING(mar_id)
        WHERE mar.patient_id=:p ORDER BY mar.scheduled_time DESC"""), {"p": patient_id})
    await db.commit()
    return [dict(r) for r in rows.mappings()]


@router.post("/patients/{patient_id}/mar/schedule-doses")
async def schedule_patient_mar_doses(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    admitted = await db.scalar(text("SELECT 1 FROM admission.admissions WHERE patient_id=:p AND actual_discharge_date IS NULL"), {"p": patient_id})
    if not admitted:
        raise HTTPException(409, "MAR scheduling is available only for an active admission")

    # Fetch active prescription items
    items = await db.execute(text("""
        SELECT pi.prescription_item_id, pi.frequency, d.generic_name, d.drug_category
        FROM pharmacy.prescriptions pr
        JOIN pharmacy.prescription_items pi USING(prescription_id)
        JOIN pharmacy.drugs d USING(drug_id)
        WHERE pr.patient_id=:p AND COALESCE(pi.item_status, 'Pending') <> 'Cancelled'
    """), {"p": patient_id})
    raw_items = items.mappings().all()

    # Schedule mapping
    freq_map = {
        "OD": [("09:00", 9)],
        "BD": [("09:00", 9), ("21:00", 21)],
        "TID": [("08:00", 8), ("14:00", 14), ("20:00", 20)],
        "Q8H": [("06:00", 6), ("14:00", 14), ("22:00", 22)],
        "Q12H": [("08:00", 8), ("20:00", 20)],
        "PRN": [("PRN", datetime.utcnow().hour)]
    }

    created_count = 0
    today = datetime.utcnow().date()

    for item in raw_items:
        freq = (item["frequency"] or "PRN").strip().upper()
        slots = freq_map.get(freq, [("09:00", 9)])
        # High-risk drug check for pre-admin vitals
        gen_lower = (item["generic_name"] or "").lower()
        cat_lower = (item["drug_category"] or "").lower()
        is_high_risk = any(k in gen_lower or k in cat_lower for k in [
            "insulin", "atenolol", "amlodipine", "metoprolol", "lisinopril", "heparin", "warfarin", "morphine"
        ])

        for label, hour in slots:
            sched_time = datetime(today.year, today.month, today.day, hour, 0, 0)
            res = await db.execute(text("""
                INSERT INTO nursing.medication_administration_records
                (patient_id, prescription_item_id, scheduled_time, administration_status, frequency_code, scheduled_hour, pre_admin_vitals_required)
                VALUES (:p, :item, :time, 'Due', :freq, :hour, :vitals_req)
                ON CONFLICT (patient_id, prescription_item_id, scheduled_time) DO UPDATE
                SET frequency_code = EXCLUDED.frequency_code, pre_admin_vitals_required = EXCLUDED.pre_admin_vitals_required
            """), {
                "p": patient_id,
                "item": item["prescription_item_id"],
                "time": sched_time,
                "freq": freq,
                "hour": label,
                "vitals_req": is_high_risk
            })
            created_count += 1

    await db.commit()
    return {"message": f"Generated/updated {created_count} MAR scheduled dose slots for patient", "patient_id": patient_id}


@router.post("/administer-medication", response_model=MedicationAdministrationResponse, status_code=201)
async def administer_medication(
    req: MedicationAdministrationCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["icu_staff", "nurse", "doctor", "admin", "super_admin"]))
):
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    allowed = {"Administered", "Missed", "Refused", "Withheld", "Unavailable"}
    if req.administration_status not in allowed: raise HTTPException(422, "Invalid administration status")
    if req.administration_status != "Administered" and not (req.exception_reason or "").strip():
        raise HTTPException(422, "A reason is required for an unadministered dose")
    if not req.mar_id: raise HTTPException(422, "Select a scheduled MAR dose")

    mar = (await db.execute(text("SELECT * FROM nursing.medication_administration_records WHERE mar_id=:id FOR UPDATE"), {"id": req.mar_id})).mappings().first()
    if not mar or mar["patient_id"] != req.patient_id: raise HTTPException(422, "MAR dose does not belong to this patient")
    if mar["administration_status"] not in ("Due", "Overdue"): raise HTTPException(409, "This dose was already recorded")

    # High-Risk Pre-Administration Vitals Check
    if mar.get("pre_admin_vitals_required") and req.administration_status == "Administered":
        if not (req.notes and any(v in req.notes.lower() for v in ["bp", "pulse", "glucose", "vitals", "hr", "/"])):
            raise HTTPException(
                status_code=400,
                detail="Pre-administration vitals verification required for this high-risk medication before administering. Please log vitals (e.g. BP/Pulse/Sugar) in administration notes."
            )

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
        if drug: req.medicine_name = drug.generic_name

    log_entry = NursingMedicationLog(
        patient_id=patient.patient_id,
        prescription_item_id=req.prescription_item_id,
        mar_id=req.mar_id,
        medicine_name=req.medicine_name,
        dosage_given=req.dosage_given,
        route=req.route,
        administered_by=cu.user_id,
        administered_at=datetime.utcnow(),
        administration_notes=req.notes,
        administration_status=req.administration_status,
        exception_reason=req.exception_reason
    )
    db.add(log_entry)
    await db.execute(text("UPDATE nursing.medication_administration_records SET administration_status=:s, vitals_recorded=:v WHERE mar_id=:id"), {
        "s": req.administration_status,
        "v": req.notes if mar.get("pre_admin_vitals_required") else None,
        "id": req.mar_id
    })
    if req.administration_status != "Administered":
        await db.execute(text("INSERT INTO core.notifications(recipient_type,source_module,source_reference_id,subject,body,status) VALUES('Role','Nursing',:src,:subject,:body,'pending')"), {"src": req.mar_id, "subject": f"Medication dose {req.administration_status.lower()}", "body": req.exception_reason})
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
        notes=log_entry.administration_notes,
        administration_status=log_entry.administration_status,
        exception_reason=log_entry.exception_reason
    )


@router.get("/ward/handover")
async def get_nurse_shift_handover(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    # Total active admissions
    census = await db.scalar(text("SELECT count(*) FROM admission.admissions WHERE actual_discharge_date IS NULL"))
    
    # Overdue and due doses count
    overdue_count = await db.scalar(text("""
        SELECT count(*) FROM nursing.medication_administration_records mar
        JOIN admission.admissions a ON a.patient_id = mar.patient_id AND a.actual_discharge_date IS NULL
        WHERE mar.administration_status = 'Due' AND mar.scheduled_time < CURRENT_TIMESTAMP - interval '1 hour'
    """))
    due_count = await db.scalar(text("""
        SELECT count(*) FROM nursing.medication_administration_records mar
        JOIN admission.admissions a ON a.patient_id = mar.patient_id AND a.actual_discharge_date IS NULL
        WHERE mar.administration_status = 'Due'
    """))

    # Recent exceptions (withheld, missed, refused)
    exceptions = await db.execute(text("""
        SELECT l.administration_log_id, p.mrn, concat_ws(' ', p.first_name, p.last_name) patient_name,
               l.medicine_name, l.administration_status, l.exception_reason, l.administered_at
        FROM nursing.medication_administration_logs l
        JOIN patient.patients p USING(patient_id)
        WHERE l.administration_status <> 'Administered'
        ORDER BY l.administered_at DESC LIMIT 10
    """))

    return {
        "handover_timestamp": datetime.utcnow(),
        "ward_census": census or 0,
        "mar_metrics": {
            "due_doses": due_count or 0,
            "overdue_doses": overdue_count or 0
        },
        "recent_dose_exceptions": [dict(r) for r in exceptions.mappings()]
    }
