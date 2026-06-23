-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 10: PHARMACY MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS pharmacy;
SET search_path TO pharmacy, public;

-- =========================================================
-- PHARMACY MASTER TABLES
-- =========================================================

CREATE TABLE pharmacy_departments (
    pharmacy_department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_code VARCHAR(100) UNIQUE NOT NULL,

    department_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pharmacy_locations (
    pharmacy_location_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    location_name VARCHAR(255),

    building_name VARCHAR(255),

    floor_number VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pharmacy_stores (
    pharmacy_store_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pharmacy_location_id UUID,

    store_code VARCHAR(100) UNIQUE NOT NULL,

    store_name VARCHAR(255),

    store_type VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pharmacy_location_id)
        REFERENCES pharmacy_locations(pharmacy_location_id)
);

CREATE TABLE pharmacy_counters (
    counter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pharmacy_store_id UUID,

    counter_name VARCHAR(255),

    counter_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pharmacy_store_id)
        REFERENCES pharmacy_stores(pharmacy_store_id)
);

-- =========================================================
-- DRUG MASTER
-- =========================================================

CREATE TABLE drug_categories (
    drug_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_name VARCHAR(255) UNIQUE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drug_subcategories (
    drug_subcategory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_category_id UUID,

    subcategory_name VARCHAR(255),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_category_id)
        REFERENCES drug_categories(drug_category_id)
);

CREATE TABLE drug_forms (
    drug_form_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    form_name VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Tablet
-- Capsule
-- Syrup
-- Injection
-- Ointment


CREATE TABLE drug_units (
    drug_unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    unit_name VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- mg
-- ml
-- gm
-- IU


CREATE TABLE drug_strengths (
    drug_strength_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    strength_value VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drug_brands (
    drug_brand_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    brand_name VARCHAR(255),

    manufacturer_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drugs (
    drug_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_code VARCHAR(100) UNIQUE NOT NULL,

    generic_name VARCHAR(255) NOT NULL,

    scientific_name VARCHAR(255),

    drug_category_id UUID,

    drug_subcategory_id UUID,

    drug_form_id UUID,

    drug_unit_id UUID,

    drug_strength_id UUID,

    drug_brand_id UUID,

    is_controlled_substance BOOLEAN DEFAULT FALSE,

    requires_prescription BOOLEAN DEFAULT TRUE,

    storage_conditions TEXT,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_category_id)
        REFERENCES drug_categories(drug_category_id),

    FOREIGN KEY (drug_subcategory_id)
        REFERENCES drug_subcategories(drug_subcategory_id),

    FOREIGN KEY (drug_form_id)
        REFERENCES drug_forms(drug_form_id),

    FOREIGN KEY (drug_unit_id)
        REFERENCES drug_units(drug_unit_id),

    FOREIGN KEY (drug_strength_id)
        REFERENCES drug_strengths(drug_strength_id),

    FOREIGN KEY (drug_brand_id)
        REFERENCES drug_brands(drug_brand_id)
);

CREATE TABLE drug_generic_mapping (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_id UUID,

    mapped_generic_drug_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),

    FOREIGN KEY (mapped_generic_drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE drug_interactions (
    interaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_id UUID,

    interacting_drug_id UUID,

    interaction_severity VARCHAR(100),

    interaction_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),

    FOREIGN KEY (interacting_drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE drug_contraindications (
    contraindication_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_id UUID,

    contraindication_condition TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE drug_allergies (
    drug_allergy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_id UUID,

    allergy_description TEXT,

    severity VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

-- =========================================================
-- PRESCRIPTIONS
-- =========================================================

CREATE TABLE prescription_statuses (
    prescription_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prescriptions (
    prescription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    prescription_number VARCHAR(100) UNIQUE NOT NULL,

    patient_id UUID NOT NULL,

    encounter_id UUID,

    doctor_id UUID,

    prescription_status_id UUID,

    diagnosis TEXT,

    prescription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    valid_until DATE,

    notes TEXT,

    created_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_status_id)
        REFERENCES prescription_statuses(prescription_status_id)
);

CREATE TABLE prescription_items (
    prescription_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    prescription_id UUID,

    drug_id UUID,

    dosage VARCHAR(255),

    frequency VARCHAR(255),

    duration VARCHAR(255),

    route VARCHAR(100),

    quantity_prescribed NUMERIC(14,2),

    instructions TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_id)
        REFERENCES prescriptions(prescription_id)
        ON DELETE CASCADE,

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE prescription_refills (
    refill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    prescription_item_id UUID,

    refill_number INT,

    refill_date TIMESTAMP,

    approved_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_item_id)
        REFERENCES prescription_items(prescription_item_id)
);

CREATE TABLE prescription_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    template_name VARCHAR(255),

    doctor_id UUID,

    template_content TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE e_prescriptions (
    e_prescription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    prescription_id UUID,

    digital_signature TEXT,

    transmission_status VARCHAR(100),

    transmitted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_id)
        REFERENCES prescriptions(prescription_id)
);

-- =========================================================
-- DISPENSING
-- =========================================================

CREATE TABLE dispensing_records (
    dispensing_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    prescription_id UUID,

    dispensed_by UUID,

    dispensing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    dispensing_status VARCHAR(100),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_id)
        REFERENCES prescriptions(prescription_id)
);

CREATE TABLE dispensing_items (
    dispensing_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    dispensing_record_id UUID,

    prescription_item_id UUID,

    batch_id UUID,

    quantity_dispensed NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dispensing_record_id)
        REFERENCES dispensing_records(dispensing_record_id),

    FOREIGN KEY (prescription_item_id)
        REFERENCES prescription_items(prescription_item_id)
);

CREATE TABLE dispensing_batches (
    dispensing_batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    dispensing_item_id UUID,

    batch_number VARCHAR(255),

    expiry_date DATE,

    quantity_used NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dispensing_item_id)
        REFERENCES dispensing_items(dispensing_item_id)
);

CREATE TABLE dispensing_returns (
    return_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    dispensing_item_id UUID,

    returned_quantity NUMERIC(14,2),

    return_reason TEXT,

    returned_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dispensing_item_id)
        REFERENCES dispensing_items(dispensing_item_id)
);

CREATE TABLE medication_administration (
    administration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    prescription_item_id UUID,

    administered_by UUID,

    administered_at TIMESTAMP,

    dosage_administered VARCHAR(255),

    administration_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_item_id)
        REFERENCES prescription_items(prescription_item_id)
);

-- =========================================================
-- INVENTORY MANAGEMENT
-- =========================================================

CREATE TABLE pharmacy_inventory (
    inventory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pharmacy_store_id UUID,

    drug_id UUID,

    available_quantity NUMERIC(14,2),

    reserved_quantity NUMERIC(14,2),

    reorder_level NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pharmacy_store_id)
        REFERENCES pharmacy_stores(pharmacy_store_id),

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE pharmacy_stock_batches (
    batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_id UUID,

    batch_number VARCHAR(255),

    manufacturing_date DATE,

    expiry_date DATE,

    quantity_received NUMERIC(14,2),

    quantity_remaining NUMERIC(14,2),

    purchase_price NUMERIC(14,2),

    selling_price NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_id)
        REFERENCES pharmacy_inventory(inventory_id)
);

CREATE TABLE stock_movements (
    stock_movement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_id UUID,

    movement_type VARCHAR(100),

    quantity NUMERIC(14,2),

    movement_reason TEXT,

    moved_by UUID,

    moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_id)
        REFERENCES pharmacy_inventory(inventory_id)
);

CREATE TABLE stock_adjustments (
    adjustment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_id UUID,

    adjustment_quantity NUMERIC(14,2),

    adjustment_reason TEXT,

    adjusted_by UUID,

    adjusted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_id)
        REFERENCES pharmacy_inventory(inventory_id)
);

CREATE TABLE stock_transfers (
    transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    from_store_id UUID,

    to_store_id UUID,

    drug_id UUID,

    quantity_transferred NUMERIC(14,2),

    transferred_by UUID,

    transferred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (from_store_id)
        REFERENCES pharmacy_stores(pharmacy_store_id),

    FOREIGN KEY (to_store_id)
        REFERENCES pharmacy_stores(pharmacy_store_id),

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE stock_expiry_tracking (
    expiry_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    batch_id UUID,

    expiry_alert_date DATE,

    alert_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (batch_id)
        REFERENCES pharmacy_stock_batches(batch_id)
);

CREATE TABLE stock_reorder_levels (
    reorder_level_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_id UUID,

    minimum_level NUMERIC(14,2),

    maximum_level NUMERIC(14,2),

    reorder_quantity NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_id)
        REFERENCES pharmacy_inventory(inventory_id)
);

-- =========================================================
-- PROCUREMENT
-- =========================================================

CREATE TABLE suppliers (
    supplier_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    supplier_name VARCHAR(255),

    contact_person VARCHAR(255),

    phone_number VARCHAR(50),

    email VARCHAR(255),

    address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_orders (
    purchase_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_order_number VARCHAR(100) UNIQUE NOT NULL,

    supplier_id UUID,

    order_date TIMESTAMP,

    expected_delivery_date DATE,

    order_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
);

CREATE TABLE purchase_order_items (
    purchase_order_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_order_id UUID,

    drug_id UUID,

    quantity_ordered NUMERIC(14,2),

    unit_price NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id),

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE goods_receipts (
    goods_receipt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_order_id UUID,

    received_by UUID,

    received_date TIMESTAMP,

    receipt_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id)
);

CREATE TABLE vendor_payments (
    vendor_payment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    supplier_id UUID,

    payment_amount NUMERIC(14,2),

    payment_date TIMESTAMP,

    payment_method VARCHAR(100),

    payment_reference VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
);

-- =========================================================
-- CONTROLLED SUBSTANCES
-- =========================================================

CREATE TABLE controlled_substances (
    controlled_substance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_id UUID,

    regulation_category VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE narcotic_registers (
    narcotic_register_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    drug_id UUID,

    transaction_type VARCHAR(100),

    quantity NUMERIC(14,2),

    transaction_date TIMESTAMP,

    performed_by UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
);

CREATE TABLE cold_chain_monitoring (
    cold_chain_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pharmacy_store_id UUID,

    temperature_value NUMERIC(5,2),

    monitored_at TIMESTAMP,

    alert_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pharmacy_store_id)
        REFERENCES pharmacy_stores(pharmacy_store_id)
);

-- =========================================================
-- BILLING
-- =========================================================

CREATE TABLE pharmacy_billing (
    pharmacy_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    prescription_id UUID,

    invoice_id UUID,

    billing_amount NUMERIC(14,2),

    billing_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_id)
        REFERENCES prescriptions(prescription_id)
);

CREATE TABLE insurance_pharmacy_claims (
    insurance_pharmacy_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pharmacy_billing_id UUID,

    insurance_provider VARCHAR(255),

    claim_amount NUMERIC(14,2),

    approved_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pharmacy_billing_id)
        REFERENCES pharmacy_billing(pharmacy_billing_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE pharmacy_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pharmacy_change_history (
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
-- END OF PHARMACY MANAGEMENT SYSTEM SCHEMA
-- =========================================================