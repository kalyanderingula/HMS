-- ==========================================
-- BLOOD BANK MANAGEMENT
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS blood_bank;

CREATE TABLE blood_bank.blood_group_types (
    blood_group_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_name VARCHAR(10) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO blood_bank.blood_group_types (group_name) VALUES
('A+'), ('A-'), ('B+'), ('B-'), ('AB+'), ('AB-'), ('O+'), ('O-');

CREATE TABLE blood_bank.blood_component_types (
    blood_component_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_name VARCHAR(100) UNIQUE NOT NULL,
    shelf_life_days INT,
    storage_temperature VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO blood_bank.blood_component_types (component_name, shelf_life_days, storage_temperature) VALUES
('Whole Blood', 35, '2-6°C'),
('PRBC', 42, '2-6°C'),
('Platelets', 5, '20-24°C'),
('FFP', 365, '-18°C or below'),
('Cryoprecipitate', 365, '-18°C or below');

CREATE TABLE blood_bank.donation_types (
    donation_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO blood_bank.donation_types (type_name) VALUES
('Voluntary'), ('Replacement'), ('Autologous');

CREATE TABLE blood_bank.blood_donors (
    blood_donor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    donor_number VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20),
    blood_group_type_id UUID REFERENCES blood_bank.blood_group_types(blood_group_type_id),
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    last_donation_date DATE,
    total_donations INT DEFAULT 0,
    is_eligible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.donor_eligibility_checks (
    eligibility_check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_donor_id UUID NOT NULL REFERENCES blood_bank.blood_donors(blood_donor_id),
    check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hemoglobin DECIMAL(5,2),
    blood_pressure VARCHAR(20),
    weight DECIMAL(5,2),
    is_eligible BOOLEAN NOT NULL,
    rejection_reason TEXT,
    checked_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_donations (
    blood_donation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    blood_donor_id UUID NOT NULL REFERENCES blood_bank.blood_donors(blood_donor_id),
    donation_type_id UUID REFERENCES blood_bank.donation_types(donation_type_id),
    donation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bag_number VARCHAR(100) UNIQUE NOT NULL,
    volume_ml INT DEFAULT 450,
    collected_by UUID,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_units (
    blood_unit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    blood_donation_id UUID NOT NULL REFERENCES blood_bank.blood_donations(blood_donation_id),
    blood_component_type_id UUID REFERENCES blood_bank.blood_component_types(blood_component_type_id),
    unit_number VARCHAR(100) UNIQUE NOT NULL,
    blood_group_type_id UUID REFERENCES blood_bank.blood_group_types(blood_group_type_id),
    volume_ml INT,
    collection_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'available',
    storage_location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_screening_tests (
    screening_test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_unit_id UUID NOT NULL REFERENCES blood_bank.blood_units(blood_unit_id),
    test_name VARCHAR(100) NOT NULL,
    result VARCHAR(20) NOT NULL,
    tested_by UUID,
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_grouping_tests (
    grouping_test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_unit_id UUID NOT NULL REFERENCES blood_bank.blood_units(blood_unit_id),
    abo_group VARCHAR(10) NOT NULL,
    rh_type VARCHAR(10) NOT NULL,
    tested_by UUID,
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_requests (
    blood_request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    requested_by UUID NOT NULL,
    blood_group_type_id UUID REFERENCES blood_bank.blood_group_types(blood_group_type_id),
    blood_component_type_id UUID REFERENCES blood_bank.blood_component_types(blood_component_type_id),
    units_requested INT NOT NULL,
    urgency VARCHAR(20) DEFAULT 'routine',
    clinical_indication TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.cross_match_tests (
    cross_match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_request_id UUID REFERENCES blood_bank.blood_requests(blood_request_id),
    blood_unit_id UUID REFERENCES blood_bank.blood_units(blood_unit_id),
    patient_id UUID NOT NULL,
    result VARCHAR(20) NOT NULL,
    tested_by UUID,
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_transfusions (
    transfusion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    blood_request_id UUID REFERENCES blood_bank.blood_requests(blood_request_id),
    blood_unit_id UUID NOT NULL REFERENCES blood_bank.blood_units(blood_unit_id),
    patient_id UUID NOT NULL,
    administered_by UUID NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    volume_transfused INT,
    status VARCHAR(30) DEFAULT 'in_progress',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.transfusion_reactions (
    reaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfusion_id UUID NOT NULL REFERENCES blood_bank.blood_transfusions(transfusion_id),
    reaction_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20),
    onset_time TIMESTAMP,
    symptoms TEXT,
    action_taken TEXT,
    reported_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_inventory (
    inventory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    blood_group_type_id UUID REFERENCES blood_bank.blood_group_types(blood_group_type_id),
    blood_component_type_id UUID REFERENCES blood_bank.blood_component_types(blood_component_type_id),
    available_units INT DEFAULT 0,
    reserved_units INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_discard_records (
    discard_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blood_unit_id UUID NOT NULL REFERENCES blood_bank.blood_units(blood_unit_id),
    discard_reason VARCHAR(100) NOT NULL,
    discarded_by UUID,
    discarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blood_bank.blood_bank_audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    performed_by UUID,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_blood_donors_tenant ON blood_bank.blood_donors(tenant_id);
CREATE INDEX idx_blood_donors_number ON blood_bank.blood_donors(donor_number);
CREATE INDEX idx_blood_donors_group ON blood_bank.blood_donors(blood_group_type_id);
CREATE INDEX idx_blood_donations_donor ON blood_bank.blood_donations(blood_donor_id);
CREATE INDEX idx_blood_donations_date ON blood_bank.blood_donations(donation_date);
CREATE INDEX idx_blood_donations_bag ON blood_bank.blood_donations(bag_number);
CREATE INDEX idx_blood_units_donation ON blood_bank.blood_units(blood_donation_id);
CREATE INDEX idx_blood_units_group ON blood_bank.blood_units(blood_group_type_id);
CREATE INDEX idx_blood_units_component ON blood_bank.blood_units(blood_component_type_id);
CREATE INDEX idx_blood_units_status ON blood_bank.blood_units(status);
CREATE INDEX idx_blood_units_expiry ON blood_bank.blood_units(expiry_date);
CREATE INDEX idx_blood_screening_unit ON blood_bank.blood_screening_tests(blood_unit_id);
CREATE INDEX idx_blood_requests_patient ON blood_bank.blood_requests(patient_id);
CREATE INDEX idx_blood_requests_status ON blood_bank.blood_requests(status);
CREATE INDEX idx_cross_match_request ON blood_bank.cross_match_tests(blood_request_id);
CREATE INDEX idx_cross_match_unit ON blood_bank.cross_match_tests(blood_unit_id);
CREATE INDEX idx_transfusions_patient ON blood_bank.blood_transfusions(patient_id);
CREATE INDEX idx_transfusions_unit ON blood_bank.blood_transfusions(blood_unit_id);
CREATE INDEX idx_transfusion_reactions_transfusion ON blood_bank.transfusion_reactions(transfusion_id);
CREATE INDEX idx_blood_inventory_group ON blood_bank.blood_inventory(blood_group_type_id);
CREATE INDEX idx_blood_discard_unit ON blood_bank.blood_discard_records(blood_unit_id);
CREATE INDEX idx_blood_audit_entity ON blood_bank.blood_bank_audit_logs(entity_type, entity_id);
