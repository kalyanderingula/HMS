import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.employee import Base

class LabDepartment(Base):
    __tablename__ = "lab_departments"
    __table_args__ = {"schema": "laboratory"}

    lab_department_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_code = Column(String(100), unique=True, nullable=False)
    department_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabTestCategory(Base):
    __tablename__ = "lab_test_categories"
    __table_args__ = {"schema": "laboratory"}

    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabTestSubcategory(Base):
    __tablename__ = "lab_test_subcategories"
    __table_args__ = {"schema": "laboratory"}

    subcategory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_categories.category_id"), nullable=False)
    subcategory_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabTest(Base):
    __tablename__ = "lab_tests"
    __table_args__ = {"schema": "laboratory"}

    test_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_code = Column(String(100), unique=True, nullable=False)
    test_name = Column(String(255), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_categories.category_id"), nullable=True)
    subcategory_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_subcategories.subcategory_id"), nullable=True)
    lab_department_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_departments.lab_department_id"), nullable=True)
    test_method = Column(String(255), nullable=True)
    specimen_type = Column(String(120), nullable=True)
    approving_specialty = Column(String(160), default="Pathology / Laboratory Medicine", nullable=False)
    performing_department = Column(String(160), default="Laboratory", nullable=False)
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
    parameter_code = Column(String(100), nullable=True)
    result_type = Column(String(30), default="NUMERIC", nullable=False)
    unit = Column(String(100), nullable=True)
    specimen_type = Column(String(120), nullable=True)
    method = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    allowed_values = Column(JSONB, nullable=True)
    interpretation = Column(Text, nullable=True)
    normal_range = Column(String(255), nullable=True)
    critical_low = Column(Numeric(14, 2), nullable=True)
    critical_high = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabTestReferenceRange(Base):
    __tablename__ = "lab_test_reference_ranges"
    __table_args__ = {"schema": "laboratory"}

    reference_range_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_parameters.parameter_id", ondelete="CASCADE"), nullable=False)
    gender = Column(String(20), nullable=True)
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    min_value = Column(Numeric(14, 2), nullable=True)
    max_value = Column(Numeric(14, 2), nullable=True)
    reference_text = Column(Text, nullable=True)
    reference_rule = Column(String(40), default="ALL", nullable=False)
    sex = Column(String(20), nullable=True)
    age_min = Column(Numeric(8, 2), nullable=True)
    age_max = Column(Numeric(8, 2), nullable=True)
    age_unit = Column(String(20), default="YEARS", nullable=False)
    pregnancy_status = Column(String(40), nullable=True)
    trimester = Column(Integer, nullable=True)
    gestational_week_min = Column(Integer, nullable=True)
    gestational_week_max = Column(Integer, nullable=True)
    menstrual_phase = Column(String(50), nullable=True)
    clinical_condition = Column(String(120), nullable=True)
    critical_low = Column(Numeric(18, 6), nullable=True)
    critical_high = Column(Numeric(18, 6), nullable=True)
    qualitative_reference = Column(JSONB, nullable=True)
    unit = Column(String(100), nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    source = Column(Text, nullable=True)
    method = Column(String(255), nullable=True)
    analyzer = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    percentile_99 = Column(Numeric(18, 6), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LabParameterInterpretationRule(Base):
    __tablename__ = "lab_parameter_interpretation_rules"
    __table_args__ = {"schema": "laboratory"}

    interpretation_rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_parameters.parameter_id", ondelete="CASCADE"), nullable=False)
    rule_code = Column(String(100), nullable=False)
    label = Column(String(120), nullable=False)
    operator = Column(String(20), nullable=False)
    lower_value = Column(Numeric(18, 6), nullable=True)
    upper_value = Column(Numeric(18, 6), nullable=True)
    qualitative_value = Column(String(255), nullable=True)
    interpretation = Column(Text, nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    source = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
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
    scheduled_at = Column(DateTime, nullable=True)
    booking_source = Column(String(40), default="Doctor", nullable=False)
    referral_type = Column(String(40), default="Doctor Referral", nullable=False)
    referral_doctor_name = Column(String(255), nullable=True)
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
    acknowledged_by = Column(UUID(as_uuid=True), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledgement_notes = Column(Text, nullable=True)

class LabResultParameter(Base):
    __tablename__ = "lab_result_parameters"
    __table_args__ = {"schema": "laboratory"}

    result_parameter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_entry_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_result_entries.result_entry_id", ondelete="CASCADE"), nullable=False)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_parameters.parameter_id"), nullable=False)
    result_value = Column(String(255), nullable=False)
    numeric_value = Column(Numeric(24, 8), nullable=True)
    text_value = Column(Text, nullable=True)
    boolean_value = Column(Boolean, nullable=True)
    coded_value = Column(String(255), nullable=True)
    predicted_value = Column(Numeric(24, 8), nullable=True)
    percent_predicted = Column(Numeric(12, 4), nullable=True)
    lower_limit_normal = Column(Numeric(24, 8), nullable=True)
    z_score = Column(Numeric(12, 4), nullable=True)
    reference_range_id = Column(UUID(as_uuid=True), ForeignKey("laboratory.lab_test_reference_ranges.reference_range_id"), nullable=True)
    interpretation = Column(Text, nullable=True)
    result_flag = Column(String(100), default="Normal")
    created_at = Column(DateTime, default=datetime.utcnow)
