-- ==========================================
-- REHABILITATION & PHYSIOTHERAPY MANAGEMENT
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS rehabilitation;

CREATE TABLE rehabilitation.rehab_specialties (
    specialty_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    specialty_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO rehabilitation.rehab_specialties (specialty_name) VALUES
('Physiotherapy'), ('Occupational Therapy'), ('Speech Therapy'), ('Cardiac Rehab');

CREATE TABLE rehabilitation.rehab_therapists (
    therapist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    employee_id UUID,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    specialty_id UUID REFERENCES rehabilitation.rehab_specialties(specialty_id),
    license_number VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rehabilitation.rehab_referrals (
    referral_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    referred_by UUID NOT NULL,
    specialty_id UUID REFERENCES rehabilitation.rehab_specialties(specialty_id),
    diagnosis TEXT,
    referral_reason TEXT,
    urgency VARCHAR(20) DEFAULT 'routine',
    status VARCHAR(30) DEFAULT 'pending',
    referral_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rehabilitation.rehab_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    referral_id UUID REFERENCES rehabilitation.rehab_referrals(referral_id),
    patient_id UUID NOT NULL,
    therapist_id UUID REFERENCES rehabilitation.rehab_therapists(therapist_id),
    assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    functional_status TEXT,
    pain_score INT,
    range_of_motion TEXT,
    strength TEXT,
    goals TEXT,
    findings TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rehabilitation.rehab_treatment_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    assessment_id UUID REFERENCES rehabilitation.rehab_assessments(assessment_id),
    patient_id UUID NOT NULL,
    therapist_id UUID REFERENCES rehabilitation.rehab_therapists(therapist_id),
    plan_name VARCHAR(255),
    frequency VARCHAR(50),
    duration_weeks INT,
    goals TEXT,
    exercises TEXT,
    start_date DATE,
    end_date DATE,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rehabilitation.rehab_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    plan_id UUID REFERENCES rehabilitation.rehab_treatment_plans(plan_id),
    patient_id UUID NOT NULL,
    therapist_id UUID REFERENCES rehabilitation.rehab_therapists(therapist_id),
    session_date TIMESTAMP NOT NULL,
    duration_minutes INT,
    exercises_performed TEXT,
    pain_score_before INT,
    pain_score_after INT,
    progress_notes TEXT,
    status VARCHAR(30) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rehabilitation.rehab_progress_records (
    progress_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES rehabilitation.rehab_treatment_plans(plan_id),
    patient_id UUID NOT NULL,
    record_date DATE NOT NULL,
    metric_name VARCHAR(100),
    metric_value VARCHAR(100),
    notes TEXT,
    recorded_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rehabilitation.rehab_equipment (
    equipment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    equipment_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    status VARCHAR(30) DEFAULT 'available',
    location VARCHAR(255),
    last_maintenance_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rehabilitation.rehab_billing (
    billing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    session_id UUID REFERENCES rehabilitation.rehab_sessions(session_id),
    patient_id UUID NOT NULL,
    service_name VARCHAR(255),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_rehab_therapists_specialty ON rehabilitation.rehab_therapists(specialty_id);
CREATE INDEX idx_rehab_therapists_employee ON rehabilitation.rehab_therapists(employee_id);
CREATE INDEX idx_rehab_referrals_patient ON rehabilitation.rehab_referrals(patient_id);
CREATE INDEX idx_rehab_referrals_doctor ON rehabilitation.rehab_referrals(referred_by);
CREATE INDEX idx_rehab_referrals_status ON rehabilitation.rehab_referrals(status);
CREATE INDEX idx_rehab_assessments_patient ON rehabilitation.rehab_assessments(patient_id);
CREATE INDEX idx_rehab_assessments_referral ON rehabilitation.rehab_assessments(referral_id);
CREATE INDEX idx_rehab_plans_patient ON rehabilitation.rehab_treatment_plans(patient_id);
CREATE INDEX idx_rehab_plans_therapist ON rehabilitation.rehab_treatment_plans(therapist_id);
CREATE INDEX idx_rehab_plans_status ON rehabilitation.rehab_treatment_plans(status);
CREATE INDEX idx_rehab_sessions_plan ON rehabilitation.rehab_sessions(plan_id);
CREATE INDEX idx_rehab_sessions_patient ON rehabilitation.rehab_sessions(patient_id);
CREATE INDEX idx_rehab_sessions_date ON rehabilitation.rehab_sessions(session_date);
CREATE INDEX idx_rehab_progress_plan ON rehabilitation.rehab_progress_records(plan_id);
CREATE INDEX idx_rehab_progress_patient ON rehabilitation.rehab_progress_records(patient_id);
CREATE INDEX idx_rehab_billing_patient ON rehabilitation.rehab_billing(patient_id);
CREATE INDEX idx_rehab_billing_session ON rehabilitation.rehab_billing(session_id);
