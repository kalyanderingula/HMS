import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.employee import Base

class LabDepartment(Base):
    __tablename__ = "lab_departments"
    __table_args__ = {"schema": "laboratory"}

    lab_department_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_code = Column(String(100), unique=True, nullable=False)
    department_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabTest(Base):
    __tablename__ = "lab_tests"
    __table_args__ = {"schema": "laboratory"}

    test_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_code = Column(String(100), unique=True, nullable=False)
    test_name = Column(String(255), nullable=False)
    test_method = Column(String(255), nullable=True)
    turnaround_time_hours = Column(Integer, default=4)
    sample_volume = Column(String(100), nullable=True)
    fasting_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    price = Column(Numeric(14, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabTestParameter(Base):
    __tablename__ = "lab_test_parameters"
    __table_args__ = {"schema": "laboratory"}

    parameter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_tests.test_id", ondelete="CASCADE"), nullable=False)
    parameter_name = Column(String(255), nullable=False)
    unit = Column(String(100), nullable=True)
    normal_range = Column(String(255), nullable=True)
    critical_low = Column(Numeric(14, 2), nullable=True)
    critical_high = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabOrderStatus(Base):
    __tablename__ = "lab_order_statuses"
    __table_args__ = {"schema": "laboratory"}

    lab_order_status_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabOrderPriority(Base):
    __tablename__ = "lab_order_priorities"
    __table_args__ = {"schema": "laboratory"}

    priority_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    priority_name = Column(String(100), unique=True, nullable=False)
    priority_level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabOrder(Base):
    __tablename__ = "lab_orders"
    __table_args__ = {"schema": "laboratory"}

    lab_order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(100), unique=True, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    encounter_id = Column(UUID(as_uuid=True), nullable=True)
    doctor_id = Column(UUID(as_uuid=True), nullable=True)
    lab_order_status_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_order_statuses.lab_order_status_id"), nullable=True)
    priority_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_order_priorities.priority_id"), nullable=True)
    ordered_at = Column(DateTime, default=datetime.utcnow)
    clinical_notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabOrderItem(Base):
    __tablename__ = "lab_order_items"
    __table_args__ = {"schema": "laboratory"}

    order_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_order_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_orders.lab_order_id", ondelete="CASCADE"), nullable=False)
    test_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_tests.test_id"), nullable=False)
    order_status = Column(String(100), default="Ordered")
    ordered_at = Column(DateTime, default=datetime.utcnow)

class SampleType(Base):
    __tablename__ = "sample_types"
    __table_args__ = {"schema": "laboratory"}

    sample_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_type_name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabSample(Base):
    __tablename__ = "lab_samples"
    __table_args__ = {"schema": "laboratory"}

    sample_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_barcode = Column(String(255), unique=True, nullable=False)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_order_items.order_item_id", ondelete="CASCADE"), nullable=False)
    sample_type_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.sample_types.sample_type_id"), nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)

class LabResultEntry(Base):
    __tablename__ = "lab_result_entries"
    __table_args__ = {"schema": "laboratory"}

    result_entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_order_items.order_item_id", ondelete="CASCADE"), nullable=False)
    technician_id = Column(UUID(as_uuid=True), nullable=True)
    result_status = Column(String(100), default="Entered")
    entered_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)

class LabResultParameter(Base):
    __tablename__ = "lab_result_parameters"
    __table_args__ = {"schema": "laboratory"}

    result_parameter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_entry_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_result_entries.result_entry_id", ondelete="CASCADE"), nullable=False)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_parameters.parameter_id"), nullable=False)
    result_value = Column(String(255), nullable=False)
    result_flag = Column(String(100), default="Normal")
    created_at = Column(DateTime, default=datetime.utcnow)
