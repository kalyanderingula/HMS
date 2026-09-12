import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, BigInteger, select, func, text, desc
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as PyUUID
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import os

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser, IdentityLink, link_identity
from app.models.employee import Base

router = APIRouter(prefix="/doctor", tags=["Doctor Portal"], dependencies=[Depends(require_roles(["doctor", "telemedicine_doctor"]))])

UPLOAD_DIR = "uploads/doctor_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- Models ---

class DoctorStatus(Base):
    __tablename__ = "doctor_statuses"
    __table_args__ = {"schema": "doctor"}
    status_id = Column(BigInteger, primary_key=True)
    status_name = Column(String(50), unique=True)


class Specialization(Base):
    __tablename__ = "specializations"
    __table_args__ = {"schema": "doctor"}
    specialization_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialization_name = Column(String(255), unique=True)
    specialization_code = Column(String(100))
    description = Column(Text)
    sub_department_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime)


class Doctor(Base):
    __tablename__ = "doctors"
    __table_args__ = {"schema": "doctor"}
    doctor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True))
    doctor_code = Column(String(50), unique=True)
    employee_id = Column(UUID(as_uuid=True))
    first_name = Column(String(100))
    middle_name = Column(String(100))
    last_name = Column(String(100))
    gender_id = Column(BigInteger)
    email = Column(String(255))
    phone = Column(String(20))
    primary_specialization_id = Column(UUID(as_uuid=True))
    status_id = Column(BigInteger)
    joining_date = Column(Date)
    consultation_experience_years = Column(Integer)
    department_id = Column(UUID(as_uuid=True))
    sub_department_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))
    deleted_at = Column(DateTime)


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    __table_args__ = {"schema": "doctor"}
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    biography = Column(Text)
    nationality = Column(String(100))
    religion = Column(String(100))
    profile_photo = Column(Text)
    linkedin_url = Column(Text)
    website_url = Column(Text)


class DoctorQualification(Base):
    __tablename__ = "doctor_qualifications"
    __table_args__ = {"schema": "doctor"}
    qualification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    qualification_name = Column(String(255))
    institution_name = Column(String(255))
    university_name = Column(String(255))
    country = Column(String(100))
    graduation_year = Column(Integer)
    certificate_number = Column(String(255))


class DoctorLicense(Base):
    __tablename__ = "doctor_licenses"
    __table_args__ = {"schema": "doctor"}
    license_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    license_number = Column(String(255), unique=True)
    issuing_authority = Column(String(255))
    issue_date = Column(Date)
    expiry_date = Column(Date)
    status = Column(String(50))
    document_path = Column(Text)


class DoctorExperience(Base):
    __tablename__ = "doctor_experiences"
    __table_args__ = {"schema": "doctor"}
    experience_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    hospital_name = Column(String(255))
    designation = Column(String(255))
    department = Column(String(255))
    start_date = Column(Date)
    end_date = Column(Date)
    responsibilities = Column(Text)


class DoctorLanguage(Base):
    __tablename__ = "doctor_languages"
    __table_args__ = {"schema": "doctor"}
    doctor_language_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    language_id = Column(UUID(as_uuid=True))
    proficiency_level = Column(String(50))


class Language(Base):
    __tablename__ = "languages"
    __table_args__ = {"schema": "doctor"}
    language_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    language_name = Column(String(100), unique=True)


class DocumentType(Base):
    __tablename__ = "master_document_types"
    __table_args__ = {"schema": "core"}
    document_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type_name = Column("type_name", String(255), unique=True)


class DoctorDocument(Base):
    __tablename__ = "doctor_documents"
    __table_args__ = {"schema": "doctor"}
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    document_type_id = Column(UUID(as_uuid=True))
    file_name = Column(String(255))
    file_path = Column(Text)
    mime_type = Column(String(100))
    file_size = Column(BigInteger)
    uploaded_by = Column(UUID(as_uuid=True))


class DoctorSpecialization(Base):
    __tablename__ = "doctor_specializations"
    __table_args__ = {"schema": "doctor"}
    doctor_specialization_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    specialization_id = Column(UUID(as_uuid=True))
    years_of_experience = Column(Integer)


class DoctorConsultationFee(Base):
    __tablename__ = "doctor_consultation_fees"
    __table_args__ = {"schema": "doctor"}
    fee_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    consultation_type = Column(String(100))
    fee_amount = Column(Numeric(12, 2))
    currency = Column(String(10))
    effective_from = Column(Date)
    effective_to = Column(Date)


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"
    __table_args__ = {"schema": "doctor"}
    availability_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True))
    available_day = Column(String(20))
    start_time = Column(String)
    end_time = Column(String)
    consultation_type = Column(String(100))
    max_patients_per_slot = Column(Integer)


# --- Schemas ---

class ProfileUpdate(BaseModel):
    biography: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None


class QualificationCreate(BaseModel):
    qualification_name: str
    institution_name: Optional[str] = None
    university_name: Optional[str] = None
    country: Optional[str] = None
    graduation_year: Optional[int] = None
    certificate_number: Optional[str] = None


class LicenseCreate(BaseModel):
    license_number: str
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = "active"


class ExperienceCreate(BaseModel):
    hospital_name: str
    designation: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    responsibilities: Optional[str] = None


class AvailabilityCreate(BaseModel):
    available_day: str
    start_time: str
    end_time: str
    consultation_type: Optional[str] = "in_person"
    max_patients_per_slot: Optional[int] = 10


class ConsultationFeeCreate(BaseModel):
    consultation_type: str
    fee_amount: float
    currency: Optional[str] = "INR"
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class FollowUpRequest(BaseModel):
    patient_id: PyUUID
    doctor_id: Optional[PyUUID] = None
    follow_up_date: date
    time_slot: Optional[str] = "10:00"
    reason: Optional[str] = "Routine follow-up"
    clinical_notes: Optional[str] = None


class AcknowledgeReportRequest(BaseModel):
    notes: Optional[str] = None


class DoctorSelfProfileUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    consultation_experience_years: Optional[int] = None
    biography: Optional[str] = None
    nationality: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    consultation_fee: Optional[float] = None


# --- Helper: Get doctor by employee_id (auto-create if not exists) ---

async def get_doctor_by_employee(db: AsyncSession, employee_id: PyUUID):
    result = await db.execute(select(Doctor).where(Doctor.employee_id == employee_id))
    doctor = result.scalars().first()
    if doctor:
        return doctor

    # Auto-create doctor record from employee data
    from app.models.employee import Employee
    emp = await db.get(Employee, employee_id)
    if not emp:
        return None

    # Get active status
    result = await db.execute(select(DoctorStatus).where(func.lower(DoctorStatus.status_name) == 'active'))
    status = result.scalars().first()
    if not status:
        return None

    doctor = Doctor(
        doctor_code=emp.employee_number,
        employee_id=employee_id,
        first_name=emp.first_name,
        middle_name=emp.middle_name,
        last_name=emp.last_name or "_",
        email=emp.official_email,
        phone=emp.official_phone,
        status_id=status.status_id,
        joining_date=emp.date_of_joining,
    )
    db.add(doctor)
    await db.flush()
    return doctor


async def get_current_doctor(db: AsyncSession, cu: CurrentUser, create_if_missing: bool = True):
    """Resolve employee-linked and standalone doctor login accounts."""
    identity = (await db.execute(select(IdentityLink).where(
        IdentityLink.user_id == cu.user_id,
        IdentityLink.identity_type == "doctor",
    ))).scalars().first()
    doctor = await db.get(Doctor, identity.identity_id) if identity else None
    if cu.employee_id:
        doctor = (await db.execute(
            select(Doctor).where(Doctor.employee_id == cu.employee_id)
        )).scalars().first()
        if not doctor:
            doctor = await get_doctor_by_employee(db, cu.employee_id)

    if not doctor:
        login = cu.username.strip()
        doctor = (await db.execute(
            select(Doctor).where(
                (func.lower(Doctor.doctor_code) == login.lower())
                | (func.lower(Doctor.email) == login.lower())
            )
        )).scalars().first()

    if not doctor and create_if_missing and "doctor" in cu.roles:
        status = (await db.execute(
            select(DoctorStatus).where(func.lower(DoctorStatus.status_name) == "active")
        )).scalars().first()
        if not status:
            status = DoctorStatus(status_name="Active")
            db.add(status)
            await db.flush()
        display_name = (cu.name or cu.username).strip()
        name_parts = display_name.split(maxsplit=1)
        doctor = Doctor(
            doctor_code=cu.username.strip(),
            employee_id=cu.employee_id,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else "",
            status_id=status.status_id,
            created_at=datetime.utcnow(),
        )
        db.add(doctor)
        await db.flush()

    if doctor and (not identity or identity.identity_id != doctor.doctor_id):
        await link_identity(db, cu.user_id, "doctor", doctor.doctor_id)

    return doctor


# --- Endpoints ---

# Get my profile (by employee_id from token)
@router.get("/my-profile/{employee_id}")
async def get_my_profile(employee_id: str, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(get_current_user)):
    if employee_id in ("current", "null", "None"):
        doctor = await get_current_doctor(db, cu)
        employee_id = doctor.employee_id if doctor else None
    else:
        employee_id = PyUUID(employee_id)
        if "doctor" in cu.roles and cu.employee_id and cu.employee_id != employee_id:
            raise HTTPException(403, "You can only view your own doctor profile")
        doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Employee not found or cannot create doctor record")

    await db.commit()  # commit auto-creation if it happened

    # Get profile
    result = await db.execute(select(DoctorProfile).where(DoctorProfile.doctor_id == doctor.doctor_id))
    profile = result.scalars().first()

    # Get specializations
    result = await db.execute(select(DoctorSpecialization).where(DoctorSpecialization.doctor_id == doctor.doctor_id))
    specs = result.scalars().all()
    spec_details = []
    for s in specs:
        sp = await db.get(Specialization, s.specialization_id)
        spec_details.append({"specialization_name": sp.specialization_name if sp else None, "years_of_experience": s.years_of_experience})

    # Get qualifications
    result = await db.execute(select(DoctorQualification).where(DoctorQualification.doctor_id == doctor.doctor_id))
    qualifications = result.scalars().all()

    # Get licenses
    result = await db.execute(select(DoctorLicense).where(DoctorLicense.doctor_id == doctor.doctor_id))
    licenses = result.scalars().all()

    # Get experiences
    result = await db.execute(select(DoctorExperience).where(DoctorExperience.doctor_id == doctor.doctor_id))
    experiences = result.scalars().all()

    # Get languages
    result = await db.execute(select(DoctorLanguage).where(DoctorLanguage.doctor_id == doctor.doctor_id))
    doc_langs = result.scalars().all()
    lang_details = []
    for dl in doc_langs:
        lang = await db.get(Language, dl.language_id)
        lang_details.append({"language_name": lang.language_name if lang else None, "proficiency_level": dl.proficiency_level})

    # Get availability
    result = await db.execute(select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor.doctor_id))
    availability = result.scalars().all()

    # Get consultation fees
    result = await db.execute(select(DoctorConsultationFee).where(DoctorConsultationFee.doctor_id == doctor.doctor_id))
    fees = result.scalars().all()

    # Get primary specialization name
    primary_spec_name = None
    if doctor.primary_specialization_id:
        sp = await db.get(Specialization, doctor.primary_specialization_id)
        primary_spec_name = sp.specialization_name if sp else None

    # Get fresh employee data for basic info
    from app.models.employee import Employee
    emp = await db.get(Employee, employee_id) if employee_id else None

    # Get employee details for personal info section
    from app.api.employees import get_employee_details
    emp_details_raw = await get_employee_details(db, employee_id) if employee_id else None
    emp_details = {}
    if emp_details_raw:
        raw = emp_details_raw.model_dump()
        for k, v in raw.items():
            if isinstance(v, PyUUID):
                raw[k] = str(v)
        emp_details = raw

    # Get documents
    result = await db.execute(select(DoctorDocument).where(DoctorDocument.doctor_id == doctor.doctor_id))
    docs = result.scalars().all()
    doc_list = []
    for dd in docs:
        dt = await db.get(DocumentType, dd.document_type_id) if dd.document_type_id else None
        doc_list.append({"document_id": str(dd.document_id), "document_type": dt.document_type_name if dt else None, "file_name": dd.file_name, "file_size": dd.file_size, "mime_type": dd.mime_type})

    return {
        "doctor_record_exists": True,
        "doctor": {
            "doctor_id": str(doctor.doctor_id),
            "doctor_code": doctor.doctor_code,
            "first_name": emp.first_name if emp else doctor.first_name,
            "middle_name": emp.middle_name if emp else doctor.middle_name,
            "last_name": emp.last_name if emp else doctor.last_name,
            "email": emp.official_email if emp else doctor.email,
            "phone": emp.official_phone if emp else doctor.phone,
            "joining_date": str(emp.date_of_joining) if emp and emp.date_of_joining else (str(doctor.joining_date) if doctor.joining_date else None),
            "consultation_experience_years": doctor.consultation_experience_years,
            "primary_specialization": primary_spec_name,
        },
        "profile": {
            "biography": profile.biography if profile else None,
            "nationality": profile.nationality if profile else None,
            "religion": profile.religion if profile else None,
            "linkedin_url": profile.linkedin_url if profile else None,
            "website_url": profile.website_url if profile else None,
        },
        "employee_details": emp_details,
        "specializations": spec_details,
        "qualifications": [{"qualification_id": str(q.qualification_id), "qualification_name": q.qualification_name, "institution_name": q.institution_name, "university_name": q.university_name, "country": q.country, "graduation_year": q.graduation_year, "certificate_number": q.certificate_number} for q in qualifications],
        "licenses": [{"license_id": str(l.license_id), "license_number": l.license_number, "issuing_authority": l.issuing_authority, "issue_date": str(l.issue_date) if l.issue_date else None, "expiry_date": str(l.expiry_date) if l.expiry_date else None, "status": l.status} for l in licenses],
        "experiences": [{"experience_id": str(e.experience_id), "hospital_name": e.hospital_name, "designation": e.designation, "department": e.department, "start_date": str(e.start_date) if e.start_date else None, "end_date": str(e.end_date) if e.end_date else None, "responsibilities": e.responsibilities} for e in experiences],
        "languages": lang_details,
        "documents": doc_list,
        "availability": [{"availability_id": str(a.availability_id), "available_day": a.available_day, "start_time": a.start_time, "end_time": a.end_time, "consultation_type": a.consultation_type, "max_patients_per_slot": a.max_patients_per_slot} for a in availability],
        "consultation_fees": [{"fee_id": str(f.fee_id), "consultation_type": f.consultation_type, "fee_amount": float(f.fee_amount) if f.fee_amount else None, "currency": f.currency, "effective_from": str(f.effective_from) if f.effective_from else None, "effective_to": str(f.effective_to) if f.effective_to else None} for f in fees],
    }


# Self profile edit by authenticated doctor
@router.put("/my-profile")
async def update_my_doctor_profile(
    data: DoctorSelfProfileUpdate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Allows authenticated doctor to update contact info, bio, consultation fee, and links."""
    doctor = await get_current_doctor(db, cu)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found for authenticated user")

    from app.models.employee import Employee
    emp = await db.get(Employee, doctor.employee_id) if doctor.employee_id else None

    # Update doctor table
    if data.phone is not None:
        doctor.phone = data.phone
        if emp: emp.official_phone = data.phone
    if data.email is not None:
        doctor.email = data.email
        if emp: emp.official_email = data.email
    if data.consultation_experience_years is not None:
        doctor.consultation_experience_years = data.consultation_experience_years
    doctor.updated_at = datetime.utcnow()

    # Update profile table (bio, links)
    prof_res = await db.execute(select(DoctorProfile).where(DoctorProfile.doctor_id == doctor.doctor_id))
    profile = prof_res.scalars().first()
    if not profile:
        profile = DoctorProfile(doctor_id=doctor.doctor_id)
        db.add(profile)
    if data.biography is not None: profile.biography = data.biography
    if data.nationality is not None: profile.nationality = data.nationality
    if data.linkedin_url is not None: profile.linkedin_url = data.linkedin_url
    if data.website_url is not None: profile.website_url = data.website_url

    # Update consultation fee
    if data.consultation_fee is not None:
        fee_res = await db.execute(select(DoctorConsultationFee).where(DoctorConsultationFee.doctor_id == doctor.doctor_id, DoctorConsultationFee.consultation_type == "OPD"))
        fee_obj = fee_res.scalars().first()
        if not fee_obj:
            fee_obj = DoctorConsultationFee(
                doctor_id=doctor.doctor_id,
                consultation_type="OPD",
                fee_amount=data.consultation_fee,
                currency="INR",
                effective_from=date.today()
            )
            db.add(fee_obj)
        else:
            fee_obj.fee_amount = data.consultation_fee

    await db.commit()
    return {
        "message": "Doctor profile updated successfully",
        "updated_fields": data.model_dump(),
    }


# Update profile
@router.put("/profile/{employee_id}")
async def update_profile(employee_id: PyUUID, data: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")

    result = await db.execute(select(DoctorProfile).where(DoctorProfile.doctor_id == doctor.doctor_id))
    profile = result.scalars().first()

    if profile:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(profile, k, v)
    else:
        profile = DoctorProfile(doctor_id=doctor.doctor_id, **data.model_dump())
        db.add(profile)

    await db.commit()
    return {"message": "Profile updated"}


# Add qualification
@router.post("/qualifications/{employee_id}")
async def add_qualification(employee_id: PyUUID, data: QualificationCreate, db: AsyncSession = Depends(get_db)):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")
    q = DoctorQualification(doctor_id=doctor.doctor_id, **data.model_dump())
    db.add(q)
    await db.commit()
    return {"message": "Qualification added", "qualification_id": str(q.qualification_id)}


# Delete qualification
@router.delete("/qualifications/{qualification_id}")
async def delete_qualification(qualification_id: PyUUID, db: AsyncSession = Depends(get_db)):
    q = await db.get(DoctorQualification, qualification_id)
    if not q:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(q)
    await db.commit()
    return {"message": "Deleted"}


# Add license
@router.post("/licenses/{employee_id}")
async def add_license(employee_id: PyUUID, data: LicenseCreate, db: AsyncSession = Depends(get_db)):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")
    l = DoctorLicense(doctor_id=doctor.doctor_id, **data.model_dump())
    db.add(l)
    await db.commit()
    return {"message": "License added", "license_id": str(l.license_id)}


# Delete license
@router.delete("/licenses/{license_id}")
async def delete_license(license_id: PyUUID, db: AsyncSession = Depends(get_db)):
    l = await db.get(DoctorLicense, license_id)
    if not l:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(l)
    await db.commit()
    return {"message": "Deleted"}


# Add experience
@router.post("/experiences/{employee_id}")
async def add_experience(employee_id: PyUUID, data: ExperienceCreate, db: AsyncSession = Depends(get_db)):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")
    e = DoctorExperience(doctor_id=doctor.doctor_id, **data.model_dump())
    db.add(e)
    await db.commit()
    return {"message": "Experience added", "experience_id": str(e.experience_id)}


# Delete experience
@router.delete("/experiences/{experience_id}")
async def delete_experience(experience_id: PyUUID, db: AsyncSession = Depends(get_db)):
    e = await db.get(DoctorExperience, experience_id)
    if not e:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(e)
    await db.commit()
    return {"message": "Deleted"}


# Add availability
@router.post("/availability/{employee_id}")
async def add_availability(employee_id: PyUUID, data: AvailabilityCreate, db: AsyncSession = Depends(get_db)):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")
    a = DoctorAvailability(doctor_id=doctor.doctor_id, **data.model_dump())
    db.add(a)
    await db.commit()
    return {"message": "Availability added"}


# Delete availability
@router.delete("/availability/{availability_id}")
async def delete_availability(availability_id: PyUUID, db: AsyncSession = Depends(get_db)):
    a = await db.get(DoctorAvailability, availability_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(a)
    await db.commit()
    return {"message": "Deleted"}


# Add consultation fee
@router.post("/consultation-fees/{employee_id}")
async def add_consultation_fee(employee_id: PyUUID, data: ConsultationFeeCreate, db: AsyncSession = Depends(get_db)):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")
    f = DoctorConsultationFee(doctor_id=doctor.doctor_id, **data.model_dump())
    db.add(f)
    await db.commit()
    return {"message": "Fee added"}


# Delete consultation fee
@router.delete("/consultation-fees/{fee_id}")
async def delete_consultation_fee(fee_id: PyUUID, db: AsyncSession = Depends(get_db)):
    f = await db.get(DoctorConsultationFee, fee_id)
    if not f:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(f)
    await db.commit()
    return {"message": "Deleted"}


# Upload document
@router.post("/documents/{employee_id}")
async def upload_document(
    employee_id: PyUUID,
    document_type_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")

    file_path = os.path.join(UPLOAD_DIR, f"{doctor.doctor_id}_{file.filename}")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = DoctorDocument(
        doctor_id=doctor.doctor_id,
        document_type_id=document_type_id,
        file_name=file.filename,
        file_path=file_path,
        mime_type=file.content_type,
        file_size=len(content),
    )
    db.add(doc)
    await db.commit()
    return {"message": "Document uploaded", "document_id": str(doc.document_id)}


# Get documents
@router.get("/documents/{employee_id}")
async def get_documents(employee_id: PyUUID, db: AsyncSession = Depends(get_db)):
    doctor = await get_doctor_by_employee(db, employee_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found")

    result = await db.execute(select(DoctorDocument).where(DoctorDocument.doctor_id == doctor.doctor_id))
    docs = result.scalars().all()
    doc_list = []
    for d in docs:
        dt = await db.get(DocumentType, d.document_type_id) if d.document_type_id else None
        doc_list.append({
            "document_id": str(d.document_id),
            "document_type": dt.document_type_name if dt else None,
            "file_name": d.file_name,
            "file_size": d.file_size,
            "mime_type": d.mime_type,
        })
    return doc_list


# Delete document
@router.delete("/documents/{document_id}")
async def delete_document(document_id: PyUUID, db: AsyncSession = Depends(get_db)):
    doc = await db.get(DoctorDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted"}


# --- Master Data Endpoints ---

@router.get("/specializations")
async def list_specializations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Specialization).order_by(Specialization.specialization_name))
    return [{"specialization_id": str(s.specialization_id), "specialization_name": s.specialization_name, "specialization_code": s.specialization_code} for s in result.scalars().all()]


@router.get("/languages")
async def list_languages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Language).order_by(Language.language_name))
    return [{"language_id": str(l.language_id), "language_name": l.language_name} for l in result.scalars().all()]


@router.get("/document-types")
async def list_document_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentType).order_by(DocumentType.document_type_name))
    return [{"document_type_id": str(d.document_type_id), "document_type_name": d.document_type_name} for d in result.scalars().all()]


# --- Patient Comprehensive Clinical History ---

@router.get("/patients/{patient_id}/clinical-history")
async def get_patient_clinical_history(
    patient_id: PyUUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Retrieve complete clinical history of the patient: past doctor consultations, previous doctors, SOAP notes, diagnoses, medications, lab results, radiology, vitals."""
    from app.models.patient import Patient, Gender, BloodGroup
    from app.models.emr_models import PatientEncounter, EncounterType, ClinicalNote, Diagnosis, MedicationRecord, VitalSign, AllergyRecord, SeverityLevel

    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")

    gender_name = (await db.get(Gender, patient.gender_id)).gender_name if patient.gender_id else "Unknown"
    blood_group_name = (await db.get(BloodGroup, patient.blood_group_id)).blood_group_name if patient.blood_group_id else "Unknown"
















    # 1. Past Consultations with Doctor details, SOAP notes, Diagnoses, Medications
    encounters_res = await db.execute(
        select(PatientEncounter)
        .where(PatientEncounter.patient_id == patient_id)
        .order_by(desc(PatientEncounter.encounter_date))
    )
    encounters = encounters_res.scalars().all()

    consultations_history = []
    for enc in encounters:
        encounter_type = await db.get(EncounterType, enc.encounter_type_id) if enc.encounter_type_id else None
        attending_doc = await db.get(Doctor, enc.doctor_id) if enc.doctor_id else None
        doc_name = f"Dr. {attending_doc.first_name} {attending_doc.last_name}" if attending_doc else "Unknown Doctor"
        doc_code = attending_doc.doctor_code if attending_doc else "-"

        spec_name = None
        if attending_doc and attending_doc.primary_specialization_id:
            sp = await db.get(Specialization, attending_doc.primary_specialization_id)
            spec_name = sp.specialization_name if sp else None

        notes_res = await db.execute(
            select(ClinicalNote).where(ClinicalNote.encounter_id == enc.encounter_id)
        )
        notes = notes_res.scalars().all()
        soap = None
        for n in notes:
            if n.note_type == "SOAP":
                try:
                    parsed = json.loads(n.note_text)
                except (json.JSONDecodeError, TypeError):
                    parsed = {"Subjective": n.note_text}
                soap = {
                    "subjective": parsed.get("Subjective", ""),
                    "objective": parsed.get("Objective", ""),
                    "assessment": parsed.get("Assessment", ""),
                    "plan": parsed.get("Plan", ""),
                }

        diag_res = await db.execute(
            select(Diagnosis).where(Diagnosis.encounter_id == enc.encounter_id)
        )
        diagnoses = [{"code": d.diagnosis_code, "name": d.diagnosis_name, "details": d.diagnosis_description} for d in diag_res.scalars().all()]

        meds_res = await db.execute(
            select(MedicationRecord).where(MedicationRecord.encounter_id == enc.encounter_id)
        )
        meds = [{
            "medicine_name": m.medicine_name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "duration": m.duration,
            "instructions": m.instructions
        } for m in meds_res.scalars().all()]

        consultations_history.append({
            "encounter_id": str(enc.encounter_id),
            "encounter_number": enc.encounter_number,
            "encounter_datetime": enc.encounter_date.isoformat() if enc.encounter_date else None,
            "encounter_type": encounter_type.type_name if encounter_type else "OPD",
            "status": enc.encounter_status,
            "doctor_name": doc_name,
            "doctor_code": doc_code,
            "specialization": spec_name or "General Medicine",
            "chief_complaint": enc.chief_complaint,
            "clinical_summary": enc.clinical_summary,
            "soap_note": soap,
            "diagnoses": diagnoses,
            "prescriptions": meds
        })























































    # 2. Laboratory Results History
    lab_sql = """
        SELECT re.result_entry_id, lt.test_name, lo.order_number, re.approved_at, re.remarks,
               re.result_status,
               COALESCE(bool_or(rp.result_flag IN ('Critical', 'High', 'Low')), false) AS has_abnormal,
               COALESCE(bool_or(rp.result_flag = 'Critical'), false) AS has_critical,
               COALESCE(json_agg(json_build_object(
                   'parameter_name', tp.parameter_name,
                   'value', rp.result_value,
                   'unit', tp.unit,
                   'normal_range', tp.normal_range,
                   'flag', rp.result_flag
               )) FILTER (WHERE rp.result_parameter_id IS NOT NULL), '[]'::json) AS parameters
        FROM laboratory.lab_result_entries re
        JOIN laboratory.lab_order_items oi USING(order_item_id)
        JOIN laboratory.lab_orders lo USING(lab_order_id)
        JOIN laboratory.lab_tests lt USING(test_id)
        LEFT JOIN laboratory.lab_result_parameters rp USING(result_entry_id)
        LEFT JOIN laboratory.lab_test_parameters tp USING(parameter_id)
        WHERE lo.patient_id = :patient_id
        GROUP BY re.result_entry_id, lt.test_name, lo.order_number, re.approved_at, re.remarks, re.result_status
        ORDER BY re.approved_at DESC NULLS LAST
        LIMIT 30
    """
    lab_rows = (await db.execute(text(lab_sql), {"patient_id": patient_id})).mappings().all()



    # 3. Radiology Reports History
    rad_sql = """
        SELECT rr.report_id, s.study_id, ro.order_number, rt.test_name,
               s.study_description, rr.report_text AS findings, rr.impression,
               rr.is_critical, rr.critical_alert_details, rr.reported_at, rr.report_status
        FROM radiology.radiology_reports rr
        JOIN radiology.imaging_studies s USING(study_id)
        LEFT JOIN radiology.radiology_appointments a USING(radiology_appointment_id)
        LEFT JOIN radiology.radiology_order_items oi ON oi.order_item_id = a.order_item_id
        LEFT JOIN radiology.radiology_orders ro USING(radiology_order_id)
        LEFT JOIN radiology.radiology_tests rt USING(radiology_test_id)
        WHERE s.patient_id = :patient_id
        ORDER BY rr.reported_at DESC
        LIMIT 20
    """
    rad_rows = (await db.execute(text(rad_sql), {"patient_id": patient_id})).mappings().all()

    # 4. Vitals Timeline
    vitals_res = await db.execute(
        select(VitalSign).where(VitalSign.patient_id == patient_id).order_by(desc(VitalSign.recorded_at)).limit(20)
    )
    vitals_list = [{
        "recorded_at": v.recorded_at.strftime("%Y-%m-%d %H:%M") if v.recorded_at else None,
        "temperature": float(v.temperature) if v.temperature else None,
        "bp": f"{v.systolic_bp}/{v.diastolic_bp}" if v.systolic_bp and v.diastolic_bp else "-",
        "heart_rate": v.heart_rate,
        "respiratory_rate": v.respiratory_rate,
        "spo2": float(v.oxygen_saturation) if v.oxygen_saturation else None,
        "bmi": float(v.bmi) if v.bmi else None,
        "pain_score": v.pain_score
    } for v in vitals_res.scalars().all()]









    # 5. Allergies
    allergies_res = await db.execute(select(AllergyRecord).where(AllergyRecord.patient_id == patient_id))
    allergies = []
    for allergy in allergies_res.scalars().all():
        severity = await db.get(SeverityLevel, allergy.severity_level_id) if allergy.severity_level_id else None
        allergies.append({
            "allergen": allergy.allergen_name,
            "type": allergy.allergy_type,
            "reaction": allergy.reaction_description,
            "severity": severity.severity_name if severity else "Moderate",
        })

    return {
        "patient": {
            "patient_id": str(patient.patient_id),
            "full_name": f"{patient.first_name} {patient.last_name or ''}".strip(),
            "mrn": patient.mrn,
            "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
            "gender": gender_name,
            "blood_group": blood_group_name,
            "allergies": allergies,
            "active_diagnoses": []
        },
        "consultations": consultations_history,
        "laboratory_results": [
            {
                "result_entry_id": str(r["result_entry_id"]),
                "test_name": r["test_name"],

                "order_number": r["order_number"],
                "result_status": r["result_status"],

                "approved_at": r["approved_at"].strftime("%Y-%m-%d %H:%M") if r["approved_at"] else None,
                "has_abnormal": r["has_abnormal"],
                "has_critical": r["has_critical"],
                "parameters": [{
                    "parameter_name": p.get("parameter_name"),
                    "result_value": p.get("value"),
                    "unit": p.get("unit"),
                    "normal_range": p.get("normal_range"),
                    "result_flag": p.get("flag"),
                } for p in r["parameters"]]
            } for r in lab_rows
        ],
        "radiology_reports": [
            {
                "report_id": str(r["report_id"]),
                "study_id": str(r["study_id"]),
                "order_number": r["order_number"] or "RAD",
                "test_name": r["test_name"] or r["study_description"] or "Radiology Exam",

                "impression": r["impression"],
                "findings": r["findings"],
                "is_critical": r["is_critical"] or False,
                "reported_at": r["reported_at"].strftime("%Y-%m-%d %H:%M") if r["reported_at"] else None


            } for r in rad_rows
        ],
        "vitals_timeline": vitals_list,
        "allergies": allergies
    }


# --- Clinical Diagnostic Reports Review & Acknowledgements ---

@router.get("/reports")
@router.get("/reports/pending")
async def get_diagnostic_reports(
    scope: str = "pending",
    q: Optional[str] = None,
    patient_id: Optional[PyUUID] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Retrieve diagnostic reports with scoping: pending acknowledgement, ordered by this doctor, or all with search."""
    doctor_query = select(Doctor).where(Doctor.employee_id == cu.employee_id) if cu.employee_id else select(Doctor).where(Doctor.doctor_code == cu.username)
    current_doc = (await db.execute(doctor_query)).scalars().first()
    curr_doc_id = current_doc.doctor_id if current_doc else None

    # Base lab query conditions
    lab_conds = ["1=1"]
    params = {"patient_id": patient_id, "doc_id": curr_doc_id, "search": f"%{q}%" if q else None}

    if scope == "pending":
        lab_conds.append("re.result_status = 'Approved'")
        lab_conds.append("re.acknowledged_at IS NULL")
    elif scope == "ordered_by_me":
        if curr_doc_id:
            lab_conds.append("lo.doctor_id = :doc_id")
        else:
            lab_conds.append("1=0")
    elif scope == "all":
        lab_conds.append("re.result_status IN ('Approved', 'Completed')")

    if patient_id:
        lab_conds.append("lo.patient_id = :patient_id")
    if q:
        lab_conds.append("(p.first_name ILIKE :search OR p.last_name ILIKE :search OR p.mrn ILIKE :search OR lt.test_name ILIKE :search)")

    lab_sql = f"""
        SELECT re.result_entry_id, lt.test_name, lo.order_number, lo.patient_id,
               p.first_name, p.last_name, p.mrn, re.entered_at, re.approved_at, re.remarks,
               re.acknowledged_at, re.result_status,
               d.first_name AS doc_first_name, d.last_name AS doc_last_name,
               COALESCE(bool_or(rp.result_flag IN ('Critical', 'High', 'Low')), false) AS has_abnormal,
               COALESCE(bool_or(rp.result_flag = 'Critical'), false) AS has_critical,
               COALESCE(json_agg(json_build_object(
                   'parameter_name', tp.parameter_name,
                   'value', rp.result_value,
                   'unit', tp.unit,
                   'normal_range', tp.normal_range,
                   'flag', rp.result_flag
               )) FILTER (WHERE rp.result_parameter_id IS NOT NULL), '[]'::json) AS parameters
        FROM laboratory.lab_result_entries re
        JOIN laboratory.lab_order_items oi USING(order_item_id)
        JOIN laboratory.lab_orders lo USING(lab_order_id)
        JOIN laboratory.lab_tests lt USING(test_id)
        JOIN patient.patients p ON p.patient_id = lo.patient_id
        LEFT JOIN doctor.doctors d ON d.doctor_id = lo.doctor_id
        LEFT JOIN laboratory.lab_result_parameters rp USING(result_entry_id)
        LEFT JOIN laboratory.lab_test_parameters tp USING(parameter_id)
        WHERE {' AND '.join(lab_conds)}
        GROUP BY re.result_entry_id, lt.test_name, lo.order_number, lo.patient_id, p.first_name, p.last_name, p.mrn, re.entered_at, re.approved_at, re.remarks, re.acknowledged_at, re.result_status, d.first_name, d.last_name
        ORDER BY re.approved_at DESC NULLS LAST
        LIMIT 50
    """
    lab_rows = (await db.execute(text(lab_sql), params)).mappings().all()

    # Radiology conditions
    rad_conds = ["1=1"]
    if scope == "pending":
        rad_conds.append("rr.report_status = 'Final'")
        rad_conds.append("rr.acknowledged_at IS NULL")
    elif scope == "ordered_by_me":
        if curr_doc_id:
            rad_conds.append("ro.doctor_id = :doc_id")
        else:
            rad_conds.append("1=0")
    elif scope == "all":
        rad_conds.append("rr.report_status IN ('Final', 'Approved')")

    if patient_id:
        rad_conds.append("s.patient_id = :patient_id")
    if q:
        rad_conds.append("(p.first_name ILIKE :search OR p.last_name ILIKE :search OR p.mrn ILIKE :search OR rt.test_name ILIKE :search)")

    rad_sql = f"""
        SELECT rr.report_id, s.study_id, ro.order_number, s.patient_id,
               p.first_name, p.last_name, p.mrn, rt.test_name, s.study_description,
               rr.report_text AS findings, rr.impression, rr.is_critical,
               rr.critical_alert_details, rr.reported_at, rr.approved_at, rr.acknowledged_at, rr.report_status,
               d.first_name AS doc_first_name, d.last_name AS doc_last_name
        FROM radiology.radiology_reports rr
        JOIN radiology.imaging_studies s USING(study_id)
        JOIN patient.patients p ON p.patient_id = s.patient_id
        LEFT JOIN radiology.radiology_appointments a USING(radiology_appointment_id)
        LEFT JOIN radiology.radiology_order_items oi ON oi.order_item_id = a.order_item_id
        LEFT JOIN radiology.radiology_orders ro USING(radiology_order_id)
        LEFT JOIN radiology.radiology_tests rt USING(radiology_test_id)
        LEFT JOIN doctor.doctors d ON d.doctor_id = ro.doctor_id
        WHERE {' AND '.join(rad_conds)}
        ORDER BY rr.reported_at DESC NULLS LAST
        LIMIT 50
    """
    rad_rows = (await db.execute(text(rad_sql), params)).mappings().all()

    return {
        "scope": scope,
        "laboratory_reports": [
            {
                "result_entry_id": str(r["result_entry_id"]),
                "test_name": r["test_name"],
                "order_number": r["order_number"],
                "patient_id": str(r["patient_id"]),
                "patient_name": f"{r['first_name']} {r['last_name']}",
                "mrn": r["mrn"],
                "approved_at": r["approved_at"].isoformat() if r["approved_at"] else None,
                "acknowledged_at": r["acknowledged_at"].isoformat() if r["acknowledged_at"] else None,

                "ordering_doctor": f"Dr. {r['doc_first_name']} {r['doc_last_name']}" if r["doc_first_name"] else "Hospital Staff",
                "remarks": r["remarks"],
                "status": r["result_status"],
                "has_abnormal": r["has_abnormal"],
                "has_critical": r["has_critical"],
                "parameters": r["parameters"]
            }
            for r in lab_rows
        ],
        "radiology_reports": [
            {
                "report_id": str(r["report_id"]),
                "study_id": str(r["study_id"]),
                "order_number": r["order_number"] or "RAD",
                "patient_id": str(r["patient_id"]),
                "patient_name": f"{r['first_name']} {r['last_name']}",
                "mrn": r["mrn"],
                "test_name": r["test_name"] or r["study_description"] or "Radiology Exam",
                "findings": r["findings"],
                "impression": r["impression"],
                "is_critical": r["is_critical"] or False,
                "critical_alert_details": r["critical_alert_details"],
                "ordering_doctor": f"Dr. {r['doc_first_name']} {r['doc_last_name']}" if r["doc_first_name"] else "Hospital Staff",
                "acknowledged_at": r["acknowledged_at"].isoformat() if r["acknowledged_at"] else None,

                "status": r["report_status"],
                "reported_at": r["reported_at"].isoformat() if r["reported_at"] else None
            }
            for r in rad_rows
        ],
        "total_count": len(lab_rows) + len(rad_rows),
        "total_pending": len([r for r in lab_rows if not r["acknowledged_at"]]) + len([r for r in rad_rows if not r["acknowledged_at"]])
    }


@router.post("/reports/lab/{result_entry_id}/acknowledge")
async def doctor_acknowledge_lab_report(
    result_entry_id: PyUUID,
    req: Optional[AcknowledgeReportRequest] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Doctor marks laboratory report as reviewed and acknowledged."""
    from app.models.laboratory_models import LabResultEntry
    res = await db.execute(select(LabResultEntry).where(LabResultEntry.result_entry_id == result_entry_id).with_for_update())
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(404, "Lab report not found")
    entry.acknowledged_by = cu.user_id
    entry.acknowledged_at = datetime.utcnow()
    entry.acknowledgement_notes = req.notes if req else None
    await db.commit()
    return {"message": "Laboratory report acknowledged", "result_entry_id": str(result_entry_id), "acknowledged_at": entry.acknowledged_at.isoformat()}


@router.post("/reports/radiology/{report_id}/acknowledge")
async def doctor_acknowledge_radiology_report(
    report_id: PyUUID,
    req: Optional[AcknowledgeReportRequest] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Doctor marks radiology report as reviewed and acknowledged."""
    from app.models.radiology_models import RadiologyReport
    res = await db.execute(select(RadiologyReport).where(RadiologyReport.report_id == report_id).with_for_update())
    rep = res.scalars().first()
    if not rep:
        raise HTTPException(404, "Radiology report not found")
    rep.acknowledged_by = cu.user_id
    rep.acknowledged_at = datetime.utcnow()
    rep.acknowledgement_notes = req.notes if req else None
    await db.commit()
    return {"message": "Radiology report acknowledged", "report_id": str(report_id), "acknowledged_at": rep.acknowledged_at.isoformat()}


@router.post("/follow-up")
async def schedule_follow_up(
    req: FollowUpRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Directly schedule a patient follow-up appointment from consultation."""
    from app.models.receptionist_models import Appointment, AppointmentStatus, AppointmentType
    from app.models.patient import Patient
    p = await db.get(Patient, req.patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")

    doctor_id = req.doctor_id
    if not doctor_id and cu.employee_id:
        doc = await get_doctor_by_employee(db, cu.employee_id)
        if doc: doctor_id = doc.doctor_id
    if not doctor_id:
        raise HTTPException(400, "Doctor must be specified or active on user account")

    st_res = await db.execute(select(AppointmentStatus).where(AppointmentStatus.status_name == "Scheduled"))
    st_obj = st_res.scalars().first()
    st_id = st_obj.appointment_status_id if st_obj else uuid.uuid4()

    typ_res = await db.execute(select(AppointmentType).where(AppointmentType.type_name == "Follow-up"))
    typ_obj = typ_res.scalars().first()
    if not typ_obj:
        typ_obj = AppointmentType(type_name="Follow-up", duration_minutes=15)
        db.add(typ_obj)
        await db.flush()

    apt_number = f"APT-FU-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    apt = Appointment(
        appointment_number=apt_number,
        patient_id=req.patient_id,
        doctor_id=doctor_id,
        appointment_date=req.follow_up_date,
        scheduled_time=req.time_slot or "10:00",
        appointment_type_id=typ_obj.type_id,
        appointment_status_id=st_id,
        reason_for_visit=req.reason or "Follow-up consultation",
        created_by=cu.user_id
    )
    db.add(apt)
    await db.commit()
    await db.refresh(apt)

    return {
        "message": "Follow-up scheduled successfully",
        "appointment_id": str(apt.appointment_id),
        "appointment_number": apt.appointment_number,
        "follow_up_date": apt.appointment_date.isoformat(),
        "scheduled_time": apt.scheduled_time
    }
