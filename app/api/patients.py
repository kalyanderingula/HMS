import uuid
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc
from sqlalchemy.orm import selectinload

from app.config import get_db
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
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientDetailResponse,
    PatientMastersResponse,
    MasterOption,
)

router = APIRouter(prefix="/patients", tags=["Patient Management"])


# =============================================================================
# Helper: Generate Next MRN & Patient Code
# =============================================================================
async def generate_patient_identifiers(db: AsyncSession):
    year = datetime.utcnow().year
    # Count total patients this year
    count_stmt = select(func.count(Patient.patient_id))
    result = await db.execute(count_stmt)
    total = (result.scalar() or 0) + 1
    mrn = f"MRN-{year}-{total:05d}"
    patient_code = f"PAT-{year}-{total:05d}"
    return mrn, patient_code


# =============================================================================
# Helper: Ensure Seed Master Data Exists
# =============================================================================
async def ensure_patient_masters(db: AsyncSession):
    # Check genders
    g_res = await db.execute(select(Gender))
    if not g_res.scalars().first():
        for g_name in ["Male", "Female", "Other"]:
            db.add(Gender(gender_name=g_name))

    # Check blood groups
    bg_res = await db.execute(select(BloodGroup))
    if not bg_res.scalars().first():
        for bg_name in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
            db.add(BloodGroup(blood_group_name=bg_name))

    # Check marital statuses
    ms_res = await db.execute(select(MaritalStatus))
    if not ms_res.scalars().first():
        for ms_name in ["Single", "Married", "Divorced", "Widowed"]:
            db.add(MaritalStatus(marital_status_name=ms_name))

    # Check patient statuses
    ps_res = await db.execute(select(PatientStatus))
    if not ps_res.scalars().first():
        for ps_name in ["Active", "Inactive", "Deceased"]:
            db.add(PatientStatus(status_name=ps_name))

    await db.commit()


# =============================================================================
# 1. Master Dropdowns Lookup API
# =============================================================================
@router.get("/masters", response_model=PatientMastersResponse)
async def get_patient_masters(db: AsyncSession = Depends(get_db)):
    await ensure_patient_masters(db)

    genders = (await db.execute(select(Gender).order_by(Gender.gender_id))).scalars().all()
    blood_groups = (await db.execute(select(BloodGroup).order_by(BloodGroup.blood_group_id))).scalars().all()
    marital_statuses = (await db.execute(select(MaritalStatus).order_by(MaritalStatus.marital_status_id))).scalars().all()
    statuses = (await db.execute(select(PatientStatus).order_by(PatientStatus.status_id))).scalars().all()

    return PatientMastersResponse(
        genders=[MasterOption(id=g.gender_id, name=g.gender_name) for g in genders],
        blood_groups=[MasterOption(id=bg.blood_group_id, name=bg.blood_group_name) for bg in blood_groups],
        marital_statuses=[MasterOption(id=ms.marital_status_id, name=ms.marital_status_name) for ms in marital_statuses],
        statuses=[MasterOption(id=st.status_id, name=st.status_name) for st in statuses],
    )


# =============================================================================
# 2. Register New Patient
# =============================================================================
@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(payload: PatientCreate, db: AsyncSession = Depends(get_db)):
    await ensure_patient_masters(db)
    mrn, patient_code = await generate_patient_identifiers(db)

    # 1. Create Patient Core Record
    patient = Patient(
        mrn=mrn,
        patient_code=patient_code,
        first_name=payload.first_name.strip(),
        middle_name=payload.middle_name.strip() if payload.middle_name else None,
        last_name=payload.last_name.strip(),
        date_of_birth=payload.date_of_birth,
        gender_id=payload.gender_id,
        blood_group_id=payload.blood_group_id,
        marital_status_id=payload.marital_status_id,
        status_id=1,  # Active
    )
    db.add(patient)
    await db.flush()  # Populates patient.patient_id

    # 2. Add Phone Contact
    if payload.phone:
        phone_contact = PatientContact(
            patient_id=patient.patient_id,
            contact_type="phone",
            contact_value=payload.phone.strip(),
            is_primary=True,
        )
        db.add(phone_contact)

    # 3. Add Email Contact
    if payload.email:
        email_contact = PatientContact(
            patient_id=patient.patient_id,
            contact_type="email",
            contact_value=payload.email.strip(),
            is_primary=False,
        )
        db.add(email_contact)

    # 4. Add Address
    if payload.address_line1:
        address = PatientAddress(
            patient_id=patient.patient_id,
            address_type="Home",
            line1=payload.address_line1.strip(),
            city=payload.city.strip() if payload.city else None,
            state=payload.state.strip() if payload.state else None,
            postal_code=payload.postal_code.strip() if payload.postal_code else None,
        )
        db.add(address)

    # 5. Add Emergency Contact
    if payload.emergency_contact_name:
        emergency = PatientEmergencyContact(
            patient_id=patient.patient_id,
            full_name=payload.emergency_contact_name.strip(),
            relationship=payload.emergency_contact_relation.strip() if payload.emergency_contact_relation else None,
            phone=payload.emergency_contact_phone.strip() if payload.emergency_contact_phone else None,
        )
        db.add(emergency)

    await db.commit()

    # Reload with relationships
    return await get_patient_response(patient.patient_id, db)


# =============================================================================
# 3. Search & List Patients
# =============================================================================
@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    q: Optional[str] = Query(None, description="Search by Name, MRN, or Phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Patient)
        .options(
            selectinload(Patient.gender),
            selectinload(Patient.blood_group),
            selectinload(Patient.marital_status),
            selectinload(Patient.status),
            selectinload(Patient.contacts),
            selectinload(Patient.addresses),
        )
        .where(Patient.deleted_at.is_(None))
        .order_by(desc(Patient.created_at))
    )

    if q:
        search_term = f"%{q.strip()}%"
        # Search patient name, MRN, patient_code, or contact phone
        query = query.outerjoin(Patient.contacts).where(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.mrn.ilike(search_term),
                Patient.patient_code.ilike(search_term),
                PatientContact.contact_value.ilike(search_term),
            )
        ).distinct()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    patients = result.scalars().all()

    return [format_patient_response(p) for p in patients]


# =============================================================================
# 4. Get Full Patient Details
# =============================================================================
@router.get("/{patient_id}", response_model=PatientDetailResponse)
async def get_patient_profile(patient_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    query = (
        select(Patient)
        .options(
            selectinload(Patient.gender),
            selectinload(Patient.blood_group),
            selectinload(Patient.marital_status),
            selectinload(Patient.status),
            selectinload(Patient.contacts),
            selectinload(Patient.addresses),
            selectinload(Patient.emergency_contacts),
        )
        .where(Patient.patient_id == patient_id, Patient.deleted_at.is_(None))
    )
    result = await db.execute(query)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    res = format_patient_response(patient)
    return PatientDetailResponse(
        **res.model_dump(),
        contacts=patient.contacts or [],
        addresses=patient.addresses or [],
        emergency_contacts=patient.emergency_contacts or [],
    )


# =============================================================================
# 5. Update Patient
# =============================================================================
@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    db: AsyncSession = Depends(get_db),
):
    patient = await db.get(Patient, patient_id)
    if not patient or patient.deleted_at:
        raise HTTPException(status_code=404, detail="Patient not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in ["phone", "email"]:
            continue
        if hasattr(patient, field) and value is not None:
            setattr(patient, field, value)

    # Update primary phone if provided
    if payload.phone:
        phone_contact = (
            await db.execute(
                select(PatientContact).where(
                    PatientContact.patient_id == patient_id,
                    PatientContact.contact_type == "phone",
                    PatientContact.is_primary == True,
                )
            )
        ).scalar_one_or_none()
        if phone_contact:
            phone_contact.contact_value = payload.phone.strip()
        else:
            db.add(
                PatientContact(
                    patient_id=patient_id,
                    contact_type="phone",
                    contact_value=payload.phone.strip(),
                    is_primary=True,
                )
            )

    # Update email if provided
    if payload.email:
        email_contact = (
            await db.execute(
                select(PatientContact).where(
                    PatientContact.patient_id == patient_id,
                    PatientContact.contact_type == "email",
                )
            )
        ).scalar_one_or_none()
        if email_contact:
            email_contact.contact_value = payload.email.strip()
        else:
            db.add(
                PatientContact(
                    patient_id=patient_id,
                    contact_type="email",
                    contact_value=payload.email.strip(),
                    is_primary=False,
                )
            )

    patient.updated_at = datetime.utcnow()
    await db.commit()
    return await get_patient_response(patient_id, db)


# =============================================================================
# Helper: Format Formatted Response
# =============================================================================
def format_patient_response(p: Patient) -> PatientResponse:
    primary_phone = None
    email_val = None
    city_val = None

    if p.contacts:
        for c in p.contacts:
            if c.contact_type == "phone" and (c.is_primary or not primary_phone):
                primary_phone = c.contact_value
            elif c.contact_type == "email":
                email_val = c.contact_value

    if p.addresses and len(p.addresses) > 0:
        city_val = p.addresses[0].city

    return PatientResponse(
        patient_id=p.patient_id,
        patient_code=p.patient_code,
        mrn=p.mrn,
        first_name=p.first_name,
        middle_name=p.middle_name,
        last_name=p.last_name,
        date_of_birth=p.date_of_birth,
        gender_id=p.gender_id,
        gender_name=p.gender.gender_name if p.gender else None,
        blood_group_id=p.blood_group_id,
        blood_group_name=p.blood_group.blood_group_name if p.blood_group else None,
        marital_status_name=p.marital_status.marital_status_name if p.marital_status else None,
        status_name=p.status.status_name if p.status else "Active",
        phone=primary_phone,
        email=email_val,
        city=city_val,
        created_at=p.created_at,
    )


async def get_patient_response(patient_id: uuid.UUID, db: AsyncSession) -> PatientResponse:
    query = (
        select(Patient)
        .options(
            selectinload(Patient.gender),
            selectinload(Patient.blood_group),
            selectinload(Patient.marital_status),
            selectinload(Patient.status),
            selectinload(Patient.contacts),
            selectinload(Patient.addresses),
        )
        .where(Patient.patient_id == patient_id)
    )
    result = await db.execute(query)
    patient = result.scalar_one()
    return format_patient_response(patient)
