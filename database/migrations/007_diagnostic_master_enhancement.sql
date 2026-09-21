-- Extend the deployed laboratory/radiology schemas into a configurable
-- diagnostic master. Existing free-text columns remain for compatibility.

ALTER TABLE laboratory.lab_tests
    ADD COLUMN IF NOT EXISTS specimen_type VARCHAR(120),
    ADD COLUMN IF NOT EXISTS approving_specialty VARCHAR(160) NOT NULL DEFAULT 'Pathology / Laboratory Medicine',
    ADD COLUMN IF NOT EXISTS performing_department VARCHAR(160) NOT NULL DEFAULT 'Laboratory';

ALTER TABLE laboratory.lab_test_parameters
    ADD COLUMN IF NOT EXISTS parameter_code VARCHAR(100),
    ADD COLUMN IF NOT EXISTS result_type VARCHAR(30) NOT NULL DEFAULT 'NUMERIC',
    ADD COLUMN IF NOT EXISTS specimen_type VARCHAR(120),
    ADD COLUMN IF NOT EXISTS method VARCHAR(255),
    ADD COLUMN IF NOT EXISTS display_order INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_required BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS allowed_values JSONB,
    ADD COLUMN IF NOT EXISTS interpretation TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_parameter_code_per_test
    ON laboratory.lab_test_parameters(test_id, parameter_code)
    WHERE parameter_code IS NOT NULL;

ALTER TABLE laboratory.lab_test_reference_ranges
    ADD COLUMN IF NOT EXISTS reference_rule VARCHAR(40) NOT NULL DEFAULT 'ALL',
    ADD COLUMN IF NOT EXISTS sex VARCHAR(20),
    ADD COLUMN IF NOT EXISTS age_min NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS age_max NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS age_unit VARCHAR(20) NOT NULL DEFAULT 'YEARS',
    ADD COLUMN IF NOT EXISTS pregnancy_status VARCHAR(40),
    ADD COLUMN IF NOT EXISTS trimester SMALLINT,
    ADD COLUMN IF NOT EXISTS gestational_week_min SMALLINT,
    ADD COLUMN IF NOT EXISTS gestational_week_max SMALLINT,
    ADD COLUMN IF NOT EXISTS menstrual_phase VARCHAR(50),
    ADD COLUMN IF NOT EXISTS clinical_condition VARCHAR(120),
    ADD COLUMN IF NOT EXISTS critical_low NUMERIC(18,6),
    ADD COLUMN IF NOT EXISTS critical_high NUMERIC(18,6),
    ADD COLUMN IF NOT EXISTS qualitative_reference JSONB,
    ADD COLUMN IF NOT EXISTS unit VARCHAR(100),
    ADD COLUMN IF NOT EXISTS effective_from DATE,
    ADD COLUMN IF NOT EXISTS effective_to DATE,
    ADD COLUMN IF NOT EXISTS source TEXT,
    ADD COLUMN IF NOT EXISTS method VARCHAR(255),
    ADD COLUMN IF NOT EXISTS analyzer VARCHAR(255),
    ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(255),
    ADD COLUMN IF NOT EXISTS percentile_99 NUMERIC(18,6),
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Retain and synchronize the historical names used by the original schema.
UPDATE laboratory.lab_test_reference_ranges
SET sex = COALESCE(sex, gender),
    age_min = COALESCE(age_min, min_age),
    age_max = COALESCE(age_max, max_age)
WHERE sex IS NULL OR age_min IS NULL OR age_max IS NULL;

CREATE INDEX IF NOT EXISTS idx_lab_reference_range_resolution
    ON laboratory.lab_test_reference_ranges
       (parameter_id, is_active, sex, pregnancy_status, trimester, age_min, age_max);

CREATE TABLE IF NOT EXISTS laboratory.lab_parameter_interpretation_rules (
    interpretation_rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parameter_id UUID NOT NULL REFERENCES laboratory.lab_test_parameters(parameter_id) ON DELETE CASCADE,
    rule_code VARCHAR(100) NOT NULL,
    label VARCHAR(120) NOT NULL,
    operator VARCHAR(20) NOT NULL,
    lower_value NUMERIC(18,6),
    upper_value NUMERIC(18,6),
    qualitative_value VARCHAR(255),
    interpretation TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    effective_from DATE,
    effective_to DATE,
    source TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(parameter_id, rule_code, version)
);

ALTER TABLE laboratory.lab_result_parameters
    ADD COLUMN IF NOT EXISTS numeric_value NUMERIC(24,8),
    ADD COLUMN IF NOT EXISTS text_value TEXT,
    ADD COLUMN IF NOT EXISTS boolean_value BOOLEAN,
    ADD COLUMN IF NOT EXISTS coded_value VARCHAR(255),
    ADD COLUMN IF NOT EXISTS predicted_value NUMERIC(24,8),
    ADD COLUMN IF NOT EXISTS percent_predicted NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS lower_limit_normal NUMERIC(24,8),
    ADD COLUMN IF NOT EXISTS z_score NUMERIC(12,4),
    ADD COLUMN IF NOT EXISTS reference_range_id UUID
        REFERENCES laboratory.lab_test_reference_ranges(reference_range_id),
    ADD COLUMN IF NOT EXISTS interpretation TEXT;

CREATE TABLE IF NOT EXISTS radiology.radiology_observation_definitions (
    observation_definition_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    radiology_test_id UUID NOT NULL REFERENCES radiology.radiology_tests(radiology_test_id) ON DELETE CASCADE,
    observation_code VARCHAR(100) NOT NULL,
    observation_name VARCHAR(255) NOT NULL,
    result_type VARCHAR(30) NOT NULL DEFAULT 'TEXT',
    unit VARCHAR(100),
    allowed_values JSONB,
    body_region VARCHAR(120),
    display_order INTEGER NOT NULL DEFAULT 0,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(radiology_test_id, observation_code)
);

CREATE TABLE IF NOT EXISTS radiology.radiology_report_observations (
    report_observation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES radiology.radiology_reports(report_id) ON DELETE CASCADE,
    observation_definition_id UUID NOT NULL
        REFERENCES radiology.radiology_observation_definitions(observation_definition_id),
    result_value TEXT,
    numeric_value NUMERIC(24,8),
    coded_value VARCHAR(255),
    is_abnormal BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(report_id, observation_definition_id)
);

CREATE TABLE IF NOT EXISTS radiology.radiology_report_approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES radiology.radiology_reports(report_id) ON DELETE CASCADE,
    approval_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    approving_specialty VARCHAR(160) NOT NULL DEFAULT 'Radiology',
    approved_by UUID,
    approval_notes TEXT,
    approved_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(report_id, version)
);

CREATE INDEX IF NOT EXISTS idx_radiology_observation_test
    ON radiology.radiology_observation_definitions(radiology_test_id, display_order);
CREATE INDEX IF NOT EXISTS idx_radiology_report_approval_status
    ON radiology.radiology_report_approvals(approval_status, approving_specialty);

