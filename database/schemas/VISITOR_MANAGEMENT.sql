-- ==========================================
-- VISITOR MANAGEMENT
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS visitor;

CREATE TABLE visitor.visitor_purposes (
    purpose_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purpose_name VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO visitor.visitor_purposes (purpose_name) VALUES
('Patient Visit'), ('Official Meeting'), ('Vendor Visit'), ('Delivery');

CREATE TABLE visitor.visitors (
    visitor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    phone VARCHAR(20),
    id_proof_type VARCHAR(100),
    id_proof_number VARCHAR(100),
    photo_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE visitor.visitor_passes (
    pass_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    visitor_id UUID NOT NULL REFERENCES visitor.visitors(visitor_id),
    purpose_id UUID REFERENCES visitor.visitor_purposes(purpose_id),
    patient_id UUID,
    ward_id UUID,
    pass_number VARCHAR(50) UNIQUE NOT NULL,
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    check_out_time TIMESTAMP,
    expected_duration_minutes INT,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE visitor.visitor_screening (
    screening_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pass_id UUID NOT NULL REFERENCES visitor.visitor_passes(pass_id),
    temperature DECIMAL(4,1),
    has_symptoms BOOLEAN DEFAULT FALSE,
    symptoms_description TEXT,
    screening_result VARCHAR(20) DEFAULT 'pass',
    screened_by UUID,
    screened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE visitor.visitor_restrictions (
    restriction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    ward_id UUID,
    patient_id UUID,
    restriction_type VARCHAR(100) NOT NULL,
    reason TEXT,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_visitors_phone ON visitor.visitors(phone);
CREATE INDEX idx_visitor_passes_visitor ON visitor.visitor_passes(visitor_id);
CREATE INDEX idx_visitor_passes_patient ON visitor.visitor_passes(patient_id);
CREATE INDEX idx_visitor_passes_status ON visitor.visitor_passes(status);
CREATE INDEX idx_visitor_passes_checkin ON visitor.visitor_passes(check_in_time);
CREATE INDEX idx_visitor_screening_pass ON visitor.visitor_screening(pass_id);
CREATE INDEX idx_visitor_restrictions_ward ON visitor.visitor_restrictions(ward_id);
CREATE INDEX idx_visitor_restrictions_patient ON visitor.visitor_restrictions(patient_id);
