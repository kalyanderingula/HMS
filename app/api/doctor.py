import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, BigInteger, select
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as PyUUID
from pydantic import BaseModel
from typing import Optional
from datetime import date
import os

from app.config import get_db
from app.models.employee import Base

router = APIRouter(prefix="/doctor", tags=["Doctor Portal"])

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
    __tablename__ = "document_types"
    __table_args__ = {"schema": "doctor"}
    document_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type_name = Column(String(255), unique=True)


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
    result = await db.execute(select(DoctorStatus).where(DoctorStatus.status_name == 'active'))
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


# --- Endpoints ---

# Get my profile (by employee_id from token)
@router.get("/my-profile/{employee_id}")
async def get_my_profile(employee_id: PyUUID, db: AsyncSession = Depends(get_db)):
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
    emp = await db.get(Employee, employee_id)

    # Get employee details for personal info section
    from app.api.employees import get_employee_details
    emp_details_raw = await get_employee_details(db, employee_id)
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
            "joining_date": str(emp.date_of_joining) if emp and emp.date_of_joining else None,
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
