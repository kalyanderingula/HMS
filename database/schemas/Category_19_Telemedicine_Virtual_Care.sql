
-- CATEGORY 19: TELEMEDICINE & VIRTUAL CARE MANAGEMENT SYSTEM
-- Enterprise HMS Schema (Core Complete Structure)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS telemedicine;
SET search_path TO telemedicine, public;

CREATE TABLE telemedicine_specialties (
    specialty_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specialty_code VARCHAR(50) UNIQUE NOT NULL,
    specialty_name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE telemedicine_services (
    service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_code VARCHAR(50) UNIQUE NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    consultation_type VARCHAR(100),
    duration_minutes INT,
    base_fee NUMERIC(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE telemedicine_providers (
    provider_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id UUID NOT NULL,
    specialty_id UUID REFERENCES telemedicine_specialties(specialty_id),
    provider_status VARCHAR(50),
    years_of_experience INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE virtual_appointments (
    virtual_appointment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL,
    provider_id UUID REFERENCES telemedicine_providers(provider_id),
    appointment_datetime TIMESTAMP,
    consultation_link TEXT,
    meeting_platform VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE video_consultation_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    virtual_appointment_id UUID REFERENCES virtual_appointments(virtual_appointment_id),
    session_start_time TIMESTAMP,
    session_end_time TIMESTAMP,
    session_status VARCHAR(50)
);

CREATE TABLE session_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES video_consultation_sessions(session_id),
    clinical_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE remote_patient_monitoring_devices (
    device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_name VARCHAR(255),
    manufacturer VARCHAR(255),
    model_number VARCHAR(255),
    device_type VARCHAR(100)
);

CREATE TABLE patient_device_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    device_id UUID REFERENCES remote_patient_monitoring_devices(device_id),
    assigned_date DATE
);

CREATE TABLE device_readings (
    reading_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID REFERENCES patient_device_assignments(assignment_id),
    reading_type VARCHAR(100),
    reading_value NUMERIC(12,2),
    reading_timestamp TIMESTAMP
);

CREATE TABLE telemedicine_encounters (
    encounter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    provider_id UUID REFERENCES telemedicine_providers(provider_id),
    session_id UUID REFERENCES video_consultation_sessions(session_id),
    encounter_datetime TIMESTAMP,
    clinical_summary TEXT
);

CREATE TABLE encounter_diagnoses (
    diagnosis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    encounter_id UUID REFERENCES telemedicine_encounters(encounter_id),
    diagnosis_code VARCHAR(50),
    diagnosis_name VARCHAR(255)
);

CREATE TABLE encounter_prescriptions (
    encounter_prescription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    encounter_id UUID REFERENCES telemedicine_encounters(encounter_id),
    medication_name VARCHAR(255),
    dosage VARCHAR(255),
    duration_days INT
);

CREATE TABLE e_prescriptions (
    prescription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    encounter_id UUID REFERENCES telemedicine_encounters(encounter_id),
    prescription_number VARCHAR(100),
    issued_at TIMESTAMP
);

CREATE TABLE e_prescription_items (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prescription_id UUID REFERENCES e_prescriptions(prescription_id),
    medication_name VARCHAR(255),
    dosage VARCHAR(255),
    frequency VARCHAR(255)
);

CREATE TABLE patient_portal_sessions (
    portal_session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    login_time TIMESTAMP,
    logout_time TIMESTAMP
);

CREATE TABLE secure_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id UUID,
    receiver_id UUID,
    message_body TEXT,
    sent_at TIMESTAMP
);

CREATE TABLE telemedicine_billing (
    billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    virtual_appointment_id UUID REFERENCES virtual_appointments(virtual_appointment_id),
    billing_amount NUMERIC(12,2),
    payment_status VARCHAR(50)
);

CREATE TABLE telemedicine_claims (
    claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    billing_id UUID REFERENCES telemedicine_billing(billing_id),
    insurance_provider VARCHAR(255),
    claim_status VARCHAR(50)
);

CREATE TABLE telemedicine_audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(255),
    action_type VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
