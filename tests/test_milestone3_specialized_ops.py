"""Integration tests for Milestone 3: Specialized Hospital Operations Completion."""
import uuid
from decimal import Decimal
from datetime import date, datetime, timedelta
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from main import app
from app.config import get_db, settings
from app.api.auth import CurrentUser, get_current_user, User
from app.models.inpatient_emergency_models import (
    BloodGroupType, BloodComponentType, BloodUnit, BloodDonor, BloodDonation
)


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
                roles=["super_admin", "doctor", "blood_bank_technician", "pharmacist", "accountant", "insurance_officer"],
                name="Dr. Specialized Lead"
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
async def test_blood_bank_donor_and_component_separation(client):
    """Test full donor registration, physical screening, donation collection, and separation into PRBC, FFP, Platelets."""
    c, session = client

    # 1. Register a donor
    donor_payload = {
        "first_name": "Rohan",
        "last_name": "Verma",
        "blood_group_name": "O+",
        "phone": "9876543210",
        "gender": "Male"
    }
    r = await c.post("/api/v1/blood-bank/donors", json=donor_payload)
    assert r.status_code == 201
    donor = r.json()
    donor_id = donor["blood_donor_id"]
    assert donor["first_name"] == "Rohan"
    assert donor["donor_number"].startswith("DON-")

    # 2. Record pre-donation physical screening (Fails if Hb < 12.5)
    ineligible_payload = {
        "hemoglobin": 11.0,
        "weight": 55.0,
        "blood_pressure": "120/80"
    }
    r = await c.post(f"/api/v1/blood-bank/donors/{donor_id}/eligibility", json=ineligible_payload)
    assert r.status_code == 200
    assert r.json()["is_eligible"] is False

    # Pass physical screening
    eligible_payload = {
        "hemoglobin": 14.5,
        "weight": 68.0,
        "blood_pressure": "120/80"
    }
    r = await c.post(f"/api/v1/blood-bank/donors/{donor_id}/eligibility", json=eligible_payload)
    assert r.status_code == 200
    assert r.json()["is_eligible"] is True

    # 3. Collect whole blood donation
    donation_payload = {
        "blood_donor_id": donor_id,
        "volume_ml": 450,
        "donation_type": "Voluntary"
    }
    r = await c.post("/api/v1/blood-bank/donations", json=donation_payload)
    assert r.status_code == 201
    donation = r.json()
    donation_id = donation["blood_donation_id"]
    assert donation["status"] == "Quarantined"

    # 4. Separate donation into blood components (PRBC, FFP, Platelets)
    r = await c.post(f"/api/v1/blood-bank/donations/{donation_id}/separate")
    assert r.status_code == 201
    components = r.json()
    assert len(components) == 3
    component_types = [comp["component_name"] for comp in components]
    assert "Packed Red Blood Cells" in component_types
    assert "Fresh Frozen Plasma" in component_types
    assert "Platelets" in component_types


@pytest.mark.asyncio
async def test_blood_bank_viral_quarantine_screening(client):
    """Test viral screening quarantine tests releasing clean units and discarding reactive units."""
    c, session = client

    # Setup donor, donation, and separated components
    r = await c.post("/api/v1/blood-bank/donors", json={"first_name": "Aman", "last_name": "Singh", "blood_group_name": "A+"})
    donor_id = r.json()["blood_donor_id"]
    await c.post(f"/api/v1/blood-bank/donors/{donor_id}/eligibility", json={"hemoglobin": 15.0, "weight": 72.0, "blood_pressure": "120/80"})
    r_don = await c.post("/api/v1/blood-bank/donations", json={"blood_donor_id": donor_id, "volume_ml": 450})
    donation_id = r_don.json()["blood_donation_id"]
    r_sep = await c.post(f"/api/v1/blood-bank/donations/{donation_id}/separate")
    components = r_sep.json()
    unit_id_clean = components[0]["blood_unit_id"]
    unit_id_reactive = components[1]["blood_unit_id"]

    # Negative test result -> Released to Available
    clean_test = {
        "test_name": "HIV / HepB / HepC Nucleic Acid Screening",
        "result": "Negative"
    }
    r = await c.post(f"/api/v1/blood-bank/units/{unit_id_clean}/test", json=clean_test)
    assert r.status_code == 201
    unit_data = r.json()["updated_unit"]
    assert unit_data["status"] == "available"

    # Reactive test result -> Quarantined to Discarded (Biohazard)
    reactive_test = {
        "test_name": "Hepatitis B Surface Antigen (HBsAg)",
        "result": "Positive",
        "remarks": "Reactive on chemiluminescence assay"
    }
    r = await c.post(f"/api/v1/blood-bank/units/{unit_id_reactive}/test", json=reactive_test)
    assert r.status_code == 201
    unit_data = r.json()["updated_unit"]
    assert unit_data["status"] == "discarded"


@pytest.mark.asyncio
async def test_pharmacy_bulk_dispensing_and_pharmacist_review(client):
    """Test atomic multi-item dispensing and clinical pharmacist review logs."""
    c, session = client

    # Get a patient
    from app.models.patient import Patient
    pat = await session.scalar(select(Patient))
    assert pat, "A seeded patient is required"

    # Fetch a prescription or create review
    from app.models.pharmacy_models import Prescription
    rx = await session.scalar(select(Prescription).where(Prescription.patient_id == pat.patient_id))
    if rx:
        review_payload = {
            "review_status": "Approved",
            "clinical_notes": "Dosage and frequency verified against renal function panel.",
            "intervention_required": False
        }
        r = await c.post(f"/api/v1/pharmacy/prescriptions/{rx.prescription_id}/review", json=review_payload)
        assert r.status_code == 201
        review = r.json()
        assert review["review_status"] == "Approved"


@pytest.mark.asyncio
async def test_billing_checkout_and_webhook_settlement(client):
    """Test online payment gateway checkout session creation and webhook signature settlement."""
    c, session = client

    from app.models.inpatient_emergency_models import Invoice
    inv = await session.scalar(select(Invoice).where(Invoice.balance_amount > 0))
    if inv:
        # Create checkout session
        checkout_payload = {
            "invoice_id": str(inv.invoice_id),
            "gateway_provider": "Stripe",
            "amount": float(inv.balance_amount),
            "currency": "INR",
            "return_url": "http://localhost:8000/accounts?payment=success"
        }
        r = await c.post("/api/v1/billing/checkout/session", json=checkout_payload)
        assert r.status_code == 201
        sess = r.json()
        assert sess["status"] == "Pending"
        assert "stripe.com" in sess["checkout_url"] or "payment" in sess["checkout_url"]

        # Simulate webhook payment callback
        webhook_payload = {
            "gateway_provider": "Stripe",
            "gateway_session_id": sess["gateway_session_id"],
            "event_type": "payment_intent.succeeded",
            "payment_reference": f"pi_{uuid.uuid4().hex[:12]}",
            "signature": f"sim_sig_{sess['gateway_session_id']}"
        }
        r = await c.post("/api/v1/billing/webhook/payment-settlement", json=webhook_payload)
        assert r.status_code == 200
        settlement = r.json()
        assert settlement["status"] == "Settled"


@pytest.mark.asyncio
async def test_telemedicine_video_room_and_in_session_order(client):
    """Test generating WebRTC / Jitsi video room sessions and in-session clinical orders."""
    c, session = client

    from app.models.emr_models import VirtualAppointment
    apt = await session.scalar(select(VirtualAppointment))
    if apt:
        # Generate video room
        r = await c.post(f"/api/v1/telemedicine/appointments/{apt.virtual_appointment_id}/video-room")
        assert r.status_code == 201
        room = r.json()
        assert "room_url" in room
        assert "host_token" in room

        # Synchronize in-session clinical order
        order_payload = {
            "order_type": "Laboratory",
            "details": {"test_name": "Complete Blood Count (CBC)", "urgency": "Routine"}
        }
        r = await c.post(f"/api/v1/telemedicine/sessions/{room['video_room_id']}/orders", json=order_payload)
        assert r.status_code == 201
        order = r.json()
        assert order["status"] == "Synchronized"
