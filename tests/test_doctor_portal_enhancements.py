"""Integration tests for Doctor Portal & Telemedicine Enhancements."""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from main import app
from app.config import get_db, settings
from app.api.auth import CurrentUser, get_current_user, User
from app.models.patient import Patient
from app.api.doctor import Doctor, DoctorProfile, DoctorConsultationFee
from app.models.emr_models import (
    VirtualAppointment, VideoConsultationSession, PatientEncounter, EncounterType, SOAPNote, Diagnosis, Prescription
)
from app.models.specialized_ops_models import VideoRoom


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
        admin = await session.scalar(select(User).where(User.status == "active"))
        assert admin, "An active seeded user is required"

        async def db_override():
            yield session

        async def user_override():
            return CurrentUser(
                user_id=admin.user_id,
                username=admin.username,
                employee_id=admin.employee_id,
                roles=["super_admin", "doctor", "telemedicine_doctor"],
                name="Dr. Senior Consultant"
            )

        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[get_current_user] = user_override
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
                yield c, session
        finally:
            app.dependency_overrides.clear()
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_doctor_self_profile_update(client):
    """Test doctor self-profile update endpoint (PUT /api/v1/doctor/my-profile)."""
    c, session = client

    payload = {
        "phone": "+91 99887 76655",
        "email": "doctor.updated@hospital.com",
        "consultation_experience_years": 15,
        "consultation_fee": 750.0,
        "biography": "Senior Consultant Physician with extensive experience in cardio-metabolic care.",
        "linkedin_url": "https://linkedin.com/in/doctor-profile",
        "website_url": "https://doctorclinic.org"
    }

    res = await c.put("/api/v1/doctor/my-profile", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "Doctor profile updated successfully" in data["message"]
    assert data["updated_fields"]["phone"] == "+91 99887 76655"
    assert data["updated_fields"]["consultation_fee"] == 750.0
    assert data["updated_fields"]["consultation_experience_years"] == 15


@pytest.mark.asyncio
async def test_patient_clinical_history_retrieval(client):
    """Test comprehensive patient clinical history endpoint (GET /api/v1/doctor/patients/{id}/clinical-history)."""
    c, session = client

    # Find or seed a patient
    patient = await session.scalar(select(Patient).limit(1))
    if not patient:
        patient = Patient(
            mrn=f"MRN-{uuid.uuid4().hex[:6].upper()}",
            first_name="Anita",
            last_name="Desai",
            gender="Female",
            date_of_birth=datetime(1985, 4, 12).date(),
            blood_group="B+",
            contact_number="9876543210"
        )
        session.add(patient)
        await session.flush()

    res = await c.get(f"/api/v1/doctor/patients/{patient.patient_id}/clinical-history")
    assert res.status_code == 200, res.text
    data = res.json()

    assert "patient" in data
    assert "consultations" in data
    assert "laboratory_results" in data
    assert "radiology_reports" in data
    assert "vitals_timeline" in data
    assert data["patient"]["patient_id"] == str(patient.patient_id)
    assert data["patient"]["mrn"] == patient.mrn


@pytest.mark.asyncio
async def test_diagnostic_reports_workspace_scopes(client):
    """Test diagnostic reports with scope filters and search parameter."""
    c, session = client

    # 1. Pending scope
    res_pending = await c.get("/api/v1/doctor/reports?scope=pending")
    assert res_pending.status_code == 200, res_pending.text
    data_pending = res_pending.json()
    assert "laboratory_reports" in data_pending
    assert "radiology_reports" in data_pending

    # 2. Ordered by me scope
    res_ordered = await c.get("/api/v1/doctor/reports?scope=ordered_by_me")
    assert res_ordered.status_code == 200, res_ordered.text
    data_ordered = res_ordered.json()
    assert "laboratory_reports" in data_ordered

    # 3. All scope with search query
    res_all = await c.get("/api/v1/doctor/reports?scope=all&q=test")
    assert res_all.status_code == 200, res_all.text


@pytest.mark.asyncio
async def test_telemedicine_video_room_and_in_session_orders(client):
    """Test WebRTC video room launcher and live in-session clinical order placement."""
    c, session = client

    patient = await session.scalar(select(Patient).limit(1))
    doctor = await session.scalar(select(Doctor).limit(1))

    if not patient or not doctor:
        pytest.skip("Patient or Doctor seed required")

    # Schedule virtual appointment
    apt_payload = {
        "patient_id": str(patient.patient_id),
        "doctor_id": str(doctor.doctor_id),
        "appointment_datetime": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "meeting_platform": "HMS Telehealth",
        "chief_complaint": "Follow-up consultation for respiratory symptoms"
    }
    apt_res = await c.post("/api/v1/telemedicine/appointments", json=apt_payload)
    assert apt_res.status_code == 201, apt_res.text
    apt_data = apt_res.json()
    apt_id = apt_data["virtual_appointment_id"]

    # Launch video room
    room_res = await c.post(f"/api/v1/telemedicine/appointments/{apt_id}/video-room")
    assert room_res.status_code == 201, room_res.text
    room_data = room_res.json()
    assert room_data["virtual_appointment_id"] == apt_id
    assert "meet.hmshospital.com" in room_data["room_url"]
    assert room_data["is_active"] is True

    # Start session
    sess_res = await c.post("/api/v1/telemedicine/sessions/start", json={"virtual_appointment_id": apt_id})
    assert sess_res.status_code == 201, sess_res.text
    sess_id = sess_res.json()["session_id"]

    # Place in-session order
    order_payload = {
        "order_type": "e-prescription",
        "details": "Amoxicillin 500mg TDS for 5 days post-food",
        "item_catalog_ids": []
    }
    order_res = await c.post(f"/api/v1/telemedicine/sessions/{sess_id}/orders", json=order_payload)
    assert order_res.status_code == 201, order_res.text
    order_data = order_res.json()
    assert order_data["order_type"] == "e-prescription"
    assert "successfully placed" in order_data["message"]

