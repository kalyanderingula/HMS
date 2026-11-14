import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import CurrentUser, get_current_user
from app.config import get_db, settings
from main import app


@pytest.fixture
async def icu_client():
    engine = create_async_engine(settings.database_url)
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()

    async def db_override():
        yield session

    async def user_override():
        return CurrentUser(user_id=uuid.uuid4(), employee_id=None, patient_id=None,
                           username="ICU-TEST", roles=["doctor", "icu_doctor"], name="ICU Doctor Test")

    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session
    app.dependency_overrides.clear()
    await session.close()
    await transaction.rollback()
    await connection.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_icu_admission_vitals_round_alert_and_discharge(icu_client):
    client, db = icu_client
    patient = await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1"))
    bed = await db.scalar(text("SELECT icu_bed_id FROM intensive_care_unit.icu_beds WHERE bed_status='Available' LIMIT 1"))
    triage = await db.scalar(text("SELECT triage_level_id FROM intensive_care_unit.icu_triage_levels ORDER BY severity_rank LIMIT 1"))
    assert patient and bed and triage

    response = await client.post("/api/v1/icu/admissions", json={
        "patient_id": str(patient), "icu_bed_id": str(bed), "triage_level_id": str(triage),
        "criticality_level": "Critical", "primary_diagnosis": "Respiratory failure",
        "admission_source": "Emergency", "admission_reason": "Requires organ support"
    })
    assert response.status_code == 201, response.text
    admission = response.json()["icu_admission_id"]

    vitals = await client.post(f"/api/v1/icu/admissions/{admission}/vitals", json={
        "temperature": 38.2, "pulse_rate": 118, "respiratory_rate": 30,
        "systolic_bp": 75, "diastolic_bp": 45, "oxygen_saturation": 86
    })
    assert vitals.status_code == 201 and vitals.json()["critical_alert_created"] is True
    assert (await client.post(f"/api/v1/icu/admissions/{admission}/rounds", json={"round_notes": "Reviewed by ICU team"})).status_code == 201
    assert (await client.post(f"/api/v1/icu/admissions/{admission}/ventilator", json={"ventilator_device_id": "VENT-01", "ventilation_mode": "Assist Control"})).status_code == 201

    chart = (await client.get(f"/api/v1/icu/admissions/{admission}")).json()
    assert chart["vitals"] and chart["rounds"] and chart["alerts"]
    alert = chart["alerts"][0]
    assert (await client.post(f"/api/v1/icu/alerts/{alert['source']}/{alert['alert_id']}/acknowledge")).status_code == 200
    discharged = await client.post(f"/api/v1/icu/admissions/{admission}/discharge", json={"discharge_condition": "Stable", "discharge_summary": "Transferred to ward"})
    assert discharged.status_code == 200, discharged.text
