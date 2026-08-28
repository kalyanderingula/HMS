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
    subgraph Users & Role Portals
        REC[🗂️ Receptionist<br/>/receptionist]
        DOC[🩺 Doctor<br/>/doctor]
        ADM[⚙️ Admin / HR<br/>/admin]
    end

    subgraph Presentation Layer
        HTML[frontend/html/<br/>index, receptionist, doctor, admin]
        CSS[frontend/css/<br/>login.css, receptionist.css, admin.css]
        JS[frontend/js/<br/>login.js, receptionist.js, doctor.js, admin.js]
    end

    subgraph API Gateway & Routers (FastAPI)
        AUTH[/api/v1/auth]
        PAT[/api/v1/patients]
        DOCTOR[/api/v1/doctor]
        DEPT[/api/v1/departments]
        EMP[/api/v1/employees]
        DOCS[/api/v1/documents]
    end

    subgraph Relational Database (PostgreSQL 14+)
        CORE[(core: Departments, Master Types)]
        HR[(human_resources: Employees, Staff)]
        PAT_DB[(patient: Patients, Contacts, Addresses)]
        DOC_DB[(doctor: Doctors, Schedules)]
        CLINICAL[(EMR, Appointments, Billing, Pharmacy, Labs)]
    end

    REC --> HTML
    DOC --> HTML
    ADM --> HTML
    HTML & CSS & JS --> AUTH & PAT & DOCTOR & DEPT & EMP & DOCS
    AUTH & PAT & DOCTOR & DEPT & EMP & DOCS --> CORE & HR & PAT_DB & DOC_DB & CLINICAL
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
│   └── migrations/             # Migration scripts
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

* **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Web Login Portal:** [http://localhost:8000/](http://localhost:8000/)
* **Receptionist Desk:** [http://localhost:8000/receptionist](http://localhost:8000/receptionist)
* **Doctor Portal:** [http://localhost:8000/doctor](http://localhost:8000/doctor)
* **Admin Dashboard:** [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 🧪 Current Status & Next Steps

* ✅ **Database Normalization:** All 35 SQL schema files verified with 0 circular dependencies and 0 broken foreign keys.
* ✅ **Master Data Integration:** `core.departments` and `core.master_document_types` centralized.
* ✅ **Patient Management (Step 1):** End-to-end patient registration, auto-generated MRN, contact management, and live search completed.
* 🚀 **Next Up (Step 2):** Appointment Booking & Doctor Daily Queue Management.
