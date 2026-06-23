-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 16: INVENTORY & PROCUREMENT MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS inventory;
SET search_path TO inventory, public;

-- =========================================================
-- INVENTORY MASTER TABLES
-- =========================================================

CREATE TABLE inventory_categories (
    inventory_category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_code VARCHAR(100) UNIQUE NOT NULL,

    category_name VARCHAR(255) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_subcategories (
    inventory_subcategory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_category_id UUID,

    subcategory_code VARCHAR(100) UNIQUE NOT NULL,

    subcategory_name VARCHAR(255),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_category_id)
        REFERENCES inventory_categories(inventory_category_id)
);

CREATE TABLE inventory_units_of_measure (
    unit_of_measure_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    unit_code VARCHAR(50) UNIQUE NOT NULL,

    unit_name VARCHAR(100),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_items (
    inventory_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_subcategory_id UUID,

    item_code VARCHAR(100) UNIQUE NOT NULL,

    item_name VARCHAR(255),

    item_description TEXT,

    item_type VARCHAR(100),

    unit_of_measure_id UUID,

    manufacturer_name VARCHAR(255),

    brand_name VARCHAR(255),

    reorder_level INT,

    maximum_stock_level INT,

    minimum_stock_level INT,

    is_expiry_tracking_required BOOLEAN DEFAULT FALSE,

    is_batch_tracking_required BOOLEAN DEFAULT FALSE,

    is_controlled_substance BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_subcategory_id)
        REFERENCES inventory_subcategories(inventory_subcategory_id),

    FOREIGN KEY (unit_of_measure_id)
        REFERENCES inventory_units_of_measure(unit_of_measure_id)
);

CREATE TABLE inventory_item_variants (
    inventory_item_variant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    variant_name VARCHAR(255),

    variant_code VARCHAR(100),

    size_specification VARCHAR(100),

    color_specification VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE inventory_item_barcodes (
    inventory_item_barcode_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    barcode_value VARCHAR(255) UNIQUE NOT NULL,

    barcode_type VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

-- =========================================================
-- WAREHOUSE MANAGEMENT
-- =========================================================

CREATE TABLE warehouses (
    warehouse_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    warehouse_code VARCHAR(100) UNIQUE NOT NULL,

    warehouse_name VARCHAR(255),

    warehouse_type VARCHAR(100),

    warehouse_address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE warehouse_locations (
    warehouse_location_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    warehouse_id UUID,

    location_code VARCHAR(100),

    location_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
);

CREATE TABLE storage_racks (
    storage_rack_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    warehouse_location_id UUID,

    rack_code VARCHAR(100),

    rack_description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (warehouse_location_id)
        REFERENCES warehouse_locations(warehouse_location_id)
);

CREATE TABLE inventory_stock (
    inventory_stock_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    warehouse_id UUID,

    current_stock_quantity NUMERIC(14,2),

    reserved_stock_quantity NUMERIC(14,2),

    available_stock_quantity NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id),

    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
);

CREATE TABLE inventory_stock_batches (
    inventory_stock_batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_stock_id UUID,

    batch_number VARCHAR(255),

    lot_number VARCHAR(255),

    manufacture_date DATE,

    expiry_date DATE,

    batch_quantity NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_stock_id)
        REFERENCES inventory_stock(inventory_stock_id)
);

CREATE TABLE inventory_stock_movements (
    inventory_stock_movement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_stock_id UUID,

    movement_type VARCHAR(100),

    movement_quantity NUMERIC(14,2),

    source_location VARCHAR(255),

    destination_location VARCHAR(255),

    moved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_stock_id)
        REFERENCES inventory_stock(inventory_stock_id)
);

-- =========================================================
-- INVENTORY TRANSACTIONS
-- =========================================================

CREATE TABLE inventory_transactions (
    inventory_transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    transaction_type VARCHAR(100),

    transaction_quantity NUMERIC(14,2),

    transaction_reference VARCHAR(255),

    transaction_date TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE stock_adjustments (
    stock_adjustment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    adjustment_reason TEXT,

    adjustment_quantity NUMERIC(14,2),

    adjusted_by UUID,

    adjusted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE stock_transfers (
    stock_transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    source_warehouse_id UUID,

    destination_warehouse_id UUID,

    transfer_quantity NUMERIC(14,2),

    transfer_status VARCHAR(100),

    transferred_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id),

    FOREIGN KEY (source_warehouse_id)
        REFERENCES warehouses(warehouse_id),

    FOREIGN KEY (destination_warehouse_id)
        REFERENCES warehouses(warehouse_id)
);

CREATE TABLE stock_returns (
    stock_return_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    return_reason TEXT,

    return_quantity NUMERIC(14,2),

    returned_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE stock_damages (
    stock_damage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    damage_description TEXT,

    damaged_quantity NUMERIC(14,2),

    damaged_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE stock_expiry_tracking (
    stock_expiry_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_stock_batch_id UUID,

    expiry_alert_status VARCHAR(100),

    expiry_alert_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_stock_batch_id)
        REFERENCES inventory_stock_batches(inventory_stock_batch_id)
);

-- =========================================================
-- VENDOR MANAGEMENT
-- =========================================================

CREATE TABLE vendors (
    vendor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    vendor_code VARCHAR(100) UNIQUE NOT NULL,

    vendor_name VARCHAR(255),

    vendor_type VARCHAR(100),

    contact_email VARCHAR(255),

    contact_phone VARCHAR(50),

    vendor_address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vendor_contacts (
    vendor_contact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    vendor_id UUID,

    contact_name VARCHAR(255),

    contact_designation VARCHAR(100),

    contact_phone VARCHAR(50),

    contact_email VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
);

CREATE TABLE vendor_contracts (
    vendor_contract_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    vendor_id UUID,

    contract_number VARCHAR(100),

    contract_start_date DATE,

    contract_end_date DATE,

    contract_terms TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
);

CREATE TABLE vendor_performance_metrics (
    vendor_performance_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    vendor_id UUID,

    metric_name VARCHAR(255),

    metric_value NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
);

CREATE TABLE approved_vendor_lists (
    approved_vendor_list_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    vendor_id UUID,

    approval_status VARCHAR(100),

    approved_by UUID,

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
);

-- =========================================================
-- PROCUREMENT MANAGEMENT
-- =========================================================

CREATE TABLE purchase_requests (
    purchase_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    requested_by UUID,

    request_date TIMESTAMP,

    request_status VARCHAR(100),

    request_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_requisitions (
    purchase_requisition_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_request_id UUID,

    requisition_number VARCHAR(100),

    requisition_status VARCHAR(100),

    approved_by UUID,

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_request_id)
        REFERENCES purchase_requests(purchase_request_id)
);

CREATE TABLE purchase_orders (
    purchase_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    vendor_id UUID,

    purchase_requisition_id UUID,

    purchase_order_number VARCHAR(100),

    order_date DATE,

    expected_delivery_date DATE,

    order_status VARCHAR(100),

    total_order_amount NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id),

    FOREIGN KEY (purchase_requisition_id)
        REFERENCES purchase_requisitions(purchase_requisition_id)
);

CREATE TABLE purchase_order_items (
    purchase_order_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_order_id UUID,

    inventory_item_id UUID,

    ordered_quantity NUMERIC(14,2),

    unit_price NUMERIC(14,2),

    total_price NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id),

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE goods_receipts (
    goods_receipt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_order_id UUID,

    receipt_number VARCHAR(100),

    received_by UUID,

    received_date TIMESTAMP,

    receipt_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id)
);

CREATE TABLE goods_receipt_items (
    goods_receipt_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    goods_receipt_id UUID,

    inventory_item_id UUID,

    received_quantity NUMERIC(14,2),

    accepted_quantity NUMERIC(14,2),

    rejected_quantity NUMERIC(14,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (goods_receipt_id)
        REFERENCES goods_receipts(goods_receipt_id),

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

-- =========================================================
-- PROCUREMENT FINANCIALS
-- =========================================================

CREATE TABLE invoice_matching (
    invoice_matching_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_order_id UUID,

    goods_receipt_id UUID,

    matching_status VARCHAR(100),

    matched_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id),

    FOREIGN KEY (goods_receipt_id)
        REFERENCES goods_receipts(goods_receipt_id)
);

CREATE TABLE procurement_invoices (
    procurement_invoice_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    vendor_id UUID,

    invoice_number VARCHAR(100),

    invoice_amount NUMERIC(14,2),

    invoice_date DATE,

    invoice_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
);

CREATE TABLE payment_tracking (
    payment_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    procurement_invoice_id UUID,

    payment_reference VARCHAR(255),

    payment_amount NUMERIC(14,2),

    payment_status VARCHAR(100),

    paid_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (procurement_invoice_id)
        REFERENCES procurement_invoices(procurement_invoice_id)
);

CREATE TABLE procurement_approvals (
    procurement_approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    purchase_order_id UUID,

    approval_level VARCHAR(100),

    approved_by UUID,

    approval_status VARCHAR(100),

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id)
);

CREATE TABLE procurement_workflows (
    procurement_workflow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    workflow_name VARCHAR(255),

    workflow_status VARCHAR(100),

    workflow_steps TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- INVENTORY CONSUMPTION & REORDER
-- =========================================================

CREATE TABLE inventory_consumption (
    inventory_consumption_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    consumed_quantity NUMERIC(14,2),

    consumed_by_department VARCHAR(255),

    consumed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE department_inventory_usage (
    department_inventory_usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_name VARCHAR(255),

    inventory_item_id UUID,

    usage_quantity NUMERIC(14,2),

    usage_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE automatic_reorder_rules (
    automatic_reorder_rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    reorder_threshold NUMERIC(14,2),

    reorder_quantity NUMERIC(14,2),

    auto_reorder_enabled BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE reorder_notifications (
    reorder_notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    notification_message TEXT,

    notification_status VARCHAR(100),

    notified_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE par_level_management (
    par_level_management_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    par_level_quantity NUMERIC(14,2),

    updated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

-- =========================================================
-- ASSET MANAGEMENT
-- =========================================================

CREATE TABLE medical_device_assets (
    medical_device_asset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    asset_code VARCHAR(100),

    asset_name VARCHAR(255),

    asset_category VARCHAR(255),

    serial_number VARCHAR(255),

    purchase_date DATE,

    asset_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE biomedical_assets (
    biomedical_asset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    medical_device_asset_id UUID,

    biomedical_category VARCHAR(255),

    calibration_required BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (medical_device_asset_id)
        REFERENCES medical_device_assets(medical_device_asset_id)
);

CREATE TABLE asset_maintenance (
    asset_maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    medical_device_asset_id UUID,

    maintenance_type VARCHAR(100),

    maintenance_notes TEXT,

    maintenance_date TIMESTAMP,

    next_maintenance_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (medical_device_asset_id)
        REFERENCES medical_device_assets(medical_device_asset_id)
);

CREATE TABLE calibration_tracking (
    calibration_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    biomedical_asset_id UUID,

    calibration_status VARCHAR(100),

    calibrated_at TIMESTAMP,

    next_calibration_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (biomedical_asset_id)
        REFERENCES biomedical_assets(biomedical_asset_id)
);

CREATE TABLE depreciation_tracking (
    depreciation_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    medical_device_asset_id UUID,

    depreciation_method VARCHAR(100),

    depreciation_value NUMERIC(14,2),

    depreciation_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (medical_device_asset_id)
        REFERENCES medical_device_assets(medical_device_asset_id)
);

-- =========================================================
-- SPECIAL COMPLIANCE TRACKING
-- =========================================================

CREATE TABLE cold_chain_monitoring (
    cold_chain_monitoring_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    warehouse_id UUID,

    temperature_range VARCHAR(100),

    monitoring_status VARCHAR(100),

    monitored_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
);

CREATE TABLE temperature_logs (
    temperature_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    cold_chain_monitoring_id UUID,

    recorded_temperature NUMERIC(5,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cold_chain_monitoring_id)
        REFERENCES cold_chain_monitoring(cold_chain_monitoring_id)
);

CREATE TABLE controlled_substance_inventory (
    controlled_substance_inventory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    controlled_quantity NUMERIC(14,2),

    compliance_status VARCHAR(100),

    audited_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

CREATE TABLE hazardous_material_tracking (
    hazardous_material_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inventory_item_id UUID,

    hazard_classification VARCHAR(255),

    safety_notes TEXT,

    tracked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (inventory_item_id)
        REFERENCES inventory_items(inventory_item_id)
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE inventory_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_change_history (
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
-- END OF INVENTORY & PROCUREMENT MANAGEMENT SYSTEM
-- =========================================================