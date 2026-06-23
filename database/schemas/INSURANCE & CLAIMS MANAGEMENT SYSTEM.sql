-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 15: INSURANCE & CLAIMS MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS insurance;
SET search_path TO insurance, public;

-- =========================================================
-- INSURANCE MASTER TABLES
-- =========================================================

CREATE TABLE insurance_providers (
    insurance_provider_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    provider_code VARCHAR(100) UNIQUE NOT NULL,

    provider_name VARCHAR(255) NOT NULL,

    provider_type VARCHAR(100),

    contact_email VARCHAR(255),

    contact_phone VARCHAR(50),

    address TEXT,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE insurance_plan_categories (
    plan_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_name VARCHAR(255),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE insurance_plans (
    insurance_plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_provider_id UUID,

    plan_category_id UUID,

    plan_code VARCHAR(100),

    plan_name VARCHAR(255),

    coverage_percentage NUMERIC(5,2),

    annual_limit NUMERIC(14,2),

    co_payment_percentage NUMERIC(5,2),

    deductible_amount NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_provider_id)
        REFERENCES insurance_providers(insurance_provider_id),

    FOREIGN KEY (plan_category_id)
        REFERENCES insurance_plan_categories(plan_category_id)
);

CREATE TABLE insurance_networks (
    insurance_network_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    network_name VARCHAR(255),

    network_type VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payer_contracts (
    payer_contract_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_provider_id UUID,

    contract_number VARCHAR(100),

    contract_start_date DATE,

    contract_end_date DATE,

    contract_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_provider_id)
        REFERENCES insurance_providers(insurance_provider_id)
);

CREATE TABLE payer_contract_terms (
    payer_contract_term_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payer_contract_id UUID,

    term_name VARCHAR(255),

    term_value TEXT,

    effective_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payer_contract_id)
        REFERENCES payer_contracts(payer_contract_id)
);

-- =========================================================
-- PATIENT INSURANCE MANAGEMENT
-- =========================================================

CREATE TABLE patient_insurance_policies (
    patient_insurance_policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    insurance_plan_id UUID,

    policy_number VARCHAR(255),

    group_number VARCHAR(255),

    subscriber_name VARCHAR(255),

    relationship_to_subscriber VARCHAR(100),

    coverage_start_date DATE,

    coverage_end_date DATE,

    policy_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_plan_id)
        REFERENCES insurance_plans(insurance_plan_id)
);

CREATE TABLE insurance_policy_dependents (
    dependent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_insurance_policy_id UUID,

    dependent_name VARCHAR(255),

    dependent_relationship VARCHAR(100),

    date_of_birth DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_insurance_policy_id)
        REFERENCES patient_insurance_policies(patient_insurance_policy_id)
);

CREATE TABLE insurance_verifications (
    insurance_verification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_insurance_policy_id UUID,

    verification_status VARCHAR(100),

    verified_by UUID,

    verification_date TIMESTAMP,

    verification_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_insurance_policy_id)
        REFERENCES patient_insurance_policies(patient_insurance_policy_id)
);

CREATE TABLE eligibility_checks (
    eligibility_check_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_insurance_policy_id UUID,

    eligibility_status VARCHAR(100),

    coverage_details TEXT,

    checked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_insurance_policy_id)
        REFERENCES patient_insurance_policies(patient_insurance_policy_id)
);

CREATE TABLE preauthorizations (
    preauthorization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_insurance_policy_id UUID,

    authorization_number VARCHAR(255),

    requested_service VARCHAR(255),

    authorization_status VARCHAR(100),

    approved_amount NUMERIC(14,2),

    valid_from DATE,

    valid_to DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_insurance_policy_id)
        REFERENCES patient_insurance_policies(patient_insurance_policy_id)
);

CREATE TABLE authorization_documents (
    authorization_document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    preauthorization_id UUID,

    document_name VARCHAR(255),

    document_path TEXT,

    uploaded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (preauthorization_id)
        REFERENCES preauthorizations(preauthorization_id)
);

-- =========================================================
-- CLAIMS MANAGEMENT
-- =========================================================

CREATE TABLE claim_batches (
    claim_batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    batch_number VARCHAR(100),

    batch_date DATE,

    total_claims INT,

    batch_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE insurance_claims (
    insurance_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    claim_batch_id UUID,

    patient_id UUID,

    patient_insurance_policy_id UUID,

    claim_number VARCHAR(255),

    claim_type VARCHAR(100),

    total_claim_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    claim_submission_date TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (claim_batch_id)
        REFERENCES claim_batches(claim_batch_id),

    FOREIGN KEY (patient_insurance_policy_id)
        REFERENCES patient_insurance_policies(patient_insurance_policy_id)
);

CREATE TABLE claim_line_items (
    claim_line_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    service_code VARCHAR(100),

    service_description TEXT,

    quantity INT,

    unit_cost NUMERIC(14,2),

    total_cost NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE diagnosis_claim_mapping (
    diagnosis_claim_mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    icd_code VARCHAR(50),

    diagnosis_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE procedure_claim_mapping (
    procedure_claim_mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    cpt_code VARCHAR(50),

    procedure_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE drg_claim_mapping (
    drg_claim_mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    drg_code VARCHAR(50),

    drg_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

-- =========================================================
-- ELECTRONIC CLAIMS & EDI
-- =========================================================

CREATE TABLE claim_submissions (
    claim_submission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    submission_method VARCHAR(100),

    submitted_at TIMESTAMP,

    submission_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE electronic_claims (
    electronic_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    claim_submission_id UUID,

    edi_file_reference VARCHAR(255),

    transmission_status VARCHAR(100),

    transmitted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (claim_submission_id)
        REFERENCES claim_submissions(claim_submission_id)
);

CREATE TABLE edi_transactions (
    edi_transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    electronic_claim_id UUID,

    transaction_type VARCHAR(100),

    transaction_reference VARCHAR(255),

    transaction_status VARCHAR(100),

    processed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (electronic_claim_id)
        REFERENCES electronic_claims(electronic_claim_id)
);

CREATE TABLE clearinghouse_responses (
    clearinghouse_response_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    edi_transaction_id UUID,

    response_code VARCHAR(100),

    response_message TEXT,

    received_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (edi_transaction_id)
        REFERENCES edi_transactions(edi_transaction_id)
);

CREATE TABLE claim_acknowledgements (
    claim_acknowledgement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    acknowledgement_status VARCHAR(100),

    acknowledgement_message TEXT,

    acknowledged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

-- =========================================================
-- CLAIM STATUS & DENIAL MANAGEMENT
-- =========================================================

CREATE TABLE claim_status_tracking (
    claim_status_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    status_code VARCHAR(100),

    status_description TEXT,

    updated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE claim_rejections (
    claim_rejection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    rejection_reason TEXT,

    rejected_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE denial_reason_codes (
    denial_reason_code_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    denial_code VARCHAR(100),

    denial_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE denial_management (
    denial_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    denial_reason_code_id UUID,

    denial_status VARCHAR(100),

    denial_notes TEXT,

    denied_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id),

    FOREIGN KEY (denial_reason_code_id)
        REFERENCES denial_reason_codes(denial_reason_code_id)
);

CREATE TABLE appeals_management (
    appeal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    denial_management_id UUID,

    appeal_reason TEXT,

    appeal_status VARCHAR(100),

    appealed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (denial_management_id)
        REFERENCES denial_management(denial_management_id)
);

CREATE TABLE resubmissions (
    resubmission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    resubmission_reason TEXT,

    resubmitted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

-- =========================================================
-- REIMBURSEMENT & PAYMENT TRACKING
-- =========================================================

CREATE TABLE reimbursement_tracking (
    reimbursement_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    reimbursement_amount NUMERIC(14,2),

    reimbursement_status VARCHAR(100),

    reimbursed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE payment_postings (
    payment_posting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    payment_reference VARCHAR(255),

    payment_amount NUMERIC(14,2),

    payment_method VARCHAR(100),

    posted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE remittance_advices (
    remittance_advice_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payment_posting_id UUID,

    remittance_number VARCHAR(255),

    remittance_details TEXT,

    received_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payment_posting_id)
        REFERENCES payment_postings(payment_posting_id)
);

CREATE TABLE payer_adjustments (
    payer_adjustment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    adjustment_reason TEXT,

    adjustment_amount NUMERIC(14,2),

    adjusted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE patient_responsibility (
    patient_responsibility_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    patient_balance NUMERIC(14,2),

    copay_amount NUMERIC(14,2),

    deductible_amount NUMERIC(14,2),

    coinsurance_amount NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

-- =========================================================
-- COORDINATION OF BENEFITS
-- =========================================================

CREATE TABLE coordination_of_benefits (
    cob_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    primary_insurance_policy_id UUID,

    secondary_insurance_policy_id UUID,

    coordination_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE secondary_claims (
    secondary_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    secondary_payer VARCHAR(255),

    claim_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE tertiary_claims (
    tertiary_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    tertiary_payer VARCHAR(255),

    claim_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE copay_collections (
    copay_collection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    collected_amount NUMERIC(14,2),

    collection_method VARCHAR(100),

    collected_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE deductible_tracking (
    deductible_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_insurance_policy_id UUID,

    deductible_total NUMERIC(14,2),

    deductible_used NUMERIC(14,2),

    deductible_remaining NUMERIC(14,2),

    updated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_insurance_policy_id)
        REFERENCES patient_insurance_policies(patient_insurance_policy_id)
);

-- =========================================================
-- COMPLIANCE & FRAUD MANAGEMENT
-- =========================================================

CREATE TABLE fraud_detection_logs (
    fraud_detection_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    fraud_indicator TEXT,

    risk_score NUMERIC(5,2),

    detected_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE compliance_validations (
    compliance_validation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    validation_type VARCHAR(255),

    validation_status VARCHAR(100),

    validation_notes TEXT,

    validated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE coding_audits (
    coding_audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    audit_type VARCHAR(255),

    audit_findings TEXT,

    audited_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

CREATE TABLE revenue_integrity_checks (
    revenue_integrity_check_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    insurance_claim_id UUID,

    integrity_status VARCHAR(100),

    integrity_notes TEXT,

    checked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (insurance_claim_id)
        REFERENCES insurance_claims(insurance_claim_id)
);

-- =========================================================
-- REPORTING & ANALYTICS
-- =========================================================

CREATE TABLE insurance_reports (
    insurance_report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    report_name VARCHAR(255),

    report_type VARCHAR(100),

    generated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE claims_analytics (
    claims_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    analytics_type VARCHAR(255),

    analytics_value NUMERIC(14,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reimbursement_metrics (
    reimbursement_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    metric_name VARCHAR(255),

    metric_value NUMERIC(14,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE denial_analytics (
    denial_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    denial_type VARCHAR(255),

    denial_count INT,

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE insurance_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE insurance_change_history (
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
-- END OF INSURANCE & CLAIMS MANAGEMENT SYSTEM
-- =========================================================