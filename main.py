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

app = FastAPI(title="HMS - Hospital Management System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(doctor_router, prefix="/api/v1")
app.include_router(departments_router, prefix="/api/v1")
app.include_router(sub_departments_router, prefix="/api/v1")
app.include_router(employees_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(locations_router, prefix="/api/v1")

# Serve static files (CSS, JS, assets)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# Login page
@app.get("/")
async def login_page():
    return FileResponse("frontend/html/index.html")


# Role-based pages
@app.get("/admin")
async def admin_page():
    return FileResponse("frontend/html/admin.html")


@app.get("/doctor")
async def doctor_page():
    return FileResponse("frontend/html/doctor.html")


@app.get("/receptionist")
async def receptionist_page():
    return FileResponse("frontend/html/receptionist.html")


@app.get("/nurse")
@app.get("/pharmacist")
@app.get("/lab")
@app.get("/radiology")
@app.get("/accounts")
@app.get("/ambulance")
@app.get("/blood-bank")
@app.get("/dietetics")
@app.get("/rehabilitation")
@app.get("/housekeeping")
@app.get("/inventory")
@app.get("/mortuary")
@app.get("/crm")
@app.get("/emergency")
@app.get("/visitor")
async def role_page():
    # Fallback for other roles until their dedicated pages are built
    return FileResponse("frontend/html/admin.html")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
