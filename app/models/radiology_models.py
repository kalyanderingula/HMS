import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.employee import Base

class RadiologyDepartment(Base):
    __tablename__ = "radiology_departments"
    __table_args__ = {"schema": "radiology"}

    radiology_department_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_code = Column(String(100), unique=True, nullable=False)
    department_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ImagingModality(Base):
    __tablename__ = "imaging_modalities"
    __table_args__ = {"schema": "radiology"}

    modality_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modality_code = Column(String(50), unique=True, nullable=False)
    modality_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ImagingRoom(Base):
    __tablename__ = "imaging_rooms"
    __table_args__ = {"schema": "radiology"}

    imaging_room_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_code = Column(String(100), unique=True, nullable=False)
    room_name = Column(String(255), nullable=False)
    modality_id = Column(UUID(as_uuid=True), ForeignKey("radiology.imaging_modalities.modality_id"), nullable=False)
    room_location = Column(String(255), nullable=True)
    room_status = Column(String(100), default="Available")
    created_at = Column(DateTime, default=datetime.utcnow)

class RadiologyTest(Base):
    __tablename__ = "radiology_tests"
    __table_args__ = {"schema": "radiology"}

    radiology_test_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_code = Column(String(100), unique=True, nullable=False)
    test_name = Column(String(255), nullable=False)
    modality_id = Column(UUID(as_uuid=True), ForeignKey("radiology.imaging_modalities.modality_id"), nullable=False)
    price = Column(Numeric(14, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RadiologyOrderStatus(Base):
    __tablename__ = "radiology_order_statuses"
    __table_args__ = {"schema": "radiology"}

    radiology_order_status_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class RadiologyPriority(Base):
    __tablename__ = "radiology_priorities"
    __table_args__ = {"schema": "radiology"}

    priority_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    priority_name = Column(String(100), unique=True, nullable=False)
    priority_level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class RadiologyOrder(Base):
    __tablename__ = "radiology_orders"
    __table_args__ = {"schema": "radiology"}

    radiology_order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(100), unique=True, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    encounter_id = Column(UUID(as_uuid=True), nullable=True)
    doctor_id = Column(UUID(as_uuid=True), nullable=True)
    radiology_order_status_id = Column(UUID(as_uuid=True), ForeignKey("radiology.radiology_order_statuses.radiology_order_status_id"), nullable=True)
    priority_id = Column(UUID(as_uuid=True), ForeignKey("radiology.radiology_priorities.priority_id"), nullable=True)
    clinical_indication = Column(Text, nullable=True)
    ordered_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RadiologyOrderItem(Base):
    __tablename__ = "radiology_order_items"
    __table_args__ = {"schema": "radiology"}

    order_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    radiology_order_id = Column(UUID(as_uuid=True), ForeignKey("radiology.radiology_orders.radiology_order_id", ondelete="CASCADE"), nullable=False)
    radiology_test_id = Column(UUID(as_uuid=True), ForeignKey("radiology.radiology_tests.radiology_test_id"), nullable=False)
    order_status = Column(String(100), default="Ordered")
    ordered_at = Column(DateTime, default=datetime.utcnow)

class RadiologyAppointment(Base):
    __tablename__ = "radiology_appointments"
    __table_args__ = {"schema": "radiology"}

    radiology_appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("radiology.radiology_order_items.order_item_id", ondelete="CASCADE"), nullable=False)
    imaging_room_id = Column(UUID(as_uuid=True), ForeignKey("radiology.imaging_rooms.imaging_room_id"), nullable=False)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    appointment_status = Column(String(100), default="Scheduled")
    created_at = Column(DateTime, default=datetime.utcnow)

class ImagingStudy(Base):
    __tablename__ = "imaging_studies"
    __table_args__ = {"schema": "radiology"}

    study_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_instance_uid = Column(String(255), unique=True, nullable=False)
    radiology_appointment_id = Column(UUID(as_uuid=True), ForeignKey("radiology.radiology_appointments.radiology_appointment_id"), nullable=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    modality_id = Column(UUID(as_uuid=True), ForeignKey("radiology.imaging_modalities.modality_id"), nullable=True)
    study_description = Column(Text, nullable=True)
    study_date = Column(DateTime, default=datetime.utcnow)
    accession_number = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Radiologist(Base):
    __tablename__ = "radiologists"
    __table_args__ = {"schema": "radiology"}

    radiologist_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), nullable=True)
    specialization = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RadiologyReport(Base):
    __tablename__ = "radiology_reports"
    __table_args__ = {"schema": "radiology"}

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id = Column(UUID(as_uuid=True), ForeignKey("radiology.imaging_studies.study_id", ondelete="CASCADE"), nullable=False)
    radiologist_id = Column(UUID(as_uuid=True), ForeignKey("radiology.radiologists.radiologist_id"), nullable=True)
    report_text = Column(Text, nullable=False)
    impression = Column(Text, nullable=False)
    report_status = Column(String(100), default="Final")
    reported_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
