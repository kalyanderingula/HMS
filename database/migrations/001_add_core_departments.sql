-- =========================================================
-- MIGRATION: Link all schemas to core.departments & core.sub_departments
-- Date: 2024
-- Description: Adds FK references from existing tables to the
--              new core.departments and core.sub_departments master tables
-- =========================================================

-- =========================================================
-- STEP 1: Create core.departments & core.sub_departments
-- (Already in SHARED_MASTER_TABLES.sql, included here for standalone execution)
-- =========================================================

CREATE TABLE IF NOT EXISTS core.departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_code VARCHAR(50) UNIQUE NOT NULL,
    department_name VARCHAR(255) NOT NULL,
    description TEXT,
    schema_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.sub_departments (
    sub_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_id UUID NOT NULL REFERENCES core.departments(department_id),
    sub_department_code VARCHAR(50) UNIQUE NOT NULL,
    sub_department_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- STEP 2: ALTER existing tables to add FK columns
-- =========================================================

-- human_resources.employees
ALTER TABLE human_resources.employees
    ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- human_resources.employee_department_mapping
ALTER TABLE human_resources.employee_department_mapping
    ADD COLUMN IF NOT EXISTS core_department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS core_sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- doctor.doctors
ALTER TABLE doctor.doctors
    ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- doctor.specializations
ALTER TABLE doctor.specializations
    ADD COLUMN IF NOT EXISTS sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- department.departments
ALTER TABLE department.departments
    ADD COLUMN IF NOT EXISTS core_department_id UUID REFERENCES core.departments(department_id),
    ADD COLUMN IF NOT EXISTS core_sub_department_id UUID REFERENCES core.sub_departments(sub_department_id);

-- =========================================================
-- STEP 3: Indexes for new columns
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_employees_core_dept ON human_resources.employees(department_id);
CREATE INDEX IF NOT EXISTS idx_employees_core_sub_dept ON human_resources.employees(sub_department_id);
CREATE INDEX IF NOT EXISTS idx_emp_dept_map_core_dept ON human_resources.employee_department_mapping(core_department_id);
CREATE INDEX IF NOT EXISTS idx_emp_dept_map_core_sub_dept ON human_resources.employee_department_mapping(core_sub_department_id);
CREATE INDEX IF NOT EXISTS idx_doctors_core_dept ON doctor.doctors(department_id);
CREATE INDEX IF NOT EXISTS idx_doctors_core_sub_dept ON doctor.doctors(sub_department_id);
CREATE INDEX IF NOT EXISTS idx_specializations_sub_dept ON doctor.specializations(sub_department_id);
CREATE INDEX IF NOT EXISTS idx_dept_core_dept ON department.departments(core_department_id);
CREATE INDEX IF NOT EXISTS idx_dept_core_sub_dept ON department.departments(core_sub_department_id);

-- =========================================================
-- STEP 4: Seed department codes
-- =========================================================

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
('DEP-HR', 'HR & Payroll Management', 'human_resources')
ON CONFLICT (department_code) DO NOTHING;

-- =========================================================
-- STEP 5: Seed sub-department codes
-- =========================================================

-- Doctor Specializations
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
) AS v(code, name) WHERE d.department_code = 'DEP-DOC'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Laboratory
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('LAB-BIO', 'Biochemistry'),
    ('LAB-HEM', 'Hematology'),
    ('LAB-MIC', 'Microbiology'),
    ('LAB-PATH', 'Pathology'),
    ('LAB-SER', 'Serology')
) AS v(code, name) WHERE d.department_code = 'DEP-LAB'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Radiology
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('RAD-XRAY', 'X-Ray'),
    ('RAD-CT', 'CT Scan'),
    ('RAD-MRI', 'MRI'),
    ('RAD-USG', 'Ultrasound'),
    ('RAD-MAM', 'Mammography')
) AS v(code, name) WHERE d.department_code = 'DEP-RAD'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Surgery
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('SUR-GEN', 'General Surgery'),
    ('SUR-CARD', 'Cardiac Surgery'),
    ('SUR-NEUR', 'Neuro Surgery'),
    ('SUR-ORTH', 'Orthopedic Surgery'),
    ('SUR-PLAS', 'Plastic Surgery')
) AS v(code, name) WHERE d.department_code = 'DEP-SUR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Nursing
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('NUR-ICU', 'ICU Nursing'),
    ('NUR-OT', 'OT Nursing'),
    ('NUR-GEN', 'General Ward Nursing'),
    ('NUR-PED', 'Pediatric Nursing'),
    ('NUR-ER', 'Emergency Nursing')
) AS v(code, name) WHERE d.department_code = 'DEP-NUR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Pharmacy
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('PHR-INP', 'Inpatient Pharmacy'),
    ('PHR-OUT', 'Outpatient Pharmacy'),
    ('PHR-STORE', 'Drug Store')
) AS v(code, name) WHERE d.department_code = 'DEP-PHR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- Emergency
INSERT INTO core.sub_departments (department_id, sub_department_code, sub_department_name)
SELECT d.department_id, v.code, v.name FROM core.departments d,
(VALUES
    ('ER-TRAU', 'Trauma Unit'),
    ('ER-TRIAGE', 'Triage'),
    ('ER-RESUS', 'Resuscitation')
) AS v(code, name) WHERE d.department_code = 'DEP-EMR'
ON CONFLICT (sub_department_code) DO NOTHING;

-- =========================================================
-- END OF MIGRATION
-- =========================================================
