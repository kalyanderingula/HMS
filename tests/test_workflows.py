"""Integration tests run against PostgreSQL; every test rolls back all writes."""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

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
            return CurrentUser(user_id=admin.user_id, username=admin.username,
                               employee_id=admin.employee_id, roles=["super_admin"], name="Test operator")
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
async def test_staff_worklists_and_pages(client):
    c, _ = client
    portal_workspaces = {
        "/nurse": "inpatient", "/pharmacist": "pharmacy", "/lab": "laboratory",
        "/accounts": "billing", "/radiology": "radiology", "/blood-bank": "blood",
        "/emergency": "emergency",
        "/surgery": "surgery",
    }
    for path, workspace in portal_workspaces.items():
        response = await c.get(path)
        assert response.status_code == 200, (path, response.text)
        assert f'data-workspace="{workspace}"' in response.text
    for path in ["/static/js/staff.js",
                 "/api/v1/inpatient/beds", "/api/v1/inpatient/admissions", "/api/v1/billing/invoices",
                 "/api/v1/worklists/laboratory", "/api/v1/worklists/radiology", "/api/v1/worklists/prescriptions"]:
        response = await c.get(path)
        assert response.status_code == 200, (path, response.text)


@pytest.mark.asyncio
async def test_operational_api_role_boundaries(client):
    c, db = client
    seeded = await db.scalar(select(User).where(User.status == "active"))

    active_role = "pharmacist"

    async def as_role():
        return CurrentUser(user_id=seeded.user_id, username=seeded.username,
                           employee_id=seeded.employee_id, roles=[active_role], name="RBAC test")

    app.dependency_overrides[get_current_user] = as_role
    assert (await c.get("/api/v1/pharmacy/inventory")).status_code == 200
    assert (await c.get("/api/v1/laboratory/tests")).status_code == 403
    assert (await c.get("/api/v1/blood-bank/inventory")).status_code == 403

    active_role = "blood_bank_technician"
    assert (await c.get("/api/v1/blood-bank/inventory")).status_code == 200
    assert (await c.get("/api/v1/pharmacy/inventory")).status_code == 403


@pytest.mark.asyncio
async def test_radiology_order_to_report_billing_and_notification(client):
    c, db = client
    patient_id = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    doctor_id = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    tests = (await c.get("/api/v1/radiology/tests")).json()
    rooms = (await c.get("/api/v1/radiology/rooms")).json()
    assert tests and rooms, "Seed a radiology test and imaging room"

    ordered = await c.post("/api/v1/radiology/orders", json={
        "patient_id": patient_id, "doctor_id": doctor_id, "priority": "Urgent",
        "clinical_indication": "Integration test imaging",
        "items": [{"radiology_test_id": tests[0]["radiology_test_id"]}],
    })
    assert ordered.status_code == 201, ordered.text
    order = ordered.json()
    item_id = order["items"][0]["order_item_id"]
    invoice_count = await db.scalar(text("""SELECT count(*) FROM billing.invoice_items
        WHERE item_type='Radiology' AND item_reference_id=:source"""),
        {"source": uuid.UUID(order["radiology_order_id"])})
    assert invoice_count == 1

    start = datetime.now() + timedelta(days=30)
    schedule_data = {"order_item_id": item_id, "imaging_room_id": rooms[0]["imaging_room_id"],
                     "scheduled_start": start.isoformat(),
                     "scheduled_end": (start + timedelta(minutes=30)).isoformat()}
    scheduled = await c.post("/api/v1/radiology/schedule", json=schedule_data)
    assert scheduled.status_code == 201, scheduled.text
    assert (await c.post("/api/v1/radiology/schedule", json=schedule_data)).status_code == 409

    study = await c.post("/api/v1/radiology/studies", json={
        "radiology_appointment_id": scheduled.json()["radiology_appointment_id"],
        "study_description": "Integration test study",
    })
    assert study.status_code == 201, study.text
    report = await c.post("/api/v1/radiology/reports", json={
        "study_id": study.json()["study_id"], "findings": "No acute abnormality.",
        "impression": "Normal integration test examination.",
    })
    assert report.status_code == 201, report.text
    assert (await c.post("/api/v1/radiology/reports", json={
        "study_id": study.json()["study_id"], "findings": "Duplicate", "impression": "Duplicate",
    })).status_code == 409

    row = next(x for x in (await c.get("/api/v1/worklists/radiology")).json()
               if x["order_item_id"] == item_id)
    assert row["order_status"] == "Completed" and row["report_id"] == report.json()["report_id"]
    summary = (await c.get(f"/api/v1/emr/patients/{patient_id}/summary")).json()
    assert any(x["report_id"] == report.json()["report_id"] for x in summary["radiology_reports"])
    notifications = await db.scalar(text("""SELECT count(*) FROM core.notifications
        WHERE source_module='Radiology' AND source_reference_id=:source"""),
        {"source": uuid.UUID(report.json()["report_id"])})
    assert notifications == 1


@pytest.mark.asyncio
async def test_blood_request_to_transfusion_billing_and_history(client):
    c, db = client
    await c.get("/api/v1/blood-bank/inventory")
    group_id = await db.scalar(text("SELECT blood_group_type_id FROM blood_bank.blood_group_types WHERE group_name='O+'"))
    component_id = await db.scalar(text("SELECT blood_component_type_id FROM blood_bank.blood_component_types WHERE component_name='PRBC'"))
    donor_id, donation_id, unit_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await db.execute(text("""INSERT INTO blood_bank.blood_donors
        (blood_donor_id,donor_number,first_name,last_name,blood_group_type_id)
        VALUES (:id,:number,'Integration','Donor',:group)"""),
        {"id": donor_id, "number": f"DON-{donor_id.hex[:12]}", "group": group_id})
    await db.execute(text("""INSERT INTO blood_bank.blood_donations
        (blood_donation_id,blood_donor_id,bag_number,volume_ml)
        VALUES (:id,:donor,:bag,450)"""),
        {"id": donation_id, "donor": donor_id, "bag": f"BAG-{donation_id.hex[:12]}"})
    await db.execute(text("""INSERT INTO blood_bank.blood_units
        (blood_unit_id,blood_donation_id,unit_number,blood_group_type_id,blood_component_type_id,
         volume_ml,collection_date,expiry_date,status)
        VALUES (:id,:donation,:number,:group,:component,450,:collected,:expiry,'available')"""),
        {"id": unit_id, "donation": donation_id, "number": f"TEST-{unit_id.hex[:12].upper()}",
         "group": group_id, "component": component_id, "collected": date.today(),
         "expiry": date.today() + timedelta(days=30)})
    unit = next(x for x in (await c.get("/api/v1/blood-bank/inventory")).json()
                if x["blood_unit_id"] == str(unit_id))
    patient_id = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    requested = await c.post("/api/v1/blood-bank/requests", json={
        "patient_id": patient_id, "blood_group": unit["blood_group"],
        "component_name": unit["component_name"], "units_requested": 1,
        "urgency": "STAT", "clinical_indication": "Integration test transfusion",
    })
    assert requested.status_code == 201, requested.text
    request_id = requested.json()["blood_request_id"]

    crossmatch_data = {"blood_request_id": request_id, "blood_unit_id": unit["blood_unit_id"],
                       "compatibility_result": "Compatible"}
    matched = await c.post("/api/v1/blood-bank/cross-match", json=crossmatch_data)
    assert matched.status_code == 201, matched.text
    assert (await c.post("/api/v1/blood-bank/cross-match", json=crossmatch_data)).status_code == 409

    issued = await c.post("/api/v1/blood-bank/issue", json={
        "blood_request_id": request_id, "blood_unit_id": unit["blood_unit_id"]})
    assert issued.status_code == 201, issued.text
    assert (await c.post("/api/v1/blood-bank/issue", json={
        "blood_request_id": request_id, "blood_unit_id": unit["blood_unit_id"]})).status_code == 409
    invoice_count = await db.scalar(text("""SELECT count(*) FROM billing.invoice_items
        WHERE item_type='Procedure' AND item_reference_id=:unit"""),
        {"unit": uuid.UUID(unit["blood_unit_id"])})
    assert invoice_count == 1

    transfused = await c.post("/api/v1/blood-bank/transfusions", json={
        "blood_request_id": request_id, "blood_unit_id": unit["blood_unit_id"],
        "volume_transfused": min(unit["volume_ml"], 350), "adverse_reaction": False,
        "notes": "Transfusion completed without immediate reaction.",
    })
    assert transfused.status_code == 201, transfused.text
    assert (await c.post("/api/v1/blood-bank/transfusions", json={
        "blood_request_id": request_id, "blood_unit_id": unit["blood_unit_id"],
        "volume_transfused": 100})).status_code == 409
    summary = (await c.get(f"/api/v1/emr/patients/{patient_id}/summary")).json()
    assert any(x["transfusion_id"] == transfused.json()["transfusion_id"]
               for x in summary["blood_transfusions"])
    request_row = next(x for x in (await c.get("/api/v1/blood-bank/requests")).json()
                       if x["blood_request_id"] == request_id)
    assert request_row["status"] == "completed"
    notification_count = await db.scalar(text("""SELECT count(*) FROM core.notifications
        WHERE source_module='BloodBank' AND source_reference_id IN (:request,:unit,:transfusion)"""),
        {"request": uuid.UUID(request_id), "unit": uuid.UUID(unit["blood_unit_id"]),
         "transfusion": uuid.UUID(transfused.json()["transfusion_id"])})
    assert notification_count >= 4


@pytest.mark.asyncio
async def test_nursing_mar_dose_lifecycle(client):
    c, db = client
    patient = str(await db.scalar(text("""SELECT p.patient_id FROM patient.patients p WHERE NOT EXISTS
        (SELECT 1 FROM admission.admissions a WHERE a.patient_id=p.patient_id AND a.actual_discharge_date IS NULL) LIMIT 1""")))
    doctor = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    bed = next(x for x in (await c.get("/api/v1/inpatient/beds")).json() if x["status"] == "Available")
    admitted = await c.post("/api/v1/inpatient/admissions", json={"patient_id":patient,"doctor_id":doctor,"bed_id":bed["bed_id"],"admission_reason":"MAR test"})
    assert admitted.status_code == 201, admitted.text
    encounter=await c.post("/api/v1/emr/encounters",json={"patient_id":patient,"doctor_id":doctor,"encounter_type":"IPD","chief_complaint":"MAR test"})
    drug=(await c.get("/api/v1/pharmacy/drugs")).json()[0]
    added=await c.post(f"/api/v1/emr/encounters/{encounter.json()['encounter_id']}/prescriptions",json={"medications":[{"drug_id":drug["drug_id"],"dosage":"1 tablet","frequency":"daily","route":"Oral","duration":"1 day","quantity_prescribed":1}]})
    assert added.status_code == 201, added.text
    await c.post(f"/api/v1/emr/encounters/{encounter.json()['encounter_id']}/complete",json={})
    mar=(await c.get(f"/api/v1/nursing/patients/{patient}/mar")).json()
    assert mar and mar[0]["administration_status"] in ("Due","Overdue")
    dose=mar[0];payload={"mar_id":dose["mar_id"],"patient_id":patient,"prescription_item_id":dose["prescription_item_id"],"medicine_name":dose["medicine_name"],"dosage_given":dose["dosage"],"route":dose["route"],"administration_status":"Missed"}
    assert (await c.post("/api/v1/nursing/administer-medication",json=payload)).status_code == 422
    payload["exception_reason"]="Patient unavailable for scheduled dose"
    recorded=await c.post("/api/v1/nursing/administer-medication",json=payload)
    assert recorded.status_code == 201, recorded.text
    assert (await c.post("/api/v1/nursing/administer-medication",json=payload)).status_code == 409
    assert await db.scalar(text("SELECT count(*) FROM core.notifications WHERE source_module='Nursing' AND source_reference_id=:id"),{"id":uuid.UUID(dose["mar_id"])}) == 1
    summary=(await c.get(f"/api/v1/emr/patients/{patient}/summary")).json()
    assert any(x["administration_log_id"]==recorded.json()["administration_id"] for x in summary["medication_administration_history"])


@pytest.mark.asyncio
async def test_billing_payment_lifecycle(client):
    c, db = client
    patient_id = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    response = await c.post("/api/v1/billing/invoices", json={"patient_id": patient_id,
        "items": [{"item_name": "Test consultation", "quantity": "2", "unit_price": "100.25"}],
        "discount_amount": "10", "tax_amount": "5"})
    assert response.status_code == 201, response.text
    invoice = response.json()
    assert Decimal(str(invoice["total_amount"])) == Decimal("195.50")
    path = f"/api/v1/billing/invoices/{invoice['invoice_id']}/payments"
    payment = {"amount": "100", "method": "Cash", "reference": str(uuid.uuid4())}
    paid = await c.post(path, json=payment)
    assert paid.status_code == 201, paid.text
    assert Decimal(str(paid.json()["balance_amount"])) == Decimal("95.50")
    duplicate = await c.post(path, json=payment)
    assert len(duplicate.json()["payments"]) == 1
    conflict = await c.post(path, json={**payment, "amount": "50"})
    assert conflict.status_code == 409
    overpayment = await c.post(path, json={**payment, "reference": str(uuid.uuid4())})
    assert overpayment.status_code == 409
    final = await c.post(path, json={**payment, "amount": "95.50", "reference": str(uuid.uuid4())})
    assert final.json()["status_name"] == "Paid"
    assert Decimal(str(final.json()["balance_amount"])) == 0


@pytest.mark.asyncio
async def test_billing_validation(client):
    c, _ = client
    for items in [[], [{"item_name":"Test","quantity":-1,"unit_price":10}],
                  [{"item_name":"Test","quantity":1,"unit_price":"NaN"}]]:
        response = await c.post("/api/v1/billing/invoices", json={"patient_id":str(uuid.uuid4()),"items":items})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_accounting_controls_and_reports(client):
    c, db = client
    patient=str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    created=await c.post("/api/v1/billing/invoices",json={"patient_id":patient,"items":[{"item_name":"Accounting test","quantity":1,"unit_price":100}]})
    invoice=created.json();iid=invoice["invoice_id"]
    paid=await c.post(f"/api/v1/billing/invoices/{iid}/payments",json={"amount":60,"method":"Cash","reference":str(uuid.uuid4())})
    assert (await c.post(f"/api/v1/billing/invoices/{iid}/cancel",json={"reason":"Cannot cancel paid invoice"})).status_code==409
    payment=paid.json()["payments"][0];reference=str(uuid.uuid4())
    refund=await c.post(f"/api/v1/billing/invoices/{iid}/refunds",json={"payment_id":payment["payment_id"],"amount":20,"reference":reference,"reason":"Approved partial refund"})
    assert refund.status_code==201,refund.text
    assert (await c.post(f"/api/v1/billing/invoices/{iid}/refunds",json={"payment_id":payment["payment_id"],"amount":20,"reference":reference,"reason":"Duplicate refund"})).status_code==409
    credit=await c.post(f"/api/v1/billing/invoices/{iid}/credit-notes",json={"amount":20,"reason":"Service adjustment"})
    assert credit.status_code==201,credit.text
    claim=await c.post(f"/api/v1/billing/invoices/{iid}/claims",json={"insurance_provider":"Test Insurance","policy_number":"POL-1","claim_number":str(uuid.uuid4()),"claim_amount":30})
    assert claim.status_code==201,claim.text
    decision=await c.put(f"/api/v1/billing/claims/{claim.json()['insurance_claim_id']}",json={"status":"Approved","approved_amount":25,"reason":"Policy copay"})
    assert decision.status_code==200 and decision.json()["approved_amount"]==25
    assert (await c.put(f"/api/v1/billing/claims/{claim.json()['insurance_claim_id']}",json={"status":"Rejected","reason":"repeat"})).status_code==409
    report=await c.get("/api/v1/billing/reports/summary")
    assert report.status_code==200 and {"revenue","collected","outstanding"}<=report.json()["totals"].keys()
    unpaid=await c.post("/api/v1/billing/invoices",json={"patient_id":patient,"items":[{"item_name":"Cancel test","quantity":1,"unit_price":10}]})
    cancelled=await c.post(f"/api/v1/billing/invoices/{unpaid.json()['invoice_id']}/cancel",json={"reason":"Order entered in error"})
    assert cancelled.status_code==200 and cancelled.json()["status_name"]=="Cancelled"


@pytest.mark.asyncio
async def test_emergency_arrival_triage_clinical_record_and_disposition(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    arrival = await c.post("/api/v1/emergency/arrivals", json={
        "patient_id": patient, "arrival_mode": "Ambulance", "brought_by": "Paramedic unit",
        "arrival_condition": "Chest pain and shortness of breath",
    })
    assert arrival.status_code == 201, arrival.text
    arrival_id = arrival.json()["emergency_arrival_id"]
    triage = await c.post("/api/v1/emergency/triage", json={
        "emergency_arrival_id": arrival_id, "esi_level": 2,
        "chief_complaint": "Acute chest pain", "vital_signs_summary": "SpO2 91%",
    })
    assert triage.status_code == 201, triage.text
    assert (await c.post("/api/v1/emergency/triage", json={
        "emergency_arrival_id": arrival_id, "esi_level": 2, "chief_complaint": "Duplicate",
    })).status_code == 409
    queue = (await c.get("/api/v1/emergency/queue")).json()
    case = next(row for row in queue if row["emergency_arrival_id"] == arrival_id)
    options_response = await c.get("/api/v1/emergency/admission-options")
    assert options_response.status_code == 200, options_response.text
    encounter_id = case["emergency_encounter_id"]
    vitals = await c.post("/api/v1/emergency/vitals", json={
        "emergency_encounter_id": encounter_id, "temperature": 37.2, "pulse_rate": 104,
        "respiratory_rate": 24, "systolic_bp": 145, "diastolic_bp": 92, "oxygen_saturation": 91,
    })
    assert vitals.status_code == 201, vitals.text
    note = await c.post("/api/v1/emergency/notes", json={
        "emergency_encounter_id": encounter_id, "note_type": "Treatment",
        "note_text": "Oxygen applied and cardiac monitoring started",
    })
    assert note.status_code == 201, note.text
    detail = (await c.get(f"/api/v1/emergency/encounters/{encounter_id}")).json()
    assert len(detail["vitals"]) == 1 and len(detail["notes"]) == 1
    closed = await c.post(f"/api/v1/emergency/encounters/{encounter_id}/disposition", json={
        "disposition": "Discharged", "notes": "Stable after observation; follow up in cardiology",
    })
    assert closed.status_code == 200 and closed.json()["status"] == "Closed"
    summary = (await c.get(f"/api/v1/emr/patients/{patient}/summary")).json()
    assert any(visit["emergency_encounter_id"] == encounter_id and visit["disposition"] == "Discharged"
               for visit in summary["emergency_visits"])
    assert (await c.post(f"/api/v1/emergency/encounters/{encounter_id}/disposition", json={
        "disposition": "Discharged", "notes": "Repeated closure",
    })).status_code == 409
    assert all(row["emergency_encounter_id"] != encounter_id for row in (await c.get("/api/v1/emergency/queue")).json())


@pytest.mark.asyncio
async def test_surgery_ot_lifecycle_conflicts_billing_and_recovery(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    doctor = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    request = await c.post("/api/v1/surgery/requests", json={"patient_id":patient,
        "procedure_name":"Laparoscopic procedure","procedure_code":"SURG-TEST","urgency":"Urgent",
        "clinical_indication":"Integration test indication","estimated_charge":1000})
    assert request.status_code == 201, request.text
    request_id=request.json()["surgery_request_id"]
    start=(datetime.utcnow()+timedelta(days=10)).replace(microsecond=0); end=start+timedelta(hours=2)
    schedule_payload={"surgery_request_id":request_id,"ot_room_number":"OT Suite 1",
        "scheduled_start":start.isoformat(),"scheduled_end":end.isoformat(),"primary_surgeon_id":doctor,
        "anesthesiologist_name":"Dr. Anesthesia"}
    schedule=await c.post("/api/v1/surgery/schedule",json=schedule_payload)
    assert schedule.status_code == 201,schedule.text
    schedule_id=schedule.json()["surgery_schedule_id"]
    second=await c.post("/api/v1/surgery/requests",json={"patient_id":patient,
        "procedure_name":"Conflicting procedure","procedure_code":"SURG-CONFLICT","urgency":"Elective",
        "clinical_indication":"Conflict validation","estimated_charge":500})
    conflict={**schedule_payload,"surgery_request_id":second.json()["surgery_request_id"]}
    assert (await c.post("/api/v1/surgery/schedule",json=conflict)).status_code==409
    assert (await c.post(f"/api/v1/surgery/cases/{schedule_id}/start",json={"anesthesia_type":"General"})).status_code==409
    checklist={"consent_verified":True,"identity_verified":True,"surgical_site_verified":True,
        "allergies_reviewed":True,"investigations_reviewed":True,"fasting_confirmed":True,
        "anesthesia_cleared":True,"asa_classification":"ASA II","notes":"Cleared"}
    assert (await c.post(f"/api/v1/surgery/requests/{request_id}/preoperative-checklist",json=checklist)).status_code==201
    assert (await c.post(f"/api/v1/surgery/cases/{schedule_id}/start",json={"anesthesia_type":"General"})).status_code==200
    item=await c.post(f"/api/v1/surgery/cases/{schedule_id}/consumables",json={"item_name":"Surgical mesh","quantity":1,"unit_price":200})
    assert item.status_code==201 and item.json()["line_total"]==200
    completed=await c.post(f"/api/v1/surgery/cases/{schedule_id}/complete",json={
        "surgical_findings":"Expected operative findings","outcome":"Transferred to PACU","complications":"None"})
    assert completed.status_code==200,completed.text
    assert await db.scalar(text("SELECT count(*) FROM billing.invoice_items WHERE item_reference_id=:id"),{"id":uuid.UUID(schedule_id)})==1
    recovery=await c.post(f"/api/v1/surgery/cases/{schedule_id}/recovery",json={
        "recovery_status":"Stable","pain_score":2,"observations":"Awake and stable","disposition":"Ward"})
    assert recovery.status_code==201 and recovery.json()["status"]=="Completed"
    summary=(await c.get(f"/api/v1/emr/patients/{patient}/summary")).json()
    assert any(case["surgery_schedule_id"]==schedule_id and case["recovery_disposition"]=="Ward"
               for case in summary["surgery_history"])
    assert (await c.post(f"/api/v1/surgery/cases/{schedule_id}/recovery",json={
        "recovery_status":"Stable","pain_score":1,"observations":"Repeat","disposition":"Ward"})).status_code==409


@pytest.mark.asyncio
async def test_inpatient_lifecycle(client):
    c, db = client
    patient_id = await db.scalar(text("""SELECT patient_id FROM patient.patients p WHERE NOT EXISTS
        (SELECT 1 FROM admission.admissions a WHERE a.patient_id=p.patient_id AND actual_discharge_date IS NULL) LIMIT 1"""))
    doctor_id = await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1"))
    beds = [b for b in (await c.get("/api/v1/inpatient/beds")).json() if b["status"] == "Available"]
    assert patient_id and doctor_id and len(beds) >= 2, "Seed patients, doctor, and two free beds"
    request = {"patient_id":str(patient_id),"doctor_id":str(doctor_id),"bed_id":beds[0]["bed_id"],"admission_reason":"Integration test"}
    response = await c.post("/api/v1/inpatient/admissions", json=request)
    assert response.status_code == 201, response.text
    admission = response.json()["admission_id"]
    assert (await c.post("/api/v1/inpatient/admissions", json=request)).status_code == 409
    transfer = await c.post("/api/v1/inpatient/transfers", json={"admission_id":admission,"new_bed_id":beds[1]["bed_id"],"transfer_reason":"Test transfer"})
    assert transfer.status_code == 200, transfer.text
    discharge = {"admission_id":admission,"discharge_summary":"Test summary", "discharge_disposition":"Home"}
    assert (await c.post("/api/v1/inpatient/discharges", json=discharge)).status_code == 200
    assert (await c.post("/api/v1/inpatient/discharges", json=discharge)).status_code == 409
    saved = (await db.execute(text("SELECT discharge_summary,actual_discharge_date FROM admission.admissions WHERE admission_id=:id"), {"id":uuid.UUID(admission)})).first()
    assert saved.discharge_summary == "Test summary" and saved.actual_discharge_date


@pytest.mark.asyncio
async def test_pharmacy_rejects_invalid_quantities(client):
    c, _ = client
    for quantity in [0,-1]:
        response = await c.post("/api/v1/pharmacy/dispense",json={"patient_id":str(uuid.uuid4()),"items":[
            {"drug_id":str(uuid.uuid4()),"batch_id":str(uuid.uuid4()),"quantity_dispensed":quantity}],
            "dispensing_reference":str(uuid.uuid4())})
        assert response.status_code == 422
    response = await c.post("/api/v1/pharmacy/batches",json={"drug_id":str(uuid.uuid4()),"batch_number":"Expired",
        "expiry_date":str(date.today()-timedelta(days=1)),"quantity_received":10,"purchase_price":1,"selling_price":1})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_access_controls():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as c:
        for path in ["/api/v1/patients/","/api/v1/employee-documents/search-employee?q=a","/api/v1/billing/invoices"]:
            assert (await c.get(path)).status_code == 401


@pytest.mark.asyncio
async def test_receptionist_cannot_access_billing(client):
    c, _ = client
    async def receptionist():
        return CurrentUser(user_id=uuid.uuid4(),username="reception",roles=["receptionist"])
    app.dependency_overrides[get_current_user] = receptionist
    assert (await c.get("/api/v1/billing/invoices")).status_code == 403


@pytest.mark.asyncio
async def test_lab_sample_result_lifecycle(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    tests = (await c.get("/api/v1/laboratory/tests")).json()
    test = next(t for t in tests if t["parameters"])
    order = await c.post("/api/v1/laboratory/orders",json={"patient_id":patient,"items":[{"test_id":test["test_id"]}]})
    assert order.status_code == 201, order.text
    assert await db.scalar(text("SELECT count(*) FROM billing.invoice_items WHERE item_type='Laboratory' AND item_reference_id=:id"),{"id":uuid.UUID(order.json()["lab_order_id"])}) == 1
    item = order.json()["items"][0]["order_item_id"]
    result = {"order_item_id":item,"parameters":[{"parameter_id":test["parameters"][0]["parameter_id"],"result_value":"10","result_flag":"High"}]}
    assert (await c.post("/api/v1/laboratory/results",json=result)).status_code == 409
    sample = await c.post("/api/v1/laboratory/collect-sample",json={"order_item_id":item})
    assert sample.status_code == 201, sample.text
    assert (await c.post("/api/v1/laboratory/collect-sample",json={"order_item_id":item})).status_code == 409
    entered = await c.post("/api/v1/laboratory/results",json=result)
    assert entered.status_code == 201, entered.text
    assert (await c.post("/api/v1/laboratory/results",json=result)).status_code == 409
    approved = await c.post(f"/api/v1/laboratory/results/{entered.json()['result_entry_id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["result_status"] == "Approved"
    assert (await c.post(f"/api/v1/laboratory/results/{entered.json()['result_entry_id']}/approve")).status_code == 409
    summary=(await c.get(f"/api/v1/emr/patients/{patient}/summary")).json()
    assert any(x["result_entry_id"]==entered.json()["result_entry_id"] for x in summary["laboratory_results"])
    assert await db.scalar(text("SELECT count(*) FROM core.notifications WHERE source_module='Laboratory' AND source_reference_id=:id"),{"id":uuid.UUID(entered.json()["result_entry_id"])}) == 1


@pytest.mark.asyncio
async def test_pharmacy_persists_patient_and_decrements_stock(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    drug = (await c.get("/api/v1/pharmacy/drugs")).json()[0]
    batch = await c.post("/api/v1/pharmacy/batches",json={"drug_id":drug["drug_id"],"batch_number":str(uuid.uuid4()),
        "expiry_date":str(date.today()+timedelta(days=30)),"quantity_received":20,"purchase_price":2,"selling_price":0})
    assert batch.status_code == 201, batch.text
    payload={"patient_id":patient,"dispensing_reference":str(uuid.uuid4()),
             "items":[{"drug_id":drug["drug_id"],"batch_id":batch.json()["batch_id"],"quantity_dispensed":3}]}
    response=await c.post("/api/v1/pharmacy/dispense",json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["total_amount"] == 0  # Free medication must not acquire a fabricated price.
    saved=await db.scalar(text("SELECT patient_id FROM pharmacy.dispensing_records WHERE dispensing_record_id=:id"),
                          {"id":uuid.UUID(response.json()["dispensing_record_id"])})
    assert str(saved) == patient
    quantity=await db.scalar(text("SELECT quantity_remaining FROM pharmacy.pharmacy_stock_batches WHERE batch_id=:id"),
                             {"id":uuid.UUID(batch.json()["batch_id"])})
    assert quantity == 17


@pytest.mark.asyncio
async def test_scheduled_booking_uses_slot_and_rejects_overlap(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    doctor = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    payload={"patient_id":patient,"doctor_id":doctor,"appointment_type":"Scheduled",
             "appointment_date":str(date.today()+timedelta(days=20)),"time_slot":"11:15"}
    response=await c.post("/api/v1/receptionist/appointments/book",json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["appointment_time"] == "11:15 AM"
    assert response.json()["payment_status"] == "Pending billing"
    assert (await c.post("/api/v1/receptionist/appointments/book",json=payload)).status_code == 409


@pytest.mark.asyncio
async def test_doctor_pharmacy_billing_end_to_end(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    doctor = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    drug = (await c.get("/api/v1/pharmacy/drugs")).json()[0]
    encounter = await c.post("/api/v1/emr/encounters", json={
        "patient_id": patient, "doctor_id": doctor, "encounter_type": "OPD",
        "chief_complaint": "Allergy safety test",
        "chief_complaint": "Integration workflow test",
    })
    assert encounter.status_code == 201, encounter.text
    encounter_id = encounter.json()["encounter_id"]
    medication = await c.post(f"/api/v1/emr/encounters/{encounter_id}/prescriptions", json={
        "medications": [{"drug_id": drug["drug_id"], "dosage": "1 tablet",
                         "frequency": "twice daily", "route": "Oral", "duration": "5 days",
                         "quantity_prescribed": 10, "instructions": "After food"}],
    })
    assert medication.status_code == 201, medication.text
    assert medication.json()[0]["medicine_name"] == drug["generic_name"]
    completed = await c.post(f"/api/v1/emr/encounters/{encounter_id}/complete", json={
        "clinical_summary": "Treatment initiated",
    })
    assert completed.status_code == 200, completed.text
    prescription_id = completed.json()["pharmacy_prescription_id"]
    queue = (await c.get("/api/v1/worklists/prescriptions")).json()
    item = next(row for row in queue if row["prescription_id"] == prescription_id)
    assert item["quantity_remaining"] == 10
    batch = await c.post("/api/v1/pharmacy/batches", json={
        "drug_id": drug["drug_id"], "batch_number": str(uuid.uuid4()),
        "expiry_date": str(date.today() + timedelta(days=60)), "quantity_received": 20,
        "purchase_price": 2, "selling_price": 3,
    })
    assert batch.status_code == 201, batch.text
    reference = str(uuid.uuid4())
    dispense = lambda quantity, ref: c.post("/api/v1/pharmacy/dispense", json={
        "patient_id": patient, "prescription_id": prescription_id, "dispensing_reference": ref,
        "items": [{"drug_id": drug["drug_id"], "prescription_item_id": item["prescription_item_id"],
                   "batch_id": batch.json()["batch_id"], "quantity_dispensed": quantity}],
    })
    partial = await dispense(4, reference)
    assert partial.status_code == 201, partial.text
    assert partial.json()["total_amount"] == 12
    assert (await dispense(4, reference)).status_code == 409
    refreshed = next(row for row in (await c.get("/api/v1/worklists/prescriptions")).json()
                     if row["prescription_item_id"] == item["prescription_item_id"])
    assert refreshed["quantity_remaining"] == 6 and refreshed["item_status"] == "Partially Dispensed"
    assert (await dispense(7, str(uuid.uuid4()))).status_code == 409
    final = await dispense(6, str(uuid.uuid4()))
    assert final.status_code == 201, final.text
    refreshed = next(row for row in (await c.get("/api/v1/worklists/prescriptions")).json()
                     if row["prescription_item_id"] == item["prescription_item_id"])
    assert refreshed["quantity_remaining"] == 0 and refreshed["status_name"] == "Dispensed"
    invoice_count = await db.scalar(text("""SELECT count(*) FROM billing.invoice_items
        WHERE item_type='Pharmacy' AND item_reference_id IN
        (SELECT di.dispensing_item_id FROM pharmacy.dispensing_items di
         JOIN pharmacy.dispensing_records dr USING(dispensing_record_id)
         WHERE dr.prescription_id=:id)"""), {"id": uuid.UUID(prescription_id)})
    assert invoice_count == 2


@pytest.mark.asyncio
async def test_prescription_allergy_guard(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    doctor = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    drug = (await c.get("/api/v1/pharmacy/drugs")).json()[0]
    await db.execute(text("""INSERT INTO electronic_medical_records.allergy_records
        (patient_id,allergen_name,allergy_type,reaction_description) VALUES
        (:patient,:name,'Drug','Integration test allergy')"""),
        {"patient": uuid.UUID(patient), "name": drug["generic_name"]})
    encounter = await c.post("/api/v1/emr/encounters", json={
        "patient_id": patient, "doctor_id": doctor, "encounter_type": "OPD",
        "chief_complaint": "Allergy safety test",
    })
    assert encounter.status_code == 201, encounter.text
    response = await c.post(f"/api/v1/emr/encounters/{encounter.json()['encounter_id']}/prescriptions", json={
        "medications": [{"drug_id": drug["drug_id"], "dosage": "1 tablet", "frequency": "daily",
                         "route": "Oral", "duration": "1 day", "quantity_prescribed": 1}],
    })
    assert response.status_code == 409
    assert "Allergy alert" in response.json()["detail"]


@pytest.mark.asyncio
async def test_prescription_substitution_and_cancellation_are_audited(client):
    c, db = client
    patient = str(await db.scalar(text("SELECT patient_id FROM patient.patients LIMIT 1")))
    doctor = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    drugs = (await c.get("/api/v1/pharmacy/drugs")).json()
    assert len(drugs) >= 2, "Seed at least two drugs for substitution testing"
    encounter = await c.post("/api/v1/emr/encounters", json={
        "patient_id": patient, "doctor_id": doctor, "encounter_type": "OPD",
        "chief_complaint": "Prescription amendment test",
    })
    encounter_id = encounter.json()["encounter_id"]
    added = await c.post(f"/api/v1/emr/encounters/{encounter_id}/prescriptions", json={
        "medications": [{"drug_id": drugs[0]["drug_id"], "dosage": "1 tablet",
                         "frequency": "daily", "route": "Oral", "duration": "3 days",
                         "quantity_prescribed": 3}],
    })
    assert added.status_code == 201, added.text
    completed = await c.post(f"/api/v1/emr/encounters/{encounter_id}/complete", json={})
    prescription_id = completed.json()["pharmacy_prescription_id"]
    queue = (await c.get("/api/v1/worklists/prescriptions")).json()
    item = next(row for row in queue if row["prescription_id"] == prescription_id)
    substitute = await c.post(f"/api/v1/pharmacy/prescriptions/{prescription_id}/substitute", json={
        "prescription_item_id": item["prescription_item_id"],
        "replacement_drug_id": drugs[1]["drug_id"], "reason": "Doctor-approved formulary substitution",
    })
    assert substitute.status_code == 200, substitute.text
    amendments = await c.get(f"/api/v1/pharmacy/prescriptions/{prescription_id}/amendments")
    assert amendments.status_code == 200 and amendments.json()[0]["action"] == "Substitution"
    cancelled = await c.post(f"/api/v1/pharmacy/prescriptions/{prescription_id}/cancel", json={
        "reason": "Treatment plan changed before dispensing",
    })
    assert cancelled.status_code == 200, cancelled.text
    amendments = (await c.get(f"/api/v1/pharmacy/prescriptions/{prescription_id}/amendments")).json()
    assert [entry["action"] for entry in amendments] == ["Substitution", "Cancellation"]
    assert not any(row["prescription_id"] == prescription_id
                   for row in (await c.get("/api/v1/worklists/prescriptions")).json())


@pytest.mark.asyncio
async def test_prescription_drug_interaction_guard(client):
    c, db = client
    patient = str(await db.scalar(text("""SELECT p.patient_id FROM patient.patients p
        WHERE NOT EXISTS (SELECT 1 FROM electronic_medical_records.allergy_records a
                          WHERE a.patient_id=p.patient_id) LIMIT 1""")))
    doctor = str(await db.scalar(text("SELECT doctor_id FROM doctor.doctors LIMIT 1")))
    drugs = (await c.get("/api/v1/pharmacy/drugs")).json()
    assert patient and len(drugs) >= 2, "Seed an allergy-free patient and two drugs"
    await db.execute(text("""INSERT INTO pharmacy.drug_interactions
        (drug_id,interacting_drug_id,interaction_severity,interaction_description)
        VALUES (:first,:second,'Severe','Integration test interaction')"""),
        {"first": uuid.UUID(drugs[0]["drug_id"]), "second": uuid.UUID(drugs[1]["drug_id"])})
    encounter = await c.post("/api/v1/emr/encounters", json={
        "patient_id": patient, "doctor_id": doctor, "encounter_type": "OPD",
        "chief_complaint": "Interaction safety test",
    })
    medication = lambda drug: {"drug_id": drug["drug_id"], "dosage": "1 tablet",
        "frequency": "daily", "route": "Oral", "duration": "1 day", "quantity_prescribed": 1}
    response = await c.post(f"/api/v1/emr/encounters/{encounter.json()['encounter_id']}/prescriptions",
                            json={"medications": [medication(drugs[0]), medication(drugs[1])]})
    assert response.status_code == 409
    assert "Drug interaction" in response.json()["detail"]
