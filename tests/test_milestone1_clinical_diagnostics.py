"""Integration tests for Milestone 1: Clinical & Diagnostics Completion."""
import uuid
from datetime import date, datetime, timedelta
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from main import app
from app.config import get_db, settings
from app.api.auth import CurrentUser, get_current_user, User
from app.models.radiology_models import ImagingStudy, RadiologyReport, ImagingStudyImage
from app.models.laboratory_models import LabResultEntry


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
                roles=["super_admin", "doctor", "radiologist"],
                name="Dr. Test Specialist"
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
async def test_notifications_lifecycle(client):
    c, session = client

    # 1. Insert a test notification
    notif_id = uuid.uuid4()
    admin = await session.scalar(select(User).where(User.status == "active"))
    await session.execute(
        text("""INSERT INTO core.notifications
                (notification_id, recipient_id, recipient_type, source_module, subject, body, status)
                VALUES (:id, :recipient, 'User', 'Laboratory', '🚨 Critical potassium alert', 'Serum potassium 6.8 mEq/L', 'pending')"""),
        {"id": notif_id, "recipient": admin.user_id}
    )

    # 2. Fetch notifications
    res = await c.get("/api/v1/notifications/my")
    assert res.status_code == 200
    data = res.json()
    assert data["unread_count"] >= 1
    found = [n for n in data["notifications"] if n["notification_id"] == str(notif_id)]
    assert len(found) == 1
    assert found[0]["is_urgent"] is True

    # 3. Mark as read
    read_res = await c.post(f"/api/v1/notifications/{notif_id}/read")
    assert read_res.status_code == 200

    # 4. Verify unread status updated
    res2 = await c.get("/api/v1/notifications/my")
    found2 = [n for n in res2.json()["notifications"] if n["notification_id"] == str(notif_id)]
    assert found2[0]["status"] == "read"

    # 5. Mark all read
    all_read = await c.post("/api/v1/notifications/read-all")
    assert all_read.status_code == 200


@pytest.mark.asyncio
async def test_radiology_critical_alert_and_pacs_viewer(client):
    c, session = client

    # Find or create a patient
    pid = await session.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1"))
    assert pid, "A test patient is required"

    # Create imaging study
    study_id = uuid.uuid4()
    accession = f"ACC-TEST-{uuid.uuid4().hex[:8].upper()}"
    uid = f"1.2.840.10008.{uuid.uuid4().hex}"
    await session.execute(
        text("""INSERT INTO radiology.imaging_studies
                (study_id, study_instance_uid, accession_number, patient_id, study_description, study_date)
                VALUES (:id, :uid, :acc, :pid, 'Chest CT with Contrast', CURRENT_TIMESTAMP)"""),
        {"id": study_id, "uid": uid, "acc": accession, "pid": pid}
    )

    # Attach PACS slices
    slice_res = await c.post(f"/api/v1/radiology/studies/{study_id}/images", json={
        "image_url": "https://pacs.example.internal/studies/101/slice1.dcm",
        "slice_description": "Axial mediastinal window at carina",
        "series_number": 1,
        "instance_number": 1,
        "is_key_image": True,
        "modality_code": "CT"
    })
    assert slice_res.status_code == 201
    assert slice_res.json()["is_key_image"] is True

    # Submit Final Report with Critical Alert
    rep_res = await c.post("/api/v1/radiology/reports", json={
        "study_id": str(study_id),
        "findings": "Large saddle pulmonary embolism extending into left main pulmonary artery.",
        "impression": "Massive pulmonary embolism requiring immediate intervention.",
        "is_critical": True,
        "critical_alert_details": "Immediate thrombectomy/anticoagulation alert"
    })
    assert rep_res.status_code == 201
    report_data = rep_res.json()
    assert report_data["is_critical"] is True
    report_id = report_data["report_id"]

    # Verify PACS viewer endpoint returns study slices and critical report
    viewer_res = await c.get(f"/api/v1/radiology/studies/{study_id}/viewer")
    assert viewer_res.status_code == 200
    vdata = viewer_res.json()
    assert vdata["accession_number"] == accession
    assert len(vdata["images"]) >= 1
    assert vdata["report"] is not None
    assert vdata["report"]["is_critical"] is True

    # Digital doctor acknowledgement
    ack_res = await c.post(f"/api/v1/radiology/reports/{report_id}/acknowledge", params={"notes": "Reviewed and alerted ICU team"})
    assert ack_res.status_code == 200
    assert ack_res.json()["message"] == "Radiology report acknowledged successfully"


@pytest.mark.asyncio
async def test_doctor_pending_reports_and_follow_up(client):
    c, session = client

    pid = await session.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1"))
    assert pid, "A test patient is required"

    # Fetch pending reports
    pending_res = await c.get(f"/api/v1/doctor/reports/pending?patient_id={pid}")
    assert pending_res.status_code == 200
    pdata = pending_res.json()
    assert "laboratory_reports" in pdata
    assert "radiology_reports" in pdata

    # Schedule Follow-up
    tomorrow = (date.today() + timedelta(days=7)).isoformat()
    fu_res = await c.post("/api/v1/doctor/follow-up", json={
        "patient_id": str(pid),
        "follow_up_date": tomorrow,
        "time_slot": "11:30",
        "reason": "1-week post medication check"
    })
    assert fu_res.status_code == 200
    assert "appointment_number" in fu_res.json()

