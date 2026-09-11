import uuid
from datetime import datetime
from sqlalchemy import Column, String, Date, Time, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class EmployeeCategory(Base):
    __tablename__ = "employee_categories"
    __table_args__ = {"schema": "human_resources"}

    employee_category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_code = Column(String(100), unique=True, nullable=False)
    category_name = Column(String(255), nullable=False)
    description = Column(Text)


class EmployeeType(Base):
    __tablename__ = "employee_types"
    __table_args__ = {"schema": "human_resources"}

    employee_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_code = Column(String(100), unique=True, nullable=False)
    type_name = Column(String(255))
    employment_nature = Column(String(100))


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = {"schema": "human_resources"}

    employee_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_number = Column(String(100), unique=True, nullable=False)
    employee_category_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employee_categories.employee_category_id"))
    employee_type_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employee_types.employee_type_id"))
    first_name = Column(String(255))
    middle_name = Column(String(255))
    last_name = Column(String(255))
    gender = Column(String(50))
    date_of_birth = Column(Date)
    date_of_joining = Column(Date)
    employment_status = Column(String(100), default="active")
    official_email = Column(String(255))
    official_phone = Column(String(50))
    department_id = Column(UUID(as_uuid=True), ForeignKey("core.departments.department_id"))
    sub_department_id = Column(UUID(as_uuid=True), ForeignKey("core.sub_departments.sub_department_id"))


class ShiftSchedule(Base):
    __tablename__ = "shift_schedules"
    __table_args__ = {"schema": "human_resources"}

    shift_schedule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_code = Column(String(50), unique=True, nullable=False)
    shift_name = Column(String(100), nullable=False)
    shift_start_time = Column(Time, nullable=False)
    shift_end_time = Column(Time, nullable=False)
    is_night_shift = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class EmployeeRoster(Base):
    __tablename__ = "employee_rosters"
    __table_args__ = (
        UniqueConstraint("employee_id", "roster_date", name="uq_employee_roster_date"),
        {"schema": "human_resources"},
    )

    employee_roster_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employees.employee_id", ondelete="CASCADE"), nullable=False)
    shift_schedule_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.shift_schedules.shift_schedule_id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("core.departments.department_id"), nullable=True)
    roster_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

