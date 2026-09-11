-- =========================================================================
-- Migration 013: Milestone 3 — Specialized Hospital Operations Completion
-- Adds:
--  1. Blood Bank: Donor registration, physical eligibility checks, donation collection,
--     component separation tracking, and infectious viral screening quarantine tests.
--  2. Pharmacy: Pharmacist clinical review & intervention logging, and interaction severity.
--  3. Accounts/Billing: Payment gateway checkout sessions & webhook transactions,
--     and insurance policy pre-authorization approval tracking.
--  4. Telemedicine: Secure WebRTC/Jitsi video consultation room management.
-- =========================================================================

BEGIN;

-- 1. BLOOD BANK DONOR LIFECYCLE & SCREENING
CREATE TABLE IF NOT EXISTS blood_bank.blood_donors (
    blood_donor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    donor_number VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20),
    blood_group_type_id UUID REFERENCES blood_bank.blood_group_types(blood_group_type_id),
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    last_donation_date DATE,
    total_donations INT DEFAULT 0,
    is_eligible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blood_bank.donor_eligibility_checks (
    eligibility_check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_donor_id UUID NOT NULL REFERENCES blood_bank.blood_donors(blood_donor_id) ON DELETE CASCADE,
    check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hemoglobin NUMERIC(5,2),
    blood_pressure VARCHAR(20),
    weight NUMERIC(5,2),
    temperature NUMERIC(4,1),
    pulse INT,
    is_eligible BOOLEAN NOT NULL,
    rejection_reason TEXT,
    checked_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blood_bank.blood_donations (
    blood_donation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    blood_donor_id UUID NOT NULL REFERENCES blood_bank.blood_donors(blood_donor_id),
    donation_type VARCHAR(50) DEFAULT 'Voluntary',
    donation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bag_number VARCHAR(100) UNIQUE NOT NULL,
    volume_ml INT DEFAULT 450,
    collected_by UUID,
    notes TEXT,
    status VARCHAR(30) DEFAULT 'collected', -- collected, separated, tested, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhance blood_units with discard tracking if not present
ALTER TABLE blood_bank.blood_units
    ADD COLUMN IF NOT EXISTS discard_reason TEXT,
    ADD COLUMN IF NOT EXISTS discarded_by UUID,
    ADD COLUMN IF NOT EXISTS discarded_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS blood_bank.blood_unit_tests (
    unit_test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_unit_id UUID NOT NULL REFERENCES blood_bank.blood_units(blood_unit_id) ON DELETE CASCADE,
    test_name VARCHAR(100) NOT NULL, -- HIV 1&2, Hepatitis B (HBsAg), Hepatitis C (HCV), Syphilis (VDRL), Malaria
    result VARCHAR(30) NOT NULL DEFAULT 'Negative', -- Negative, Reactive, Indeterminate
    tested_by UUID,
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_by UUID,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. PHARMACY PHARMACIST REVIEW & DRUG INTERACTION SEVERITY
CREATE TABLE IF NOT EXISTS pharmacy.pharmacist_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID NOT NULL REFERENCES pharmacy.prescriptions(prescription_id) ON DELETE CASCADE,
    pharmacist_id UUID NOT NULL,
    review_status VARCHAR(30) DEFAULT 'Approved', -- Approved, Flagged, Modified, Rejected
    intervention_type VARCHAR(50) DEFAULT 'Routine Cleared', -- Dose Adjustment, Drug Substitution, Allergy Override, Interaction Override, Routine Cleared
    clinical_notes TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pharmacy.drug_interaction_rules (
    interaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_a_id UUID NOT NULL REFERENCES pharmacy.drugs(drug_id),
    drug_b_id UUID NOT NULL REFERENCES pharmacy.drugs(drug_id),
    severity_level VARCHAR(20) DEFAULT 'Moderate', -- Mild, Moderate, Severe, Contraindicated
    description TEXT,
    action_required VARCHAR(100) DEFAULT 'Monitor patient',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_drug_pair UNIQUE (drug_a_id, drug_b_id)
);

-- 3. BILLING: PAYMENT GATEWAY CHECKOUT SESSIONS & INSURANCE PRE-AUTHORIZATIONS
CREATE TABLE IF NOT EXISTS billing.payment_gateway_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES billing.invoices(invoice_id) ON DELETE CASCADE,
    gateway_provider VARCHAR(50) NOT NULL, -- Stripe, Razorpay, UPI
    gateway_session_id VARCHAR(255) UNIQUE NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    status VARCHAR(30) DEFAULT 'Pending', -- Pending, Completed, Failed, Cancelled
    payment_reference VARCHAR(255),
    signature_verified BOOLEAN DEFAULT FALSE,
    webhook_payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing.insurance_preauthorizations (
    preauth_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patient.patients(patient_id) ON DELETE CASCADE,
    insurance_provider VARCHAR(255) NOT NULL,
    policy_number VARCHAR(255) NOT NULL,
    approval_code VARCHAR(100) UNIQUE NOT NULL,
    authorized_amount NUMERIC(14,2) NOT NULL,
    copay_percentage NUMERIC(5,2) DEFAULT 0,
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'Approved', -- Approved, Consumed, Expired, Cancelled
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. TELEMEDICINE: WEBRTC / JITSI VIDEO CONSULTATION ROOMS
CREATE TABLE IF NOT EXISTS telemedicine.video_rooms (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    virtual_appointment_id UUID NOT NULL REFERENCES telemedicine.virtual_appointments(virtual_appointment_id) ON DELETE CASCADE,
    room_name VARCHAR(255) UNIQUE NOT NULL,
    room_url VARCHAR(500) NOT NULL,
    host_token VARCHAR(255),
    participant_token VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

COMMIT;
