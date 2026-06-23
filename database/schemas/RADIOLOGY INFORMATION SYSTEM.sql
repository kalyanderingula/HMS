-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 9: RADIOLOGY INFORMATION SYSTEM (RIS) & PACS
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS radiology;
SET search_path TO radiology, public;

-- =========================================================
-- MASTER TABLES
-- =========================================================

CREATE TABLE radiology_departments (
    radiology_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE imaging_modalities (
    modality_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    modality_code VARCHAR(50) UNIQUE NOT NULL,

    modality_name VARCHAR(255),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- CT
-- MRI
-- XRAY
-- USG
-- PET
-- Mammography


CREATE TABLE radiology_test_categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_name VARCHAR(255) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE radiology_order_statuses (
    radiology_order_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE radiology_priorities (
    priority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    priority_name VARCHAR(100),

    priority_level INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- IMAGING ROOMS
-- =========================================================

CREATE TABLE imaging_rooms (
    imaging_room_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    room_code VARCHAR(100) UNIQUE NOT NULL,

    room_name VARCHAR(255),

    modality_id UUID,

    room_location VARCHAR(255),

    room_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

-- =========================================================
-- RADIOLOGY TESTS
-- =========================================================

CREATE TABLE radiology_tests (
    radiology_test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    test_code VARCHAR(100) UNIQUE NOT NULL,

    test_name VARCHAR(255),

    category_id UUID,

    modality_id UUID,

    radiology_department_id UUID,

    preparation_instructions TEXT,

    contrast_required BOOLEAN DEFAULT FALSE,

    estimated_duration_minutes INT,

    price NUMERIC(14,2),

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id)
        REFERENCES radiology_test_categories(category_id),

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id),

    FOREIGN KEY (radiology_department_id)
        REFERENCES radiology_departments(radiology_department_id)
);

-- =========================================================
-- RADIOLOGY PANELS
-- =========================================================

CREATE TABLE radiology_panels (
    panel_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    panel_code VARCHAR(100) UNIQUE NOT NULL,

    panel_name VARCHAR(255),

    description TEXT,

    price NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE radiology_panel_tests (
    panel_test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    panel_id UUID NOT NULL,

    radiology_test_id UUID NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (panel_id)
        REFERENCES radiology_panels(panel_id)
        ON DELETE CASCADE,

    FOREIGN KEY (radiology_test_id)
        REFERENCES radiology_tests(radiology_test_id)
);

-- =========================================================
-- RADIOLOGY ORDERS
-- =========================================================

CREATE TABLE radiology_orders (
    radiology_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    order_number VARCHAR(100) UNIQUE NOT NULL,

    patient_id UUID NOT NULL,

    encounter_id UUID,

    doctor_id UUID,

    radiology_order_status_id UUID,

    priority_id UUID,

    clinical_indication TEXT,

    ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (radiology_order_status_id)
        REFERENCES radiology_order_statuses(radiology_order_status_id),

    FOREIGN KEY (priority_id)
        REFERENCES radiology_priorities(priority_id)
);

CREATE TABLE radiology_order_items (
    order_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    radiology_order_id UUID NOT NULL,

    radiology_test_id UUID,

    panel_id UUID,

    order_status VARCHAR(100),

    ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (radiology_order_id)
        REFERENCES radiology_orders(radiology_order_id)
        ON DELETE CASCADE,

    FOREIGN KEY (radiology_test_id)
        REFERENCES radiology_tests(radiology_test_id),

    FOREIGN KEY (panel_id)
        REFERENCES radiology_panels(panel_id)
);

-- =========================================================
-- RADIOLOGY SCHEDULING
-- =========================================================

CREATE TABLE radiology_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    imaging_room_id UUID,

    radiology_test_id UUID,

    available_from TIMESTAMP,

    available_to TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (imaging_room_id)
        REFERENCES imaging_rooms(imaging_room_id),

    FOREIGN KEY (radiology_test_id)
        REFERENCES radiology_tests(radiology_test_id)
);

CREATE TABLE radiology_appointments (
    radiology_appointment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    order_item_id UUID NOT NULL,

    imaging_room_id UUID,

    scheduled_start TIMESTAMP,

    scheduled_end TIMESTAMP,

    appointment_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_item_id)
        REFERENCES radiology_order_items(order_item_id),

    FOREIGN KEY (imaging_room_id)
        REFERENCES imaging_rooms(imaging_room_id)
);

-- =========================================================
-- IMAGING STUDIES
-- =========================================================

CREATE TABLE imaging_studies (
    study_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_instance_uid VARCHAR(255) UNIQUE NOT NULL,

    radiology_appointment_id UUID,

    patient_id UUID,

    modality_id UUID,

    study_description TEXT,

    study_date TIMESTAMP,

    accession_number VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (radiology_appointment_id)
        REFERENCES radiology_appointments(radiology_appointment_id),

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

CREATE TABLE imaging_series (
    series_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    series_instance_uid VARCHAR(255) UNIQUE NOT NULL,

    series_description TEXT,

    modality_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE,

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

CREATE TABLE imaging_instances (
    instance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    series_id UUID NOT NULL,

    sop_instance_uid VARCHAR(255) UNIQUE NOT NULL,

    image_number INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (series_id)
        REFERENCES imaging_series(series_id)
        ON DELETE CASCADE
);

CREATE TABLE dicom_files (
    dicom_file_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instance_id UUID NOT NULL,

    file_path TEXT,

    file_size BIGINT,

    compression_type VARCHAR(100),

    checksum VARCHAR(255),

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (instance_id)
        REFERENCES imaging_instances(instance_id)
        ON DELETE CASCADE
);

CREATE TABLE pacs_storage (
    storage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    storage_location TEXT,

    storage_type VARCHAR(100),

    archived BOOLEAN DEFAULT FALSE,

    archived_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE
);

CREATE TABLE imaging_annotations (
    annotation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    annotated_by UUID,

    annotation_text TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE
);

-- =========================================================
-- RADIOLOGY STAFF & PROTOCOLS
-- =========================================================

CREATE TABLE radiology_technicians (
    technician_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    technician_name VARCHAR(255),

    qualification VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE radiologists (
    radiologist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    doctor_id UUID,

    specialization VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE imaging_protocols (
    protocol_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    modality_id UUID,

    protocol_name VARCHAR(255),

    protocol_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

CREATE TABLE contrast_administrations (
    contrast_administration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    contrast_name VARCHAR(255),

    dosage VARCHAR(100),

    administered_by UUID,

    administered_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE
);

CREATE TABLE radiation_dose_logs (
    dose_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    radiation_dose VARCHAR(100),

    dose_unit VARCHAR(50),

    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE
);

-- =========================================================
-- REPORTING
-- =========================================================

CREATE TABLE radiology_report_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    template_name VARCHAR(255),

    modality_id UUID,

    template_content TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

CREATE TABLE radiology_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    radiologist_id UUID,

    report_text TEXT,

    impression TEXT,

    report_status VARCHAR(100),

    reported_at TIMESTAMP,

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE,

    FOREIGN KEY (radiologist_id)
        REFERENCES radiologists(radiologist_id)
);

CREATE TABLE radiology_findings (
    finding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    report_id UUID NOT NULL,

    finding_text TEXT,

    severity VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (report_id)
        REFERENCES radiology_reports(report_id)
        ON DELETE CASCADE
);

CREATE TABLE radiology_impressions (
    impression_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    report_id UUID NOT NULL,

    impression_text TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (report_id)
        REFERENCES radiology_reports(report_id)
        ON DELETE CASCADE
);

CREATE TABLE critical_imaging_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    report_id UUID NOT NULL,

    alert_message TEXT,

    notified_to UUID,

    acknowledged BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (report_id)
        REFERENCES radiology_reports(report_id)
        ON DELETE CASCADE
);

-- =========================================================
-- AI & ADVANCED IMAGING
-- =========================================================

CREATE TABLE ai_imaging_analysis (
    ai_analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    ai_model_name VARCHAR(255),

    analysis_result TEXT,

    confidence_score NUMERIC(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE
);

CREATE TABLE imaging_measurements (
    measurement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    measurement_name VARCHAR(255),

    measurement_value VARCHAR(100),

    measurement_unit VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE
);

CREATE TABLE imaging_reconstructions (
    reconstruction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    study_id UUID NOT NULL,

    reconstruction_type VARCHAR(100),

    reconstruction_path TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (study_id)
        REFERENCES imaging_studies(study_id)
        ON DELETE CASCADE
);

-- =========================================================
-- BILLING
-- =========================================================

CREATE TABLE radiology_billing (
    radiology_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    radiology_order_id UUID NOT NULL,

    invoice_id UUID,

    billing_amount NUMERIC(14,2),

    billing_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (radiology_order_id)
        REFERENCES radiology_orders(radiology_order_id)
);

CREATE TABLE insurance_radiology_claims (
    insurance_radiology_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    radiology_billing_id UUID NOT NULL,

    insurance_provider VARCHAR(255),

    claim_amount NUMERIC(14,2),

    approved_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (radiology_billing_id)
        REFERENCES radiology_billing(radiology_billing_id)
);

-- =========================================================
-- INTEGRATIONS
-- =========================================================

CREATE TABLE modality_worklists (
    worklist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    modality_id UUID,

    worklist_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

CREATE TABLE modality_integrations (
    integration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    modality_id UUID,

    integration_type VARCHAR(100),

    integration_details TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

CREATE TABLE dicom_nodes (
    dicom_node_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ae_title VARCHAR(255),

    ip_address VARCHAR(100),

    port INT,

    node_type VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE hl7_integrations (
    hl7_integration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    integration_name VARCHAR(255),

    endpoint_url TEXT,

    integration_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- INVENTORY & MAINTENANCE
-- =========================================================

CREATE TABLE radiology_inventory (
    inventory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    item_name VARCHAR(255),

    quantity_available NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contrast_inventory (
    contrast_inventory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    contrast_name VARCHAR(255),

    quantity_available NUMERIC(14,2),

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE imaging_equipment_maintenance (
    maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    modality_id UUID,

    maintenance_type VARCHAR(100),

    maintenance_notes TEXT,

    maintenance_date TIMESTAMP,

    performed_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (modality_id)
        REFERENCES imaging_modalities(modality_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE radiology_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE radiology_change_history (
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
-- END OF RIS & PACS SCHEMA
-- =========================================================