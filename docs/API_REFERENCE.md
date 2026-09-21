# 📡 HMS Backend API Reference Documentation

Base URL: `http://localhost:8000/api/v1`  
Interactive Swagger Docs: `http://localhost:8000/docs`  
ReDoc Documentation: `http://localhost:8000/redoc`

---

## 1. Authentication (`/auth`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Authenticates employee by ID and password | `{ username, password }` | `{ token, roles, employee_id, name }` |
| `GET` | `/auth/roles` | Lists all available system roles | None | `[{ role_id, role_name }]` |
| `POST` | `/auth/change-password` | Updates password on initial login | `{ current_password, new_password }` | `{ message: "Password updated" }` |

---

## 2. Patient Management (`/patients`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/patients/masters` | Fetches dropdown options for Gender, Blood Group, Marital Status | None | `{ genders, blood_groups, marital_statuses }` |
| `POST` | `/patients/` | Registers new patient & auto-generates MRN | `PatientCreate` JSON | `PatientResponse` (includes `mrn`, `patient_code`) |
| `GET` | `/patients/` | Search & list patients (filter by Name, MRN, Phone) | `?q=...&skip=0&limit=50` | `List[PatientResponse]` |
| `GET` | `/patients/{patient_id}` | Fetches complete patient profile with contacts & emergency details | None | `PatientDetailResponse` |
| `PUT` | `/patients/{patient_id}` | Updates existing patient profile & contact numbers | `PatientUpdate` JSON | `PatientResponse` |

### Sample `POST /patients/` Payload:
```json
{
  "first_name": "John",
  "middle_name": "D.",
  "last_name": "Doe",
  "date_of_birth": "1990-05-15",
  "gender_id": 1,
  "blood_group_id": 1,
  "marital_status_id": 2,
  "phone": "+91 9876543210",
  "email": "john.doe@example.com",
  "address_line1": "Flat 402, Green Valley Apartments",
  "city": "Mumbai",
  "state": "Maharashtra",
  "postal_code": "400001",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_relation": "Spouse",
  "emergency_contact_phone": "+91 9876543211"
}
```

---

## 3. Doctor Management (`/doctor`)

| Method | Endpoint | Description | Request Body / Query | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/doctor/profile` | Fetches logged-in doctor's profile, qualifications, and schedules | `Authorization: Bearer <token>` | `DoctorProfileResponse` |
| `GET` | `/doctor/list` | Lists all active doctors with specializations | None | `List[DoctorSummaryResponse]` |
| `POST` | `/doctor/schedules` | Sets consultation availability and time slots | `DoctorScheduleCreate` | `DoctorScheduleResponse` |
| `POST` | `/doctor/qualifications` | Adds medical degree / certification | `QualificationCreate` | `QualificationResponse` |
| `POST` | `/doctor/leaves` | Submits doctor leave request | `LeaveRequestCreate` | `LeaveResponse` |

---

## 4. Departments & Sub-Departments (`/departments`, `/sub-departments`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/departments/` | Lists all core hospital departments | None | `List[DepartmentResponse]` |
| `POST` | `/departments/` | Creates a new hospital department | `{ department_code, department_name, description }` | `DepartmentResponse` |
| `GET` | `/departments/{id}` | Gets single department details | None | `DepartmentResponse` |
| `PUT` | `/departments/{id}` | Updates department metadata & status | `DepartmentUpdate` JSON | `DepartmentResponse` |
| `GET` | `/sub-departments/` | Lists all sub-departments / specializations | None | `List[SubDepartmentResponse]` |
| `POST` | `/sub-departments/` | Creates a sub-department linked to a parent department | `{ department_id, sub_department_code, sub_department_name }` | `SubDepartmentResponse` |

---

## 5. Employee Management (`/employees`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/employees/` | Lists all hospital employees | None | `List[EmployeeResponse]` |
| `POST` | `/employees/` | Creates a new employee & links user credentials | `EmployeeCreate` JSON | `EmployeeResponse` |
| `GET` | `/employees/{id}` | Fetches full employee profile | None | `EmployeeResponse` |
| `PUT` | `/employees/{id}` | Updates employee details | `EmployeeUpdate` JSON | `EmployeeResponse` |
| `DELETE` | `/employees/{id}` | Deactivates employee | None | `{ status: "success" }` |

---

## 6. Documents & Locations (`/documents`, `/locations`)

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/documents/upload` | Uploads employee or patient identity documents | `multipart/form-data` (file, type) | `DocumentResponse` |
| `GET` | `/documents/{id}` | Downloads uploaded document | None | File stream |
| `GET` | `/locations/countries` | Lists master countries | None | `List[CountryResponse]` |
| `GET` | `/locations/states` | Lists master states | `?country_id=...` | `List[StateResponse]` |

---

## 7. Laboratory (`/laboratory`)

| Method | Endpoint | Primary role | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/laboratory/tests` | Clinical/booking roles | List active laboratory tests and parameters |
| `GET` | `/laboratory/tests/{test_id}/parameter-rules` | Clinical staff | Resolve the current effective parameter rules for supplied patient context |
| `GET` | `/laboratory/booking-slots` | Patient/reception | List collection slots and capacity |
| `POST` | `/laboratory/bookings` | Patient/reception | Book tests and create source-linked billing |
| `GET` | `/laboratory/worklist` | Laboratory staff | View ordered and in-progress work |
| `POST` | `/laboratory/collect-sample` | Laboratory staff | Record barcode, specimen, and collection time |
| `POST` | `/laboratory/results` | Laboratory staff | Enter parameter results; request flags are non-authoritative |
| `GET` | `/laboratory/results/{result_entry_id}` | Authorized clinical staff | View a result entry and its parameters |
| `POST` | `/laboratory/results/{result_entry_id}/approve` | `pathologist` | Approve and release a laboratory report |

An entered result is not a final patient report. Only pathologist approval releases it. General doctors review released results and decide treatment; they do not approve laboratory reports.

## 8. Radiology (`/radiology`)

| Method | Endpoint | Primary role | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/radiology/tests` | Clinical/booking roles | List active imaging tests |
| `POST` | `/radiology/orders` | Doctor/reception | Create an imaging order |
| `GET` | `/radiology/worklist` | Radiology staff | View ordered, scheduled, and performed studies |
| `GET` | `/radiology/tests/{radiology_test_id}/observations` | Radiology staff | Load structured observations configured for an imaging test |
| `POST` | `/radiology/reports` | `radiologist` | Create, sign, and release the final report |
| `GET` | `/radiology/studies/{study_id}/viewer` | Authorized clinical staff | Load study metadata, images, and final report |
| `POST` | `/radiology/reports/{report_id}/acknowledge` | Treating doctor | Acknowledge a communicated critical finding |

Structured observations submitted with a report must belong to the test linked to the imaging order. Approval identity is derived from the authenticated radiologist, not selected by the browser.

See [Diagnostic workflow](DIAGNOSTIC_WORKFLOW.md) for lifecycle, release, notification, and auditing rules.
