"""Integration tests for Milestone 2: Acute Care & Inpatient Operations Completion."""
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
                roles=["super_admin", "doctor", "nurse", "pharmacist", "billing_clerk", "surgeon"],
                name="Dr. Acute Care Lead"
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
async def test_inpatient_clearance_and_discharge_gate(client):
    """Test 4-department clearance gate (Doctor, Pharmacy, Nursing, Billing) before inpatient discharge."""
    c, session = client

    # 1. Fetch an existing active admission or create one
    admission_id = await session.scalar(
        text("SELECT admission_id FROM admission.admissions WHERE status = 'admitted' LIMIT 1")
    )
    if not admission_id:
        patient_id = await session.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1"))
        bed_id = await session.scalar(text("SELECT bed_id FROM ward.beds LIMIT 1"))
        doctor_id = await session.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1"))
        admission_id = uuid.uuid4()
        await session.execute(
            text("""INSERT INTO admission.admissions 
                    (admission_id, admission_number, patient_id, bed_id, admitting_doctor_id, admission_datetime, status)
                    VALUES (:aid, :anum, :pid, :bid, :did, NOW(), 'admitted')"""),
            {
                "aid": admission_id,
                "anum": f"ADM-{uuid.uuid4().hex[:8].upper()}",
                "pid": patient_id,
                "bid": bed_id,
                "did": doctor_id
            }
        )

    # 2. Check initial clearance status
    res = await c.get(f"/api/v1/inpatient/admissions/{admission_id}/clearance")
    assert res.status_code == 200
    clr_data = res.json()
    assert clr_data["admission_id"] == str(admission_id)
    assert "ready_for_discharge" in clr_data

    # 3. Attempt premature discharge -> Should be blocked if not fully cleared
    if not clr_data["ready_for_discharge"]:
        dc_res = await c.post("/api/v1/inpatient/discharges", json={
            "admission_id": str(admission_id),
            "discharge_type": "regular",
            "discharge_notes": "Attempting premature discharge"
        })
        assert dc_res.status_code == 400
        assert "Clearance required" in dc_res.json()["detail"]

    # 4. Clear all 4 departments sequentially
    depts = ["doctor", "pharmacy", "nursing", "billing"]
    for dept in depts:
        step_res = await c.post(f"/api/v1/inpatient/admissions/{admission_id}/clearance", json={
            "department": dept,
            "notes": f"Approved by {dept} lead"
        })
        assert step_res.status_code == 200
        assert step_res.json()[f"{'discharge_summary_signed' if dept == 'doctor' else dept + '_cleared'}"] is True

    # 5. Verify all cleared now
    res_cleared = await c.get(f"/api/v1/inpatient/admissions/{admission_id}/clearance")
    assert res_cleared.status_code == 200
    assert res_cleared.json()["ready_for_discharge"] is True

    # 6. Execute discharge -> Should succeed
    final_dc = await c.post("/api/v1/inpatient/discharges", json={
        "admission_id": str(admission_id),
        "discharge_type": "regular",
        "discharge_notes": "Routine discharge, patient fully stabilized."
    })
    assert final_dc.status_code == 200
    assert final_dc.json()["status"] == "discharged"

    # 7. Printable discharge slip
    slip_res = await c.get(f"/api/v1/inpatient/admissions/{admission_id}/discharge-summary")
    assert slip_res.status_code == 200
    assert slip_res.json()["admission_id"] == str(admission_id)
    assert slip_res.json()["status"] == "discharged"


@pytest.mark.asyncio
async def test_inpatient_daily_clinical_rounds(client):
    """Test physician and nursing daily rounding notes with vitals."""
    c, session = client

    admission_id = await session.scalar(
        text("SELECT admission_id FROM admission.admissions LIMIT 1")
    )
    assert admission_id, "Need an admission for rounding test"

    # 1. Log a clinical round
    round_payload = {
        "round_type": "physician",
        "assessment": "Patient afebrile, wound site clean and healing well. Tolerating normal diet.",
        "plan": "Discontinue IV antibiotics; transition to oral amoxicillin. Plan discharge tomorrow.",
        "vitals_snapshot": {
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "heart_rate": 72,
            "respiratory_rate": 16,
            "temperature": 98.4,
            "spO2": 99
        }
    }
    create_res = await c.post(f"/api/v1/inpatient/admissions/{admission_id}/rounds", json=round_payload)
    assert create_res.status_code == 200
    round_data = create_res.json()
    assert round_data["round_type"] == "physician"
    assert round_data["assessment"] == round_payload["assessment"]
    assert round_data["vitals_snapshot"]["heart_rate"] == 72

    # 2. Retrieve rounding history
    get_res = await c.get(f"/api/v1/inpatient/admissions/{admission_id}/rounds")
    assert get_res.status_code == 200
    rounds_list = get_res.json()
    assert len(rounds_list) >= 1
    assert any(r["round_id"] == round_data["round_id"] for r in rounds_list)


@pytest.mark.asyncio
async def test_nursing_mar_schedule_and_handover(client):
    """Test nursing MAR shift dose auto-scheduling and shift handover summary."""
    c, session = client

    patient_id = await session.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1"))
    admission_id = await session.scalar(
        text("SELECT admission_id FROM admission.admissions WHERE patient_id = :pid LIMIT 1"),
        {"pid": patient_id}
    )

    # 1. Trigger shift dose generation (TID / BID / QID)
    sched_res = await c.post(
        f"/api/v1/nursing/patients/{patient_id}/mar/schedule-doses",
        params={"shift": "morning", "frequency": "TID"}
    )
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    assert sched_data["status"] == "success"
    assert "doses_scheduled" in sched_data

    # 2. Query MAR doses for patient
    mar_res = await c.get(f"/api/v1/nursing/patients/{patient_id}/mar")
    assert mar_res.status_code == 200
    mar_doses = mar_res.json()
    assert isinstance(mar_doses, list)

    # 3. Test ward shift handover endpoint
    handover_res = await c.get("/api/v1/nursing/ward/handover")
    assert handover_res.status_code == 200
    ho_data = handover_res.json()
    assert "shift" in ho_data
    assert "census" in ho_data
    assert "pending_medications_count" in ho_data


@pytest.mark.asyncio
async def test_emergency_unidentified_arrival_and_mci(client):
    """Test fast-track unidentified trauma registration and Mass-Casualty Incident disaster mode."""
    c, session = client

    # 1. Register fast-track unidentified trauma victim
    unidentified_payload = {
        "estimated_age": 35,
        "gender": "male",
        "triage_acuity": "red",
        "chief_complaint": "Pedestrian struck by vehicle, unresponsive, severe head trauma",
        "transport_mode": "EMS",
        "incident_code": "TRAUMA-HIGHWAY-09"
    }
    reg_res = await c.post("/api/v1/emergency/arrivals/unidentified", json=unidentified_payload)
    assert reg_res.status_code == 200
    trauma_data = reg_res.json()
    assert trauma_data["is_unidentified"] is True
    assert "TEMP-" in trauma_data["temp_tag"]
    assert trauma_data["triage_acuity"] == "red"

    # 2. Declare Mass-Casualty Incident (MCI)
    mci_payload = {
        "event_code": f"MCI-TEST-{uuid.uuid4().hex[:6].upper()}",
        "description": "Multi-vehicle collision on Outer Ring Road",
        "triage_color_lead": "red"
    }
    mci_res = await c.post("/api/v1/emergency/mci/activate", json=mci_payload)
    assert mci_res.status_code == 200
    mci_event = mci_res.json()
    assert mci_event["status"] == "active"
    assert mci_event["event_code"] == mci_payload["event_code"]

    # 3. Check active MCI status
    status_res = await c.get("/api/v1/emergency/mci/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["mci_active"] is True
    assert status_data["active_event"]["event_code"] == mci_payload["event_code"]

    # 4. Deactivate MCI incident
    deact_res = await c.post(f"/api/v1/emergency/mci/{mci_event['mci_id']}/deactivate")
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "deactivated"

    # 5. Verify MCI status now inactive
    status_res2 = await c.get("/api/v1/emergency/mci/status")
    assert status_res2.status_code == 200
    assert status_res2.json()["mci_active"] is False


@pytest.mark.asyncio
async def test_surgery_cssd_implants_and_aldrete_recovery(client):
    """Test CSSD sterile tray verification, implant tracking, and Aldrete PACU discharge rules."""
    c, session = client

    # 1. Fetch a surgical case or create a mock case
    case_id = await session.scalar(text("SELECT case_id FROM surgery.surgical_cases LIMIT 1"))
    if not case_id:
        patient_id = await session.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1"))
        theatre_id = await session.scalar(text("SELECT theatre_id FROM surgery.operating_theatres LIMIT 1"))
        surgeon_id = await session.scalar(text("SELECT surgeon_id FROM surgery.surgeons LIMIT 1"))
        case_id = uuid.uuid4()
        await session.execute(
            text("""INSERT INTO surgery.surgical_cases
                    (case_id, case_number, patient_id, theatre_id, lead_surgeon_id, scheduled_start, scheduled_end, procedure_name, status)
                    VALUES (:cid, :cnum, :pid, :tid, :sid, NOW(), NOW() + INTERVAL '2 hours', 'Exploratory Laparotomy', 'in_progress')"""),
            {
                "cid": case_id,
                "cnum": f"SURG-{uuid.uuid4().hex[:6].upper()}",
                "pid": patient_id,
                "tid": theatre_id,
                "sid": surgeon_id
            }
        )

    # 2. Record CSSD sterile tray batch
    tray_payload = {
        "tray_barcode": f"TRAY-LAP-{uuid.uuid4().hex[:6].upper()}",
        "tray_name": "Major Laparotomy Instrument Set",
        "autoclave_batch": "AC-2026-09-001",
        "sterilization_date": str(date.today() - timedelta(days=1)),
        "sterile_expiry": str(date.today() + timedelta(days=29)),
        "biological_indicator_pass": True
    }
    tray_res = await c.post(f"/api/v1/surgery/cases/{case_id}/cssd-trays", json=tray_payload)
    assert tray_res.status_code == 200
    assert tray_res.json()["tray_name"] == tray_payload["tray_name"]
    assert tray_res.json()["biological_indicator_pass"] is True

    # 3. Retrieve CSSD trays for case
    trays_list = await c.get(f"/api/v1/surgery/cases/{case_id}/cssd-trays")
    assert trays_list.status_code == 200
    assert len(trays_list.json()) >= 1

    # 4. Record surgical implant (serial and lot tracking)
    implant_payload = {
        "implant_name": "Polypropylene Surgical Hernia Mesh 15x15cm",
        "serial_number": f"SN-{uuid.uuid4().hex[:8].upper()}",
        "lot_number": "LOT-998811",
        "manufacturer": "Ethicon Surgical Care",
        "anatomical_site": "Right Inguinal Canal",
        "verified_by_nurse": True
    }
    imp_res = await c.post(f"/api/v1/surgery/cases/{case_id}/implants", json=implant_payload)
    assert imp_res.status_code == 200
    assert imp_res.json()["serial_number"] == implant_payload["serial_number"]

    # 5. Post-Anesthesia Recovery (PACU) Aldrete scoring:
    # Attempt discharge to ward with failing Aldrete score (< 9) and no clinical override -> 400
    failing_pacu = {
        "consciousness_level": "drowsy",
        "respiratory_status": "shallow breathing, requires nasal cannula",
        "spo2": 93.0,
        "vital_signs_stable": False,
        "pain_score": 6,
        "aldrete_score": 7,
        "discharge_readiness": True,
        "destination": "inpatient_ward",
        "clinical_override_reason": None
    }
    fail_res = await c.post(f"/api/v1/surgery/cases/{case_id}/recovery", json=failing_pacu)
    assert fail_res.status_code == 400
    assert "Aldrete score" in fail_res.json()["detail"]

    # Now provide qualifying Aldrete score (>= 9) -> Succeeded
    passing_pacu = {
        "consciousness_level": "fully_awake",
        "respiratory_status": "spontaneous breathing on room air",
        "spo2": 99.0,
        "vital_signs_stable": True,
        "pain_score": 2,
        "aldrete_score": 10,
        "discharge_readiness": True,
        "destination": "inpatient_ward"
    }
    pass_res = await c.post(f"/api/v1/surgery/cases/{case_id}/recovery", json=passing_pacu)
    assert pass_res.status_code == 200
    assert pass_res.json()["aldrete_score"] == 10
    assert pass_res.json()["discharge_readiness"] is True

