import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.employee import Base


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "core"}

    department_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_code = Column(String(50), unique=True, nullable=False)
    department_name = Column(String(255), nullable=False)
    description = Column(Text)
    schema_name = Column(String(100))
    is_active = Column(Boolean, default=True)


class SubDepartment(Base):
    __tablename__ = "sub_departments"
    __table_args__ = {"schema": "core"}

    sub_department_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id = Column(UUID(as_uuid=True), ForeignKey("core.departments.department_id"), nullable=False)
    sub_department_code = Column(String(50), unique=True, nullable=False)
    sub_department_name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)


class Country(Base):
    __tablename__ = "countries"
    __table_args__ = {"schema": "core"}

    country_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(10), unique=True, nullable=False)
    country_name = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)


class State(Base):
    __tablename__ = "states"
    __table_args__ = {"schema": "core"}

    state_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_id = Column(UUID(as_uuid=True), ForeignKey("core.countries.country_id"), nullable=False)
    state_code = Column(String(50), unique=True, nullable=False)
    state_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
