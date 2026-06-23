-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 14: EMERGENCY & TRAUMA MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS emergency;
SET search_path TO emergency, public;

-- =========================================================
-- EMERGENCY MASTER TABLES
-- =========================================================

CREATE TABLE emergency_departments (
    emergency_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE emergency_units (
    emergency_unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_department_id UUID,

    unit_code VARCHAR(100) UNIQUE NOT NULL,

    unit_name VARCHAR(255),

    unit_type VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_department_id)
        REFERENCES emergency_departments(emergency_department_id)
);

CREATE TABLE emergency_rooms (
    emergency_room_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_unit_id UUID,

    room_number VARCHAR(100),

    room_type VARCHAR(100),

    room_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_unit_id)
        REFERENCES emergency_units(emergency_unit_id)
);

CREATE TABLE trauma_bays (
    trauma_bay_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_room_id UUID,

    trauma_bay_code VARCHAR(100),

    trauma_level VARCHAR(100),

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_room_id)
        REFERENCES emergency_rooms(emergency_room_id)
);

CREATE TABLE resuscitation_rooms (
    resuscitation_room_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_room_id UUID,

    room_identifier VARCHAR(100),

    ventilator_supported BOOLEAN DEFAULT TRUE,

    cardiac_monitor_supported BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_room_id)
        REFERENCES emergency_rooms(emergency_room_id)
);

CREATE TABLE isolation_rooms (
    isolation_room_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_room_id UUID,

    isolation_type VARCHAR(100),

    negative_pressure_supported BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_room_id)
        REFERENCES emergency_rooms(emergency_room_id)
);

-- =========================================================
-- TRIAGE & ARRIVAL MANAGEMENT
-- =========================================================

CREATE TABLE emergency_triage_levels (
    triage_level_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    level_name VARCHAR(100),

    severity_rank INT,

    response_time_minutes INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE triage_protocols (
    triage_protocol_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    triage_level_id UUID,

    protocol_name VARCHAR(255),

    protocol_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (triage_level_id)
        REFERENCES emergency_triage_levels(triage_level_id)
);

CREATE TABLE emergency_arrivals (
    emergency_arrival_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    arrival_mode VARCHAR(100),

    arrival_time TIMESTAMP,

    brought_by VARCHAR(255),

    arrival_condition TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ambulance_arrivals (
    ambulance_arrival_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_arrival_id UUID,

    ambulance_reference VARCHAR(255),

    paramedic_notes TEXT,

    gps_location TEXT,

    arrival_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_arrival_id)
        REFERENCES emergency_arrivals(emergency_arrival_id)
);

CREATE TABLE walkin_patients (
    walkin_patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_arrival_id UUID,

    self_reported_complaint TEXT,

    arrival_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_arrival_id)
        REFERENCES emergency_arrivals(emergency_arrival_id)
);

CREATE TABLE mass_casualty_events (
    mass_casualty_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    event_name VARCHAR(255),

    event_type VARCHAR(255),

    event_location VARCHAR(255),

    event_start_time TIMESTAMP,

    event_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- EMERGENCY ENCOUNTERS
-- =========================================================

CREATE TABLE emergency_registrations (
    emergency_registration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_arrival_id UUID,

    registration_number VARCHAR(100),

    registered_at TIMESTAMP,

    registration_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_arrival_id)
        REFERENCES emergency_arrivals(emergency_arrival_id)
);

CREATE TABLE emergency_encounters (
    emergency_encounter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_registration_id UUID,

    triage_level_id UUID,

    attending_physician UUID,

    chief_complaint TEXT,

    encounter_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_registration_id)
        REFERENCES emergency_registrations(emergency_registration_id),

    FOREIGN KEY (triage_level_id)
        REFERENCES emergency_triage_levels(triage_level_id)
);

CREATE TABLE emergency_bed_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    emergency_room_id UUID,

    assigned_from TIMESTAMP,

    assigned_to TIMESTAMP,

    assignment_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id),

    FOREIGN KEY (emergency_room_id)
        REFERENCES emergency_rooms(emergency_room_id)
);

CREATE TABLE emergency_transfers (
    transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    transfer_destination VARCHAR(255),

    transfer_reason TEXT,

    transferred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE emergency_discharges (
    discharge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    discharge_condition VARCHAR(255),

    discharge_summary TEXT,

    discharged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

-- =========================================================
-- TRAUMA MANAGEMENT
-- =========================================================

CREATE TABLE trauma_cases (
    trauma_case_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    trauma_type VARCHAR(255),

    trauma_mechanism TEXT,

    trauma_severity VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE trauma_assessments (
    trauma_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    trauma_case_id UUID,

    assessment_notes TEXT,

    assessed_by UUID,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (trauma_case_id)
        REFERENCES trauma_cases(trauma_case_id)
);

CREATE TABLE primary_surveys (
    primary_survey_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    trauma_case_id UUID,

    airway_status VARCHAR(100),

    breathing_status VARCHAR(100),

    circulation_status VARCHAR(100),

    disability_status VARCHAR(100),

    exposure_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (trauma_case_id)
        REFERENCES trauma_cases(trauma_case_id)
);

CREATE TABLE secondary_surveys (
    secondary_survey_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    trauma_case_id UUID,

    detailed_findings TEXT,

    imaging_requested BOOLEAN DEFAULT FALSE,

    survey_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (trauma_case_id)
        REFERENCES trauma_cases(trauma_case_id)
);

CREATE TABLE trauma_scores (
    trauma_score_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    trauma_case_id UUID,

    trauma_score_type VARCHAR(100),

    score_value NUMERIC(10,2),

    calculated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (trauma_case_id)
        REFERENCES trauma_cases(trauma_case_id)
);

CREATE TABLE injury_classifications (
    injury_classification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    trauma_case_id UUID,

    injury_type VARCHAR(255),

    injury_location VARCHAR(255),

    severity_level VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (trauma_case_id)
        REFERENCES trauma_cases(trauma_case_id)
);

-- =========================================================
-- EMERGENCY ASSESSMENTS
-- =========================================================

CREATE TABLE emergency_vital_signs (
    emergency_vital_sign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    temperature NUMERIC(5,2),

    pulse_rate INT,

    respiratory_rate INT,

    systolic_bp INT,

    diastolic_bp INT,

    oxygen_saturation NUMERIC(5,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE emergency_observations (
    observation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    observation_type VARCHAR(255),

    observation_value TEXT,

    observed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE pain_assessments (
    pain_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    pain_score INT,

    pain_location TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE neurological_assessments (
    neurological_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    neurological_findings TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE glasgow_coma_scale (
    gcs_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    eye_response INT,

    verbal_response INT,

    motor_response INT,

    total_score INT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

-- =========================================================
-- EMERGENCY PROCEDURES & MEDICATIONS
-- =========================================================

CREATE TABLE emergency_procedures (
    emergency_procedure_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    procedure_name VARCHAR(255),

    procedure_notes TEXT,

    performed_by UUID,

    performed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE bedside_procedures (
    bedside_procedure_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_procedure_id UUID,

    bedside_procedure_type VARCHAR(255),

    bedside_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_procedure_id)
        REFERENCES emergency_procedures(emergency_procedure_id)
);

CREATE TABLE emergency_medications (
    emergency_medication_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    medication_name VARCHAR(255),

    dosage VARCHAR(100),

    route VARCHAR(100),

    prescribed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE medication_administration (
    administration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_medication_id UUID,

    administered_by UUID,

    administered_at TIMESTAMP,

    administration_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_medication_id)
        REFERENCES emergency_medications(emergency_medication_id)
);

CREATE TABLE blood_transfusions (
    blood_transfusion_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    blood_product_type VARCHAR(100),

    units_transfused INT,

    transfusion_started_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

-- =========================================================
-- AIRWAY & RESUSCITATION
-- =========================================================

CREATE TABLE airway_management (
    airway_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    airway_device VARCHAR(255),

    intubation_time TIMESTAMP,

    airway_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE ventilator_support (
    ventilator_support_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    ventilator_mode VARCHAR(255),

    oxygen_percentage NUMERIC(5,2),

    support_started_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE cardiac_resuscitation (
    cardiac_resuscitation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    cpr_started_at TIMESTAMP,

    cpr_ended_at TIMESTAMP,

    resuscitation_outcome VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE defibrillation_logs (
    defibrillation_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    cardiac_resuscitation_id UUID,

    shock_number INT,

    joules_delivered INT,

    delivered_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cardiac_resuscitation_id)
        REFERENCES cardiac_resuscitation(cardiac_resuscitation_id)
);

CREATE TABLE code_blue_events (
    code_blue_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    event_location VARCHAR(255),

    event_time TIMESTAMP,

    event_summary TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

-- =========================================================
-- LAB & RADIOLOGY
-- =========================================================

CREATE TABLE emergency_lab_orders (
    lab_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    order_priority VARCHAR(100),

    ordered_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE emergency_radiology_orders (
    radiology_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    imaging_type VARCHAR(100),

    order_priority VARCHAR(100),

    ordered_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE point_of_care_tests (
    poc_test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    test_name VARCHAR(255),

    test_result TEXT,

    tested_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE stat_lab_results (
    stat_lab_result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    result_name VARCHAR(255),

    critical_flag BOOLEAN DEFAULT FALSE,

    resulted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE critical_alerts (
    critical_alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    alert_type VARCHAR(255),

    alert_message TEXT,

    alert_time TIMESTAMP,

    acknowledged BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

-- =========================================================
-- CONSULTATIONS & ROUNDS
-- =========================================================

CREATE TABLE emergency_consultations (
    consultation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    specialist_reference UUID,

    consultation_notes TEXT,

    consulted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE specialist_referrals (
    referral_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    referred_department VARCHAR(255),

    referral_reason TEXT,

    referred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE emergency_rounds (
    emergency_round_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    round_notes TEXT,

    rounded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE multidisciplinary_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    note_type VARCHAR(100),

    note_text TEXT,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

-- =========================================================
-- DISASTER MANAGEMENT
-- =========================================================

CREATE TABLE disaster_management (
    disaster_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    disaster_name VARCHAR(255),

    disaster_type VARCHAR(255),

    disaster_status VARCHAR(100),

    activated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE incident_command_logs (
    command_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    disaster_management_id UUID,

    command_action TEXT,

    action_taken_by UUID,

    action_time TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (disaster_management_id)
        REFERENCES disaster_management(disaster_management_id)
);

CREATE TABLE disaster_resource_tracking (
    resource_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    disaster_management_id UUID,

    resource_type VARCHAR(255),

    resource_quantity INT,

    tracking_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (disaster_management_id)
        REFERENCES disaster_management(disaster_management_id)
);

CREATE TABLE emergency_preparedness_drills (
    drill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drill_name VARCHAR(255),

    drill_type VARCHAR(255),

    conducted_at TIMESTAMP,

    drill_outcome TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- BILLING & INSURANCE
-- =========================================================

CREATE TABLE emergency_billing (
    emergency_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    billing_amount NUMERIC(14,2),

    billing_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE trauma_billing (
    trauma_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    trauma_case_id UUID,

    trauma_charges NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (trauma_case_id)
        REFERENCES trauma_cases(trauma_case_id)
);

CREATE TABLE insurance_emergency_claims (
    insurance_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_billing_id UUID,

    insurance_provider VARCHAR(255),

    claim_amount NUMERIC(14,2),

    approved_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_billing_id)
        REFERENCES emergency_billing(emergency_billing_id)
);

-- =========================================================
-- QUALITY & INCIDENT MANAGEMENT
-- =========================================================

CREATE TABLE emergency_quality_metrics (
    quality_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    metric_name VARCHAR(255),

    metric_value NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortality_reviews (
    mortality_review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    cause_of_death TEXT,

    review_notes TEXT,

    reviewed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE sentinel_event_reports (
    sentinel_event_report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    event_type VARCHAR(255),

    event_description TEXT,

    severity_level VARCHAR(100),

    occurred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

CREATE TABLE adverse_event_tracking (
    adverse_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_encounter_id UUID,

    event_type VARCHAR(255),

    event_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_encounter_id)
        REFERENCES emergency_encounters(emergency_encounter_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE emergency_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE emergency_change_history (
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
-- INDEXES
-- =========================================================

CREATE INDEX idx_emergency_arrivals_patient ON emergency_arrivals(patient_id);
CREATE INDEX idx_emergency_arrivals_time ON emergency_arrivals(arrival_time);
CREATE INDEX idx_emergency_encounters_registration ON emergency_encounters(emergency_registration_id);
CREATE INDEX idx_emergency_encounters_triage ON emergency_encounters(triage_level_id);
CREATE INDEX idx_emergency_encounters_status ON emergency_encounters(encounter_status);
CREATE INDEX idx_emergency_bed_assign_encounter ON emergency_bed_assignments(emergency_encounter_id);
CREATE INDEX idx_trauma_cases_encounter ON trauma_cases(emergency_encounter_id);
CREATE INDEX idx_trauma_assessments_case ON trauma_assessments(trauma_case_id);
CREATE INDEX idx_emergency_vitals_encounter ON emergency_vital_signs(emergency_encounter_id);
CREATE INDEX idx_emergency_procedures_encounter ON emergency_procedures(emergency_encounter_id);
CREATE INDEX idx_emergency_medications_encounter ON emergency_medications(emergency_encounter_id);
CREATE INDEX idx_emergency_lab_orders_encounter ON emergency_lab_orders(emergency_encounter_id);
CREATE INDEX idx_emergency_radiology_encounter ON emergency_radiology_orders(emergency_encounter_id);
CREATE INDEX idx_critical_alerts_encounter ON critical_alerts(emergency_encounter_id);
CREATE INDEX idx_emergency_billing_encounter ON emergency_billing(emergency_encounter_id);
CREATE INDEX idx_code_blue_encounter ON code_blue_events(emergency_encounter_id);
CREATE INDEX idx_emergency_audit_entity ON emergency_audit_logs(entity_name, entity_id);

-- =========================================================
-- END OF EMERGENCY & TRAUMA MANAGEMENT SYSTEM
-- =========================================================