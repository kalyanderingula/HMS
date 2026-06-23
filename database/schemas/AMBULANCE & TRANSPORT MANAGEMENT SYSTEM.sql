-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 18: AMBULANCE & TRANSPORT MANAGEMENT SYSTEM
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS ambulance;
SET search_path TO ambulance, public;

-- =========================================================
-- AMBULANCE MASTER TABLES
-- =========================================================

CREATE TABLE ambulance_types (
    ambulance_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_code VARCHAR(100) UNIQUE NOT NULL,

    type_name VARCHAR(255),

    emergency_level VARCHAR(100),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ambulances (
    ambulance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_type_id UUID,

    vehicle_number VARCHAR(100) UNIQUE NOT NULL,

    registration_number VARCHAR(100),

    chassis_number VARCHAR(255),

    manufacturer_name VARCHAR(255),

    model_name VARCHAR(255),

    manufacturing_year INT,

    current_status VARCHAR(100),

    gps_enabled BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_type_id)
        REFERENCES ambulance_types(ambulance_type_id)
);

CREATE TABLE ambulance_devices (
    ambulance_device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    device_name VARCHAR(255),

    device_serial_number VARCHAR(255),

    device_status VARCHAR(100),

    installed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE ambulance_equipments (
    ambulance_equipment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    equipment_name VARCHAR(255),

    equipment_quantity INT,

    equipment_status VARCHAR(100),

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE ambulance_maintenance (
    ambulance_maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    maintenance_type VARCHAR(100),

    maintenance_notes TEXT,

    maintenance_date DATE,

    next_maintenance_date DATE,

    maintenance_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE ambulance_fuel_logs (
    ambulance_fuel_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    fuel_quantity NUMERIC(10,2),

    fuel_cost NUMERIC(14,2),

    odometer_reading NUMERIC(14,2),

    fueled_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE ambulance_insurance (
    ambulance_insurance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    insurance_provider VARCHAR(255),

    policy_number VARCHAR(255),

    coverage_amount NUMERIC(14,2),

    policy_start_date DATE,

    policy_end_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE ambulance_permits (
    ambulance_permit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    permit_type VARCHAR(255),

    permit_number VARCHAR(255),

    issued_by VARCHAR(255),

    issue_date DATE,

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- AMBULANCE STAFF MANAGEMENT
-- =========================================================

CREATE TABLE ambulance_staff (
    ambulance_staff_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    employee_id UUID,

    staff_role VARCHAR(100),

    certification_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ambulance_driver_assignments (
    ambulance_driver_assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    ambulance_staff_id UUID,

    assignment_start_date DATE,

    assignment_end_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id),

    FOREIGN KEY (ambulance_staff_id)
        REFERENCES ambulance_staff(ambulance_staff_id)
);

CREATE TABLE paramedic_assignments (
    paramedic_assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    ambulance_staff_id UUID,

    assignment_start_date DATE,

    assignment_end_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id),

    FOREIGN KEY (ambulance_staff_id)
        REFERENCES ambulance_staff(ambulance_staff_id)
);

CREATE TABLE ambulance_shift_schedules (
    ambulance_shift_schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    shift_name VARCHAR(255),

    shift_start_time TIME,

    shift_end_time TIME,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transport_crews (
    transport_crew_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    crew_lead_id UUID,

    crew_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- DISPATCH MANAGEMENT
-- =========================================================

CREATE TABLE emergency_dispatch_requests (
    emergency_dispatch_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    request_source VARCHAR(255),

    emergency_type VARCHAR(255),

    pickup_location TEXT,

    destination_location TEXT,

    dispatch_status VARCHAR(100),

    requested_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dispatch_priorities (
    dispatch_priority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    priority_code VARCHAR(100),

    priority_name VARCHAR(255),

    response_time_target_minutes INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dispatch_statuses (
    dispatch_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_code VARCHAR(100),

    status_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dispatch_assignments (
    dispatch_assignment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emergency_dispatch_request_id UUID,

    ambulance_id UUID,

    dispatch_priority_id UUID,

    assigned_at TIMESTAMP,

    assignment_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_dispatch_request_id)
        REFERENCES emergency_dispatch_requests(emergency_dispatch_request_id),

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id),

    FOREIGN KEY (dispatch_priority_id)
        REFERENCES dispatch_priorities(dispatch_priority_id)
);

CREATE TABLE dispatch_tracking (
    dispatch_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    dispatch_assignment_id UUID,

    tracking_status VARCHAR(100),

    tracking_notes TEXT,

    tracked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dispatch_assignment_id)
        REFERENCES dispatch_assignments(dispatch_assignment_id)
);

CREATE TABLE gps_tracking_logs (
    gps_tracking_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    latitude NUMERIC(10,7),

    longitude NUMERIC(10,7),

    speed NUMERIC(10,2),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE live_location_tracking (
    live_location_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    current_latitude NUMERIC(10,7),

    current_longitude NUMERIC(10,7),

    last_updated TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- PATIENT TRANSPORT MANAGEMENT
-- =========================================================

CREATE TABLE patient_transport_requests (
    patient_transport_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    transport_type VARCHAR(255),

    pickup_location TEXT,

    destination_location TEXT,

    transport_status VARCHAR(100),

    requested_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE interfacility_transfers (
    interfacility_transfer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_transport_request_id UUID,

    source_facility VARCHAR(255),

    destination_facility VARCHAR(255),

    transfer_reason TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_transport_request_id)
        REFERENCES patient_transport_requests(patient_transport_request_id)
);

CREATE TABLE discharge_transport_requests (
    discharge_transport_request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    patient_id UUID,

    discharge_location TEXT,

    transport_status VARCHAR(100),

    requested_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transport_routes (
    transport_route_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    route_name VARCHAR(255),

    source_location TEXT,

    destination_location TEXT,

    estimated_distance_km NUMERIC(10,2),

    estimated_travel_time_minutes INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transport_checklists (
    transport_checklist_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    checklist_name VARCHAR(255),

    checklist_status VARCHAR(100),

    checked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- EMERGENCY RESPONSE ANALYTICS
-- =========================================================

CREATE TABLE emergency_response_logs (
    emergency_response_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    dispatch_assignment_id UUID,

    response_start_time TIMESTAMP,

    response_end_time TIMESTAMP,

    total_response_minutes INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dispatch_assignment_id)
        REFERENCES dispatch_assignments(dispatch_assignment_id)
);

CREATE TABLE response_time_metrics (
    response_time_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    dispatch_assignment_id UUID,

    target_response_minutes INT,

    actual_response_minutes INT,

    metric_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dispatch_assignment_id)
        REFERENCES dispatch_assignments(dispatch_assignment_id)
);

CREATE TABLE route_optimization_logs (
    route_optimization_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    optimized_route_details TEXT,

    optimization_score NUMERIC(10,2),

    optimized_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE traffic_delay_logs (
    traffic_delay_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    delay_reason TEXT,

    delay_duration_minutes INT,

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- TRIP MANAGEMENT & BILLING
-- =========================================================

CREATE TABLE ambulance_trip_records (
    ambulance_trip_record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    trip_start_time TIMESTAMP,

    trip_end_time TIMESTAMP,

    trip_distance_km NUMERIC(10,2),

    trip_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE trip_patients (
    trip_patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_trip_record_id UUID,

    patient_id UUID,

    patient_condition VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_trip_record_id)
        REFERENCES ambulance_trip_records(ambulance_trip_record_id)
);

CREATE TABLE trip_billing (
    trip_billing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_trip_record_id UUID,

    billing_amount NUMERIC(14,2),

    billing_status VARCHAR(100),

    billed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_trip_record_id)
        REFERENCES ambulance_trip_records(ambulance_trip_record_id)
);

CREATE TABLE insurance_transport_claims (
    insurance_transport_claim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    trip_billing_id UUID,

    insurance_provider VARCHAR(255),

    claim_amount NUMERIC(14,2),

    claim_status VARCHAR(100),

    submitted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (trip_billing_id)
        REFERENCES trip_billing(trip_billing_id)
);

-- =========================================================
-- AMBULANCE INVENTORY
-- =========================================================

CREATE TABLE ambulance_inventory (
    ambulance_inventory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    inventory_item_name VARCHAR(255),

    quantity_available INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE onboard_medications (
    onboard_medication_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    medication_name VARCHAR(255),

    medication_quantity INT,

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE onboard_consumables (
    onboard_consumable_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    consumable_name VARCHAR(255),

    quantity_available INT,

    expiry_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE onboard_equipment_tracking (
    onboard_equipment_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    equipment_name VARCHAR(255),

    equipment_status VARCHAR(100),

    last_checked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- INCIDENT & SAFETY MANAGEMENT
-- =========================================================

CREATE TABLE ambulance_incidents (
    ambulance_incident_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    incident_type VARCHAR(255),

    incident_description TEXT,

    incident_date TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE accident_reports (
    accident_report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_incident_id UUID,

    accident_location TEXT,

    accident_severity VARCHAR(100),

    reported_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_incident_id)
        REFERENCES ambulance_incidents(ambulance_incident_id)
);

CREATE TABLE incident_investigations (
    incident_investigation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_incident_id UUID,

    investigator_name VARCHAR(255),

    investigation_findings TEXT,

    investigation_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_incident_id)
        REFERENCES ambulance_incidents(ambulance_incident_id)
);

CREATE TABLE safety_compliance_tracking (
    safety_compliance_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    compliance_type VARCHAR(255),

    compliance_status VARCHAR(100),

    compliance_due_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- TELEMATICS & MAINTENANCE
-- =========================================================

CREATE TABLE vehicle_telematics (
    vehicle_telematics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    engine_health_status VARCHAR(100),

    battery_status VARCHAR(100),

    tire_pressure_status VARCHAR(100),

    recorded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE fuel_efficiency_metrics (
    fuel_efficiency_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    fuel_efficiency_kmpl NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE preventive_maintenance (
    preventive_maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    maintenance_activity VARCHAR(255),

    scheduled_date DATE,

    maintenance_status VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE breakdown_assistance_logs (
    breakdown_assistance_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    breakdown_reason TEXT,

    assistance_provided TEXT,

    resolved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

-- =========================================================
-- DOCUMENTS & COMPLIANCE
-- =========================================================

CREATE TABLE ambulance_documents (
    ambulance_document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    document_name VARCHAR(255),

    document_type VARCHAR(100),

    document_path TEXT,

    uploaded_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE regulatory_compliance_tracking (
    regulatory_compliance_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    compliance_category VARCHAR(255),

    compliance_status VARCHAR(100),

    due_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE emergency_protocols (
    emergency_protocol_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    protocol_name VARCHAR(255),

    protocol_description TEXT,

    protocol_version VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- ANALYTICS & KPI TRACKING
-- =========================================================

CREATE TABLE ambulance_analytics (
    ambulance_analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    analytics_name VARCHAR(255),

    analytics_value NUMERIC(14,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fleet_utilization_metrics (
    fleet_utilization_metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    ambulance_id UUID,

    utilization_percentage NUMERIC(10,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (ambulance_id)
        REFERENCES ambulances(ambulance_id)
);

CREATE TABLE emergency_heatmaps (
    emergency_heatmap_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    location_name VARCHAR(255),

    emergency_case_count INT,

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transport_kpi_tracking (
    transport_kpi_tracking_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    kpi_name VARCHAR(255),

    kpi_value NUMERIC(14,2),

    reporting_period VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- AUDIT & CHANGE HISTORY
-- =========================================================

CREATE TABLE ambulance_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    entity_name VARCHAR(255),

    entity_id UUID,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ambulance_change_history (
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
-- END OF AMBULANCE & TRANSPORT MANAGEMENT SYSTEM
-- =========================================================