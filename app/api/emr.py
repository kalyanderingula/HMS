import uuid, json
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, text

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.api.doctor import Doctor
from app.models.patient import Patient, Gender, BloodGroup
from app.models.emr_models import (
    EncounterType, DiagnosisType, SeverityLevel, PatientEncounter,
    ClinicalNote, VitalSign, Diagnosis, MedicationRecord, AllergyRecord, Referral
)
from app.models.receptionist_models import Appointment, AppointmentStatus, AppointmentType, QueueServicePoint, QueueToken
from app.models.pharmacy_models import Drug, DrugInteraction, Prescription, PrescriptionItem, PrescriptionStatus
from app.schemas.emr import (
    StartEncounterRequest, EncounterResponse, EncounterClinicalRecord,
    VitalSignsRequest, VitalSignsResponse,
    SOAPNoteRequest, SOAPNoteResponse,
    DiagnosisRequest, DiagnosisResponse,
    PrescriptionResponse, BulkPrescriptionRequest,
    AllergyRequest, AllergyResponse,
    ReferralRequest, ReferralResponse,
    PatientEMRSummaryResponse, CompleteEncounterRequest,
)

router = APIRouter(prefix="/emr", tags=["EMR - Clinical Encounters"])

async def ensure_emr_masters(db):
    for t in ["OPD","IPD","Emergency","Teleconsultation"]:
        r = await db.execute(select(EncounterType).where(EncounterType.type_name == t))
        if not r.scalars().first():
            db.add(EncounterType(type_name=t))
    for dt in ["Primary","Secondary","Differential"]:
        r = await db.execute(select(DiagnosisType).where(DiagnosisType.diagnosis_type_name == dt))
        if not r.scalars().first():
            db.add(DiagnosisType(diagnosis_type_name=dt))
    for rank, sev in enumerate(["Mild","Moderate","Severe","Critical","Life-threatening"],1):
        r = await db.execute(select(SeverityLevel).where(SeverityLevel.severity_name == sev))
        if not r.scalars().first():
            db.add(SeverityLevel(severity_name=sev, severity_rank=rank))
    await db.commit()

async def get_p(pid, db):
    r = await db.execute(select(Patient).where(Patient.patient_id == pid))
    p = r.scalars().first()
    if not p: raise HTTPException(404, "Patient not found")
    return p

async def get_enc(eid, db):
    r = await db.execute(select(PatientEncounter).where(PatientEncounter.encounter_id == eid))
    e = r.scalars().first()
    if not e: raise HTTPException(404, "Encounter not found")
    return e

def ensure_open(enc):
    if enc.encounter_status != "In Progress":
        raise HTTPException(409, f"Encounter is {enc.encounter_status.lower()} and cannot be modified")


def medication_response(m):
    return PrescriptionResponse(
        medication_record_id=m.medication_record_id, encounter_id=m.encounter_id,
        patient_id=m.patient_id, doctor_id=m.doctor_id, medicine_name=m.medicine_name,
        drug_id=m.drug_id, quantity_prescribed=float(m.quantity_prescribed) if m.quantity_prescribed else None,
        medication_status=m.medication_status or "Draft", dosage=m.dosage,
        frequency=m.frequency, route=m.route, duration=m.duration,
        instructions=m.instructions, created_at=m.created_at,
    )


async def validate_medication_safety(db, patient_id, drug_ids):
    """Reject duplicate, known-allergen, and configured interaction risks."""
    if len(drug_ids) != len(set(drug_ids)):
        raise HTTPException(409, "The same drug cannot be prescribed twice in one request")
    drugs = (await db.execute(select(Drug).where(Drug.drug_id.in_(drug_ids)))).scalars().all()
    if len(drugs) != len(drug_ids):
        raise HTTPException(404, "One or more selected drugs do not exist")
    names = {d.drug_id: d.generic_name for d in drugs}
    allergies = (await db.execute(select(AllergyRecord).where(
        AllergyRecord.patient_id == patient_id,
        func.lower(AllergyRecord.allergy_type).in_(["drug", "medication"]),
    ))).scalars().all()
    for allergy in allergies:
        allergen = (allergy.allergen_name or "").strip().lower()
        for drug in drugs:
            candidates = [drug.generic_name, drug.scientific_name]
            if allergen and any(allergen in (name or "").lower() or (name or "").lower() in allergen for name in candidates):
                raise HTTPException(409, f"Allergy alert: patient is allergic to {allergy.allergen_name}")
    existing = (await db.execute(select(MedicationRecord.drug_id).where(
        MedicationRecord.patient_id == patient_id, MedicationRecord.ended_at.is_(None),
        MedicationRecord.drug_id.is_not(None),
    ))).scalars().all()
    all_ids = set(drug_ids) | set(existing)
    interactions = (await db.execute(select(DrugInteraction).where(
        DrugInteraction.drug_id.in_(all_ids), DrugInteraction.interacting_drug_id.in_(all_ids)
    ))).scalars().all()
    for interaction in interactions:
        if interaction.drug_id in drug_ids or interaction.interacting_drug_id in drug_ids:
            left = names.get(interaction.drug_id) or await db.scalar(select(Drug.generic_name).where(Drug.drug_id == interaction.drug_id))
            right = names.get(interaction.interacting_drug_id) or await db.scalar(select(Drug.generic_name).where(Drug.drug_id == interaction.interacting_drug_id))
            raise HTTPException(409, f"Drug interaction ({interaction.interaction_severity or 'unspecified'}): {left} + {right}. {interaction.interaction_description or ''}".strip())

async def enforce_doctor_scope(cu, db, doctor_id=None, patient_id=None):
    if any(role in cu.roles for role in ("admin", "super_admin", "receptionist", "nurse")):
        return
    if "doctor" not in cu.roles:
        raise HTTPException(403, "Clinical access is restricted")
    doctor_query = select(Doctor).where(Doctor.employee_id == cu.employee_id) if cu.employee_id else select(Doctor).where(Doctor.doctor_code == cu.username)
    doctor = (await db.execute(doctor_query)).scalars().first()
    if not doctor:
        raise HTTPException(403, "No doctor profile is linked to this login")
    if doctor_id and doctor.doctor_id != doctor_id:
        raise HTTPException(403, "This record is assigned to another doctor")
    if patient_id and not doctor_id:
        assigned = (await db.execute(select(PatientEncounter.encounter_id).where(
            PatientEncounter.patient_id == patient_id,
            PatientEncounter.doctor_id == doctor.doctor_id,
        ).limit(1))).first()
        queued = (await db.execute(select(Appointment.appointment_id).where(
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == doctor.doctor_id,
        ).limit(1))).first()
        if not assigned and not queued:
            raise HTTPException(403, "This patient is not assigned to you")

async def get_sev_id(name, db):
    r = await db.execute(select(SeverityLevel).where(SeverityLevel.severity_name == name))
    sv = r.scalars().first()
    return sv.severity_level_id if sv else None

def bp_status(s, d):
    if not s or not d: return None
    if s < 90 or d < 60: return "LOW - Hypotension"
    if s < 120 and d < 80: return "Normal"
    if s < 130: return "Elevated"
    if s < 140: return "Stage 1 Hypertension"
    return "Stage 2 Hypertension (HIGH)"

def bmi_status(bmi):
    if not bmi: return None
    if bmi < 18.5: return "Underweight"
    if bmi < 25: return "Normal Weight"
    if bmi < 30: return "Overweight"
    return "Obese"

def spo2_status(spo2):
    if not spo2: return None
    if spo2 >= 95: return "Normal"
    if spo2 >= 90: return "Low - Monitor closely"
    return "Critical - Oxygen therapy needed"

async def enc_resp(enc, db):
    p = await get_p(enc.patient_id, db)
    rd = await db.execute(select(Doctor).where(Doctor.doctor_id == enc.doctor_id))
    d = rd.scalars().first()
    ret = await db.execute(select(EncounterType).where(EncounterType.encounter_type_id == enc.encounter_type_id))
    et = ret.scalars().first()
    return EncounterResponse(
        encounter_id=enc.encounter_id, encounter_number=enc.encounter_number,
        patient_id=enc.patient_id, patient_name=f"{p.first_name} {p.last_name}", mrn=p.mrn,
        doctor_id=enc.doctor_id, doctor_name=f"Dr. {d.first_name} {d.last_name}" if d else "Unknown",
        encounter_type=et.type_name if et else "OPD", chief_complaint=enc.chief_complaint or "",
        encounter_status=enc.encounter_status, encounter_date=enc.encounter_date, created_at=enc.created_at,
    )

@router.post("/encounters", response_model=EncounterResponse, status_code=201)
async def start_encounter(req: StartEncounterRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","receptionist","admin","super_admin"]))):
    await ensure_emr_masters(db)
    await get_p(req.patient_id, db)
    doctor = (await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id))).scalars().first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    await enforce_doctor_scope(cu, db, doctor_id=req.doctor_id)
    if req.appointment_id:
        appointment = (await db.execute(select(Appointment).where(Appointment.appointment_id == req.appointment_id))).scalars().first()
        if not appointment:
            raise HTTPException(404, "Appointment not found")
        if appointment.patient_id != req.patient_id or appointment.doctor_id != req.doctor_id:
            raise HTTPException(409, "Appointment does not belong to the selected patient and doctor")
        existing = (await db.execute(select(PatientEncounter).where(
            PatientEncounter.appointment_id == req.appointment_id,
            PatientEncounter.encounter_status == "In Progress",
        ).order_by(desc(PatientEncounter.created_at)))).scalars().first()
        if existing:
            return await enc_resp(existing, db)
    ret = await db.execute(select(EncounterType).where(EncounterType.type_name == req.encounter_type))
    et = ret.scalars().first()
    enc = PatientEncounter(
        encounter_number=f"ENC-{datetime.utcnow().year}-{uuid.uuid4().hex[:12].upper()}",
        patient_id=req.patient_id, doctor_id=req.doctor_id,
        appointment_id=req.appointment_id, department_id=req.department_id,
        encounter_type_id=et.encounter_type_id if et else None,
        encounter_date=datetime.utcnow(), chief_complaint=req.chief_complaint,
        encounter_status="In Progress", created_by=cu.user_id,
    )
    db.add(enc)
    await db.commit()
    await db.refresh(enc)
    return await enc_resp(enc, db)

@router.get("/encounters/{encounter_id}", response_model=EncounterClinicalRecord)
async def get_encounter(encounter_id: uuid.UUID, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    enc = await get_enc(encounter_id, db)
    await enforce_doctor_scope(cu, db, doctor_id=enc.doctor_id)
    vital_rows = (await db.execute(select(VitalSign).where(VitalSign.encounter_id == encounter_id).order_by(desc(VitalSign.recorded_at)))).scalars().all()
    vitals = [vital_response(v) for v in vital_rows]
    note_rows = (await db.execute(select(ClinicalNote).where(ClinicalNote.encounter_id == encounter_id).order_by(desc(ClinicalNote.created_at)))).scalars().all()
    notes = []
    for n in note_rows:
        try: parsed = json.loads(n.note_text)
        except (TypeError, json.JSONDecodeError): parsed = {"Subjective": n.note_text, "Objective": "", "Assessment": "", "Plan": ""}
        notes.append(SOAPNoteResponse(note_id=n.note_id, encounter_id=n.encounter_id, doctor_id=n.doctor_id, note_type=n.note_type, subjective=parsed.get("Subjective", parsed.get("clinical_notes", "")), objective=parsed.get("Objective", ""), assessment=parsed.get("Assessment", ""), plan=parsed.get("Plan", ""), is_confidential=n.is_confidential, created_at=n.created_at))
    diagnoses = await get_diagnoses(encounter_id, db, cu)
    prescriptions = await get_prescriptions(encounter_id, db, cu)
    return EncounterClinicalRecord(encounter=await enc_resp(enc, db), vitals=vitals, soap_notes=notes, diagnoses=diagnoses, prescriptions=prescriptions)

@router.get("/patients/{patient_id}/encounters", response_model=List[EncounterResponse])
async def list_encounters(patient_id: uuid.UUID, limit: int = 10, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = await db.execute(select(PatientEncounter).where(PatientEncounter.patient_id == patient_id).order_by(desc(PatientEncounter.encounter_date)).limit(limit))
    return [await enc_resp(e, db) for e in r.scalars().all()]

@router.post("/encounters/{encounter_id}/vitals", response_model=VitalSignsResponse, status_code=201)
async def record_vitals(encounter_id: uuid.UUID, req: VitalSignsRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","nurse","admin","super_admin"]))):
    enc = await get_enc(encounter_id, db)
    await enforce_doctor_scope(cu, db, doctor_id=enc.doctor_id)
    ensure_open(enc)
    bmi = None
    if req.height_cm and req.weight_kg:
        bmi = round(float(req.weight_kg) / ((float(req.height_cm)/100)**2), 2)
    v = VitalSign(encounter_id=encounter_id, patient_id=enc.patient_id, temperature=req.temperature,
        systolic_bp=req.systolic_bp, diastolic_bp=req.diastolic_bp, heart_rate=req.heart_rate,
        respiratory_rate=req.respiratory_rate, oxygen_saturation=req.oxygen_saturation,
        height_cm=req.height_cm, weight_kg=req.weight_kg, bmi=bmi,
        pain_score=req.pain_score, recorded_by=cu.user_id)
    db.add(v); await db.commit(); await db.refresh(v)
    return vital_response(v)

def vital_response(v):
    return VitalSignsResponse(
        vital_sign_id=v.vital_sign_id, encounter_id=v.encounter_id, patient_id=v.patient_id,
        temperature=float(v.temperature) if v.temperature else None,
        systolic_bp=v.systolic_bp, diastolic_bp=v.diastolic_bp, heart_rate=v.heart_rate,
        respiratory_rate=v.respiratory_rate,
        oxygen_saturation=float(v.oxygen_saturation) if v.oxygen_saturation else None,
        height_cm=float(v.height_cm) if v.height_cm else None,
        weight_kg=float(v.weight_kg) if v.weight_kg else None,
        bmi=float(v.bmi) if v.bmi else None, pain_score=v.pain_score,
        bp_status=bp_status(v.systolic_bp, v.diastolic_bp),
        bmi_status=bmi_status(float(v.bmi) if v.bmi else None),
        spo2_status=spo2_status(float(v.oxygen_saturation) if v.oxygen_saturation else None),
        recorded_at=v.recorded_at)

@router.get("/encounters/{encounter_id}/vitals", response_model=List[VitalSignsResponse])
async def get_vitals(encounter_id: uuid.UUID, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = await db.execute(select(VitalSign).where(VitalSign.encounter_id == encounter_id).order_by(desc(VitalSign.recorded_at)))
    result = []
    for v in r.scalars().all():
        result.append(VitalSignsResponse(
            vital_sign_id=v.vital_sign_id, encounter_id=v.encounter_id, patient_id=v.patient_id,
            temperature=float(v.temperature) if v.temperature else None,
            systolic_bp=v.systolic_bp, diastolic_bp=v.diastolic_bp, heart_rate=v.heart_rate,
            respiratory_rate=v.respiratory_rate,
            oxygen_saturation=float(v.oxygen_saturation) if v.oxygen_saturation else None,
            height_cm=float(v.height_cm) if v.height_cm else None,
            weight_kg=float(v.weight_kg) if v.weight_kg else None,
            bmi=float(v.bmi) if v.bmi else None, pain_score=v.pain_score,
            bp_status=bp_status(v.systolic_bp, v.diastolic_bp),
            bmi_status=bmi_status(float(v.bmi) if v.bmi else None),
            spo2_status=spo2_status(float(v.oxygen_saturation) if v.oxygen_saturation else None),
            recorded_at=v.recorded_at))
    return result

@router.post("/encounters/{encounter_id}/soap-notes", response_model=SOAPNoteResponse, status_code=201)
async def add_soap(encounter_id: uuid.UUID, req: SOAPNoteRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","admin","super_admin"]))):
    enc = await get_enc(encounter_id, db)
    await enforce_doctor_scope(cu, db, doctor_id=enc.doctor_id)
    ensure_open(enc)
    soap = json.dumps({"Subjective":req.subjective,"Objective":req.objective,"Assessment":req.assessment,"Plan":req.plan}, indent=2)
    n = ClinicalNote(encounter_id=encounter_id, doctor_id=enc.doctor_id, note_type="SOAP", note_text=soap, is_confidential=req.is_confidential)
    db.add(n); await db.commit(); await db.refresh(n)
    return SOAPNoteResponse(note_id=n.note_id, encounter_id=n.encounter_id, doctor_id=n.doctor_id, note_type=n.note_type, subjective=req.subjective, objective=req.objective, assessment=req.assessment, plan=req.plan, is_confidential=n.is_confidential, created_at=n.created_at)

@router.get("/encounters/{encounter_id}/soap-notes", response_model=List[SOAPNoteResponse])
async def get_soap(encounter_id: uuid.UUID, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = await db.execute(select(ClinicalNote).where(ClinicalNote.encounter_id == encounter_id).order_by(desc(ClinicalNote.created_at)))
    result = []
    for n in r.scalars().all():
        try: parsed = json.loads(n.note_text)
        except: parsed = {"Subjective":n.note_text,"Objective":"","Assessment":"","Plan":""}
        result.append(SOAPNoteResponse(note_id=n.note_id, encounter_id=n.encounter_id, doctor_id=n.doctor_id, note_type=n.note_type, subjective=parsed.get("Subjective",""), objective=parsed.get("Objective",""), assessment=parsed.get("Assessment",""), plan=parsed.get("Plan",""), is_confidential=n.is_confidential, created_at=n.created_at))
    return result

@router.post("/encounters/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=201)
async def add_diagnosis(encounter_id: uuid.UUID, req: DiagnosisRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","admin","super_admin"]))):
    enc = await get_enc(encounter_id, db)
    await enforce_doctor_scope(cu, db, doctor_id=enc.doctor_id)
    ensure_open(enc)
    await ensure_emr_masters(db)
    rdt = await db.execute(select(DiagnosisType).where(DiagnosisType.diagnosis_type_name == req.diagnosis_type))
    dt = rdt.scalars().first()
    sev_id = await get_sev_id(req.severity, db)
    diag = Diagnosis(encounter_id=encounter_id, patient_id=enc.patient_id, doctor_id=enc.doctor_id,
        diagnosis_type_id=dt.diagnosis_type_id if dt else None, severity_level_id=sev_id,
        diagnosis_code=req.diagnosis_code, diagnosis_name=req.diagnosis_name, diagnosis_description=req.diagnosis_description)
    db.add(diag); await db.commit(); await db.refresh(diag)
    return DiagnosisResponse(diagnosis_id=diag.diagnosis_id, encounter_id=diag.encounter_id, patient_id=diag.patient_id, doctor_id=diag.doctor_id, diagnosis_code=diag.diagnosis_code, diagnosis_name=diag.diagnosis_name, diagnosis_description=diag.diagnosis_description, diagnosis_type=req.diagnosis_type, severity=req.severity, diagnosed_at=diag.diagnosed_at)

@router.get("/encounters/{encounter_id}/diagnoses", response_model=List[DiagnosisResponse])
async def get_diagnoses(encounter_id: uuid.UUID, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = await db.execute(select(Diagnosis).where(Diagnosis.encounter_id == encounter_id))
    result = []
    for d in r.scalars().all():
        rdt = await db.execute(select(DiagnosisType).where(DiagnosisType.diagnosis_type_id == d.diagnosis_type_id))
        dt = rdt.scalars().first()
        rsv = await db.execute(select(SeverityLevel).where(SeverityLevel.severity_level_id == d.severity_level_id))
        sv = rsv.scalars().first()
        result.append(DiagnosisResponse(diagnosis_id=d.diagnosis_id, encounter_id=d.encounter_id, patient_id=d.patient_id, doctor_id=d.doctor_id, diagnosis_code=d.diagnosis_code, diagnosis_name=d.diagnosis_name, diagnosis_description=d.diagnosis_description, diagnosis_type=dt.diagnosis_type_name if dt else "Primary", severity=sv.severity_name if sv else "Moderate", diagnosed_at=d.diagnosed_at))
    return result

@router.post("/encounters/{encounter_id}/prescriptions", response_model=List[PrescriptionResponse], status_code=201)
async def add_prescriptions(encounter_id: uuid.UUID, req: BulkPrescriptionRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","admin","super_admin"]))):
    enc = await get_enc(encounter_id, db)
    await enforce_doctor_scope(cu, db, doctor_id=enc.doctor_id)
    ensure_open(enc)
    await validate_medication_safety(db, enc.patient_id, [med.drug_id for med in req.medications])
    already_added = set((await db.execute(select(MedicationRecord.drug_id).where(
        MedicationRecord.encounter_id == encounter_id,
        MedicationRecord.ended_at.is_(None),
    ))).scalars().all())
    duplicates = already_added.intersection(med.drug_id for med in req.medications)
    if duplicates:
        raise HTTPException(409, "A selected drug is already present in this encounter")
    saved = []
    for med in req.medications:
        drug = await db.get(Drug, med.drug_id)
        m = MedicationRecord(encounter_id=encounter_id, patient_id=enc.patient_id, doctor_id=enc.doctor_id,
            drug_id=drug.drug_id, medicine_name=drug.generic_name,
            quantity_prescribed=med.quantity_prescribed, medication_status="Draft",
            dosage=med.dosage, frequency=med.frequency, route=med.route,
            duration=med.duration, instructions=med.instructions)
        db.add(m); await db.flush(); saved.append(m)
    await db.commit()
    return [medication_response(m) for m in saved]

@router.get("/encounters/{encounter_id}/prescriptions", response_model=List[PrescriptionResponse])
async def get_prescriptions(encounter_id: uuid.UUID, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = await db.execute(select(MedicationRecord).where(MedicationRecord.encounter_id == encounter_id))
    return [medication_response(m) for m in r.scalars().all()]

@router.post("/patients/{patient_id}/allergies", response_model=AllergyResponse, status_code=201)
async def add_allergy(patient_id: uuid.UUID, req: AllergyRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","nurse","admin","super_admin"]))):
    await enforce_doctor_scope(cu, db, patient_id=patient_id)
    await get_p(patient_id, db)
    await ensure_emr_masters(db)
    sev_id = await get_sev_id(req.severity, db)
    a = AllergyRecord(patient_id=patient_id, allergen_name=req.allergen_name, allergy_type=req.allergy_type, reaction_description=req.reaction_description, severity_level_id=sev_id)
    db.add(a); await db.commit(); await db.refresh(a)
    return AllergyResponse(allergy_record_id=a.allergy_record_id, patient_id=a.patient_id, allergen_name=a.allergen_name, allergy_type=a.allergy_type, reaction_description=a.reaction_description, severity=req.severity, created_at=a.created_at)

@router.get("/patients/{patient_id}/allergies", response_model=List[AllergyResponse])
async def get_allergies(patient_id: uuid.UUID, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    r = await db.execute(select(AllergyRecord).where(AllergyRecord.patient_id == patient_id))
    result = []
    for a in r.scalars().all():
        rsv = await db.execute(select(SeverityLevel).where(SeverityLevel.severity_level_id == a.severity_level_id))
        sv = rsv.scalars().first()
        result.append(AllergyResponse(allergy_record_id=a.allergy_record_id, patient_id=a.patient_id, allergen_name=a.allergen_name, allergy_type=a.allergy_type, reaction_description=a.reaction_description or "", severity=sv.severity_name if sv else "Moderate", created_at=a.created_at))
    return result

@router.post("/encounters/{encounter_id}/referrals", response_model=ReferralResponse, status_code=201)
async def add_referral(encounter_id: uuid.UUID, req: ReferralRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","admin","super_admin"]))):
    enc = await get_enc(encounter_id, db)
    await enforce_doctor_scope(cu, db, doctor_id=enc.doctor_id)
    ensure_open(enc)
    ref = Referral(encounter_id=encounter_id, referring_doctor_id=enc.doctor_id, referred_doctor_id=req.referred_doctor_id, referred_department_id=req.referred_department_id, referral_reason=req.referral_reason, referral_status="Pending")
    db.add(ref)
    if req.referred_doctor_id:
        receiving_doctor = (await db.execute(select(Doctor).where(Doctor.doctor_id == req.referred_doctor_id))).scalars().first()
        if not receiving_doctor:
            raise HTTPException(404, "Receiving doctor not found")
        if receiving_doctor.doctor_id == enc.doctor_id:
            raise HTTPException(409, "A referral must be sent to a different doctor")
        checked_in = (await db.execute(select(AppointmentStatus).where(AppointmentStatus.status_name == "Checked-In"))).scalars().first()
        referral_type = (await db.execute(select(AppointmentType).where(AppointmentType.type_name == "Follow-Up"))).scalars().first()
        service_point = (await db.execute(select(QueueServicePoint).where(QueueServicePoint.is_active.is_(True)).limit(1))).scalars().first()
        if not checked_in:
            checked_in = AppointmentStatus(status_name="Checked-In", description="Patient waiting for consultation")
            db.add(checked_in)
        if not referral_type:
            referral_type = AppointmentType(type_name="Follow-Up", description="Doctor referral")
            db.add(referral_type)
        if not service_point:
            service_point = QueueServicePoint(point_name="OPD Central Reception", location="Ground Floor", is_active=True)
            db.add(service_point)
        await db.flush()
        now = datetime.utcnow()
        appointment = Appointment(
            appointment_number=f"REF-{now:%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            patient_id=enc.patient_id, doctor_id=receiving_doctor.doctor_id,
            department_id=req.referred_department_id or receiving_doctor.department_id,
            appointment_type_id=referral_type.appointment_type_id,
            appointment_status_id=checked_in.appointment_status_id,
            appointment_date=now.date(), start_time=now.time(),
            end_time=(now + timedelta(minutes=15)).time(),
            chief_complaint=req.referral_reason, notes=f"Referred from encounter {enc.encounter_number}",
            booking_source="Doctor Referral", booked_by=cu.user_id, checked_in_at=now,
        )
        db.add(appointment)
        await db.flush()
        db.add(QueueToken(
            service_point_id=service_point.service_point_id,
            token_number=f"R-{uuid.uuid4().hex[:5].upper()}", patient_id=enc.patient_id,
            appointment_id=appointment.appointment_id, token_type="referral", priority=1,
            status="waiting", issued_at=now,
        ))
    await db.commit(); await db.refresh(ref)
    return ReferralResponse(referral_id=ref.referral_id, encounter_id=ref.encounter_id, referring_doctor_id=ref.referring_doctor_id, referred_department_id=ref.referred_department_id, referred_doctor_id=ref.referred_doctor_id, referral_reason=ref.referral_reason, referral_status=ref.referral_status, referred_at=ref.referred_at)

@router.get("/patients/{patient_id}/summary", response_model=PatientEMRSummaryResponse)
async def patient_summary(patient_id: uuid.UUID, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    await enforce_doctor_scope(cu, db, patient_id=patient_id)
    p = await get_p(patient_id, db)
    rg = await db.execute(select(Gender).where(Gender.gender_id == p.gender_id))
    g = rg.scalars().first()
    rbg = await db.execute(select(BloodGroup).where(BloodGroup.blood_group_id == p.blood_group_id))
    bg = rbg.scalars().first()
    # Allergies
    ra = await db.execute(select(AllergyRecord).where(AllergyRecord.patient_id == patient_id))
    allergies = []
    for a in ra.scalars().all():
        rsv = await db.execute(select(SeverityLevel).where(SeverityLevel.severity_level_id == a.severity_level_id))
        sv = rsv.scalars().first()
        allergies.append(AllergyResponse(allergy_record_id=a.allergy_record_id, patient_id=a.patient_id, allergen_name=a.allergen_name, allergy_type=a.allergy_type, reaction_description=a.reaction_description or "", severity=sv.severity_name if sv else "Moderate", created_at=a.created_at))
    # Latest vitals
    rv = await db.execute(select(VitalSign).where(VitalSign.patient_id == patient_id).order_by(desc(VitalSign.recorded_at)).limit(50))
    vital_rows = rv.scalars().all()
    vraw = vital_rows[0] if vital_rows else None
    latest_vitals = None
    if vraw:
        latest_vitals = VitalSignsResponse(vital_sign_id=vraw.vital_sign_id, encounter_id=vraw.encounter_id, patient_id=vraw.patient_id, temperature=float(vraw.temperature) if vraw.temperature else None, systolic_bp=vraw.systolic_bp, diastolic_bp=vraw.diastolic_bp, heart_rate=vraw.heart_rate, respiratory_rate=vraw.respiratory_rate, oxygen_saturation=float(vraw.oxygen_saturation) if vraw.oxygen_saturation else None, height_cm=float(vraw.height_cm) if vraw.height_cm else None, weight_kg=float(vraw.weight_kg) if vraw.weight_kg else None, bmi=float(vraw.bmi) if vraw.bmi else None, pain_score=vraw.pain_score, bp_status=bp_status(vraw.systolic_bp, vraw.diastolic_bp), bmi_status=bmi_status(float(vraw.bmi) if vraw.bmi else None), spo2_status=spo2_status(float(vraw.oxygen_saturation) if vraw.oxygen_saturation else None), recorded_at=vraw.recorded_at)
    # Diagnoses
    rd = await db.execute(select(Diagnosis).where(Diagnosis.patient_id == patient_id).order_by(desc(Diagnosis.diagnosed_at)).limit(20))
    diagnoses = []
    for d in rd.scalars().all():
        rdt = await db.execute(select(DiagnosisType).where(DiagnosisType.diagnosis_type_id == d.diagnosis_type_id))
        dt = rdt.scalars().first()
        rsv = await db.execute(select(SeverityLevel).where(SeverityLevel.severity_level_id == d.severity_level_id))
        sv = rsv.scalars().first()
        diagnoses.append(DiagnosisResponse(diagnosis_id=d.diagnosis_id, encounter_id=d.encounter_id, patient_id=d.patient_id, doctor_id=d.doctor_id, diagnosis_code=d.diagnosis_code, diagnosis_name=d.diagnosis_name, diagnosis_description=d.diagnosis_description, diagnosis_type=dt.diagnosis_type_name if dt else "Primary", severity=sv.severity_name if sv else "Moderate", diagnosed_at=d.diagnosed_at))
    # Medications
    rm = await db.execute(select(MedicationRecord).where(MedicationRecord.patient_id == patient_id, MedicationRecord.ended_at.is_(None)).order_by(desc(MedicationRecord.created_at)).limit(20))
    medications = [medication_response(m) for m in rm.scalars().all()]
    # Past encounters
    re = await db.execute(select(PatientEncounter).where(PatientEncounter.patient_id == patient_id).order_by(desc(PatientEncounter.encounter_date)).limit(10))
    past = []
    for e in re.scalars().all():
        rdr = await db.execute(select(Doctor).where(Doctor.doctor_id == e.doctor_id))
        doc = rdr.scalars().first()
        past.append({"encounter_id":str(e.encounter_id),"encounter_number":e.encounter_number,"doctor":f"Dr. {doc.first_name} {doc.last_name}" if doc else "Unknown","chief_complaint":e.chief_complaint,"status":e.encounter_status,"date":e.encounter_date.strftime("%Y-%m-%d %H:%M") if e.encounter_date else ""})
    rr = await db.execute(select(Referral).join(PatientEncounter, Referral.encounter_id == PatientEncounter.encounter_id).where(PatientEncounter.patient_id == patient_id, Referral.referral_status == "Pending").order_by(desc(Referral.referred_at)))
    referrals = [ReferralResponse(referral_id=x.referral_id, encounter_id=x.encounter_id, referring_doctor_id=x.referring_doctor_id, referred_department_id=x.referred_department_id, referred_doctor_id=x.referred_doctor_id, referral_reason=x.referral_reason or "", referral_status=x.referral_status, referred_at=x.referred_at) for x in rr.scalars().all()]
    radiology_reports = [dict(row) for row in (await db.execute(text("""SELECT rr.report_id,
        ro.order_number,rt.test_name,s.study_date,rr.report_status,rr.report_text AS findings,rr.impression,
        rr.reported_at FROM radiology.radiology_reports rr JOIN radiology.imaging_studies s USING(study_id)
        JOIN radiology.radiology_appointments a USING(radiology_appointment_id)
        JOIN radiology.radiology_order_items oi ON oi.order_item_id=a.order_item_id
        JOIN radiology.radiology_orders ro USING(radiology_order_id)
        JOIN radiology.radiology_tests rt USING(radiology_test_id)
        WHERE s.patient_id=:patient ORDER BY rr.reported_at DESC LIMIT 20"""),
        {"patient": patient_id})).mappings()]
    blood_transfusions = [dict(row) for row in (await db.execute(text("""SELECT bt.transfusion_id,
        bu.unit_number,bg.group_name blood_group,bc.component_name,bt.volume_transfused,
        bt.start_time,bt.status,bt.adverse_reaction,bt.reaction_details,bt.notes
        FROM blood_bank.blood_transfusions bt JOIN blood_bank.blood_units bu USING(blood_unit_id)
        LEFT JOIN blood_bank.blood_group_types bg USING(blood_group_type_id)
        LEFT JOIN blood_bank.blood_component_types bc USING(blood_component_type_id)
        WHERE bt.patient_id=:patient ORDER BY bt.start_time DESC LIMIT 20"""),
        {"patient": patient_id})).mappings()]
    laboratory_results=[dict(row) for row in (await db.execute(text("""SELECT re.result_entry_id,lt.test_name,re.result_status,re.entered_at,re.approved_at,re.remarks,COALESCE(json_agg(json_build_object('parameter_name',tp.parameter_name,'value',rp.result_value,'unit',tp.unit,'flag',rp.result_flag)) FILTER (WHERE rp.result_parameter_id IS NOT NULL),'[]') parameters FROM laboratory.lab_result_entries re JOIN laboratory.lab_order_items oi USING(order_item_id) JOIN laboratory.lab_orders lo USING(lab_order_id) JOIN laboratory.lab_tests lt USING(test_id) LEFT JOIN laboratory.lab_result_parameters rp USING(result_entry_id) LEFT JOIN laboratory.lab_test_parameters tp USING(parameter_id) WHERE lo.patient_id=:patient AND re.result_status='Approved' GROUP BY re.result_entry_id,lt.test_name ORDER BY re.approved_at DESC LIMIT 20"""),{"patient":patient_id})).mappings()]
    medication_history=[dict(row) for row in (await db.execute(text("SELECT administration_log_id,medicine_name,dosage_given,route,administered_at,administration_status,exception_reason,administration_notes FROM nursing.medication_administration_logs WHERE patient_id=:patient ORDER BY administered_at DESC LIMIT 100"),{"patient":patient_id})).mappings()]
    emergency_visits=[dict(row) for row in (await db.execute(text("""SELECT e.emergency_encounter_id,
        r.registration_number,a.arrival_time,a.arrival_mode,e.chief_complaint,l.severity_rank esi_level,
        l.level_name triage_category,e.encounter_status,e.disposition,e.disposition_notes,e.disposition_at
        FROM emergency.emergency_encounters e JOIN emergency.emergency_registrations r USING(emergency_registration_id)
        JOIN emergency.emergency_arrivals a USING(emergency_arrival_id)
        LEFT JOIN emergency.emergency_triage_levels l ON l.triage_level_id=e.triage_level_id
        WHERE a.patient_id=:patient ORDER BY a.arrival_time DESC LIMIT 20"""),{"patient":patient_id})).mappings()]
    surgery_history=[dict(row) for row in (await db.execute(text("""SELECT sr.surgery_request_id,
        ss.surgery_schedule_id,sr.procedure_name,sr.procedure_code,sr.request_priority,
        ss.scheduled_start,ss.actual_start,ss.actual_end,ss.anesthesia_type,ss.surgical_findings,
        ss.complications,ss.outcome,ss.schedule_status,rr.recovery_status,rr.pain_score,
        rr.observations recovery_observations,rr.disposition recovery_disposition
        FROM surgery.surgery_requests sr LEFT JOIN surgery.surgery_scheduling ss USING(surgery_request_id)
        LEFT JOIN surgery.ot_recovery_records rr USING(surgery_schedule_id)
        WHERE sr.patient_id=:patient ORDER BY COALESCE(ss.actual_start,sr.requested_date) DESC LIMIT 20"""),{"patient":patient_id})).mappings()]
    return PatientEMRSummaryResponse(patient_id=p.patient_id, patient_name=f"{p.first_name} {p.last_name}", mrn=p.mrn, date_of_birth=p.date_of_birth, gender=g.gender_name if g else "Unknown", blood_group=bg.blood_group_name if bg else "Unknown", active_allergies=allergies, latest_vitals=latest_vitals, vital_signs_timeline=[vital_response(v) for v in vital_rows], active_diagnoses=diagnoses, current_medications=medications, past_encounters=past, pending_referrals=referrals, radiology_reports=radiology_reports, blood_transfusions=blood_transfusions,laboratory_results=laboratory_results,medication_administration_history=medication_history,emergency_visits=emergency_visits,surgery_history=surgery_history)

@router.post("/encounters/{encounter_id}/complete")
async def complete_encounter(encounter_id: uuid.UUID, req: CompleteEncounterRequest, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["doctor","admin","super_admin"]))):
    enc = (await db.execute(select(PatientEncounter).where(
        PatientEncounter.encounter_id == encounter_id).with_for_update())).scalars().first()
    if not enc:
        raise HTTPException(404, "Encounter not found")
    await enforce_doctor_scope(cu, db, doctor_id=enc.doctor_id)
    ensure_open(enc)
    medications = (await db.execute(select(MedicationRecord).where(
        MedicationRecord.encounter_id == encounter_id,
        MedicationRecord.ended_at.is_(None),
    ).with_for_update())).scalars().all()
    unlinked = [med for med in medications if not med.drug_id or not med.quantity_prescribed]
    if unlinked:
        raise HTTPException(409, "All active medications must use a catalog drug and prescribed quantity before completion")
    pharmacy_prescription = None
    if medications:
        pharmacy_prescription = (await db.execute(select(Prescription).where(
            Prescription.encounter_id == encounter_id).with_for_update())).scalars().first()
        if not pharmacy_prescription:
            pending = (await db.execute(select(PrescriptionStatus).where(
                PrescriptionStatus.status_name == "Pending"))).scalars().first()
            if not pending:
                pending = PrescriptionStatus(status_name="Pending")
                db.add(pending)
                await db.flush()
            diagnoses = (await db.execute(select(Diagnosis.diagnosis_name).where(
                Diagnosis.encounter_id == encounter_id))).scalars().all()
            pharmacy_prescription = Prescription(
                prescription_number=f"RX-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}",
                patient_id=enc.patient_id, encounter_id=encounter_id, doctor_id=enc.doctor_id,
                prescription_status_id=pending.prescription_status_id,
                diagnosis=", ".join(diagnoses), valid_until=date.today() + timedelta(days=30),
                notes="Issued when the clinical encounter was completed", created_by=cu.user_id,
            )
            db.add(pharmacy_prescription)
            await db.flush()
        existing_items = set((await db.execute(select(PrescriptionItem.medication_record_id).where(
            PrescriptionItem.prescription_id == pharmacy_prescription.prescription_id
        ))).scalars().all())
        for med in medications:
            if med.medication_record_id not in existing_items:
                db.add(PrescriptionItem(
                    prescription_id=pharmacy_prescription.prescription_id,
                    medication_record_id=med.medication_record_id, drug_id=med.drug_id,
                    dosage=med.dosage, frequency=med.frequency, duration=med.duration,
                    route=med.route, quantity_prescribed=med.quantity_prescribed,
                    quantity_dispensed=0, item_status="Pending", instructions=med.instructions,
                ))
            med.medication_status = "Issued"
    enc.encounter_status = "Completed"
    if req.clinical_summary: enc.clinical_summary = req.clinical_summary
    enc.updated_by = cu.user_id
    if enc.appointment_id:
        rst = await db.execute(select(AppointmentStatus).where(AppointmentStatus.status_name == "Completed"))
        st = rst.scalars().first()
        if st:
            rpt = await db.execute(select(Appointment).where(Appointment.appointment_id == enc.appointment_id))
            apt = rpt.scalars().first()
            if apt: apt.appointment_status_id = st.appointment_status_id; apt.completed_at = datetime.utcnow()
        rtok = await db.execute(select(QueueToken).where(QueueToken.appointment_id == enc.appointment_id))
        tok = rtok.scalars().first()
        if tok: tok.status = "completed"; tok.completed_at = datetime.utcnow()
    await db.commit()
    return {"message":"Encounter completed successfully","encounter_id":str(enc.encounter_id),
            "encounter_number":enc.encounter_number,"status":"Completed",
            "pharmacy_prescription_id":str(pharmacy_prescription.prescription_id) if pharmacy_prescription else None}
