import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import CurrentUser, get_current_user
from app.config import get_db, settings
from main import app


@pytest.fixture
async def ambulance_client():
    engine = create_async_engine(settings.database_url)
    connection = await engine.connect()
    transaction = await connection.begin()
    session = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)()

    async def db_override():
        yield session

    async def user_override():
        return CurrentUser(user_id=uuid.uuid4(), employee_id=None, patient_id=None,
                           username="AMBULANCE-TEST", roles=["ambulance_staff"], name="Ambulance Test")

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
async def test_dispatch_assignment_tracking_arrival_and_completion(ambulance_client):
    client, db = ambulance_client
    patient = await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1"))
    vehicle = await db.scalar(text("SELECT ambulance_id FROM ambulance.ambulances WHERE current_status='Available' LIMIT 1"))
    priority = await db.scalar(text("SELECT dispatch_priority_id FROM ambulance.dispatch_priorities ORDER BY response_time_target_minutes LIMIT 1"))
    assert patient and vehicle and priority

    created = await client.post("/api/v1/ambulance/dispatches", json={
        "patient_id": str(patient), "request_source": "Emergency hotline",
        "emergency_type": "Road traffic injury", "pickup_location": "Main Street",
        "destination_location": "HMS Emergency Department"
    })
    assert created.status_code == 201, created.text
    request_id = created.json()["emergency_dispatch_request_id"]

    assigned = await client.post(f"/api/v1/ambulance/dispatches/{request_id}/assign", json={
        "ambulance_id": str(vehicle), "dispatch_priority_id": str(priority)
    })
    assert assigned.status_code == 201, assigned.text
    assignment_id = assigned.json()["dispatch_assignment_id"]

    location = await client.post(f"/api/v1/ambulance/assignments/{assignment_id}/location", json={
        "latitude": 6.9271, "longitude": 79.8612, "speed": 42
    })
    assert location.status_code == 201, location.text

    for status in ["En Route", "At Scene", "Patient Onboard", "Arrived", "Completed"]:
        response = await client.post(f"/api/v1/ambulance/assignments/{assignment_id}/status", json={
            "status": status, "notes": f"Status changed to {status}",
            "patient_condition": "Stable", "distance_km": 12.5 if status == "Completed" else None
        })
        assert response.status_code == 200, response.text

    assert await db.scalar(text("SELECT current_status FROM ambulance.ambulances WHERE ambulance_id=:id"), {"id": vehicle}) == "Available"
    assert await db.scalar(text("SELECT count(*) FROM emergency.emergency_arrivals WHERE patient_id=:id AND arrival_mode='Ambulance'"), {"id": patient}) >= 1
