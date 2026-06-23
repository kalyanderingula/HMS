-- =========================================================
-- ENTERPRISE HOSPITAL MANAGEMENT SYSTEM (HMS)
-- CATEGORY 3: DEPARTMENT MANAGEMENT
-- PostgreSQL Compatible
-- =========================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS department;
SET search_path TO department, public;

-- =========================================================
-- MASTER TABLES
-- =========================================================

CREATE TABLE department_types (
    department_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Clinical
-- Non-Clinical
-- Administrative


CREATE TABLE department_categories (
    category_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    category_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Cardiology
-- Neurology
-- Finance
-- HR


CREATE TABLE department_statuses (
    status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    status_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Active
-- Inactive
-- Under Maintenance


CREATE TABLE service_types (
    service_type_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    service_type_name VARCHAR(255) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example:
-- Consultation
-- Surgery
-- Emergency
-- Diagnostic


CREATE TABLE workflow_statuses (
    workflow_status_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    workflow_status_name VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- MAIN DEPARTMENTS TABLE
-- =========================================================

CREATE TABLE departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tenant_id UUID,

    department_code VARCHAR(50) UNIQUE NOT NULL,

    department_name VARCHAR(255) UNIQUE NOT NULL,

    department_type_id UUID NOT NULL,

    category_id UUID,

    status_id UUID,

    description TEXT,

    email VARCHAR(255),
    phone VARCHAR(20),

    established_date DATE,

    floor_number VARCHAR(50),
    building_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    created_by UUID,
    updated_by UUID,

    deleted_at TIMESTAMP NULL,

    FOREIGN KEY (department_type_id)
        REFERENCES department_types(department_type_id),

    FOREIGN KEY (category_id)
        REFERENCES department_categories(category_id),

    FOREIGN KEY (status_id)
        REFERENCES department_statuses(status_id)
);

-- =========================================================
-- DEPARTMENT UNITS
-- =========================================================

CREATE TABLE department_units (
    unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    unit_name VARCHAR(255) NOT NULL,
    unit_code VARCHAR(100),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- Example:
-- ICU Unit
-- Cath Lab
-- Trauma Unit


-- =========================================================
-- DEPARTMENT LOCATIONS
-- =========================================================

CREATE TABLE department_locations (
    location_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    branch_name VARCHAR(255),

    building_name VARCHAR(255),

    floor_number VARCHAR(50),

    room_reference VARCHAR(100),

    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),

    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),

    postal_code VARCHAR(20),

    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DEPARTMENT HEADS
-- =========================================================

CREATE TABLE department_heads (
    department_head_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    doctor_id UUID NOT NULL,

    assigned_from DATE,
    assigned_to DATE,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- doctor_id should later reference doctors(doctor_id)


-- =========================================================
-- DEPARTMENT STAFF
-- =========================================================

CREATE TABLE department_staff (
    department_staff_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    employee_id UUID NOT NULL,

    role_name VARCHAR(100),

    assigned_from DATE,
    assigned_to DATE,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- employee_id should later reference employees(employee_id)


-- =========================================================
-- DEPARTMENT SERVICES
-- =========================================================

CREATE TABLE department_services (
    service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    service_type_id UUID,

    service_name VARCHAR(255) NOT NULL,

    service_code VARCHAR(100),

    description TEXT,

    service_cost NUMERIC(12,2),

    duration_minutes INT,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE,

    FOREIGN KEY (service_type_id)
        REFERENCES service_types(service_type_id)
);

-- =========================================================
-- DEPARTMENT OPERATING HOURS
-- =========================================================

CREATE TABLE department_operating_hours (
    operating_hour_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    day_of_week VARCHAR(20),

    open_time TIME,
    close_time TIME,

    is_24_hours BOOLEAN DEFAULT FALSE,

    emergency_available BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DEPARTMENT ROOMS
-- =========================================================

CREATE TABLE department_rooms (
    department_room_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    room_id UUID NOT NULL,

    room_purpose VARCHAR(255),

    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- room_id should later reference rooms(room_id)


-- =========================================================
-- DEPARTMENT EQUIPMENTS
-- =========================================================

CREATE TABLE department_equipments (
    department_equipment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    equipment_id UUID NOT NULL,

    assigned_date DATE,

    quantity INT DEFAULT 1,

    status VARCHAR(50),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- equipment_id should later reference equipments(equipment_id)


-- =========================================================
-- DEPARTMENT COST CENTERS
-- =========================================================

CREATE TABLE department_cost_centers (
    cost_center_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    cost_center_code VARCHAR(100) UNIQUE NOT NULL,

    budget_amount NUMERIC(14,2),

    fiscal_year VARCHAR(20),

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DEPARTMENT HIERARCHY
-- =========================================================

CREATE TABLE department_hierarchy (
    hierarchy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    parent_department_id UUID NOT NULL,

    child_department_id UUID NOT NULL,

    hierarchy_level INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE,

    FOREIGN KEY (child_department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- Example:
-- Hospital
--   ├── Clinical
--   │      ├── Cardiology
--   │      └── ICU
--   └── Non-Clinical


-- =========================================================
-- DEPARTMENT WORKFLOWS
-- =========================================================

CREATE TABLE department_workflows (
    workflow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    workflow_name VARCHAR(255),

    workflow_status_id UUID,

    workflow_definition JSONB,

    version_number INT DEFAULT 1,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE,

    FOREIGN KEY (workflow_status_id)
        REFERENCES workflow_statuses(workflow_status_id)
);

-- workflow_definition stores:
-- workflow rules
-- approval chains
-- automation steps


-- =========================================================
-- DEPARTMENT DOCUMENTS
-- =========================================================

CREATE TABLE department_documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    document_name VARCHAR(255),

    document_type VARCHAR(100),

    file_path TEXT NOT NULL,

    mime_type VARCHAR(100),

    file_size BIGINT,

    uploaded_by UUID,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DEPARTMENT POLICIES
-- =========================================================

CREATE TABLE department_policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    policy_name VARCHAR(255),

    policy_code VARCHAR(100),

    policy_document_path TEXT,

    effective_from DATE,
    effective_to DATE,

    version_number INT DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DEPARTMENT PERFORMANCE METRICS
-- =========================================================

CREATE TABLE department_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    metric_name VARCHAR(255),

    metric_value NUMERIC(14,2),

    metric_period_start DATE,
    metric_period_end DATE,

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- Example Metrics:
-- Patient count
-- Revenue
-- Occupancy
-- Satisfaction score


-- =========================================================
-- DEPARTMENT AUDIT LOGS
-- =========================================================

CREATE TABLE department_audit_logs (
    audit_log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    action_type VARCHAR(100),

    action_description TEXT,

    performed_by UUID,

    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(100),

    device_info TEXT,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- =========================================================
-- DEPARTMENT CHANGE HISTORY
-- =========================================================

CREATE TABLE department_change_history (
    change_history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    department_id UUID NOT NULL,

    changed_field VARCHAR(255),

    old_value TEXT,
    new_value TEXT,

    changed_by UUID,

    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
        ON DELETE CASCADE
);

-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_departments_name
ON departments(department_name);

CREATE INDEX idx_departments_code
ON departments(department_code);

CREATE INDEX idx_department_units_department
ON department_units(department_id);

CREATE INDEX idx_department_locations_department
ON department_locations(department_id);

CREATE INDEX idx_department_heads_department
ON department_heads(department_id);

CREATE INDEX idx_department_staff_department
ON department_staff(department_id);

CREATE INDEX idx_department_services_department
ON department_services(department_id);

CREATE INDEX idx_department_operating_hours_department
ON department_operating_hours(department_id);

CREATE INDEX idx_department_rooms_department
ON department_rooms(department_id);

CREATE INDEX idx_department_equipments_department
ON department_equipments(department_id);

CREATE INDEX idx_department_cost_centers_department
ON department_cost_centers(department_id);

CREATE INDEX idx_department_hierarchy_parent
ON department_hierarchy(parent_department_id);

CREATE INDEX idx_department_hierarchy_child
ON department_hierarchy(child_department_id);

CREATE INDEX idx_department_workflows_department
ON department_workflows(department_id);

CREATE INDEX idx_department_documents_department
ON department_documents(department_id);

CREATE INDEX idx_department_policies_department
ON department_policies(department_id);

CREATE INDEX idx_department_performance_metrics_department
ON department_performance_metrics(department_id);

CREATE INDEX idx_department_audit_logs_department
ON department_audit_logs(department_id);

-- =========================================================
-- HIGH-LEVEL RELATIONSHIP FLOW
-- =========================================================

/*

departments
│
├── department_types
├── department_categories
├── department_units
├── department_locations
├── department_heads ─── doctors
├── department_staff ─── employees
├── department_services
├── department_operating_hours
├── department_rooms ─── rooms
├── department_equipments ─── equipments
├── department_cost_centers
├── department_hierarchy
├── department_workflows
├── department_documents
├── department_policies
├── department_performance_metrics
├── department_audit_logs
└── department_change_history

*/

-- =========================================================
-- END OF DEPARTMENT MANAGEMENT SCHEMA
-- =========================================================