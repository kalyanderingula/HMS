
-- ==========================================================
-- CATEGORY 23 : MULTI-HOSPITAL / MULTI-TENANT MANAGEMENT
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS multi_hospital;
SET search_path TO multi_hospital, public;

-- HEALTHCARE GROUPS
CREATE TABLE healthcare_groups (
    healthcare_group_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_name VARCHAR(255) NOT NULL,
    group_code VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE healthcare_group_settings (
    setting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    healthcare_group_id UUID REFERENCES healthcare_groups(healthcare_group_id),
    setting_name VARCHAR(255),
    setting_value TEXT
);

CREATE TABLE healthcare_group_brands (
    brand_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    healthcare_group_id UUID REFERENCES healthcare_groups(healthcare_group_id),
    brand_name VARCHAR(255)
);

-- HOSPITALS
CREATE TABLE hospital_types (
    hospital_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_name VARCHAR(255)
);

CREATE TABLE hospitals (
    hospital_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    healthcare_group_id UUID REFERENCES healthcare_groups(healthcare_group_id),
    hospital_type_id UUID REFERENCES hospital_types(hospital_type_id),
    hospital_name VARCHAR(255),
    hospital_code VARCHAR(100)
);

CREATE TABLE hospital_classifications (
    classification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(hospital_id),
    classification_name VARCHAR(255)
);

CREATE TABLE hospital_accreditations (
    accreditation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(hospital_id),
    accreditation_name VARCHAR(255)
);

CREATE TABLE hospital_licenses (
    license_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(hospital_id),
    license_number VARCHAR(255)
);

-- BRANCHES
CREATE TABLE hospital_branches (
    branch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(hospital_id),
    branch_name VARCHAR(255)
);

CREATE TABLE branch_settings (
    setting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID REFERENCES hospital_branches(branch_id),
    setting_name VARCHAR(255)
);

CREATE TABLE branch_contacts (
    contact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID REFERENCES hospital_branches(branch_id),
    contact_name VARCHAR(255)
);

CREATE TABLE branch_addresses (
    address_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID REFERENCES hospital_branches(branch_id),
    address_line TEXT
);

-- FACILITIES
CREATE TABLE facility_types (
    facility_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_type_name VARCHAR(255)
);

CREATE TABLE facilities (
    facility_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID REFERENCES hospital_branches(branch_id),
    facility_type_id UUID REFERENCES facility_types(facility_type_id),
    facility_name VARCHAR(255)
);

CREATE TABLE facility_locations (
    location_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES facilities(facility_id),
    location_name VARCHAR(255)
);

CREATE TABLE facility_services (
    service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID REFERENCES facilities(facility_id),
    service_name VARCHAR(255)
);

-- TENANTS
CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(hospital_id),
    tenant_name VARCHAR(255)
);

CREATE TABLE tenant_settings (
    tenant_setting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    setting_name VARCHAR(255)
);

CREATE TABLE tenant_configurations (
    configuration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    configuration_name VARCHAR(255)
);

CREATE TABLE tenant_domains (
    domain_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    domain_name VARCHAR(255)
);

CREATE TABLE tenant_subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    subscription_plan VARCHAR(255)
);

-- PATIENT NETWORK
CREATE TABLE patient_global_registry (
    global_patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    master_patient_number VARCHAR(255)
);

CREATE TABLE cross_hospital_patient_mapping (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    global_patient_id UUID REFERENCES patient_global_registry(global_patient_id),
    hospital_id UUID REFERENCES hospitals(hospital_id)
);

CREATE TABLE patient_merge_requests (
    merge_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    global_patient_id UUID REFERENCES patient_global_registry(global_patient_id)
);

-- DOCTOR NETWORK
CREATE TABLE doctor_network_registry (
    network_doctor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_name VARCHAR(255)
);

CREATE TABLE doctor_hospital_affiliations (
    affiliation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    network_doctor_id UUID REFERENCES doctor_network_registry(network_doctor_id),
    hospital_id UUID REFERENCES hospitals(hospital_id)
);

CREATE TABLE doctor_privileges (
    privilege_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    affiliation_id UUID REFERENCES doctor_hospital_affiliations(affiliation_id),
    privilege_name VARCHAR(255)
);

-- INVENTORY NETWORK
CREATE TABLE centralized_inventory (
    centralized_inventory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_name VARCHAR(255)
);

CREATE TABLE inventory_transfers (
    transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_hospital_id UUID REFERENCES hospitals(hospital_id),
    destination_hospital_id UUID REFERENCES hospitals(hospital_id)
);

CREATE TABLE inventory_transfer_items (
    transfer_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transfer_id UUID REFERENCES inventory_transfers(transfer_id),
    item_name VARCHAR(255)
);

-- PROCUREMENT NETWORK
CREATE TABLE centralized_procurement (
    procurement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procurement_name VARCHAR(255)
);

CREATE TABLE vendor_network_registry (
    vendor_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_name VARCHAR(255)
);

-- SHARED SERVICES
CREATE TABLE shared_services (
    shared_service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(255)
);

CREATE TABLE shared_laboratories (
    laboratory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    laboratory_name VARCHAR(255)
);

CREATE TABLE shared_radiology_centers (
    radiology_center_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    center_name VARCHAR(255)
);

CREATE TABLE shared_pharmacies (
    pharmacy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pharmacy_name VARCHAR(255)
);

-- REFERRALS & TRANSFERS
CREATE TABLE inter_hospital_referrals (
    referral_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID
);

CREATE TABLE patient_transfers (
    transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID
);

CREATE TABLE transfer_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transfer_id UUID REFERENCES patient_transfers(transfer_id)
);

-- FINANCIALS
CREATE TABLE consolidated_financials (
    consolidated_financial_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    healthcare_group_id UUID REFERENCES healthcare_groups(healthcare_group_id)
);

CREATE TABLE group_budgets (
    budget_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    healthcare_group_id UUID REFERENCES healthcare_groups(healthcare_group_id)
);

CREATE TABLE branch_financials (
    branch_financial_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID REFERENCES hospital_branches(branch_id)
);

-- ANALYTICS
CREATE TABLE multi_hospital_dashboards (
    dashboard_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_name VARCHAR(255)
);

CREATE TABLE group_kpi_tracking (
    kpi_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    healthcare_group_id UUID REFERENCES healthcare_groups(healthcare_group_id)
);

CREATE TABLE benchmark_comparisons (
    benchmark_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(hospital_id)
);

-- AUDIT
CREATE TABLE multi_tenant_audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE multi_tenant_change_history (
    change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
