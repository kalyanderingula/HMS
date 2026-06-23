-- =====================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM
-- CATEGORY 2: DOCTOR MANAGEMENT
-- PostgreSQL Compatible
-- =====================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS doctor;
SET search_path TO doctor, public;

-- =====================================================
-- MASTER TABLES
-- =====================================================

CREATE TABLE doctor_statuses (
    status_id BIGSERIAL PRIMARY KEY,
    status_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE specializations (
    specialization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    specialization_name VARCHAR(255) UNIQUE NOT NULL,
    specialization_code VARCHAR(100),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_name VARCHAR(255) UNIQUE NOT NULL,
    department_code VARCHAR(100) UNIQUE,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE languages (
    language_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    language_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE leave_types (
    leave_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    leave_type_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE document_types (
    document_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    document_type_name VARCHAR(255) UNIQUE NOT NULL
);

-- =====================================================
-- DOCTORS
-- =====================================================

CREATE TABLE doctors (
    doctor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tenant_id UUID,

    doctor_code VARCHAR(50) UNIQUE NOT NULL,

    employee_id UUID,

    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,

    gender_id BIGINT,

    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),

    primary_specialization_id UUID,

    status_id BIGINT NOT NULL,

    joining_date DATE,

    consultation_experience_years INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_by UUID,
    updated_by UUID,

    deleted_at TIMESTAMP NULL,

    FOREIGN KEY (primary_specialization_id)
        REFERENCES specializations(specialization_id),

    FOREIGN KEY (status_id)
        REFERENCES doctor_statuses(status_id)
);

-- =====================================================
-- DOCTOR PROFILES
-- =====================================================

CREATE TABLE doctor_profiles (
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID UNIQUE NOT NULL,

    biography TEXT,

    nationality VARCHAR(100),
    religion VARCHAR(100),

    profile_photo TEXT,

    linkedin_url TEXT,
    website_url TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR SPECIALIZATIONS
-- =====================================================

CREATE TABLE doctor_specializations (
    doctor_specialization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,
    specialization_id UUID NOT NULL,

    years_of_experience INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE,

    FOREIGN KEY (specialization_id)
        REFERENCES specializations(specialization_id)
);

-- =====================================================
-- DOCTOR DEPARTMENTS
-- =====================================================

CREATE TABLE doctor_departments (
    doctor_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,
    department_id UUID NOT NULL,

    assigned_from DATE,
    assigned_to DATE,

    is_primary BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

-- =====================================================
-- DOCTOR QUALIFICATIONS
-- =====================================================

CREATE TABLE doctor_qualifications (
    qualification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    qualification_name VARCHAR(255) NOT NULL,

    institution_name VARCHAR(255),

    university_name VARCHAR(255),

    country VARCHAR(100),

    graduation_year INT,

    certificate_number VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR LICENSES
-- =====================================================

CREATE TABLE doctor_licenses (
    license_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    license_number VARCHAR(255) UNIQUE NOT NULL,

    issuing_authority VARCHAR(255),

    issue_date DATE,
    expiry_date DATE,

    status VARCHAR(50),

    document_path TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR AVAILABILITY
-- =====================================================

CREATE TABLE doctor_availability (
    availability_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    available_day VARCHAR(20),

    start_time TIME,
    end_time TIME,

    consultation_type VARCHAR(100),

    max_patients_per_slot INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR SCHEDULES
-- =====================================================

CREATE TABLE doctor_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    department_id UUID,

    shift_name VARCHAR(100),

    shift_start TIMESTAMP,
    shift_end TIMESTAMP,

    schedule_status VARCHAR(50),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

-- =====================================================
-- DOCTOR CONSULTATION FEES
-- =====================================================

CREATE TABLE doctor_consultation_fees (
    fee_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    consultation_type VARCHAR(100),

    fee_amount NUMERIC(12,2),

    currency VARCHAR(10),

    effective_from DATE,
    effective_to DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR LANGUAGES
-- =====================================================

CREATE TABLE doctor_languages (
    doctor_language_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,
    language_id UUID NOT NULL,

    proficiency_level VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE,

    FOREIGN KEY (language_id)
        REFERENCES languages(language_id)
);

-- =====================================================
-- DOCTOR EXPERIENCES
-- =====================================================

CREATE TABLE doctor_experiences (
    experience_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    hospital_name VARCHAR(255),

    designation VARCHAR(255),

    department VARCHAR(255),

    start_date DATE,
    end_date DATE,

    responsibilities TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR DOCUMENTS
-- =====================================================

CREATE TABLE doctor_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    document_type_id UUID,

    file_name VARCHAR(255),

    file_path TEXT NOT NULL,

    mime_type VARCHAR(100),

    file_size BIGINT,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    uploaded_by UUID,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE,

    FOREIGN KEY (document_type_id)
        REFERENCES document_types(document_type_id)
);

-- =====================================================
-- DOCTOR LEAVE REQUESTS
-- =====================================================

CREATE TABLE doctor_leave_requests (
    leave_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    leave_type_id UUID,

    leave_start_date DATE,
    leave_end_date DATE,

    reason TEXT,

    approval_status VARCHAR(50),

    approved_by UUID,

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE,

    FOREIGN KEY (leave_type_id)
        REFERENCES leave_types(leave_type_id)
);

-- =====================================================
-- DOCTOR PERFORMANCE METRICS
-- =====================================================

CREATE TABLE doctor_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    metric_name VARCHAR(255),

    metric_value NUMERIC(12,2),

    metric_period_start DATE,
    metric_period_end DATE,

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR RATINGS
-- =====================================================

CREATE TABLE doctor_ratings (
    rating_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    patient_id UUID,

    rating_score NUMERIC(2,1),

    review_comment TEXT,

    rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR AUDIT LOGS
-- =====================================================

CREATE TABLE doctor_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(100),

    device_info TEXT,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- DOCTOR CHANGE HISTORY
-- =====================================================

CREATE TABLE doctor_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    changed_field VARCHAR(255),

    old_value TEXT,
    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id)
        ON DELETE CASCADE
);

-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX idx_doctors_code
ON doctors(doctor_code);

CREATE INDEX idx_doctors_name
ON doctors(first_name, last_name);

CREATE INDEX idx_doctor_specializations_doctor
ON doctor_specializations(doctor_id);

CREATE INDEX idx_doctor_departments_doctor
ON doctor_departments(doctor_id);

CREATE INDEX idx_doctor_licenses_doctor
ON doctor_licenses(doctor_id);

CREATE INDEX idx_doctor_availability_doctor
ON doctor_availability(doctor_id);

CREATE INDEX idx_doctor_schedules_doctor
ON doctor_schedules(doctor_id);

CREATE INDEX idx_doctor_documents_doctor
ON doctor_documents(doctor_id);

CREATE INDEX idx_doctor_ratings_doctor
ON doctor_ratings(doctor_id);

CREATE INDEX idx_doctor_audit_logs_doctor
ON doctor_audit_logs(doctor_id);

-- =====================================================
-- END OF DOCTOR MANAGEMENT SCHEMA
-- =====================================================