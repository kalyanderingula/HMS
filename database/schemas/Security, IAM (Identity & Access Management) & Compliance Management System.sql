
-- ==========================================================
-- CATEGORY 22 : SECURITY, IAM & COMPLIANCE MANAGEMENT
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS security;
SET search_path TO security, public;

-- USERS & ACCESS
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash TEXT NOT NULL,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_profiles (
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone VARCHAR(50)
);

CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    login_time TIMESTAMP,
    logout_time TIMESTAMP
);

CREATE TABLE login_history (
    login_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    ip_address VARCHAR(255),
    login_time TIMESTAMP
);

-- RBAC
CREATE TABLE roles (
    role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(255) UNIQUE
);

CREATE TABLE permissions (
    permission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permission_name VARCHAR(255) UNIQUE
);

CREATE TABLE role_permissions (
    role_permission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_id UUID REFERENCES roles(role_id),
    permission_id UUID REFERENCES permissions(permission_id)
);

CREATE TABLE user_roles (
    user_role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    role_id UUID REFERENCES roles(role_id)
);

-- PASSWORD SECURITY
CREATE TABLE password_policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    min_length INT,
    expiry_days INT
);

CREATE TABLE password_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    password_hash TEXT,
    changed_at TIMESTAMP
);

CREATE TABLE account_lockouts (
    lockout_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    locked_at TIMESTAMP
);

-- MFA
CREATE TABLE multi_factor_authentication (
    mfa_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    mfa_type VARCHAR(100),
    enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE trusted_devices (
    trusted_device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    device_name VARCHAR(255)
);

-- API SECURITY
CREATE TABLE api_clients (
    client_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_name VARCHAR(255)
);

CREATE TABLE api_keys (
    api_key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES api_clients(client_id),
    api_key TEXT
);

CREATE TABLE oauth_clients (
    oauth_client_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_name VARCHAR(255)
);

CREATE TABLE oauth_tokens (
    token_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    oauth_client_id UUID REFERENCES oauth_clients(oauth_client_id),
    access_token TEXT
);

-- CONSENT
CREATE TABLE consent_policies (
    consent_policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_name VARCHAR(255)
);

CREATE TABLE patient_consents (
    patient_consent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consent_policy_id UUID REFERENCES consent_policies(consent_policy_id),
    patient_id UUID
);

-- AUDIT & SECURITY EVENTS
CREATE TABLE audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(255),
    action_type VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security_events (
    security_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_name VARCHAR(255),
    severity VARCHAR(50)
);

CREATE TABLE security_incidents (
    incident_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    security_event_id UUID REFERENCES security_events(security_event_id),
    incident_status VARCHAR(100)
);

-- DATA PROTECTION
CREATE TABLE data_classifications (
    classification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    classification_name VARCHAR(255)
);

CREATE TABLE retention_policies (
    retention_policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_name VARCHAR(255)
);

CREATE TABLE data_masking_rules (
    masking_rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(255)
);

CREATE TABLE encryption_keys (
    encryption_key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_name VARCHAR(255)
);

-- COMPLIANCE
CREATE TABLE compliance_frameworks (
    framework_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_name VARCHAR(255)
);

CREATE TABLE compliance_controls (
    control_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_id UUID REFERENCES compliance_frameworks(framework_id),
    control_name VARCHAR(255)
);

CREATE TABLE compliance_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_id UUID REFERENCES compliance_frameworks(framework_id)
);

CREATE TABLE compliance_findings (
    finding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES compliance_assessments(assessment_id)
);

-- RISK
CREATE TABLE risk_assessments (
    risk_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_name VARCHAR(255)
);

CREATE TABLE risk_register (
    risk_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    risk_assessment_id UUID REFERENCES risk_assessments(risk_assessment_id),
    risk_name VARCHAR(255)
);

-- DOCUMENTS
CREATE TABLE security_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_name VARCHAR(255)
);

CREATE TABLE security_policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_name VARCHAR(255)
);

CREATE TABLE security_audit_logs (
    security_audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security_change_history (
    change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
