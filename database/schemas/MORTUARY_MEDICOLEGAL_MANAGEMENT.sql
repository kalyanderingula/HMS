-- ==========================================
-- MORTUARY & MEDICO-LEGAL MANAGEMENT
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS mortuary;

CREATE TABLE mortuary.mortuary_units (
    mortuary_unit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    unit_name VARCHAR(255) NOT NULL,
    building_id UUID,
    total_compartments INT NOT NULL,
    occupied_compartments INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortuary.death_records (
    death_record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    admission_id UUID,
    date_of_death TIMESTAMP NOT NULL,
    time_of_death TIME,
    cause_of_death TEXT,
    manner_of_death VARCHAR(50),
    certifying_doctor UUID,
    certificate_number VARCHAR(100),
    is_medico_legal BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortuary.body_storage_records (
    storage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    death_record_id UUID NOT NULL REFERENCES mortuary.death_records(death_record_id),
    mortuary_unit_id UUID REFERENCES mortuary.mortuary_units(mortuary_unit_id),
    compartment_number VARCHAR(20),
    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMP,
    status VARCHAR(30) DEFAULT 'stored',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortuary.body_release_records (
    release_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    death_record_id UUID NOT NULL REFERENCES mortuary.death_records(death_record_id),
    released_to VARCHAR(255) NOT NULL,
    relationship VARCHAR(100),
    id_proof_type VARCHAR(100),
    id_proof_number VARCHAR(100),
    released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    authorized_by UUID,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortuary.autopsy_records (
    autopsy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    death_record_id UUID NOT NULL REFERENCES mortuary.death_records(death_record_id),
    requested_by VARCHAR(255),
    autopsy_date TIMESTAMP,
    pathologist UUID,
    findings TEXT,
    cause_of_death_final TEXT,
    report_url TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortuary.medico_legal_cases (
    mlc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    case_number VARCHAR(100) UNIQUE NOT NULL,
    case_type VARCHAR(100) NOT NULL,
    incident_date TIMESTAMP,
    fir_number VARCHAR(100),
    police_station VARCHAR(255),
    brought_by VARCHAR(255),
    status VARCHAR(30) DEFAULT 'open',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortuary.mlc_examination_records (
    examination_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mlc_id UUID NOT NULL REFERENCES mortuary.medico_legal_cases(mlc_id),
    examined_by UUID NOT NULL,
    examination_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    findings TEXT,
    injuries_description TEXT,
    opinion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mortuary.mlc_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mlc_id UUID NOT NULL REFERENCES mortuary.medico_legal_cases(mlc_id),
    document_type VARCHAR(100) NOT NULL,
    document_name VARCHAR(255),
    file_url TEXT,
    uploaded_by UUID,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_death_records_patient ON mortuary.death_records(patient_id);
CREATE INDEX idx_death_records_date ON mortuary.death_records(date_of_death);
CREATE INDEX idx_death_records_doctor ON mortuary.death_records(certifying_doctor);
CREATE INDEX idx_body_storage_death ON mortuary.body_storage_records(death_record_id);
CREATE INDEX idx_body_storage_unit ON mortuary.body_storage_records(mortuary_unit_id);
CREATE INDEX idx_body_storage_status ON mortuary.body_storage_records(status);
CREATE INDEX idx_body_release_death ON mortuary.body_release_records(death_record_id);
CREATE INDEX idx_autopsy_death ON mortuary.autopsy_records(death_record_id);
CREATE INDEX idx_mlc_patient ON mortuary.medico_legal_cases(patient_id);
CREATE INDEX idx_mlc_case_number ON mortuary.medico_legal_cases(case_number);
CREATE INDEX idx_mlc_status ON mortuary.medico_legal_cases(status);
CREATE INDEX idx_mlc_exam_mlc ON mortuary.mlc_examination_records(mlc_id);
CREATE INDEX idx_mlc_docs_mlc ON mortuary.mlc_documents(mlc_id);
