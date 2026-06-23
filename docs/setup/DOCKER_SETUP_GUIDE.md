# Hospital Management System - Docker & PostgreSQL Setup Guide

---

## Prerequisites

- Docker Desktop installed and running

---

## Quick Start

```bash
cd "C:\Users\kalyan.deringula\OneDrive - ascendion\Documents\Z"

# First time (or reset)
docker-compose down -v
docker-compose up -d

# Check status
docker-compose ps
```

Expected:

```
NAME            STATUS         PORTS
hms_postgres    Up (healthy)   0.0.0.0:5434->5432/tcp
```

---

## Connection Details

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5434` |
| Database | `hospital_management_system` |
| Username | `hms_admin` |
| Password | `hms_secure_password_2024` |
| Connection String | `postgresql://hms_admin:hms_secure_password_2024@localhost:5434/hospital_management_system` |

---

## How to Access Database

### Option 1: Command Line (psql inside container)

```bash
docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system
```

### Option 2: DBeaver / DataGrip / pgAdmin (External tool)

Use the connection details above with host `localhost` and port `5434`.

---

## Useful SQL Commands

```sql
-- List all schemas
\dn

-- List tables in a specific schema
\dt patient.*
\dt doctor.*
\dt appointment.*
\dt laboratory.*
\dt electronic_medical_records.*
\dt intensive_care_unit.*
\dt human_resources.*
\dt artificial_intelligence.*
\dt customer_relationship_management.*
\dt queue_management.*
\dt rehabilitation.*
\dt biomedical_waste.*
\dt multi_hospital.*

-- Count total tables across all schemas
SELECT schemaname, count(*) 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY schemaname
ORDER BY schemaname;

-- See a table structure
\d patient.patients
\d doctor.doctors
\d laboratory.lab_orders
\d intensive_care_unit.icu_admissions

-- Query a table
SELECT * FROM patient.genders;
SELECT * FROM patient.patients LIMIT 5;

-- List all schemas with table count
SELECT schema_name FROM information_schema.schemata 
WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema';

-- Exit psql
\q
```

---

## Database Schema Layout

After deployment, tables are organized into separate schemas:

```
hospital_management_system/
├── core                              → shared tables (buildings, notifications, services)
├── patient                           → patients, profiles, allergies, insurance
├── doctor                            → doctors, specializations, schedules
├── department                        → departments, units, staff, workflows
├── appointment                       → appointments, slots, queues, reminders
├── electronic_medical_records        → encounters, diagnoses, procedures
├── admission                         → admissions, wards, rooms, beds
├── billing                           → invoices, payments, refunds
├── laboratory                        → lab_orders, samples, results
├── radiology                         → imaging_orders, studies, DICOM files
├── pharmacy                          → prescriptions, drugs, dispensing
├── nursing                           → nurses, tasks, vital_signs
├── intensive_care_unit               → icu_admissions, ventilators, monitoring
├── surgery                           → surgery_requests, scheduling, OT
├── emergency                         → emergency_encounters, trauma, triage
├── insurance                         → claims, preauthorizations, policies
├── inventory                         → items, purchase_orders, vendors
├── human_resources                   → employees, payroll, attendance
├── ambulance                         → ambulances, dispatch, GPS tracking
├── telemedicine                      → virtual_appointments, video_sessions
├── customer_relationship_management  → leads, campaigns, feedback
├── analytics                         → dashboards, KPIs, reports
├── security                          → users, roles, permissions, audit_logs
├── multi_hospital                    → hospitals, tenants, branches
├── artificial_intelligence           → models, clinical_rules, risk_scores
├── blood_bank                        → donors, units, transfusions
├── dietetics                         → diet_orders, meals, nutrition
├── biomedical_waste                  → waste_collection, disposal, compliance
├── visitor                           → visitors, passes, screening
├── rehabilitation                    → referrals, sessions, progress
├── mortuary                          → death_records, medico_legal_cases
├── queue_management                  → tokens, service_points, wait_times
└── housekeeping                      → tasks, schedules, inspections
```

---

## Common Commands

```bash
# Start PostgreSQL
docker-compose up -d

# Stop (keep data)
docker-compose down

# Stop + DELETE all data (full reset)
docker-compose down -v

# Restart
docker-compose restart

# View logs
docker-compose logs postgres

# Follow logs live
docker-compose logs -f postgres

# Enter container bash
docker exec -it hms_postgres bash

# Enter psql directly
docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system

# Run a single SQL file manually
docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system -f /docker-entrypoint-initdb.d/schemas/patient.sql
```

---

## Troubleshooting

### Port 5434 already in use

```bash
# Windows - find what's using port
netstat -ano | findstr :5434

# Kill it
taskkill /PID <PID_NUMBER> /F

# Then restart
docker-compose up -d
```

### Container not starting

```bash
docker-compose logs postgres
```

### Schemas not created (init script didn't run)

Init scripts only run on FIRST start with empty volume. To re-run:

```bash
# Delete volume and restart
docker-compose down -v
docker-compose up -d
```

### Manual schema deployment (if init-db.sh fails)

```bash
docker exec -it hms_postgres bash

# Inside container:
cd /docker-entrypoint-initdb.d/schemas
psql -U hms_admin -d hospital_management_system -f SHARED_MASTER_TABLES.sql
psql -U hms_admin -d hospital_management_system -f patient.sql
psql -U hms_admin -d hospital_management_system -f doctor.sql
# ... continue with remaining files
```

---

## Verify Everything Works

```bash
# 1. Container running?
docker-compose ps
# Expected: hms_postgres Up (healthy)

# 2. Can connect?
docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system -c "\dn"
# Expected: list of schemas (core, patient, doctor, etc.)

# 3. Tables exist?
docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system -c "\dt patient.*"
# Expected: list of patient tables

# 4. Schema count?
docker exec -it hms_postgres psql -U hms_admin -d hospital_management_system -c "SELECT count(DISTINCT schemaname) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema');"
# Expected: 33
```

---

## File Structure

```
Z/
├── docker-compose.yml              ← Docker config (PostgreSQL only)
├── .env                            ← Environment variables
├── scripts/
│   └── init-db.sh                  ← Runs all SQL files on first start
├── data_schemas/
│   ├── sql/                        ← 34 SQL schema files
│   └── docs/                       ← Documentation
├── PROJECT_TIMETABLE.md            ← Development roadmap
└── DOCKER_SETUP_GUIDE.md           ← This file
```

---
