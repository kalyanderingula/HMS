import uuid
from datetime import datetime, date, time, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc, text
from sqlalchemy.orm import selectinload

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import (
    Patient,
    Gender,
    BloodGroup,
    MaritalStatus,
    PatientStatus,
    PatientContact,
    PatientAddress,
    PatientEmergencyContact,
)
from app.models.department import Department, SubDepartment
from app.models.employee import Employee
from app.api.doctor import Doctor, Specialization, DoctorStatus
from app.models.receptionist_models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    QueueServicePoint,
    QueueToken,
    Ward,
    Room,
    Bed,
    Admission,
    Visitor,
    VisitorPass,
)
from app.schemas.receptionist import (
    DashboardSummaryResponse,
    RecentActivityItem,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicatePatientMatch,
    DoctorRosterItem,
    AppointmentBookRequest,
    OPDVisitSlipResponse,
    CheckInResponse,
    QueueTokenItem,
    QueueLiveResponse,
    IssueTokenRequest,
    InpatientEnquiryItem,
    VisitorPassRequest,
    VisitorPassResponse,
)

router = APIRouter(prefix="/receptionist", tags=["Receptionist Desk"], dependencies=[Depends(require_roles(["receptionist", "doctor", "nurse", "admin", "visitor_desk"]))])


# =============================================================================
# Helper: Ensure Core Master Statuses Exist
# =============================================================================
async def ensure_appointment_masters(db: AsyncSession):
    for s_name in ["Scheduled", "Confirmed", "Checked-In", "In-Consultation", "Completed", "Cancelled", "No Show"]:
        res = await db.execute(select(AppointmentStatus).where(AppointmentStatus.status_name == s_name))
        if not res.scalars().first():
            db.add(AppointmentStatus(status_name=s_name, description=f"{s_name} status"))

    for t_name in ["Walk-in", "Scheduled", "Follow-Up", "Emergency", "Teleconsultation"]:
        res = await db.execute(select(AppointmentType).where(AppointmentType.type_name == t_name))
        if not res.scalars().first():
            db.add(AppointmentType(type_name=t_name, description=f"{t_name} appointment type"))

    # Service Point
    res_sp = await db.execute(select(QueueServicePoint).where(QueueServicePoint.point_name == "OPD Central Reception"))
    if not res_sp.scalars().first():
        db.add(QueueServicePoint(point_name="OPD Central Reception", location="Ground Floor - Main Lobby"))

    await db.commit()


# =============================================================================
# 1. DASHBOARD & SUMMARY METRICS
# =============================================================================
@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    await ensure_appointment_masters(db)
    today = date.today()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)

    # 1. Total Patients registered today
    res_pat = await db.execute(
        select(func.count(Patient.patient_id)).where(Patient.created_at >= today_start)
    )
    total_patients_today = res_pat.scalar() or 0

    # 2. Total Appointments today
    res_apt = await db.execute(
        select(func.count(Appointment.appointment_id)).where(Appointment.appointment_date == today)
    )
    total_appointments_today = res_apt.scalar() or 0

    # 3. Checked-In today
    res_ci = await db.execute(
        select(func.count(Appointment.appointment_id)).where(
            Appointment.appointment_date == today,
            Appointment.checked_in_at.isnot(None)
        )
    )
    checked_in_today = res_ci.scalar() or 0

    # 4. Active Doctors count
    res_doc = await db.execute(
        select(func.count(Doctor.doctor_id))
    )
    active_doctors_count = res_doc.scalar() or 0

    # 5. Waiting Queue tokens today
    res_q = await db.execute(
        select(func.count(QueueToken.token_id)).where(
            QueueToken.issued_at >= today_start,
            QueueToken.status == "waiting"
        )
    )
    waiting_tokens_count = res_q.scalar() or 0

    # 6. Recent activity feed
    recent_activities: List[RecentActivityItem] = []

    # Recent patients
    res_recent_p = await db.execute(
        select(Patient).order_by(desc(Patient.created_at)).limit(4)
    )
    for p in res_recent_p.scalars().all():
        recent_activities.append(RecentActivityItem(
            activity_type="registration",
            title=f"New Patient Registered: {p.first_name} {p.last_name}",
            description=f"MRN: {p.mrn} | Patient Code: {p.patient_code}",
            timestamp=p.created_at or datetime.utcnow(),
            badge="Registration"
        ))

    # Recent appointments
    res_recent_a = await db.execute(
        select(Appointment).order_by(desc(Appointment.created_at)).limit(4)
    )
    for a in res_recent_a.scalars().all():
        recent_activities.append(RecentActivityItem(
            activity_type="appointment",
            title=f"Appointment Booked: {a.appointment_number}",
            description=f"Date: {a.appointment_date} {a.start_time.strftime('%H:%M') if a.start_time else ''}",
            timestamp=a.created_at or datetime.utcnow(),
            badge="OPD Booking"
        ))

    recent_activities.sort(key=lambda x: x.timestamp, reverse=True)

    return DashboardSummaryResponse(
        total_patients_today=total_patients_today,
        total_appointments_today=total_appointments_today,
        checked_in_today=checked_in_today,
        active_doctors_count=active_doctors_count,
        waiting_tokens_count=waiting_tokens_count,
        today_collections_amount=float(total_appointments_today * 500.0),
        recent_activities=recent_activities[:8]
    )


# =============================================================================
# 2. PATIENT LOOKUP & DUPLICATE PREVENTION
# =============================================================================
@router.post("/patients/check-duplicate", response_model=DuplicateCheckResponse)
async def check_patient_duplicate(req: DuplicateCheckRequest, db: AsyncSession = Depends(get_db)):
    matches: List[DuplicatePatientMatch] = []

    # Check by phone
    if req.phone and len(req.phone.strip()) >= 7:
        clean_phone = req.phone.strip()
        res_contacts = await db.execute(
            select(PatientContact).where(PatientContact.contact_value.ilike(f"%{clean_phone}%"))
        )
        contact_matches = res_contacts.scalars().all()
        for c in contact_matches:
            res_p = await db.execute(select(Patient).where(Patient.patient_id == c.patient_id))
            p = res_p.scalars().first()
            if p:
                matches.append(DuplicatePatientMatch(
                    patient_id=p.patient_id,
                    mrn=p.mrn,
                    patient_code=p.patient_code,
                    full_name=f"{p.first_name} {p.last_name}",
                    phone=c.contact_value,
                    date_of_birth=p.date_of_birth,
                    match_reason=f"Matching Phone Number ({c.contact_value})"
                ))

    # Check by First + Last Name and DOB
    if req.first_name and req.last_name:
        query = select(Patient).where(
            Patient.first_name.ilike(req.first_name.strip()),
            Patient.last_name.ilike(req.last_name.strip())
        )
        if req.date_of_birth:
            query = query.where(Patient.date_of_birth == req.date_of_birth)
        
        res_name = await db.execute(query)
        for p in res_name.scalars().all():
            if not any(m.patient_id == p.patient_id for m in matches):
                matches.append(DuplicatePatientMatch(
                    patient_id=p.patient_id,
                    mrn=p.mrn,
                    patient_code=p.patient_code,
                    full_name=f"{p.first_name} {p.last_name}",
                    phone=None,
                    date_of_birth=p.date_of_birth,
                    match_reason="Matching Full Name and Date of Birth"
                ))

    return DuplicateCheckResponse(
        is_duplicate=len(matches) > 0,
        matches=matches
    )


# =============================================================================
# 3. DOCTOR OPD ROSTER & REAL-TIME AVAILABILITY
# =============================================================================
@router.get("/doctors/availability", response_model=List[DoctorRosterItem])
async def get_doctor_availability(
    department_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Doctor)
    if department_id:
        query = query.where(Doctor.department_id == department_id)
    
    res = await db.execute(query)
    doctors = res.scalars().all()

    today = date.today()
    roster: List[DoctorRosterItem] = []

    for d in doctors:
        # Get Dept Name
        dept_name = "General Medicine"
        if d.department_id:
            res_dept = await db.execute(select(Department).where(Department.department_id == d.department_id))
            dept_obj = res_dept.scalars().first()
            if dept_obj:
                dept_name = dept_obj.department_name

        # Get Specialization
        spec_name = "Consultant Physician"
        if d.sub_department_id:
            res_sub = await db.execute(select(SubDepartment).where(SubDepartment.sub_department_id == d.sub_department_id))
            sub_obj = res_sub.scalars().first()
            if sub_obj:
                spec_name = sub_obj.sub_department_name

        # Today's tokens count for this doctor
        res_t = await db.execute(
            select(func.count(Appointment.appointment_id)).where(
                Appointment.doctor_id == d.doctor_id,
                Appointment.appointment_date == today
            )
        )
        tokens_issued = res_t.scalar() or 0

        # Waiting count
        res_w = await db.execute(
            select(func.count(Appointment.appointment_id)).where(
                Appointment.doctor_id == d.doctor_id,
                Appointment.appointment_date == today,
                Appointment.checked_in_at.isnot(None),
                Appointment.completed_at.is_(None)
            )
        )
        waiting_count = res_w.scalar() or 0

        # Room Number mapping based on doctor code
        room_no = f"Room {100 + (hash(d.doctor_code) % 30) if d.doctor_code else 101}"

        roster.append(DoctorRosterItem(
            doctor_id=d.doctor_id,
            doctor_code=d.doctor_code or "DOC-001",
            doctor_name=f"Dr. {d.first_name} {d.last_name}",
            department_name=dept_name,
            specialization_name=spec_name,
            room_number=room_no,
            consultation_fee=600.0,
            status="Available" if d.status_id == 1 else "On Duty",
            shift_timings="09:00 AM - 05:00 PM",
            tokens_issued_today=tokens_issued,
            waiting_queue_count=waiting_count
        ))

    return roster


# =============================================================================
# 4. OPD APPOINTMENT BOOKING & VISIT SLIP GENERATION
# =============================================================================
@router.post("/appointments/book", response_model=OPDVisitSlipResponse)
async def book_opd_appointment(req: AppointmentBookRequest, db: AsyncSession = Depends(get_db)):
    await ensure_appointment_masters(db)

    # 1. Verify Patient
    res_p = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = res_p.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 2. Verify Doctor
    res_d = await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id).with_for_update())
    doctor = res_d.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Dept & Specialization
    dept_name = "General Medicine"
    if doctor.department_id:
        res_dept = await db.execute(select(Department).where(Department.department_id == doctor.department_id))
        d_obj = res_dept.scalars().first()
        if d_obj:
            dept_name = d_obj.department_name

    spec_name = "Consultant"
    if doctor.sub_department_id:
        res_sub = await db.execute(select(SubDepartment).where(SubDepartment.sub_department_id == doctor.sub_department_id))
        s_obj = res_sub.scalars().first()
        if s_obj:
            spec_name = s_obj.sub_department_name

    apt_date = req.appointment_date or date.today()
    if apt_date < date.today():
        raise HTTPException(422, "Appointment date cannot be in the past")
    now_time = datetime.now().time().replace(microsecond=0)
    if req.time_slot and req.time_slot != "Immediate":
        try:
            now_time = time.fromisoformat(req.time_slot)
        except ValueError:
            raise HTTPException(422, "Time slot must use HH:MM format")
    if req.appointment_type != "Walk-in" and req.time_slot in (None, "Immediate"):
        raise HTTPException(422, "Select a time for scheduled appointments")
    end_at = datetime.combine(apt_date, now_time) + timedelta(minutes=15)
    if end_at.date() != apt_date:
        raise HTTPException(422, "Appointment must finish on the selected date")
    if req.appointment_type != "Walk-in":
        conflict = await db.scalar(select(Appointment).join(AppointmentStatus).where(
            Appointment.doctor_id == req.doctor_id, Appointment.appointment_date == apt_date,
            Appointment.start_time < end_at.time(), Appointment.end_time > now_time,
            AppointmentStatus.status_name.notin_(["Cancelled", "No Show"])))
        if conflict:
            raise HTTPException(409, "Doctor already has an appointment at this time")

    # Generate Appointment Number
    year = datetime.utcnow().year
    res_count = await db.execute(select(func.count(Appointment.appointment_id)))
    apt_seq = (res_count.scalar() or 0) + 1
    apt_number = f"APT-{year}-{uuid.uuid4().hex[:12].upper()}"

    # Generate Token Number for this Doctor on this date
    res_tok_count = await db.execute(
        select(func.count(Appointment.appointment_id)).where(
            Appointment.doctor_id == doctor.doctor_id,
            Appointment.appointment_date == apt_date
        )
    )
    doc_seq = (res_tok_count.scalar() or 0) + 1
    token_number = f"T-{doc_seq:02d}"

    # Get status ID
    res_status = await db.execute(select(AppointmentStatus).where(AppointmentStatus.status_name == ("Checked-In" if req.appointment_type == "Walk-in" else "Confirmed")))
    status_obj = res_status.scalars().first()

    # Get type ID
    res_type = await db.execute(select(AppointmentType).where(AppointmentType.type_name == req.appointment_type))
    type_obj = res_type.scalars().first()

    appointment = Appointment(
        appointment_number=apt_number,
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        department_id=doctor.department_id,
        appointment_type_id=type_obj.appointment_type_id if type_obj else None,
        appointment_status_id=status_obj.appointment_status_id if status_obj else uuid.uuid4(),
        appointment_date=apt_date,
        start_time=now_time,
        end_time=(datetime.combine(apt_date, now_time) + timedelta(minutes=15)).time(),
        chief_complaint=req.chief_complaint,
        checked_in_at=datetime.utcnow() if req.appointment_type == "Walk-in" else None
    )
    db.add(appointment)
    await db.flush()

    # Create Queue Token record
    res_sp = await db.execute(select(QueueServicePoint).limit(1))
    sp = res_sp.scalars().first()
    sp_id = sp.service_point_id if sp else uuid.uuid4()

    queue_tok = QueueToken(
        service_point_id=sp_id,
        token_number=token_number,
        patient_id=patient.patient_id,
        appointment_id=appointment.appointment_id,
        token_type="walk_in" if req.appointment_type == "Walk-in" else "scheduled",
        status="waiting"
    )
    db.add(queue_tok)
    await db.commit()

    # Get Patient Phone
    phone = None
    res_con = await db.execute(select(PatientContact).where(PatientContact.patient_id == patient.patient_id))
    contacts = res_con.scalars().all()
    if contacts:
        phone = contacts[0].contact_value

    room_no = f"Room {100 + (hash(doctor.doctor_code) % 30) if doctor.doctor_code else 101}"

    return OPDVisitSlipResponse(
        appointment_id=appointment.appointment_id,
        appointment_number=apt_number,
        token_number=token_number,
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn,
        phone=phone,
        doctor_name=f"Dr. {doctor.first_name} {doctor.last_name}",
        department_name=dept_name,
        specialization_name=spec_name,
        room_number=room_no,
        appointment_date=apt_date,
        appointment_time=now_time.strftime("%I:%M %p"),
        appointment_type=req.appointment_type,
        consultation_fee=req.consultation_fee,
        payment_method=req.payment_method,
        payment_status="Pending billing",
        queue_status="Waiting (Token Active)",
        issued_at=datetime.utcnow()
    )


# =============================================================================
# 5. PATIENT CHECK-IN
# =============================================================================
@router.post("/appointments/{appointment_id}/check-in", response_model=CheckInResponse)
async def check_in_patient(appointment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Appointment).where(Appointment.appointment_id == appointment_id).with_for_update())
    apt = res.scalars().first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if apt.appointment_date != date.today():
        raise HTTPException(409, "Check-in is only available on the appointment date")
    if apt.completed_at or apt.cancelled_at:
        raise HTTPException(409, "Closed appointments cannot be checked in")
    apt.checked_in_at = datetime.utcnow()

    res_st = await db.execute(select(AppointmentStatus).where(AppointmentStatus.status_name == "Checked-In"))
    st = res_st.scalars().first()
    if st:
        apt.appointment_status_id = st.appointment_status_id

    # Update or add Queue Token
    res_tok = await db.execute(select(QueueToken).where(QueueToken.appointment_id == apt.appointment_id))
    tok = res_tok.scalars().first()
    token_str = "T-01"
    if tok:
        tok.status = "waiting"
        token_str = tok.token_number
    else:
        res_sp = await db.execute(select(QueueServicePoint).limit(1))
        sp = res_sp.scalars().first()
        tok = QueueToken(
            service_point_id=sp.service_point_id if sp else uuid.uuid4(),
            token_number="T-01",
            patient_id=apt.patient_id,
            appointment_id=apt.appointment_id,
            status="waiting"
        )
        db.add(tok)

    await db.commit()

    # Get details for response
    res_p = await db.execute(select(Patient).where(Patient.patient_id == apt.patient_id))
    p = res_p.scalars().first()

    res_d = await db.execute(select(Doctor).where(Doctor.doctor_id == apt.doctor_id))
    d = res_d.scalars().first()

    return CheckInResponse(
        appointment_id=apt.appointment_id,
        appointment_number=apt.appointment_number,
        patient_name=f"{p.first_name} {p.last_name}" if p else "Patient",
        mrn=p.mrn if p else "",
        doctor_name=f"Dr. {d.first_name} {d.last_name}" if d else "Doctor",
        room_number="Room 102",
        token_number=token_str,
        status="Checked-In (Active in Queue)",
        checked_in_at=apt.checked_in_at
    )


# =============================================================================
# 6. LIVE OPD QUEUE MANAGEMENT
# =============================================================================
@router.get("/queue/live", response_model=QueueLiveResponse)
async def get_live_queue(db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    today_start = datetime.combine(date.today(), time.min)

    token_query = select(QueueToken).where(QueueToken.issued_at >= today_start)
    if "doctor" in cu.roles and not any(r in cu.roles for r in ("admin", "super_admin", "receptionist")):
        doctor_query = select(Doctor).where(Doctor.employee_id == cu.employee_id) if cu.employee_id else select(Doctor).where(Doctor.doctor_code == cu.username)
        doctor = (await db.execute(doctor_query)).scalars().first()
        if not doctor:
            raise HTTPException(403, "No doctor profile is linked to this login")
        token_query = token_query.join(Appointment, QueueToken.appointment_id == Appointment.appointment_id).where(Appointment.doctor_id == doctor.doctor_id)
    res_tokens = await db.execute(token_query.order_by(QueueToken.issued_at.asc()))
    tokens = res_tokens.scalars().all()

    items: List[QueueTokenItem] = []
    waiting_count = 0
    in_cons_count = 0
    completed_count = 0

    for t in tokens:
        if t.status == "waiting":
            waiting_count += 1
        elif t.status == "in_consultation":
            in_cons_count += 1
        elif t.status == "completed":
            completed_count += 1

        p_name = "Walk-in Patient"
        mrn = "-"
        if t.patient_id:
            res_p = await db.execute(select(Patient).where(Patient.patient_id == t.patient_id))
            p = res_p.scalars().first()
            if p:
                p_name = f"{p.first_name} {p.last_name}"
                mrn = p.mrn

        doc_name = "OPD Duty Doctor"
        doctor_id = None
        dept_name = "General OPD"
        room_no = "Room 101"

        if t.appointment_id:
            res_a = await db.execute(select(Appointment).where(Appointment.appointment_id == t.appointment_id))
            a = res_a.scalars().first()
            if a and a.doctor_id:
                res_d = await db.execute(select(Doctor).where(Doctor.doctor_id == a.doctor_id))
                d = res_d.scalars().first()
                if d:
                    doctor_id = d.doctor_id
                    doc_name = f"Dr. {d.first_name} {d.last_name}"
                    room_no = f"Room {100 + (hash(d.doctor_code) % 30) if d.doctor_code else 101}"

        items.append(QueueTokenItem(
            token_id=t.token_id,
            appointment_id=t.appointment_id,
            token_number=t.token_number,
            patient_id=t.patient_id,
            patient_name=p_name,
            mrn=mrn,
            doctor_name=doc_name,
            doctor_id=doctor_id,
            department_name=dept_name,
            room_number=room_no,
            token_type=t.token_type,
            priority=t.priority,
            status=t.status,
            issued_at=t.issued_at,
            called_at=t.called_at
        ))

    return QueueLiveResponse(
        total_in_queue=len(tokens),
        waiting_count=waiting_count,
        in_consultation_count=in_cons_count,
        completed_count=completed_count,
        tokens=items
    )


@router.put("/queue/{token_id}/status")
async def update_queue_token_status(token_id: uuid.UUID, new_status: str = Query(...), db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    res = await db.execute(select(QueueToken).where(QueueToken.token_id == token_id))
    tok = res.scalars().first()
    if not tok:
        raise HTTPException(status_code=404, detail="Token not found")
    if "doctor" in cu.roles and not any(r in cu.roles for r in ("admin", "super_admin", "receptionist")):
        doctor_query = select(Doctor).where(Doctor.employee_id == cu.employee_id) if cu.employee_id else select(Doctor).where(Doctor.doctor_code == cu.username)
        doctor = (await db.execute(doctor_query)).scalars().first()
        appointment = (await db.execute(select(Appointment).where(Appointment.appointment_id == tok.appointment_id))).scalars().first()
        if not doctor or not appointment or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(403, "This patient is assigned to another doctor")

    tok.status = new_status
    if new_status == "called":
        tok.called_at = datetime.utcnow()
    elif new_status == "in_consultation":
        tok.serving_at = datetime.utcnow()
    elif new_status == "completed":
        tok.completed_at = datetime.utcnow()

    await db.commit()
    return {"message": f"Token {tok.token_number} updated to {new_status}", "token_id": token_id}


# =============================================================================
# 7. INPATIENT / BED ENQUIRY
# =============================================================================
@router.get("/enquiry/inpatient", response_model=List[InpatientEnquiryItem])
async def search_inpatient_admissions(
    q: Optional[str] = Query(None, description="Patient Name or MRN"),
    db: AsyncSession = Depends(get_db)
):
    query = select(Admission)
    res = await db.execute(query.order_by(desc(Admission.admission_date)).limit(25))
    admissions = res.scalars().all()

    results: List[InpatientEnquiryItem] = []

    for adm in admissions:
        res_p = await db.execute(select(Patient).where(Patient.patient_id == adm.patient_id))
        p = res_p.scalars().first()
        if not p:
            continue

        full_name = f"{p.first_name} {p.last_name}"
        if q and q.strip():
            query_str = q.strip().lower()
            if query_str not in full_name.lower() and query_str not in p.mrn.lower():
                continue

        # Ward
        ward_name = "General Medical Ward"
        floor_no = "2nd Floor"
        if adm.ward_id:
            res_w = await db.execute(select(Ward).where(Ward.ward_id == adm.ward_id))
            w = res_w.scalars().first()
            if w:
                ward_name = w.ward_name
                floor_no = w.floor_number or "2nd Floor"

        # Room & Bed
        room_no = "Room 204"
        if adm.room_id:
            res_r = await db.execute(select(Room).where(Room.room_id == adm.room_id))
            r = res_r.scalars().first()
            if r:
                room_no = r.room_number

        bed_no = "Bed B-02"
        if adm.bed_id:
            res_b = await db.execute(select(Bed).where(Bed.bed_id == adm.bed_id))
            b = res_b.scalars().first()
            if b:
                bed_no = b.bed_number

        # Doctor
        doc_name = "Dr. Robert Vance"
        if adm.admitting_doctor_id:
            res_d = await db.execute(select(Doctor).where(Doctor.doctor_id == adm.admitting_doctor_id))
            d = res_d.scalars().first()
            if d:
                doc_name = f"Dr. {d.first_name} {d.last_name}"

        results.append(InpatientEnquiryItem(
            admission_id=adm.admission_id,
            admission_number=adm.admission_number,
            patient_name=full_name,
            mrn=p.mrn,
            gender="Female" if p.gender_id == 2 else "Male",
            age_or_dob=str(p.date_of_birth),
            ward_name=ward_name,
            room_number=room_no,
            bed_number=bed_no,
            floor_number=floor_no,
            attending_doctor=doc_name,
            department_name="Inpatient Care",
            admission_date=adm.admission_date,
            admission_status="Admitted" if not adm.actual_discharge_date else "Discharged"
        ))

    return results


# =============================================================================
# 8. VISITOR PASS MANAGEMENT
# =============================================================================
@router.post("/visitors/issue-pass", response_model=VisitorPassResponse)
async def issue_visitor_pass(req: VisitorPassRequest, db: AsyncSession = Depends(get_db)):
    # 1. Create or get Visitor
    res_v = await db.execute(select(Visitor).where(Visitor.phone == req.visitor_phone))
    visitor = res_v.scalars().first()
    if not visitor:
        names = req.visitor_name.split(" ", 1)
        visitor = Visitor(
            first_name=names[0],
            last_name=names[1] if len(names) > 1 else "",
            phone=req.visitor_phone,
            id_proof_number=req.id_proof_number
        )
        db.add(visitor)
        await db.flush()

    # 2. Generate Pass Number
    year = datetime.utcnow().year
    res_c = await db.execute(select(func.count(VisitorPass.pass_id)))
    v_seq = (res_c.scalar() or 0) + 1
    pass_number = f"VP-{year}-{v_seq:04d}"

    issued_at = datetime.utcnow()
    valid_until = issued_at + timedelta(hours=req.valid_hours)

    v_pass = VisitorPass(
        visitor_id=visitor.visitor_id,
        patient_id=req.patient_id,
        pass_number=pass_number,
        check_in_time=issued_at,
        expected_duration_minutes=req.valid_hours * 60,
        status="active"
    )
    db.add(v_pass)
    await db.commit()

    return VisitorPassResponse(
        pass_id=v_pass.pass_id,
        pass_number=pass_number,
        visitor_name=req.visitor_name,
        visitor_phone=req.visitor_phone,
        patient_name=req.patient_mrn_or_name,
        patient_mrn=req.patient_mrn_or_name,
        ward_or_room=req.ward_or_room or "Ward 3A - Room 302",
        issued_at=issued_at,
        valid_until=valid_until,
        status="Active (Valid)"
    )


@router.get("/visitors/today", response_model=List[VisitorPassResponse])
async def list_today_visitor_passes(db: AsyncSession = Depends(get_db)):
    today_start = datetime.combine(date.today(), time.min)
    res = await db.execute(
        select(VisitorPass).where(VisitorPass.check_in_time >= today_start).order_by(desc(VisitorPass.check_in_time))
    )
    passes = res.scalars().all()

    results: List[VisitorPassResponse] = []
    for vp in passes:
        res_v = await db.execute(select(Visitor).where(Visitor.visitor_id == vp.visitor_id))
        v = res_v.scalars().first()

        p_name = "Admitted Patient"
        if vp.patient_id:
            res_p = await db.execute(select(Patient).where(Patient.patient_id == vp.patient_id))
            p = res_p.scalars().first()
            if p:
                p_name = f"{p.first_name} {p.last_name} ({p.mrn})"

        results.append(VisitorPassResponse(
            pass_id=vp.pass_id,
            pass_number=vp.pass_number,
            visitor_name=f"{v.first_name} {v.last_name}" if v else "Visitor",
            visitor_phone=v.phone if v else "-",
            patient_name=p_name,
            patient_mrn=p_name,
            ward_or_room="Inpatient Ward 2B",
            issued_at=vp.check_in_time,
            valid_until=vp.check_in_time + timedelta(minutes=vp.expected_duration_minutes or 240),
            status=vp.status.upper()
        ))

    return results
