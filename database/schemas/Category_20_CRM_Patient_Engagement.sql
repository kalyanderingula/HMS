
-- ==========================================================
-- CATEGORY 20 : CRM & PATIENT ENGAGEMENT MANAGEMENT SYSTEM
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS customer_relationship_management;
SET search_path TO customer_relationship_management, public;

-- LEAD MANAGEMENT
CREATE TABLE lead_sources (
    lead_source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_code VARCHAR(50) UNIQUE NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lead_statuses (
    lead_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status_code VARCHAR(50),
    status_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE patient_leads (
    lead_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_source_id UUID REFERENCES lead_sources(lead_source_id),
    lead_status_id UUID REFERENCES lead_statuses(lead_status_id),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255),
    mobile_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lead_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES patient_leads(lead_id),
    assigned_employee_id UUID,
    assigned_date TIMESTAMP
);

CREATE TABLE lead_activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES patient_leads(lead_id),
    activity_type VARCHAR(100),
    activity_notes TEXT,
    activity_date TIMESTAMP
);

-- MARKETING
CREATE TABLE marketing_campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_name VARCHAR(255),
    campaign_type VARCHAR(100),
    start_date DATE,
    end_date DATE
);

CREATE TABLE campaign_channels (
    channel_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES marketing_campaigns(campaign_id),
    channel_name VARCHAR(100)
);

CREATE TABLE campaign_audiences (
    audience_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES marketing_campaigns(campaign_id),
    audience_name VARCHAR(255)
);

CREATE TABLE campaign_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES marketing_campaigns(campaign_id),
    execution_date TIMESTAMP
);

CREATE TABLE campaign_responses (
    response_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES marketing_campaigns(campaign_id),
    patient_id UUID,
    response_type VARCHAR(100)
);

-- ENQUIRIES
CREATE TABLE enquiry_categories (
    enquiry_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name VARCHAR(255)
);

CREATE TABLE patient_enquiries (
    enquiry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    enquiry_category_id UUID REFERENCES enquiry_categories(enquiry_category_id),
    enquiry_subject VARCHAR(255),
    enquiry_status VARCHAR(100)
);

CREATE TABLE enquiry_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enquiry_id UUID REFERENCES patient_enquiries(enquiry_id),
    assigned_to UUID
);

CREATE TABLE enquiry_resolutions (
    resolution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enquiry_id UUID REFERENCES patient_enquiries(enquiry_id),
    resolution_notes TEXT
);

-- CALL CENTER
CREATE TABLE call_center_agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID,
    agent_name VARCHAR(255)
);

CREATE TABLE call_logs (
    call_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES call_center_agents(agent_id),
    patient_id UUID,
    call_type VARCHAR(100)
);

CREATE TABLE call_recordings (
    recording_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_log_id UUID REFERENCES call_logs(call_log_id),
    recording_url TEXT
);

CREATE TABLE outbound_call_campaigns (
    outbound_campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_name VARCHAR(255)
);

-- NOTIFICATIONS
CREATE TABLE notification_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255),
    template_type VARCHAR(100)
);

CREATE TABLE appointment_reminders (
    reminder_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID,
    reminder_date TIMESTAMP
);

CREATE TABLE sms_notifications (
    sms_notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    template_id UUID REFERENCES notification_templates(template_id)
);

CREATE TABLE email_notifications (
    email_notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    template_id UUID REFERENCES notification_templates(template_id)
);

CREATE TABLE push_notifications (
    push_notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    template_id UUID REFERENCES notification_templates(template_id)
);

CREATE TABLE whatsapp_notifications (
    whatsapp_notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    template_id UUID REFERENCES notification_templates(template_id)
);

-- FEEDBACK & SURVEYS
CREATE TABLE feedback_categories (
    feedback_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name VARCHAR(255)
);

CREATE TABLE patient_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    feedback_category_id UUID REFERENCES feedback_categories(feedback_category_id),
    rating NUMERIC(3,2),
    feedback_text TEXT
);

CREATE TABLE patient_surveys (
    survey_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_name VARCHAR(255)
);

CREATE TABLE survey_questions (
    question_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id UUID REFERENCES patient_surveys(survey_id),
    question_text TEXT
);

CREATE TABLE survey_responses (
    response_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id UUID REFERENCES patient_surveys(survey_id),
    patient_id UUID,
    response_text TEXT
);

-- COMPLAINTS
CREATE TABLE complaint_categories (
    complaint_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name VARCHAR(255)
);

CREATE TABLE patient_complaints (
    complaint_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    complaint_category_id UUID REFERENCES complaint_categories(complaint_category_id)
);

CREATE TABLE complaint_assignments (
    complaint_assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id UUID REFERENCES patient_complaints(complaint_id)
);

CREATE TABLE complaint_resolutions (
    complaint_resolution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id UUID REFERENCES patient_complaints(complaint_id)
);

CREATE TABLE complaint_escalations (
    escalation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id UUID REFERENCES patient_complaints(complaint_id)
);

-- LOYALTY
CREATE TABLE loyalty_programs (
    loyalty_program_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_name VARCHAR(255)
);

CREATE TABLE loyalty_tiers (
    loyalty_tier_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loyalty_program_id UUID REFERENCES loyalty_programs(loyalty_program_id),
    tier_name VARCHAR(255)
);

CREATE TABLE loyalty_points (
    loyalty_point_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    points_balance INT
);

CREATE TABLE loyalty_transactions (
    loyalty_transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loyalty_point_id UUID REFERENCES loyalty_points(loyalty_point_id),
    points INT
);

-- REFERRALS
CREATE TABLE referral_programs (
    referral_program_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_name VARCHAR(255)
);

CREATE TABLE patient_referrals (
    patient_referral_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    referred_patient_id UUID
);

CREATE TABLE referral_rewards (
    reward_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_referral_id UUID REFERENCES patient_referrals(patient_referral_id)
);

-- FOLLOWUPS
CREATE TABLE followup_campaigns (
    followup_campaign_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_name VARCHAR(255)
);

CREATE TABLE followup_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    followup_campaign_id UUID REFERENCES followup_campaigns(followup_campaign_id)
);

CREATE TABLE followup_activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID REFERENCES followup_schedules(schedule_id)
);

-- ANALYTICS
CREATE TABLE engagement_scores (
    engagement_score_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    score NUMERIC(10,2)
);

CREATE TABLE patient_engagement_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    metric_name VARCHAR(255)
);

CREATE TABLE crm_analytics (
    analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analytics_name VARCHAR(255)
);

CREATE TABLE retention_metrics (
    retention_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

-- DOCUMENTS & AUDIT
CREATE TABLE crm_documents (
    crm_document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    document_name VARCHAR(255)
);

CREATE TABLE crm_notes (
    crm_note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    note_text TEXT
);

CREATE TABLE crm_audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(255),
    action_type VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crm_change_history (
    change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255),
    record_id UUID,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
