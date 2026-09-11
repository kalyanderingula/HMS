import uuid
from datetime import datetime, date, time
from sqlalchemy import Column, String, Date, DateTime, Time, Boolean, ForeignKey, BigInteger, Text, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship as orm_relationship
from app.models.employee import Base


# ==========================================
# APPOINTMENT MANAGEMENT SCHEMA
# ==========================================

class AppointmentStatus(Base):
    __tablename__ = "appointment_statuses"
    __table_args__ = {"schema": "appointment"}

    appointment_status_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class AppointmentType(Base):
    __tablename__ = "appointment_types"
    __table_args__ = {"schema": "appointment"}

    appointment_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = {"schema": "appointment"}

    appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    appointment_number = Column(String(100), unique=True, nullable=False)

    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctor.doctors.doctor_id", ondelete="RESTRICT"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("core.departments.department_id"), nullable=True)

    appointment_type_id = Column(UUID(as_uuid=True), ForeignKey("appointment.appointment_types.appointment_type_id"), nullable=True)
    appointment_status_id = Column(UUID(as_uuid=True), ForeignKey("appointment.appointment_statuses.appointment_status_id"), nullable=False)

    appointment_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    estimated_duration_minutes = Column(Integer, default=15)
    chief_complaint = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    booking_source = Column(String(100), default="Reception Desk")
    booked_by = Column(UUID(as_uuid=True), nullable=True)
    booked_at = Column(DateTime, default=datetime.utcnow)
    checked_in_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==========================================
# QUEUE MANAGEMENT SCHEMA
# ==========================================

class QueueServicePoint(Base):
    __tablename__ = "queue_service_points"
    __table_args__ = {"schema": "queue_management"}

    service_point_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    point_name = Column(String(255), nullable=False)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    location = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)


class QueueToken(Base):
    __tablename__ = "queue_tokens"
    __table_args__ = {"schema": "queue_management"}

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    service_point_id = Column(UUID(as_uuid=True), ForeignKey("queue_management.queue_service_points.service_point_id"), nullable=False)
    token_number = Column(String(20), nullable=False)
    patient_id = Column(UUID(as_uuid=True), nullable=True)
    appointment_id = Column(UUID(as_uuid=True), nullable=True)
    token_type = Column(String(30), default="walk_in")
    priority = Column(Integer, default=0)
    status = Column(String(30), default="waiting")  # 'waiting', 'called', 'in_consultation', 'completed', 'no_show'
    issued_at = Column(DateTime, default=datetime.utcnow)
    called_at = Column(DateTime, nullable=True)
    serving_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


# ==========================================
# INPATIENT ADMISSION SCHEMA
# ==========================================

class Ward(Base):
    __tablename__ = "wards"
    __table_args__ = {"schema": "admission"}

    ward_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ward_code = Column(String(100), unique=True, nullable=False)
    ward_name = Column(String(255), nullable=False)
    floor_number = Column(String(50), nullable=True)
    building_name = Column(String(255), nullable=True)


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = {"schema": "admission"}

    room_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ward_id = Column(UUID(as_uuid=True), ForeignKey("admission.wards.ward_id"), nullable=False)
    room_number = Column(String(100), unique=True, nullable=False)
    floor_number = Column(String(50), nullable=True)


class BedStatus(Base):
    __tablename__ = "bed_statuses"
    __table_args__ = {"schema": "admission"}
    bed_status_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status_name = Column(String(100), unique=True, nullable=False)


class Bed(Base):
    __tablename__ = "beds"
    __table_args__ = {"schema": "admission"}

    bed_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("admission.rooms.room_id"), nullable=False)
    bed_number = Column(String(100), nullable=False)
    bed_status_id = Column(UUID(as_uuid=True), ForeignKey("admission.bed_statuses.bed_status_id"))
    bed_type = Column(String(100))


class Admission(Base):
    __tablename__ = "admissions"
    __table_args__ = {"schema": "admission"}

    admission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admission_number = Column(String(100), unique=True, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    admitting_doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctor.doctors.doctor_id", ondelete="RESTRICT"), nullable=True)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    ward_id = Column(UUID(as_uuid=True), ForeignKey("admission.wards.ward_id"), nullable=True)
    room_id = Column(UUID(as_uuid=True), ForeignKey("admission.rooms.room_id"), nullable=True)
    bed_id = Column(UUID(as_uuid=True), ForeignKey("admission.beds.bed_id"), nullable=True)
    admission_reason = Column(Text, nullable=True)
    admission_date = Column(DateTime, default=datetime.utcnow)
    actual_discharge_date = Column(DateTime, nullable=True)
    discharge_summary = Column(Text)
    discharge_condition = Column(Text)
    discharge_summary_signed = Column(Boolean, default=False, nullable=False)
    pharmacy_cleared = Column(Boolean, default=False, nullable=False)
    nursing_cleared = Column(Boolean, default=False, nullable=False)
    billing_cleared = Column(Boolean, default=False, nullable=False)
    clearance_notes = Column(Text, nullable=True)
    discharged_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text)


class InpatientRound(Base):
    __tablename__ = "inpatient_rounds"
    __table_args__ = {"schema": "admission"}

    round_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admission_id = Column(UUID(as_uuid=True), ForeignKey("admission.admissions.admission_id", ondelete="CASCADE"), nullable=False)
    round_datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctor.doctors.doctor_id", ondelete="RESTRICT"), nullable=True)
    nurse_id = Column(UUID(as_uuid=True), nullable=True)
    chief_complaint_today = Column(Text, nullable=True)
    clinical_progress_notes = Column(Text, nullable=False)
    temperature = Column(Numeric(4, 2), nullable=True)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    oxygen_saturation = Column(Numeric(4, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ==========================================
# VISITOR MANAGEMENT SCHEMA
# ==========================================

class Visitor(Base):
    __tablename__ = "visitors"
    __table_args__ = {"schema": "visitor"}

    visitor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    id_proof_number = Column(String(100), nullable=True)


class VisitorPass(Base):
    __tablename__ = "visitor_passes"
    __table_args__ = {"schema": "visitor"}

    pass_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("visitor.visitors.visitor_id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), nullable=True)
    pass_number = Column(String(50), unique=True, nullable=False)
    check_in_time = Column(DateTime, default=datetime.utcnow)
    check_out_time = Column(DateTime, nullable=True)
    expected_duration_minutes = Column(Integer, default=240)
    status = Column(String(30), default="active")
