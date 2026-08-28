import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, String, Date, DateTime, Boolean, ForeignKey, BigInteger, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.employee import Base


class Gender(Base):
    __tablename__ = "genders"
    __table_args__ = {"schema": "patient"}

    gender_id = Column(BigInteger, primary_key=True, autoincrement=True)
    gender_name = Column(String(50), unique=True, nullable=False)


class BloodGroup(Base):
    __tablename__ = "blood_groups"
    __table_args__ = {"schema": "patient"}

    blood_group_id = Column(BigInteger, primary_key=True, autoincrement=True)
    blood_group_name = Column(String(10), unique=True, nullable=False)


class MaritalStatus(Base):
    __tablename__ = "marital_statuses"
    __table_args__ = {"schema": "patient"}

    marital_status_id = Column(BigInteger, primary_key=True, autoincrement=True)
    marital_status_name = Column(String(50), unique=True, nullable=False)


class PatientStatus(Base):
    __tablename__ = "patient_statuses"
    __table_args__ = {"schema": "patient"}

    status_id = Column(BigInteger, primary_key=True, autoincrement=True)
    status_name = Column(String(50), unique=True, nullable=False)


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {"schema": "patient"}

    patient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)

    patient_code = Column(String(50), unique=True, nullable=False)
    mrn = Column(String(50), unique=True, nullable=False)

    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)

    date_of_birth = Column(Date, nullable=False)

    gender_id = Column(BigInteger, ForeignKey("patient.genders.gender_id"), nullable=False)
    blood_group_id = Column(BigInteger, ForeignKey("patient.blood_groups.blood_group_id"), nullable=True)
    marital_status_id = Column(BigInteger, ForeignKey("patient.marital_statuses.marital_status_id"), nullable=True)
    status_id = Column(BigInteger, ForeignKey("patient.patient_statuses.status_id"), default=1)

    deceased_flag = Column(Boolean, default=False)
    deceased_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    gender = relationship("Gender")
    blood_group = relationship("BloodGroup")
    marital_status = relationship("MaritalStatus")
    status = relationship("PatientStatus")
    contacts = relationship("PatientContact", back_populates="patient", cascade="all, delete-orphan")
    addresses = relationship("PatientAddress", back_populates="patient", cascade="all, delete-orphan")
    emergency_contacts = relationship("PatientEmergencyContact", back_populates="patient", cascade="all, delete-orphan")


class PatientContact(Base):
    __tablename__ = "patient_contacts"
    __table_args__ = {"schema": "patient"}

    contact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    contact_type = Column(String(50), nullable=False)  # 'phone', 'email', etc.
    contact_value = Column(String(255), nullable=False)
    is_primary = Column(Boolean, default=False)
    verified_flag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="contacts")


class PatientAddress(Base):
    __tablename__ = "patient_addresses"
    __table_args__ = {"schema": "patient"}

    address_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    address_type = Column(String(50), default="Home")
    line1 = Column(String(255), nullable=False)
    line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    postal_code = Column(String(20), nullable=True)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="addresses")


class PatientEmergencyContact(Base):
    __tablename__ = "patient_emergency_contacts"
    __table_args__ = {"schema": "patient"}

    emergency_contact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    relationship = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="emergency_contacts")
