# Docker Container, Database, Migration & Seeding Guide

> **Project:** Hospital Management System (HMS)
> **Database:** PostgreSQL 15 (Alpine)
> **Container:** `hms_postgres`

---

## Table of Contents

1. [Docker Container Management](#1-docker-container-management)
2. [Database Initialization & Schema Execution](#2-database-initialization--schema-execution)
3. [Inserting / Seeding Data](#3-inserting--seeding-data)
4. [Table Structure & Schema Overview](#4-table-structure--schema-overview)
5. [Adding & Running Migrations](#5-adding--running-migrations)

---

## 1. Docker Container Management

### 1.1 Prerequisites

- Docker Desktop installed and running
- Port **5434** free (the container maps host:5434 → container:5432)

### 1.2 Start Container

```bash
# Navigate to project root
cd "C:\Users\kalyan.deringula\OneDrive - ascendion\Documents\HMS"

# Start PostgreSQL in detached mode
docker-compose up -d

# Check container status
docker-compose ps
```

**Expected output:**
```
NAME            STATUS         PORTS
hms_postgres    Up (healthy)   0.0.0.0:5434->5432/tcp
```

### 1.3 Stop Container

```bash
# Stop container (data persists in Docker volume)
docker-compose down
```

### 1.4 Full Reset — Delete Everything

> ⚠️ **WARNING:** This deletes ALL data (schemas, tables, rows, volumes).

```bash
# Stop + remove container AND delete the PostgreSQL volume
docker-compose down -v

# Then restart — init scripts will re-run from scratch
docker-compose up -d
```

This triggers `scripts/init-db.sh` which executes all 34 SQL schema files in dependency order, then runs migrations.

### 1.5 Restart Container

```bash
docker-compose restart
```

### 1.6 View Logs

```bash
# View all logs
docker-compose logs postgres

# Follow logs live
docker-compose logs -f postgres
```

### 1.7 Health Check

```bash
# Manual health check via pg_isready
docker exec hms_postgres pg_isready -U hms_admin -d hospital_management_system
```

**Expected:**
```
localhost:5432 - accepting connections
```

### 1.8 Enter Container Shell

```bash
# Bash shell inside the container
docker exec -it hms_postgres bash

# Or directly into psql
docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system
```

### 1.9 Connection Details

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5434` |
| Database | `hospital_management_system` |
| Username | `hms_admin` |
| Password | `hms_secure_password_2024` |
| Connection String | `postgresql://hms_admin:hms_secure_password_2024@localhost:5434/hospital_management_system` |

---

## 2. Database Initialization & Schema Execution

### 2.1 How Initialization Works (init-db.sh Flow)

When a fresh container starts for the **first time** (after `docker-compose down -v && docker-compose up -d`), the `scripts/init-db.sh` script runs automatically. It:

1. **Executes 34 schema SQL files** in strict dependency order (shared master tables first, then dependent modules)
2. **Runs production functions & triggers** (`00_PRODUCTION_FUNCTIONS_TRIGGERS.sql`)
3. **Runs migration files** from `database/migrations/` directory
4. **Verifies** schemas and table counts

### 2.2 Schema Execution Order

The `init-db.sh` script runs these SQL files sequentially:

```
 1. SHARED_MASTER_TABLES.sql                 ← Foundation: buildings, floors, notifications, etc.
 2. Security, IAM & Compliance Management     ← users, roles, permissions, audit_logs
 3. Multi-Hospital Multi-Tenant Management    ← hospitals, tenants, branches
 4. patient.sql                               ← patients, profiles, allergies, insurance
 5. doctor.sql                                ← doctors, specializations, schedules
 6. department.sql                            ← departments, units, staff, workflows
 7. appointment_management.sql                ← appointments, slots, queues, reminders
 8. Electronic_Medical_Records.sql            ← encounters, diagnoses, procedures
 9. ADMISSION_&_BED_MANAGEMENT.sql            ← admissions, wards, rooms, beds
10. BILLING_&_FINANCIAL_MANAGEMENT.sql        ← invoices, payments, refunds
11. PHARMACY_MANAGEMENT_SYSTEM.sql            ← prescriptions, drugs, dispensing
12. Laboratory Information System.sql         ← lab_orders, samples, results
13. RADIOLOGY INFORMATION SYSTEM.sql          ← imaging_orders, studies, DICOM
14. EMERGENCY_&_TRAUMA_MANAGEMENT.sql         ← emergency_encounters, trauma, triage
15. SURGERY_&_OT_MANAGEMENT_SYSTEM.sql        ← surgery_requests, scheduling, OT
16. ICU_&_CRITICAL_CARE_MANAGEMENT.sql        ← icu_admissions, ventilators, monitoring
17. NURSING_MANAGEMENT_SYSTEM.sql             ← nurses, tasks, vital_signs
18. INSURANCE & CLAIMS MANAGEMENT.sql         ← claims, preauthorizations, policies
19. INVENTORY & PROCUREMENT MANAGEMENT.sql    ← items, purchase_orders, vendors
20. HR & PAYROLL MANAGEMENT SYSTEM.sql        ← employees, payroll, attendance
21. AMBULANCE & TRANSPORT MANAGEMENT.sql      ← ambulances, dispatch, GPS tracking
22. BLOOD_BANK_MANAGEMENT.sql                 ← donors, units, transfusions
23. DIETETICS_NUTRITION_MANAGEMENT.sql        ← diet_orders, meals, nutrition
24. Category_19_Telemedicine_Virtual_Care.sql ← virtual_appointments, video_sessions
25. Category_20_CRM_Patient_Engagement.sql    ← leads, campaigns, feedback
26. QUEUE_MANAGEMENT_SYSTEM.sql               ← tokens, service_points, wait_times
27. HOUSEKEEPING_MANAGEMENT.sql               ← tasks, schedules, inspections
28. VISITOR_MANAGEMENT.sql                    ← visitors, passes, screening
29. BIOMEDICAL_WASTE_MANAGEMENT.sql           ← waste_collection, disposal
30. MORTUARY_MEDICOLEGAL_MANAGEMENT.sql       ← death_records, medico_legal_cases
31. REHABILITATION_PHYSIOTHERAPY_MANAGEMENT.sql ← referrals, sessions, progress
32. Analytics & Business Intelligence.sql     ← dashboards, KPIs, reports
33. AI & CLINICAL DECISION SUPPORT.sql        ← models, clinical_rules, risk_scores

Then:
34. 00_PRODUCTION_FUNCTIONS_TRIGGERS.sql      ← Functions & triggers (audit, soft-delete, etc.)
35. database/migrations/*.sql                 ← Migration files (e.g., 001_add_core_departments.sql)
```

### 2.3 Verify Initialization Success

```bash
# List all schemas (should be 33+)
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
ORDER BY schema_name;"

# Count tables per schema
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "
SELECT schemaname, count(*) as table_count
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schemaname
ORDER BY schemaname;"
```

### 2.4 Manual Schema Deployment (if init-db.sh fails)

If the init script fails, execute files manually inside the container:

```bash
docker exec -it hms_postgres bash

# Inside container:
cd /docker-entrypoint-initdb.d/schemas
psql -U hms_admin -d hospital_management_system -f SHARED_MASTER_TABLES.sql
psql -U hms_admin -d hospital_management_system -f patient.sql
psql -U hms_admin -d hospital_management_system -f doctor.sql
# ... continue with remaining files

# Then run migrations
cd /docker-entrypoint-initdb.d/migrations
psql -U hms_admin -d hospital_management_system -f 001_add_core_departments.sql
```

---

## 3. Inserting / Seeding Data

### 3.1 Seed the Super Admin User

The project includes `seed_admin.py` which creates a default super admin.

```bash
# From project root (container must be running)
cd "C:\Users\kalyan.deringula\OneDrive - ascendion\Documents\HMS"
python seed_admin.py
```

**Created credentials:**

| Field | Value |
|---|---|
| Employee ID | `ADMIN-SUPER-00001` |
| Email | `admin@hospital.com` |
| Password | `Admin_@_01011990` |
| Role | `super_admin` |

### 3.2 Verify Admin User Created

```bash
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "
SELECT u.username, u.email, u.status, r.role_name
FROM security.users u
JOIN security.user_roles ur ON u.user_id = ur.user_id
JOIN security.roles r ON ur.role_id = r.role_id
WHERE u.username = 'ADMIN-SUPER-00001';"
```

### 3.3 Insert Custom Data via SQL

```bash
# Single query
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "
INSERT INTO patient.genders (gender_id, gender_name) VALUES
(gen_random_uuid(), 'Male'),
(gen_random_uuid(), 'Female'),
(gen_random_uuid(), 'Other');"

# Run a SQL file
docker exec -i hms_postgres psql -U hms_admin -d hospital_management_system < path/to/seed_data.sql
```

### 3.4 Insert Test Data into Specific Tables

```bash
# Insert a test department
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "
INSERT INTO core.departments (department_code, department_name, schema_name)
VALUES ('DEP-TEST', 'Test Department', 'testing')
ON CONFLICT (department_code) DO NOTHING;"

# Insert a test patient
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "
INSERT INTO patient.patients (first_name, last_name, date_of_birth, gender_id, phone)
VALUES ('John', 'Doe', '1990-01-01',
  (SELECT gender_id FROM patient.genders LIMIT 1),
  '+1234567890');"
```

---

## 4. Table Structure & Schema Overview

### 4.1 All Schemas in the System

| # | Schema | Description |
|---|---|---|
| 1 | `core` | Shared master tables (buildings, floors, notifications, services) |
| 2 | `security` | Users, roles, permissions, audit logs, IAM |
| 3 | `multi_hospital` | Hospitals, tenants, branches |
| 4 | `patient` | Patients, profiles, allergies, insurance policies |
| 5 | `doctor` | Doctors, specializations, schedules |
| 6 | `department` | Departments, units, staff, workflows |
| 7 | `appointment` | Appointments, slots, queues, reminders |
| 8 | `electronic_medical_records` | Encounters, diagnoses, procedures |
| 9 | `admission` | Admissions, wards, rooms, beds |
| 10 | `billing` | Invoices, payments, refunds, billing accounts |
| 11 | `pharmacy` | Prescriptions, drugs, dispensing |
| 12 | `laboratory` | Lab orders, samples, results |
| 13 | `radiology` | Imaging orders, studies, DICOM files |
| 14 | `emergency` | Emergency encounters, trauma, triage |
| 15 | `surgery` | Surgery requests, scheduling, OT management |
| 16 | `intensive_care_unit` | ICU admissions, ventilators, monitoring |
| 17 | `nursing` | Nurses, tasks, vital signs |
| 18 | `insurance` | Claims, preauthorizations, policies |
| 19 | `inventory` | Items, purchase orders, vendors |
| 20 | `human_resources` | Employees, payroll, attendance |
| 21 | `ambulance` | Ambulances, dispatch, GPS tracking |
| 22 | `blood_bank` | Donors, units, transfusions |
| 23 | `dietetics` | Diet orders, meals, nutrition |
| 24 | `telemedicine` | Virtual appointments, video sessions |
| 25 | `customer_relationship_management` | Leads, campaigns, feedback |
| 26 | `queue_management` | Tokens, service points, wait times |
| 27 | `housekeeping` | Tasks, schedules, inspections |
| 28 | `visitor` | Visitors, passes, screening |
| 29 | `biomedical_waste` | Waste collection, disposal, compliance |
| 30 | `mortuary` | Death records, medico-legal cases |
| 31 | `rehabilitation` | Referrals, sessions, progress tracking |
| 32 | `analytics` | Dashboards, KPIs, reports |
| 33 | `artificial_intelligence` | Models, clinical rules, risk scores |

### 4.2 List Tables in a Schema

```bash
# List all tables in the patient schema
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\dt patient.*"

# List tables in doctor schema
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\dt doctor.*"

# List tables in appointment schema
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\dt appointment.*"
```

### 4.3 Describe a Table (Columns, Types, Constraints)

```bash
# View full table structure
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\d patient.patients"
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\d doctor.doctors"
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\d admission.admissions"
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\d billing.invoices"
```

### 4.4 Cross-Module Foreign Key Reference Map

| Source Table | FK Column | Target Table | Target Column |
|---|---|---|---|
| `appointment.appointments` | `patient_id` | `patient.patients` | `patient_id` |
| `appointment.appointments` | `doctor_id` | `doctor.doctors` | `doctor_id` |
| `appointment.appointments` | `department_id` | `department.departments` | `department_id` |
| `admission.admissions` | `patient_id` | `patient.patients` | `patient_id` |
| `admission.admissions` | `encounter_id` | `electronic_medical_records.patient_encounters` | `encounter_id` |
| `admission.admissions` | `ward_id` | `admission.wards` | `ward_id` |
| `admission.admissions` | `bed_id` | `admission.beds` | `bed_id` |
| `laboratory.lab_orders` | `patient_id` | `patient.patients` | `patient_id` |
| `laboratory.lab_orders` | `doctor_id` | `doctor.doctors` | `doctor_id` |
| `laboratory.lab_orders` | `encounter_id` | `electronic_medical_records.patient_encounters` | `encounter_id` |
| `billing.invoices` | `patient_id` | `patient.patients` | `patient_id` |
| `billing.invoices` | `admission_id` | `admission.admissions` | `admission_id` |
| `insurance.insurance_claims` | `invoice_id` | `billing.invoices` | `invoice_id` |
| `surgery.surgery_requests` | `patient_id` | `patient.patients` | `patient_id` |
| `pharmacy.prescriptions` | `patient_id` | `patient.patients` | `patient_id` |
| `pharmacy.prescriptions` | `doctor_id` | `doctor.doctors` | `doctor_id` |
| `emergency.emergency_encounters` | `patient_id` | `patient.patients` | `patient_id` |
| `human_resources.doctors` | `employee_id` | `human_resources.employees` | `employee_id` |
| `human_resources.employees` | `department_id` | `core.departments` | `department_id` |
| `doctor.doctors` | `department_id` | `core.departments` | `department_id` |
| `admission.wards` | `department_id` | `department.departments` | `department_id` |

### 4.5 Query Sample Data

```bash
# View 5 patients
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "SELECT * FROM patient.patients LIMIT 5;"

# View active departments
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "SELECT * FROM core.departments WHERE is_active = true;"

# Count total tables in database
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "
SELECT count(*) FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');"
```

---

## 5. Adding & Running Migrations

### 5.1 Migration File Structure

Migrations live in `database/migrations/` and are executed **after** all schema files during initialization. They use the naming convention:

```
database/migrations/
├── 001_add_core_departments.sql    ← First migration: link schemas to core tables
├── 002_...sql                      ← Future migration
└── 003_...sql                      ← Future migration
```

### 5.2 How Migrations Work

- Migrations are **idempotent** — they use `IF NOT EXISTS`, `CREATE IF NOT EXISTS`, and `ON CONFLICT DO NOTHING` to avoid errors on re-run.
- They are executed by `scripts/init-db.sh` automatically on fresh container start.
- They can also be run manually against a running database.

### 5.3 Creating a New Migration

To add a new migration, create a new `.sql` file in `database/migrations/`:

```sql
-- =========================================================
-- MIGRATION: 002_add_department_audit_fields.sql
-- Date: 2025-01-01
-- Description: Add audit columns to core.departments
-- =========================================================

-- STEP 1: Add new columns (idempotent)
ALTER TABLE core.departments
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES security.users(user_id),
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- STEP 2: Create indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_departments_updated_at ON core.departments(updated_at);
CREATE INDEX IF NOT EXISTS idx_departments_deleted_at ON core.departments(deleted_at);

-- STEP 3: Update existing rows
UPDATE core.departments SET updated_at = created_at WHERE updated_at IS NULL;

-- =========================================================
-- END OF MIGRATION 002
-- =========================================================
```

**File naming convention:**
- Use sequential numbering: `001_...sql`, `002_...sql`, `003_...sql`
- Use descriptive names: `002_add_department_audit_fields.sql`
- Include a header comment with date and description

### 5.4 Running a Migration Manually

```bash
# Run a specific migration file against running database
docker exec -i hms_postgres psql -U hms_admin -d hospital_management_system -f /docker-entrypoint-initdb.d/migrations/001_add_core_departments.sql

# Or from host (pipe the file into psql)
docker exec -i hms_postgres psql -U hms_admin -d hospital_management_system < database/migrations/001_add_core_departments.sql
```

### 5.5 Applying New Migrations to a Running Container

If the container is already running and you need to apply a **new** migration without resetting:

```bash
# 1. Copy the new migration file into the container
docker cp database/migrations/002_new_migration.sql hms_postgres:/tmp/

# 2. Execute it inside the container
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -f /tmp/002_new_migration.sql

# 3. Verify the changes
docker exec hms_postgres psql -U hms_admin -d hospital_management_system -c "\d core.departments"
```

### 5.6 Migration That Includes Both Container Start + Running DB

Migrations are designed to work both:
1. **Automatically on fresh start** — via `init-db.sh` looping through `database/migrations/*.sql`
2. **Manually on running DB** — via `docker exec` as shown above

This is safe because all SQL statements use `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` guards.

### 5.7 Existing Migration: 001_add_core_departments.sql

The first migration (`database/migrations/001_add_core_departments.sql`) does the following:

**Purpose:** Link all existing module schemas to the centralized `core.departments` and `core.sub_departments` master tables.

**What it does:**
1. Creates `core.departments` and `core.sub_departments` (if not exist)
2. Adds FK columns to tables in `human_resources`, `doctor`, `department` schemas
3. Creates indexes for performance
4. Seeds 32+ core departments (DEP-PAT, DEP-DOC, DEP-APT, etc.)
5. Seeds sub-departments for: Doctor Specializations, Lab, Radiology, Surgery, Nursing, Pharmacy, Emergency

---

## Quick Reference Commands

| Action | Command |
|---|---|
| **Start containers** | `docker-compose up -d` |
| **Stop containers** | `docker-compose down` |
| **Full reset** | `docker-compose down -v && docker-compose up -d` |
| **Restart** | `docker-compose restart` |
| **View logs** | `docker-compose logs -f postgres` |
| **Enter psql** | `docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system` |
| **Enter bash** | `docker exec -it hms_postgres bash` |
| **List schemas** | `\dn` (inside psql) |
| **List tables** | `\dt patient.*` (inside psql) |
| **Describe table** | `\d patient.patients` (inside psql) |
| **Run SQL file** | `docker exec -i hms_postgres psql -U hms_admin -d hospital_management_system -f /path/to/file.sql` |
| **Seed admin user** | `python seed_admin.py` |
| **Health check** | `docker exec hms_postgres pg_isready -U hms_admin -d hospital_management_system` |
| **Copy migration** | `docker cp database/migrations/NEW_FILE.sql hms_postgres:/tmp/` |
| **Run new migration** | `docker exec hms_postgres psql -U hms_admin -d hospital_management_system -f /tmp/NEW_FILE.sql` |
| **Find port usage** | `netstat -ano \| findstr :5434` |
| **Kill port process** | `taskkill /PID <PID> /F` |

