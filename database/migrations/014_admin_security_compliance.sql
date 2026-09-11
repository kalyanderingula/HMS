-- =========================================================================
-- Migration 014: Milestone 4 — Administration, Security & Compliance Completion
-- Adds:
--  1. Security: Granular permissions catalog and role-permission mappings.
--  2. HR & Administration: Shift schedule catalog and employee duty rostering with double-booking prevention.
--  3. Document Security: Cryptographic checksum (SHA-256), MIME type, and file size tracking.
-- =========================================================================

BEGIN;

-- 1. GRANULAR PERMISSION CATALOG & ROLE PERMISSION MAPPING
CREATE TABLE IF NOT EXISTS security.permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_code VARCHAR(100) UNIQUE NOT NULL,
    permission_name VARCHAR(255) NOT NULL,
    module VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS security.role_permissions (
    role_permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES security.roles(role_id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES security.permissions(permission_id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON security.role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON security.role_permissions(permission_id);

-- Seed standard core permissions if not present
INSERT INTO security.permissions (permission_code, permission_name, module, description)
VALUES
    ('users.read', 'View Users', 'users', 'Ability to view employee and system users'),
    ('users.manage', 'Manage Users', 'users', 'Create and modify employee accounts and system users'),
    ('roles.manage', 'Manage Roles & Permissions', 'security', 'Configure roles and assign granular security permissions'),
    ('patients.read', 'View Patients', 'patients', 'Access patient search, registration, and demographics'),
    ('patients.manage', 'Register & Edit Patients', 'patients', 'Register new patients and modify demographic details'),
    ('emr.read', 'View Clinical Records', 'emr', 'Access EMR clinical summaries, vitals, and diagnostic notes'),
    ('emr.write', 'Record Clinical Consultations', 'emr', 'Create SOAP notes, prescribe medications, and add clinical entries'),
    ('appointments.manage', 'Manage Appointments', 'appointments', 'Schedule, reschedule, and check-in patient appointments'),
    ('rosters.manage', 'Manage Duty Rosters', 'human_resources', 'Create and schedule staff shift duty rosters'),
    ('pharmacy.dispense', 'Dispense Medications', 'pharmacy', 'Review prescriptions and dispense medications from stock'),
    ('laboratory.order', 'Order Lab Tests', 'laboratory', 'Order diagnostic laboratory investigations'),
    ('laboratory.process', 'Process Lab Tests', 'laboratory', 'Collect samples, enter parameter results, and verify lab findings'),
    ('radiology.view', 'View Radiology PACS', 'radiology', 'Inspect radiology worklist, study series, and PACS viewer'),
    ('radiology.report', 'Finalize Radiology Reports', 'radiology', 'Submit and sign off on diagnostic radiology imaging reports'),
    ('emergency.triage', 'Emergency Intake & Triage', 'emergency', 'Perform emergency arrivals, trauma intake, and disaster mode triage'),
    ('surgery.schedule', 'Schedule Surgery & OT', 'surgery', 'Book surgical cases, operating theatres, and surgeon teams'),
    ('blood_bank.manage', 'Blood Bank Operations', 'blood_bank', 'Manage donor collection, component separation, and cross-matching'),
    ('billing.invoices', 'Generate Invoices', 'billing', 'Create, itemize, and issue patient billing accounts and invoices'),
    ('billing.payments', 'Collect Payments & Refunds', 'billing', 'Process cash/online payments, webhook settlements, and refunds'),
    ('documents.verify', 'Verify Document Integrity', 'security', 'Execute cryptographic SHA-256 tamper verification on files')
ON CONFLICT (permission_code) DO NOTHING;

-- Seed default permissions to standard roles (super_admin, admin, doctor, etc.)
INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM security.roles r
CROSS JOIN security.permissions p
WHERE r.role_name = 'super_admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM security.roles r
CROSS JOIN security.permissions p
WHERE r.role_name = 'doctor'
  AND p.module IN ('patients', 'emr', 'appointments', 'laboratory', 'radiology', 'emergency')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 2. STAFF SHIFT DUTY ROSTERING & SCHEDULING
CREATE TABLE IF NOT EXISTS human_resources.shift_schedules (
    shift_schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shift_code VARCHAR(50) UNIQUE NOT NULL,
    shift_name VARCHAR(100) NOT NULL,
    shift_start_time TIME NOT NULL,
    shift_end_time TIME NOT NULL,
    is_night_shift BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS human_resources.employee_rosters (
    employee_roster_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES human_resources.employees(employee_id) ON DELETE CASCADE,
    shift_schedule_id UUID NOT NULL REFERENCES human_resources.shift_schedules(shift_schedule_id) ON DELETE RESTRICT,
    department_id UUID REFERENCES core.departments(department_id),
    roster_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_employee_roster_date UNIQUE (employee_id, roster_date)
);

CREATE INDEX IF NOT EXISTS idx_employee_rosters_date ON human_resources.employee_rosters(roster_date);
CREATE INDEX IF NOT EXISTS idx_employee_rosters_emp ON human_resources.employee_rosters(employee_id);

-- Seed standard hospital shift configurations
INSERT INTO human_resources.shift_schedules (shift_code, shift_name, shift_start_time, shift_end_time, is_night_shift)
VALUES
    ('SHIFT_MORNING', 'Morning Shift (OPD & Rounds)', '08:00:00', '16:00:00', FALSE),
    ('SHIFT_EVENING', 'Evening Shift (OPD & Coverage)', '16:00:00', '00:00:00', FALSE),
    ('SHIFT_NIGHT', 'Night Duty (Emergency & Inpatient)', '00:00:00', '08:00:00', TRUE),
    ('SHIFT_GENERAL', 'General Staff Office Hours', '09:00:00', '17:00:00', FALSE)
ON CONFLICT (shift_code) DO NOTHING;

-- 3. DOCUMENT SECURITY & CRYPTOGRAPHIC INTEGRITY
ALTER TABLE human_resources.employee_documents
    ADD COLUMN IF NOT EXISTS checksum_sha256 VARCHAR(64),
    ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100);

COMMIT;
