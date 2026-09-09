"""Integration tests run against PostgreSQL; every test rolls back all writes."""
import uuid
from datetime import date, timedelta
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
    for path in ["/nurse", "/pharmacist", "/lab", "/accounts", "/static/js/staff.js",
                 "/api/v1/inpatient/beds", "/api/v1/inpatient/admissions", "/api/v1/billing/invoices",
                 "/api/v1/worklists/laboratory", "/api/v1/worklists/radiology", "/api/v1/worklists/prescriptions"]:
        response = await c.get(path)
        assert response.status_code == 200, (path, response.text)


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
