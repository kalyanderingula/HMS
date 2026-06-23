-- ==========================================================
-- CATEGORY 24 : AI & CLINICAL DECISION SUPPORT SYSTEM
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS artificial_intelligence;
SET search_path TO artificial_intelligence, public;

-- ==========================================================
-- AI MODEL MANAGEMENT
-- ==========================================================

CREATE TABLE ai_models (
    ai_model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_model_versions (
    model_version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ai_model_id UUID NOT NULL,
    version_number VARCHAR(50),
    release_date DATE,
    status VARCHAR(50),

    FOREIGN KEY (ai_model_id)
        REFERENCES ai_models(ai_model_id)
);

CREATE TABLE ai_model_deployments (
    deployment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_version_id UUID NOT NULL,
    deployment_environment VARCHAR(100),
    deployed_at TIMESTAMP,

    FOREIGN KEY (model_version_id)
        REFERENCES ai_model_versions(model_version_id)
);

CREATE TABLE ai_training_datasets (
    dataset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_name VARCHAR(255),
    source_system VARCHAR(255),
    dataset_size BIGINT,
    created_at TIMESTAMP
);

CREATE TABLE ai_model_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_version_id UUID,
    metric_name VARCHAR(255),
    metric_value NUMERIC(10,4),

    FOREIGN KEY (model_version_id)
        REFERENCES ai_model_versions(model_version_id)
);

-- ==========================================================
-- CLINICAL RULE ENGINE
-- ==========================================================

CREATE TABLE clinical_rule_categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name VARCHAR(255)
);

CREATE TABLE clinical_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID,
    rule_name VARCHAR(255),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,

    FOREIGN KEY (category_id)
        REFERENCES clinical_rule_categories(category_id)
);

CREATE TABLE clinical_rule_conditions (
    condition_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID,
    condition_expression TEXT,

    FOREIGN KEY (rule_id)
        REFERENCES clinical_rules(rule_id)
);

CREATE TABLE clinical_rule_actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID,
    action_type VARCHAR(100),
    action_definition TEXT,

    FOREIGN KEY (rule_id)
        REFERENCES clinical_rules(rule_id)
);

CREATE TABLE clinical_rule_versions (
    version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID,
    version_number VARCHAR(50),

    FOREIGN KEY (rule_id)
        REFERENCES clinical_rules(rule_id)
);

-- ==========================================================
-- DIAGNOSIS SUPPORT
-- ==========================================================

CREATE TABLE diagnosis_support (
    diagnosis_support_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    encounter_id UUID,
    analysis_date TIMESTAMP
);

CREATE TABLE diagnosis_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diagnosis_support_id UUID,
    diagnosis_name VARCHAR(255),

    FOREIGN KEY (diagnosis_support_id)
        REFERENCES diagnosis_support(diagnosis_support_id)
);

CREATE TABLE differential_diagnoses (
    differential_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diagnosis_support_id UUID,
    diagnosis_name VARCHAR(255),

    FOREIGN KEY (diagnosis_support_id)
        REFERENCES diagnosis_support(diagnosis_support_id)
);

CREATE TABLE diagnosis_confidence_scores (
    confidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diagnosis_support_id UUID,
    confidence_score NUMERIC(5,2),

    FOREIGN KEY (diagnosis_support_id)
        REFERENCES diagnosis_support(diagnosis_support_id)
);

-- ==========================================================
-- TREATMENT SUPPORT
-- ==========================================================

CREATE TABLE treatment_guidelines (
    guideline_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guideline_name VARCHAR(255),
    specialty VARCHAR(255)
);

CREATE TABLE treatment_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    guideline_id UUID,

    FOREIGN KEY (guideline_id)
        REFERENCES treatment_guidelines(guideline_id)
);

CREATE TABLE care_pathways (
    pathway_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pathway_name VARCHAR(255)
);

CREATE TABLE treatment_outcomes (
    outcome_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    outcome_description TEXT
);

-- ==========================================================
-- MEDICATION SAFETY
-- ==========================================================

CREATE TABLE medication_interactions (
    interaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medication_1 VARCHAR(255),
    medication_2 VARCHAR(255),
    severity VARCHAR(50)
);

CREATE TABLE allergy_checks (
    allergy_check_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    allergy_name VARCHAR(255)
);

CREATE TABLE dosage_recommendations (
    dosage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medication_name VARCHAR(255),
    age_group VARCHAR(100),
    recommended_dose VARCHAR(255)
);

CREATE TABLE prescription_validations (
    validation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prescription_id UUID,
    validation_result VARCHAR(100)
);

-- ==========================================================
-- RISK ASSESSMENT
-- ==========================================================

CREATE TABLE risk_assessment_models (
    risk_model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255)
);

CREATE TABLE patient_risk_scores (
    patient_risk_score_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    risk_model_id UUID,
    risk_score NUMERIC(10,2),

    FOREIGN KEY (risk_model_id)
        REFERENCES risk_assessment_models(risk_model_id)
);

CREATE TABLE risk_factors (
    risk_factor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    risk_model_id UUID,
    factor_name VARCHAR(255),

    FOREIGN KEY (risk_model_id)
        REFERENCES risk_assessment_models(risk_model_id)
);

CREATE TABLE risk_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_risk_score_id UUID,
    alert_message TEXT,

    FOREIGN KEY (patient_risk_score_id)
        REFERENCES patient_risk_scores(patient_risk_score_id)
);

-- ==========================================================
-- EARLY WARNING SYSTEMS
-- ==========================================================

CREATE TABLE early_warning_scores (
    warning_score_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    score NUMERIC(10,2)
);

CREATE TABLE sepsis_detection (
    sepsis_detection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    risk_level VARCHAR(50)
);

CREATE TABLE deterioration_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    prediction_score NUMERIC(10,2)
);

CREATE TABLE icu_risk_predictions (
    icu_prediction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    risk_score NUMERIC(10,2)
);

-- ==========================================================
-- AI RADIOLOGY
-- ==========================================================

CREATE TABLE ai_radiology_models (
    radiology_model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255)
);

CREATE TABLE radiology_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    radiology_model_id UUID,
    patient_id UUID,

    FOREIGN KEY (radiology_model_id)
        REFERENCES ai_radiology_models(radiology_model_id)
);

CREATE TABLE imaging_findings (
    finding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID,
    finding_description TEXT,

    FOREIGN KEY (prediction_id)
        REFERENCES radiology_predictions(prediction_id)
);

-- ==========================================================
-- AI PATHOLOGY
-- ==========================================================

CREATE TABLE ai_pathology_models (
    pathology_model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255)
);

CREATE TABLE pathology_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pathology_model_id UUID,
    patient_id UUID,

    FOREIGN KEY (pathology_model_id)
        REFERENCES ai_pathology_models(pathology_model_id)
);

CREATE TABLE pathology_findings (
    finding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID,
    finding_description TEXT,

    FOREIGN KEY (prediction_id)
        REFERENCES pathology_predictions(prediction_id)
);

-- ==========================================================
-- FORECASTING
-- ==========================================================

CREATE TABLE predictive_analytics_models (
    analytics_model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255)
);

CREATE TABLE patient_volume_forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_date DATE,
    predicted_volume INT
);

CREATE TABLE bed_occupancy_forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_date DATE,
    occupancy_percentage NUMERIC(5,2)
);

CREATE TABLE revenue_forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_date DATE,
    predicted_revenue NUMERIC(18,2)
);

-- ==========================================================
-- AI ASSISTANTS
-- ==========================================================

CREATE TABLE chatbot_assistants (
    chatbot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_name VARCHAR(255)
);

CREATE TABLE virtual_health_assistants (
    assistant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assistant_name VARCHAR(255)
);

CREATE TABLE ai_conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    conversation_text TEXT
);

CREATE TABLE ai_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    recommendation_text TEXT
);

-- ==========================================================
-- KNOWLEDGE BASE
-- ==========================================================

CREATE TABLE knowledge_base_articles (
    article_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_title VARCHAR(255)
);

CREATE TABLE clinical_guidelines (
    guideline_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guideline_title VARCHAR(255)
);

CREATE TABLE medical_literature (
    literature_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255)
);

CREATE TABLE evidence_references (
    reference_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_title VARCHAR(255)
);

-- ==========================================================
-- AUDIT
-- ==========================================================

CREATE TABLE ai_audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(255),
    action_type VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_change_history (
    change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255),
    record_id UUID,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);