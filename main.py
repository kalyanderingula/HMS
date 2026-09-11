from pathlib import Path
from app.api.billing import router as billing_router
from app.api.worklists import router as worklists_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.departments import router as departments_router
from app.api.sub_departments import router as sub_departments_router
from app.api.employees import router as employees_router
from app.api.documents import router as documents_router
from app.api.locations import router as locations_router
from app.api.auth import router as auth_router
from app.api.doctor import router as doctor_router
from app.api.patients import router as patients_router
from app.api.receptionist import router as receptionist_router
from app.api.emr import router as emr_router
from app.api.telemedicine import router as telemedicine_router
from app.api.pharmacy import router as pharmacy_router
from app.api.laboratory import router as laboratory_router
from app.api.radiology import router as radiology_router
from app.api.emergency import router as emergency_router
from app.api.inpatient import router as inpatient_router
from app.api.nursing import router as nursing_router
from app.api.surgery import router as surgery_router
from app.api.blood_bank import router as blood_bank_router
from app.api.patient_portal import router as patient_portal_router
from app.api.notifications import router as notifications_router
from app.api.rosters import router as rosters_router
from app.api.roles_permissions import router as roles_permissions_router

app = FastAPI(title="HMS - Hospital Management System", version="1.0.0")

ROOT = Path(__file__).resolve().parent
app.include_router(billing_router, prefix="/api/v1")
app.include_router(worklists_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(doctor_router, prefix="/api/v1")
app.include_router(receptionist_router, prefix="/api/v1")
app.include_router(emr_router, prefix="/api/v1")
app.include_router(telemedicine_router, prefix="/api/v1")
app.include_router(pharmacy_router, prefix="/api/v1")
app.include_router(laboratory_router, prefix="/api/v1")
app.include_router(radiology_router, prefix="/api/v1")
app.include_router(emergency_router, prefix="/api/v1")
app.include_router(inpatient_router, prefix="/api/v1")
app.include_router(nursing_router, prefix="/api/v1")
app.include_router(surgery_router, prefix="/api/v1")
app.include_router(blood_bank_router, prefix="/api/v1")
app.include_router(patient_portal_router, prefix="/api/v1")
app.include_router(departments_router, prefix="/api/v1")
app.include_router(sub_departments_router, prefix="/api/v1")
app.include_router(employees_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(locations_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(rosters_router, prefix="/api/v1")
app.include_router(roles_permissions_router, prefix="/api/v1")

# Serve static files (CSS, JS, assets)
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


# Login page
@app.get("/")
async def login_page():
    return FileResponse(ROOT / "frontend/html/index.html")


# Role-based pages
@app.get("/admin")
async def admin_page():
    return FileResponse(ROOT / "frontend/html/admin.html")


@app.get("/doctor")
async def doctor_page():
    return FileResponse(ROOT / "frontend/html/doctor.html")


@app.get("/receptionist")
async def receptionist_page():
    return FileResponse(ROOT / "frontend/html/receptionist.html")


@app.get("/nurse")
async def nurse_page():
    return FileResponse(ROOT / "frontend/html/nurse.html")


@app.get("/pharmacist")
async def pharmacist_page():
    return FileResponse(ROOT / "frontend/html/pharmacist.html")


@app.get("/lab")
async def laboratory_page():
    return FileResponse(ROOT / "frontend/html/lab.html")


@app.get("/radiology")
async def radiology_page():
    return FileResponse(ROOT / "frontend/html/radiology.html")


@app.get("/accounts")
async def accounts_page():
    return FileResponse(ROOT / "frontend/html/accounts.html")


@app.get("/blood-bank")
async def blood_bank_page():
    return FileResponse(ROOT / "frontend/html/blood-bank.html")


@app.get("/emergency")
async def emergency_page():
    return FileResponse(ROOT / "frontend/html/emergency.html")


@app.get("/surgery")
async def surgery_page():
    return FileResponse(ROOT / "frontend/html/surgery.html")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
