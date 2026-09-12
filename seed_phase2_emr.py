"""Seed idempotent Phase 2 EMR master data and one realistic OPD record."""
import asyncio
import json
from datetime import datetime

from sqlalchemy import select

from app.config import async_session, engine
from app.api.doctor import Doctor
from app.models.department import Department  # noqa: F401 - registers FK metadata
from app.models.patient import Patient
from app.models.pharmacy_models import Drug  # noqa: F401 - registers medication FK metadata
from app.models.receptionist_models import Appointment  # noqa: F401 - registers FK metadata
from app.models.emr_models import (
    AllergyRecord, ClinicalNote, Diagnosis, DiagnosisType, EncounterType,
    MedicationRecord, PatientEncounter, SeverityLevel, VitalSign,
)


async def get_or_create(db, model, lookup, **values):
    row = (await db.execute(select(model).filter_by(**lookup))).scalars().first()
    if row:
        return row
    row = model(**lookup, **values)
    db.add(row)
    await db.flush()
    return row


async def seed():
    async with async_session() as db:
        encounter_types = {
            name: await get_or_create(db, EncounterType, {"type_name": name})
            for name in ("OPD", "IPD", "Emergency", "Teleconsultation")
        }
        diagnosis_types = {
            name: await get_or_create(db, DiagnosisType, {"diagnosis_type_name": name})
            for name in ("Primary", "Secondary", "Differential")
        }
        severities = {}
        for rank, name in enumerate(("Mild", "Moderate", "Severe", "Critical", "Life-threatening"), 1):
            severities[name] = await get_or_create(
                db, SeverityLevel, {"severity_name": name}, severity_rank=rank
            )

        patient = (await db.execute(select(Patient).order_by(Patient.created_at))).scalars().first()
        doctor = (await db.execute(select(Doctor).order_by(Doctor.created_at))).scalars().first()
        if not patient or not doctor:
            await db.commit()
            print("EMR master data seeded; add a patient and doctor before seeding the sample encounter.")
            return

        encounter = (await db.execute(
            select(PatientEncounter).where(PatientEncounter.encounter_number == "ENC-DEMO-PHASE2-001")
        )).scalars().first()
        if not encounter:
            encounter = PatientEncounter(
                encounter_number="ENC-DEMO-PHASE2-001", patient_id=patient.patient_id,
                doctor_id=doctor.doctor_id, encounter_type_id=encounter_types["OPD"].encounter_type_id,
                encounter_date=datetime.utcnow(), chief_complaint="Headache, dizziness and elevated blood pressure",
                clinical_summary="Essential hypertension; medication and lifestyle plan initiated.",
                encounter_status="Completed",
            )
            db.add(encounter)
            await db.flush()
            db.add(VitalSign(
                encounter_id=encounter.encounter_id, patient_id=patient.patient_id,
                temperature=37.1, systolic_bp=146, diastolic_bp=92, heart_rate=86,
                respiratory_rate=16, oxygen_saturation=98, height_cm=172,
                weight_kg=78, bmi=26.37, pain_score=3,
            ))
            db.add(ClinicalNote(
                encounter_id=encounter.encounter_id, doctor_id=doctor.doctor_id,
                note_type="SOAP", note_text=json.dumps({
                    "Subjective": "Intermittent morning headache and dizziness for three days.",
                    "Objective": "BP 146/92; cardiovascular and neurological examinations otherwise normal.",
                    "Assessment": "Newly detected essential hypertension.",
                    "Plan": "Start amlodipine, reduce sodium intake, maintain BP diary, review in two weeks.",
                }),
            ))
            db.add(Diagnosis(
                encounter_id=encounter.encounter_id, patient_id=patient.patient_id,
                doctor_id=doctor.doctor_id,
                diagnosis_type_id=diagnosis_types["Primary"].diagnosis_type_id,
                severity_level_id=severities["Moderate"].severity_level_id,
                diagnosis_code="I10", diagnosis_name="Essential (primary) hypertension",
            ))
            db.add(MedicationRecord(
                encounter_id=encounter.encounter_id, patient_id=patient.patient_id,
                doctor_id=doctor.doctor_id, medicine_name="Amlodipine", dosage="5 mg",
                frequency="Once daily", route="Oral", duration="30 days",
                instructions="Take each morning and monitor blood pressure.",
            ))

        allergy = (await db.execute(select(AllergyRecord).where(
            AllergyRecord.patient_id == patient.patient_id,
            AllergyRecord.allergen_name == "Penicillin",
        ))).scalars().first()
        if not allergy:
            db.add(AllergyRecord(
                patient_id=patient.patient_id, allergen_name="Penicillin", allergy_type="Drug",
                reaction_description="Generalized urticaria",
                severity_level_id=severities["Severe"].severity_level_id,
            ))
        await db.commit()
        print("Phase 2 EMR masters and demo clinical record seeded successfully.")


if __name__ == "__main__":
    async def main():
        try:
            await seed()
        finally:
            await engine.dispose()
    asyncio.run(main())
