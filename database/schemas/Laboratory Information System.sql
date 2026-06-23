-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 8: LABORATORY INFORMATION SYSTEM (LIS)
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS laboratory;
SET search_path TO laboratory, public;

-- =========================================================
-- LAB DEPARTMENTS
-- =========================================================

CREATE TABLE lab_departments (
    lab_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255) NOT NULL,

    description TEXT,

    department_head UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- LAB TEST MASTER
-- =========================================================

CREATE TABLE lab_test_categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_name VARCHAR(255) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_test_subcategories (
    subcategory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_id UUID NOT NULL,

    subcategory_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id)
        REFERENCES lab_test_categories(category_id)
);

CREATE TABLE lab_tests (
    test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    test_code VARCHAR(100) UNIQUE NOT NULL,

    test_name VARCHAR(255) NOT NULL,

    category_id UUID,

    subcategory_id UUID,

    lab_department_id UUID,

    test_method VARCHAR(255),

    turnaround_time_hours INT,

    sample_volume VARCHAR(100),

    fasting_required BOOLEAN DEFAULT FALSE,

    is_active BOOLEAN DEFAULT TRUE,

    price NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id)
        REFERENCES lab_test_categories(category_id),

    FOREIGN KEY (subcategory_id)
        REFERENCES lab_test_subcategories(subcategory_id),

    FOREIGN KEY (lab_department_id)
        REFERENCES lab_departments(lab_department_id)
);

CREATE TABLE lab_test_parameters (
    parameter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    test_id UUID NOT NULL,

    parameter_name VARCHAR(255),

    unit VARCHAR(100),

    normal_range VARCHAR(255),

    critical_low NUMERIC(14,2),

    critical_high NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (test_id)
        REFERENCES lab_tests(test_id)
        ON DELETE CASCADE
);

CREATE TABLE lab_test_reference_ranges (
    reference_range_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    parameter_id UUID NOT NULL,

    gender VARCHAR(20),

    min_age INT,

    max_age INT,

    min_value NUMERIC(14,2),

    max_value NUMERIC(14,2),

    reference_text TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parameter_id)
        REFERENCES lab_test_parameters(parameter_id)
        ON DELETE CASCADE
);

-- =========================================================
-- LAB PANELS
-- =========================================================

CREATE TABLE lab_panels (
    panel_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    panel_code VARCHAR(100) UNIQUE NOT NULL,

    panel_name VARCHAR(255),

    description TEXT,

    price NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_panel_tests (
    panel_test_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    panel_id UUID NOT NULL,

    test_id UUID NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (panel_id)
        REFERENCES lab_panels(panel_id)
        ON DELETE CASCADE,

    FOREIGN KEY (test_id)
        REFERENCES lab_tests(test_id)
);

-- =========================================================
-- LAB ORDERS
-- =========================================================

CREATE TABLE lab_order_statuses (
    lab_order_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_order_priorities (
    priority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    priority_name VARCHAR(100) UNIQUE NOT NULL,

    priority_level INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_orders (
    lab_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    order_number VARCHAR(100) UNIQUE NOT NULL,

    patient_id UUID NOT NULL,

    encounter_id UUID,

    doctor_id UUID,

    lab_order_status_id UUID,

    priority_id UUID,

    ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    clinical_notes TEXT,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_order_status_id)
        REFERENCES lab_order_statuses(lab_order_status_id),

    FOREIGN KEY (priority_id)
        REFERENCES lab_order_priorities(priority_id)
);

CREATE TABLE lab_order_items (
    order_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    lab_order_id UUID NOT NULL,

    test_id UUID,

    panel_id UUID,

    order_status VARCHAR(100),

    ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_order_id)
        REFERENCES lab_orders(lab_order_id)
        ON DELETE CASCADE,

    FOREIGN KEY (test_id)
        REFERENCES lab_tests(test_id),

    FOREIGN KEY (panel_id)
        REFERENCES lab_panels(panel_id)
);

CREATE TABLE lab_order_notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    lab_order_id UUID NOT NULL,

    note_text TEXT,

    added_by UUID,

    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_order_id)
        REFERENCES lab_orders(lab_order_id)
        ON DELETE CASCADE
);

CREATE TABLE lab_order_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    lab_order_id UUID NOT NULL,

    document_name VARCHAR(255),

    file_path TEXT,

    uploaded_by UUID,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_order_id)
        REFERENCES lab_orders(lab_order_id)
        ON DELETE CASCADE
);

-- =========================================================
-- SAMPLE MANAGEMENT
-- =========================================================

CREATE TABLE sample_types (
    sample_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sample_type_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE specimen_containers (
    container_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    container_name VARCHAR(255),

    container_color VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_samples (
    sample_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sample_barcode VARCHAR(255) UNIQUE NOT NULL,

    order_item_id UUID NOT NULL,

    sample_type_id UUID,

    container_id UUID,

    collected_at TIMESTAMP,

    received_at TIMESTAMP,

    sample_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_item_id)
        REFERENCES lab_order_items(order_item_id),

    FOREIGN KEY (sample_type_id)
        REFERENCES sample_types(sample_type_id),

    FOREIGN KEY (container_id)
        REFERENCES specimen_containers(container_id)
);

CREATE TABLE sample_collection (
    collection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sample_id UUID NOT NULL,

    collected_by UUID,

    collection_site VARCHAR(255),

    collection_notes TEXT,

    collected_at TIMESTAMP,

    FOREIGN KEY (sample_id)
        REFERENCES lab_samples(sample_id)
        ON DELETE CASCADE
);

CREATE TABLE sample_tracking (
    tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sample_id UUID NOT NULL,

    location_name VARCHAR(255),

    status VARCHAR(100),

    updated_by UUID,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sample_id)
        REFERENCES lab_samples(sample_id)
        ON DELETE CASCADE
);

CREATE TABLE sample_rejections (
    rejection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sample_id UUID NOT NULL,

    rejection_reason TEXT,

    rejected_by UUID,

    rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sample_id)
        REFERENCES lab_samples(sample_id)
        ON DELETE CASCADE
);

CREATE TABLE sample_storage (
    storage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sample_id UUID NOT NULL,

    storage_location VARCHAR(255),

    temperature VARCHAR(100),

    stored_at TIMESTAMP,

    FOREIGN KEY (sample_id)
        REFERENCES lab_samples(sample_id)
        ON DELETE CASCADE
);

-- =========================================================
-- LAB WORKLISTS
-- =========================================================

CREATE TABLE lab_worklists (
    worklist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    worklist_name VARCHAR(255),

    lab_department_id UUID,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_department_id)
        REFERENCES lab_departments(lab_department_id)
);

CREATE TABLE lab_worklist_items (
    worklist_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    worklist_id UUID NOT NULL,

    sample_id UUID NOT NULL,

    assigned_to UUID,

    work_status VARCHAR(100),

    FOREIGN KEY (worklist_id)
        REFERENCES lab_worklists(worklist_id)
        ON DELETE CASCADE,

    FOREIGN KEY (sample_id)
        REFERENCES lab_samples(sample_id)
);

CREATE TABLE lab_technicians (
    technician_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    technician_name VARCHAR(255),

    qualification VARCHAR(255),

    specialization VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- RESULTS MANAGEMENT
-- =========================================================

CREATE TABLE lab_result_entries (
    result_entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    order_item_id UUID NOT NULL,

    technician_id UUID,

    result_status VARCHAR(100),

    entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    approved_by UUID,

    approved_at TIMESTAMP,

    remarks TEXT,

    FOREIGN KEY (order_item_id)
        REFERENCES lab_order_items(order_item_id)
        ON DELETE CASCADE
);

CREATE TABLE lab_result_parameters (
    result_parameter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    result_entry_id UUID NOT NULL,

    parameter_id UUID NOT NULL,

    result_value VARCHAR(255),

    result_flag VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (result_entry_id)
        REFERENCES lab_result_entries(result_entry_id)
        ON DELETE CASCADE,

    FOREIGN KEY (parameter_id)
        REFERENCES lab_test_parameters(parameter_id)
);

CREATE TABLE lab_result_approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    result_entry_id UUID NOT NULL,

    approved_by UUID,

    approval_status VARCHAR(100),

    approval_notes TEXT,

    approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (result_entry_id)
        REFERENCES lab_result_entries(result_entry_id)
        ON DELETE CASCADE
);

CREATE TABLE lab_result_amendments (
    amendment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    result_entry_id UUID NOT NULL,

    old_value TEXT,

    new_value TEXT,

    amendment_reason TEXT,

    amended_by UUID,

    amended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (result_entry_id)
        REFERENCES lab_result_entries(result_entry_id)
        ON DELETE CASCADE
);

CREATE TABLE critical_result_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    result_entry_id UUID NOT NULL,

    alert_message TEXT,

    notified_to UUID,

    acknowledged BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (result_entry_id)
        REFERENCES lab_result_entries(result_entry_id)
        ON DELETE CASCADE
);

-- =========================================================
-- MICROBIOLOGY & PATHOLOGY
-- =========================================================

CREATE TABLE microbiology_cultures (
    culture_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    result_entry_id UUID NOT NULL,

    organism_name VARCHAR(255),

    growth_status VARCHAR(100),

    colony_count VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (result_entry_id)
        REFERENCES lab_result_entries(result_entry_id)
);

CREATE TABLE antibiograms (
    antibiogram_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    culture_id UUID NOT NULL,

    antibiotic_name VARCHAR(255),

    sensitivity_result VARCHAR(100),

    mic_value VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (culture_id)
        REFERENCES microbiology_cultures(culture_id)
);

CREATE TABLE pathology_reports (
    pathology_report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    result_entry_id UUID NOT NULL,

    report_text TEXT,

    diagnosis TEXT,

    approved_by UUID,

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (result_entry_id)
        REFERENCES lab_result_entries(result_entry_id)
);

CREATE TABLE histopathology_results (
    histopathology_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pathology_report_id UUID NOT NULL,

    tissue_description TEXT,

    microscopic_findings TEXT,

    diagnosis TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pathology_report_id)
        REFERENCES pathology_reports(pathology_report_id)
);

CREATE TABLE cytology_results (
    cytology_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pathology_report_id UUID NOT NULL,

    specimen_description TEXT,

    cytology_findings TEXT,

    diagnosis TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pathology_report_id)
        REFERENCES pathology_reports(pathology_report_id)
);

-- =========================================================
-- LAB INSTRUMENTS & QC
-- =========================================================

CREATE TABLE lab_instruments (
    instrument_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instrument_code VARCHAR(100) UNIQUE,

    instrument_name VARCHAR(255),

    manufacturer VARCHAR(255),

    model_number VARCHAR(255),

    serial_number VARCHAR(255),

    installation_date DATE,

    status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE instrument_interfaces (
    interface_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instrument_id UUID NOT NULL,

    interface_type VARCHAR(100),

    connection_details TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (instrument_id)
        REFERENCES lab_instruments(instrument_id)
);

CREATE TABLE instrument_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instrument_id UUID NOT NULL,

    run_date TIMESTAMP,

    operator_id UUID,

    run_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (instrument_id)
        REFERENCES lab_instruments(instrument_id)
);

CREATE TABLE qc_rules (
    qc_rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instrument_id UUID,

    qc_rule_name VARCHAR(255),

    qc_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (instrument_id)
        REFERENCES lab_instruments(instrument_id)
);

CREATE TABLE qc_results (
    qc_result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    qc_rule_id UUID NOT NULL,

    qc_result_value VARCHAR(255),

    qc_status VARCHAR(100),

    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (qc_rule_id)
        REFERENCES qc_rules(qc_rule_id)
);

CREATE TABLE calibration_logs (
    calibration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instrument_id UUID NOT NULL,

    calibrated_by UUID,

    calibration_date TIMESTAMP,

    calibration_status VARCHAR(100),

    notes TEXT,

    FOREIGN KEY (instrument_id)
        REFERENCES lab_instruments(instrument_id)
);

CREATE TABLE maintenance_logs (
    maintenance_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    instrument_id UUID NOT NULL,

    maintenance_type VARCHAR(100),

    maintenance_notes TEXT,

    performed_by UUID,

    maintenance_date TIMESTAMP,

    FOREIGN KEY (instrument_id)
        REFERENCES lab_instruments(instrument_id)
);

-- =========================================================
-- LAB INVENTORY
-- =========================================================

CREATE TABLE lab_inventory_items (
    inventory_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    item_code VARCHAR(100),

    item_name VARCHAR(255),

    quantity_available NUMERIC(14,2),

    reorder_level NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reagent_lots (
    reagent_lot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID NOT NULL,

    lot_number VARCHAR(255),

    expiry_date DATE,

    quantity_received NUMERIC(14,2),

    quantity_remaining NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES lab_inventory_items(inventory_item_id)
);

CREATE TABLE reagent_usage (
    usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    reagent_lot_id UUID NOT NULL,

    quantity_used NUMERIC(14,2),

    used_for_test UUID,

    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reagent_lot_id)
        REFERENCES reagent_lots(reagent_lot_id)
);

CREATE TABLE lab_consumables (
    consumable_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    consumable_name VARCHAR(255),

    quantity_available NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- LAB BILLING
-- =========================================================

CREATE TABLE lab_billing (
    lab_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    lab_order_id UUID NOT NULL,

    invoice_id UUID,

    billing_amount NUMERIC(14,2),

    billing_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_order_id)
        REFERENCES lab_orders(lab_order_id)
);

CREATE TABLE insurance_lab_claims (
    insurance_lab_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    lab_billing_id UUID NOT NULL,

    insurance_provider VARCHAR(255),

    claim_amount NUMERIC(14,2),

    approved_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_billing_id)
        REFERENCES lab_billing(lab_billing_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE lab_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_change_history (
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
-- INDEXES
-- =========================================================

CREATE INDEX idx_lab_tests_category ON lab_tests(category_id);
CREATE INDEX idx_lab_tests_department ON lab_tests(lab_department_id);
CREATE INDEX idx_lab_tests_code ON lab_tests(test_code);
CREATE INDEX idx_lab_test_params_test ON lab_test_parameters(test_id);
CREATE INDEX idx_lab_test_ref_ranges_param ON lab_test_reference_ranges(parameter_id);
CREATE INDEX idx_lab_panel_tests_panel ON lab_panel_tests(panel_id);
CREATE INDEX idx_lab_panel_tests_test ON lab_panel_tests(test_id);
CREATE INDEX idx_lab_orders_patient ON lab_orders(patient_id);
CREATE INDEX idx_lab_orders_doctor ON lab_orders(doctor_id);
CREATE INDEX idx_lab_orders_encounter ON lab_orders(encounter_id);
CREATE INDEX idx_lab_orders_status ON lab_orders(lab_order_status_id);
CREATE INDEX idx_lab_order_items_order ON lab_order_items(lab_order_id);
CREATE INDEX idx_lab_order_items_test ON lab_order_items(test_id);
CREATE INDEX idx_lab_samples_barcode ON lab_samples(sample_barcode);
CREATE INDEX idx_lab_samples_order_item ON lab_samples(order_item_id);
CREATE INDEX idx_lab_samples_status ON lab_samples(sample_status);
CREATE INDEX idx_sample_collection_sample ON sample_collection(sample_id);
CREATE INDEX idx_sample_tracking_sample ON sample_tracking(sample_id);
CREATE INDEX idx_lab_result_entries_order_item ON lab_result_entries(order_item_id);
CREATE INDEX idx_lab_result_entries_status ON lab_result_entries(result_status);
CREATE INDEX idx_lab_result_params_entry ON lab_result_parameters(result_entry_id);
CREATE INDEX idx_lab_result_params_param ON lab_result_parameters(parameter_id);
CREATE INDEX idx_microbiology_cultures_result ON microbiology_cultures(result_entry_id);
CREATE INDEX idx_antibiograms_culture ON antibiograms(culture_id);
CREATE INDEX idx_pathology_reports_result ON pathology_reports(result_entry_id);
CREATE INDEX idx_lab_worklist_items_worklist ON lab_worklist_items(worklist_id);
CREATE INDEX idx_lab_worklist_items_sample ON lab_worklist_items(sample_id);
CREATE INDEX idx_instrument_runs_instrument ON instrument_runs(instrument_id);
CREATE INDEX idx_reagent_lots_item ON reagent_lots(inventory_item_id);
CREATE INDEX idx_lab_billing_order ON lab_billing(lab_order_id);
CREATE INDEX idx_lab_audit_entity ON lab_audit_logs(entity_name, entity_id);

-- =========================================================
-- END OF LABORATORY INFORMATION SYSTEM (LIS)
-- =========================================================