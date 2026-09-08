import uuid
import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.api.doctor import Doctor
from app.models.patient import Patient
from app.models.emr_models import (
    TelemedicineProvider, VirtualAppointment, VideoConsultationSession, SessionNote,
    EncounterType, PatientEncounter, ClinicalNote,
)
from app.schemas.emr import (
    TeleAppointmentRequest, TeleAppointmentResponse,
    TeleSessionRequest, TeleSessionResponse, TeleSessionCompleteRequest,
)

router = APIRouter(prefix="/telemedicine", tags=["Telemedicine & Virtual Care"])

def gen_meeting_link(doc_name: str, apt_id: uuid.UUID) -> str:
    return f"https://telehealth.hmshospital.com/meet/{str(apt_id)[:8]}"

async def appointment_response(apt: VirtualAppointment, db: AsyncSession) -> TeleAppointmentResponse:
    rp = await db.execute(select(Patient).where(Patient.patient_id == apt.patient_id))
    patient = rp.scalars().first()
    rpr = await db.execute(select(TelemedicineProvider).where(TelemedicineProvider.provider_id == apt.provider_id))
    provider = rpr.scalars().first()
    doctor = None
    if provider:
        rd = await db.execute(select(Doctor).where(Doctor.doctor_id == provider.doctor_id))
        doctor = rd.scalars().first()
    return TeleAppointmentResponse(
        virtual_appointment_id=apt.virtual_appointment_id,
        patient_name=f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
        mrn=patient.mrn if patient else "",
        doctor_name=f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Unknown",
        appointment_datetime=apt.appointment_datetime,
        consultation_link=apt.consultation_link or "",
        meeting_platform=apt.meeting_platform,
        status=apt.status,
        chief_complaint=apt.chief_complaint,
        emr_encounter_id=apt.emr_encounter_id,
        created_at=apt.created_at,
    )

@router.post("/appointments", response_model=TeleAppointmentResponse, status_code=201)
async def book_virtual_appointment(
    req: TeleAppointmentRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["receptionist","doctor","admin","super_admin"]))
):
    """Schedule a teleconsultation with a meeting link for patient and doctor."""
    rp = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    p = rp.scalars().first()
    if not p: raise HTTPException(404, "Patient not found")
    rd = await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id))
    d = rd.scalars().first()
    if not d: raise HTTPException(404, "Doctor not found")

    # Get or create telemedicine provider
    rpr = await db.execute(select(TelemedicineProvider).where(TelemedicineProvider.doctor_id == req.doctor_id))
    provider = rpr.scalars().first()
    if not provider:
        provider = TelemedicineProvider(doctor_id=req.doctor_id, provider_status="Active")
        db.add(provider)
        await db.flush()

    apt = VirtualAppointment(
        patient_id=req.patient_id,
        provider_id=provider.provider_id,
        appointment_datetime=req.appointment_datetime,
        meeting_platform=req.meeting_platform,
        chief_complaint=req.chief_complaint,
        status="Scheduled",
    )
    db.add(apt)
    await db.flush()
    apt.consultation_link = gen_meeting_link(f"{d.first_name}_{d.last_name}", apt.virtual_appointment_id)
    await db.commit()
    await db.refresh(apt)

    return await appointment_response(apt, db)

@router.get("/appointments/{appointment_id}", response_model=TeleAppointmentResponse)
async def get_virtual_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(VirtualAppointment).where(VirtualAppointment.virtual_appointment_id == appointment_id))
    appointment = result.scalars().first()
    if not appointment:
        raise HTTPException(404, "Virtual appointment not found")
    return await appointment_response(appointment, db)

@router.get("/appointments", response_model=List[TeleAppointmentResponse])
async def list_virtual_appointments(
    patient_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    q = select(VirtualAppointment).order_by(desc(VirtualAppointment.appointment_datetime))
    if patient_id:
        q = q.where(VirtualAppointment.patient_id == patient_id)
    r = await db.execute(q.limit(25))
    return [await appointment_response(apt, db) for apt in r.scalars().all()]

@router.post("/sessions/start", response_model=TeleSessionResponse, status_code=201)
async def start_session(
    req: TeleSessionRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor","admin","super_admin"]))
):
    """Start a live video consultation session."""
    rapt = await db.execute(select(VirtualAppointment).where(VirtualAppointment.virtual_appointment_id == req.virtual_appointment_id))
    apt = rapt.scalars().first()
    if not apt: raise HTTPException(404, "Virtual appointment not found")
    if apt.status in ("In Progress", "Completed"):
        raise HTTPException(409, f"Virtual appointment is already {apt.status.lower()}")

    apt.status = "In Progress"
    sess = VideoConsultationSession(
        virtual_appointment_id=req.virtual_appointment_id,
        session_start_time=datetime.utcnow(),
        session_status="Active"
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)

    return TeleSessionResponse(
        session_id=sess.session_id,
        virtual_appointment_id=sess.virtual_appointment_id,
        session_status=sess.session_status,
        session_start_time=sess.session_start_time,
        session_end_time=None,
    )

@router.post("/sessions/{session_id}/complete", response_model=TeleSessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    req: TeleSessionCompleteRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor","admin","super_admin"]))
):
    """Complete a teleconsultation session and save clinical notes."""
    rs = await db.execute(select(VideoConsultationSession).where(VideoConsultationSession.session_id == session_id))
    sess = rs.scalars().first()
    if not sess: raise HTTPException(404, "Session not found")
    if sess.session_status == "Completed":
        raise HTTPException(409, "Session is already completed")

    sess.session_end_time = datetime.utcnow()
    sess.session_status = "Completed"
    duration = None
    if sess.session_start_time:
        duration = int((sess.session_end_time - sess.session_start_time).total_seconds() / 60)

    note = SessionNote(session_id=session_id, clinical_notes=req.clinical_notes)
    db.add(note)

    # Mark virtual appointment completed
    rapt = await db.execute(select(VirtualAppointment).where(VirtualAppointment.virtual_appointment_id == sess.virtual_appointment_id))
    apt = rapt.scalars().first()
    if apt:
        apt.status = "Completed"
        provider_result = await db.execute(select(TelemedicineProvider).where(TelemedicineProvider.provider_id == apt.provider_id))
        provider = provider_result.scalars().first()
        type_result = await db.execute(select(EncounterType).where(EncounterType.type_name == "Teleconsultation"))
        encounter_type = type_result.scalars().first()
        if not encounter_type:
            encounter_type = EncounterType(type_name="Teleconsultation", description="Virtual clinical consultation")
            db.add(encounter_type)
            await db.flush()
        encounter = PatientEncounter(
            encounter_number=f"TEL-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            patient_id=apt.patient_id,
            doctor_id=provider.doctor_id,
            encounter_type_id=encounter_type.encounter_type_id,
            encounter_date=sess.session_start_time or datetime.utcnow(),
            chief_complaint=apt.chief_complaint or "Telemedicine consultation",
            clinical_summary=req.clinical_notes,
            encounter_status="Completed",
            created_by=cu.user_id,
            updated_by=cu.user_id,
        )
        db.add(encounter)
        await db.flush()
        db.add(ClinicalNote(
            encounter_id=encounter.encounter_id,
            doctor_id=provider.doctor_id,
            note_type="Teleconsultation",
            note_text=json.dumps({"clinical_notes": req.clinical_notes}),
        ))
        apt.emr_encounter_id = encounter.encounter_id

    await db.commit()

    return TeleSessionResponse(
        session_id=sess.session_id,
        virtual_appointment_id=sess.virtual_appointment_id,
        session_status=sess.session_status,
        session_start_time=sess.session_start_time,
        session_end_time=sess.session_end_time,
        duration_minutes=duration,
    )
