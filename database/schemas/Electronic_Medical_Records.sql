-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 5: EMR / EHR (Electronic Medical Records)
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS electronic_medical_records;
SET search_path TO electronic_medical_records, public;

-- =========================================================
-- MASTER TABLES
-- =========================================================

CREATE TABLE encounter_types (
    encounter_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_name VARCHAR(100) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- OPD
-- IPD
-- Emergency
-- Teleconsultation


CREATE TABLE diagnosis_types (
    diagnosis_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    diagnosis_type_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Primary
-- Secondary
-- Differential


CREATE TABLE severity_levels (
    severity_level_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    severity_name VARCHAR(100) UNIQUE NOT NULL,

    severity_rank INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- PATIENT ENCOUNTERS
-- =========================================================

CREATE TABLE patient_encounters (
    encounter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tenant_id UUID,

    encounter_number VARCHAR(100) UNIQUE NOT NULL,

    patient_id UUID NOT NULL,

    appointment_id UUID,

    doctor_id UUID NOT NULL,

    department_id UUID,

    encounter_type_id UUID,

    encounter_date TIMESTAMP NOT NULL,

    chief_complaint TEXT,

    clinical_summary TEXT,

    encounter_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_by UUID,
    updated_by UUID,

    deleted_at TIMESTAMP NULL,

    FOREIGN KEY (encounter_type_id)
        REFERENCES encounter_types(encounter_type_id)
);

-- patient_id references patients(patient_id)
-- appointment_id references appointments(appointment_id)
-- doctor_id references doctors(doctor_id)
-- department_id references departments(department_id)


-- =========================================================
-- CLINICAL NOTES
-- =========================================================

CREATE TABLE clinical_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    note_type VARCHAR(100),

    note_text TEXT NOT NULL,

    is_confidential BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- VITAL SIGNS
-- =========================================================

CREATE TABLE vital_signs (
    vital_sign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    temperature NUMERIC(5,2),

    systolic_bp INT,
    diastolic_bp INT,

    heart_rate INT,

    respiratory_rate INT,

    oxygen_saturation NUMERIC(5,2),

    height_cm NUMERIC(5,2),
    weight_kg NUMERIC(5,2),

    bmi NUMERIC(5,2),

    pain_score INT,

    recorded_by UUID,

    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DIAGNOSES
-- =========================================================

CREATE TABLE diagnoses (
    diagnosis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    diagnosis_type_id UUID,

    severity_level_id UUID,

    diagnosis_code VARCHAR(50),

    diagnosis_name VARCHAR(255),

    diagnosis_description TEXT,

    diagnosed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE,

    FOREIGN KEY (diagnosis_type_id)
        REFERENCES diagnosis_types(diagnosis_type_id),

    FOREIGN KEY (severity_level_id)
        REFERENCES severity_levels(severity_level_id)
);

-- =========================================================
-- SYMPTOMS
-- =========================================================

CREATE TABLE symptoms (
    symptom_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    symptom_name VARCHAR(255),

    symptom_duration VARCHAR(100),

    severity_level_id UUID,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE,

    FOREIGN KEY (severity_level_id)
        REFERENCES severity_levels(severity_level_id)
);

-- =========================================================
-- CARE PLANS
-- =========================================================

CREATE TABLE care_plans (
    care_plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    care_plan_title VARCHAR(255),

    care_plan_description TEXT,

    goals TEXT,

    instructions TEXT,

    start_date DATE,
    end_date DATE,

    care_plan_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- PROCEDURES
-- =========================================================

CREATE TABLE procedures (
    procedure_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    procedure_code VARCHAR(100),

    procedure_name VARCHAR(255),

    procedure_description TEXT,

    performed_at TIMESTAMP,

    outcome_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- IMMUNIZATIONS
-- =========================================================

CREATE TABLE immunizations (
    immunization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    vaccine_name VARCHAR(255),

    manufacturer VARCHAR(255),

    batch_number VARCHAR(100),

    administered_by UUID,

    administered_at TIMESTAMP,

    next_due_date DATE,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- ALLERGY RECORDS
-- =========================================================

CREATE TABLE allergy_records (
    allergy_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    allergen_name VARCHAR(255),

    allergy_type VARCHAR(100),

    reaction_description TEXT,

    severity_level_id UUID,

    diagnosed_at TIMESTAMP,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (severity_level_id)
        REFERENCES severity_levels(severity_level_id)
);

-- =========================================================
-- MEDICATION RECORDS
-- =========================================================

CREATE TABLE medication_records (
    medication_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    medicine_name VARCHAR(255),

    dosage VARCHAR(100),

    frequency VARCHAR(100),

    duration VARCHAR(100),

    route VARCHAR(100),

    instructions TEXT,

    started_at TIMESTAMP,
    ended_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- NURSING NOTES
-- =========================================================

CREATE TABLE nursing_notes (
    nursing_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    nurse_id UUID NOT NULL,

    nursing_note TEXT,

    observation_time TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- TREATMENT PLANS
-- =========================================================

CREATE TABLE treatment_plans (
    treatment_plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    treatment_title VARCHAR(255),

    treatment_description TEXT,

    treatment_goals TEXT,

    treatment_status VARCHAR(100),

    start_date DATE,
    end_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- CLINICAL DOCUMENTS
-- =========================================================

CREATE TABLE clinical_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    document_name VARCHAR(255),

    document_type VARCHAR(100),

    file_path TEXT NOT NULL,

    mime_type VARCHAR(100),

    file_size BIGINT,

    uploaded_by UUID,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- REFERRALS
-- =========================================================

CREATE TABLE referrals (
    referral_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    referring_doctor_id UUID,

    referred_department_id UUID,

    referred_doctor_id UUID,

    referral_reason TEXT,

    referral_status VARCHAR(100),

    referred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DISCHARGE SUMMARIES
-- =========================================================

CREATE TABLE discharge_summaries (
    discharge_summary_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    admission_date DATE,
    discharge_date DATE,

    discharge_condition TEXT,

    discharge_instructions TEXT,

    followup_instructions TEXT,

    summary_document_path TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- CLINICAL ALERTS
-- =========================================================

CREATE TABLE clinical_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    encounter_id UUID,

    alert_type VARCHAR(100),

    alert_message TEXT,

    severity_level_id UUID,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
        ON DELETE CASCADE,

    FOREIGN KEY (severity_level_id)
        REFERENCES severity_levels(severity_level_id)
);

-- =========================================================
-- EMR AUDIT LOGS
-- =========================================================

CREATE TABLE emr_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID,

    patient_id UUID NOT NULL,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(100),

    device_info TEXT
);

-- =========================================================
-- EMR CHANGE HISTORY
-- =========================================================

CREATE TABLE emr_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    encounter_id UUID,

    changed_table VARCHAR(255),

    changed_field VARCHAR(255),

    old_value TEXT,
    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_patient_encounters_patient
ON patient_encounters(patient_id);

CREATE INDEX idx_patient_encounters_doctor
ON patient_encounters(doctor_id);

CREATE INDEX idx_patient_encounters_date
ON patient_encounters(encounter_date);

CREATE INDEX idx_clinical_notes_encounter
ON clinical_notes(encounter_id);

CREATE INDEX idx_vital_signs_encounter
ON vital_signs(encounter_id);

CREATE INDEX idx_diagnoses_encounter
ON diagnoses(encounter_id);

CREATE INDEX idx_symptoms_encounter
ON symptoms(encounter_id);

CREATE INDEX idx_care_plans_encounter
ON care_plans(encounter_id);

CREATE INDEX idx_procedures_encounter
ON procedures(encounter_id);

CREATE INDEX idx_medication_records_encounter
ON medication_records(encounter_id);

CREATE INDEX idx_nursing_notes_encounter
ON nursing_notes(encounter_id);

CREATE INDEX idx_treatment_plans_encounter
ON treatment_plans(encounter_id);

CREATE INDEX idx_clinical_documents_encounter
ON clinical_documents(encounter_id);

CREATE INDEX idx_referrals_encounter
ON referrals(encounter_id);

CREATE INDEX idx_discharge_summaries_encounter
ON discharge_summaries(encounter_id);

CREATE INDEX idx_clinical_alerts_patient
ON clinical_alerts(patient_id);

CREATE INDEX idx_emr_audit_logs_patient
ON emr_audit_logs(patient_id);

-- =========================================================
-- HIGH-LEVEL RELATIONSHIP FLOW
-- =========================================================

/*

patient_encounters
│
├── clinical_notes
├── vital_signs
├── diagnoses
├── symptoms
├── care_plans
├── procedures
├── medication_records
├── nursing_notes
├── treatment_plans
├── clinical_documents
├── referrals
├── discharge_summaries
├── clinical_alerts
├── emr_audit_logs
└── emr_change_history

patients
│
├── immunizations
├── allergy_records
└── clinical_alerts

*/

-- =========================================================
-- END OF EMR / EHR SCHEMA
-- =========================================================