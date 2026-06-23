-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 4: APPOINTMENT MANAGEMENT
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS appointment;
SET search_path TO appointment, public;

-- =========================================================
-- MASTER TABLES
-- =========================================================

CREATE TABLE appointment_statuses (
    appointment_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Scheduled
-- Confirmed
-- Checked-In
-- Completed
-- Cancelled
-- No Show


CREATE TABLE appointment_types (
    appointment_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_name VARCHAR(100) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- OPD
-- Follow-Up
-- Emergency
-- Teleconsultation


CREATE TABLE appointment_priorities (
    priority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    priority_name VARCHAR(100) UNIQUE NOT NULL,

    priority_level INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Low
-- Normal
-- High
-- Critical


CREATE TABLE cancellation_reasons (
    cancellation_reason_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    reason_name VARCHAR(255) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- APPOINTMENTS
-- =========================================================

CREATE TABLE appointments (
    appointment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tenant_id UUID,

    appointment_number VARCHAR(100) UNIQUE NOT NULL,

    patient_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    department_id UUID,

    appointment_type_id UUID,

    appointment_status_id UUID NOT NULL,

    priority_id UUID,

    appointment_date DATE NOT NULL,

    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    estimated_duration_minutes INT,

    chief_complaint TEXT,

    notes TEXT,

    is_first_visit BOOLEAN DEFAULT FALSE,

    requires_followup BOOLEAN DEFAULT FALSE,

    booking_source VARCHAR(100),

    booked_by UUID,

    booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    confirmed_at TIMESTAMP,

    checked_in_at TIMESTAMP,

    completed_at TIMESTAMP,

    cancelled_at TIMESTAMP,

    cancellation_reason_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_by UUID,
    updated_by UUID,

    deleted_at TIMESTAMP NULL,

    FOREIGN KEY (appointment_type_id)
        REFERENCES appointment_types(appointment_type_id),

    FOREIGN KEY (appointment_status_id)
        REFERENCES appointment_statuses(appointment_status_id),

    FOREIGN KEY (priority_id)
        REFERENCES appointment_priorities(priority_id),

    FOREIGN KEY (cancellation_reason_id)
        REFERENCES cancellation_reasons(cancellation_reason_id)

);

-- patient_id references patients(patient_id)
-- doctor_id references doctors(doctor_id)
-- department_id references departments(department_id)


-- =========================================================
-- APPOINTMENT SLOTS
-- =========================================================

CREATE TABLE appointment_slots (
    slot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID NOT NULL,

    department_id UUID,

    slot_date DATE NOT NULL,

    slot_start_time TIME NOT NULL,
    slot_end_time TIME NOT NULL,

    slot_duration_minutes INT,

    max_bookings INT DEFAULT 1,

    booked_count INT DEFAULT 0,

    is_available BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- =========================================================
-- APPOINTMENT CHECK-INS
-- =========================================================

CREATE TABLE appointment_checkins (
    checkin_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    patient_id UUID NOT NULL,

    checked_in_by UUID,

    checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    queue_number VARCHAR(50),

    waiting_area VARCHAR(100),

    notes TEXT,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT RESCHEDULES
-- =========================================================

CREATE TABLE appointment_reschedules (
    reschedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    old_appointment_date DATE,
    old_start_time TIME,
    old_end_time TIME,

    new_appointment_date DATE,
    new_start_time TIME,
    new_end_time TIME,

    reschedule_reason TEXT,

    rescheduled_by UUID,

    rescheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT FOLLOWUPS
-- =========================================================

CREATE TABLE appointment_followups (
    followup_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    parent_appointment_id UUID NOT NULL,

    followup_appointment_id UUID NOT NULL,

    followup_reason TEXT,

    recommended_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE,

    FOREIGN KEY (followup_appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT REMINDERS
-- =========================================================

CREATE TABLE appointment_reminders (
    reminder_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    reminder_type VARCHAR(100),

    reminder_channel VARCHAR(100),

    scheduled_time TIMESTAMP,

    sent_time TIMESTAMP,

    delivery_status VARCHAR(100),

    message_content TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- Example Channels:
-- SMS
-- Email
-- WhatsApp
-- Push Notification


-- =========================================================
-- APPOINTMENT WAITLIST
-- =========================================================

CREATE TABLE appointment_waitlist (
    waitlist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    preferred_doctor_id UUID,

    preferred_department_id UUID,

    preferred_date DATE,

    priority_id UUID,

    notes TEXT,

    waitlist_status VARCHAR(100),

    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- =========================================================
-- APPOINTMENT QUEUES
-- =========================================================

CREATE TABLE appointment_queues (
    queue_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID,

    doctor_id UUID,

    appointment_id UUID,

    queue_number VARCHAR(50),

    queue_position INT,

    queue_status VARCHAR(100),

    called_at TIMESTAMP,

    completed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT PAYMENTS
-- =========================================================

CREATE TABLE appointment_payments (
    appointment_payment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    bill_id UUID,

    payment_amount NUMERIC(12,2),

    payment_status VARCHAR(100),

    payment_method VARCHAR(100),

    paid_at TIMESTAMP,

    transaction_reference VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- bill_id should later reference bills(bill_id)


-- =========================================================
-- TELEMEDICINE APPOINTMENTS
-- =========================================================

CREATE TABLE telemedicine_appointments (
    telemedicine_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    meeting_provider VARCHAR(100),

    meeting_link TEXT,

    meeting_id VARCHAR(255),

    meeting_password VARCHAR(255),

    session_started_at TIMESTAMP,
    session_ended_at TIMESTAMP,

    session_recording_link TEXT,

    technical_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT DOCUMENTS
-- =========================================================

CREATE TABLE appointment_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    document_name VARCHAR(255),

    document_type VARCHAR(100),

    file_path TEXT NOT NULL,

    mime_type VARCHAR(100),

    file_size BIGINT,

    uploaded_by UUID,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT NOTES
-- =========================================================

CREATE TABLE appointment_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    note_type VARCHAR(100),

    note_text TEXT,

    added_by UUID,

    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT AUDIT LOGS
-- =========================================================

CREATE TABLE appointment_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(100),

    device_info TEXT,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- APPOINTMENT CHANGE HISTORY
-- =========================================================

CREATE TABLE appointment_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appointment_id UUID NOT NULL,

    changed_field VARCHAR(255),

    old_value TEXT,
    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id)
        REFERENCES appointments(appointment_id)
        ON DELETE CASCADE
);

-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_appointments_number
ON appointments(appointment_number);

CREATE INDEX idx_appointments_patient
ON appointments(patient_id);

CREATE INDEX idx_appointments_doctor
ON appointments(doctor_id);

CREATE INDEX idx_appointments_department
ON appointments(department_id);

CREATE INDEX idx_appointments_date
ON appointments(appointment_date);

CREATE INDEX idx_appointment_slots_doctor
ON appointment_slots(doctor_id);

CREATE INDEX idx_appointment_slots_date
ON appointment_slots(slot_date);

CREATE INDEX idx_appointment_checkins_appointment
ON appointment_checkins(appointment_id);

CREATE INDEX idx_appointment_reschedules_appointment
ON appointment_reschedules(appointment_id);

CREATE INDEX idx_appointment_followups_parent
ON appointment_followups(parent_appointment_id);

CREATE INDEX idx_appointment_reminders_appointment
ON appointment_reminders(appointment_id);

CREATE INDEX idx_appointment_queues_appointment
ON appointment_queues(appointment_id);

CREATE INDEX idx_appointment_payments_appointment
ON appointment_payments(appointment_id);

CREATE INDEX idx_telemedicine_appointments_appointment
ON telemedicine_appointments(appointment_id);

CREATE INDEX idx_appointment_documents_appointment
ON appointment_documents(appointment_id);

CREATE INDEX idx_appointment_notes_appointment
ON appointment_notes(appointment_id);

CREATE INDEX idx_appointment_audit_logs_appointment
ON appointment_audit_logs(appointment_id);

-- =========================================================
-- HIGH-LEVEL RELATIONSHIP FLOW
-- =========================================================

/*

appointments
│
├── appointment_statuses
├── appointment_types
├── appointment_priorities
├── cancellation_reasons
├── appointment_slots
├── appointment_checkins
├── appointment_reschedules
├── appointment_followups
├── appointment_reminders
├── appointment_waitlist
├── appointment_queues
├── appointment_payments
├── telemedicine_appointments
├── appointment_documents
├── appointment_notes
├── appointment_audit_logs
└── appointment_change_history

Relationships:
appointments
    ├── patients
    ├── doctors
    ├── departments
    └── billing

*/

-- =========================================================
-- END OF APPOINTMENT MANAGEMENT SCHEMA
-- =========================================================