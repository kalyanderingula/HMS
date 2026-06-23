-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 6: ADMISSION & BED MANAGEMENT
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS admission;
SET search_path TO admission, public;

-- =========================================================
-- MASTER TABLES
-- =========================================================

CREATE TABLE admission_statuses (
    admission_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Admitted
-- Under Observation
-- Discharged
-- Transferred
-- Cancelled


CREATE TABLE admission_types (
    admission_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_name VARCHAR(100) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Emergency
-- Elective
-- ICU
-- Maternity


CREATE TABLE bed_statuses (
    bed_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Available
-- Occupied
-- Reserved
-- Maintenance
-- Cleaning


CREATE TABLE room_types (
    room_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- General Ward
-- Semi Private
-- Private
-- ICU
-- Deluxe


CREATE TABLE transfer_reasons (
    transfer_reason_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    reason_name VARCHAR(255) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- WARDS
-- =========================================================

CREATE TABLE wards (
    ward_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID,

    ward_code VARCHAR(100) UNIQUE NOT NULL,

    ward_name VARCHAR(255) NOT NULL,

    floor_number VARCHAR(50),

    building_name VARCHAR(255),

    total_rooms INT DEFAULT 0,

    total_beds INT DEFAULT 0,

    ward_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- department_id references departments(department_id)


-- =========================================================
-- ROOMS
-- =========================================================

CREATE TABLE rooms (
    room_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ward_id UUID NOT NULL,

    room_number VARCHAR(100) UNIQUE NOT NULL,

    room_type_id UUID,

    room_status VARCHAR(100),

    floor_number VARCHAR(50),

    capacity INT DEFAULT 1,

    current_occupancy INT DEFAULT 0,

    daily_charge NUMERIC(12,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ward_id)
        REFERENCES wards(ward_id)
        ON DELETE CASCADE,

    FOREIGN KEY (room_type_id)
        REFERENCES room_types(room_type_id)
);

-- =========================================================
-- BEDS
-- =========================================================

CREATE TABLE beds (
    bed_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    room_id UUID NOT NULL,

    bed_number VARCHAR(100) NOT NULL,

    bed_status_id UUID,

    bed_type VARCHAR(100),

    is_icu BOOLEAN DEFAULT FALSE,

    daily_charge NUMERIC(12,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id)
        ON DELETE CASCADE,

    FOREIGN KEY (bed_status_id)
        REFERENCES bed_statuses(bed_status_id)
);

-- =========================================================
-- ADMISSIONS
-- =========================================================

CREATE TABLE admissions (
    admission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tenant_id UUID,

    admission_number VARCHAR(100) UNIQUE NOT NULL,

    patient_id UUID NOT NULL,

    encounter_id UUID,

    admission_type_id UUID,

    admission_status_id UUID,

    admitting_doctor_id UUID,

    department_id UUID,

    ward_id UUID,

    room_id UUID,

    bed_id UUID,

    admission_reason TEXT,

    admission_date TIMESTAMP NOT NULL,

    expected_discharge_date DATE,

    actual_discharge_date TIMESTAMP,

    discharge_summary TEXT,

    discharge_condition TEXT,

    referred_by VARCHAR(255),

    emergency_contact_name VARCHAR(255),

    emergency_contact_phone VARCHAR(20),

    insurance_approval_status VARCHAR(100),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_by UUID,
    updated_by UUID,

    deleted_at TIMESTAMP NULL,

    FOREIGN KEY (admission_type_id)
        REFERENCES admission_types(admission_type_id),

    FOREIGN KEY (admission_status_id)
        REFERENCES admission_statuses(admission_status_id),

    FOREIGN KEY (ward_id)
        REFERENCES wards(ward_id),

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id),

    FOREIGN KEY (bed_id)
        REFERENCES beds(bed_id)
);

-- patient_id references patients(patient_id)
-- encounter_id references patient_encounters(encounter_id)
-- admitting_doctor_id references doctors(doctor_id)
-- department_id references departments(department_id)


-- =========================================================
-- BED ALLOCATIONS
-- =========================================================

CREATE TABLE bed_allocations (
    bed_allocation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    bed_id UUID NOT NULL,

    allocated_from TIMESTAMP NOT NULL,

    allocated_to TIMESTAMP,

    allocation_status VARCHAR(100),

    allocated_by UUID,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE,

    FOREIGN KEY (bed_id)
        REFERENCES beds(bed_id)
);

-- =========================================================
-- BED TRANSFERS
-- =========================================================

CREATE TABLE bed_transfers (
    transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    from_bed_id UUID,

    to_bed_id UUID,

    from_room_id UUID,
    to_room_id UUID,

    from_ward_id UUID,
    to_ward_id UUID,

    transfer_reason_id UUID,

    transfer_notes TEXT,

    transferred_by UUID,

    transferred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE,

    FOREIGN KEY (transfer_reason_id)
        REFERENCES transfer_reasons(transfer_reason_id)
);

-- =========================================================
-- ROOM MAINTENANCE
-- =========================================================

CREATE TABLE room_maintenance (
    maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    room_id UUID NOT NULL,

    maintenance_type VARCHAR(100),

    maintenance_description TEXT,

    maintenance_status VARCHAR(100),

    reported_by UUID,

    maintenance_start TIMESTAMP,

    maintenance_end TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id)
        ON DELETE CASCADE
);

-- =========================================================
-- BED MAINTENANCE
-- =========================================================

CREATE TABLE bed_maintenance (
    bed_maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    bed_id UUID NOT NULL,

    maintenance_type VARCHAR(100),

    maintenance_description TEXT,

    maintenance_status VARCHAR(100),

    maintenance_start TIMESTAMP,

    maintenance_end TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (bed_id)
        REFERENCES beds(bed_id)
        ON DELETE CASCADE
);

-- =========================================================
-- ADMISSION DOCUMENTS
-- =========================================================

CREATE TABLE admission_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    document_name VARCHAR(255),

    document_type VARCHAR(100),

    file_path TEXT NOT NULL,

    mime_type VARCHAR(100),

    file_size BIGINT,

    uploaded_by UUID,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE
);

-- =========================================================
-- ADMISSION NOTES
-- =========================================================

CREATE TABLE admission_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    note_type VARCHAR(100),

    note_text TEXT,

    added_by UUID,

    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DISCHARGE PLANS
-- =========================================================

CREATE TABLE discharge_plans (
    discharge_plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    discharge_plan TEXT,

    medications TEXT,

    followup_instructions TEXT,

    home_care_instructions TEXT,

    planned_discharge_date DATE,

    approved_by UUID,

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE
);

-- =========================================================
-- ADMISSION BILLING
-- =========================================================

CREATE TABLE admission_billing (
    admission_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    billing_reference VARCHAR(255),

    total_room_charges NUMERIC(14,2),

    total_bed_charges NUMERIC(14,2),

    total_service_charges NUMERIC(14,2),

    insurance_coverage NUMERIC(14,2),

    patient_payable NUMERIC(14,2),

    billing_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE
);

-- =========================================================
-- ADMISSION AUDIT LOGS
-- =========================================================

CREATE TABLE admission_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(100),

    device_info TEXT,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE
);

-- =========================================================
-- ADMISSION CHANGE HISTORY
-- =========================================================

CREATE TABLE admission_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    admission_id UUID NOT NULL,

    changed_field VARCHAR(255),

    old_value TEXT,
    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id)
        REFERENCES admissions(admission_id)
        ON DELETE CASCADE
);

-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_wards_department
ON wards(department_id);

CREATE INDEX idx_rooms_ward
ON rooms(ward_id);

CREATE INDEX idx_beds_room
ON beds(room_id);

CREATE INDEX idx_admissions_patient
ON admissions(patient_id);

CREATE INDEX idx_admissions_doctor
ON admissions(admitting_doctor_id);

CREATE INDEX idx_admissions_department
ON admissions(department_id);

CREATE INDEX idx_admissions_ward
ON admissions(ward_id);

CREATE INDEX idx_admissions_room
ON admissions(room_id);

CREATE INDEX idx_admissions_bed
ON admissions(bed_id);

CREATE INDEX idx_bed_allocations_admission
ON bed_allocations(admission_id);

CREATE INDEX idx_bed_transfers_admission
ON bed_transfers(admission_id);

CREATE INDEX idx_room_maintenance_room
ON room_maintenance(room_id);

CREATE INDEX idx_bed_maintenance_bed
ON bed_maintenance(bed_id);

CREATE INDEX idx_admission_documents_admission
ON admission_documents(admission_id);

CREATE INDEX idx_admission_notes_admission
ON admission_notes(admission_id);

CREATE INDEX idx_discharge_plans_admission
ON discharge_plans(admission_id);

CREATE INDEX idx_admission_billing_admission
ON admission_billing(admission_id);

CREATE INDEX idx_admission_audit_logs_admission
ON admission_audit_logs(admission_id);

-- =========================================================
-- HIGH-LEVEL RELATIONSHIP FLOW
-- =========================================================

/*

wards
│
└── rooms
      │
      └── beds
             │
             ├── bed_allocations
             ├── bed_transfers
             └── bed_maintenance

admissions
│
├── patients
├── doctors
├── departments
├── wards
├── rooms
├── beds
├── admission_documents
├── admission_notes
├── discharge_plans
├── admission_billing
├── admission_audit_logs
└── admission_change_history

*/

-- =========================================================
-- END OF ADMISSION & BED MANAGEMENT SCHEMA
-- =========================================================