import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, Time
from sqlalchemy.dialects.postgresql import UUID
from app.models.employee import Base

# ==================== EMERGENCY ====================
class EmergencyTriageLevel(Base):
    __tablename__ = "emergency_triage_levels"
    __table_args__ = {"schema": "emergency"}

    triage_level_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_name = Column(String(100), nullable=False)
    severity_rank = Column(Integer, nullable=False)
    response_time_minutes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmergencyArrival(Base):
    __tablename__ = "emergency_arrivals"
    __table_args__ = {"schema": "emergency"}

    emergency_arrival_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    arrival_mode = Column(String(100), default="Walk-in")
    arrival_time = Column(DateTime, default=datetime.utcnow)
    brought_by = Column(String(255), nullable=True)
    arrival_condition = Column(Text, nullable=False)
    is_unidentified = Column(Boolean, default=False, nullable=False)
    temp_tag = Column(String(50), nullable=True)
    incident_code = Column(String(50), nullable=True)
    is_mci = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MCIEvent(Base):
    __tablename__ = "mci_events"
    __table_args__ = {"schema": "emergency"}

    mci_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_code = Column(String(50), unique=True, nullable=False)
    incident_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    declared_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    declared_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)

class EmergencyTriageAssessment(Base):
    __tablename__ = "emergency_triage_assessments"
    __table_args__ = {"schema": "emergency"}

    triage_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    emergency_arrival_id = Column(UUID(as_uuid=True), ForeignKey("emergency.emergency_arrivals.emergency_arrival_id", ondelete="CASCADE"), nullable=False)
    triage_level_id = Column(UUID(as_uuid=True), ForeignKey("emergency.emergency_triage_levels.triage_level_id"), nullable=True)
    chief_complaint = Column(Text, nullable=False)
    vital_signs_summary = Column(Text, nullable=True)
    trauma_bay_code = Column(String(100), nullable=True)
    assessed_by = Column(UUID(as_uuid=True), nullable=True)
    assessed_at = Column(DateTime, default=datetime.utcnow)

# ==================== NURSING ====================
class NursingRound(Base):
    __tablename__ = "nursing_rounds"
    __table_args__ = {"schema": "nursing"}

    round_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    nurse_id = Column(UUID(as_uuid=True), nullable=True)
    round_time = Column(DateTime, default=datetime.utcnow)
    round_notes = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MedicationAdministrationRecord(Base):
    __tablename__ = "medication_administration_records"
    __table_args__ = {"schema": "nursing"}

    mar_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    prescription_item_id = Column(UUID(as_uuid=True), nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    administration_status = Column(String(40), default="Due")
    frequency_code = Column(String(20), default="PRN")
    scheduled_hour = Column(String(10), nullable=True)
    pre_admin_vitals_required = Column(Boolean, default=False, nullable=False)
    vitals_recorded = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NursingMedicationLog(Base):
    __tablename__ = "medication_administration_logs"
    __table_args__ = {"schema": "nursing"}

    administration_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mar_id = Column(UUID(as_uuid=True), nullable=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    prescription_item_id = Column(UUID(as_uuid=True), nullable=True)
    medicine_name = Column(String(255), nullable=False)
    dosage_given = Column(String(255), nullable=False)
    route = Column(String(100), default="Oral")
    administered_by = Column(UUID(as_uuid=True), nullable=True)
    administered_at = Column(DateTime, default=datetime.utcnow)
    administration_notes = Column(Text, nullable=True)
    administration_status = Column(String(40), default="Administered")
    exception_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==================== SURGERY ====================
class SurgeryRequest(Base):
    __tablename__ = "surgery_requests"
    __table_args__ = {"schema": "surgery"}

    surgery_request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    requested_by = Column(UUID(as_uuid=True), nullable=True)
    procedure_name = Column(String(255), nullable=False)
    procedure_code = Column(String(100), nullable=True)
    request_priority = Column(String(100), default="Elective")
    request_reason = Column(Text, nullable=True)
    requested_date = Column(DateTime, default=datetime.utcnow)
    request_status = Column(String(100), default="Requested")
    encounter_id = Column(UUID(as_uuid=True), nullable=True)
    admission_id = Column(UUID(as_uuid=True), nullable=True)
    estimated_charge = Column(Numeric(14, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class SurgerySchedule(Base):
    __tablename__ = "surgery_scheduling"
    __table_args__ = {"schema": "surgery"}

    surgery_schedule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surgery_request_id = Column(UUID(as_uuid=True), ForeignKey("surgery.surgery_requests.surgery_request_id", ondelete="CASCADE"), nullable=False)
    ot_room_number = Column(String(100), default="OT Suite 1")
    primary_surgeon_id = Column(UUID(as_uuid=True), nullable=True)
    anesthesiologist_name = Column(String(255), nullable=True)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    schedule_status = Column(String(100), default="Scheduled")  # Scheduled, In Progress, Completed
    surgical_findings = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    anesthesia_type = Column(String(100), nullable=True)
    complications = Column(Text, nullable=True)
    completed_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OTCSSDTray(Base):
    __tablename__ = "ot_cssd_trays"
    __table_args__ = {"schema": "surgery"}

    tray_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surgery_schedule_id = Column(UUID(as_uuid=True), ForeignKey("surgery.surgery_scheduling.surgery_schedule_id", ondelete="CASCADE"), nullable=False)
    tray_name = Column(String(150), nullable=False)
    tray_barcode = Column(String(100), nullable=True)
    autoclave_batch_number = Column(String(100), nullable=False)
    sterilization_date = Column(Date, nullable=False)
    sterile_expiry_date = Column(Date, nullable=False)
    is_indicator_passed = Column(Boolean, default=True, nullable=False)
    verified_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OTImplant(Base):
    __tablename__ = "ot_implants"
    __table_args__ = {"schema": "surgery"}

    implant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surgery_schedule_id = Column(UUID(as_uuid=True), ForeignKey("surgery.surgery_scheduling.surgery_schedule_id", ondelete="CASCADE"), nullable=False)
    implant_name = Column(String(200), nullable=False)
    manufacturer = Column(String(150), nullable=False)
    serial_number = Column(String(100), nullable=False)
    lot_number = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OTRecoveryRecord(Base):
    __tablename__ = "ot_recovery_records"
    __table_args__ = {"schema": "surgery"}

    recovery_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    surgery_schedule_id = Column(UUID(as_uuid=True), ForeignKey("surgery.surgery_scheduling.surgery_schedule_id"), unique=True, nullable=False)
    recovery_status = Column(String(40), nullable=False)
    pain_score = Column(Integer, nullable=False)
    observations = Column(Text, nullable=False)
    disposition = Column(String(40), nullable=False)
    aldrete_score = Column(Integer, nullable=True)
    aldrete_criteria = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# ==================== BLOOD BANK ====================
class BloodGroupType(Base):
    __tablename__ = "blood_group_types"
    __table_args__ = {"schema": "blood_bank"}

    blood_group_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String(10), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class BloodComponentType(Base):
    __tablename__ = "blood_component_types"
    __table_args__ = {"schema": "blood_bank"}

    blood_component_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_name = Column(String(100), unique=True, nullable=False)
    shelf_life_days = Column(Integer, default=35)
    storage_temperature = Column(String(50), default="2-6C")
    unit_price = Column(Numeric(14, 2), default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)

class BloodUnit(Base):
    __tablename__ = "blood_units"
    __table_args__ = {"schema": "blood_bank"}

    blood_unit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blood_donation_id = Column(UUID(as_uuid=True), nullable=True)
    blood_component_type_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_component_types.blood_component_type_id"), nullable=True)
    unit_number = Column(String(100), unique=True, nullable=False)
    blood_group_type_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_group_types.blood_group_type_id"), nullable=True)
    volume_ml = Column(Integer, default=450)
    collection_date = Column(Date, default=date.today)
    expiry_date = Column(Date, nullable=False)
    status = Column(String(30), default="available")  # available, crossmatched, transfused, discarded
    storage_location = Column(String(100), default="Main Blood Refrigerator 1")
    discard_reason = Column(Text, nullable=True)
    discarded_by = Column(UUID(as_uuid=True), nullable=True)
    discarded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class BloodRequest(Base):
    __tablename__ = "blood_requests"
    __table_args__ = {"schema": "blood_bank"}

    blood_request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    requested_by = Column(UUID(as_uuid=True), nullable=True)
    blood_group_type_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_group_types.blood_group_type_id"), nullable=True)
    blood_component_type_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_component_types.blood_component_type_id"), nullable=True)
    units_requested = Column(Integer, default=1)
    urgency = Column(String(20), default="routine")
    clinical_indication = Column(Text, nullable=True)
    status = Column(String(30), default="pending")  # pending, crossmatched, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

class CrossMatchTest(Base):
    __tablename__ = "cross_match_tests"
    __table_args__ = {"schema": "blood_bank"}

    cross_match_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blood_request_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_requests.blood_request_id"), nullable=False)
    blood_unit_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_units.blood_unit_id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id"), nullable=False)
    result = Column(String(20), default="Compatible")  # Compatible, Incompatible
    tested_by = Column(UUID(as_uuid=True), nullable=True)
    tested_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class BloodTransfusion(Base):
    __tablename__ = "blood_transfusions"
    __table_args__ = {"schema": "blood_bank"}

    transfusion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blood_request_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_requests.blood_request_id"), nullable=False)
    blood_unit_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_units.blood_unit_id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id"), nullable=False)
    administered_by = Column(UUID(as_uuid=True), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    volume_transfused = Column(Integer, default=350)
    status = Column(String(30), default="completed")
    notes = Column(Text, nullable=True)
    adverse_reaction = Column(Boolean, default=False)
    reaction_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class BloodDonor(Base):
    __tablename__ = "blood_donors"
    __table_args__ = {"schema": "blood_bank"}

    blood_donor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    donor_number = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    blood_group_type_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_group_types.blood_group_type_id"), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    last_donation_date = Column(Date, nullable=True)
    total_donations = Column(Integer, default=0)
    is_eligible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class DonorEligibilityCheck(Base):
    __tablename__ = "donor_eligibility_checks"
    __table_args__ = {"schema": "blood_bank"}

    eligibility_check_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blood_donor_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_donors.blood_donor_id", ondelete="CASCADE"), nullable=False)
    check_date = Column(DateTime, default=datetime.utcnow)
    hemoglobin = Column(Numeric(5, 2), nullable=True)
    blood_pressure = Column(String(20), nullable=True)
    weight = Column(Numeric(5, 2), nullable=True)
    temperature = Column(Numeric(4, 1), nullable=True)
    pulse = Column(Integer, nullable=True)
    is_eligible = Column(Boolean, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    checked_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class BloodDonation(Base):
    __tablename__ = "blood_donations"
    __table_args__ = {"schema": "blood_bank"}

    blood_donation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    blood_donor_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_donors.blood_donor_id"), nullable=False)
    donation_type = Column(String(50), default="Voluntary")
    donation_date = Column(DateTime, default=datetime.utcnow)
    bag_number = Column(String(100), unique=True, nullable=False)
    volume_ml = Column(Integer, default=450)
    collected_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(30), default="collected")  # collected, separated, tested, completed
    created_at = Column(DateTime, default=datetime.utcnow)

class BloodUnitTest(Base):
    __tablename__ = "blood_unit_tests"
    __table_args__ = {"schema": "blood_bank"}

    unit_test_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blood_unit_id = Column(UUID(as_uuid=True), ForeignKey("blood_bank.blood_units.blood_unit_id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String(100), nullable=False)
    result = Column(String(30), nullable=False, default="Negative")  # Negative, Reactive, Indeterminate
    tested_by = Column(UUID(as_uuid=True), nullable=True)
    tested_at = Column(DateTime, default=datetime.utcnow)
    verified_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

