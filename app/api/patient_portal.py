import uuid
from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUser, Role, User, UserRole, IdentityLink, hash_password, require_roles, link_identity
from app.config import get_db
from app.models.patient import Patient, PatientContact
from app.models.emr_models import TelemedicineProvider, VirtualAppointment
from app.identifiers import generate_appointment_number


router = APIRouter(prefix="/patient-portal", tags=["Patient Self Service"])
patient_access = require_roles(["patient"])


class PatientAccountRegistration(BaseModel):
    mrn: str = Field(min_length=3, max_length=50)
    date_of_birth: date
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    password: str = Field(min_length=8, max_length=72)

    @model_validator(mode="after")
    def require_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Email or phone is required")
        return self

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if value and ("@" not in value or "." not in value.rsplit("@", 1)[-1]):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("password")
    @classmethod
    def valid_password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class PatientProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    email: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if value and ("@" not in value or "." not in value.rsplit("@", 1)[-1]):
            raise ValueError("Enter a valid email address")
        return value


class PatientAppointmentCreate(BaseModel):
    doctor_id: uuid.UUID
    appointment_date: date
    time_slot: time
    appointment_mode: Literal["In-person", "Virtual"] = "In-person"
    chief_complaint: str = Field(min_length=2, max_length=2000)


class PatientAppointmentReschedule(BaseModel):
    appointment_date: date
    time_slot: time


class CancellationReason(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


async def own_patient(db: AsyncSession, user: CurrentUser):
    patient_id = await db.scalar(select(IdentityLink.identity_id).where(
        IdentityLink.user_id == user.user_id, IdentityLink.identity_type == "patient"))
    if not patient_id:
        patient_id = await db.scalar(select(User.patient_id).where(User.user_id == user.user_id))
    if not patient_id:
        raise HTTPException(403, "Patient account is not linked to a patient record")
    return patient_id


@router.post("/register", status_code=201)
async def register_patient_account(req: PatientAccountRegistration, db: AsyncSession = Depends(get_db)):
    patient = await db.scalar(select(Patient).where(Patient.mrn == req.mrn.strip(),
                                                     Patient.date_of_birth == req.date_of_birth,
                                                     Patient.deleted_at.is_(None)))
    if not patient:
        raise HTTPException(404, "Patient identity could not be verified")
    supplied = (req.email or req.phone or "").strip().lower()
    contact_match = await db.scalar(select(PatientContact.contact_id).where(
        PatientContact.patient_id == patient.patient_id,
        PatientContact.contact_value.ilike(supplied)))
    if not contact_match:
        raise HTTPException(403, "Contact information does not match the patient record")
    if await db.scalar(select(User.user_id).where(User.patient_id == patient.patient_id)):
        raise HTTPException(409, "A portal account already exists for this patient")
    username = patient.mrn
    if await db.scalar(select(User.user_id).where(User.username == username)):
        raise HTTPException(409, "The patient username is already in use")
    role = await db.scalar(select(Role).where(Role.role_name == "patient"))
    if not role:
        role = Role(role_name="patient"); db.add(role); await db.flush()
    email = str(req.email).lower() if req.email else None
    if email and await db.scalar(select(User.user_id).where(User.email == email)):
        raise HTTPException(409, "Email is already associated with another account")
    user = User(username=username, email=email, password_hash=hash_password(req.password), status="active",
                must_change_password=False, patient_id=patient.patient_id)
    db.add(user); await db.flush()
    await link_identity(db, user.user_id, "patient", patient.patient_id)
    db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    await db.commit()
    return {"username":username,"patient_id":patient.patient_id,"message":"Patient portal account created"}


@router.get("/me")
async def patient_profile(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id = await own_patient(db, user)
    row = (await db.execute(text("""SELECT p.patient_id,p.patient_code,p.mrn,p.first_name,p.middle_name,
        p.last_name,p.date_of_birth,g.gender_name,b.blood_group_name,m.marital_status_name,
        max(c.contact_value) FILTER(WHERE c.contact_type='phone') phone,
        max(c.contact_value) FILTER(WHERE c.contact_type='email') email
        FROM patient.patients p JOIN patient.genders g USING(gender_id)
        LEFT JOIN patient.blood_groups b USING(blood_group_id)
        LEFT JOIN patient.marital_statuses m USING(marital_status_id)
        LEFT JOIN patient.patient_contacts c USING(patient_id) WHERE p.patient_id=:id
        GROUP BY p.patient_id,g.gender_name,b.blood_group_name,m.marital_status_name"""),{"id":patient_id})).mappings().first()
    if not row: raise HTTPException(404,"Patient record not found")
    return dict(row)


@router.put("/me")
async def update_patient_contact(req: PatientProfileUpdate, db: AsyncSession = Depends(get_db),
                                 user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    if req.phone is None and req.email is None: raise HTTPException(422,"Provide an email or phone update")
    for contact_type,value in (("phone",req.phone),("email",str(req.email) if req.email else None)):
        if value is None: continue
        existing=await db.scalar(select(PatientContact).where(PatientContact.patient_id==patient_id,
                                                               PatientContact.contact_type==contact_type,
                                                               PatientContact.is_primary.is_(contact_type=="phone")))
        if existing: existing.contact_value=value.strip()
        else: db.add(PatientContact(patient_id=patient_id,contact_type=contact_type,
                                    contact_value=value.strip(),is_primary=contact_type=="phone"))
        if contact_type=="email": await db.execute(text("UPDATE security.users SET email=:email WHERE user_id=:user"),{"email":value.lower(),"user":user.user_id})
    await db.commit(); return await patient_profile(db,user)


@router.get("/appointments")
async def patient_appointments(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    rows=await db.execute(text("""SELECT a.appointment_id,a.appointment_number,a.appointment_date,a.doctor_id,
        a.start_time,a.end_time,a.chief_complaint,a.notes,s.status_name,
        concat('Dr. ',d.first_name,' ',d.last_name) doctor_name
        FROM appointment.appointments a LEFT JOIN appointment.appointment_statuses s USING(appointment_status_id)
        LEFT JOIN doctor.doctors d USING(doctor_id) WHERE a.patient_id=:patient
        ORDER BY a.appointment_date DESC,a.start_time DESC LIMIT 100"""),{"patient":patient_id})
    appointments = [{**dict(row), "appointment_mode": "In-person", "consultation_link": None}
                    for row in rows.mappings()]
    virtual_rows = await db.execute(text("""SELECT va.virtual_appointment_id appointment_id,
        concat('VIRTUAL-',upper(substr(CAST(va.virtual_appointment_id AS text),1,8))) appointment_number,
        va.appointment_datetime,va.chief_complaint,va.status status_name,va.consultation_link,
        tp.doctor_id,concat('Dr. ',d.first_name,' ',d.last_name) doctor_name
        FROM telemedicine.virtual_appointments va
        JOIN telemedicine.telemedicine_providers tp USING(provider_id)
        JOIN doctor.doctors d USING(doctor_id)
        WHERE va.patient_id=:patient ORDER BY va.appointment_datetime DESC LIMIT 100"""),
        {"patient": patient_id})
    for row in virtual_rows.mappings():
        start = row["appointment_datetime"]
        appointments.append({
            "appointment_id": row["appointment_id"], "appointment_number": row["appointment_number"],
            "appointment_date": start.date(), "doctor_id": row["doctor_id"],
            "start_time": start.time(), "end_time": (start + timedelta(minutes=15)).time(),
            "chief_complaint": row["chief_complaint"], "notes": None,
            "status_name": row["status_name"], "doctor_name": row["doctor_name"],
            "appointment_mode": "Virtual", "consultation_link": row["consultation_link"],
        })
    appointments.sort(key=lambda item: datetime.combine(item["appointment_date"], item["start_time"]), reverse=True)
    return appointments[:100]


@router.get("/doctors")
async def patient_doctors(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(patient_access)):
    rows=await db.execute(text("""SELECT d.doctor_id,d.doctor_code,
        concat('Dr. ',d.first_name,' ',d.last_name) doctor_name,dep.department_name,
        sub.sub_department_name specialization_name FROM doctor.doctors d
        LEFT JOIN core.departments dep USING(department_id)
        LEFT JOIN core.sub_departments sub USING(sub_department_id)
        WHERE d.deleted_at IS NULL ORDER BY d.first_name,d.last_name"""))
    return [dict(row) for row in rows.mappings()]


@router.get("/doctors/{doctor_id}/availability")
async def patient_doctor_availability(
    doctor_id: uuid.UUID,
    day: date,
    exclude_appointment_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(patient_access),
):
    doctor_exists = await db.scalar(text(
        "SELECT doctor_id FROM doctor.doctors WHERE doctor_id=:doctor AND deleted_at IS NULL"
    ), {"doctor": doctor_id})
    if not doctor_exists:
        raise HTTPException(404, "Doctor not found")

    patient_id = await own_patient(db, user)
    exclusion = ""
    parameters = {"doctor": doctor_id, "day": day}
    current_appointment = None
    if exclude_appointment_id:
        current_appointment = (await db.execute(text("""SELECT appointment_id,appointment_date,start_time,end_time
            FROM appointment.appointments
            WHERE appointment_id=:appointment AND patient_id=:patient AND doctor_id=:doctor"""),
            {"appointment": exclude_appointment_id, "patient": patient_id, "doctor": doctor_id})).mappings().first()
        if not current_appointment:
            raise HTTPException(404, "Appointment not found")
        exclusion = "AND a.appointment_id<>:exclude"
        parameters["exclude"] = exclude_appointment_id

    opd_rows = (await db.execute(text(f"""SELECT a.start_time,a.end_time
        FROM appointment.appointments a
        LEFT JOIN appointment.appointment_statuses s USING(appointment_status_id)
        WHERE a.doctor_id=:doctor AND a.appointment_date=:day
        AND COALESCE(s.status_name,'') NOT IN ('Cancelled','No Show')
        {exclusion}"""), parameters)).mappings().all()
    patient_parameters = {"patient": patient_id, "day": day}
    patient_exclusion = ""
    if exclude_appointment_id:
        patient_parameters["exclude"] = exclude_appointment_id
        patient_exclusion = "AND a.appointment_id<>:exclude"
    patient_rows = (await db.execute(text(f"""SELECT a.start_time,a.end_time
        FROM appointment.appointments a
        LEFT JOIN appointment.appointment_statuses s USING(appointment_status_id)
        WHERE a.patient_id=:patient AND a.appointment_date=:day
        AND COALESCE(s.status_name,'') NOT IN ('Cancelled','No Show')
        {patient_exclusion}"""), patient_parameters)).mappings().all()
    virtual_rows = (await db.execute(text("""SELECT va.appointment_datetime
        FROM telemedicine.virtual_appointments va
        JOIN telemedicine.telemedicine_providers tp USING(provider_id)
        WHERE tp.doctor_id=:doctor
        AND va.appointment_datetime>=:day_start AND va.appointment_datetime<:day_end
        AND va.status NOT IN ('Cancelled','Completed')"""), {
            "doctor": doctor_id,
            "day_start": datetime.combine(day, time.min),
            "day_end": datetime.combine(day + timedelta(days=1), time.min),
        })).mappings().all()
    patient_virtual_rows = (await db.execute(text("""SELECT va.appointment_datetime
        FROM telemedicine.virtual_appointments va
        WHERE va.patient_id=:patient
        AND va.appointment_datetime>=:day_start AND va.appointment_datetime<:day_end
        AND va.status NOT IN ('Cancelled','Completed')"""), {
            "patient": patient_id,
            "day_start": datetime.combine(day, time.min),
            "day_end": datetime.combine(day + timedelta(days=1), time.min),
        })).mappings().all()

    slots = []
    cursor = datetime.combine(day, time(9, 0))
    finish = datetime.combine(day, time(17, 0))
    while cursor < finish:
        slot_end = cursor + timedelta(minutes=15)
        opd_conflict = any(
            datetime.combine(day, row["start_time"]) < slot_end
            and datetime.combine(day, row["end_time"]) > cursor
            for row in opd_rows
        )
        virtual_conflict = any(
            row["appointment_datetime"] < slot_end
            and row["appointment_datetime"] + timedelta(minutes=15) > cursor
            for row in virtual_rows
        )
        patient_conflict = any(
            datetime.combine(day, row["start_time"]) < slot_end
            and datetime.combine(day, row["end_time"]) > cursor
            for row in patient_rows
        ) or any(
            row["appointment_datetime"] < slot_end
            and row["appointment_datetime"] + timedelta(minutes=15) > cursor
            for row in patient_virtual_rows
        )
        current_booking = bool(
            current_appointment
            and current_appointment["appointment_date"] == day
            and datetime.combine(day, current_appointment["start_time"]) < slot_end
            and datetime.combine(day, current_appointment["end_time"]) > cursor
        )
        past = cursor < datetime.now()
        slots.append({
            "start_time": cursor.strftime("%H:%M"),
            "end_time": slot_end.strftime("%H:%M"),
            "available": not past and not current_booking and not patient_conflict and not opd_conflict and not virtual_conflict,
            "status": "Past" if past else "Current booking" if current_booking else "Your appointment" if patient_conflict else "Booked" if opd_conflict or virtual_conflict else "Available",
        })
        cursor = slot_end
    return {"doctor_id": doctor_id, "date": day, "slot_minutes": 15, "slots": slots}


async def appointment_status_id(db, name):
    return await db.scalar(text("""INSERT INTO appointment.appointment_statuses(status_name)
        VALUES(:name) ON CONFLICT(status_name) DO UPDATE SET status_name=EXCLUDED.status_name
        RETURNING appointment_status_id"""),{"name":name})


async def ensure_slot_available(db, doctor_id, patient_id, appointment_date, start_at, exclude=None):
    start_datetime = datetime.combine(appointment_date, start_at)
    if start_datetime < datetime.now():
        raise HTTPException(422, "Appointment time must be in the future")
    if start_at < time(9, 0) or start_at >= time(17, 0) or start_at.minute % 15 != 0 or start_at.second:
        raise HTTPException(422, "Select a 15-minute slot between 09:00 and 17:00")
    end_datetime = start_datetime + timedelta(minutes=15)
    end_at=end_datetime.time()
    exclusion = "AND a.appointment_id<>:exclude" if exclude else ""
    conflict=await db.scalar(text(f"""SELECT a.appointment_id FROM appointment.appointments a
        LEFT JOIN appointment.appointment_statuses s USING(appointment_status_id)
        WHERE a.doctor_id=:doctor AND a.appointment_date=:day AND a.start_time<:finish AND a.end_time>:start
        AND COALESCE(s.status_name,'') NOT IN ('Cancelled','No Show')
        {exclusion} LIMIT 1"""),
        {"doctor":doctor_id,"day":appointment_date,"start":start_at,"finish":end_at,"exclude":exclude})
    if conflict: raise HTTPException(409,"Doctor already has an appointment at this time")
    virtual_conflict = await db.scalar(text("""SELECT va.virtual_appointment_id
        FROM telemedicine.virtual_appointments va
        JOIN telemedicine.telemedicine_providers tp USING(provider_id)
        WHERE tp.doctor_id=:doctor AND va.status NOT IN ('Cancelled','Completed')
        AND va.appointment_datetime<:finish
        AND va.appointment_datetime + interval '15 minutes'>:start LIMIT 1"""),
        {"doctor": doctor_id, "start": start_datetime, "finish": end_datetime})
    if virtual_conflict:
        raise HTTPException(409, "Doctor already has a virtual consultation at this time")
    patient_conflict = await db.scalar(text(f"""SELECT a.appointment_id
        FROM appointment.appointments a
        LEFT JOIN appointment.appointment_statuses s USING(appointment_status_id)
        WHERE a.patient_id=:patient AND a.appointment_date=:day
        AND a.start_time<:finish AND a.end_time>:start
        AND COALESCE(s.status_name,'') NOT IN ('Cancelled','No Show')
        {exclusion} LIMIT 1"""),
        {"patient": patient_id, "day": appointment_date, "start": start_at,
         "finish": end_at, "exclude": exclude})
    if patient_conflict:
        raise HTTPException(409, "You already have another appointment at this time")
    patient_virtual_conflict = await db.scalar(text("""SELECT virtual_appointment_id
        FROM telemedicine.virtual_appointments
        WHERE patient_id=:patient AND status NOT IN ('Cancelled','Completed')
        AND appointment_datetime<:finish
        AND appointment_datetime + interval '15 minutes'>:start LIMIT 1"""),
        {"patient": patient_id, "start": start_datetime, "finish": end_datetime})
    if patient_virtual_conflict:
        raise HTTPException(409, "You already have a virtual consultation at this time")
    return end_at


@router.post("/appointments", status_code=201)
async def book_patient_appointment(req: PatientAppointmentCreate, db: AsyncSession = Depends(get_db),
                                   user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    if req.appointment_date<date.today(): raise HTTPException(422,"Appointment date cannot be in the past")
    await db.execute(text("SELECT patient_id FROM patient.patients WHERE patient_id=:id FOR UPDATE"), {"id": patient_id})
    doctor=(await db.execute(text("SELECT doctor_id,department_id FROM doctor.doctors WHERE doctor_id=:id AND deleted_at IS NULL FOR UPDATE"),{"id":req.doctor_id})).mappings().first()
    if not doctor: raise HTTPException(404,"Doctor not found")
    end_at=await ensure_slot_available(db,req.doctor_id,patient_id,req.appointment_date,req.time_slot)
    if req.appointment_mode == "Virtual":
        provider = (await db.execute(select(TelemedicineProvider).where(
            TelemedicineProvider.doctor_id == req.doctor_id
        ))).scalars().first()
        if not provider:
            provider = TelemedicineProvider(doctor_id=req.doctor_id, provider_status="Active")
            db.add(provider)
            await db.flush()
        virtual_appointment = VirtualAppointment(
            patient_id=patient_id, provider_id=provider.provider_id,
            appointment_datetime=datetime.combine(req.appointment_date, req.time_slot),
            meeting_platform="HMS Telehealth", chief_complaint=req.chief_complaint,
            status="Scheduled",
        )
        db.add(virtual_appointment)
        await db.flush()
        virtual_appointment.consultation_link = f"https://telehealth.hmshospital.com/meet/{str(virtual_appointment.virtual_appointment_id)[:8]}"
        await db.commit()
        return {"appointment_id": virtual_appointment.virtual_appointment_id,
                "appointment_number": f"VIRTUAL-{str(virtual_appointment.virtual_appointment_id)[:8].upper()}",
                "appointment_mode": "Virtual", "consultation_link": virtual_appointment.consultation_link,
                "status": "Scheduled"}
    appointment_type=await db.scalar(text("""INSERT INTO appointment.appointment_types(type_name)
        VALUES('Scheduled') ON CONFLICT(type_name) DO UPDATE SET type_name=EXCLUDED.type_name
        RETURNING appointment_type_id"""))
    appointment_id=uuid.uuid4(); number=await generate_appointment_number(db, req.appointment_date)
    await db.execute(text("""INSERT INTO appointment.appointments
        (appointment_id,appointment_number,patient_id,doctor_id,department_id,appointment_type_id,
         appointment_status_id,appointment_date,start_time,end_time,estimated_duration_minutes,
         chief_complaint,booking_source,booked_by)
        VALUES(:id,:number,:patient,:doctor,:department,:type,:status,:day,:start,:finish,15,:complaint,'Patient Portal',:user)"""),
        {"id":appointment_id,"number":number,"patient":patient_id,"doctor":req.doctor_id,
         "department":doctor["department_id"],"type":appointment_type,
         "status":await appointment_status_id(db,"Confirmed"),"day":req.appointment_date,
         "start":req.time_slot,"finish":end_at,"complaint":req.chief_complaint,"user":user.user_id})
    await db.commit(); return {"appointment_id":appointment_id,"appointment_number":number,
                              "appointment_mode":"In-person","status":"Confirmed"}


@router.put("/appointments/{appointment_id}/reschedule")
async def reschedule_patient_appointment(appointment_id: uuid.UUID, req: PatientAppointmentReschedule,
                                         db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    if req.appointment_date<date.today(): raise HTTPException(422,"Appointment date cannot be in the past")
    await db.execute(text("SELECT patient_id FROM patient.patients WHERE patient_id=:id FOR UPDATE"), {"id": patient_id})
    appointment=(await db.execute(text("""SELECT a.*,s.status_name FROM appointment.appointments a
        LEFT JOIN appointment.appointment_statuses s USING(appointment_status_id)
        WHERE a.appointment_id=:id AND a.patient_id=:patient FOR UPDATE OF a"""),{"id":appointment_id,"patient":patient_id})).mappings().first()
    if not appointment: raise HTTPException(404,"Appointment not found")
    if appointment["status_name"] in {"Cancelled","Completed","Checked-In"}: raise HTTPException(409,"Appointment cannot be rescheduled in its current status")
    end_at=await ensure_slot_available(db,appointment["doctor_id"],patient_id,req.appointment_date,req.time_slot,appointment_id)
    await db.execute(text("UPDATE appointment.appointments SET appointment_date=:day,start_time=:start,end_time=:finish,updated_at=CURRENT_TIMESTAMP WHERE appointment_id=:id"),{"day":req.appointment_date,"start":req.time_slot,"finish":end_at,"id":appointment_id})
    await db.commit(); return {"appointment_id":appointment_id,"status":"Confirmed","message":"Appointment rescheduled"}


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_patient_appointment(appointment_id: uuid.UUID, req: CancellationReason,
                                     db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    appointment=(await db.execute(text("""SELECT a.appointment_id,s.status_name FROM appointment.appointments a
        LEFT JOIN appointment.appointment_statuses s USING(appointment_status_id)
        WHERE a.appointment_id=:id AND a.patient_id=:patient FOR UPDATE OF a"""),{"id":appointment_id,"patient":patient_id})).mappings().first()
    if not appointment: raise HTTPException(404,"Appointment not found")
    if appointment["status_name"] in {"Cancelled","Completed"}: raise HTTPException(409,"Appointment cannot be cancelled in its current status")
    await db.execute(text("""UPDATE appointment.appointments SET appointment_status_id=:status,
        cancelled_at=CURRENT_TIMESTAMP,notes=concat_ws(E'\\n',notes,CAST(:reason AS TEXT)),updated_at=CURRENT_TIMESTAMP
        WHERE appointment_id=:id"""),{"status":await appointment_status_id(db,"Cancelled"),"reason":f"Patient cancellation: {req.reason}","id":appointment_id})
    await db.commit(); return {"appointment_id":appointment_id,"status":"Cancelled"}


@router.get("/prescriptions")
async def patient_prescriptions(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    rows=await db.execute(text("""SELECT p.prescription_id,p.prescription_number,p.prescription_date,
        s.status_name,pi.prescription_item_id,d.generic_name,pi.dosage,pi.frequency,pi.duration,
        pi.route,pi.quantity_prescribed,pi.quantity_dispensed,pi.item_status,pi.instructions
        FROM pharmacy.prescriptions p JOIN pharmacy.prescription_items pi USING(prescription_id)
        JOIN pharmacy.drugs d USING(drug_id) LEFT JOIN pharmacy.prescription_statuses s USING(prescription_status_id)
        WHERE p.patient_id=:patient ORDER BY p.prescription_date DESC"""),{"patient":patient_id})
    return [dict(row) for row in rows.mappings()]


@router.get("/results")
async def patient_results(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    laboratory=[dict(row) for row in (await db.execute(text("""SELECT re.result_entry_id,lt.test_name,
        re.result_status,re.approved_at,re.remarks FROM laboratory.lab_result_entries re
        JOIN laboratory.lab_order_items oi USING(order_item_id) JOIN laboratory.lab_orders lo USING(lab_order_id)
        JOIN laboratory.lab_tests lt USING(test_id) WHERE lo.patient_id=:patient AND re.result_status='Approved'
        ORDER BY re.approved_at DESC"""),{"patient":patient_id})).mappings()]
    radiology=[dict(row) for row in (await db.execute(text("""SELECT rr.report_id,rt.test_name,
        rr.report_status,rr.report_text findings,rr.impression,rr.reported_at
        FROM radiology.radiology_reports rr JOIN radiology.imaging_studies s USING(study_id)
        JOIN radiology.radiology_appointments a USING(radiology_appointment_id)
        JOIN radiology.radiology_order_items oi ON oi.order_item_id=a.order_item_id
        JOIN radiology.radiology_orders ro USING(radiology_order_id)
        JOIN radiology.radiology_tests rt USING(radiology_test_id)
        WHERE s.patient_id=:patient AND rr.report_status='Final' ORDER BY rr.reported_at DESC"""),{"patient":patient_id})).mappings()]
    return {"laboratory":laboratory,"radiology":radiology}


@router.get("/billing")
async def patient_billing(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    invoices=[dict(row) for row in (await db.execute(text("""SELECT i.invoice_id,i.invoice_number,i.invoice_date,
        i.total_amount,i.paid_amount,i.balance_amount,s.status_name FROM billing.invoices i
        LEFT JOIN billing.billing_statuses s USING(billing_status_id) WHERE i.patient_id=:patient
        ORDER BY i.invoice_date DESC"""),{"patient":patient_id})).mappings()]
    return {"invoices":invoices,"total_outstanding":sum((row["balance_amount"] or 0 for row in invoices),0)}


@router.get("/care-history")
async def patient_care_history(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    patient_id=await own_patient(db,user)
    admissions=[dict(row) for row in (await db.execute(text("SELECT admission_id,admission_number,admission_date,actual_discharge_date,admission_reason,discharge_summary,discharge_condition FROM admission.admissions WHERE patient_id=:patient ORDER BY admission_date DESC"),{"patient":patient_id})).mappings()]
    emergency=[dict(row) for row in (await db.execute(text("""SELECT e.emergency_encounter_id,a.arrival_time,e.chief_complaint,
        l.level_name triage_category,e.encounter_status,e.disposition,e.disposition_notes,e.disposition_at
        FROM emergency.emergency_encounters e JOIN emergency.emergency_registrations r USING(emergency_registration_id)
        JOIN emergency.emergency_arrivals a USING(emergency_arrival_id)
        LEFT JOIN emergency.emergency_triage_levels l ON l.triage_level_id=e.triage_level_id
        WHERE a.patient_id=:patient ORDER BY a.arrival_time DESC"""),{"patient":patient_id})).mappings()]
    surgeries=[dict(row) for row in (await db.execute(text("""SELECT sr.surgery_request_id,ss.surgery_schedule_id,
        sr.procedure_name,sr.request_priority,sr.request_status,ss.scheduled_start,ss.surgical_findings,
        ss.outcome,rr.recovery_status,rr.disposition FROM surgery.surgery_requests sr
        LEFT JOIN surgery.surgery_scheduling ss USING(surgery_request_id)
        LEFT JOIN surgery.ot_recovery_records rr USING(surgery_schedule_id)
        WHERE sr.patient_id=:patient ORDER BY sr.requested_date DESC"""),{"patient":patient_id})).mappings()]
    return {"admissions":admissions,"emergency":emergency,"surgeries":surgeries}


@router.get("/notifications")
async def patient_notifications(db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(patient_access)):
    await own_patient(db,user)
    rows=await db.execute(text("SELECT notification_id,source_module,subject,body,status,created_at,sent_at FROM core.notifications WHERE recipient_id=:user ORDER BY created_at DESC LIMIT 100"),{"user":user.user_id})
    return [dict(row) for row in rows.mappings()]
