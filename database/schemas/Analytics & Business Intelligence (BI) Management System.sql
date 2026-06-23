
-- ==========================================================
-- CATEGORY 21 : ANALYTICS & BUSINESS INTELLIGENCE (BI)
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS analytics;
SET search_path TO analytics, public;

-- DATA WAREHOUSE
CREATE TABLE data_sources (
    data_source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(255),
    source_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE data_warehouse_jobs (
    warehouse_job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(255),
    job_status VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE data_marts (
    data_mart_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mart_name VARCHAR(255),
    description TEXT
);

CREATE TABLE etl_jobs (
    etl_job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(255),
    source_id UUID REFERENCES data_sources(data_source_id)
);

CREATE TABLE etl_job_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    etl_job_id UUID REFERENCES etl_jobs(etl_job_id),
    execution_time TIMESTAMP,
    execution_status VARCHAR(100)
);

-- KPI MANAGEMENT
CREATE TABLE kpi_categories (
    kpi_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_name VARCHAR(255)
);

CREATE TABLE kpi_definitions (
    kpi_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kpi_category_id UUID REFERENCES kpi_categories(kpi_category_id),
    kpi_name VARCHAR(255)
);

CREATE TABLE kpi_targets (
    target_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kpi_id UUID REFERENCES kpi_definitions(kpi_id),
    target_value NUMERIC(18,2)
);

CREATE TABLE kpi_measurements (
    measurement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kpi_id UUID REFERENCES kpi_definitions(kpi_id),
    measured_value NUMERIC(18,2),
    measured_at TIMESTAMP
);

CREATE TABLE kpi_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kpi_id UUID REFERENCES kpi_definitions(kpi_id),
    alert_message TEXT
);

-- DASHBOARDS
CREATE TABLE dashboards (
    dashboard_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_name VARCHAR(255)
);

CREATE TABLE dashboard_widgets (
    widget_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_id UUID REFERENCES dashboards(dashboard_id),
    widget_name VARCHAR(255)
);

CREATE TABLE dashboard_filters (
    filter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_id UUID REFERENCES dashboards(dashboard_id),
    filter_name VARCHAR(255)
);

CREATE TABLE dashboard_shares (
    share_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_id UUID REFERENCES dashboards(dashboard_id),
    shared_with UUID
);

-- REPORTING
CREATE TABLE reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_name VARCHAR(255)
);

CREATE TABLE report_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(report_id),
    template_name VARCHAR(255)
);

CREATE TABLE report_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(report_id),
    schedule_type VARCHAR(100)
);

CREATE TABLE report_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(report_id),
    executed_at TIMESTAMP
);

CREATE TABLE report_exports (
    export_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(report_id),
    export_format VARCHAR(50)
);

-- CLINICAL ANALYTICS
CREATE TABLE clinical_analytics (
    clinical_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

CREATE TABLE patient_outcome_metrics (
    outcome_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

CREATE TABLE infection_control_metrics (
    infection_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

CREATE TABLE mortality_metrics (
    mortality_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

CREATE TABLE readmission_metrics (
    readmission_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

-- OPERATIONAL ANALYTICS
CREATE TABLE operational_analytics (
    operational_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

CREATE TABLE bed_utilization_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    utilization_percent NUMERIC(10,2)
);

CREATE TABLE ot_utilization_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    utilization_percent NUMERIC(10,2)
);

CREATE TABLE ambulance_utilization_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    utilization_percent NUMERIC(10,2)
);

CREATE TABLE staff_productivity_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    productivity_score NUMERIC(10,2)
);

-- FINANCIAL ANALYTICS
CREATE TABLE financial_analytics (
    financial_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(255)
);

CREATE TABLE revenue_metrics (
    revenue_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    revenue_amount NUMERIC(18,2)
);

CREATE TABLE expense_metrics (
    expense_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_amount NUMERIC(18,2)
);

CREATE TABLE profitability_metrics (
    profitability_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profit_amount NUMERIC(18,2)
);

CREATE TABLE claim_analytics (
    claim_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_metric VARCHAR(255)
);

-- PREDICTIVE ANALYTICS
CREATE TABLE predictive_models (
    model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255)
);

CREATE TABLE prediction_results (
    prediction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES predictive_models(model_id),
    prediction_value NUMERIC(18,2)
);

CREATE TABLE forecasting_models (
    forecast_model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255)
);

CREATE TABLE forecasting_results (
    forecast_result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_model_id UUID REFERENCES forecasting_models(forecast_model_id),
    forecast_value NUMERIC(18,2)
);

-- BENCHMARKING
CREATE TABLE benchmark_metrics (
    benchmark_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    benchmark_name VARCHAR(255)
);

CREATE TABLE industry_comparisons (
    comparison_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    benchmark_id UUID REFERENCES benchmark_metrics(benchmark_id),
    comparison_value NUMERIC(18,2)
);

-- DOCUMENTS & AUDIT
CREATE TABLE analytics_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_name VARCHAR(255)
);

CREATE TABLE analytics_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    note_text TEXT
);

CREATE TABLE analytics_audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(255),
    action_type VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE analytics_change_history (
    change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255),
    record_id UUID,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
