import uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel, Field

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

emergency_access = require_roles(["receptionist", "emergency_staff", "nurse", "doctor", "admin"])
clinical_access = require_roles(["emergency_staff", "nurse", "doctor", "admin"])
doctor_access = require_roles(["emergency_staff", "doctor", "admin"])
router = APIRouter(prefix="/emergency", tags=["Emergency & Trauma Care"], dependencies=[Depends(emergency_access)])


class EmergencyVitalsCreate(BaseModel):
    emergency_encounter_id: uuid.UUID
    temperature: float = Field(ge=25, le=45)
    pulse_rate: int = Field(ge=10, le=300)
    respiratory_rate: int = Field(ge=1, le=100)
    systolic_bp: int = Field(ge=30, le=300)
    diastolic_bp: int = Field(ge=20, le=200)
    oxygen_saturation: float = Field(ge=0, le=100)


class EmergencyNoteCreate(BaseModel):
    emergency_encounter_id: uuid.UUID
    note_type: Literal["Assessment", "Treatment", "Procedure", "Observation"]
    note_text: str = Field(min_length=2, max_length=4000)


class EmergencyDisposition(BaseModel):
    disposition: Literal["Discharged", "Admitted", "Transferred", "Deceased"]
    notes: str = Field(min_length=3, max_length=4000)
    doctor_id: uuid.UUID | None = None
    bed_id: uuid.UUID | None = None

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
    cu: CurrentUser = Depends(require_roles(["receptionist", "emergency_staff", "nurse", "doctor", "admin"]))
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
    cu: CurrentUser = Depends(clinical_access)
):
    await ensure_emergency_masters(db)
    arr_res = await db.execute(select(EmergencyArrival).where(EmergencyArrival.emergency_arrival_id == req.emergency_arrival_id).with_for_update())
    arrival = arr_res.scalars().first()
    if not arrival: raise HTTPException(404, "Emergency arrival record not found")

    p_res = await db.execute(select(Patient).where(Patient.patient_id == arrival.patient_id))
    patient = p_res.scalars().first()

    lvl_res = await db.execute(select(EmergencyTriageLevel).where(EmergencyTriageLevel.severity_rank == req.esi_level))
    level = lvl_res.scalars().first()
    if not level: raise HTTPException(400, "Invalid ESI triage level (Must be 1 to 5)")

    if await db.scalar(select(EmergencyTriageAssessment.triage_id).where(EmergencyTriageAssessment.emergency_arrival_id == req.emergency_arrival_id)):
        raise HTTPException(409, "Arrival has already been triaged")
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
    registration_id = uuid.uuid4()
    encounter_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO emergency.emergency_registrations
        (emergency_registration_id,emergency_arrival_id,registration_number,registered_at,registration_status)
        VALUES(:id,:arrival,:number,CURRENT_TIMESTAMP,'Registered')"""),
        {"id":registration_id,"arrival":arrival.emergency_arrival_id,"number":f"ER-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"})
    await db.execute(text("""INSERT INTO emergency.emergency_encounters
        (emergency_encounter_id,emergency_registration_id,triage_level_id,chief_complaint,encounter_status)
        VALUES(:id,:registration,:level,:complaint,'Active')"""),
        {"id":encounter_id,"registration":registration_id,"level":level.triage_level_id,"complaint":req.chief_complaint})
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


@router.get("/queue")
async def emergency_queue(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    condition = "AND e.encounter_status='Active'" if active_only else ""
    rows = await db.execute(text(f"""SELECT e.emergency_encounter_id,a.emergency_arrival_id,
        r.registration_number,p.patient_id,p.mrn,concat_ws(' ',p.first_name,p.last_name) patient_name,
        a.arrival_mode,a.arrival_time,a.arrival_condition,t.chief_complaint,l.severity_rank esi_level,
        l.level_name triage_category,l.response_time_minutes,t.trauma_bay_code,e.encounter_status,
        e.disposition,e.disposition_at
        FROM emergency.emergency_encounters e
        JOIN emergency.emergency_registrations r USING(emergency_registration_id)
        JOIN emergency.emergency_arrivals a USING(emergency_arrival_id)
        JOIN patient.patients p USING(patient_id)
        JOIN emergency.emergency_triage_assessments t USING(emergency_arrival_id)
        JOIN emergency.emergency_triage_levels l ON l.triage_level_id=e.triage_level_id
        WHERE 1=1 {condition} ORDER BY l.severity_rank,a.arrival_time"""))
    return [dict(row) for row in rows.mappings()]


@router.get("/untriaged")
async def untriaged_arrivals(patient_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    patient_filter = "AND a.patient_id=:patient" if patient_id else ""
    rows = await db.execute(text(f"""SELECT a.emergency_arrival_id,a.patient_id,a.arrival_time,
        concat_ws(' ',p.first_name,p.last_name) patient_name,p.mrn,a.arrival_mode,
        concat(a.arrival_mode,' - ',to_char(a.arrival_time,'DD Mon HH24:MI')) arrival_label
        FROM emergency.emergency_arrivals a JOIN patient.patients p USING(patient_id)
        WHERE NOT EXISTS (SELECT 1 FROM emergency.emergency_triage_assessments t
                          WHERE t.emergency_arrival_id=a.emergency_arrival_id)
        {patient_filter} ORDER BY a.arrival_time DESC LIMIT 100"""), {"patient":patient_id})
    return [dict(row) for row in rows.mappings()]


@router.get("/admission-options")
async def emergency_admission_options(db: AsyncSession = Depends(get_db)):
    beds = [dict(row) for row in (await db.execute(text("""SELECT b.bed_id,
        concat(w.ward_name,' / ',r.room_number,' / ',b.bed_number) label
        FROM admission.beds b JOIN admission.rooms r USING(room_id) JOIN admission.wards w USING(ward_id)
        LEFT JOIN admission.admissions a ON a.bed_id=b.bed_id AND a.actual_discharge_date IS NULL
        WHERE a.admission_id IS NULL ORDER BY w.ward_name,r.room_number,b.bed_number LIMIT 100"""))).mappings()]
    doctors = [dict(row) for row in (await db.execute(text("""SELECT doctor_id,
        concat('Dr. ',first_name,' ',last_name) label FROM doctor.doctors
        WHERE deleted_at IS NULL ORDER BY first_name,last_name"""))).mappings()]
    return {"beds":beds,"doctors":doctors}


async def active_encounter(db, encounter_id, lock=False):
    query = "SELECT * FROM emergency.emergency_encounters WHERE emergency_encounter_id=:id"
    if lock: query += " FOR UPDATE"
    row = (await db.execute(text(query), {"id": encounter_id})).mappings().first()
    if not row: raise HTTPException(404, "Emergency encounter not found")
    if row["encounter_status"] != "Active": raise HTTPException(409, "Emergency encounter is already closed")
    return row


@router.post("/vitals", status_code=201)
async def record_emergency_vitals(req: EmergencyVitalsCreate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(clinical_access)):
    await active_encounter(db, req.emergency_encounter_id)
    vital_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO emergency.emergency_vital_signs
        (emergency_vital_sign_id,emergency_encounter_id,temperature,pulse_rate,respiratory_rate,
         systolic_bp,diastolic_bp,oxygen_saturation,recorded_at)
        VALUES(:id,:encounter,:temperature,:pulse,:respiratory,:systolic,:diastolic,:oxygen,CURRENT_TIMESTAMP)"""),
        {"id":vital_id,"encounter":req.emergency_encounter_id,"temperature":req.temperature,
         "pulse":req.pulse_rate,"respiratory":req.respiratory_rate,"systolic":req.systolic_bp,
         "diastolic":req.diastolic_bp,"oxygen":req.oxygen_saturation})
    await db.commit()
    return {"emergency_vital_sign_id":vital_id,"status":"Recorded"}


@router.post("/notes", status_code=201)
async def record_emergency_note(req: EmergencyNoteCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(clinical_access)):
    await active_encounter(db, req.emergency_encounter_id)
    note_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO emergency.emergency_clinical_notes
        (emergency_note_id,emergency_encounter_id,note_type,note_text,recorded_by)
        VALUES(:id,:encounter,:type,:note,:user)"""),
        {"id":note_id,"encounter":req.emergency_encounter_id,"type":req.note_type,"note":req.note_text,"user":user.user_id})
    await db.commit()
    return {"emergency_note_id":note_id,"status":"Recorded"}


@router.get("/encounters/{encounter_id}")
async def emergency_encounter_detail(encounter_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    queue = await emergency_queue(False, db)
    case = next((row for row in queue if row["emergency_encounter_id"] == encounter_id), None)
    if not case: raise HTTPException(404, "Emergency encounter not found")
    case["vitals"] = [dict(r) for r in (await db.execute(text("SELECT * FROM emergency.emergency_vital_signs WHERE emergency_encounter_id=:id ORDER BY recorded_at"),{"id":encounter_id})).mappings()]
    case["notes"] = [dict(r) for r in (await db.execute(text("SELECT * FROM emergency.emergency_clinical_notes WHERE emergency_encounter_id=:id ORDER BY recorded_at"),{"id":encounter_id})).mappings()]
    return case


@router.post("/encounters/{encounter_id}/disposition")
async def dispose_emergency_encounter(encounter_id: uuid.UUID, req: EmergencyDisposition,
                                      db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(doctor_access)):
    encounter = await active_encounter(db, encounter_id, True)
    admission_id = None
    if req.disposition == "Admitted":
        if not req.doctor_id or not req.bed_id:
            raise HTTPException(422, "Doctor and available bed are required for admission")
        patient_id = await db.scalar(text("""SELECT a.patient_id FROM emergency.emergency_registrations r
            JOIN emergency.emergency_arrivals a USING(emergency_arrival_id)
            WHERE r.emergency_registration_id=:id"""), {"id":encounter["emergency_registration_id"]})
        if await db.scalar(text("SELECT admission_id FROM admission.admissions WHERE patient_id=:patient AND actual_discharge_date IS NULL"),{"patient":patient_id}):
            raise HTTPException(409, "Patient already has an active admission")
        bed = (await db.execute(text("""SELECT b.bed_id,b.room_id,r.ward_id FROM admission.beds b
            JOIN admission.rooms r USING(room_id) WHERE b.bed_id=:id FOR UPDATE"""),{"id":req.bed_id})).mappings().first()
        if not bed or await db.scalar(text("SELECT admission_id FROM admission.admissions WHERE bed_id=:bed AND actual_discharge_date IS NULL"),{"bed":req.bed_id}):
            raise HTTPException(409, "Bed is not available")
        if not await db.scalar(text("SELECT doctor_id FROM doctor.doctors WHERE doctor_id=:id"),{"id":req.doctor_id}):
            raise HTTPException(404, "Doctor not found")
        admission_id = uuid.uuid4()
        await db.execute(text("""INSERT INTO admission.admissions
            (admission_id,admission_number,patient_id,bed_id,room_id,ward_id,admitting_doctor_id,
             admission_date,admission_reason,notes)
            VALUES(:id,:number,:patient,:bed,:room,:ward,:doctor,CURRENT_TIMESTAMP,:reason,'Admission type: Emergency')"""),
            {"id":admission_id,"number":f"ADM-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}",
             "patient":patient_id,"bed":req.bed_id,"room":bed["room_id"],"ward":bed["ward_id"],
             "doctor":req.doctor_id,"reason":req.notes})
    if req.disposition == "Discharged":
        await db.execute(text("INSERT INTO emergency.emergency_discharges(emergency_encounter_id,discharge_condition,discharge_summary,discharged_at) VALUES(:id,'Stable',:notes,CURRENT_TIMESTAMP)"),{"id":encounter_id,"notes":req.notes})
    elif req.disposition == "Transferred":
        await db.execute(text("INSERT INTO emergency.emergency_transfers(emergency_encounter_id,transfer_destination,transfer_reason,transferred_at) VALUES(:id,'External facility',:notes,CURRENT_TIMESTAMP)"),{"id":encounter_id,"notes":req.notes})
    await db.execute(text("""UPDATE emergency.emergency_encounters SET encounter_status='Closed',
        disposition=:disposition,disposition_notes=:notes,disposition_at=CURRENT_TIMESTAMP,
        disposition_by=:user,admission_id=:admission WHERE emergency_encounter_id=:id"""),
        {"disposition":req.disposition,"notes":req.notes,"user":user.user_id,"admission":admission_id,"id":encounter_id})
    await db.commit()
    return {"emergency_encounter_id":encounter_id,"disposition":req.disposition,"admission_id":admission_id,"status":"Closed"}
