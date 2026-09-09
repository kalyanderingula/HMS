import asyncio, os, httpx
import uuid
from datetime import datetime, timedelta
from main import app

async def test_phase3():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        # Admin login for full authorization in tests
        r_login = await c.post("/api/v1/auth/login", json={"username":"ADMIN-SUPER-00001", "password":"Admin_@_01011990"})
        print("1. Admin Login:", r_login.status_code)
        token = r_login.json()["token"]
        h = {"Authorization": f"Bearer {token}"}

        # Get baseline patient
        rp = await c.get("/api/v1/patients/")
        patient = rp.json()[0]
        patient_id = patient["patient_id"]
        print("   Patient:", patient["first_name"], patient["last_name"], "| MRN:", patient["mrn"])

        # ----------------------------------------------------
        # TEST 1: PHARMACY
        # ----------------------------------------------------
        print("\n--- Testing Pharmacy Management ---")
        r_drugs = await c.get("/api/v1/pharmacy/drugs", headers=h)
        print("Pharmacy Drug Catalog:", r_drugs.status_code, f"({len(r_drugs.json())} drugs)")
        drug = r_drugs.json()[0]

        r_inv = await c.get("/api/v1/pharmacy/inventory", headers=h)
        inv_item = next(i for i in r_inv.json() if i["drug_id"] == drug["drug_id"])
        batch = inv_item["batches"][0]
        initial_stock = inv_item["available_quantity"]
        print(f"   Drug: {drug['generic_name']} | Stock: {initial_stock} | Batch: {batch['batch_number']}")

        # Dispense 10 units
        dispense_payload = {
            "patient_id": patient_id,
            "dispensing_reference": str(uuid.uuid4()),
            "items": [
                {"drug_id": drug["drug_id"], "batch_id": batch["batch_id"], "quantity_dispensed": 10.0}
            ],
            "notes": "Dispensed 10 tablets for outpatient therapy"
        }
        r_disp = await c.post("/api/v1/pharmacy/dispense", json=dispense_payload, headers=h)
        print("Medication Dispensed:", r_disp.status_code, "| Total Amount: $", r_disp.json().get("total_amount"))

        # Verify stock decrement
        r_inv_after = await c.get("/api/v1/pharmacy/inventory", headers=h)
        inv_after = next(i for i in r_inv_after.json() if i["drug_id"] == drug["drug_id"])
        print("   Stock After Dispensing:", inv_after["available_quantity"], f"(Reduced by {initial_stock - inv_after['available_quantity']})")
        assert inv_after["available_quantity"] == initial_stock - 10.0

        # ----------------------------------------------------
        # TEST 2: LABORATORY (LIS)
        # ----------------------------------------------------
        print("\n--- Testing Laboratory Information System ---")
        r_tests = await c.get("/api/v1/laboratory/tests", headers=h)
        print("Lab Test Catalog:", r_tests.status_code, f"({len(r_tests.json())} tests)")
        cbc_test = next(t for t in r_tests.json() if "CBC" in t["test_code"])

        # 1. Order test
        lab_order_payload = {
            "patient_id": patient_id,
            "priority": "Routine",
            "clinical_notes": "Suspected anemia and fatigue",
            "items": [{"test_id": cbc_test["test_id"]}]
        }
        r_order = await c.post("/api/v1/laboratory/orders", json=lab_order_payload, headers=h)
        order_data = r_order.json()
        order_item = order_data["items"][0]
        print("Lab Order Created:", r_order.status_code, order_data["order_number"], "| Status:", order_data["status"])

        # 2. Collect sample
        sample_payload = {
            "order_item_id": order_item["order_item_id"],
            "sample_type": "Venous Blood"
        }
        r_sample = await c.post("/api/v1/laboratory/collect-sample", json=sample_payload, headers=h)
        sample_data = r_sample.json()
        print("Sample Collected:", r_sample.status_code, "| Barcode:", sample_data["sample_barcode"])

        # 3. Enter test parameter results
        param = cbc_test["parameters"][0]  # Hemoglobin
        result_payload = {
            "order_item_id": order_item["order_item_id"],
            "technician_remarks": "Specimen analyzed on automated hematology counter",
            "parameters": [
                {"parameter_id": param["parameter_id"], "result_value": "11.2", "result_flag": "Low"}
            ]
        }
        r_result = await c.post("/api/v1/laboratory/results", json=result_payload, headers=h)
        res_data = r_result.json()
        print("Results Entered:", r_result.status_code, "| Status:", res_data["result_status"])

        # 4. Pathologist Approval
        r_appr = await c.post(f"/api/v1/laboratory/results/{res_data['result_entry_id']}/approve", headers=h)
        print("Lab Report Approved:", r_appr.status_code, "| Status:", r_appr.json()["result_status"])

        # ----------------------------------------------------
        # TEST 3: RADIOLOGY (RIS & PACS)
        # ----------------------------------------------------
        print("\n--- Testing Radiology Information System ---")
        r_mods = await c.get("/api/v1/radiology/modalities", headers=h)
        print("Radiology Modalities:", r_mods.status_code, [m["modality_code"] for m in r_mods.json()])

        r_rad_tests = await c.get("/api/v1/radiology/tests", headers=h)
        cxr_test = next(t for t in r_rad_tests.json() if "CXR" in t["test_code"])
        print("Imaging Catalog:", r_rad_tests.status_code, f"({len(r_rad_tests.json())} imaging exams)")

        # 1. Place scan order
        rad_order_payload = {
            "patient_id": patient_id,
            "priority": "Routine",
            "clinical_indication": "Persistent cough and dyspnea on exertion",
            "items": [{"radiology_test_id": cxr_test["radiology_test_id"]}]
        }
        r_rad_order = await c.post("/api/v1/radiology/orders", json=rad_order_payload, headers=h)
        rad_order_data = r_rad_order.json()
        rad_item = rad_order_data["items"][0]
        print("Radiology Order Placed:", r_rad_order.status_code, rad_order_data["order_number"])

        # 2. Schedule appointment
        r_rooms = await c.get("/api/v1/radiology/rooms", headers=h)
        room = r_rooms.json()[0]
        now = datetime.utcnow()
        sched_payload = {
            "order_item_id": rad_item["order_item_id"],
            "imaging_room_id": room["imaging_room_id"],
            "scheduled_start": (now + timedelta(hours=1)).isoformat(),
            "scheduled_end": (now + timedelta(hours=1, minutes=30)).isoformat()
        }
        r_sched = await c.post("/api/v1/radiology/schedule", json=sched_payload, headers=h)
        apt_data = r_sched.json()
        print("Radiology Appointment Scheduled:", r_sched.status_code, "| Room:", apt_data["room_name"])

        # 3. Complete imaging study
        study_payload = {
            "radiology_appointment_id": apt_data["radiology_appointment_id"],
            "study_description": "Chest Radiograph PA View - 1 Exposure"
        }
        r_study = await c.post("/api/v1/radiology/studies", json=study_payload, headers=h)
        study_data = r_study.json()
        print("Imaging Study Recorded:", r_study.status_code, "| Accession #:", study_data["accession_number"])

        # 4. Radiologist report & impression
        report_payload = {
            "study_id": study_data["study_id"],
            "findings": "Lungs are clear bilaterally. Cardiothoracic ratio is within normal limits. Both costophrenic angles are sharp.",
            "impression": "No acute cardiopulmonary disease. Normal chest radiograph."
        }
        r_report = await c.post("/api/v1/radiology/reports", json=report_payload, headers=h)
        report_data = r_report.json()
        print("Radiology Diagnostic Report Signed:", r_report.status_code, "| Impression:", report_data["impression"])

        print("\nAll Phase 3 Diagnostic & Ancillary tests passed successfully!")

asyncio.run(test_phase3())
