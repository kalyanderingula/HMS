-- Consolidated final application schema extensions.
-- Historical migration boundaries are retained below for traceability.
-- This file runs after all domain schema files during fresh database initialization.


-- ============================================================================
-- Source: 001_add_core_departments.sql
-- ============================================================================
-- =========================================================
-- MIGRATION: Link all schemas to core.departments & core.sub_departments
-- Date: 2024
-- Description: Adds FK references from existing tables to the
--              new core.departments and core.sub_departments master tables
-- =========================================================

-- =========================================================
-- STEP 1: Create core.departments & core.sub_departments
-- (Already in SHARED_MASTER_TABLES.sql, included here for standalone execution)
-- =========================================================

CREATE TABLE IF NOT EXISTS core.departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_code VARCHAR(50) UNIQUE NOT NULL,
    department_name VARCHAR(255) NOT NULL,
    description TEXT,
    schema_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.sub_departments (
    sub_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_id UUID NOT NULL REFERENCES core.departments(department_id),
    sub_department_code VARCHAR(50) UNIQUE NOT NULL,
    sub_department_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- STEP 2: ALTER existing tables to add FK columns
-- =========================================================

-- human_resources.employees
ALTER TABLE human_resources.employees
    ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- human_resources.employee_department_mapping
ALTER TABLE human_resources.employee_department_mapping
    ADD COLUMN IF NOT EXISTS core_department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS core_sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- doctor.doctors
ALTER TABLE doctor.doctors
    ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- doctor.specializations
ALTER TABLE doctor.specializations
    ADD COLUMN IF NOT EXISTS sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- department.departments
ALTER TABLE department.departments
    ADD COLUMN IF NOT EXISTS core_department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS core_sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- =========================================================
-- STEP 3: Indexes for new columns
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_employees_core_dept ON human_resources.employees(department_id);
CREATE INDEX IF NOT EXISTS idx_employees_core_sub_dept ON human_resources.employees(sub_department_id);
CREATE INDEX IF NOT EXISTS idx_emp_dept_map_core_dept ON human_resources.employee_department_mapping(core_department_id);
CREATE INDEX IF NOT EXISTS idx_emp_dept_map_core_sub_dept ON human_resources.employee_department_mapping(core_sub_department_id);
CREATE INDEX IF NOT EXISTS idx_doctors_core_dept ON doctor.doctors(department_id);
CREATE INDEX IF NOT EXISTS idx_doctors_core_sub_dept ON doctor.doctors(sub_department_id);
CREATE INDEX IF NOT EXISTS idx_specializations_sub_dept ON doctor.specializations(sub_department_id);
CREATE INDEX IF NOT EXISTS idx_dept_core_dept ON department.departments(core_department_id);
CREATE INDEX IF NOT EXISTS idx_dept_core_sub_dept ON department.departments(core_sub_department_id);

-- =========================================================
-- STEP 4: Seed department codes
-- =========================================================

INSERT INTO core.departments (department_code, department_name, schema_name) VALUES
('DEP-PAT', 'Patient Management', 'patient'),
('DEP-DOC', 'Doctor Management', 'doctor'),
('DEP-DEPT', 'Department Management', 'department'),
('DEP-APT', 'Appointment Management', 'appointment'),
('DEP-ADM', 'Admission & Bed Management', 'admission'),
('DEP-BIL', 'Billing & Financial Management', 'billing'),
('DEP-PHR', 'Pharmacy Management', 'pharmacy'),
('DEP-LAB', 'Laboratory Information System', 'laboratory'),
('DEP-RAD', 'Radiology Information System', 'radiology'),
('DEP-EMR', 'Emergency & Trauma Management', 'emergency'),
('DEP-SUR', 'Surgery & OT Management', 'surgery'),
('DEP-ICU', 'ICU & Critical Care', 'intensive_care_unit'),
('DEP-NUR', 'Nursing Management', 'nursing'),
('DEP-INS', 'Insurance & Claims Management', 'insurance'),
('DEP-INV', 'Inventory & Procurement', 'inventory'),
('DEP-EMR2', 'Electronic Medical Records', 'electronic_medical_records'),
('DEP-AMB', 'Ambulance & Transport', 'ambulance'),
('DEP-BB', 'Blood Bank Management', 'blood_bank'),
('DEP-DIET', 'Dietetics & Nutrition', 'dietetics'),
('DEP-TELE', 'Telemedicine & Virtual Care', 'telemedicine'),
('DEP-CRM', 'CRM & Patient Engagement', 'customer_relationship_management'),
('DEP-QUE', 'Queue Management', 'queue_management'),
('DEP-HK', 'Housekeeping Management', 'housekeeping'),
('DEP-VIS', 'Visitor Management', 'visitor'),
('DEP-BMW', 'Biomedical Waste Management', 'biomedical_waste'),
('DEP-MOR', 'Mortuary & Medicolegal', 'mortuary'),
('DEP-REH', 'Rehabilitation & Physiotherapy', 'rehabilitation'),
('DEP-SEC', 'Security & IAM', 'security'),
('DEP-ANA', 'Analytics & Business Intelligence', 'analytics'),
('DEP-AI', 'AI & Clinical Decision Support', 'artificial_intelligence'),
('DEP-MH', 'Multi-Hospital Management', 'multi_hospital'),
('DEP-HR', 'HR & Payroll Management', 'human_resources')
ON CONFLICT (department_code) DO NOTHING;

-- =========================================================
-- STEP 5: Seed sub-department codes
-- =========================================================

-- Doctor Specializations
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('DOC-ENT', 'ENT (Ear, Nose, Throat)'),
    ('DOC-CARD', 'Cardiology'),
    ('DOC-ORTH', 'Orthopedics'),
    ('DOC-NEUR', 'Neurology'),
    ('DOC-DERM', 'Dermatology'),
    ('DOC-PEDI', 'Pediatrics'),
    ('DOC-GYNE', 'Gynecology'),
    ('DOC-OPTH', 'Ophthalmology'),
    ('DOC-PSYC', 'Psychiatry'),
    ('DOC-ANES', 'Anesthesiology'),
    ('DOC-ONCO', 'Oncology'),
    ('DOC-NEPH', 'Nephrology'),
    ('DOC-PULM', 'Pulmonology'),
    ('DOC-GAST', 'Gastroenterology'),
    ('DOC-ENDO', 'Endocrinology'),
    ('DOC-UROL', 'Urology'),
    ('DOC-GP', 'General Physician'),
    ('DOC-SURG', 'General Surgery')
) AS v(code, name) WHERE d.department_code = 'DEP-DOC'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Laboratory
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('LAB-BIO', 'Biochemistry'),
    ('LAB-HEM', 'Hematology'),
    ('LAB-MIC', 'Microbiology'),
    ('LAB-PATH', 'Pathology'),
    ('LAB-SER', 'Serology')
) AS v(code, name) WHERE d.department_code = 'DEP-LAB'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Radiology
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('RAD-XRAY', 'X-Ray'),
    ('RAD-CT', 'CT Scan'),
    ('RAD-MRI', 'MRI'),
    ('RAD-USG', 'Ultrasound'),
    ('RAD-MAM', 'Mammography')
) AS v(code, name) WHERE d.department_code = 'DEP-RAD'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Surgery
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('SUR-GEN', 'General Surgery'),
    ('SUR-CARD', 'Cardiac Surgery'),
    ('SUR-NEUR', 'Neuro Surgery'),
    ('SUR-ORTH', 'Orthopedic Surgery'),
    ('SUR-PLAS', 'Plastic Surgery')
) AS v(code, name) WHERE d.department_code = 'DEP-SUR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Nursing
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('NUR-ICU', 'ICU Nursing'),
    ('NUR-OT', 'OT Nursing'),
    ('NUR-GEN', 'General Ward Nursing'),
    ('NUR-PED', 'Pediatric Nursing'),
    ('NUR-ER', 'Emergency Nursing')
) AS v(code, name) WHERE d.department_code = 'DEP-NUR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Pharmacy
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('PHR-INP', 'Inpatient Pharmacy'),
    ('PHR-OUT', 'Outpatient Pharmacy'),
    ('PHR-STORE', 'Drug Store')
) AS v(code, name) WHERE d.department_code = 'DEP-PHR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Emergency
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('ER-TRAU', 'Trauma Unit'),
    ('ER-TRIAGE', 'Triage'),
    ('ER-RESUS', 'Resuscitation')
) AS v(code, name) WHERE d.department_code = 'DEP-EMR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- =========================================================
-- END OF MIGRATION
-- =========================================================



-- ============================================================================
-- Source: 002_phase2_emr_telemedicine.sql
-- ============================================================================
BEGIN;

ALTER TABLE telemedicine.virtual_appointments
    ADD COLUMN IF NOT EXISTS chief_complaint TEXT,
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Scheduled',
    ADD COLUMN IF NOT EXISTS emr_encounter_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'virtual_appointments_emr_encounter_id_fkey'
    ) THEN
        ALTER TABLE telemedicine.virtual_appointments
            ADD CONSTRAINT virtual_appointments_emr_encounter_id_fkey
            FOREIGN KEY (emr_encounter_id)
            REFERENCES electronic_medical_records.patient_encounters(encounter_id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_encounters_patient_date
    ON electronic_medical_records.patient_encounters(patient_id, encounter_date DESC);
CREATE INDEX IF NOT EXISTS idx_vitals_patient_recorded
    ON electronic_medical_records.vital_signs(patient_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_diagnoses_patient
    ON electronic_medical_records.diagnoses(patient_id, diagnosed_at DESC);
CREATE INDEX IF NOT EXISTS idx_virtual_appointments_patient_date
    ON telemedicine.virtual_appointments(patient_id, appointment_datetime DESC);

COMMIT;



-- ============================================================================
-- Source: 003_backfill_doctor_employees.sql
-- ============================================================================
BEGIN;

INSERT INTO doctor.doctor_statuses (status_name)
SELECT 'Active'
WHERE NOT EXISTS (
    SELECT 1 FROM doctor.doctor_statuses WHERE lower(status_name) = 'active'
);

INSERT INTO doctor.doctors (
    doctor_code, employee_id, first_name, middle_name, last_name,
    email, phone, department_id, sub_department_id, status_id,
    joining_date, created_at, updated_at
)
SELECT
    e.employee_number, e.employee_id, e.first_name, e.middle_name, e.last_name,
    e.official_email, e.official_phone, e.department_id, e.sub_department_id,
    (SELECT status_id FROM doctor.doctor_statuses WHERE lower(status_name) = 'active' ORDER BY status_id LIMIT 1),
    e.date_of_joining, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM human_resources.employees e
JOIN security.users u ON u.employee_id = e.employee_id
JOIN security.user_roles ur ON ur.user_id = u.user_id
JOIN security.roles r ON r.role_id = ur.role_id
WHERE r.role_name IN ('doctor', 'surgeon', 'telemedicine_doctor')
  AND NOT EXISTS (
      SELECT 1 FROM doctor.doctors d WHERE d.employee_id = e.employee_id
  )
ON CONFLICT (doctor_code) DO NOTHING;

COMMIT;



-- ============================================================================
-- Source: 004_workflow_completion.sql
-- ============================================================================
-- Additive compatibility migration; existing records are preserved.
ALTER TABLE surgery.surgery_requests ADD COLUMN IF NOT EXISTS procedure_code VARCHAR(100);
ALTER TABLE pharmacy.dispensing_records ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patient.patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_invoices_patient_date ON billing.invoices(patient_id,invoice_date DESC);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_reference ON billing.payments(invoice_id,payment_reference);
CREATE INDEX IF NOT EXISTS idx_active_admissions_bed ON admission.admissions(bed_id) WHERE actual_discharge_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_active_admissions_patient ON admission.admissions(patient_id) WHERE actual_discharge_date IS NULL;



-- ============================================================================
-- Source: 005_clinical_pharmacy_billing_integration.sql
-- ============================================================================
BEGIN;

ALTER TABLE electronic_medical_records.medication_records
    ADD COLUMN IF NOT EXISTS drug_id UUID REFERENCES pharmacy.drugs(drug_id),
    ADD COLUMN IF NOT EXISTS quantity_prescribed NUMERIC(14,2),
    ADD COLUMN IF NOT EXISTS medication_status VARCHAR(40) DEFAULT 'Draft';

ALTER TABLE pharmacy.prescription_items
    ADD COLUMN IF NOT EXISTS medication_record_id UUID REFERENCES electronic_medical_records.medication_records(medication_record_id),
    ADD COLUMN IF NOT EXISTS quantity_dispensed NUMERIC(14,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS item_status VARCHAR(40) NOT NULL DEFAULT 'Pending';

ALTER TABLE pharmacy.dispensing_records
    ADD COLUMN IF NOT EXISTS dispensing_reference VARCHAR(100);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pharmacy_prescription_encounter
    ON pharmacy.prescriptions(encounter_id) WHERE encounter_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_prescription_item_medication
    ON pharmacy.prescription_items(medication_record_id) WHERE medication_record_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_item_source
    ON billing.invoice_items(item_type, item_reference_id) WHERE item_reference_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS pharmacy.prescription_amendments (
    amendment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prescription_id UUID NOT NULL REFERENCES pharmacy.prescriptions(prescription_id),
    prescription_item_id UUID REFERENCES pharmacy.prescription_items(prescription_item_id),
    action VARCHAR(40) NOT NULL,
    reason TEXT NOT NULL,
    before_value JSONB,
    after_value JSONB,
    amended_by UUID,
    amended_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispensing_items_prescription_item
    ON pharmacy.dispensing_items(prescription_item_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dispensing_reference
    ON pharmacy.dispensing_records(dispensing_reference) WHERE dispensing_reference IS NOT NULL;

COMMIT;



-- ============================================================================
-- Source: 006_blood_bank_workflow.sql
-- ============================================================================
BEGIN;

ALTER TABLE blood_bank.blood_component_types
    ADD COLUMN IF NOT EXISTS unit_price NUMERIC(14,2) NOT NULL DEFAULT 1000;

ALTER TABLE blood_bank.blood_transfusions
    ADD COLUMN IF NOT EXISTS adverse_reaction BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reaction_details TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_blood_crossmatch_request_unit
    ON blood_bank.cross_match_tests(blood_request_id, blood_unit_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_blood_transfusion_unit
    ON blood_bank.blood_transfusions(blood_unit_id);

COMMIT;



-- ============================================================================
-- Source: 007_nursing_mar_workflow.sql
-- ============================================================================
BEGIN;
ALTER TABLE nursing.medication_administration_logs
  ADD COLUMN IF NOT EXISTS patient_id UUID,
  ADD COLUMN IF NOT EXISTS prescription_item_id UUID,
  ADD COLUMN IF NOT EXISTS medicine_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS route VARCHAR(100),
  ADD COLUMN IF NOT EXISTS administration_status VARCHAR(40) NOT NULL DEFAULT 'Administered',
  ADD COLUMN IF NOT EXISTS exception_reason TEXT;
ALTER TABLE nursing.medication_administration_logs
  DROP CONSTRAINT IF EXISTS medication_administration_logs_administered_by_fkey;
CREATE UNIQUE INDEX IF NOT EXISTS uq_nursing_log_mar ON nursing.medication_administration_logs(mar_id) WHERE mar_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_nursing_mar_dose ON nursing.medication_administration_records(patient_id,prescription_item_id,scheduled_time);
COMMIT;



-- ============================================================================
-- Source: 008_accounts_controls.sql
-- ============================================================================
BEGIN;
CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_refund_reference ON billing.refunds(refund_reference);
CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_claim_number ON billing.insurance_claims(claim_number);
CREATE TABLE IF NOT EXISTS billing.billing_action_audit (
  audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), invoice_id UUID REFERENCES billing.invoices(invoice_id),
  action VARCHAR(50) NOT NULL, amount NUMERIC(14,2), reason TEXT NOT NULL, performed_by UUID,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMIT;



-- ============================================================================
-- Source: 009_emergency_workflow.sql
-- ============================================================================
BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_emergency_triage_arrival
    ON emergency.emergency_triage_assessments(emergency_arrival_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_emergency_registration_arrival
    ON emergency.emergency_registrations(emergency_arrival_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_emergency_encounter_registration
    ON emergency.emergency_encounters(emergency_registration_id);

ALTER TABLE emergency.emergency_encounters
    ADD COLUMN IF NOT EXISTS disposition VARCHAR(40),
    ADD COLUMN IF NOT EXISTS disposition_notes TEXT,
    ADD COLUMN IF NOT EXISTS disposition_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS disposition_by UUID,
    ADD COLUMN IF NOT EXISTS admission_id UUID;

CREATE TABLE IF NOT EXISTS emergency.emergency_clinical_notes (
    emergency_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    emergency_encounter_id UUID NOT NULL REFERENCES emergency.emergency_encounters(emergency_encounter_id),
    note_type VARCHAR(50) NOT NULL,
    note_text TEXT NOT NULL,
    recorded_by UUID,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_emergency_notes_encounter
    ON emergency.emergency_clinical_notes(emergency_encounter_id, recorded_at);

COMMIT;



-- ============================================================================
-- Source: 010_surgery_ot_workflow.sql
-- ============================================================================
BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_surgery_request_schedule
    ON surgery.surgery_scheduling(surgery_request_id);
CREATE INDEX IF NOT EXISTS idx_surgery_room_schedule
    ON surgery.surgery_scheduling(ot_room_number, scheduled_start, scheduled_end);

ALTER TABLE surgery.surgery_requests
    ADD COLUMN IF NOT EXISTS encounter_id UUID,
    ADD COLUMN IF NOT EXISTS admission_id UUID,
    ADD COLUMN IF NOT EXISTS estimated_charge NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE surgery.surgery_scheduling
    ADD COLUMN IF NOT EXISTS actual_start TIMESTAMP,
    ADD COLUMN IF NOT EXISTS actual_end TIMESTAMP,
    ADD COLUMN IF NOT EXISTS anesthesia_type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS complications TEXT,
    ADD COLUMN IF NOT EXISTS completed_by UUID;

CREATE TABLE IF NOT EXISTS surgery.ot_preoperative_checklists (
    checklist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    surgery_request_id UUID NOT NULL UNIQUE REFERENCES surgery.surgery_requests(surgery_request_id),
    consent_verified BOOLEAN NOT NULL,
    identity_verified BOOLEAN NOT NULL,
    surgical_site_verified BOOLEAN NOT NULL,
    allergies_reviewed BOOLEAN NOT NULL,
    investigations_reviewed BOOLEAN NOT NULL,
    fasting_confirmed BOOLEAN NOT NULL,
    anesthesia_cleared BOOLEAN NOT NULL,
    asa_classification VARCHAR(20),
    notes TEXT,
    completed_by UUID,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS surgery.ot_recovery_records (
    recovery_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    surgery_schedule_id UUID NOT NULL UNIQUE REFERENCES surgery.surgery_scheduling(surgery_schedule_id),
    recovery_status VARCHAR(40) NOT NULL,
    pain_score INT NOT NULL CHECK (pain_score BETWEEN 0 AND 10),
    observations TEXT NOT NULL,
    disposition VARCHAR(40) NOT NULL,
    recorded_by UUID,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS surgery.ot_consumables (
    consumable_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    surgery_schedule_id UUID NOT NULL REFERENCES surgery.surgery_scheduling(surgery_schedule_id),
    item_name VARCHAR(255) NOT NULL,
    quantity NUMERIC(12,2) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(14,2) NOT NULL CHECK (unit_price >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;



-- ============================================================================
-- Source: 011_clinical_diagnostics_completion.sql
-- ============================================================================
BEGIN;

-- 1. Doctor Acknowledgement & Tracking for Laboratory Results
ALTER TABLE laboratory.lab_result_entries
    ADD COLUMN IF NOT EXISTS acknowledged_by UUID,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS acknowledgement_notes TEXT;

-- 2. Doctor Acknowledgement & Critical Flags for Radiology Reports
ALTER TABLE radiology.radiology_reports
    ADD COLUMN IF NOT EXISTS is_critical BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS critical_alert_details TEXT,
    ADD COLUMN IF NOT EXISTS acknowledged_by UUID,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS acknowledgement_notes TEXT;

-- 3. PACS Imaging Series & Key Images for Studies
CREATE TABLE IF NOT EXISTS radiology.imaging_study_images (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id UUID NOT NULL REFERENCES radiology.imaging_studies(study_id) ON DELETE CASCADE,
    series_number INT NOT NULL DEFAULT 1,
    instance_number INT NOT NULL DEFAULT 1,
    image_url TEXT NOT NULL,
    slice_description VARCHAR(255),
    is_key_image BOOLEAN NOT NULL DEFAULT FALSE,
    modality_code VARCHAR(50),
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_imaging_study_images_study ON radiology.imaging_study_images(study_id);

-- 4. Notification read tracking
ALTER TABLE core.notifications
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMP;

COMMIT;



-- ============================================================================
-- Source: 011_patient_portal_accounts.sql
-- ============================================================================
BEGIN;

ALTER TABLE security.users
    ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patient.patients(patient_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_security_user_patient
    ON security.users(patient_id) WHERE patient_id IS NOT NULL;
INSERT INTO security.roles(role_name) VALUES('patient') ON CONFLICT(role_name) DO NOTHING;

COMMIT;



-- ============================================================================
-- Source: 012_acute_care_inpatient_completion.sql
-- ============================================================================
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




-- ============================================================================
-- Source: 013_specialized_hospital_operations.sql
-- ============================================================================
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

-- Upgrade earlier versions of the donor tables when they already exist.
ALTER TABLE blood_bank.donor_eligibility_checks
    ADD COLUMN IF NOT EXISTS temperature NUMERIC(4,1),
    ADD COLUMN IF NOT EXISTS pulse INT;
ALTER TABLE blood_bank.blood_donations
    ADD COLUMN IF NOT EXISTS donation_type VARCHAR(50) DEFAULT 'Voluntary',
    ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'collected';

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



-- ============================================================================
-- Source: 014_admin_security_compliance.sql
-- ============================================================================
-- =========================================================================
-- Migration 014: Milestone 4 — Administration, Security & Compliance Completion
-- Adds:
--  1. Security: Granular permissions catalog and role-permission mappings.
--  2. HR & Administration: Shift schedule catalog and employee duty rostering with double-booking prevention.
--  3. Document Security: Cryptographic checksum (SHA-256), MIME type, and file size tracking.
-- =========================================================================

BEGIN;

-- Existing installations may already contain earlier, smaller versions of
-- these tables. Bring those versions up to the current contract before seeds.
ALTER TABLE security.permissions
    ADD COLUMN IF NOT EXISTS permission_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS module VARCHAR(100),
    ADD COLUMN IF NOT EXISTS description TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_security_permission_code
    ON security.permissions(permission_code);

ALTER TABLE human_resources.shift_schedules
    ADD COLUMN IF NOT EXISTS shift_code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS is_night_shift BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_hr_shift_code
    ON human_resources.shift_schedules(shift_code);

ALTER TABLE human_resources.employee_rosters
    ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS notes TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_security_role_permission
    ON security.role_permissions(role_id, permission_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_hr_employee_roster_date
    ON human_resources.employee_rosters(employee_id, roster_date);

-- 1. GRANULAR PERMISSION CATALOG & ROLE PERMISSION MAPPING
CREATE TABLE IF NOT EXISTS security.permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_code VARCHAR(100) UNIQUE NOT NULL,
    permission_name VARCHAR(255) NOT NULL,
    module VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS security.role_permissions (
    role_permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES security.roles(role_id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES security.permissions(permission_id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON security.role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON security.role_permissions(permission_id);

-- Seed standard core permissions if not present
INSERT INTO security.permissions (permission_code, permission_name, module, description)
VALUES
    ('users.read', 'View Users', 'users', 'Ability to view employee and system users'),
    ('users.manage', 'Manage Users', 'users', 'Create and modify employee accounts and system users'),
    ('roles.manage', 'Manage Roles & Permissions', 'security', 'Configure roles and assign granular security permissions'),
    ('patients.read', 'View Patients', 'patients', 'Access patient search, registration, and demographics'),
    ('patients.manage', 'Register & Edit Patients', 'patients', 'Register new patients and modify demographic details'),
    ('emr.read', 'View Clinical Records', 'emr', 'Access EMR clinical summaries, vitals, and diagnostic notes'),
    ('emr.write', 'Record Clinical Consultations', 'emr', 'Create SOAP notes, prescribe medications, and add clinical entries'),
    ('appointments.manage', 'Manage Appointments', 'appointments', 'Schedule, reschedule, and check-in patient appointments'),
    ('rosters.manage', 'Manage Duty Rosters', 'human_resources', 'Create and schedule staff shift duty rosters'),
    ('pharmacy.dispense', 'Dispense Medications', 'pharmacy', 'Review prescriptions and dispense medications from stock'),
    ('laboratory.order', 'Order Lab Tests', 'laboratory', 'Order diagnostic laboratory investigations'),
    ('laboratory.process', 'Process Lab Tests', 'laboratory', 'Collect samples, enter parameter results, and verify lab findings'),
    ('radiology.view', 'View Radiology PACS', 'radiology', 'Inspect radiology worklist, study series, and PACS viewer'),
    ('radiology.report', 'Finalize Radiology Reports', 'radiology', 'Submit and sign off on diagnostic radiology imaging reports'),
    ('emergency.triage', 'Emergency Intake & Triage', 'emergency', 'Perform emergency arrivals, trauma intake, and disaster mode triage'),
    ('surgery.schedule', 'Schedule Surgery & OT', 'surgery', 'Book surgical cases, operating theatres, and surgeon teams'),
    ('blood_bank.manage', 'Blood Bank Operations', 'blood_bank', 'Manage donor collection, component separation, and cross-matching'),
    ('billing.invoices', 'Generate Invoices', 'billing', 'Create, itemize, and issue patient billing accounts and invoices'),
    ('billing.payments', 'Collect Payments & Refunds', 'billing', 'Process cash/online payments, webhook settlements, and refunds'),
    ('documents.verify', 'Verify Document Integrity', 'security', 'Execute cryptographic SHA-256 tamper verification on files')
ON CONFLICT (permission_code) DO NOTHING;

-- Seed default permissions to standard roles (super_admin, admin, doctor, etc.)
INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM security.roles r
CROSS JOIN security.permissions p
WHERE r.role_name = 'super_admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM security.roles r
CROSS JOIN security.permissions p
WHERE r.role_name = 'doctor'
  AND p.module IN ('patients', 'emr', 'appointments', 'laboratory', 'radiology', 'emergency')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 2. STAFF SHIFT DUTY ROSTERING & SCHEDULING
CREATE TABLE IF NOT EXISTS human_resources.shift_schedules (
    shift_schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shift_code VARCHAR(50) UNIQUE NOT NULL,
    shift_name VARCHAR(100) NOT NULL,
    shift_start_time TIME NOT NULL,
    shift_end_time TIME NOT NULL,
    is_night_shift BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS human_resources.employee_rosters (
    employee_roster_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES human_resources.employees(employee_id) ON DELETE CASCADE,
    shift_schedule_id UUID NOT NULL REFERENCES human_resources.shift_schedules(shift_schedule_id) ON DELETE RESTRICT,
    department_id UUID REFERENCES core.departments(department_id),
    roster_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_employee_roster_date UNIQUE (employee_id, roster_date)
);

CREATE INDEX IF NOT EXISTS idx_employee_rosters_date ON human_resources.employee_rosters(roster_date);
CREATE INDEX IF NOT EXISTS idx_employee_rosters_emp ON human_resources.employee_rosters(employee_id);

-- Seed standard hospital shift configurations
INSERT INTO human_resources.shift_schedules (shift_code, shift_name, shift_start_time, shift_end_time, is_night_shift)
VALUES
    ('SHIFT_MORNING', 'Morning Shift (OPD & Rounds)', '08:00:00', '16:00:00', FALSE),
    ('SHIFT_EVENING', 'Evening Shift (OPD & Coverage)', '16:00:00', '00:00:00', FALSE),
    ('SHIFT_NIGHT', 'Night Duty (Emergency & Inpatient)', '00:00:00', '08:00:00', TRUE),
    ('SHIFT_GENERAL', 'General Staff Office Hours', '09:00:00', '17:00:00', FALSE)
ON CONFLICT (shift_code) DO NOTHING;

-- 3. DOCUMENT SECURITY & CRYPTOGRAPHIC INTEGRITY
ALTER TABLE human_resources.employee_documents
    ADD COLUMN IF NOT EXISTS checksum_sha256 VARCHAR(64),
    ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100);

COMMIT;


