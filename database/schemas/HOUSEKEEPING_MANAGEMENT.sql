-- ==========================================
-- HOUSEKEEPING MANAGEMENT
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS housekeeping;

CREATE TABLE housekeeping.housekeeping_task_types (
    task_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO housekeeping.housekeeping_task_types (type_name) VALUES
('Room Cleaning'), ('Bed Turnover'), ('Floor Mopping'), ('Terminal Cleaning');

CREATE TABLE housekeeping.housekeeping_staff (
    staff_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    employee_id UUID,
    staff_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    shift VARCHAR(20),
    zone_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE housekeeping.housekeeping_zones (
    zone_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    zone_name VARCHAR(255) NOT NULL,
    building_id UUID,
    floor_id UUID,
    department_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE housekeeping.housekeeping_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    zone_id UUID REFERENCES housekeeping.housekeeping_zones(zone_id),
    task_type_id UUID REFERENCES housekeeping.housekeeping_task_types(task_type_id),
    assigned_to UUID REFERENCES housekeeping.housekeeping_staff(staff_id),
    priority VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(30) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE housekeeping.housekeeping_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    zone_id UUID REFERENCES housekeeping.housekeeping_zones(zone_id),
    task_type_id UUID REFERENCES housekeeping.housekeeping_task_types(task_type_id),
    frequency VARCHAR(50) NOT NULL,
    scheduled_time TIME,
    assigned_to UUID REFERENCES housekeeping.housekeeping_staff(staff_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE housekeeping.housekeeping_inspections (
    inspection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    zone_id UUID REFERENCES housekeeping.housekeeping_zones(zone_id),
    inspected_by UUID,
    inspection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cleanliness_score INT,
    status VARCHAR(30) NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE housekeeping.linen_management (
    linen_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    ward_id UUID,
    linen_type VARCHAR(100) NOT NULL,
    quantity_issued INT NOT NULL,
    quantity_returned INT DEFAULT 0,
    issue_date DATE NOT NULL,
    return_date DATE,
    status VARCHAR(30) DEFAULT 'issued',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_hk_tasks_zone ON housekeeping.housekeeping_tasks(zone_id);
CREATE INDEX idx_hk_tasks_type ON housekeeping.housekeeping_tasks(task_type_id);
CREATE INDEX idx_hk_tasks_assigned ON housekeeping.housekeeping_tasks(assigned_to);
CREATE INDEX idx_hk_tasks_status ON housekeeping.housekeeping_tasks(status);
CREATE INDEX idx_hk_schedules_zone ON housekeeping.housekeeping_schedules(zone_id);
CREATE INDEX idx_hk_inspections_zone ON housekeeping.housekeeping_inspections(zone_id);
CREATE INDEX idx_hk_inspections_date ON housekeeping.housekeeping_inspections(inspection_date);
CREATE INDEX idx_linen_ward ON housekeeping.linen_management(ward_id);
CREATE INDEX idx_linen_issue_date ON housekeeping.linen_management(issue_date);
