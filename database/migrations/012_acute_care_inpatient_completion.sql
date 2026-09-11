BEGIN;

-- 1. Inpatient Multi-Department Discharge Clearance Gate
ALTER TABLE admission.admissions
    ADD COLUMN IF NOT EXISTS discharge_summary_signed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pharmacy_cleared BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS nursing_cleared BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS billing_cleared BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS clearance_notes TEXT,
    ADD COLUMN IF NOT EXISTS discharged_by UUID;

-- 2. Inpatient Daily Clinical Rounds
CREATE TABLE IF NOT EXISTS admission.inpatient_rounds (
    round_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_id UUID NOT NULL REFERENCES admission.admissions(admission_id) ON DELETE CASCADE,
    round_datetime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    doctor_id UUID REFERENCES doctor.doctors(doctor_id),
    nurse_id UUID,
    chief_complaint_today TEXT,
    clinical_progress_notes TEXT NOT NULL,
    temperature NUMERIC(4,2),
    systolic_bp INT,
    diastolic_bp INT,
    heart_rate INT,
    respiratory_rate INT,
    oxygen_saturation NUMERIC(4,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inpatient_rounds_admission
    ON admission.inpatient_rounds(admission_id, round_datetime DESC);

-- 3. Nursing MAR Shift Frequency & High-Risk Pre-Administration Vitals
ALTER TABLE nursing.medication_administration_records
    ADD COLUMN IF NOT EXISTS frequency_code VARCHAR(20) DEFAULT 'PRN',
    ADD COLUMN IF NOT EXISTS scheduled_hour VARCHAR(10),
    ADD COLUMN IF NOT EXISTS pre_admin_vitals_required BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS vitals_recorded TEXT;

-- 4. Emergency Unidentified Fast-Track Arrivals & Disaster Tagging
ALTER TABLE emergency.emergency_arrivals
    ADD COLUMN IF NOT EXISTS is_unidentified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS temp_tag VARCHAR(50),
    ADD COLUMN IF NOT EXISTS incident_code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS is_mci BOOLEAN NOT NULL DEFAULT FALSE;

-- 5. Emergency Mass-Casualty Incident (MCI) Events Table
CREATE TABLE IF NOT EXISTS emergency.mci_events (
    mci_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_code VARCHAR(50) UNIQUE NOT NULL,
    incident_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    declared_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    declared_by UUID,
    notes TEXT
);

-- 6. Surgery CSSD (Central Sterile Services Dept) Tray Tracking
CREATE TABLE IF NOT EXISTS surgery.ot_cssd_trays (
    tray_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    surgery_schedule_id UUID NOT NULL REFERENCES surgery.surgery_scheduling(surgery_schedule_id) ON DELETE CASCADE,
    tray_name VARCHAR(150) NOT NULL,
    tray_barcode VARCHAR(100),
    autoclave_batch_number VARCHAR(100) NOT NULL,
    sterilization_date DATE NOT NULL,
    sterile_expiry_date DATE NOT NULL,
    is_indicator_passed BOOLEAN NOT NULL DEFAULT TRUE,
    verified_by UUID,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_surgery_cssd_schedule
    ON surgery.ot_cssd_trays(surgery_schedule_id);

-- 7. Surgery Implant & Prosthetics Tracking
CREATE TABLE IF NOT EXISTS surgery.ot_implants (
    implant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    surgery_schedule_id UUID NOT NULL REFERENCES surgery.surgery_scheduling(surgery_schedule_id) ON DELETE CASCADE,
    implant_name VARCHAR(200) NOT NULL,
    manufacturer VARCHAR(150) NOT NULL,
    serial_number VARCHAR(100) NOT NULL,
    lot_number VARCHAR(100) NOT NULL,
    expiry_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_surgery_implants_schedule
    ON surgery.ot_implants(surgery_schedule_id);

-- 8. Surgery PACU Aldrete Recovery Score
ALTER TABLE surgery.ot_recovery_records
    ADD COLUMN IF NOT EXISTS aldrete_score INT,
    ADD COLUMN IF NOT EXISTS aldrete_criteria TEXT;

COMMIT;

