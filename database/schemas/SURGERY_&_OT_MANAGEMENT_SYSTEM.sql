-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 13: SURGERY & OPERATION THEATRE (OT) MANAGEMENT
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS surgery;
SET search_path TO surgery, public;

-- =========================================================
-- SURGERY MASTER TABLES
-- =========================================================

CREATE TABLE surgery_departments (
    surgery_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE surgery_specialties (
    specialty_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    specialty_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE operating_theatres (
    operating_theatre_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    theatre_code VARCHAR(100) UNIQUE NOT NULL,

    theatre_name VARCHAR(255),

    theatre_type VARCHAR(100),

    floor_number VARCHAR(50),

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ot_rooms (
    ot_room_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    operating_theatre_id UUID,

    room_number VARCHAR(100),

    room_type VARCHAR(100),

    room_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (operating_theatre_id)
        REFERENCES operating_theatres(operating_theatre_id)
);

CREATE TABLE ot_room_configurations (
    room_configuration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ot_room_id UUID,

    airflow_type VARCHAR(100),

    sterility_level VARCHAR(100),

    negative_pressure_supported BOOLEAN DEFAULT FALSE,

    robotic_surgery_supported BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ot_room_id)
        REFERENCES ot_rooms(ot_room_id)
);

-- =========================================================
-- OT EQUIPMENT MANAGEMENT
-- =========================================================

CREATE TABLE ot_equipment (
    equipment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    equipment_code VARCHAR(100) UNIQUE NOT NULL,

    equipment_name VARCHAR(255),

    equipment_category VARCHAR(255),

    manufacturer_name VARCHAR(255),

    serial_number VARCHAR(255),

    ot_room_id UUID,

    equipment_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ot_room_id)
        REFERENCES ot_rooms(ot_room_id)
);

CREATE TABLE ot_equipment_maintenance (
    maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    equipment_id UUID,

    maintenance_type VARCHAR(100),

    maintenance_notes TEXT,

    maintenance_date TIMESTAMP,

    next_due_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (equipment_id)
        REFERENCES ot_equipment(equipment_id)
);

-- =========================================================
-- SURGICAL STAFF MANAGEMENT
-- =========================================================

CREATE TABLE surgeons (
    surgeon_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID,

    specialty_id UUID,

    surgeon_code VARCHAR(100),

    years_of_experience INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (specialty_id)
        REFERENCES surgery_specialties(specialty_id)
);

CREATE TABLE anesthesiologists (
    anesthesiologist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID,

    qualification VARCHAR(255),

    years_of_experience INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE surgical_teams (
    surgical_team_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    team_name VARCHAR(255),

    specialty_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (specialty_id)
        REFERENCES surgery_specialties(specialty_id)
);

CREATE TABLE surgical_team_members (
    team_member_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgical_team_id UUID,

    member_role VARCHAR(100),

    member_reference_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgical_team_id)
        REFERENCES surgical_teams(surgical_team_id)
);

CREATE TABLE ot_staff_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ot_room_id UUID,

    staff_reference_id UUID,

    staff_role VARCHAR(100),

    assigned_from TIMESTAMP,

    assigned_to TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ot_room_id)
        REFERENCES ot_rooms(ot_room_id)
);

-- =========================================================
-- SURGERY TYPES & PROCEDURES
-- =========================================================

CREATE TABLE surgery_categories (
    surgery_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_name VARCHAR(255),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE surgery_types (
    surgery_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_category_id UUID,

    surgery_type_name VARCHAR(255),

    complexity_level VARCHAR(100),

    average_duration_minutes INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_category_id)
        REFERENCES surgery_categories(surgery_category_id)
);

CREATE TABLE surgical_procedures (
    procedure_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_type_id UUID,

    procedure_code VARCHAR(100),

    procedure_name VARCHAR(255),

    procedure_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_type_id)
        REFERENCES surgery_types(surgery_type_id)
);

CREATE TABLE procedure_checklists (
    checklist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    procedure_id UUID,

    checklist_item TEXT,

    is_mandatory BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (procedure_id)
        REFERENCES surgical_procedures(procedure_id)
);

CREATE TABLE surgery_risk_assessments (
    risk_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    procedure_id UUID,

    asa_score VARCHAR(50),

    risk_level VARCHAR(100),

    assessment_notes TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (procedure_id)
        REFERENCES surgical_procedures(procedure_id)
);

-- =========================================================
-- SURGERY REQUEST & SCHEDULING
-- =========================================================

CREATE TABLE surgery_requests (
    surgery_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    requested_by UUID,

    procedure_id UUID,

    request_priority VARCHAR(100),

    request_reason TEXT,

    requested_date TIMESTAMP,

    request_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (procedure_id)
        REFERENCES surgical_procedures(procedure_id)
);

CREATE TABLE surgery_scheduling (
    surgery_schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_request_id UUID,

    ot_room_id UUID,

    surgical_team_id UUID,

    anesthesiologist_id UUID,

    scheduled_start TIMESTAMP,

    scheduled_end TIMESTAMP,

    schedule_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_request_id)
        REFERENCES surgery_requests(surgery_request_id),

    FOREIGN KEY (ot_room_id)
        REFERENCES ot_rooms(ot_room_id),

    FOREIGN KEY (surgical_team_id)
        REFERENCES surgical_teams(surgical_team_id),

    FOREIGN KEY (anesthesiologist_id)
        REFERENCES anesthesiologists(anesthesiologist_id)
);

CREATE TABLE surgery_waitlists (
    waitlist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_request_id UUID,

    waitlist_priority VARCHAR(100),

    expected_surgery_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_request_id)
        REFERENCES surgery_requests(surgery_request_id)
);

CREATE TABLE ot_booking_slots (
    booking_slot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ot_room_id UUID,

    slot_start TIMESTAMP,

    slot_end TIMESTAMP,

    slot_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ot_room_id)
        REFERENCES ot_rooms(ot_room_id)
);

CREATE TABLE ot_calendar_management (
    calendar_entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ot_room_id UUID,

    calendar_date DATE,

    schedule_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ot_room_id)
        REFERENCES ot_rooms(ot_room_id)
);

-- =========================================================
-- PREOPERATIVE MANAGEMENT
-- =========================================================

CREATE TABLE preoperative_assessments (
    preoperative_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_request_id UUID,

    assessment_notes TEXT,

    fasting_status VARCHAR(100),

    allergies_checked BOOLEAN DEFAULT FALSE,

    assessed_by UUID,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_request_id)
        REFERENCES surgery_requests(surgery_request_id)
);

CREATE TABLE anesthesia_assessments (
    anesthesia_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_request_id UUID,

    anesthesia_type VARCHAR(100),

    airway_assessment TEXT,

    asa_classification VARCHAR(50),

    assessment_notes TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_request_id)
        REFERENCES surgery_requests(surgery_request_id)
);

CREATE TABLE consent_forms (
    consent_form_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_request_id UUID,

    consent_type VARCHAR(100),

    signed_by VARCHAR(255),

    signed_at TIMESTAMP,

    document_path TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_request_id)
        REFERENCES surgery_requests(surgery_request_id)
);

CREATE TABLE surgical_clearances (
    clearance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_request_id UUID,

    clearance_type VARCHAR(100),

    clearance_status VARCHAR(100),

    cleared_by UUID,

    cleared_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_request_id)
        REFERENCES surgery_requests(surgery_request_id)
);

CREATE TABLE preoperative_checklists (
    checklist_entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_request_id UUID,

    checklist_item TEXT,

    completion_status BOOLEAN DEFAULT FALSE,

    completed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_request_id)
        REFERENCES surgery_requests(surgery_request_id)
);

-- =========================================================
-- ANESTHESIA MANAGEMENT
-- =========================================================

CREATE TABLE anesthesia_records (
    anesthesia_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    anesthesia_type VARCHAR(100),

    anesthesia_start TIMESTAMP,

    anesthesia_end TIMESTAMP,

    anesthesiologist_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id),

    FOREIGN KEY (anesthesiologist_id)
        REFERENCES anesthesiologists(anesthesiologist_id)
);

CREATE TABLE anesthesia_medications (
    anesthesia_medication_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    anesthesia_record_id UUID,

    medication_name VARCHAR(255),

    dosage VARCHAR(100),

    administered_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (anesthesia_record_id)
        REFERENCES anesthesia_records(anesthesia_record_id)
);

CREATE TABLE anesthesia_monitoring (
    anesthesia_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    anesthesia_record_id UUID,

    heart_rate INT,

    blood_pressure VARCHAR(100),

    oxygen_saturation NUMERIC(5,2),

    monitoring_notes TEXT,

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (anesthesia_record_id)
        REFERENCES anesthesia_records(anesthesia_record_id)
);

CREATE TABLE airway_management (
    airway_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    anesthesia_record_id UUID,

    airway_device VARCHAR(255),

    intubation_time TIMESTAMP,

    extubation_time TIMESTAMP,

    airway_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (anesthesia_record_id)
        REFERENCES anesthesia_records(anesthesia_record_id)
);

-- =========================================================
-- INTRAOPERATIVE MANAGEMENT
-- =========================================================

CREATE TABLE intraoperative_records (
    intraoperative_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    surgery_start TIMESTAMP,

    surgery_end TIMESTAMP,

    intraoperative_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE surgical_notes (
    surgical_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    intraoperative_record_id UUID,

    operative_findings TEXT,

    procedure_performed TEXT,

    complications TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (intraoperative_record_id)
        REFERENCES intraoperative_records(intraoperative_record_id)
);

CREATE TABLE implant_usage (
    implant_usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    intraoperative_record_id UUID,

    implant_name VARCHAR(255),

    implant_serial_number VARCHAR(255),

    implant_manufacturer VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (intraoperative_record_id)
        REFERENCES intraoperative_records(intraoperative_record_id)
);

CREATE TABLE surgical_instruments_tracking (
    instrument_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    intraoperative_record_id UUID,

    instrument_name VARCHAR(255),

    sterilization_status VARCHAR(100),

    used_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (intraoperative_record_id)
        REFERENCES intraoperative_records(intraoperative_record_id)
);

CREATE TABLE surgical_counts (
    surgical_count_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    intraoperative_record_id UUID,

    count_type VARCHAR(100),

    initial_count INT,

    final_count INT,

    count_verified BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (intraoperative_record_id)
        REFERENCES intraoperative_records(intraoperative_record_id)
);

CREATE TABLE blood_usage_tracking (
    blood_usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    intraoperative_record_id UUID,

    blood_product_type VARCHAR(100),

    units_used INT,

    transfusion_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (intraoperative_record_id)
        REFERENCES intraoperative_records(intraoperative_record_id)
);

-- =========================================================
-- POSTOPERATIVE MANAGEMENT
-- =========================================================

CREATE TABLE postoperative_notes (
    postoperative_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    postoperative_condition TEXT,

    recovery_status VARCHAR(100),

    postoperative_instructions TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE recovery_room_management (
    recovery_room_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    admitted_to_recovery_at TIMESTAMP,

    discharged_from_recovery_at TIMESTAMP,

    recovery_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE postoperative_complications (
    complication_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    complication_type VARCHAR(255),

    complication_description TEXT,

    occurred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE pain_management_records (
    pain_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    pain_score INT,

    medication_given VARCHAR(255),

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE discharge_from_ot (
    discharge_ot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    discharge_destination VARCHAR(255),

    discharge_time TIMESTAMP,

    discharge_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

-- =========================================================
-- CSSD & STERILIZATION
-- =========================================================

CREATE TABLE cssd_requests (
    cssd_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ot_room_id UUID,

    requested_items TEXT,

    request_status VARCHAR(100),

    requested_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ot_room_id)
        REFERENCES ot_rooms(ot_room_id)
);

CREATE TABLE sterilization_tracking (
    sterilization_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instrument_set_name VARCHAR(255),

    sterilization_method VARCHAR(100),

    sterilized_at TIMESTAMP,

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE instrument_sterility_logs (
    sterility_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sterilization_tracking_id UUID,

    instrument_name VARCHAR(255),

    sterility_status VARCHAR(100),

    logged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sterilization_tracking_id)
        REFERENCES sterilization_tracking(sterilization_tracking_id)
);

-- =========================================================
-- SURGICAL MEDIA & ADVANCED SYSTEMS
-- =========================================================

CREATE TABLE surgical_images (
    surgical_image_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    image_type VARCHAR(100),

    image_path TEXT,

    captured_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE surgery_video_recordings (
    surgery_video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    video_path TEXT,

    recording_duration VARCHAR(100),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE robotic_surgery_logs (
    robotic_surgery_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    robotic_system_name VARCHAR(255),

    robotic_session_notes TEXT,

    logged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE navigation_system_logs (
    navigation_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    navigation_system_name VARCHAR(255),

    navigation_notes TEXT,

    logged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

-- =========================================================
-- BILLING & INSURANCE
-- =========================================================

CREATE TABLE surgical_billing (
    surgical_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    billing_amount NUMERIC(14,2),

    billing_status VARCHAR(100),

    invoice_reference VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE implant_billing (
    implant_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    implant_usage_id UUID,

    implant_cost NUMERIC(14,2),

    billing_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (implant_usage_id)
        REFERENCES implant_usage(implant_usage_id)
);

CREATE TABLE insurance_surgery_claims (
    insurance_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgical_billing_id UUID,

    insurance_provider VARCHAR(255),

    claim_amount NUMERIC(14,2),

    approved_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgical_billing_id)
        REFERENCES surgical_billing(surgical_billing_id)
);

-- =========================================================
-- QUALITY & INCIDENT MANAGEMENT
-- =========================================================

CREATE TABLE surgery_quality_metrics (
    quality_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    metric_name VARCHAR(255),

    metric_value NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE morbidity_mortality_reviews (
    review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    review_notes TEXT,

    reviewed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

CREATE TABLE surgical_incident_reports (
    incident_report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    surgery_schedule_id UUID,

    incident_type VARCHAR(255),

    incident_description TEXT,

    severity_level VARCHAR(100),

    occurred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (surgery_schedule_id)
        REFERENCES surgery_scheduling(surgery_schedule_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE ot_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ot_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    table_name VARCHAR(255),

    record_id UUID,

    changed_field VARCHAR(255),

    old_value TEXT,

    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- END OF SURGERY & OT MANAGEMENT SYSTEM
-- =========================================================