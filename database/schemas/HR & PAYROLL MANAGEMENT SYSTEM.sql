-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 17: HR & PAYROLL MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS human_resources;
SET search_path TO human_resources, public;

-- =========================================================
-- EMPLOYEE MASTER TABLES
-- =========================================================

CREATE TABLE employee_categories (
    employee_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_code VARCHAR(100) UNIQUE NOT NULL,

    category_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employee_types (
    employee_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_code VARCHAR(100) UNIQUE NOT NULL,

    type_name VARCHAR(255),

    employment_nature VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employees (
    employee_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_number VARCHAR(100) UNIQUE NOT NULL,

    employee_category_id UUID,

    employee_type_id UUID,

    first_name VARCHAR(255),

    middle_name VARCHAR(255),

    last_name VARCHAR(255),

    gender VARCHAR(50),

    date_of_birth DATE,

    date_of_joining DATE,

    employment_status VARCHAR(100),

    official_email VARCHAR(255),

    official_phone VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_category_id)
        REFERENCES employee_categories(employee_category_id),

    FOREIGN KEY (employee_type_id)
        REFERENCES employee_types(employee_type_id)
);

CREATE TABLE employee_profiles (
    employee_profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    marital_status VARCHAR(100),

    nationality VARCHAR(100),

    blood_group VARCHAR(10),

    emergency_contact_name VARCHAR(255),

    emergency_contact_phone VARCHAR(50),

    profile_photo_url TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE employee_identifiers (
    employee_identifier_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    identifier_type VARCHAR(100),

    identifier_number VARCHAR(255),

    issued_country VARCHAR(100),

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE employee_contacts (
    employee_contact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    contact_type VARCHAR(100),

    contact_value VARCHAR(255),

    is_primary BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE employee_addresses (
    employee_address_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    address_type VARCHAR(100),

    address_line_1 TEXT,

    address_line_2 TEXT,

    city VARCHAR(100),

    state VARCHAR(100),

    postal_code VARCHAR(50),

    country VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

-- =========================================================
-- ORGANIZATIONAL STRUCTURE
-- =========================================================

CREATE TABLE departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255),

    department_type VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE designations (
    designation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    designation_code VARCHAR(100) UNIQUE NOT NULL,

    designation_name VARCHAR(255),

    designation_level VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employee_department_mapping (
    employee_department_mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    department_id UUID,

    designation_id UUID,

    assigned_from DATE,

    assigned_to DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id),

    FOREIGN KEY (designation_id)
        REFERENCES designations(designation_id)
);

CREATE TABLE reporting_hierarchy (
    reporting_hierarchy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    reporting_manager_id UUID,

    hierarchy_level INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    FOREIGN KEY (reporting_manager_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE organizational_units (
    organizational_unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    unit_name VARCHAR(255),

    parent_unit_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_unit_id)
        REFERENCES organizational_units(organizational_unit_id)
);

-- =========================================================
-- QUALIFICATIONS & CREDENTIALS
-- =========================================================

CREATE TABLE employee_qualifications (
    employee_qualification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    qualification_name VARCHAR(255),

    institution_name VARCHAR(255),

    completion_year INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE employee_certifications (
    employee_certification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    certification_name VARCHAR(255),

    issuing_authority VARCHAR(255),

    issue_date DATE,

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE employee_licenses (
    employee_license_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    license_number VARCHAR(255),

    license_type VARCHAR(255),

    issued_by VARCHAR(255),

    issue_date DATE,

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE credential_verifications (
    credential_verification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    verification_type VARCHAR(255),

    verification_status VARCHAR(100),

    verified_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE continuing_education (
    continuing_education_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    course_name VARCHAR(255),

    provider_name VARCHAR(255),

    completed_at DATE,

    credits_earned NUMERIC(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

-- =========================================================
-- RECRUITMENT & ONBOARDING
-- =========================================================

CREATE TABLE recruitment_requests (
    recruitment_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID,

    requested_position VARCHAR(255),

    requested_count INT,

    request_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

CREATE TABLE job_postings (
    job_posting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    recruitment_request_id UUID,

    job_title VARCHAR(255),

    job_description TEXT,

    posting_date DATE,

    closing_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (recruitment_request_id)
        REFERENCES recruitment_requests(recruitment_request_id)
);

CREATE TABLE candidates (
    candidate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    candidate_name VARCHAR(255),

    candidate_email VARCHAR(255),

    candidate_phone VARCHAR(50),

    applied_position VARCHAR(255),

    application_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE interviews (
    interview_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    candidate_id UUID,

    interview_round VARCHAR(100),

    interviewer_name VARCHAR(255),

    interview_date TIMESTAMP,

    interview_status VARCHAR(100),

    feedback TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (candidate_id)
        REFERENCES candidates(candidate_id)
);

CREATE TABLE onboarding_workflows (
    onboarding_workflow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    workflow_name VARCHAR(255),

    workflow_steps TEXT,

    workflow_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employee_onboarding (
    employee_onboarding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    onboarding_workflow_id UUID,

    onboarding_status VARCHAR(100),

    completed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    FOREIGN KEY (onboarding_workflow_id)
        REFERENCES onboarding_workflows(onboarding_workflow_id)
);

-- =========================================================
-- ATTENDANCE & SHIFT MANAGEMENT
-- =========================================================

CREATE TABLE attendance_records (
    attendance_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    attendance_date DATE,

    check_in_time TIMESTAMP,

    check_out_time TIMESTAMP,

    attendance_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE biometric_attendance (
    biometric_attendance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    biometric_device_id VARCHAR(255),

    biometric_timestamp TIMESTAMP,

    biometric_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE shift_schedules (
    shift_schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    shift_name VARCHAR(255),

    shift_start_time TIME,

    shift_end_time TIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employee_rosters (
    employee_roster_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    shift_schedule_id UUID,

    roster_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    FOREIGN KEY (shift_schedule_id)
        REFERENCES shift_schedules(shift_schedule_id)
);

CREATE TABLE overtime_tracking (
    overtime_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    overtime_hours NUMERIC(10,2),

    overtime_reason TEXT,

    approved_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE leave_requests (
    leave_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    leave_type VARCHAR(100),

    leave_start_date DATE,

    leave_end_date DATE,

    leave_reason TEXT,

    leave_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE leave_balances (
    leave_balance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    leave_type VARCHAR(100),

    total_leave_days NUMERIC(10,2),

    used_leave_days NUMERIC(10,2),

    remaining_leave_days NUMERIC(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE holiday_calendars (
    holiday_calendar_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    holiday_name VARCHAR(255),

    holiday_date DATE,

    holiday_type VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- PAYROLL MANAGEMENT
-- =========================================================

CREATE TABLE payroll_cycles (
    payroll_cycle_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payroll_month INT,

    payroll_year INT,

    payroll_status VARCHAR(100),

    processed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE salary_structures (
    salary_structure_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    structure_name VARCHAR(255),

    basic_salary NUMERIC(14,2),

    hra NUMERIC(14,2),

    allowances NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employee_salary_assignments (
    employee_salary_assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    salary_structure_id UUID,

    effective_from DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    FOREIGN KEY (salary_structure_id)
        REFERENCES salary_structures(salary_structure_id)
);

CREATE TABLE payroll_processing (
    payroll_processing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payroll_cycle_id UUID,

    employee_id UUID,

    gross_salary NUMERIC(14,2),

    net_salary NUMERIC(14,2),

    payroll_status VARCHAR(100),

    processed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payroll_cycle_id)
        REFERENCES payroll_cycles(payroll_cycle_id),

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE payroll_components (
    payroll_component_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payroll_processing_id UUID,

    component_name VARCHAR(255),

    component_type VARCHAR(100),

    component_amount NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payroll_processing_id)
        REFERENCES payroll_processing(payroll_processing_id)
);

CREATE TABLE payroll_deductions (
    payroll_deduction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payroll_processing_id UUID,

    deduction_name VARCHAR(255),

    deduction_amount NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payroll_processing_id)
        REFERENCES payroll_processing(payroll_processing_id)
);

CREATE TABLE tax_calculations (
    tax_calculation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payroll_processing_id UUID,

    tax_type VARCHAR(100),

    taxable_amount NUMERIC(14,2),

    tax_amount NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payroll_processing_id)
        REFERENCES payroll_processing(payroll_processing_id)
);

CREATE TABLE payslips (
    payslip_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    payroll_processing_id UUID,

    payslip_number VARCHAR(100),

    generated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payroll_processing_id)
        REFERENCES payroll_processing(payroll_processing_id)
);

-- =========================================================
-- BENEFITS & REIMBURSEMENTS
-- =========================================================

CREATE TABLE employee_benefits (
    employee_benefit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    benefit_name VARCHAR(255),

    benefit_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE insurance_benefits (
    insurance_benefit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    insurance_provider VARCHAR(255),

    policy_number VARCHAR(255),

    coverage_amount NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE retirement_plans (
    retirement_plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    retirement_plan_type VARCHAR(255),

    contribution_percentage NUMERIC(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE reimbursement_claims (
    reimbursement_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    claim_type VARCHAR(255),

    claim_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    claimed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE travel_allowances (
    travel_allowance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    travel_purpose TEXT,

    allowance_amount NUMERIC(14,2),

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

-- =========================================================
-- PERFORMANCE MANAGEMENT
-- =========================================================

CREATE TABLE employee_performance_reviews (
    employee_performance_review_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    review_period VARCHAR(100),

    review_score NUMERIC(10,2),

    reviewer_name VARCHAR(255),

    review_comments TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE kpi_tracking (
    kpi_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    kpi_name VARCHAR(255),

    kpi_value NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE appraisal_cycles (
    appraisal_cycle_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    appraisal_name VARCHAR(255),

    appraisal_start_date DATE,

    appraisal_end_date DATE,

    appraisal_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE disciplinary_actions (
    disciplinary_action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    action_type VARCHAR(255),

    action_reason TEXT,

    action_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE grievance_management (
    grievance_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    grievance_type VARCHAR(255),

    grievance_description TEXT,

    grievance_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

-- =========================================================
-- TRAINING MANAGEMENT
-- =========================================================

CREATE TABLE training_programs (
    training_program_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    program_name VARCHAR(255),

    program_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE training_sessions (
    training_session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    training_program_id UUID,

    session_date DATE,

    trainer_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (training_program_id)
        REFERENCES training_programs(training_program_id)
);

CREATE TABLE employee_training_records (
    employee_training_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    training_session_id UUID,

    completion_status VARCHAR(100),

    completion_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    FOREIGN KEY (training_session_id)
        REFERENCES training_sessions(training_session_id)
);

CREATE TABLE competency_assessments (
    competency_assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    competency_name VARCHAR(255),

    competency_score NUMERIC(10,2),

    assessed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

-- =========================================================
-- DOCUMENTS & COMPLIANCE
-- =========================================================

CREATE TABLE employee_documents (
    employee_document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    document_name VARCHAR(255),

    document_type VARCHAR(100),

    document_path TEXT,

    uploaded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE background_verifications (
    background_verification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    verification_type VARCHAR(255),

    verification_status VARCHAR(100),

    verified_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE compliance_tracking (
    compliance_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    compliance_type VARCHAR(255),

    compliance_status VARCHAR(100),

    compliance_due_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE vaccination_tracking (
    vaccination_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    vaccine_name VARCHAR(255),

    vaccination_date DATE,

    next_due_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

-- =========================================================
-- HR ANALYTICS
-- =========================================================

CREATE TABLE hr_analytics (
    hr_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    analytics_name VARCHAR(255),

    analytics_value NUMERIC(14,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workforce_metrics (
    workforce_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    metric_name VARCHAR(255),

    metric_value NUMERIC(14,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE attrition_tracking (
    attrition_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    attrition_reason TEXT,

    attrition_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
);

CREATE TABLE staffing_forecasts (
    staffing_forecast_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID,

    forecast_period VARCHAR(100),

    required_staff_count INT,

    forecast_generated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE hr_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE hr_change_history (
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
-- END OF HR & PAYROLL MANAGEMENT SYSTEM
-- =========================================================