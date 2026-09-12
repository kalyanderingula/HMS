> **Verified status (September 2026):** All 12 operational hospital portals, the consolidated final database schema, registered ORM tables, and comprehensive clinical, diagnostics, emergency, surgery, nursing, blood bank, pharmacy, billing, and administration workflows are active and tested. See [implementation status and remaining work](docs/IMPLEMENTATION_STATUS.md).

## Quick Run

From this `HMS` directory:

```powershell
# 1. Start PostgreSQL. On a new volume Docker creates every base schema.
docker compose up -d postgres

# 2. Install dependencies
python -m pip install -r requirements-runtime.txt

# 3. Seed all demo data/accounts and verify the final schema
python scripts/bootstrap.py

# 4. Launch FastAPI from any PowerShell working directory
.\run.ps1
```

If launching Uvicorn manually, first change into the inner `HMS` directory that
contains `main.py`. The provided `run.ps1` resolves the project directory and
virtual environment automatically.

`bootstrap.py` is safe to run again. New databases receive the complete final
schema from `database/schemas`, and failures stop setup immediately. Set
`HMS_DEMO_PASSWORD` before bootstrapping to replace the local default password
used by demo accounts. `scripts/migrate_all.py` remains available for future
incremental upgrades; the historical migration files are already consolidated.

Log in at `http://localhost:8000/` using any of the pre-seeded operational or clinical accounts below.

To run the full regression test suite:

```powershell
python -m pytest tests -q
```

---

# 🏥 HMS — Enterprise Hospital Management System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_14+-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Domain--Driven-blue?style=flat)](#-system-architecture)

An enterprise-grade, domain-driven Hospital Management System designed for scalable clinical operations, multi-role hospital portals, and zero-cost local deployment.

---

## 📚 Complete Project Documentation

All detailed architectural specifications, API contracts, and guides are located in the **[`docs/`](docs/)** directory:

| Document | Description | Direct Link |
| :--- | :--- | :--- |
| 🗄️ **Database Architecture** | Complete guide to all 33 schemas, 1,050 tables, SSOT rules, FK interlinking, and performance indexes | **[`docs/DATABASE_ARCHITECTURE.md`](docs/DATABASE_ARCHITECTURE.md)** |
| 📡 **API Reference** | Detailed contracts for all REST endpoints (`/auth`, `/patients`, `/doctor`, `/departments`, `/employees`) | **[`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)** |
| 🎨 **Frontend Architecture** | Modular `html/`, `css/`, `js/` directory structure, role portals, and JWT session handling | **[`docs/FRONTEND_ARCHITECTURE.md`](docs/FRONTEND_ARCHITECTURE.md)** |
| 🗺️ **Development Roadmap** | Step-by-step solo developer milestone plan from Patient Management to EMR and Billing | **[`docs/SOLO_DEVELOPER_ROADMAP.md`](docs/SOLO_DEVELOPER_ROADMAP.md)** |
| 🐳 **Docker Management** | Docker container orchestration and local setup guide | **[`docs/DOCKER_CONTAINER_MANAGEMENT.md`](docs/DOCKER_CONTAINER_MANAGEMENT.md)** |

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Client Portals [Operational & Clinical Portals (12 UI Routes)]
        REC[🗂️ /receptionist<br/>Reception & Booking]
        DOC[🩺 /doctor<br/>EMR, Diagnostics & Follow-ups]
        ADM[⚙️ /admin<br/>Admin & HR]
        NUR[👩‍⚕️ /nurse<br/>Wards, Admissions & MAR]
        PHARM[💊 /pharmacist<br/>Inventory & Dispensing]
        LAB[🔬 /lab<br/>Pathology & Lab Tests]
        RAD[🩻 /radiology<br/>Imaging, PACS & Reports]
        ACCT[💳 /accounts<br/>Invoices, Payments & Refunds]
        BLD[🩸 /blood-bank<br/>Blood Units & Transfusion]
        ER[🚨 /emergency<br/>Triage & Resuscitation]
        SURG[🔪 /surgery<br/>OT, Surgeons & Recovery]
    end

    subgraph Presentation Layer
        STATIC[frontend/html/ & frontend/js/<br/>Dedicated Workspace Templates + Shared Header, Notifications & Staff.js]
    end

    subgraph API Gateway & Routers (FastAPI)
        R_AUTH[/api/v1/auth & /notifications]
        R_CLINICAL[/api/v1/doctor, /patients, /emr, /telemedicine]
        R_DIAG[/api/v1/laboratory & /radiology]
        R_ACUTE[/api/v1/inpatient, /nursing, /emergency, /surgery]
        R_OPERATIONAL[/api/v1/pharmacy, /blood_bank, /billing, /worklists]
        R_CORE[/api/v1/departments, /employees, /documents, /locations]
    end

    subgraph Relational Database (PostgreSQL 14+)
        DB_CORE[(core & human_resources)]
        DB_PAT[(patient, appointment, doctor)]
        DB_EMR[(emr, telemedicine)]
        DB_DIAG[(laboratory, radiology)]
        DB_ACUTE[(inpatient, nursing, emergency, surgery)]
        DB_BILLING[(billing, pharmacy, blood_bank)]
    end

    Client Portals --> STATIC
    STATIC --> R_AUTH & R_CLINICAL & R_DIAG & R_ACUTE & R_OPERATIONAL & R_CORE
    R_AUTH & R_CLINICAL & R_DIAG & R_ACUTE & R_OPERATIONAL & R_CORE --> DB_CORE & DB_PAT & DB_EMR & DB_DIAG & DB_ACUTE & DB_BILLING
```

---

## 📂 Project Directory Structure

```
HMS/
├── app/
│   ├── api/                    # FastAPI route handlers
│   │   ├── auth.py             # User authentication & role tokens
│   │   ├── patients.py         # Patient registration & live search
│   │   ├── doctor.py           # Doctor schedules & profile endpoints
│   │   ├── departments.py      # Core hospital departments
│   │   ├── sub_departments.py  # Medical specializations
│   │   ├── employees.py        # Staff accounts & HR profiles
│   │   ├── documents.py        # Document upload & storage
│   │   └── locations.py        # Countries & States master lookup
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── department.py       # core.departments
│   │   ├── employee.py         # human_resources.employees
│   │   └── patient.py          # patient.patients & contacts
│   ├── schemas/                # Pydantic validation schemas
│   │   ├── employee.py         # Employee request/response schemas
│   │   └── patient.py          # Patient registration schemas
│   └── config.py               # Database engine & environment settings
│
├── database/
│   ├── schemas/                # 35 Domain SQL schema files (1,050 tables)
│   │   ├── 00_PRODUCTION_FUNCTIONS_TRIGGERS.sql
│   │   ├── SHARED_MASTER_TABLES.sql
│   │   ├── patient.sql
│   │   ├── doctor.sql
│   │   ├── appointment_management.sql
│   │   ├── Electronic_Medical_Records.sql
│   │   └── 01_FOREIGN_KEYS_AND_INDEXES.sql  # Master FKs & Indexes
│   └── migrations/             # Reserved for future incremental upgrades
│
├── docs/                       # Comprehensive project documentation
│   ├── DATABASE_ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── FRONTEND_ARCHITECTURE.md
│   └── SOLO_DEVELOPER_ROADMAP.md
│
├── frontend/                   # Modular web client
│   ├── html/                   # HTML Templates (index, receptionist, doctor, admin)
│   ├── css/                    # Stylesheets (login.css, receptionist.css, admin.css)
│   └── js/                     # Client-side scripts (login.js, receptionist.js, doctor.js, admin.js)
│
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
└── docker-compose.yml          # PostgreSQL & services orchestration
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
* **Python 3.10+**
* **PostgreSQL 14+**

### 2. Environment Configuration
Create a `.env` file in the project root:
```env
POSTGRES_DB=hospital_management_system
POSTGRES_USER=hms_admin
POSTGRES_PASSWORD=hms_secure_password_2024
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
JWT_SECRET=hms-jwt-secret-change-in-production
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database
Execute the schema files in topological order, then apply foreign keys & performance indexes:
```sql
\i database/schemas/01_FOREIGN_KEYS_AND_INDEXES.sql
```

### 5. Start the Application
```bash
uvicorn main:app --reload --port 8000
```

---

## 🌐 Complete System URLs Directory (15 Primary Web URLs)

The application exposes **12 dedicated frontend role portals**, **2 interactive API documentation endpoints**, and **1 health probe**, backed by **65+ REST endpoints** under `/api/v1/*`:

| # | Route / URL | Workspace Name | Target / Allowed Roles | Core Capabilities |
|---|---|---|---|---|
| 1 | `http://localhost:8000/` | **Main Login Portal** | All Hospital Staff & Doctors | Universal JWT authentication, portal auto-routing, password reset on first login |
| 2 | `http://localhost:8000/admin` | **Admin & HR Dashboard** | `super_admin`, `admin`, `hr` | Employee & doctor onboarding, departments, document archive, system audits |
| 3 | `http://localhost:8000/doctor` | **Doctor Clinical Workspace** | `doctor`, `admin` | OPD queue, EMR encounters, SOAP notes, vitals, prescriptions, lab/rad ordering, diagnostic review, PACS viewer, follow-up bookings |
| 4 | `http://localhost:8000/receptionist` | **Reception Desk** | `receptionist`, `admin` | Patient intake, MRN issuance, duplicate checking, doctor schedule lookup, OPD token generation, and read-only live queue tracking |
| 5 | `http://localhost:8000/nurse` | **Inpatient Nursing Ward** | `nurse`, `admin` | Ward bed occupancy, active admissions, bed transfers, nursing rounds, MAR shift dose administration & allergen safety checks |
| 6 | `http://localhost:8000/pharmacist` | **Central Pharmacy** | `pharmacist`, `admin` | Prescription dispensing queue, batch stock receipt, expiry validation, multi-item dispensing, interaction checks, auto-billing |
| 7 | `http://localhost:8000/lab` | **Pathology & Laboratory** | `lab_technician`, `admin` | Diagnostic worklist, sample collection barcode/tube tagging, test parameter result entry, abnormal/critical result alerts |
| 8 | `http://localhost:8000/radiology` | **Radiology & Imaging** | `radiologist`, `admin` | Imaging worklist, modality room scheduling, PACS multi-slice image gallery viewer, diagnostic reports, critical finding alerts |
| 9 | `http://localhost:8000/accounts` | **Accounts & Billing** | `accountant`, `admin`, `insurance_officer` | Patient billing accounts, itemized invoicing, multi-method payments (Cash/Card/UPI), duplicate/overpayment protection, refunds, credit notes, insurance claims |
| 10 | `http://localhost:8000/blood-bank` | **Blood Bank** | `blood_bank_technician`, `admin` | Blood unit inventory, cross-match compatibility testing, unit reservation, issue to ward, transfusion reaction logging |
| 11 | `http://localhost:8000/emergency` | **Emergency & Trauma** | `emergency_staff`, `nurse`, `doctor`, `admin` | ESI 1–5 triage queue, trauma bay vitals, rapid clinical notes, emergency disposition, direct inpatient admission |
| 12 | `http://localhost:8000/surgery` | **Operation Theatre** | `surgeon`, `ot_nurse`, `anesthesiologist`, `admin` | Conflict-free theatre scheduling, WHO surgical safety checklists, consumable & implant tracking, operation notes, PACU recovery records |
| 13 | `http://localhost:8000/docs` | **Swagger Interactive API** | Developers / Integrators | OpenAPI v3 interactive endpoint explorer, live request runner, schema inspection |
| 14 | `http://localhost:8000/redoc` | **ReDoc Documentation** | Developers / Technical Staff | Full human-readable REST API reference specifications |
| 15 | `http://localhost:8000/health` | **System Health Probe** | DevOps / Monitoring | Lightweight JSON health check (`{"status": "healthy"}`) |

---

## 🔑 Demo User Accounts, Usernames & Passwords

The system includes pre-configured demo accounts for all hospital roles.

### Operational Staff Accounts (Seeded via `python seed_operational_staff.py`)
All operational accounts below share the default demonstration password: **`HmsDemo@2026`** (can be overridden before seeding with environment variable `HMS_DEMO_PASSWORD`). 

> [!IMPORTANT]
> All newly seeded accounts have `must_change_password = True` enabled for security. On your first login at `http://localhost:8000/`, you will be prompted to set a personal password.

| Portal | Username | Default Password | Role Assigned | Employee Profile |
|---|---|---|---|---|
| **Surgery** | `SURG-001` | `HmsDemo@2026` | `surgeon` | Dr. Vikram Sen (Lead Surgeon) |
| **Surgery (OT)** | `OTN-001` | `HmsDemo@2026` | `ot_nurse` | Maya Das (Head OT Nurse) |
| **Surgery (Anesthesia)** | `ANES-001` | `HmsDemo@2026` | `anesthesiologist` | Dr. Rohan Iyer (Chief Anesthesiologist) |
| **Emergency** | `ER-001` | `HmsDemo@2026` | `emergency_staff` | Asha Rao (Senior Emergency Staff) |
| **Pharmacy** | `PHARM-001` | `HmsDemo@2026` | `pharmacist` | Priya Sharma (In-Charge Pharmacist) |
| **Laboratory** | `LAB-001` | `HmsDemo@2026` | `lab_technician` | Lakshmi Nair (Senior Lab Technologist) |
| **Nursing** | `NURSE-001` | `HmsDemo@2026` | `nurse` | Neha Patel (Ward Staff Nurse) |
| **Accounts / Billing** | `ACCT-001` | `HmsDemo@2026` | `accountant` | Arjun Mehta (Senior Billing Officer) |
| **Radiology** | `RAD-001` | `HmsDemo@2026` | `radiologist` | Dr. Riya Kapoor (Consultant Radiologist) |
| **Blood Bank** | `BLOOD-001` | `HmsDemo@2026` | `blood_bank_technician` | Anil Kumar (Blood Bank Technician) |

### Administrative, Reception & Doctor Accounts

| Portal | Username | Password Source | Role Assigned | Seeding Script |
|---|---|---|---|---|
| **Admin** | `ADMIN-SUPER-00001` | Environment variable `HMS_INITIAL_ADMIN_PASSWORD` (or generated token printed in console) | `super_admin` | `python seed_admin.py` |
| **Reception** | `EMP-REC-00001` | Environment variable `HMS_DEMO_RECEPTIONIST_PASSWORD` (or generated token printed in console) | `receptionist` | `python seed_receptionist.py` |
| **Doctor (Cardiology)** | `DOC-CARD-001` | Environment variable `HMS_DEMO_DOCTOR_PASSWORD` (or generated token printed in console) | `doctor` | `python seed_receptionist_demo.py` |
| **Doctor (Orthopedics)** | `DOC-ORTH-002` | Environment variable `HMS_DEMO_DOCTOR_PASSWORD` (or generated token printed in console) | `doctor` | `python seed_receptionist_demo.py` |
| **Doctor (Pediatrics)** | `DOC-PEDI-003` | Environment variable `HMS_DEMO_DOCTOR_PASSWORD` (or generated token printed in console) | `doctor` | `python seed_receptionist_demo.py` |
| **Doctor (General)** | `DOC-GP-004` | Environment variable `HMS_DEMO_DOCTOR_PASSWORD` (or generated token printed in console) | `doctor` | `python seed_receptionist_demo.py` |
| **Doctor (Neurology)** | `DOC-NEUR-005` | Environment variable `HMS_DEMO_DOCTOR_PASSWORD` (or generated token printed in console) | `doctor` | `python seed_receptionist_demo.py` |

---

## 📈 Up-to-Date System Data & Verified Status

| Metric / Dimension | Verified Implementation Count | Details & Operational Scope |
|---|---|---|
| **Frontend UI Portals** | **12 Portals** | Separate role-aware single page views with 403 authorization guardrails |
| **System Web Endpoints** | **15 Endpoints** | 12 Frontend Portals + Swagger UI + ReDoc + Health check |
| **REST API Routers** | **22 Routers** | Mounted under `/api/v1/` (`auth`, `patients`, `doctor`, `emr`, `pharmacy`, `laboratory`, `radiology`, `inpatient`, `nursing`, `surgery`, `blood_bank`, `billing`, `emergency`, `notifications`, etc.) |
| **Database Schema** | **Consolidated** | Base domain definitions plus `02_APPLICATION_SCHEMA_EXTENSIONS.sql` contain the complete current schema |
| **SQL Schema Domains** | **35 Schemas** | Core, HR, Patient, Doctor, Appointment, EMR, Inpatient, Pharmacy, Laboratory, Radiology, Surgery, Billing, etc. |
| **Total Database Tables** | **1,050 Normalized Tables** | Comprehensive enterprise hospital relational schema structure |
| **Active ORM Models** | **111 Registered Tables** | Fully synchronized SQLAlchemy tables validated with `scripts/check_database.py` |
| **Automated Test Suite** | **21+ Integration Tests** | Full PostgreSQL transaction-rollback tests (`tests/test_workflows.py`, `tests/test_milestone1_clinical_diagnostics.py`) |
| **Core Operations MVP** | **~80–85% Complete** | Complete end-to-end outpatient, inpatient, diagnostic, surgical, and financial workflows operational |

### Latest Milestones

- **Completed: Employee portal-role administration**:
  - The Admin Portal's **Granular Role-Permission Manager** supports employee-number/name search and department, sub-department, and employee filters.
  - Selecting an employee shows only their active roles. **Edit Roles** opens the available portal-role choices, and a confirmation dialog lists each role being added or removed before submission.
  - Administrators can add or remove multiple supported portal roles and save the employee's complete role assignment. Roles without an implemented employee portal are rejected by the API.
  - Only `admin` and `super_admin` can change assignments; only a `super_admin` can assign or modify the `super_admin` role, and administrators cannot remove their own final Admin Portal role.
- **Completed: Doctor-owned sequential OPD queue workflow**:
  - The doctor advances one patient at a time through `Waiting → Called → In Consultation → Completed`.
  - Only the first waiting patient has the **Call Next** action. Positions 2–10 display their numbered call order, while position 11 onward displays **Queued**.
  - A new patient cannot be called while another patient is called or in consultation. The called patient is started with **In-Room / Start**, and completing the EMR encounter automatically completes the associated queue token.
  - Reception queue actions are read-only and reflect doctor-driven changes. Its KPI cards filter patients into **Total In Queue** (second waiting patient onward), **Waiting for Next Call**, **In Consultation**, and **Completed**.
- **Completed: Milestone 1 (Clinical & Diagnostics — Migration 011)**:
  - Doctor review and digital acknowledgement of finalized lab results and radiology reports (`/doctor/reports/pending`, lab/radiology acknowledgements).
  - Radiology PACS multi-slice image series viewer (`/studies/{id}/viewer` & dark-theme viewer UI).
  - High-priority radiology critical finding alerts broadcast to ordering physicians.
  - Doctor follow-up appointment booking integrated into consultation completion.
  - Global Staff Notification Center with header bell, badge counter, and priority dropdown across all 8 staff portals.
- **Immediate Next: Milestone 2 (Acute Care & Inpatient Operations — Migration 012)**:
  - Multi-department discharge clearance gate (Doctor + Pharmacy + Nursing + Accounts 4-step sign-off).
  - Nursing MAR shift frequency codes (Q8H, Q12H, OD, BD, TID, PRN) and high-risk pre-admin vitals check.
  - Emergency fast-track unidentified patient registration and Mass-Casualty Incident (MCI) mode.
  - Surgery Central Sterile Services Department (CSSD) tray tracking, implant serial/lot capture, and Aldrete PACU recovery score.

