"""Seed rich demo data for Receptionist, OPD Doctors, and Inpatient Wards"""
import asyncio
import os
import secrets
from datetime import datetime, date, time, timedelta
import bcrypt
from sqlalchemy import select
from app.config import async_session
from app.models.department import Department, SubDepartment
from app.models.employee import Employee, EmployeeCategory, EmployeeType
from app.api.auth import User, Role, UserRole
from app.api.doctor import Doctor, Specialization, DoctorStatus
from app.models.patient import (
    Patient, Gender, BloodGroup, MaritalStatus, PatientStatus,
    PatientContact, PatientAddress, PatientEmergencyContact
)
from app.models.receptionist_models import (
    Appointment, AppointmentStatus, AppointmentType,
    QueueServicePoint, QueueToken, Ward, Room, Bed, Admission
)

async def seed_demo():
    async with async_session() as db:
        print("1. Ensuring Master Lookups...")
        # Genders
        g_map = {}
        for g_name in ["Male", "Female", "Other"]:
            res = await db.execute(select(Gender).where(Gender.gender_name == g_name))
            g = res.scalars().first()
            if not g:
                g = Gender(gender_name=g_name)
                db.add(g)
                await db.flush()
            g_map[g_name] = g.gender_id

        # Blood Groups
        bg_map = {}
        for bg_name in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
            res = await db.execute(select(BloodGroup).where(BloodGroup.blood_group_name == bg_name))
            bg = res.scalars().first()
            if not bg:
                bg = BloodGroup(blood_group_name=bg_name)
                db.add(bg)
                await db.flush()
            bg_map[bg_name] = bg.blood_group_id

        # Marital Status
        ms_map = {}
        for ms_name in ["Single", "Married", "Divorced", "Widowed"]:
            res = await db.execute(select(MaritalStatus).where(MaritalStatus.marital_status_name == ms_name))
            ms = res.scalars().first()
            if not ms:
                ms = MaritalStatus(marital_status_name=ms_name)
                db.add(ms)
                await db.flush()
            ms_map[ms_name] = ms.marital_status_id

        # Patient Status
        ps_map = {}
        for ps_name in ["Active", "Inactive", "Deceased"]:
            res = await db.execute(select(PatientStatus).where(PatientStatus.status_name == ps_name))
            ps = res.scalars().first()
            if not ps:
                ps = PatientStatus(status_name=ps_name)
                db.add(ps)
                await db.flush()
            ps_map[ps_name] = ps.status_id

        # Doctor Statuses
        ds_map = {}
        for ds_name in ["Active", "On Leave", "In Surgery", "Off Duty"]:
            res = await db.execute(select(DoctorStatus).where(DoctorStatus.status_name == ds_name))
            ds = res.scalars().first()
            if not ds:
                ds = DoctorStatus(status_name=ds_name)
                db.add(ds)
                await db.flush()
            ds_map[ds_name] = ds.status_id

        # Appointment Statuses
        apt_st_map = {}
        for s_name in ["Scheduled", "Confirmed", "Checked-In", "In-Consultation", "Completed", "Cancelled"]:
            res = await db.execute(select(AppointmentStatus).where(AppointmentStatus.status_name == s_name))
            s = res.scalars().first()
            if not s:
                s = AppointmentStatus(status_name=s_name, description=s_name)
                db.add(s)
                await db.flush()
            apt_st_map[s_name] = s.appointment_status_id

        # Appointment Types
        apt_tp_map = {}
        for t_name in ["Walk-in", "Scheduled", "Follow-Up", "Emergency"]:
            res = await db.execute(select(AppointmentType).where(AppointmentType.type_name == t_name))
            t = res.scalars().first()
            if not t:
                t = AppointmentType(type_name=t_name, description=t_name)
                db.add(t)
                await db.flush()
            apt_tp_map[t_name] = t.appointment_type_id

        # Service Point
        res_sp = await db.execute(select(QueueServicePoint).where(QueueServicePoint.point_name == "OPD Central Reception"))
        sp = res_sp.scalars().first()
        if not sp:
            sp = QueueServicePoint(point_name="OPD Central Reception", location="Ground Floor - Main Lobby")
            db.add(sp)
            await db.flush()

        await db.commit()

        print("2. Seeding Sample Doctors...")
        # Get doctor department
        res_d_dept = await db.execute(select(Department).where(Department.department_code == "DEP-DOC"))
        doc_dept = res_d_dept.scalars().first()

        doctors_data = [
            ("DOC-CARD-001", "Marcus", "Vance", "marcus.vance@hospital.com", "DOC-CARD", 12, "Cardiology"),
            ("DOC-ORTH-002", "Elena", "Rostova", "elena.rostova@hospital.com", "DOC-ORTH", 8, "Orthopedics"),
            ("DOC-PEDI-003", "Aarav", "Sharma", "aarav.sharma@hospital.com", "DOC-PEDI", 15, "Pediatrics"),
            ("DOC-GP-004", "David", "Kim", "david.kim@hospital.com", "DOC-GP", 10, "General Physician"),
            ("DOC-NEUR-005", "Sophia", "Chen", "sophia.chen@hospital.com", "DOC-NEUR", 14, "Neurology"),
        ]

        doc_objs = []
        for code, fn, ln, email, sub_code, exp, spec_title in doctors_data:
            res_sub = await db.execute(select(SubDepartment).where(SubDepartment.sub_department_code == sub_code))
            sub_obj = res_sub.scalars().first()

            res_doc = await db.execute(select(Doctor).where(Doctor.doctor_code == code))
            doc = res_doc.scalars().first()
            if not doc:
                doc = Doctor(
                    doctor_code=code,
                    first_name=fn,
                    last_name=ln,
                    email=email,
                    phone="+1-555-0100",
                    status_id=ds_map.get("Active", 1),
                    joining_date=date(2020, 6, 1),
                    consultation_experience_years=exp,
                    department_id=doc_dept.department_id if doc_dept else None,
                    sub_department_id=sub_obj.sub_department_id if sub_obj else None,
                    created_at=datetime.utcnow()
                )
                db.add(doc)
                await db.flush()

                # User account
                res_u = await db.execute(select(User).where(User.username == code))
                if not res_u.scalars().first():
                    temporary_password = os.getenv("HMS_DEMO_DOCTOR_PASSWORD") or secrets.token_urlsafe(14)
                    pwd_hash = bcrypt.hashpw(temporary_password.encode(), bcrypt.gensalt()).decode()
                    user = User(
                        username=code,
                        email=email,
                        password_hash=pwd_hash,
                        status="active",
                        must_change_password=True
                    )
                    db.add(user)
                    await db.flush()
                    print(f"  Temporary credential for {code}: {temporary_password}")

                    res_r = await db.execute(select(Role).where(Role.role_name == "doctor"))
                    role = res_r.scalars().first()
                    if role:
                        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

            doc_objs.append(doc)

        await db.commit()

        print("3. Seeding Sample Patients...")
        sample_patients = [
            ("MRN-2024-00001", "PAT-2024-00001", "James", "Wilson", date(1982, 5, 14), "Male", "O+", "+1-555-0201", "james.wilson@example.com", "742 Evergreen Terrace", "Springfield"),
            ("MRN-2024-00002", "PAT-2024-00002", "Emily", "Clark", date(1991, 11, 23), "Female", "A+", "+1-555-0202", "emily.clark@example.com", "10880 Wilshire Blvd", "Los Angeles"),
            ("MRN-2024-00003", "PAT-2024-00003", "Robert", "Chen", date(1975, 3, 9), "Male", "B+", "+1-555-0203", "robert.chen@example.com", "450 Sutter St", "San Francisco"),
            ("MRN-2024-00004", "PAT-2024-00004", "Priya", "Patel", date(1998, 8, 17), "Female", "AB+", "+1-555-0204", "priya.patel@example.com", "230 Park Ave", "New York"),
            ("MRN-2024-00005", "PAT-2024-00005", "Michael", "Brown", date(1965, 12, 30), "Male", "O-", "+1-555-0205", "michael.brown@example.com", "1600 Amphitheatre Pkwy", "Mountain View"),
        ]

        patient_objs = []
        for mrn, pcode, fn, ln, dob, g_name, bg_name, phone, email, addr, city in sample_patients:
            res_p = await db.execute(select(Patient).where(Patient.mrn == mrn))
            p = res_p.scalars().first()
            if not p:
                p = Patient(
                    mrn=mrn,
                    patient_code=pcode,
                    first_name=fn,
                    last_name=ln,
                    date_of_birth=dob,
                    gender_id=g_map.get(g_name, 1),
                    blood_group_id=bg_map.get(bg_name, 1),
                    marital_status_id=ms_map.get("Married", 1),
                    status_id=ps_map.get("Active", 1),
                    created_at=datetime.utcnow()
                )
                db.add(p)
                await db.flush()

                db.add(PatientContact(patient_id=p.patient_id, contact_type="phone", contact_value=phone, is_primary=True))
                db.add(PatientContact(patient_id=p.patient_id, contact_type="email", contact_value=email, is_primary=False))
                db.add(PatientAddress(patient_id=p.patient_id, address_type="Home", line1=addr, city=city, state="CA", postal_code="94043"))
                db.add(PatientEmergencyContact(patient_id=p.patient_id, full_name=f"Mary {ln}", relationship="Spouse", phone=phone))

            patient_objs.append(p)

        await db.commit()

        print("4. Seeding Sample Inpatient Wards, Rooms, Beds & Admissions...")
        # Wards
        ward_data = [
            ("WARD-MED-A", "General Medical Ward A", "2nd Floor", "Main Hospital Tower"),
            ("WARD-CARD-B", "Cardiology Care Ward", "3rd Floor", "Heart & Vascular Pavilion"),
            ("WARD-ORTH-C", "Orthopedic Recovery Ward", "4th Floor", "Surgical Tower"),
        ]
        ward_objs = []
        for wcode, wname, floor, bldg in ward_data:
            res_w = await db.execute(select(Ward).where(Ward.ward_code == wcode))
            w = res_w.scalars().first()
            if not w:
                w = Ward(ward_code=wcode, ward_name=wname, floor_number=floor, building_name=bldg)
                db.add(w)
                await db.flush()
            ward_objs.append(w)

        # Rooms & Beds
        room_objs = []
        bed_objs = []
        for i, w in enumerate(ward_objs):
            for r_num in [f"{200 + i*10 + 1}", f"{200 + i*10 + 2}"]:
                res_r = await db.execute(select(Room).where(Room.room_number == f"Room {r_num}"))
                r = res_r.scalars().first()
                if not r:
                    r = Room(ward_id=w.ward_id, room_number=f"Room {r_num}", floor_number=w.floor_number)
                    db.add(r)
                    await db.flush()
                room_objs.append(r)

                for b_num in ["Bed A", "Bed B"]:
                    res_b = await db.execute(select(Bed).where(Bed.room_id == r.room_id, Bed.bed_number == b_num))
                    b = res_b.scalars().first()
                    if not b:
                        b = Bed(room_id=r.room_id, bed_number=b_num)
                        db.add(b)
                        await db.flush()
                    bed_objs.append(b)

        await db.commit()

        # Create 2 sample admissions for Inpatient Enquiry
        if len(patient_objs) >= 2 and len(bed_objs) >= 2 and len(doc_objs) >= 2:
            res_adm = await db.execute(select(Admission).where(Admission.admission_number == "ADM-2024-00001"))
            if not res_adm.scalars().first():
                adm1 = Admission(
                    admission_number="ADM-2024-00001",
                    patient_id=patient_objs[0].patient_id,
                    admitting_doctor_id=doc_objs[0].doctor_id,
                    ward_id=ward_objs[1].ward_id,
                    room_id=room_objs[1].room_id,
                    bed_id=bed_objs[2].bed_id,
                    admission_reason="Acute Chest Pain - Under Observation",
                    admission_date=datetime.utcnow() - timedelta(days=2)
                )
                db.add(adm1)

            res_adm2 = await db.execute(select(Admission).where(Admission.admission_number == "ADM-2024-00002"))
            if not res_adm2.scalars().first():
                adm2 = Admission(
                    admission_number="ADM-2024-00002",
                    patient_id=patient_objs[1].patient_id,
                    admitting_doctor_id=doc_objs[1].doctor_id,
                    ward_id=ward_objs[2].ward_id,
                    room_id=room_objs[2].room_id,
                    bed_id=bed_objs[4].bed_id,
                    admission_reason="Post-Op Knee Arthroscopy Recovery",
                    admission_date=datetime.utcnow() - timedelta(days=1)
                )
                db.add(adm2)

        # 5. Create 2 Sample Today Appointments & Tokens
        today = date.today()
        res_apt = await db.execute(select(Appointment).where(Appointment.appointment_number == "APT-2024-00001"))
        if not res_apt.scalars().first() and len(patient_objs) >= 3 and len(doc_objs) >= 2:
            apt1 = Appointment(
                appointment_number="APT-2024-00001",
                patient_id=patient_objs[2].patient_id,
                doctor_id=doc_objs[0].doctor_id,
                department_id=doc_objs[0].department_id,
                appointment_type_id=apt_tp_map.get("Walk-in"),
                appointment_status_id=apt_st_map.get("Checked-In"),
                appointment_date=today,
                start_time=time(10, 30),
                end_time=time(10, 45),
                chief_complaint="Routine Cardiovascular Follow-Up",
                checked_in_at=datetime.utcnow() - timedelta(minutes=15)
            )
            db.add(apt1)
            await db.flush()

            db.add(QueueToken(
                service_point_id=sp.service_point_id,
                token_number="T-01",
                patient_id=patient_objs[2].patient_id,
                appointment_id=apt1.appointment_id,
                token_type="walk_in",
                status="waiting",
                issued_at=datetime.utcnow() - timedelta(minutes=15)
            ))

            apt2 = Appointment(
                appointment_number="APT-2024-00002",
                patient_id=patient_objs[3].patient_id,
                doctor_id=doc_objs[2].doctor_id,
                department_id=doc_objs[2].department_id,
                appointment_type_id=apt_tp_map.get("Walk-in"),
                appointment_status_id=apt_st_map.get("Checked-In"),
                appointment_date=today,
                start_time=time(11, 0),
                end_time=time(11, 15),
                chief_complaint="High Grade Fever & Cough",
                checked_in_at=datetime.utcnow() - timedelta(minutes=5)
            )
            db.add(apt2)
            await db.flush()

            db.add(QueueToken(
                service_point_id=sp.service_point_id,
                token_number="T-02",
                patient_id=patient_objs[3].patient_id,
                appointment_id=apt2.appointment_id,
                token_type="walk_in",
                status="waiting",
                issued_at=datetime.utcnow() - timedelta(minutes=5)
            ))

        await db.commit()
        print("=== Seed Demo Data Complete ===")
        print("  Doctors seeded: 5 (Cardiology, Orthopedics, Pediatrics, GP, Neurology)")
        print("  Patients seeded: 5 with MRN & contact details")
        print("  Inpatients seeded: 2 admitted in Wards A & B")
        print("  Appointments & Active Tokens: 2 in queue")

asyncio.run(seed_demo())
