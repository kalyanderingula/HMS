from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List


class PatientCreate(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    date_of_birth: date
    gender_id: int
    blood_group_id: Optional[int] = None
    marital_status_id: Optional[int] = None

    # Primary Contact & Address (Auto-created with patient)
    phone: str
    email: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None

    # Emergency Contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender_id: Optional[int] = None
    blood_group_id: Optional[int] = None
    marital_status_id: Optional[int] = None
    status_id: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ContactItem(BaseModel):
    contact_id: UUID
    contact_type: str
    contact_value: str
    is_primary: bool

    class Config:
        from_attributes = True


class AddressItem(BaseModel):
    address_id: UUID
    address_type: Optional[str]
    line1: str
    line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]

    class Config:
        from_attributes = True


class EmergencyContactItem(BaseModel):
    emergency_contact_id: UUID
    full_name: str
    relationship: Optional[str]
    phone: Optional[str]
    email: Optional[str]

    class Config:
        from_attributes = True


class PatientResponse(BaseModel):
    patient_id: UUID
    patient_code: str
    mrn: str
    first_name: str
    middle_name: Optional[str]
    last_name: str
    date_of_birth: date
    gender_id: int
    gender_name: Optional[str] = None
    blood_group_id: Optional[int] = None
    blood_group_name: Optional[str] = None
    marital_status_name: Optional[str] = None
    status_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PatientDetailResponse(PatientResponse):
    contacts: List[ContactItem] = []
    addresses: List[AddressItem] = []
    emergency_contacts: List[EmergencyContactItem] = []

    class Config:
        from_attributes = True


class MasterOption(BaseModel):
    id: int
    name: str


class PatientMastersResponse(BaseModel):
    genders: List[MasterOption]
    blood_groups: List[MasterOption]
    marital_statuses: List[MasterOption]
    statuses: List[MasterOption]
