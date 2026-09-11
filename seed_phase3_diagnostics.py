"""Seed Phase 3 Diagnostic and Pharmacy Masters & Baseline Catalog"""
import asyncio
from datetime import date, datetime
from sqlalchemy import select
from app.config import async_session, engine
from app.api.auth import Role
from app.models.pharmacy_models import Drug, PharmacyStore, PharmacyInventory, PharmacyStockBatch
from app.models.laboratory_models import LabTest, LabTestParameter, SampleType
from app.models.radiology_models import ImagingModality, ImagingRoom, RadiologyTest

async def seed_phase3():
    async with async_session() as db:
        print("1. Ensuring Ancillary Staff Roles...")
        for r_name in ["pharmacist", "lab_technician", "radiologist"]:
            res = await db.execute(select(Role).where(Role.role_name == r_name))
            if not res.scalars().first():
                db.add(Role(role_name=r_name))
        await db.flush()

        print("2. Seeding Pharmacy Formulary & Initial Stock Batches...")
        store_res = await db.execute(select(PharmacyStore).where(PharmacyStore.store_code == "PHARM-MAIN"))
        store = store_res.scalars().first()
        if not store:
            store = PharmacyStore(store_code="PHARM-MAIN", store_name="Central Outpatient Pharmacy")
            db.add(store)
            await db.flush()

        drugs_data = [
            ("DRUG-AML-001", "Amlodipine Besylate", "Amlodipine", "Norvasc", 15.0, 100),
            ("DRUG-PCM-002", "Paracetamol", "Acetaminophen", "Tylenol", 5.0, 250),
            ("DRUG-AMX-003", "Amoxicillin Trihydrate", "Amoxicillin", "Amoxil", 25.0, 120),
            ("DRUG-MET-004", "Metformin Hydrochloride", "Metformin", "Glucophage", 18.0, 150),
            ("DRUG-ATO-005", "Atorvastatin Calcium", "Atorvastatin", "Lipitor", 35.0, 80),
        ]

        for code, generic, sci, brand, price, init_qty in drugs_data:
            res_d = await db.execute(select(Drug).where(Drug.drug_code == code))
            d = res_d.scalars().first()
            if not d:
                d = Drug(drug_code=code, generic_name=generic, scientific_name=sci)
                db.add(d)
                await db.flush()

                inv = PharmacyInventory(pharmacy_store_id=store.pharmacy_store_id, drug_id=d.drug_id, available_quantity=init_qty, reorder_level=20)
                db.add(inv)
                await db.flush()

                batch = PharmacyStockBatch(
                    inventory_id=inv.inventory_id,
                    batch_number=f"BAT-{code[-3:]}-2026",
                    manufacturing_date=date(2025, 6, 1),
                    expiry_date=date(2027, 6, 1),
                    quantity_received=init_qty,
                    quantity_remaining=init_qty,
                    purchase_price=price * 0.6,
                    selling_price=price
                )
                db.add(batch)

        print("3. Seeding Laboratory Test Catalog & Parameters...")
        lab_tests = [
            ("LAB-CBC-01", "Complete Blood Count (CBC)", "Hematology Analyzer", 350.0, [
                ("Hemoglobin", "g/dL", "13.5 - 17.5"),
                ("White Blood Cell Count (WBC)", "x10^3/uL", "4.5 - 11.0"),
                ("Platelet Count", "x10^3/uL", "150 - 450")
            ]),
            ("LAB-LIPID-02", "Lipid Profile", "Photometric Assay", 550.0, [
                ("Total Cholesterol", "mg/dL", "< 200"),
                ("HDL Cholesterol", "mg/dL", "> 40"),
                ("LDL Cholesterol", "mg/dL", "< 100"),
                ("Triglycerides", "mg/dL", "< 150")
            ]),
            ("LAB-HBA1C-03", "Glycated Hemoglobin (HbA1c)", "HPLC", 450.0, [
                ("HbA1c", "%", "4.0 - 5.6")
            ])
        ]

        for tcode, tname, method, price, params in lab_tests:
            res_t = await db.execute(select(LabTest).where(LabTest.test_code == tcode))
            t = res_t.scalars().first()
            if not t:
                t = LabTest(test_code=tcode, test_name=tname, test_method=method, price=price, turnaround_time_hours=4)
                db.add(t)
                await db.flush()
                for pname, unit, nrange in params:
                    db.add(LabTestParameter(test_id=t.test_id, parameter_name=pname, unit=unit, normal_range=nrange))

        print("4. Seeding Radiology Modalities, Rooms & Imaging Tests...")
        xray_res = await db.execute(select(ImagingModality).where(ImagingModality.modality_code == "XRAY"))
        xray_mod = xray_res.scalars().first()
        if not xray_mod:
            xray_mod = ImagingModality(modality_code="XRAY", modality_name="Digital Radiography (X-Ray)")
            db.add(xray_mod)
            await db.flush()

        ct_res = await db.execute(select(ImagingModality).where(ImagingModality.modality_code == "CT"))
        ct_mod = ct_res.scalars().first()
        if not ct_mod:
            ct_mod = ImagingModality(modality_code="CT", modality_name="Computed Tomography (CT Scan)")
            db.add(ct_mod)
            await db.flush()

        mri_res = await db.execute(select(ImagingModality).where(ImagingModality.modality_code == "MRI"))
        mri_mod = mri_res.scalars().first()
        if not mri_mod:
            mri_mod = ImagingModality(modality_code="MRI", modality_name="Magnetic Resonance Imaging (MRI)")
            db.add(mri_mod)
            await db.flush()

        room_res = await db.execute(select(ImagingRoom).where(ImagingRoom.room_code == "RAD-ROOM-1"))
        if not room_res.scalars().first():
            db.add(ImagingRoom(room_code="RAD-ROOM-1", room_name="General Radiography Suite 1", modality_id=xray_mod.modality_id, room_location="1st Floor Diagnostic Center"))

        rad_tests = [
            ("RAD-CXR-01", "Chest X-Ray PA View", xray_mod.modality_id, 450.0),
            ("RAD-CT-ABD-02", "CT Abdomen & Pelvis with Contrast", ct_mod.modality_id, 3500.0),
            ("RAD-MRI-BRN-03", "MRI Brain without Contrast", mri_mod.modality_id, 4500.0)
        ]

        for code, name, mid, price in rad_tests:
            res_rt = await db.execute(select(RadiologyTest).where(RadiologyTest.test_code == code))
            if not res_rt.scalars().first():
                db.add(RadiologyTest(test_code=code, test_name=name, modality_id=mid, price=price, is_active=True))

        await db.commit()
        print("=== Phase 3 Seeding Complete ===")

if __name__ == "__main__":
    async def main():
        try:
            await seed_phase3()
        finally:
            await engine.dispose()
    asyncio.run(main())
