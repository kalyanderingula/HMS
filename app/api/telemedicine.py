import uuid
import json
from datetime import date, datetime, time, timedelta
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
from app.models.specialized_ops_models import VideoRoom
from app.models.receptionist_models import Appointment, AppointmentStatus
from app.schemas.emr import (
    TeleAppointmentRequest, TeleAppointmentResponse,
    TeleSessionRequest, TeleSessionResponse, TeleSessionCompleteRequest,
)
from app.schemas.specialized_operations import (
    VideoRoomResponse, InSessionOrderRequest, InSessionOrderResponse
)

router = APIRouter(prefix="/telemedicine", tags=["Telemedicine & Virtual Care"])


async def enforce_virtual_appointment_access(
    appointment: VirtualAppointment,
    cu: CurrentUser,
    db: AsyncSession,
    *,
    allow_reception: bool = False,
) -> None:
    """Enforce ownership/assignment for a single virtual appointment."""
    roles = set(cu.roles or [])
    if roles.intersection({"admin", "super_admin"}):
        return
    if "patient" in roles:
        if cu.patient_id != appointment.patient_id:
            raise HTTPException(404, "Virtual appointment not found")
        return
    if allow_reception and "receptionist" in roles:
        return
    if roles.intersection({"doctor", "telemedicine_doctor"}):
        provider = await db.get(TelemedicineProvider, appointment.provider_id)
        doctor = await db.get(Doctor, provider.doctor_id) if provider else None
        if not doctor or not cu.employee_id or doctor.employee_id != cu.employee_id:
            raise HTTPException(404, "Virtual appointment not found")
        return
    raise HTTPException(403, "Telemedicine access is restricted")

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


@router.get("/availability")
async def virtual_consultation_availability(
    doctor_id: uuid.UUID,
    schedule_date: date,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["receptionist", "doctor", "telemedicine_doctor", "admin", "super_admin"])),
):
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    if any(role in cu.roles for role in ("doctor", "telemedicine_doctor")) and not any(role in cu.roles for role in ("receptionist", "admin", "super_admin")):
        if not cu.employee_id or doctor.employee_id != cu.employee_id:
            raise HTTPException(403, "Doctors can view only their own availability")

    day_start = datetime.combine(schedule_date, time.min)
    day_end = day_start + timedelta(days=1)
    provider = (await db.execute(select(TelemedicineProvider).where(
        TelemedicineProvider.doctor_id == doctor_id))).scalars().first()
    virtual_rows = []
    if provider:
        virtual_rows = (await db.execute(select(VirtualAppointment).where(
            VirtualAppointment.provider_id == provider.provider_id,
            VirtualAppointment.appointment_datetime >= day_start,
            VirtualAppointment.appointment_datetime < day_end,
            VirtualAppointment.status.notin_(["Cancelled", "Completed"]),
        ))).scalars().all()
    opd_rows = (await db.execute(select(Appointment, AppointmentStatus).join(
        AppointmentStatus, AppointmentStatus.appointment_status_id == Appointment.appointment_status_id
    ).where(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == schedule_date,
        AppointmentStatus.status_name.notin_(["Cancelled", "No Show"]),
    ))).all()

    slots = []
    cursor = datetime.combine(schedule_date, time(9, 0))
    finish = datetime.combine(schedule_date, time(17, 0))
    while cursor < finish:
        slot_end = cursor + timedelta(minutes=15)
        is_past = cursor < datetime.now()
        virtual_conflict = next((item for item in virtual_rows
            if item.appointment_datetime < slot_end and item.appointment_datetime + timedelta(minutes=15) > cursor), None)
        opd_conflict = next((item for item, _ in opd_rows
            if datetime.combine(schedule_date, item.start_time) < slot_end
            and datetime.combine(schedule_date, item.end_time) > cursor), None)
        conflict_type = "Past time" if is_past else "Virtual consultation" if virtual_conflict else "OPD appointment" if opd_conflict else None
        slots.append({"start_time": cursor.strftime("%H:%M"), "end_time": slot_end.strftime("%H:%M"),
                      "available": not is_past and not virtual_conflict and not opd_conflict, "conflict_type": conflict_type})
        cursor = slot_end
    return {"doctor_id": str(doctor_id), "date": schedule_date.isoformat(), "slot_minutes": 15, "slots": slots}

@router.post("/appointments", response_model=TeleAppointmentResponse, status_code=201)
async def book_virtual_appointment(
    req: TeleAppointmentRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["receptionist","doctor","telemedicine_doctor","admin","super_admin"]))
):
    """Schedule a teleconsultation with a meeting link for patient and doctor."""
    rp = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    p = rp.scalars().first()
    if not p: raise HTTPException(404, "Patient not found")
    rd = await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id))
    d = rd.scalars().first()
    if not d: raise HTTPException(404, "Doctor not found")

    slot_start = req.appointment_datetime
    slot_end = slot_start + timedelta(minutes=15)
    if slot_start < datetime.now():
        raise HTTPException(422, "Virtual consultation time must be in the future")
    await db.execute(select(Patient.patient_id).where(Patient.patient_id == req.patient_id).with_for_update())
    await db.execute(select(Doctor.doctor_id).where(Doctor.doctor_id == req.doctor_id).with_for_update())
    from app.api.patient_portal import ensure_slot_available
    await ensure_slot_available(db, req.doctor_id, req.patient_id, slot_start.date(), slot_start.time())
    provider_for_conflict = (await db.execute(select(TelemedicineProvider).where(
        TelemedicineProvider.doctor_id == req.doctor_id))).scalars().first()
    if provider_for_conflict:
        virtual_conflict = await db.scalar(select(VirtualAppointment.virtual_appointment_id).where(
            VirtualAppointment.provider_id == provider_for_conflict.provider_id,
            VirtualAppointment.status.notin_(["Cancelled", "Completed"]),
            VirtualAppointment.appointment_datetime < slot_end,
            VirtualAppointment.appointment_datetime + timedelta(minutes=15) > slot_start,
        ).limit(1))
        if virtual_conflict:
            raise HTTPException(409, "Doctor already has a virtual consultation in this time slot")
    opd_conflict = await db.scalar(select(Appointment.appointment_id).join(
        AppointmentStatus, AppointmentStatus.appointment_status_id == Appointment.appointment_status_id
    ).where(
        Appointment.doctor_id == req.doctor_id,
        Appointment.appointment_date == slot_start.date(),
        Appointment.start_time < slot_end.time(),
        Appointment.end_time > slot_start.time(),
        AppointmentStatus.status_name.notin_(["Cancelled", "No Show"]),
    ).limit(1))
    if opd_conflict:
        raise HTTPException(409, "Doctor already has an OPD appointment in this time slot")

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
    await enforce_virtual_appointment_access(appointment, cu, db, allow_reception=True)
    return await appointment_response(appointment, db)

@router.get("/appointments", response_model=List[TeleAppointmentResponse])
async def list_virtual_appointments(
    patient_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    roles = set(cu.roles or [])
    q = select(VirtualAppointment).order_by(desc(VirtualAppointment.appointment_datetime))
    if "patient" in roles:
        if not cu.patient_id:
            raise HTTPException(403, "No patient profile is linked to this login")
        if patient_id and patient_id != cu.patient_id:
            raise HTTPException(404, "Patient not found")
        q = q.where(VirtualAppointment.patient_id == cu.patient_id)
    elif roles.intersection({"doctor", "telemedicine_doctor"}) and not roles.intersection({"admin", "super_admin"}):
        if not cu.employee_id:
            raise HTTPException(403, "No doctor profile is linked to this login")
        q = q.join(
            TelemedicineProvider,
            VirtualAppointment.provider_id == TelemedicineProvider.provider_id,
        ).join(Doctor, TelemedicineProvider.doctor_id == Doctor.doctor_id).where(
            Doctor.employee_id == cu.employee_id
        )
        if patient_id:
            q = q.where(VirtualAppointment.patient_id == patient_id)
    elif roles.intersection({"receptionist", "admin", "super_admin"}):
        if patient_id:
            q = q.where(VirtualAppointment.patient_id == patient_id)
    else:
        raise HTTPException(403, "Telemedicine access is restricted")
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
    await enforce_virtual_appointment_access(apt, cu, db)
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
    appointment = await db.get(VirtualAppointment, sess.virtual_appointment_id)
    if not appointment:
        raise HTTPException(404, "Virtual appointment not found")
    await enforce_virtual_appointment_access(appointment, cu, db)
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


# ----------------- Milestone 3: WebRTC Video Room & Live Clinical Orders -----------------

@router.post("/appointments/{appointment_id}/video-room", response_model=VideoRoomResponse, status_code=201)
async def get_or_create_video_room(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "patient", "admin", "super_admin"]))
):
    """Generate or retrieve a secure WebRTC/Jitsi embedded video consultation room."""
    apt = await db.get(VirtualAppointment, appointment_id)
    if not apt:
        raise HTTPException(404, "Virtual appointment not found")
    await enforce_virtual_appointment_access(apt, cu, db)

    existing_room = await db.scalar(
        select(VideoRoom).where(VideoRoom.virtual_appointment_id == appointment_id, VideoRoom.is_active == True)
    )
    if existing_room:
        return VideoRoomResponse(
            room_id=existing_room.room_id,
            virtual_appointment_id=existing_room.virtual_appointment_id,
            room_name=existing_room.room_name,
            room_url=existing_room.room_url,
            host_token="" if "patient" in (cu.roles or []) else (existing_room.host_token or ""),
            participant_token=existing_room.participant_token or "",
            is_active=existing_room.is_active
        )

    room_name = f"telemeet-{str(appointment_id)[:8]}"
    room_url = f"https://meet.hmshospital.com/{room_name}#config.prejoinPageEnabled=false"
    host_token = f"host_tok_{uuid.uuid4().hex[:16]}"
    part_token = f"part_tok_{uuid.uuid4().hex[:16]}"

    room = VideoRoom(
        virtual_appointment_id=appointment_id,
        room_name=room_name,
        room_url=room_url,
        host_token=host_token,
        participant_token=part_token,
        is_active=True
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)

    return VideoRoomResponse(
        room_id=room.room_id,
        virtual_appointment_id=room.virtual_appointment_id,
        room_name=room.room_name,
        room_url=room.room_url,
        host_token="" if "patient" in (cu.roles or []) else room.host_token,
        participant_token=room.participant_token,
        is_active=room.is_active
    )


@router.post("/sessions/{session_id}/orders", response_model=InSessionOrderResponse, status_code=201)
async def create_in_session_order(
    session_id: uuid.UUID,
    req: InSessionOrderRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"]))
):
    """Synchronize clinical orders (e-prescription, lab order, radiology) during an active teleconsultation."""
    sess = await db.get(VideoConsultationSession, session_id)
    if not sess:
        raise HTTPException(404, "Video session not found")

    apt = await db.get(VirtualAppointment, sess.virtual_appointment_id)
    if not apt:
        raise HTTPException(404, "Virtual appointment not found")
    await enforce_virtual_appointment_access(apt, cu, db)

    ref_id = uuid.uuid4()
    # If the appointment already has an emr encounter, link it
    encounter_id = apt.emr_encounter_id

    # Record order note
    note_content = {
        "order_type": req.order_type,
        "details": req.details,
        "item_catalog_ids": [str(x) for x in req.item_catalog_ids],
        "ordered_in_session_id": str(session_id),
        "reference_id": str(ref_id)
    }
    session_note = SessionNote(
        session_id=session_id,
        clinical_notes=f"[{req.order_type.upper()} ORDER]: {req.details}"
    )
    db.add(session_note)
    await db.commit()

    return InSessionOrderResponse(
        order_type=req.order_type,
        linked_encounter_id=encounter_id,
        reference_id=ref_id,
        message=f"Live {req.order_type} successfully placed during teleconsultation session"
    )

