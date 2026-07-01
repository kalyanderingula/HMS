-- ==========================================
-- SHARED MASTER TABLES
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS core;

-- Buildings
CREATE TABLE core.buildings (
    building_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    building_code VARCHAR(100) UNIQUE NOT NULL,
    building_name VARCHAR(255) NOT NULL,
    address TEXT,
    total_floors INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Floors
CREATE TABLE core.floors (
    floor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    building_id UUID NOT NULL REFERENCES core.buildings(building_id),
    floor_number INT NOT NULL,
    floor_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notification Channels
CREATE TABLE core.notification_channels (
    channel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_name VARCHAR(50) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO core.notification_channels (channel_name) VALUES
('SMS'), ('Email'), ('WhatsApp'), ('Push'), ('In-App');

-- Notification Templates
CREATE TABLE core.notification_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    template_name VARCHAR(255) NOT NULL,
    channel_id UUID REFERENCES core.notification_channels(channel_id),
    subject VARCHAR(500),
    body_template TEXT NOT NULL,
    module VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE core.notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    channel_id UUID REFERENCES core.notification_channels(channel_id),
    template_id UUID REFERENCES core.notification_templates(template_id),
    recipient_id UUID,
    recipient_type VARCHAR(50),
    source_module VARCHAR(100) NOT NULL,
    source_reference_id UUID,
    subject VARCHAR(500),
    body TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hospital Service Categories
CREATE TABLE core.hospital_service_categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO core.hospital_service_categories (category_name) VALUES
('Consultation'), ('Diagnostics'), ('Procedure'), ('Therapy'), ('Pharmacy');

-- Hospital Services
CREATE TABLE core.hospital_services (
    service_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    category_id UUID REFERENCES core.hospital_service_categories(category_id),
    service_code VARCHAR(100) UNIQUE NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    department_id UUID,
    base_price DECIMAL(12,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Master Document Types
CREATE TABLE core.master_document_types (
    document_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    applicable_to VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Master Languages
CREATE TABLE core.master_languages (
    language_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language_name VARCHAR(100) UNIQUE NOT NULL,
    language_code VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- DEPARTMENTS & SUB-DEPARTMENTS (Master)
-- ==========================================

-- Master Departments
CREATE TABLE core.departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_code VARCHAR(50) UNIQUE NOT NULL,
    department_name VARCHAR(255) NOT NULL,
    description TEXT,
    schema_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sub-Departments (specializations under each department)
CREATE TABLE core.sub_departments (
    sub_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_id UUID NOT NULL REFERENCES core.departments(department_id),
    sub_department_code VARCHAR(50) UNIQUE NOT NULL,
    sub_department_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Departments
INSERT INTO core.departments (department_code, department_name, schema_name) VALUES
('DEP-PAT', 'Patient Management', 'patient'),
('DEP-DOC', 'Doctor Management', 'doctor'),
('DEP-DEPT', 'Department Management', 'department'),
('DEP-APT', 'Appointment Management', 'appointment'),
('DEP-ADM', 'Admission & Bed Management', 'admission'),
('DEP-BIL', 'Billing & Financial Management', 'billing'),
('DEP-PHR', 'Pharmacy Management', 'pharmacy'),
('DEP-LAB', 'Laboratory Information System', 'laboratory'),
('DEP-RAD', 'Radiology Information System', 'radiology'),
('DEP-EMR', 'Emergency & Trauma Management', 'emergency'),
('DEP-SUR', 'Surgery & OT Management', 'surgery'),
('DEP-ICU', 'ICU & Critical Care', 'intensive_care_unit'),
('DEP-NUR', 'Nursing Management', 'nursing'),
('DEP-INS', 'Insurance & Claims Management', 'insurance'),
('DEP-INV', 'Inventory & Procurement', 'inventory'),
('DEP-EMR2', 'Electronic Medical Records', 'electronic_medical_records'),
('DEP-AMB', 'Ambulance & Transport', 'ambulance'),
('DEP-BB', 'Blood Bank Management', 'blood_bank'),
('DEP-DIET', 'Dietetics & Nutrition', 'dietetics'),
('DEP-TELE', 'Telemedicine & Virtual Care', 'telemedicine'),
('DEP-CRM', 'CRM & Patient Engagement', 'customer_relationship_management'),
('DEP-QUE', 'Queue Management', 'queue_management'),
('DEP-HK', 'Housekeeping Management', 'housekeeping'),
('DEP-VIS', 'Visitor Management', 'visitor'),
('DEP-BMW', 'Biomedical Waste Management', 'biomedical_waste'),
('DEP-MOR', 'Mortuary & Medicolegal', 'mortuary'),
('DEP-REH', 'Rehabilitation & Physiotherapy', 'rehabilitation'),
('DEP-SEC', 'Security & IAM', 'security'),
('DEP-ANA', 'Analytics & Business Intelligence', 'analytics'),
('DEP-AI', 'AI & Clinical Decision Support', 'artificial_intelligence'),
('DEP-MH', 'Multi-Hospital Management', 'multi_hospital'),
('DEP-HR', 'HR & Payroll Management', 'human_resources');

-- Seed Sub-Departments (Doctor Specializations)
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('DOC-ENT', 'ENT (Ear, Nose, Throat)'),
    ('DOC-CARD', 'Cardiology'),
    ('DOC-ORTH', 'Orthopedics'),
    ('DOC-NEUR', 'Neurology'),
    ('DOC-DERM', 'Dermatology'),
    ('DOC-PEDI', 'Pediatrics'),
    ('DOC-GYNE', 'Gynecology'),
    ('DOC-OPTH', 'Ophthalmology'),
    ('DOC-PSYC', 'Psychiatry'),
    ('DOC-ANES', 'Anesthesiology'),
    ('DOC-ONCO', 'Oncology'),
    ('DOC-NEPH', 'Nephrology'),
    ('DOC-PULM', 'Pulmonology'),
    ('DOC-GAST', 'Gastroenterology'),
    ('DOC-ENDO', 'Endocrinology'),
    ('DOC-UROL', 'Urology'),
    ('DOC-GP', 'General Physician'),
    ('DOC-SURG', 'General Surgery')
) AS v(code, name) WHERE d.department_code = 'DEP-DOC';

-- Seed Sub-Departments (Laboratory)
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('LAB-BIO', 'Biochemistry'),
    ('LAB-HEM', 'Hematology'),
    ('LAB-MIC', 'Microbiology'),
    ('LAB-PATH', 'Pathology'),
    ('LAB-SER', 'Serology')
) AS v(code, name) WHERE d.department_code = 'DEP-LAB';

-- Seed Sub-Departments (Radiology)
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('RAD-XRAY', 'X-Ray'),
    ('RAD-CT', 'CT Scan'),
    ('RAD-MRI', 'MRI'),
    ('RAD-USG', 'Ultrasound'),
    ('RAD-MAM', 'Mammography')
) AS v(code, name) WHERE d.department_code = 'DEP-RAD';

-- Seed Sub-Departments (Surgery)
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('SUR-GEN', 'General Surgery'),
    ('SUR-CARD', 'Cardiac Surgery'),
    ('SUR-NEUR', 'Neuro Surgery'),
    ('SUR-ORTH', 'Orthopedic Surgery'),
    ('SUR-PLAS', 'Plastic Surgery')
) AS v(code, name) WHERE d.department_code = 'DEP-SUR';

-- Seed Sub-Departments (Nursing)
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('NUR-ICU', 'ICU Nursing'),
    ('NUR-OT', 'OT Nursing'),
    ('NUR-GEN', 'General Ward Nursing'),
    ('NUR-PED', 'Pediatric Nursing'),
    ('NUR-ER', 'Emergency Nursing')
) AS v(code, name) WHERE d.department_code = 'DEP-NUR';

-- Seed Sub-Departments (Pharmacy)
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('PHR-INP', 'Inpatient Pharmacy'),
    ('PHR-OUT', 'Outpatient Pharmacy'),
    ('PHR-STORE', 'Drug Store')
) AS v(code, name) WHERE d.department_code = 'DEP-PHR';

-- Seed Sub-Departments (Emergency)
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('ER-TRAU', 'Trauma Unit'),
    ('ER-TRIAGE', 'Triage'),
    ('ER-RESUS', 'Resuscitation')
) AS v(code, name) WHERE d.department_code = 'DEP-EMR';

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_core_departments_code ON core.departments(department_code);
CREATE INDEX idx_core_sub_departments_dept ON core.sub_departments(department_id);
CREATE INDEX idx_core_sub_departments_code ON core.sub_departments(sub_department_code);

-- ==========================================
-- COUNTRIES & STATES (Master)
-- ==========================================

CREATE TABLE core.countries (
    country_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_code VARCHAR(10) UNIQUE NOT NULL,
    country_name VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core.states (
    state_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_id UUID NOT NULL REFERENCES core.countries(country_id),
    state_code VARCHAR(50) UNIQUE NOT NULL,
    state_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO core.countries (country_code, country_name) VALUES
('IN', 'India'), ('US', 'United States'), ('UK', 'United Kingdom'),
('AE', 'United Arab Emirates'), ('SA', 'Saudi Arabia'), ('AU', 'Australia'),
('CA', 'Canada'), ('SG', 'Singapore'), ('DE', 'Germany'), ('FR', 'France'),
('JP', 'Japan'), ('NP', 'Nepal'), ('LK', 'Sri Lanka'), ('BD', 'Bangladesh'), ('PK', 'Pakistan');

CREATE INDEX idx_core_countries_code ON core.countries(country_code);
CREATE INDEX idx_core_states_country ON core.states(country_id);
CREATE INDEX idx_core_states_code ON core.states(state_code);

CREATE INDEX idx_buildings_tenant ON core.buildings(tenant_id);
CREATE INDEX idx_buildings_code ON core.buildings(building_code);
CREATE INDEX idx_floors_building ON core.floors(building_id);
CREATE INDEX idx_notifications_recipient ON core.notifications(recipient_id);
CREATE INDEX idx_notifications_source_module ON core.notifications(source_module);
CREATE INDEX idx_notifications_source_ref ON core.notifications(source_reference_id);
CREATE INDEX idx_notifications_status ON core.notifications(status);
CREATE INDEX idx_notification_templates_module ON core.notification_templates(module);
CREATE INDEX idx_hospital_services_category ON core.hospital_services(category_id);
CREATE INDEX idx_hospital_services_department ON core.hospital_services(department_id);
CREATE INDEX idx_hospital_services_code ON core.hospital_services(service_code);
