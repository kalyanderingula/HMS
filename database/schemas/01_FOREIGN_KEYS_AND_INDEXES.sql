-- =============================================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- MASTER SCRIPT: CROSS-SCHEMA FOREIGN KEYS & PERFORMANCE INDEXES
-- Purpose: Enforce relational integrity and create B-Tree indexes across all 33 schemas.
-- Execution: Run this script AFTER all domain schema files have been created.
-- =============================================================================

-- =============================================================================
-- SECTION 1: CROSS-SCHEMA FOREIGN KEY CONSTRAINTS (IDEMPOTENT)
-- =============================================================================

DO $$
BEGIN

    -- 1. SECURITY -> HR
    BEGIN
        ALTER TABLE security.users 
        ADD CONSTRAINT fk_users_employee 
        FOREIGN KEY (employee_id) REFERENCES human_resources.employees(employee_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 2. DOCTORS -> HR & CORE
    BEGIN
        ALTER TABLE doctor.doctors 
        ADD CONSTRAINT fk_doctors_employee 
        FOREIGN KEY (employee_id) REFERENCES human_resources.employees(employee_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE doctor.doctors 
        ADD CONSTRAINT fk_doctors_core_dept 
        FOREIGN KEY (department_id) REFERENCES core.departments(department_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 3. APPOINTMENTS -> PATIENTS & DOCTORS
    BEGIN
        ALTER TABLE appointment.appointments 
        ADD CONSTRAINT fk_appointments_patient 
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE appointment.appointments 
        ADD CONSTRAINT fk_appointments_doctor 
        FOREIGN KEY (doctor_id) REFERENCES doctor.doctors(doctor_id) ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE appointment.appointments 
        ADD CONSTRAINT fk_appointments_dept 
        FOREIGN KEY (department_id) REFERENCES core.departments(department_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 4. EMR (PATIENT ENCOUNTERS) -> PATIENTS, DOCTORS, APPOINTMENTS
    BEGIN
        ALTER TABLE electronic_medical_records.patient_encounters 
        ADD CONSTRAINT fk_encounters_patient 
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE electronic_medical_records.patient_encounters 
        ADD CONSTRAINT fk_encounters_doctor 
        FOREIGN KEY (doctor_id) REFERENCES doctor.doctors(doctor_id) ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE electronic_medical_records.patient_encounters 
        ADD CONSTRAINT fk_encounters_appointment 
        FOREIGN KEY (appointment_id) REFERENCES appointment.appointments(appointment_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE electronic_medical_records.patient_encounters 
        ADD CONSTRAINT fk_encounters_dept 
        FOREIGN KEY (department_id) REFERENCES core.departments(department_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 5. BILLING (INVOICES) -> PATIENTS, ENCOUNTERS, APPOINTMENTS
    BEGIN
        ALTER TABLE billing.invoices 
        ADD CONSTRAINT fk_invoices_patient 
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE billing.invoices 
        ADD CONSTRAINT fk_invoices_encounter 
        FOREIGN KEY (encounter_id) REFERENCES electronic_medical_records.patient_encounters(encounter_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE billing.invoices 
        ADD CONSTRAINT fk_invoices_appointment 
        FOREIGN KEY (appointment_id) REFERENCES appointment.appointments(appointment_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 6. PHARMACY (PRESCRIPTIONS) -> PATIENTS & DOCTORS
    BEGIN
        ALTER TABLE pharmacy.prescriptions 
        ADD CONSTRAINT fk_pharmacy_prescriptions_patient 
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE pharmacy.prescriptions 
        ADD CONSTRAINT fk_pharmacy_prescriptions_doctor 
        FOREIGN KEY (doctor_id) REFERENCES doctor.doctors(doctor_id) ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 7. LABORATORY (LAB ORDERS) -> PATIENTS & DOCTORS
    BEGIN
        ALTER TABLE laboratory.lab_orders 
        ADD CONSTRAINT fk_lab_orders_patient 
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE laboratory.lab_orders 
        ADD CONSTRAINT fk_lab_orders_doctor 
        FOREIGN KEY (doctor_id) REFERENCES doctor.doctors(doctor_id) ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 8. RADIOLOGY (ORDERS) -> PATIENTS & DOCTORS
    BEGIN
        ALTER TABLE radiology.radiology_orders
        ADD CONSTRAINT fk_radiology_orders_patient
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE radiology.radiology_orders
        ADD CONSTRAINT fk_radiology_orders_doctor
        FOREIGN KEY (doctor_id) REFERENCES doctor.doctors(doctor_id) ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 9. ADMISSIONS -> PATIENTS & DOCTORS
    BEGIN
        ALTER TABLE admission.admissions 
        ADD CONSTRAINT fk_admissions_patient 
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE admission.admissions 
        ADD CONSTRAINT fk_admissions_doctor 
        FOREIGN KEY (admitting_doctor_id) REFERENCES doctor.doctors(doctor_id) ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 10. EMERGENCY ARRIVALS -> PATIENTS
    BEGIN
        ALTER TABLE emergency.emergency_arrivals
        ADD CONSTRAINT fk_emergency_arrivals_patient
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    -- 11. QUEUE MANAGEMENT -> PATIENTS & APPOINTMENTS
    BEGIN
        ALTER TABLE queue_management.queue_tokens
        ADD CONSTRAINT fk_queue_patient 
        FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE CASCADE;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

    BEGIN
        ALTER TABLE queue_management.queue_tokens
        ADD CONSTRAINT fk_queue_appointment 
        FOREIGN KEY (appointment_id) REFERENCES appointment.appointments(appointment_id) ON DELETE SET NULL;
    EXCEPTION WHEN duplicate_object THEN NULL; END;

END $$;

-- =============================================================================
-- SECTION 2: HIGH-PERFORMANCE B-TREE INDEXES
-- Purpose: Accelerate lookups on high-cardinality keys, foreign keys, and dates.
-- =============================================================================

-- Patient Indexes
CREATE INDEX IF NOT EXISTS idx_patients_mrn ON patient.patients(mrn);
CREATE INDEX IF NOT EXISTS idx_patient_contacts_value ON patient.patient_contacts(contact_value);
CREATE INDEX IF NOT EXISTS idx_patients_name ON patient.patients(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_patients_created_at ON patient.patients(created_at);

-- Doctor Indexes
CREATE INDEX IF NOT EXISTS idx_doctors_employee_id ON doctor.doctors(employee_id);
CREATE INDEX IF NOT EXISTS idx_doctors_department_id ON doctor.doctors(department_id);
CREATE INDEX IF NOT EXISTS idx_doctors_doctor_code ON doctor.doctors(doctor_code);
CREATE INDEX IF NOT EXISTS idx_doctors_email ON doctor.doctors(email);
CREATE INDEX IF NOT EXISTS idx_doctors_status ON doctor.doctors(status_id);

-- Appointment Indexes
CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointment.appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_id ON appointment.appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointment.appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointment.appointments(appointment_status_id);
CREATE INDEX IF NOT EXISTS idx_appointments_tenant_id ON appointment.appointments(tenant_id);

-- EMR & Clinical Notes Indexes
CREATE INDEX IF NOT EXISTS idx_encounters_patient_id ON electronic_medical_records.patient_encounters(patient_id);
CREATE INDEX IF NOT EXISTS idx_encounters_doctor_id ON electronic_medical_records.patient_encounters(doctor_id);
CREATE INDEX IF NOT EXISTS idx_encounters_appointment_id ON electronic_medical_records.patient_encounters(appointment_id);
CREATE INDEX IF NOT EXISTS idx_encounters_date ON electronic_medical_records.patient_encounters(encounter_date);
CREATE INDEX IF NOT EXISTS idx_clinical_notes_encounter ON electronic_medical_records.clinical_notes(encounter_id);
CREATE INDEX IF NOT EXISTS idx_vital_signs_encounter ON electronic_medical_records.vital_signs(encounter_id);

-- Billing & Invoices Indexes
CREATE INDEX IF NOT EXISTS idx_invoices_patient_id ON billing.invoices(patient_id);
CREATE INDEX IF NOT EXISTS idx_invoices_encounter_id ON billing.invoices(encounter_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON billing.invoices(billing_status_id);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON billing.invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON billing.payments(invoice_id);

-- Pharmacy Indexes
CREATE INDEX IF NOT EXISTS idx_prescriptions_patient_id ON pharmacy.prescriptions(patient_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor_id ON pharmacy.prescriptions(doctor_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_date ON pharmacy.prescriptions(prescription_date);
CREATE INDEX IF NOT EXISTS idx_dispensing_prescription_id ON pharmacy.dispensing_records(prescription_id);

-- Laboratory Indexes
CREATE INDEX IF NOT EXISTS idx_lab_orders_patient_id ON laboratory.lab_orders(patient_id);
CREATE INDEX IF NOT EXISTS idx_lab_orders_doctor_id ON laboratory.lab_orders(doctor_id);
CREATE INDEX IF NOT EXISTS idx_lab_results_order_item_id ON laboratory.lab_result_entries(order_item_id);

-- Radiology Indexes
CREATE INDEX IF NOT EXISTS idx_radiology_orders_patient_id ON radiology.radiology_orders(patient_id);
CREATE INDEX IF NOT EXISTS idx_radiology_orders_doctor_id ON radiology.radiology_orders(doctor_id);
CREATE INDEX IF NOT EXISTS idx_radiology_reports_study_id ON radiology.radiology_reports(study_id);

-- Admission Indexes
CREATE INDEX IF NOT EXISTS idx_admissions_patient_id ON admission.admissions(patient_id);
CREATE INDEX IF NOT EXISTS idx_admissions_doctor_id ON admission.admissions(admitting_doctor_id);
CREATE INDEX IF NOT EXISTS idx_admissions_status ON admission.admissions(admission_status_id);
CREATE INDEX IF NOT EXISTS idx_bed_allocations_admission ON admission.bed_allocations(admission_id);

-- Emergency Indexes
CREATE INDEX IF NOT EXISTS idx_emergency_arrivals_patient_id ON emergency.emergency_arrivals(patient_id);
CREATE INDEX IF NOT EXISTS idx_emergency_reg_arrival_id ON emergency.emergency_registrations(emergency_arrival_id);

-- HR & Security Indexes
CREATE INDEX IF NOT EXISTS idx_employees_number ON human_resources.employees(employee_number);
CREATE INDEX IF NOT EXISTS idx_employees_dept ON human_resources.employees(department_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON security.users(username);
CREATE INDEX IF NOT EXISTS idx_users_employee ON security.users(employee_id);
