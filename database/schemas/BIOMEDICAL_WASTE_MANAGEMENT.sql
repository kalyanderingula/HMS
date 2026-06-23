-- ==========================================
-- BIOMEDICAL WASTE MANAGEMENT
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS biomedical_waste;

CREATE TABLE biomedical_waste.waste_categories (
    waste_category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    category_name VARCHAR(100) NOT NULL,
    color_code VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO biomedical_waste.waste_categories (category_name, color_code) VALUES
('Infectious waste', 'Yellow'),
('Contaminated recyclables', 'Red'),
('Glassware', 'Blue'),
('Sharps', 'White'),
('General non-hazardous', 'Black');

CREATE TABLE biomedical_waste.waste_disposal_methods (
    disposal_method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    method_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO biomedical_waste.waste_disposal_methods (method_name) VALUES
('Incineration'), ('Autoclaving'), ('Chemical treatment'), ('Deep burial'), ('Recycling');

CREATE TABLE biomedical_waste.waste_generation_points (
    generation_point_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    department_id UUID,
    location_name VARCHAR(255) NOT NULL,
    building_id UUID,
    floor_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE biomedical_waste.waste_collection_records (
    collection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    generation_point_id UUID NOT NULL REFERENCES biomedical_waste.waste_generation_points(generation_point_id),
    waste_category_id UUID NOT NULL REFERENCES biomedical_waste.waste_categories(waste_category_id),
    collection_date DATE NOT NULL,
    weight_kg DECIMAL(8,3) NOT NULL,
    collected_by UUID,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE biomedical_waste.waste_disposal_records (
    disposal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    collection_id UUID REFERENCES biomedical_waste.waste_collection_records(collection_id),
    disposal_method_id UUID REFERENCES biomedical_waste.waste_disposal_methods(disposal_method_id),
    disposal_date TIMESTAMP NOT NULL,
    vendor_name VARCHAR(255),
    manifest_number VARCHAR(100),
    weight_kg DECIMAL(8,3),
    disposed_by UUID,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE biomedical_waste.waste_transport_records (
    transport_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    disposal_id UUID REFERENCES biomedical_waste.waste_disposal_records(disposal_id),
    vehicle_number VARCHAR(50),
    driver_name VARCHAR(255),
    departure_time TIMESTAMP,
    arrival_time TIMESTAMP,
    destination VARCHAR(255),
    manifest_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE biomedical_waste.waste_compliance_checks (
    compliance_check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    department_id UUID,
    inspection_date DATE NOT NULL,
    inspector_name VARCHAR(255),
    compliance_status VARCHAR(30) NOT NULL,
    findings TEXT,
    corrective_action TEXT,
    next_inspection_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE biomedical_waste.waste_spill_incidents (
    spill_incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    location VARCHAR(255) NOT NULL,
    incident_date TIMESTAMP NOT NULL,
    waste_category_id UUID REFERENCES biomedical_waste.waste_categories(waste_category_id),
    description TEXT,
    action_taken TEXT,
    reported_by UUID,
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE biomedical_waste.sharps_injury_records (
    injury_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    employee_id UUID NOT NULL,
    incident_date TIMESTAMP NOT NULL,
    location VARCHAR(255),
    injury_type VARCHAR(100),
    device_involved VARCHAR(100),
    patient_id UUID,
    action_taken TEXT,
    follow_up_status VARCHAR(30),
    reported_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_waste_generation_dept ON biomedical_waste.waste_generation_points(department_id);
CREATE INDEX idx_waste_collection_point ON biomedical_waste.waste_collection_records(generation_point_id);
CREATE INDEX idx_waste_collection_category ON biomedical_waste.waste_collection_records(waste_category_id);
CREATE INDEX idx_waste_collection_date ON biomedical_waste.waste_collection_records(collection_date);
CREATE INDEX idx_waste_disposal_collection ON biomedical_waste.waste_disposal_records(collection_id);
CREATE INDEX idx_waste_disposal_method ON biomedical_waste.waste_disposal_records(disposal_method_id);
CREATE INDEX idx_waste_disposal_date ON biomedical_waste.waste_disposal_records(disposal_date);
CREATE INDEX idx_waste_transport_disposal ON biomedical_waste.waste_transport_records(disposal_id);
CREATE INDEX idx_waste_compliance_dept ON biomedical_waste.waste_compliance_checks(department_id);
CREATE INDEX idx_waste_compliance_date ON biomedical_waste.waste_compliance_checks(inspection_date);
CREATE INDEX idx_waste_spill_date ON biomedical_waste.waste_spill_incidents(incident_date);
CREATE INDEX idx_sharps_injury_employee ON biomedical_waste.sharps_injury_records(employee_id);
CREATE INDEX idx_sharps_injury_date ON biomedical_waste.sharps_injury_records(incident_date);
