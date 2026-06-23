-- =====================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM
-- CATEGORY: PATIENT MANAGEMENT
-- PostgreSQL Compatible
-- =====================================================

-- =====================================================
-- EXTENSIONS
-- =====================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS patient;
SET search_path TO patient, public;

-- =====================================================
-- MASTER TABLES
-- =====================================================

CREATE TABLE genders (
    gender_id BIGSERIAL PRIMARY KEY,
    gender_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE blood_groups (
    blood_group_id BIGSERIAL PRIMARY KEY,
    blood_group_name VARCHAR(10) UNIQUE NOT NULL
);

CREATE TABLE marital_statuses (
    marital_status_id BIGSERIAL PRIMARY KEY,
    marital_status_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE patient_statuses (
    status_id BIGSERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE insurance_providers (
    provider_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    provider_name VARCHAR(255) NOT NULL,
    provider_code VARCHAR(100) UNIQUE,

    contact_number VARCHAR(20),
    email VARCHAR(255),
    address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_types (
    document_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    document_type_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE consent_types (
    consent_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    consent_name VARCHAR(255) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PATIENTS
-- =====================================================

CREATE TABLE patients (
    patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tenant_id UUID,

    patient_code VARCHAR(50) UNIQUE NOT NULL,
    mrn VARCHAR(50) UNIQUE NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,

    date_of_birth DATE NOT NULL,

    gender_id BIGINT NOT NULL,
    blood_group_id BIGINT,
    marital_status_id BIGINT,
    status_id BIGINT NOT NULL,

    deceased_flag BOOLEAN DEFAULT FALSE,
    deceased_date TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_by UUID,
    updated_by UUID,

    deleted_at TIMESTAMP NULL,

    CONSTRAINT fk_patient_gender
        FOREIGN KEY (gender_id)
        REFERENCES genders(gender_id),

    CONSTRAINT fk_patient_blood_group
        FOREIGN KEY (blood_group_id)
        REFERENCES blood_groups(blood_group_id),

    CONSTRAINT fk_patient_marital_status
        FOREIGN KEY (marital_status_id)
        REFERENCES marital_statuses(marital_status_id),

    CONSTRAINT fk_patient_status
        FOREIGN KEY (status_id)
        REFERENCES patient_statuses(status_id)
);

-- =====================================================
-- PATIENT PROFILES
-- =====================================================

CREATE TABLE patient_profiles (
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID UNIQUE NOT NULL,

    occupation VARCHAR(255),
    nationality VARCHAR(100),
    religion VARCHAR(100),
    ethnicity VARCHAR(100),

    preferred_language VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT IDENTIFIERS
-- =====================================================

CREATE TABLE patient_identifiers (
    identifier_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    identifier_type VARCHAR(100) NOT NULL,
    identifier_value VARCHAR(255) NOT NULL,

    issued_country VARCHAR(100),

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT CONTACTS
-- =====================================================

CREATE TABLE patient_contacts (
    contact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    contact_type VARCHAR(50) NOT NULL,
    contact_value VARCHAR(255) NOT NULL,

    is_primary BOOLEAN DEFAULT FALSE,
    verified_flag BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT ADDRESSES
-- =====================================================

CREATE TABLE patient_addresses (
    address_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    address_type VARCHAR(50),

    line1 VARCHAR(255) NOT NULL,
    line2 VARCHAR(255),

    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),

    postal_code VARCHAR(20),

    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT EMERGENCY CONTACTS
-- =====================================================

CREATE TABLE patient_emergency_contacts (
    emergency_contact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    full_name VARCHAR(255) NOT NULL,
    relationship VARCHAR(100),

    phone VARCHAR(20),
    email VARCHAR(255),

    address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT GUARDIANS
-- =====================================================

CREATE TABLE patient_guardians (
    guardian_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    guardian_name VARCHAR(255) NOT NULL,
    relationship VARCHAR(100),

    phone VARCHAR(20),
    email VARCHAR(255),

    address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT ALLERGIES
-- =====================================================

CREATE TABLE patient_allergies (
    allergy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    allergy_name VARCHAR(255) NOT NULL,
    allergy_type VARCHAR(100),

    severity VARCHAR(50),

    reaction TEXT,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT CONDITIONS
-- =====================================================

CREATE TABLE patient_conditions (
    condition_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    condition_name VARCHAR(255) NOT NULL,

    diagnosis_date DATE,

    status VARCHAR(50),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT MEDICAL HISTORY
-- =====================================================

CREATE TABLE patient_medical_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    disease_name VARCHAR(255),

    diagnosis_date DATE,

    treatment TEXT,

    hospital_name VARCHAR(255),

    doctor_name VARCHAR(255),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT FAMILY HISTORY
-- =====================================================

CREATE TABLE patient_family_history (
    family_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    family_member VARCHAR(100),

    disease_name VARCHAR(255),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT SOCIAL HISTORY
-- =====================================================

CREATE TABLE patient_social_history (
    social_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    smoking_status VARCHAR(100),
    alcohol_use VARCHAR(100),
    drug_use VARCHAR(100),

    occupation VARCHAR(255),

    exercise_frequency VARCHAR(100),

    dietary_preferences TEXT,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT INSURANCE
-- =====================================================

CREATE TABLE patient_insurance (
    insurance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    provider_id UUID NOT NULL,

    policy_number VARCHAR(255) NOT NULL,

    policy_holder_name VARCHAR(255),

    coverage_amount NUMERIC(12,2),

    valid_from DATE,
    valid_to DATE,

    status VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE,

    FOREIGN KEY (provider_id)
        REFERENCES insurance_providers(provider_id)
);

-- =====================================================
-- PATIENT DOCUMENTS
-- =====================================================

CREATE TABLE patient_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    document_type_id UUID,

    file_name VARCHAR(255),
    file_path TEXT NOT NULL,

    mime_type VARCHAR(100),

    file_size BIGINT,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    uploaded_by UUID,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE,

    FOREIGN KEY (document_type_id)
        REFERENCES document_types(document_type_id)
);

-- =====================================================
-- PATIENT PHOTOS
-- =====================================================

CREATE TABLE patient_photos (
    photo_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    photo_path TEXT NOT NULL,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    is_primary BOOLEAN DEFAULT TRUE,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT CONSENTS
-- =====================================================

CREATE TABLE patient_consents (
    consent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    consent_type_id UUID NOT NULL,

    consent_date TIMESTAMP NOT NULL,

    expiry_date TIMESTAMP,

    status VARCHAR(50),

    signed_by VARCHAR(255),

    witness_name VARCHAR(255),

    document_path TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE,

    FOREIGN KEY (consent_type_id)
        REFERENCES consent_types(consent_type_id)
);

-- =====================================================
-- PATIENT PORTAL ACCOUNTS
-- =====================================================

CREATE TABLE patient_portal_accounts (
    portal_account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID UNIQUE NOT NULL,

    username VARCHAR(100) UNIQUE NOT NULL,

    password_hash TEXT NOT NULL,

    last_login TIMESTAMP,

    account_status VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT AUDIT LOGS
-- =====================================================

CREATE TABLE patient_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(100),

    device_info TEXT,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- PATIENT CHANGE HISTORY
-- =====================================================

CREATE TABLE patient_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    changed_field VARCHAR(255),

    old_value TEXT,
    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE CASCADE
);

-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX idx_patients_mrn
ON patients(mrn);

CREATE INDEX idx_patients_name
ON patients(first_name, last_name);

CREATE INDEX idx_patient_contacts_patient
ON patient_contacts(patient_id);

CREATE INDEX idx_patient_addresses_patient
ON patient_addresses(patient_id);

CREATE INDEX idx_patient_documents_patient
ON patient_documents(patient_id);

CREATE INDEX idx_patient_insurance_patient
ON patient_insurance(patient_id);

CREATE INDEX idx_patient_allergies_patient
ON patient_allergies(patient_id);

CREATE INDEX idx_patient_conditions_patient
ON patient_conditions(patient_id);

CREATE INDEX idx_patient_audit_logs_patient
ON patient_audit_logs(patient_id);

-- =====================================================
-- END OF PATIENT MANAGEMENT SCHEMA
-- =====================================================