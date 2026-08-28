# 🎨 Frontend Architecture Documentation

The HMS frontend is organized into **role-specific portals** with a clean separation of **HTML pages, CSS stylesheets, and JavaScript modules**.

---

## 1. Directory Structure

```
frontend/
├── html/                   # Clean HTML templates for each portal
│   ├── index.html          # Authentication & Login Page
│   ├── receptionist.html   # 🗂️ Receptionist Desk & Patient Portal
│   ├── doctor.html         # 🩺 Doctor Consultation Portal
│   └── admin.html          # ⚙️ Administrator & HR Portal
│
├── css/                    # Modular stylesheets
│   ├── login.css           # Sign-in card & role selection styles
│   ├── receptionist.css    # Reception desk & directory tables
│   └── admin.css           # Master tables, forms, modals, badges, toast
│
└── js/                     # Client-side JavaScript controllers
    ├── login.js            # Authentication, JWT storage, role router
    ├── receptionist.js     # Patient CRUD, live search, profile cards
    ├── doctor.js           # Doctor profile, schedules, password change
    └── admin.js            # Department & Employee management controllers
```

---

## 2. Role-Based Portals

| Route | HTML Template | Primary Users | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | `html/index.html` | All staff | Login and role selection interface |
| `/receptionist` | `html/receptionist.html` | Receptionists | Patient registration, live directory search, MRN issuance |
| `/doctor` | `html/doctor.html` | Doctors, Specialists | Doctor consultation desk, schedule management, profile details |
| `/admin` | `html/admin.html` | Administrators, HR | Managing departments, sub-departments, staff accounts, documents |

---

## 3. Client-Side Authentication Flow

1. User enters employee credentials on `/`.
2. Backend returns JWT token and authorized roles array (`['receptionist', 'admin']`).
3. Tokens are saved in browser `localStorage`:
   - `hms_token`: Bearer authentication token.
   - `hms_roles`: JSON array of user roles.
   - `hms_name`: Full name of logged-in staff.
4. If user has multiple roles, `login.js` displays a visual **Role Picker**.
5. Once selected, the user is redirected to their dedicated portal (`/receptionist`, `/doctor`, `/admin`).
6. Each portal verifies `localStorage` on page load; unauthenticated requests are redirected back to `/`.

---

## 4. UI Design System & Component Library

* **CSS Variables:** Consistent primary blue (`#2563eb`), dark slate headers (`#1e293b`), subtle borders (`#e2e8f0`), and soft background fills (`#f8fafc`).
* **Interactive Data Tables:** Standardized headers, hover rows, status badges (`.badge-active`, `.badge-inactive`), and action buttons (`.btn-view`, `.btn-danger`).
* **Live Search Bars:** Debounced instant client-side filtering by Name, Phone, MRN, or Department code.
* **Floating Toast Notifications:** Non-blocking success/error toast alerts (`#toast`).
