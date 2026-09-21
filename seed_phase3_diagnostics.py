"""Seed Phase 3 Diagnostic and Pharmacy Masters & Baseline Catalog"""
import asyncio
from datetime import date, datetime, timedelta
from sqlalchemy import select
from app.config import async_session, engine
from app.api.auth import Role
from app.models.pharmacy_models import Drug, PharmacyStore, PharmacyInventory, PharmacyStockBatch
from app.models.laboratory_models import (
    LabTest, LabTestParameter, LabTestCategory, LabTestSubcategory,
    LabTestReferenceRange, LabParameterInterpretationRule,
    SampleType, LabOrderStatus, LabOrderPriority,
    LabOrder, LabOrderItem, LabSample, LabResultEntry, LabResultParameter,
)
from app.models.patient import Patient
from app.models.radiology_models import (
    ImagingModality, ImagingRoom, RadiologyTest, RadiologyObservationDefinition,
)
from scripts.laboratory_catalog import LAB_TEST_CATALOG
from scripts.diagnostic_catalog import DIAGNOSTIC_CATALOG
from scripts.laboratory_reference_data import REFERENCE_RANGES, INTERPRETATION_RULES

async def seed_phase3():
    async with async_session() as db:
        print("1. Ensuring Ancillary Staff Roles...")
        for r_name in ["pharmacist", "lab_technician", "pathologist", "radiologist"]:
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
            ]),
            ("LAB-LFT-04", "Liver Function Test", "Photometric Assay", 650.0, [
                ("Total Bilirubin", "mg/dL", "0.3 - 1.2"), ("ALT (SGPT)", "U/L", "7 - 56"),
                ("AST (SGOT)", "U/L", "10 - 40"), ("Alkaline Phosphatase", "U/L", "44 - 147")
            ]),
            ("LAB-RFT-05", "Renal Function Test", "Kinetic Assay", 600.0, [
                ("Serum Creatinine", "mg/dL", "0.6 - 1.3"), ("Blood Urea Nitrogen", "mg/dL", "7 - 20"),
                ("eGFR", "mL/min/1.73m2", "> 90")
            ]),
            ("LAB-TSH-06", "Thyroid Stimulating Hormone (TSH)", "CLIA", 500.0, [
                ("TSH", "uIU/mL", "0.4 - 4.0")
            ]),
            ("LAB-URINE-07", "Urine Routine Examination", "Microscopy and Dipstick", 250.0, [
                ("pH", "", "4.5 - 8.0"), ("Protein", "", "Negative"),
                ("Glucose", "", "Negative"), ("WBC", "/HPF", "0 - 5")
            ]),
            ("LAB-CRP-08", "C-Reactive Protein (CRP)", "Immunoturbidimetry", 450.0, [
                ("CRP", "mg/L", "< 5")
            ]),
            ("LAB-ELEC-09", "Serum Electrolytes", "Ion Selective Electrode", 500.0, [
                ("Sodium", "mmol/L", "135 - 145"), ("Potassium", "mmol/L", "3.5 - 5.1"),
                ("Chloride", "mmol/L", "98 - 107")
            ]),
            ("LAB-GLU-10", "Fasting Blood Glucose", "Hexokinase", 180.0, [
                ("Glucose", "mg/dL", "70 - 99")
            ])
        ]

        # The compact legacy list above is retained for migration readability;
        # the canonical catalog contains the full clinical definitions.
        lab_tests = LAB_TEST_CATALOG
        category = (await db.execute(select(LabTestCategory).where(
            LabTestCategory.category_name == "Laboratory"))).scalars().first()
        if not category:
            category = LabTestCategory(category_name="Laboratory", description="Clinical laboratory diagnostics")
            db.add(category)
            await db.flush()
        subcategories = {}
        for definition in lab_tests:
            tcode, tname = definition["code"], definition["name"]
            method, price, params = definition["method"], definition["price"], definition["parameters"]
            res_t = await db.execute(select(LabTest).where(LabTest.test_code == tcode))
            t = res_t.scalars().first()
            if not t:
                t = LabTest(test_code=tcode, test_name=tname)
                db.add(t)
                await db.flush()
            t.test_name = tname
            prefix = tcode.split("-")[1] if "-" in tcode else "GENERAL"
            subcategory_name = {
                "CBC":"Hematology", "CMP":"Clinical Biochemistry", "LFT":"Clinical Biochemistry",
                "KFT":"Clinical Biochemistry", "ELEC":"Clinical Biochemistry", "LIPID":"Lipid Studies",
                "THY":"Endocrinology", "DIAB":"Diabetes", "COAG":"Coagulation",
                "IRON":"Vitamins and Nutrition", "CARD":"Cardiac Markers", "INFL":"Immunology",
                "VIT":"Vitamins and Nutrition", "VITD":"Vitamins and Nutrition", "ABG":"Blood Gas",
                "HEP":"Serology", "HIV":"Serology", "BG":"Blood Bank",
            }.get(prefix, "General Laboratory")
            if subcategory_name not in subcategories:
                subcategory = (await db.execute(select(LabTestSubcategory).where(
                    LabTestSubcategory.category_id == category.category_id,
                    LabTestSubcategory.subcategory_name == subcategory_name,
                ))).scalars().first()
                if not subcategory:
                    subcategory = LabTestSubcategory(category_id=category.category_id, subcategory_name=subcategory_name)
                    db.add(subcategory)
                    await db.flush()
                subcategories[subcategory_name] = subcategory
            t.category_id = category.category_id
            t.subcategory_id = subcategories[subcategory_name].subcategory_id
            t.test_method = method
            t.specimen_type = definition["volume"]
            t.performing_department = "Laboratory"
            t.approving_specialty = "Pathology / Laboratory Medicine"
            t.price = price
            t.turnaround_time_hours = definition["tat"]
            t.sample_volume = definition["volume"]
            t.fasting_required = definition["fasting"]
            t.is_active = True
            for parameter in params:
                existing_parameter = await db.execute(select(LabTestParameter).where(
                    LabTestParameter.test_id == t.test_id,
                    LabTestParameter.parameter_name == parameter["name"],
                ))
                lab_parameter = existing_parameter.scalars().first()
                if not lab_parameter:
                    lab_parameter = LabTestParameter(test_id=t.test_id, parameter_name=parameter["name"])
                    db.add(lab_parameter)
                lab_parameter.unit = parameter["unit"]
                lab_parameter.normal_range = parameter["range"]
                lab_parameter.critical_low = parameter["critical_low"]
                lab_parameter.critical_high = parameter["critical_high"]
                lab_parameter.parameter_code = "".join(ch if ch.isalnum() else "_" for ch in parameter["name"].upper()).strip("_")[:100]
                if parameter["name"] == "ABO Group":
                    lab_parameter.result_type, lab_parameter.allowed_values = "ENUM", ["A", "B", "AB", "O"]
                elif parameter["name"] == "Rh(D)":
                    lab_parameter.result_type, lab_parameter.allowed_values = "ENUM", ["Positive", "Negative"]
                elif any(token in parameter["range"] for token in ("Non-reactive", "Positive", "Negative")):
                    lab_parameter.result_type = "QUALITATIVE"
                else:
                    lab_parameter.result_type = "CALCULATED" if "Calculated" in parameter["range"] else "NUMERIC"
                lab_parameter.specimen_type = definition["volume"]
                lab_parameter.method = method
                lab_parameter.display_order = params.index(parameter) + 1

        await db.flush()
        for definition in REFERENCE_RANGES:
            test = (await db.execute(select(LabTest).where(LabTest.test_code == definition["test_code"]))).scalars().first()
            if not test:
                continue
            parameter = (await db.execute(select(LabTestParameter).where(
                LabTestParameter.test_id == test.test_id,
                LabTestParameter.parameter_name == definition["parameter"],
            ))).scalars().first()
            if not parameter:
                continue
            existing_range = (await db.execute(select(LabTestReferenceRange).where(
                LabTestReferenceRange.parameter_id == parameter.parameter_id,
                LabTestReferenceRange.reference_rule == definition["rule"],
                LabTestReferenceRange.sex == definition["sex"],
                LabTestReferenceRange.age_min == definition["age_min"],
                LabTestReferenceRange.age_max == definition["age_max"],
                LabTestReferenceRange.version == 1,
            ))).scalars().first()
            if not existing_range:
                db.add(LabTestReferenceRange(
                    parameter_id=parameter.parameter_id, reference_rule=definition["rule"],
                    sex=definition["sex"], age_min=definition["age_min"], age_max=definition["age_max"],
                    min_value=definition["low"], max_value=definition["high"],
                    critical_low=definition["critical_low"], critical_high=definition["critical_high"],
                    unit=definition["unit"], reference_text=definition["text"],
                    pregnancy_status=definition["pregnancy_status"], trimester=definition["trimester"],
                    source="Illustrative demo interval; local laboratory validation required",
                ))
        for rule in INTERPRETATION_RULES:
            test = (await db.execute(select(LabTest).where(LabTest.test_code == rule["test_code"]))).scalars().first()
            if not test:
                continue
            parameter = (await db.execute(select(LabTestParameter).where(
                LabTestParameter.test_id == test.test_id,
                LabTestParameter.parameter_name == rule["parameter"],
            ))).scalars().first()
            if parameter and not (await db.execute(select(LabParameterInterpretationRule).where(
                LabParameterInterpretationRule.parameter_id == parameter.parameter_id,
                LabParameterInterpretationRule.rule_code == rule["code"],
                LabParameterInterpretationRule.version == 1,
            ))).scalars().first():
                db.add(LabParameterInterpretationRule(
                    parameter_id=parameter.parameter_id, rule_code=rule["code"], label=rule["label"],
                    operator=rule["operator"], lower_value=rule.get("lower"), upper_value=rule.get("upper"),
                    priority=rule["priority"], source="Illustrative clinical category; validate locally",
                ))

        for sample_name in ["Venous Blood", "Capillary Blood", "Serum", "Plasma", "Urine", "Swab", "Sputum"]:
            existing = await db.execute(select(SampleType).where(SampleType.sample_type_name == sample_name))
            if not existing.scalars().first():
                db.add(SampleType(sample_type_name=sample_name))

        print("4. Seeding Laboratory Operational Worklist...")
        statuses = {}
        for status_name in ["Ordered", "Sample Collected", "In Analysis", "Completed", "Cancelled"]:
            result = await db.execute(select(LabOrderStatus).where(LabOrderStatus.status_name == status_name))
            status = result.scalars().first()
            if not status:
                status = LabOrderStatus(status_name=status_name)
                db.add(status)
                await db.flush()
            statuses[status_name] = status
        priorities = {}
        for level, priority_name in enumerate(["Routine", "Urgent", "STAT"], 1):
            result = await db.execute(select(LabOrderPriority).where(LabOrderPriority.priority_name == priority_name))
            priority = result.scalars().first()
            if not priority:
                priority = LabOrderPriority(priority_name=priority_name, priority_level=level)
                db.add(priority)
                await db.flush()
            priorities[priority_name] = priority
        await db.flush()

        patients = (await db.execute(select(Patient).where(Patient.deleted_at.is_(None)).order_by(Patient.created_at).limit(4))).scalars().all()
        tests = (await db.execute(select(LabTest).where(LabTest.is_active.is_(True)).order_by(LabTest.test_code).limit(4))).scalars().all()
        demo_states = [
            ("Ordered", "Routine", None),
            ("Sample Collected", "Urgent", None),
            ("In Analysis", "STAT", "Entered"),
            ("Completed", "Routine", "Approved"),
        ]
        for index, (patient, test, state) in enumerate(zip(patients, tests, demo_states), 1):
            order_number = f"LAB-DEMO-2026-{index:04d}"
            exists = await db.execute(select(LabOrder).where(LabOrder.order_number == order_number))
            if exists.scalars().first():
                continue
            order = LabOrder(
                order_number=order_number, patient_id=patient.patient_id,
                lab_order_status_id=statuses[state[0]].lab_order_status_id,
                priority_id=priorities[state[1]].priority_id,
                ordered_at=datetime.utcnow() - timedelta(hours=5-index),
                clinical_notes="Demonstration diagnostic worklist record",
            )
            db.add(order)
            await db.flush()
            item = LabOrderItem(lab_order_id=order.lab_order_id, test_id=test.test_id, order_status=state[0])
            db.add(item)
            await db.flush()
            if state[0] != "Ordered":
                sample_type = (await db.execute(select(SampleType).where(SampleType.sample_type_name == "Venous Blood"))).scalars().first()
                db.add(LabSample(
                    sample_barcode=f"SMP-DEMO-{index:05d}", order_item_id=item.order_item_id,
                    sample_type_id=sample_type.sample_type_id if sample_type else None,
                    collected_at=datetime.utcnow() - timedelta(hours=4-index),
                ))
            if state[2]:
                entered_at = datetime.utcnow() - timedelta(hours=2)
                entry = LabResultEntry(
                    order_item_id=item.order_item_id, result_status=state[2], entered_at=entered_at,
                    approved_at=datetime.utcnow() - timedelta(hours=1) if state[2] == "Approved" else None,
                    remarks="Quality control passed; demo result for portal validation.",
                )
                db.add(entry)
                await db.flush()
                parameters = (await db.execute(select(LabTestParameter).where(LabTestParameter.test_id == test.test_id))).scalars().all()
                for parameter_index, parameter in enumerate(parameters, 1):
                    db.add(LabResultParameter(
                        result_entry_id=entry.result_entry_id, parameter_id=parameter.parameter_id,
                        result_value=str(10 + parameter_index), result_flag="Normal",
                    ))

        print("5. Seeding Radiology Modalities, Rooms & Imaging Tests...")
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

        modality_definitions = {
            "USG": "Ultrasonography (Ultrasound)", "MAMMO": "Mammography",
            "NM": "Nuclear Medicine", "PET": "PET / PET-CT",
            "DEXA": "Bone Densitometry (DEXA)", "DENTAL": "Dental Radiography",
        }
        modalities = {"XRAY": xray_mod, "CT": ct_mod, "MRI": mri_mod}
        for code, name in modality_definitions.items():
            modality = (await db.execute(select(ImagingModality).where(
                ImagingModality.modality_code == code))).scalars().first()
            if not modality:
                modality = ImagingModality(modality_code=code, modality_name=name)
                db.add(modality)
                await db.flush()
            modalities[code] = modality

        modality_by_subcategory = {
            "X-Ray": "XRAY", "CT": "CT", "CT Angiography": "CT",
            "MRI": "MRI", "Ultrasound": "USG", "Doppler": "USG",
            "Mammography": "MAMMO", "PET": "PET", "Scintigraphy": "NM",
            "Bone Density": "DEXA", "Dental Imaging": "DENTAL",
        }
        base_prices = {"XRAY": 450, "CT": 3500, "MRI": 4500, "USG": 1200,
                       "MAMMO": 1800, "NM": 4000, "PET": 12000,
                       "DEXA": 1800, "DENTAL": 900}
        rad_tests = []
        for definition in DIAGNOSTIC_CATALOG:
            modality_code = modality_by_subcategory.get(definition["subcategory"])
            if modality_code:
                rad_tests.append((
                    f'DX-{definition["code"]}', definition["name"],
                    modalities[modality_code].modality_id, base_prices[modality_code],
                ))

        for code, name, mid, price in rad_tests:
            res_rt = await db.execute(select(RadiologyTest).where(RadiologyTest.test_code == code))
            radiology_test = res_rt.scalars().first()
            if not radiology_test:
                radiology_test = RadiologyTest(test_code=code, test_name=name, modality_id=mid, price=price, is_active=True)
                db.add(radiology_test)
                await db.flush()
            catalog_code = code.removeprefix("DX-")
            catalog_definition = next((row for row in DIAGNOSTIC_CATALOG if row["code"] == catalog_code), None)
            if catalog_definition:
                for index, observation_name in enumerate(catalog_definition["parameters"], 1):
                    observation_code = "".join(ch if ch.isalnum() else "_" for ch in observation_name.upper()).strip("_")[:100]
                    exists = (await db.execute(select(RadiologyObservationDefinition).where(
                        RadiologyObservationDefinition.radiology_test_id == radiology_test.radiology_test_id,
                        RadiologyObservationDefinition.observation_code == observation_code,
                    ))).scalars().first()
                    if not exists:
                        db.add(RadiologyObservationDefinition(
                            radiology_test_id=radiology_test.radiology_test_id,
                            observation_code=observation_code, observation_name=observation_name,
                            result_type="TEXT", display_order=index,
                        ))

        await db.commit()
        print("=== Phase 3 Seeding Complete ===")

if __name__ == "__main__":
    async def main():
        try:
            await seed_phase3()
        finally:
            await engine.dispose()
    asyncio.run(main())
