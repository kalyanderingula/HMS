-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 11: NURSING MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS nursing;
SET search_path TO nursing, public;

-- =========================================================
-- NURSING MASTER TABLES
-- =========================================================

CREATE TABLE nursing_departments (
    nursing_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE nursing_units (
    nursing_unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nursing_department_id UUID,

    unit_code VARCHAR(100) UNIQUE NOT NULL,

    unit_name VARCHAR(255),

    floor_number VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nursing_department_id)
        REFERENCES nursing_departments(nursing_department_id)
);

CREATE TABLE nursing_stations (
    nursing_station_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nursing_unit_id UUID,

    station_name VARCHAR(255),

    station_location VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nursing_unit_id)
        REFERENCES nursing_units(nursing_unit_id)
);

CREATE TABLE nursing_shifts (
    nursing_shift_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    shift_name VARCHAR(100),

    start_time TIME,

    end_time TIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- NURSE MANAGEMENT
-- =========================================================

CREATE TABLE nurses (
    nurse_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    nurse_code VARCHAR(100) UNIQUE NOT NULL,

    first_name VARCHAR(255),

    last_name VARCHAR(255),

    gender VARCHAR(50),

    phone_number VARCHAR(50),

    email VARCHAR(255),

    hire_date DATE,

    employment_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE nurse_profiles (
    nurse_profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID UNIQUE,

    profile_photo TEXT,

    date_of_birth DATE,

    blood_group VARCHAR(20),

    address TEXT,

    emergency_contact TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
        ON DELETE CASCADE
);

CREATE TABLE nurse_qualifications (
    qualification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID,

    qualification_name VARCHAR(255),

    institution_name VARCHAR(255),

    completion_year INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nurse_certifications (
    certification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID,

    certification_name VARCHAR(255),

    issued_by VARCHAR(255),

    issue_date DATE,

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nurse_specializations (
    specialization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID,

    specialization_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nurse_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID,

    nursing_shift_id UUID,

    scheduled_date DATE,

    assigned_station_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id),

    FOREIGN KEY (nursing_shift_id)
        REFERENCES nursing_shifts(nursing_shift_id),

    FOREIGN KEY (assigned_station_id)
        REFERENCES nursing_stations(nursing_station_id)
);

CREATE TABLE nurse_attendance (
    attendance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID,

    attendance_date DATE,

    check_in_time TIMESTAMP,

    check_out_time TIMESTAMP,

    attendance_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nurse_leave_requests (
    leave_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID,

    leave_type VARCHAR(100),

    start_date DATE,

    end_date DATE,

    leave_reason TEXT,

    approval_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

-- =========================================================
-- SHIFT ASSIGNMENTS
-- =========================================================

CREATE TABLE nursing_shift_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nurse_id UUID,

    nursing_shift_id UUID,

    nursing_station_id UUID,

    assignment_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id),

    FOREIGN KEY (nursing_shift_id)
        REFERENCES nursing_shifts(nursing_shift_id),

    FOREIGN KEY (nursing_station_id)
        REFERENCES nursing_stations(nursing_station_id)
);

-- =========================================================
-- PATIENT NURSING ASSIGNMENTS
-- =========================================================

CREATE TABLE patient_nursing_assignments (
    patient_assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    nurse_id UUID,

    nursing_unit_id UUID,

    assigned_from TIMESTAMP,

    assigned_to TIMESTAMP,

    assignment_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id),

    FOREIGN KEY (nursing_unit_id)
        REFERENCES nursing_units(nursing_unit_id)
);

-- =========================================================
-- NURSING CARE
-- =========================================================

CREATE TABLE nursing_rounds (
    round_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    nurse_id UUID,

    round_time TIMESTAMP,

    round_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nursing_notes (
    nursing_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    nurse_id UUID,

    note_type VARCHAR(100),

    note_text TEXT,

    noted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nursing_observations (
    observation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    nurse_id UUID,

    observation_type VARCHAR(255),

    observation_value TEXT,

    observation_time TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nursing_care_plans (
    care_plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    nurse_id UUID,

    diagnosis TEXT,

    goals TEXT,

    interventions TEXT,

    evaluation_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nursing_interventions (
    intervention_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    care_plan_id UUID,

    intervention_name VARCHAR(255),

    intervention_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (care_plan_id)
        REFERENCES nursing_care_plans(care_plan_id),

    FOREIGN KEY (performed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nursing_tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    assigned_nurse_id UUID,

    task_name VARCHAR(255),

    task_priority VARCHAR(100),

    due_time TIMESTAMP,

    task_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assigned_nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE nursing_task_checklists (
    checklist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    task_id UUID,

    checklist_item TEXT,

    is_completed BOOLEAN DEFAULT FALSE,

    completed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id)
        REFERENCES nursing_tasks(task_id)
);

-- =========================================================
-- PATIENT ASSESSMENTS
-- =========================================================

CREATE TABLE vital_signs (
    vital_sign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    recorded_by UUID,

    temperature NUMERIC(5,2),

    pulse_rate INT,

    respiratory_rate INT,

    systolic_bp INT,

    diastolic_bp INT,

    oxygen_saturation NUMERIC(5,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (recorded_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE intake_output_records (
    io_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    recorded_by UUID,

    intake_type VARCHAR(100),

    intake_amount NUMERIC(10,2),

    output_type VARCHAR(100),

    output_amount NUMERIC(10,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (recorded_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE pain_assessments (
    pain_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    assessed_by UUID,

    pain_score INT,

    pain_location TEXT,

    pain_description TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assessed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE fall_risk_assessments (
    fall_risk_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    assessed_by UUID,

    fall_risk_score INT,

    risk_level VARCHAR(100),

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assessed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE braden_scale_assessments (
    braden_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    assessed_by UUID,

    braden_score INT,

    risk_level VARCHAR(100),

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assessed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE glasgow_coma_scale (
    gcs_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    assessed_by UUID,

    eye_response INT,

    verbal_response INT,

    motor_response INT,

    total_score INT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assessed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE early_warning_scores (
    ews_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    assessed_by UUID,

    total_score INT,

    risk_level VARCHAR(100),

    action_required TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assessed_by)
        REFERENCES nurses(nurse_id)
);

-- =========================================================
-- MEDICATION ADMINISTRATION
-- =========================================================

CREATE TABLE medication_administration_records (
    mar_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    prescription_item_id UUID,

    scheduled_time TIMESTAMP,

    administration_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE medication_administration_logs (
    administration_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    mar_id UUID,

    administered_by UUID,

    administered_at TIMESTAMP,

    dosage_given VARCHAR(255),

    administration_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (mar_id)
        REFERENCES medication_administration_records(mar_id),

    FOREIGN KEY (administered_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE infusion_records (
    infusion_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    medication_name VARCHAR(255),

    infusion_rate VARCHAR(100),

    started_at TIMESTAMP,

    ended_at TIMESTAMP,

    monitored_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (monitored_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE iv_line_management (
    iv_line_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    line_type VARCHAR(100),

    insertion_site VARCHAR(255),

    inserted_at TIMESTAMP,

    removed_at TIMESTAMP,

    managed_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (managed_by)
        REFERENCES nurses(nurse_id)
);

-- =========================================================
-- WOUND & DEVICE MANAGEMENT
-- =========================================================

CREATE TABLE wound_assessments (
    wound_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    assessed_by UUID,

    wound_type VARCHAR(255),

    wound_size VARCHAR(255),

    wound_status VARCHAR(100),

    assessment_notes TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (assessed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE dressing_changes (
    dressing_change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    wound_assessment_id UUID,

    changed_by UUID,

    dressing_type VARCHAR(255),

    changed_at TIMESTAMP,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (wound_assessment_id)
        REFERENCES wound_assessments(wound_assessment_id),

    FOREIGN KEY (changed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE catheter_management (
    catheter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    catheter_type VARCHAR(255),

    inserted_at TIMESTAMP,

    removed_at TIMESTAMP,

    managed_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (managed_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE ventilator_monitoring (
    ventilator_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    ventilator_mode VARCHAR(255),

    fio2 VARCHAR(100),

    peep VARCHAR(100),

    monitored_at TIMESTAMP,

    monitored_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (monitored_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE oxygen_therapy_records (
    oxygen_therapy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    oxygen_device VARCHAR(255),

    oxygen_flow_rate VARCHAR(100),

    started_at TIMESTAMP,

    monitored_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (monitored_by)
        REFERENCES nurses(nurse_id)
);

-- =========================================================
-- HANDOVER & DISCHARGE
-- =========================================================

CREATE TABLE nursing_handover_notes (
    handover_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    outgoing_nurse_id UUID,

    incoming_nurse_id UUID,

    handover_notes TEXT,

    handover_time TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (outgoing_nurse_id)
        REFERENCES nurses(nurse_id),

    FOREIGN KEY (incoming_nurse_id)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE discharge_nursing_summaries (
    discharge_summary_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    prepared_by UUID,

    discharge_summary TEXT,

    discharge_instructions TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prepared_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE patient_education_records (
    education_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    educated_by UUID,

    education_topic VARCHAR(255),

    education_notes TEXT,

    educated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (educated_by)
        REFERENCES nurses(nurse_id)
);

-- =========================================================
-- DEVICE & ALERT INTEGRATIONS
-- =========================================================

CREATE TABLE nurse_call_system_logs (
    nurse_call_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    nursing_station_id UUID,

    call_type VARCHAR(100),

    called_at TIMESTAMP,

    responded_at TIMESTAMP,

    response_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (nursing_station_id)
        REFERENCES nursing_stations(nursing_station_id)
);

CREATE TABLE bedside_monitor_integrations (
    monitor_integration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    device_identifier VARCHAR(255),

    integration_status VARCHAR(100),

    last_sync_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE device_alert_logs (
    device_alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    device_identifier VARCHAR(255),

    alert_type VARCHAR(255),

    alert_message TEXT,

    alert_time TIMESTAMP,

    acknowledged BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- QUALITY & INCIDENT MANAGEMENT
-- =========================================================

CREATE TABLE nursing_quality_metrics (
    quality_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    metric_name VARCHAR(255),

    metric_value NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE nursing_incident_reports (
    incident_report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    reported_by UUID,

    incident_type VARCHAR(255),

    incident_description TEXT,

    incident_time TIMESTAMP,

    severity_level VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reported_by)
        REFERENCES nurses(nurse_id)
);

CREATE TABLE infection_control_logs (
    infection_control_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    recorded_by UUID,

    infection_type VARCHAR(255),

    precautions TEXT,

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (recorded_by)
        REFERENCES nurses(nurse_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE nursing_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE nursing_change_history (
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
-- END OF NURSING MANAGEMENT SYSTEM SCHEMA
-- =========================================================