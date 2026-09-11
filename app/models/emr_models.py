import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from app.models.employee import Base


# ============================================================
# EMR MASTER LOOKUP TABLES
# ============================================================

class EncounterType(Base):
    __tablename__ = "encounter_types"
    __table_args__ = {"schema": "electronic_medical_records"}

    encounter_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DiagnosisType(Base):
    __tablename__ = "diagnosis_types"
    __table_args__ = {"schema": "electronic_medical_records"}

    diagnosis_type_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnosis_type_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SeverityLevel(Base):
    __tablename__ = "severity_levels"
    __table_args__ = {"schema": "electronic_medical_records"}

    severity_level_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    severity_name = Column(String(100), unique=True, nullable=False)
    severity_rank = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# PATIENT ENCOUNTERS (Clinical Visit Record)
# ============================================================

class PatientEncounter(Base):
    __tablename__ = "patient_encounters"
    __table_args__ = {"schema": "electronic_medical_records"}

    encounter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    encounter_number = Column(String(100), unique=True, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointment.appointments.appointment_id", ondelete="SET NULL"), nullable=True)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctor.doctors.doctor_id", ondelete="RESTRICT"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("core.departments.department_id"), nullable=True)
    encounter_type_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.encounter_types.encounter_type_id"), nullable=True)
    encounter_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    chief_complaint = Column(Text, nullable=True)
    clinical_summary = Column(Text, nullable=True)
    encounter_status = Column(String(100), default="In Progress")  # In Progress | Completed | Cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)


# ============================================================
# CLINICAL NOTES (SOAP)
# ============================================================

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"
    __table_args__ = {"schema": "electronic_medical_records"}

    note_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.patient_encounters.encounter_id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), nullable=False)
    note_type = Column(String(100), default="SOAP")  # SOAP | Progress | Discharge | Nursing
    note_text = Column(Text, nullable=False)
    is_confidential = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Compatibility name used by the doctor-portal test suite and older callers.
SOAPNote = ClinicalNote


# ============================================================
# VITAL SIGNS
# ============================================================

class VitalSign(Base):
    __tablename__ = "vital_signs"
    __table_args__ = {"schema": "electronic_medical_records"}

    vital_sign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.patient_encounters.encounter_id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    temperature = Column(Numeric(5, 2), nullable=True)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    oxygen_saturation = Column(Numeric(5, 2), nullable=True)
    height_cm = Column(Numeric(5, 2), nullable=True)
    weight_kg = Column(Numeric(5, 2), nullable=True)
    bmi = Column(Numeric(5, 2), nullable=True)
    pain_score = Column(Integer, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# DIAGNOSES (ICD-10)
# ============================================================

class Diagnosis(Base):
    __tablename__ = "diagnoses"
    __table_args__ = {"schema": "electronic_medical_records"}

    diagnosis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.patient_encounters.encounter_id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), nullable=False)
    diagnosis_type_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.diagnosis_types.diagnosis_type_id"), nullable=True)
    severity_level_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.severity_levels.severity_level_id"), nullable=True)
    diagnosis_code = Column(String(50), nullable=False)
    diagnosis_name = Column(String(255), nullable=False)
    diagnosis_description = Column(Text, nullable=True)
    diagnosed_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# MEDICATION RECORDS / PRESCRIPTIONS
# ============================================================

class MedicationRecord(Base):
    __tablename__ = "medication_records"
    __table_args__ = {"schema": "electronic_medical_records"}

    medication_record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.patient_encounters.encounter_id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), nullable=False)
    medicine_name = Column(String(255), nullable=False)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.drugs.drug_id"), nullable=True)
    quantity_prescribed = Column(Numeric(14, 2), nullable=True)
    medication_status = Column(String(40), default="Draft")
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    route = Column(String(100), default="Oral")
    duration = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Compatibility name retained for older doctor-portal callers.
Prescription = MedicationRecord


# ============================================================
# ALLERGY RECORDS
# ============================================================

class AllergyRecord(Base):
    __tablename__ = "allergy_records"
    __table_args__ = {"schema": "electronic_medical_records"}

    allergy_record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    allergen_name = Column(String(255), nullable=False)
    allergy_type = Column(String(100), default="Drug")
    reaction_description = Column(Text, nullable=True)
    severity_level_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.severity_levels.severity_level_id"), nullable=True)
    diagnosed_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# SYMPTOMS
# ============================================================

class Symptom(Base):
    __tablename__ = "symptoms"
    __table_args__ = {"schema": "electronic_medical_records"}

    symptom_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.patient_encounters.encounter_id", ondelete="CASCADE"), nullable=False)
    symptom_name = Column(String(255), nullable=False)
    symptom_duration = Column(String(100), nullable=True)
    severity_level_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.severity_levels.severity_level_id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# REFERRALS
# ============================================================

class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = {"schema": "electronic_medical_records"}

    referral_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.patient_encounters.encounter_id", ondelete="CASCADE"), nullable=False)
    referring_doctor_id = Column(UUID(as_uuid=True), nullable=True)
    referred_department_id = Column(UUID(as_uuid=True), nullable=True)
    referred_doctor_id = Column(UUID(as_uuid=True), nullable=True)
    referral_reason = Column(Text, nullable=True)
    referral_status = Column(String(100), default="Pending")  # Pending | Accepted | Completed
    referred_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# TELEMEDICINE TABLES
# ============================================================

class TelemedicineProvider(Base):
    __tablename__ = "telemedicine_providers"
    __table_args__ = {"schema": "telemedicine"}

    provider_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctor.doctors.doctor_id", ondelete="CASCADE"), nullable=False)
    provider_status = Column(String(50), default="Active")
    years_of_experience = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VirtualAppointment(Base):
    __tablename__ = "virtual_appointments"
    __table_args__ = {"schema": "telemedicine"}

    virtual_appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("telemedicine.telemedicine_providers.provider_id", ondelete="CASCADE"), nullable=False)
    appointment_datetime = Column(DateTime, nullable=False)
    consultation_link = Column(Text, nullable=True)
    meeting_platform = Column(String(100), default="HMS Telehealth")
    chief_complaint = Column(Text, nullable=True)
    status = Column(String(50), default="Scheduled")
    emr_encounter_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.patient_encounters.encounter_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VideoConsultationSession(Base):
    __tablename__ = "video_consultation_sessions"
    __table_args__ = {"schema": "telemedicine"}

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    virtual_appointment_id = Column(UUID(as_uuid=True), ForeignKey("telemedicine.virtual_appointments.virtual_appointment_id", ondelete="CASCADE"), nullable=False)
    session_start_time = Column(DateTime, nullable=True)
    session_end_time = Column(DateTime, nullable=True)
    session_status = Column(String(50), default="Scheduled")  # Scheduled | Active | Completed | Missed


class SessionNote(Base):
    __tablename__ = "session_notes"
    __table_args__ = {"schema": "telemedicine"}

    note_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("telemedicine.video_consultation_sessions.session_id", ondelete="CASCADE"), nullable=False)
    clinical_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
