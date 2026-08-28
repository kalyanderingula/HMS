# ??? HMS — In-Depth Development Roadmap (Solo Developer)

> This is the **real, complete vision** of the HMS system — a full-stack, AI-agentic hospital platform where every patient, doctor, and employee has a conversational AI assistant that understands their role, their context, and their needs.

---

## ?? The Core Vision: AI-Agentic HMS

Unlike a basic CRUD hospital system, HMS is designed as an **AI-first hospital operating system**. Every person who walks into the hospital — or logs into the system — gets their own contextual AI agent:

| Who | What the Agent Does |
| :--- | :--- |
| ???????? **Patient (at kiosk/mobile)** | Chat-based self-registration, symptom collection, auto-routing to the right doctor/department, appointment booking — all in natural language, no forms. |
| ??? **Receptionist** | AI co-pilot that auto-fills patient forms from conversation, checks doctor availability in real-time, suggests next steps, flags duplicates. |
| ?? **Doctor** | Clinical AI that summarizes patient history before consultation, suggests differential diagnoses based on vitals/symptoms, auto-drafts prescriptions. |
| ?? **Pharmacist** | Agent that reads incoming prescriptions, checks drug-drug interactions, alerts low stock, suggests generics. |
| ?? **Lab Technician** | Reads pending lab orders, flags abnormal ranges on results, alerts the ordering doctor automatically. |
| ??? **Admin / HR** | AI that answers HR policy questions, helps with employee onboarding flows, generates reports on demand. |

---

## ??? System Architecture Overview

```
+---------------------------------------------------------------------+
¦                        HMS SYSTEM ARCHITECTURE                       ¦
+---------------------------------------------------------------------¦
¦  FRONTEND (Role Portals)¦  AI Agent Layer                           ¦
¦  ---------------------  ¦  -----------------------------------------¦
¦  html/index.html        ¦  Patient Agent (Gemini Flash / Ollama)    ¦
¦  html/receptionist.html ¦  Receptionist Agent                       ¦
¦  html/doctor.html       ¦  Doctor Clinical Agent                    ¦
¦  html/pharmacy.html     ¦  Pharmacist Agent                         ¦
¦  html/lab.html          ¦  Lab Tech Agent                           ¦
¦  html/admin.html        ¦  Admin / HR Agent                         ¦
+---------------------------------------------------------------------¦
¦                FastAPI Backend (main.py / app/)                      ¦
¦  /api/v1/patients   /api/v1/appointments  /api/v1/consultations      ¦
¦  /api/v1/pharmacy   /api/v1/lab           /api/v1/billing            ¦
¦  /api/v1/chat       <- AI Agent Endpoints (RAG + Tool Calling)       ¦
+---------------------------------------------------------------------¦
¦  RAG Pipeline (Free / Low Cost Stack)                                ¦
¦  -----------------------------------------------------------------  ¦
¦  ChromaDB (Local Vector DB) <- Embed hospital knowledge              ¦
¦  Sentence-Transformers (FREE embeddings - no subscription needed)    ¦
¦  Gemini Flash / Ollama (LLaMA 3.2 local) <- LLM reasoning           ¦
¦  LangChain / LlamaIndex <- Orchestration                            ¦
+---------------------------------------------------------------------¦
¦  PostgreSQL 14+ (35 Domain Schemas, 1,050 Tables)                   ¦
¦  core | patient | doctor | appointment | EMR | pharmacy | billing    ¦
+---------------------------------------------------------------------+
```

---

## ?? Phase-by-Phase Build Plan

---

### ? Phase 1: Core Foundation & Patient Management *(DONE)*

**Goal:** Build the backbone — database, backend models, frontend portals.

- [x] Audit & normalize all 35 SQL schema files (1,050 tables, 33 schemas).
- [x] Establish `core.departments` as Single Source of Truth.
- [x] `01_FOREIGN_KEYS_AND_INDEXES.sql` — cross-schema FK integrity + performance indexes.
- [x] `Patient` SQLAlchemy model + Pydantic schemas + FastAPI CRUD endpoints.
- [x] Modularize frontend: `html/`, `css/`, `js/`.
- [x] Dedicated **Receptionist Desk Portal** (`receptionist.html`) with live search and auto-MRN.

---

### ?? Phase 2: Appointments & Doctor Queue *(Next)*

**Goal:** Allow receptionists to book appointments and give doctors a real-time patient queue.

#### 2A — Backend
- [ ] `app/models/appointment.py` — Map `appointment.appointments`, `appointment_slots`, `doctor_availability`.
- [ ] `app/api/appointments.py` — Endpoints:
  - `GET /api/v1/doctors/available?date=&department_id=` — Returns available doctors + free slots.
  - `POST /api/v1/appointments/` — Book appointment (patient + doctor + slot).
  - `GET /api/v1/appointments/doctor/{doctor_id}/queue?date=today` — Daily patient queue list.
  - `PUT /api/v1/appointments/{id}/status` — Update to `Checked-In`, `In Consultation`, `Completed`, `No-Show`.

#### 2B — Frontend
- [ ] `receptionist.html` — Add **"Book Appointment" tab**:
  - Search and select patient by MRN.
  - Filter doctors by department/specialty.
  - Show available time slots calendar.
  - Confirm and print appointment slip.
- [ ] `doctor.html` — Add **"Today's Queue" section**:
  - Shows all patients with status badges.
  - "Call Next Patient" button updates status in real-time.

---

### Phase 3: Doctor Consultation & Electronic Medical Records (EMR)

**Goal:** When a patient sits with the doctor, the entire clinical workflow happens in the system.

#### 3A — Backend
- [ ] Models: `PatientEncounter`, `VitalSign`, `ClinicalNote`, `Diagnosis`, `Prescription`, `PrescriptionItem`.
- [ ] APIs:
  - `POST /api/v1/consultations/start` — Opens an encounter linked to the appointment.
  - `POST /api/v1/consultations/{id}/vitals` — Record BP, pulse, temp, weight, SpO2.
  - `POST /api/v1/consultations/{id}/diagnosis` — Attach ICD-10 codes + free-text notes.
  - `POST /api/v1/consultations/{id}/prescriptions` — Add medication rows (drug, dose, frequency, days).
  - `POST /api/v1/consultations/{id}/lab-orders` — Order lab tests.
  - `POST /api/v1/consultations/{id}/close` — Finalize encounter, generate EMR summary.
  - `GET /api/v1/patients/{id}/history` — Full clinical timeline.

#### 3B — Frontend
- [ ] `doctor.html` — Clinical workspace:
  - Patient summary sidebar (Name, DOB, Blood Group, Allergies, Last visit).
  - Vitals input grid.
  - Diagnosis text area + ICD-10 code search.
  - Prescription builder (add rows: medicine, dosage, duration).
  - Lab order selector.
  - "Finalize & Send to Pharmacy/Lab" button.

---

### Phase 4: Pharmacy & Laboratory

**Goal:** Complete the clinical loop — ordered medicines get dispensed, lab results come back to the doctor.

#### Pharmacy
- [ ] Drug inventory catalog (drug name, batch, expiry, stock count).
- [ ] Incoming prescription queue from consultations.
- [ ] Dispense workflow: Pharmacist marks drugs as dispensed.
- [ ] Drug-drug interaction alerts.
- [ ] Low stock alerts.
- [ ] Portal: `html/pharmacy.html`.

#### Laboratory
- [ ] Pending test orders queue.
- [ ] Specimen collection log.
- [ ] Result entry form with reference range validation.
- [ ] Auto-flag abnormal values (HIGH / LOW / CRITICAL).
- [ ] Auto-notify ordering doctor when results are ready.
- [ ] Portal: `html/lab.html`.

---

### Phase 5: Billing, Invoicing & Insurance

- [ ] Auto-generate invoice from: consultation fee + medicines + lab tests + procedures.
- [ ] Payment modes: Cash, Card, UPI, Insurance.
- [ ] Insurance claim document generation.
- [ ] Discharge summary: Final bill + clinical summary.
- [ ] Portal: `html/billing.html`.

---

### Phase 6: RAG Knowledge Base *(No expensive subscription needed)*

**Goal:** Feed all hospital knowledge into a local vector database so AI agents can answer questions accurately.

#### What gets embedded into RAG:

| Knowledge Type | Source | Used By |
| :--- | :--- | :--- |
| Hospital departments and services | Departments table | Patient agent (routing queries) |
| Doctor profiles, specialties, availability | Doctor table | Patient & Receptionist agents |
| Drug formulary (generic names, interactions, side effects) | Pharmacy catalog | Pharmacist & Doctor agents |
| Lab test catalog (test names, normal ranges, sample type) | Lab catalog | Lab tech & Doctor agents |
| Hospital policies, SOPs | Uploaded PDF/DOCX docs | Admin & HR agents |
| ICD-10 disease codes & descriptions | CSV file (public domain) | Doctor agent |
| Discharge summaries & clinical notes | EMR (patient-specific) | Doctor agent (patient history) |

#### Free Stack for RAG:

```
Embeddings:    sentence-transformers/all-MiniLM-L6-v2  (100% free, runs locally)
Vector DB:     ChromaDB                                (100% free, runs locally)
LLM:           Google Gemini Flash (free tier - 1M tokens/month)  OR
               Ollama + LLaMA 3.2 (100% offline, completely free)
Orchestration: LangChain (free open source)
```

#### Implementation Steps:
- [ ] `pip install chromadb sentence-transformers langchain`
- [ ] `app/rag/embedder.py` — Load and chunk knowledge documents, embed them into ChromaDB.
- [ ] `app/rag/retriever.py` — Similarity search against ChromaDB using user query.
- [ ] `app/rag/context_builder.py` — Fetch live DB data + inject into prompt.
- [ ] `app/api/chat.py` — FastAPI endpoint `POST /api/v1/chat` receives messages, routes to correct agent.

---

### Phase 7: Agentic AI — Role-Based AI Assistants

**Goal:** Every portal gets a chat widget backed by an agent with real tool-calling capabilities.

---

#### ???????? Patient Self-Service Agent (Kiosk / Mobile Chat)

Patient walks into hospital and opens the kiosk chat:

```
Patient: "I have chest pain and shortness of breath for 3 days"

Agent:   "I'm sorry to hear that. Are you a first-time visitor?
          [Yes / No, I have an MRN]"

Patient: "First time"

Agent:   "Can I have your name and phone number?"
          ? Calls register_patient() ? creates record in DB

Agent:   "Based on your symptoms, you should see a Cardiologist.
          Dr. Anand Sharma is available today at 3:00 PM and 4:00 PM.
          Which slot do you prefer?"
          ? Calls search_doctor(symptom="chest pain", date="today")

Patient: "3 PM"

Agent:   "Done! Appointment confirmed for 3:00 PM with Dr. Anand Sharma.
          Your Queue Token: C-014. Please proceed to Cardiology, Floor 2."
          ? Calls book_appointment(patient_id, doctor_id, slot_id)
```

**Tools this agent calls:**
- `register_patient(name, phone, dob, gender)` ? POST /api/v1/patients/
- `search_doctor(symptom_or_speciality, date)` ? GET /api/v1/doctors/available
- `book_appointment(patient_id, doctor_id, slot_id)` ? POST /api/v1/appointments/
- `get_department_info(name)` ? Returns location, floor, hours
- `check_appointment_status(mrn)` ? Returns queue position

---

#### ??? Receptionist AI Co-Pilot

```
Receptionist: "New patient — Ramesh Kumar, 45 yrs, male, chest pain"

Agent:   "Auto-detected: Mr. Ramesh Kumar, 45M.
          Recommended: Cardiology Department.
          Dr. Priya is free at 11:30 AM today.
          Shall I register and book? (Phone number?)"

Receptionist: "Yes, 9876543210"

Agent:   ? Registers patient ? Books appointment ? Issues token
         "Done. MRN: MRN-2026-00042 | Token: C-008 | Dr. Priya 11:30 AM"
```

---

#### ?? Doctor Clinical Agent

Before patient enters, doctor asks:

```
Doctor: "Summarize last 3 visits for MRN-2026-00012"

Agent:  "Patient: Ravi Sharma, 52M, Diabetic, HTN
         12-Jul-2026: BP 160/100, Dx: Hypertension (I10)
           Rx: Amlodipine 5mg OD, Telmisartan 40mg OD
         03-Mar-2026: HbA1c 8.2%, Dx: T2DM
           Rx: Metformin 500mg BD, Glipizide 5mg OD
         Labs Pending: CBC, Lipid Profile (ordered 12-Jul, not uploaded yet)"

Doctor: "Add vitals: BP 140/90, pulse 82, Temp 98.6"
Agent:  ? Saves to encounter in DB

Doctor: "His knee pain is worse. Differentials?"
Agent:  "For 52M diabetic with knee pain:
         1. Osteoarthritis (most likely, age + metabolic syndrome)
         2. Gout (elevated uric acid common in T2DM + HTN)
         3. Diabetic peripheral neuropathy
         Recommend: Uric Acid, ESR, X-Ray Knee AP/Lateral"

Doctor: "Order those labs and add Etoricoxib 60mg OD for 5 days"
Agent:  ? Orders labs ? Updates prescription
        "Done. Labs ordered, prescription updated."
```

---

#### ?? Pharmacist Agent

```
Pharmacist: "Show pending prescriptions since morning"

Agent:  "4 pending:
         1. MRN-00042: Amlodipine 5mg (30), Telmisartan 40mg (30)
            ?? Stock Alert: Telmisartan = only 8 units left
         2. MRN-00051: Metformin 500mg (60) — In stock ?"

Pharmacist: "Dispense order 1, substitute Telmisartan"

Agent:  "Generic alternative: Telma-H 40mg by Cipla (12 in stock).
         Shall I substitute and dispense?"
```

---

### Phase 8: AI Infrastructure (100% Free Stack)

| Component | Tool | Cost |
| :--- | :--- | :--- |
| **LLM (cloud, free tier)** | Google Gemini Flash 2.0 | Free (1M tokens/month) |
| **LLM (fully offline)** | Ollama + Llama 3.2 3B | Free (runs on 8GB RAM) |
| **Embeddings** | sentence-transformers all-MiniLM-L6-v2 | Free |
| **Vector DB** | ChromaDB (local, persistent) | Free |
| **Orchestration** | LangChain Community | Free |
| **Speech Input** | OpenAI Whisper (local model) | Free |
| **Chat UI** | Vanilla JS custom widget | Free |
| **Database** | PostgreSQL (existing) | Free |

---

## ?? Complete Build Order Summary

| Phase | What | Key Output | Status |
| :--- | :--- | :--- | :--- |
| 1 | Database + Patient Backend + Portals | All 35 schemas, `/patients` API, Receptionist Portal | ? Done |
| 2 | Appointments & Doctor Queue | `/appointments` API, Booking UI, Doctor Queue | ?? Next |
| 3 | Consultations & EMR | Clinical workspace, Vitals, Diagnosis, Prescriptions | ? Planned |
| 4 | Pharmacy & Lab | Dispensing queue, Lab results, Alerts | ? Planned |
| 5 | Billing & Discharge | Auto-invoice, Insurance claims, Discharge summary | ? Planned |
| 6 | RAG Knowledge Base | ChromaDB + embeddings + hospital knowledge indexed | ? Planned |
| 7 | AI Agents — All Roles | Patient kiosk, Receptionist co-pilot, Doctor clinical, Pharmacist, Lab, Admin | ? Planned |
| 8 | Advanced AI | Voice input, multi-language, proactive alerts, predictive triaging | ? Planned |

> **Golden Rule:** Always build the **real data and APIs first** (Phases 2–5), then layer the AI agents on top (Phases 6–8). An AI agent is only as smart as the live database it can READ and WRITE from. Without real appointment, prescription, and lab data flowing through the APIs, the agents have nothing meaningful to act on.
