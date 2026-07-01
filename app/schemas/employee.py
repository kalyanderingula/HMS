from pydantic import BaseModel
from uuid import UUID
from datetime import date
from typing import Optional


class EmployeeCreate(BaseModel):
    employee_number: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    date_of_joining: Optional[date] = None
    employment_status: Optional[str] = "active"
    official_email: Optional[str] = None
    official_phone: Optional[str] = None
    employee_category_id: Optional[UUID] = None
    employee_type_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    sub_department_id: Optional[UUID] = None


class EmployeeResponse(BaseModel):
    employee_id: UUID
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
    employee_category_id: Optional[UUID]
    employee_type_id: Optional[UUID]
    department_id: Optional[UUID]
    sub_department_id: Optional[UUID]

    class Config:
        from_attributes = True


class EmployeeCategoryCreate(BaseModel):
    category_code: str
    category_name: str
    description: Optional[str] = None


class EmployeeCategoryResponse(BaseModel):
    employee_category_id: UUID
    category_code: str
    category_name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class EmployeeTypeCreate(BaseModel):
    type_code: str
    type_name: str
    employment_nature: Optional[str] = None


class EmployeeTypeResponse(BaseModel):
    employee_type_id: UUID
    type_code: str
    type_name: Optional[str]
    employment_nature: Optional[str]

    class Config:
        from_attributes = True
