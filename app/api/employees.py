import uuid
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as PyUUID
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date

from app.config import get_db
from app.models.employee import Base, Employee
from app.models.department import Department, SubDepartment

router = APIRouter(prefix="/employees", tags=["Employees"])


# --- Models for related tables ---

class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    __table_args__ = {"schema": "human_resources"}

    employee_profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employees.employee_id"))
    marital_status = Column(String(100))
    nationality = Column(String(100))
    blood_group = Column(String(10))
    emergency_contact_name = Column(String(255))
    emergency_contact_phone = Column(String(50))


class EmployeeAddress(Base):
    __tablename__ = "employee_addresses"
    __table_args__ = {"schema": "human_resources"}

    employee_address_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employees.employee_id"))
    address_type = Column(String(100))
    address_line_1 = Column(Text)
    address_line_2 = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(50))
    country = Column(String(100))


class EmployeeContact(Base):
    __tablename__ = "employee_contacts"
    __table_args__ = {"schema": "human_resources"}

    employee_contact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employees.employee_id"))
    contact_type = Column(String(100))
    contact_value = Column(String(255))
    is_primary = Column(Boolean, default=False)


# --- Schemas ---

class ProfileData(BaseModel):
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator('nationality', 'emergency_contact_name')
    @classmethod
    def must_be_alpha(cls, v, info):
        if v and not v.replace(' ', '').replace('.', '').isalpha():
            raise ValueError(f'{info.field_name} must contain only letters')
        return v.strip() if v else v

    @field_validator('emergency_contact_phone')
    @classmethod
    def validate_emergency_phone(cls, v):
        if v and not re.match(r'^\+?[\d\s-]{7,15}$', v):
            raise ValueError('Emergency phone must be 7-15 digits')
        return v


class AddressData(BaseModel):
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    @field_validator('city')
    @classmethod
    def city_must_be_alpha(cls, v):
        if v and not v.replace(' ', '').isalpha():
            raise ValueError('City must contain only letters')
        return v.strip() if v else v

    @field_validator('postal_code')
    @classmethod
    def validate_postal_code(cls, v):
        if v and not re.match(r'^[\d]{4,10}$', v):
            raise ValueError('Postal code must be 4-10 digits')
        return v


class ContactData(BaseModel):
    personal_phone: Optional[str] = None
    personal_email: Optional[str] = None

    @field_validator('personal_phone')
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?[\d\s-]{7,15}$', v):
            raise ValueError('Personal phone must be 7-15 digits')
        return v

    @field_validator('personal_email')
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', v):
            raise ValueError('Invalid personal email format')
        return v


class EmployeeCreate(BaseModel):
    # Basic (mandatory: first_name, last_name, gender, date_of_birth)
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    gender: str
    date_of_birth: date
    date_of_joining: Optional[date] = None
    official_email: Optional[str] = None
    official_phone: Optional[str] = None
    department_id: Optional[PyUUID] = None
    sub_department_id: Optional[PyUUID] = None
    # Roles for RBAC (one or more)
    roles: list[str]
    # Profile (optional)
    profile: Optional[ProfileData] = None
    # Address (optional)
    address: Optional[AddressData] = None
    # Contact (optional)
    contact: Optional[ContactData] = None

    @field_validator('first_name', 'last_name')
    @classmethod
    def name_must_be_alpha(cls, v, info):
        if not v.replace(' ', '').isalpha():
            raise ValueError(f'{info.field_name} must contain only letters')
        return v.strip()

    @field_validator('official_email')
    @classmethod
    def validate_official_email(cls, v):
        if v and not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', v):
            raise ValueError('Invalid official email format')
        return v

    @field_validator('official_phone')
    @classmethod
    def validate_official_phone(cls, v):
        if v and not re.match(r'^\+?[\d\s-]{7,15}$', v):
            raise ValueError('Official phone must be 7-15 digits')
        return v


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    date_of_joining: Optional[date] = None
    employment_status: Optional[str] = None
    official_email: Optional[str] = None
    official_phone: Optional[str] = None
    department_id: Optional[PyUUID] = None
    sub_department_id: Optional[PyUUID] = None
    roles: Optional[list[str]] = None
    profile: Optional[ProfileData] = None
    address: Optional[AddressData] = None
    contact: Optional[ContactData] = None


class EmployeeResponse(BaseModel):
    employee_id: PyUUID
    employee_number: str
    first_name: Optional[str]
    last_name: Optional[str]
    middle_name: Optional[str]
    gender: Optional[str]
    date_of_birth: Optional[date]
    date_of_joining: Optional[date]
    employment_status: Optional[str]
    official_email: Optional[str]
    official_phone: Optional[str]
    department_id: Optional[PyUUID]
    sub_department_id: Optional[PyUUID]
    profile: Optional[dict] = None
    address: Optional[dict] = None
    contact: Optional[dict] = None
    roles: Optional[list[str]] = None

    class Config:
        from_attributes = True


# --- Helpers ---

async def generate_employee_number(db: AsyncSession, department_id, sub_department_id):
    dept_code = "GEN"
    if department_id:
        dept = await db.get(Department, department_id)
        if dept:
            dept_code = dept.department_code.replace("DEP-", "")

    sub_dept_code = "GEN"
    if sub_department_id:
        sub_dept = await db.get(SubDepartment, sub_department_id)
        if sub_dept:
            sub_dept_code = sub_dept.sub_department_code.split("-", 1)[-1] if "-" in sub_dept.sub_department_code else sub_dept.sub_department_code

    prefix = f"{dept_code}-{sub_dept_code}"
    result = await db.execute(
        select(Employee).where(Employee.employee_number.like(f"{prefix}-%")).order_by(Employee.employee_number.desc())
    )
    last = result.scalars().first()
    next_num = int(last.employee_number.rsplit("-", 1)[-1]) + 1 if last else 1
    return f"{prefix}-{next_num:05d}"


async def get_employee_details(db: AsyncSession, employee_id):
    """Get employee with profile, address, contact"""
    emp = await db.get(Employee, employee_id)
    if not emp:
        return None

    # Profile
    result = await db.execute(select(EmployeeProfile).where(EmployeeProfile.employee_id == employee_id))
    profile = result.scalars().first()

    # Address
    result = await db.execute(select(EmployeeAddress).where(EmployeeAddress.employee_id == employee_id))
    address = result.scalars().first()

    # Contact (personal)
    result = await db.execute(select(EmployeeContact).where(EmployeeContact.employee_id == employee_id))
    contacts = result.scalars().all()

    personal_phone = None
    personal_email = None
    for c in contacts:
        if c.contact_type == "personal_phone":
            personal_phone = c.contact_value
        elif c.contact_type == "personal_email":
            personal_email = c.contact_value

    # Get roles
    from app.api.auth import User, UserRole, Role
    result = await db.execute(select(User).where(User.employee_id == employee_id))
    user = result.scalars().first()
    roles_list = []
    if user:
        result = await db.execute(
            select(Role).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user.user_id)
        )
        roles_list = [r.role_name for r in result.scalars().all()]

    return EmployeeResponse(
        employee_id=emp.employee_id,
        employee_number=emp.employee_number,
        first_name=emp.first_name,
        last_name=emp.last_name,
        middle_name=emp.middle_name,
        gender=emp.gender,
        date_of_birth=emp.date_of_birth,
        date_of_joining=emp.date_of_joining,
        employment_status=emp.employment_status,
        official_email=emp.official_email,
        official_phone=emp.official_phone,
        department_id=emp.department_id,
        sub_department_id=emp.sub_department_id,
        profile={
            "marital_status": profile.marital_status,
            "nationality": profile.nationality,
            "blood_group": profile.blood_group,
            "emergency_contact_name": profile.emergency_contact_name,
            "emergency_contact_phone": profile.emergency_contact_phone,
        } if profile else None,
        address={
            "address_line_1": address.address_line_1,
            "address_line_2": address.address_line_2,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
        } if address else None,
        contact={
            "personal_phone": personal_phone,
            "personal_email": personal_email,
        } if (personal_phone or personal_email) else None,
        roles=roles_list,
    )


# --- Endpoints ---

@router.post("/", response_model=EmployeeResponse, status_code=201)
async def create_employee(data: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    if data.department_id:
        if not await db.get(Department, data.department_id):
            raise HTTPException(status_code=404, detail="Department not found")
    if data.sub_department_id:
        if not await db.get(SubDepartment, data.sub_department_id):
            raise HTTPException(status_code=404, detail="Sub-department not found")

    # Generate employee number
    emp_number = await generate_employee_number(db, data.department_id, data.sub_department_id)

    # Create employee
    employee = Employee(
        employee_number=emp_number,
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        gender=data.gender,
        date_of_birth=data.date_of_birth,
        date_of_joining=data.date_of_joining,
        employment_status="active",
        official_email=data.official_email,
        official_phone=data.official_phone,
        department_id=data.department_id,
        sub_department_id=data.sub_department_id,
    )
    db.add(employee)
    await db.flush()

    # Create profile
    if data.profile:
        profile = EmployeeProfile(employee_id=employee.employee_id, **data.profile.model_dump())
        db.add(profile)

    # Create address
    if data.address:
        address = EmployeeAddress(employee_id=employee.employee_id, address_type="permanent", **data.address.model_dump())
        db.add(address)

    # Create contacts
    if data.contact:
        if data.contact.personal_phone:
            db.add(EmployeeContact(employee_id=employee.employee_id, contact_type="personal_phone", contact_value=data.contact.personal_phone, is_primary=True))
        if data.contact.personal_email:
            db.add(EmployeeContact(employee_id=employee.employee_id, contact_type="personal_email", contact_value=data.contact.personal_email))

    # Create login account
    # Password format: Firstname_@_DDMMYYYY (first letter caps)
    from app.api.auth import create_user_account_multi_roles
    first_name_cap = data.first_name[0].upper() + data.first_name[1:].lower()
    dob_str = data.date_of_birth.strftime("%d%m%Y")
    auto_password = f"{first_name_cap}_@_{dob_str}"
    await create_user_account_multi_roles(db, employee.employee_id, emp_number, data.official_email, auto_password, data.roles)

    await db.commit()
    return await get_employee_details(db, employee.employee_id)


@router.get("/", response_model=list[EmployeeResponse])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee))
    employees = result.scalars().all()
    responses = []
    for emp in employees:
        detail = await get_employee_details(db, emp.employee_id)
        responses.append(detail)
    return responses


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: PyUUID, db: AsyncSession = Depends(get_db)):
    detail = await get_employee_details(db, employee_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Employee not found")
    return detail


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(employee_id: PyUUID, db: AsyncSession = Depends(get_db)):
    employee = await db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    # Delete related records
    for model in [EmployeeProfile, EmployeeAddress, EmployeeContact]:
        result = await db.execute(select(model).where(model.employee_id == employee_id))
        for row in result.scalars().all():
            await db.delete(row)
    # Delete user account
    from app.api.auth import User, UserRole
    result = await db.execute(select(User).where(User.employee_id == employee_id))
    user = result.scalars().first()
    if user:
        result = await db.execute(select(UserRole).where(UserRole.user_id == user.user_id))
        for ur in result.scalars().all():
            await db.delete(ur)
        await db.delete(user)
    await db.delete(employee)
    await db.commit()


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(employee_id: PyUUID, data: EmployeeUpdate, db: AsyncSession = Depends(get_db)):
    employee = await db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Update basic fields
    basic_fields = ["first_name", "last_name", "middle_name", "gender", "date_of_birth",
                    "date_of_joining", "employment_status", "official_email", "official_phone",
                    "department_id", "sub_department_id"]
    update_data = data.model_dump(exclude_unset=True, exclude={"profile", "address", "contact"})
    for field in basic_fields:
        if field in update_data:
            setattr(employee, field, update_data[field])

    # Update profile
    if data.profile:
        result = await db.execute(select(EmployeeProfile).where(EmployeeProfile.employee_id == employee_id))
        profile = result.scalars().first()
        if profile:
            for k, v in data.profile.model_dump(exclude_unset=True).items():
                setattr(profile, k, v)
        else:
            db.add(EmployeeProfile(employee_id=employee_id, **data.profile.model_dump()))

    # Update address
    if data.address:
        result = await db.execute(select(EmployeeAddress).where(EmployeeAddress.employee_id == employee_id))
        address = result.scalars().first()
        if address:
            for k, v in data.address.model_dump(exclude_unset=True).items():
                setattr(address, k, v)
        else:
            db.add(EmployeeAddress(employee_id=employee_id, address_type="permanent", **data.address.model_dump()))

    # Update contacts
    if data.contact:
        if data.contact.personal_phone:
            result = await db.execute(select(EmployeeContact).where(EmployeeContact.employee_id == employee_id, EmployeeContact.contact_type == "personal_phone"))
            c = result.scalars().first()
            if c:
                c.contact_value = data.contact.personal_phone
            else:
                db.add(EmployeeContact(employee_id=employee_id, contact_type="personal_phone", contact_value=data.contact.personal_phone, is_primary=True))

        if data.contact.personal_email:
            result = await db.execute(select(EmployeeContact).where(EmployeeContact.employee_id == employee_id, EmployeeContact.contact_type == "personal_email"))
            c = result.scalars().first()
            if c:
                c.contact_value = data.contact.personal_email
            else:
                db.add(EmployeeContact(employee_id=employee_id, contact_type="personal_email", contact_value=data.contact.personal_email))

    # Update roles (replace all)
    if data.roles is not None:
        from app.api.auth import User, UserRole, Role
        result = await db.execute(select(User).where(User.employee_id == employee_id))
        user = result.scalars().first()
        if user:
            # Delete existing roles
            result = await db.execute(select(UserRole).where(UserRole.user_id == user.user_id))
            for ur in result.scalars().all():
                await db.delete(ur)
            # Add new roles
            for role_name in data.roles:
                result = await db.execute(select(Role).where(Role.role_name == role_name))
                role = result.scalars().first()
                if role:
                    db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

    await db.commit()
    return await get_employee_details(db, employee_id)
