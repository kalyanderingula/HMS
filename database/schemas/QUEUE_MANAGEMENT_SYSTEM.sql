-- ==========================================
-- QUEUE MANAGEMENT SYSTEM
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS queue_management;

CREATE TABLE queue_management.queue_service_points (
    service_point_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    point_name VARCHAR(255) NOT NULL,
    department_id UUID,
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE queue_management.queue_configurations (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_point_id UUID NOT NULL REFERENCES queue_management.queue_service_points(service_point_id),
    max_tokens_per_day INT,
    avg_service_time_minutes INT,
    priority_enabled BOOLEAN DEFAULT TRUE,
    auto_call_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE queue_management.queue_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    service_point_id UUID NOT NULL REFERENCES queue_management.queue_service_points(service_point_id),
    token_number VARCHAR(20) NOT NULL,
    patient_id UUID,
    appointment_id UUID,
    token_type VARCHAR(30) DEFAULT 'walk_in',
    priority INT DEFAULT 0,
    status VARCHAR(30) DEFAULT 'issued',
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    called_at TIMESTAMP,
    serving_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE queue_management.queue_calls (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id UUID NOT NULL REFERENCES queue_management.queue_tokens(token_id),
    service_point_id UUID REFERENCES queue_management.queue_service_points(service_point_id),
    called_by UUID,
    call_type VARCHAR(20) DEFAULT 'initial',
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE queue_management.queue_wait_time_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id UUID NOT NULL REFERENCES queue_management.queue_tokens(token_id),
    wait_time_minutes INT,
    service_time_minutes INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE queue_management.queue_display_configs (
    display_config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_point_id UUID REFERENCES queue_management.queue_service_points(service_point_id),
    display_name VARCHAR(255),
    display_location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE queue_management.queue_analytics (
    analytics_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    service_point_id UUID REFERENCES queue_management.queue_service_points(service_point_id),
    analytics_date DATE NOT NULL,
    total_tokens INT DEFAULT 0,
    avg_wait_time_minutes INT,
    avg_service_time_minutes INT,
    no_show_count INT DEFAULT 0,
    peak_hour INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_queue_tokens_service_point ON queue_management.queue_tokens(service_point_id);
CREATE INDEX idx_queue_tokens_patient ON queue_management.queue_tokens(patient_id);
CREATE INDEX idx_queue_tokens_status ON queue_management.queue_tokens(status);
CREATE INDEX idx_queue_tokens_issued ON queue_management.queue_tokens(issued_at);
CREATE INDEX idx_queue_tokens_type ON queue_management.queue_tokens(token_type);
CREATE INDEX idx_queue_calls_token ON queue_management.queue_calls(token_id);
CREATE INDEX idx_queue_wait_time_token ON queue_management.queue_wait_time_logs(token_id);
CREATE INDEX idx_queue_analytics_point ON queue_management.queue_analytics(service_point_id);
CREATE INDEX idx_queue_analytics_date ON queue_management.queue_analytics(analytics_date);
