-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 12: ICU & CRITICAL CARE MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS intensive_care_unit;
SET search_path TO intensive_care_unit, public;

-- =========================================================
-- ICU MASTER TABLES
-- =========================================================

CREATE TABLE icu_departments (
    icu_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE icu_units (
    icu_unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_department_id UUID,

    unit_code VARCHAR(100) UNIQUE NOT NULL,

    unit_name VARCHAR(255),

    unit_type VARCHAR(100),

    floor_number VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_department_id)
        REFERENCES icu_departments(icu_department_id)
);

CREATE TABLE icu_beds (
    icu_bed_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_unit_id UUID,

    bed_number VARCHAR(100),

    bed_type VARCHAR(100),

    bed_status VARCHAR(100),

    ventilator_supported BOOLEAN DEFAULT FALSE,

    isolation_supported BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_unit_id)
        REFERENCES icu_units(icu_unit_id)
);

CREATE TABLE icu_room_configurations (
    room_configuration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_unit_id UUID,

    room_number VARCHAR(100),

    room_type VARCHAR(100),

    negative_pressure_supported BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_unit_id)
        REFERENCES icu_units(icu_unit_id)
);

-- =========================================================
-- ICU ADMISSION MANAGEMENT
-- =========================================================

CREATE TABLE icu_triage_levels (
    triage_level_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    level_name VARCHAR(100),

    severity_rank INT,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE critical_care_patients (
    critical_care_patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID NOT NULL,

    criticality_level VARCHAR(100),

    primary_diagnosis TEXT,

    admission_source VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE icu_admissions (
    icu_admission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    critical_care_patient_id UUID,

    icu_bed_id UUID,

    triage_level_id UUID,

    admitted_by UUID,

    admission_time TIMESTAMP,

    admission_reason TEXT,

    admission_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (critical_care_patient_id)
        REFERENCES critical_care_patients(critical_care_patient_id),

    FOREIGN KEY (icu_bed_id)
        REFERENCES icu_beds(icu_bed_id),

    FOREIGN KEY (triage_level_id)
        REFERENCES icu_triage_levels(triage_level_id)
);

CREATE TABLE icu_bed_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    icu_bed_id UUID,

    assigned_from TIMESTAMP,

    assigned_to TIMESTAMP,

    assignment_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id),

    FOREIGN KEY (icu_bed_id)
        REFERENCES icu_beds(icu_bed_id)
);

CREATE TABLE icu_transfers (
    transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    from_unit_id UUID,

    to_unit_id UUID,

    transfer_reason TEXT,

    transferred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id),

    FOREIGN KEY (from_unit_id)
        REFERENCES icu_units(icu_unit_id),

    FOREIGN KEY (to_unit_id)
        REFERENCES icu_units(icu_unit_id)
);

CREATE TABLE icu_discharges (
    discharge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    discharge_time TIMESTAMP,

    discharge_condition VARCHAR(255),

    discharge_summary TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- VENTILATOR & RESPIRATORY MANAGEMENT
-- =========================================================

CREATE TABLE ventilator_management (
    ventilator_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    ventilator_device_id VARCHAR(255),

    ventilation_mode VARCHAR(255),

    started_at TIMESTAMP,

    ended_at TIMESTAMP,

    managed_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE ventilator_settings (
    ventilator_setting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ventilator_management_id UUID,

    fio2 NUMERIC(5,2),

    peep NUMERIC(5,2),

    tidal_volume NUMERIC(10,2),

    respiratory_rate INT,

    pressure_support NUMERIC(10,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ventilator_management_id)
        REFERENCES ventilator_management(ventilator_management_id)
);

CREATE TABLE ventilator_logs (
    ventilator_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ventilator_management_id UUID,

    log_message TEXT,

    logged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ventilator_management_id)
        REFERENCES ventilator_management(ventilator_management_id)
);

CREATE TABLE oxygen_therapy_management (
    oxygen_therapy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    oxygen_device VARCHAR(255),

    oxygen_flow_rate VARCHAR(100),

    started_at TIMESTAMP,

    monitored_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE respiratory_assessments (
    respiratory_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    respiratory_rate INT,

    breath_sounds TEXT,

    oxygen_saturation NUMERIC(5,2),

    assessment_notes TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- HEMODYNAMIC & CARDIAC MONITORING
-- =========================================================

CREATE TABLE hemodynamic_monitoring (
    hemodynamic_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    cardiac_output NUMERIC(10,2),

    cvp NUMERIC(10,2),

    map_value NUMERIC(10,2),

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE arterial_line_monitoring (
    arterial_line_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    arterial_pressure NUMERIC(10,2),

    waveform_quality VARCHAR(100),

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE central_line_management (
    central_line_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    line_type VARCHAR(255),

    insertion_site VARCHAR(255),

    inserted_at TIMESTAMP,

    removed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE cardiac_monitoring (
    cardiac_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    heart_rate INT,

    rhythm VARCHAR(255),

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE ecg_monitoring (
    ecg_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    ecg_result TEXT,

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- INFUSION & MEDICATION TITRATION
-- =========================================================

CREATE TABLE infusion_pumps (
    infusion_pump_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    pump_identifier VARCHAR(255),

    medication_name VARCHAR(255),

    infusion_rate VARCHAR(100),

    started_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE vasopressor_management (
    vasopressor_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    vasopressor_name VARCHAR(255),

    dosage VARCHAR(100),

    started_at TIMESTAMP,

    titrated_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE sedation_management (
    sedation_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    sedation_medication VARCHAR(255),

    sedation_score VARCHAR(100),

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE pain_management (
    pain_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    pain_score INT,

    pain_medication VARCHAR(255),

    managed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE medication_titration_logs (
    titration_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    medication_name VARCHAR(255),

    previous_dose VARCHAR(100),

    new_dose VARCHAR(100),

    titrated_at TIMESTAMP,

    titrated_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- ICU ASSESSMENTS
-- =========================================================

CREATE TABLE icu_vital_signs (
    icu_vital_sign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    temperature NUMERIC(5,2),

    pulse_rate INT,

    respiratory_rate INT,

    systolic_bp INT,

    diastolic_bp INT,

    oxygen_saturation NUMERIC(5,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE neurological_assessments (
    neurological_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    consciousness_level VARCHAR(255),

    motor_response TEXT,

    sensory_response TEXT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE glasgow_coma_scale (
    gcs_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    eye_response INT,

    verbal_response INT,

    motor_response INT,

    total_score INT,

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE pupillary_assessments (
    pupillary_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    left_pupil_response VARCHAR(100),

    right_pupil_response VARCHAR(100),

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE seizure_monitoring (
    seizure_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    seizure_type VARCHAR(255),

    seizure_duration VARCHAR(100),

    observed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- RENAL & FLUID MANAGEMENT
-- =========================================================

CREATE TABLE renal_replacement_therapy (
    rrt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    therapy_type VARCHAR(255),

    started_at TIMESTAMP,

    ended_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE dialysis_sessions (
    dialysis_session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    rrt_id UUID,

    session_duration VARCHAR(100),

    ultrafiltration_volume VARCHAR(100),

    session_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (rrt_id)
        REFERENCES renal_replacement_therapy(rrt_id)
);

CREATE TABLE fluid_balance_monitoring (
    fluid_balance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    intake_amount NUMERIC(10,2),

    output_amount NUMERIC(10,2),

    balance_amount NUMERIC(10,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE electrolyte_monitoring (
    electrolyte_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    sodium_level NUMERIC(10,2),

    potassium_level NUMERIC(10,2),

    calcium_level NUMERIC(10,2),

    magnesium_level NUMERIC(10,2),

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- CRITICAL ALERTS & LABS
-- =========================================================

CREATE TABLE critical_lab_alerts (
    critical_lab_alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    alert_type VARCHAR(255),

    alert_message TEXT,

    alert_time TIMESTAMP,

    acknowledged BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE abg_results (
    abg_result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    ph_value NUMERIC(5,2),

    pco2 NUMERIC(10,2),

    po2 NUMERIC(10,2),

    hco3 NUMERIC(10,2),

    lactate NUMERIC(10,2),

    analyzed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE sepsis_screening (
    sepsis_screening_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    qsofa_score INT,

    sepsis_risk VARCHAR(100),

    screening_notes TEXT,

    screened_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE infection_surveillance (
    infection_surveillance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    infection_type VARCHAR(255),

    culture_result TEXT,

    isolation_required BOOLEAN DEFAULT FALSE,

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- CODE BLUE & RESUSCITATION
-- =========================================================

CREATE TABLE code_blue_events (
    code_blue_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    event_time TIMESTAMP,

    event_location VARCHAR(255),

    event_summary TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE resuscitation_records (
    resuscitation_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    code_blue_event_id UUID,

    resuscitation_start TIMESTAMP,

    resuscitation_end TIMESTAMP,

    outcome VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (code_blue_event_id)
        REFERENCES code_blue_events(code_blue_event_id)
);

CREATE TABLE emergency_interventions (
    emergency_intervention_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    code_blue_event_id UUID,

    intervention_type VARCHAR(255),

    intervention_notes TEXT,

    performed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (code_blue_event_id)
        REFERENCES code_blue_events(code_blue_event_id)
);

-- =========================================================
-- DEVICE & TELEMETRY INTEGRATIONS
-- =========================================================

CREATE TABLE bedside_device_integrations (
    device_integration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    device_identifier VARCHAR(255),

    integration_status VARCHAR(100),

    last_sync_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE real_time_monitoring_streams (
    monitoring_stream_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_bed_id UUID,

    stream_source VARCHAR(255),

    stream_status VARCHAR(100),

    last_received_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_bed_id)
        REFERENCES icu_beds(icu_bed_id)
);

CREATE TABLE device_alerts (
    device_alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    device_identifier VARCHAR(255),

    alert_type VARCHAR(255),

    alert_message TEXT,

    alert_time TIMESTAMP,

    acknowledged BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE telemetry_logs (
    telemetry_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    telemetry_data TEXT,

    logged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- ICU ROUNDS & FAMILY CARE
-- =========================================================

CREATE TABLE icu_rounds (
    icu_round_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    rounded_by UUID,

    round_notes TEXT,

    rounded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE multidisciplinary_notes (
    multidisciplinary_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    note_type VARCHAR(100),

    note_text TEXT,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE family_counseling_records (
    family_counseling_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    counseling_notes TEXT,

    counseled_by UUID,

    counseled_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE end_of_life_care (
    end_of_life_care_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    care_plan TEXT,

    dnr_status BOOLEAN DEFAULT FALSE,

    comfort_measures TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- QUALITY & INCIDENT MANAGEMENT
-- =========================================================

CREATE TABLE icu_quality_metrics (
    quality_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    metric_name VARCHAR(255),

    metric_value NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortality_reviews (
    mortality_review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    cause_of_death TEXT,

    review_notes TEXT,

    reviewed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

CREATE TABLE adverse_event_tracking (
    adverse_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    icu_admission_id UUID,

    event_type VARCHAR(255),

    event_description TEXT,

    severity_level VARCHAR(100),

    occurred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (icu_admission_id)
        REFERENCES icu_admissions(icu_admission_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE icu_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE icu_change_history (
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

CREATE INDEX idx_icu_units_department ON icu_units(icu_department_id);
CREATE INDEX idx_icu_beds_unit ON icu_beds(icu_unit_id);
CREATE INDEX idx_icu_beds_status ON icu_beds(bed_status);
CREATE INDEX idx_critical_care_patients_patient ON critical_care_patients(patient_id);
CREATE INDEX idx_icu_admissions_patient ON icu_admissions(critical_care_patient_id);
CREATE INDEX idx_icu_admissions_bed ON icu_admissions(icu_bed_id);
CREATE INDEX idx_icu_admissions_status ON icu_admissions(admission_status);
CREATE INDEX idx_icu_admissions_time ON icu_admissions(admission_time);
CREATE INDEX idx_icu_bed_assignments_admission ON icu_bed_assignments(icu_admission_id);
CREATE INDEX idx_icu_transfers_admission ON icu_transfers(icu_admission_id);
CREATE INDEX idx_icu_discharges_admission ON icu_discharges(icu_admission_id);
CREATE INDEX idx_ventilator_mgmt_admission ON ventilator_management(icu_admission_id);
CREATE INDEX idx_ventilator_settings_mgmt ON ventilator_settings(ventilator_management_id);
CREATE INDEX idx_oxygen_therapy_admission ON oxygen_therapy_management(icu_admission_id);
CREATE INDEX idx_respiratory_assess_admission ON respiratory_assessments(icu_admission_id);
CREATE INDEX idx_hemodynamic_admission ON hemodynamic_monitoring(icu_admission_id);
CREATE INDEX idx_cardiac_monitoring_admission ON cardiac_monitoring(icu_admission_id);
CREATE INDEX idx_infusion_pumps_admission ON infusion_pumps(icu_admission_id);
CREATE INDEX idx_vasopressor_admission ON vasopressor_management(icu_admission_id);
CREATE INDEX idx_sedation_admission ON sedation_management(icu_admission_id);
CREATE INDEX idx_icu_vitals_admission ON icu_vital_signs(icu_admission_id);
CREATE INDEX idx_icu_vitals_recorded ON icu_vital_signs(recorded_at);
CREATE INDEX idx_neuro_assess_admission ON neurological_assessments(icu_admission_id);
CREATE INDEX idx_gcs_admission ON glasgow_coma_scale(icu_admission_id);
CREATE INDEX idx_rrt_admission ON renal_replacement_therapy(icu_admission_id);
CREATE INDEX idx_fluid_balance_admission ON fluid_balance_monitoring(icu_admission_id);
CREATE INDEX idx_electrolyte_admission ON electrolyte_monitoring(icu_admission_id);
CREATE INDEX idx_critical_lab_alerts_admission ON critical_lab_alerts(icu_admission_id);
CREATE INDEX idx_abg_results_admission ON abg_results(icu_admission_id);
CREATE INDEX idx_sepsis_screening_admission ON sepsis_screening(icu_admission_id);
CREATE INDEX idx_infection_surv_admission ON infection_surveillance(icu_admission_id);
CREATE INDEX idx_code_blue_admission ON code_blue_events(icu_admission_id);
CREATE INDEX idx_resuscitation_event ON resuscitation_records(code_blue_event_id);
CREATE INDEX idx_device_alerts_admission ON device_alerts(icu_admission_id);
CREATE INDEX idx_icu_rounds_admission ON icu_rounds(icu_admission_id);
CREATE INDEX idx_mortality_reviews_admission ON mortality_reviews(icu_admission_id);
CREATE INDEX idx_adverse_events_admission ON adverse_event_tracking(icu_admission_id);
CREATE INDEX idx_icu_audit_entity ON icu_audit_logs(entity_name, entity_id);

-- =========================================================
-- END OF ICU & CRITICAL CARE MANAGEMENT SCHEMA
-- =========================================================