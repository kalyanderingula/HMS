import asyncio, httpx
import os
from datetime import datetime, timedelta
from main import app

async def test():
    doctor_password = os.environ.get("HMS_TEST_DOCTOR_PASSWORD", "Doctor_@_2024")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/auth/login", json={"username":"DOC-CARD-001","password":doctor_password})
        print("1. Doctor Login:", r.status_code, "Roles:", r.json().get("roles"))
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}"}
        profile = await c.get("/api/v1/doctor/my-profile/current", headers=h)
        print("   Scoped doctor profile:", profile.status_code, profile.json().get("doctor", {}).get("doctor_code"))
        forbidden_admin_api = await c.get("/api/v1/employees/", headers=h)
        print("   Doctor blocked from Admin API:", forbidden_admin_api.status_code)

        rp = await c.get("/api/v1/patients/")
        p0 = rp.json()[0]
        pat_id = p0["patient_id"]
        print("   Patient:", p0["first_name"], p0["last_name"], "MRN:", p0["mrn"])

        profile_data = profile.json().get("doctor", {})
        doc_id = profile_data.get("doctor_id")
        print("   Doctor:", profile_data.get("first_name"), profile_data.get("last_name"), "ID:", doc_id)

        r2 = await c.post("/api/v1/emr/encounters", json={"patient_id":pat_id,"doctor_id":doc_id,"encounter_type":"OPD","chief_complaint":"Persistent headache 3 days, dizziness and mild nausea"}, headers=h)
        print("2. Start Encounter:", r2.status_code, r2.json().get("encounter_number"), r2.json().get("encounter_status"))
        enc_id = r2.json()["encounter_id"]

        r3 = await c.post(f"/api/v1/emr/encounters/{enc_id}/vitals", json={"temperature":37.6,"systolic_bp":145,"diastolic_bp":92,"heart_rate":88,"respiratory_rate":16,"oxygen_saturation":98.2,"height_cm":175.0,"weight_kg":82.0,"pain_score":4}, headers=h)
        print("3. Vital Signs:", r3.status_code)
        v = r3.json()
        print("   BP:", v["systolic_bp"], "/", v["diastolic_bp"], "->", v["bp_status"])
        print("   BMI:", v["bmi"], "->", v["bmi_status"])
        print("   SpO2:", v["oxygen_saturation"], "->", v["spo2_status"])

        r4 = await c.post(f"/api/v1/emr/encounters/{enc_id}/soap-notes", json={"subjective":"Persistent throbbing headache for 3 days, worse in morning, dizziness","objective":"BP 145/92, HR 88, Temp 37.6, SpO2 98%. Neuro exam normal.","assessment":"Stage 1 Hypertension with hypertensive headache ICD-10 I10","plan":"Amlodipine 5mg OD. Low sodium diet. ECHO ordered. Follow up 2 weeks.","is_confidential":False}, headers=h)
        print("4. SOAP Notes:", r4.status_code, r4.json().get("note_type"))

        r5 = await c.post(f"/api/v1/emr/encounters/{enc_id}/diagnoses", json={"diagnosis_code":"I10","diagnosis_name":"Essential Hypertension","diagnosis_description":"Primary hypertension - no secondary cause","diagnosis_type":"Primary","severity":"Moderate"}, headers=h)
        print("5. Diagnosis:", r5.status_code, r5.json().get("diagnosis_code"), r5.json().get("diagnosis_name"), r5.json().get("severity"))

        r6 = await c.post(f"/api/v1/emr/patients/{pat_id}/allergies", json={"allergen_name":"Aspirin","allergy_type":"Drug","reaction_description":"GI bleeding on NSAID use","severity":"Severe"}, headers=h)
        print("6. Allergy:", r6.status_code, r6.json().get("allergen_name"), r6.json().get("severity"))

        drug_catalog = (await c.get("/api/v1/pharmacy/drugs", headers=h)).json()
        if len(drug_catalog) < 2:
            raise RuntimeError("Seed at least two pharmacy drugs before running phase 2")
        r7 = await c.post(f"/api/v1/emr/encounters/{enc_id}/prescriptions", json={"medications":[
            {"drug_id":drug_catalog[0]["drug_id"],"dosage":"5mg","frequency":"OD","route":"Oral","duration":"30 days","quantity_prescribed":30,"instructions":"Take in morning"},
            {"drug_id":drug_catalog[1]["drug_id"],"dosage":"500mg","frequency":"TDS","route":"Oral","duration":"5 days","quantity_prescribed":15,"instructions":"Take with food"}
        ]}, headers=h)
        print("7. Prescriptions:", r7.status_code, len(r7.json()), "medications")
        for m in r7.json():
            print("  Rx:", m["medicine_name"], m["dosage"], m["frequency"])

        rd = await c.get("/api/v1/receptionist/doctors/availability")
        doctors = rd.json()
        receiving = next((d for d in doctors if d["doctor_id"] != doc_id), None)
        if receiving:
            rr = await c.post(f"/api/v1/emr/encounters/{enc_id}/referrals", json={"referred_doctor_id":receiving["doctor_id"],"referral_reason":"Specialist opinion requested"}, headers=h)
            print("7b. Referral Queue Handoff:", rr.status_code, "->", receiving["doctor_name"])
            recipient_login = await c.post("/api/v1/auth/login", json={"username":receiving["doctor_code"],"password":doctor_password})
            if recipient_login.status_code == 200:
                recipient_headers = {"Authorization": f"Bearer {recipient_login.json()['token']}"}
                recipient_queue = await c.get("/api/v1/receptionist/queue/live", headers=recipient_headers)
                handed_off = any(x["patient_id"] == pat_id and x["status"] == "waiting" for x in recipient_queue.json()["tokens"])
                print("    Receiving doctor queue contains patient:", handed_off)
                if not handed_off: print("    Queue response:", recipient_queue.status_code, recipient_queue.json())

        r8 = await c.get(f"/api/v1/emr/patients/{pat_id}/summary", headers=h)
        s = r8.json()
        print("8. Patient 360 Summary:", r8.status_code)
        print("   Allergies:", len(s["active_allergies"]), "| Diagnoses:", len(s["active_diagnoses"]), "| Meds:", len(s["current_medications"]), "| Encounters:", len(s["past_encounters"]))

        r9 = await c.post(f"/api/v1/emr/encounters/{enc_id}/complete", json={"clinical_summary":"Stage 1 HTN - Amlodipine started. Follow up 2 weeks."}, headers=h)
        print("9. Complete Encounter:", r9.status_code, r9.json().get("status"))

        fut = (datetime.utcnow() + timedelta(days=3)).isoformat()
        r10 = await c.post("/api/v1/telemedicine/appointments", json={"patient_id":pat_id,"doctor_id":doc_id,"appointment_datetime":fut,"meeting_platform":"HMS Telehealth"}, headers=h)
        print("10. Telemedicine Appt:", r10.status_code)
        if r10.status_code == 201:
            ta = r10.json()
            print("    Patient:", ta["patient_name"], "| Link:", ta["consultation_link"])
            virtual_id = ta["virtual_appointment_id"]

            r11 = await c.get(f"/api/v1/telemedicine/appointments/{virtual_id}", headers=h)
            print("11. Retrieve Telemedicine Appt:", r11.status_code, r11.json().get("status"))

            r12 = await c.post("/api/v1/telemedicine/sessions/start", json={"virtual_appointment_id":virtual_id}, headers=h)
            print("12. Start Virtual Session:", r12.status_code, r12.json().get("session_status"))
            session_id = r12.json()["session_id"]

            r13 = await c.post(f"/api/v1/telemedicine/sessions/{session_id}/complete", json={"clinical_notes":"Video review completed. Symptoms improving; continue current treatment and BP diary."}, headers=h)
            print("13. Complete Virtual Session:", r13.status_code, r13.json().get("session_status"))

            r14 = await c.get(f"/api/v1/telemedicine/appointments/{virtual_id}", headers=h)
            emr_id = r14.json().get("emr_encounter_id")
            r15 = await c.get(f"/api/v1/emr/encounters/{emr_id}", headers=h)
            print("14. Telemedicine -> EMR Sync:", r15.status_code, r15.json().get("encounter", {}).get("encounter_status"))

asyncio.run(test())
