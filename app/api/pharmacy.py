import uuid
import json
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.emr_models import MedicationRecord, AllergyRecord
from app.models.pharmacy_models import (
    Drug, PharmacyStore, PharmacyInventory, PharmacyStockBatch,
    Prescription, PrescriptionItem, PrescriptionStatus,
    DispensingRecord, DispensingItem, PrescriptionAmendment,
    PharmacistReview
)
from app.schemas.pharmacy import (
    DrugCreateRequest, DrugResponse,
    StockBatchReceiveRequest, StockBatchResponse,
    InventoryStatusResponse, DispensePrescriptionRequest,
    DispensingRecordResponse, DispensedItemResponse,
    PrescriptionAmendRequest, PrescriptionCancelRequest
)
from app.schemas.specialized_operations import (
    BulkDispenseRequest, BulkDispenseResponse,
    PharmacistReviewCreate, PharmacistReviewResponse
)

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy Management"])


async def create_dispensing_invoice(db, patient_id, dispensing_record_id, items, created_by):
    """Create one source-linked pharmacy invoice atomically with dispensing."""
    existing = await db.scalar(text("""SELECT invoice_id FROM billing.invoice_items
        WHERE item_type='Pharmacy' AND item_reference_id=:source LIMIT 1"""),
        {"source": dispensing_record_id})
    if existing:
        return existing
    account = await db.scalar(text("""SELECT billing_account_id FROM billing.billing_accounts
        WHERE patient_id=:patient ORDER BY created_at LIMIT 1 FOR UPDATE"""), {"patient": patient_id})
    if not account:
        account = uuid.uuid4()
        await db.execute(text("""INSERT INTO billing.billing_accounts
            (billing_account_id,patient_id,account_number,account_status,total_due,total_paid)
            VALUES (:id,:patient,:number,'Active',0,0)"""),
            {"id": account, "patient": patient_id, "number": f"ACC-{uuid.uuid4().hex}"})
    total = sum((Decimal(str(item["total"])) for item in items), Decimal("0.00"))
    billing_status = "Paid" if total == 0 else "Pending"
    status_id = await db.scalar(text("""INSERT INTO billing.billing_statuses(status_name)
        VALUES (:status) ON CONFLICT(status_name) DO UPDATE SET status_name=EXCLUDED.status_name
        RETURNING billing_status_id"""), {"status": billing_status})
    invoice_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO billing.invoices
        (invoice_id,invoice_number,billing_account_id,patient_id,billing_status_id,
         subtotal_amount,tax_amount,discount_amount,total_amount,paid_amount,balance_amount,notes,created_by)
        VALUES (:id,:number,:account,:patient,:status,:total,0,0,:total,0,:total,:notes,:user)"""),
        {"id": invoice_id, "number": f"INV-PH-{uuid.uuid4().hex[:14].upper()}", "account": account,
         "patient": patient_id, "status": status_id, "total": total,
         "notes": "Automatically generated from pharmacy dispensing", "user": created_by})
    for item in items:
        await db.execute(text("""INSERT INTO billing.invoice_items
            (invoice_id,item_type,item_reference_id,item_name,quantity,unit_price,
             tax_amount,discount_amount,line_total) VALUES
            (:invoice,'Pharmacy',:source,:name,:quantity,:price,0,0,:total)"""),
            {"invoice": invoice_id, "source": item["source"], "name": item["name"],
             "quantity": item["quantity"], "price": item["price"], "total": item["total"]})
    await db.execute(text("""UPDATE billing.billing_accounts SET total_due=COALESCE(total_due,0)+:total,
        updated_at=CURRENT_TIMESTAMP WHERE billing_account_id=:account"""),
        {"account": account, "total": total})
    return invoice_id

async def ensure_pharmacy_masters(db: AsyncSession):
    for st in ["Pending", "Partially Dispensed", "Dispensed", "Cancelled"]:
        res = await db.execute(select(PrescriptionStatus).where(PrescriptionStatus.status_name == st))
        if not res.scalars().first():
            db.add(PrescriptionStatus(status_name=st))
    
    res_store = await db.execute(select(PharmacyStore).limit(1))
    if not res_store.scalars().first():
        db.add(PharmacyStore(store_code="PHARM-MAIN", store_name="Central Outpatient Pharmacy"))
    
    await db.commit()


async def get_or_create_prescription_status(db: AsyncSession, name: str):
    status_obj = (await db.execute(select(PrescriptionStatus).where(
        PrescriptionStatus.status_name == name))).scalars().first()
    if not status_obj:
        status_obj = PrescriptionStatus(status_name=name)
        db.add(status_obj)
        await db.flush()
    return status_obj


# ----------------- Drugs -----------------
@router.get("/drugs", response_model=List[DrugResponse])
async def list_drugs(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "doctor", "nurse", "admin"]))
):
    query = select(Drug)
    if q:
        query = query.where(Drug.generic_name.ilike(f"%{q}%") | Drug.drug_code.ilike(f"%{q}%"))
    res = await db.execute(query.order_by(Drug.generic_name).limit(50))
    drugs = res.scalars().all()
    return [
        DrugResponse(
            drug_id=d.drug_id, drug_code=d.drug_code, generic_name=d.generic_name,
            scientific_name=d.scientific_name, brand_name=None, dosage_form="Tablet",
            strength="Standard", is_controlled_substance=d.is_controlled_substance,
            requires_prescription=d.requires_prescription, storage_conditions=d.storage_conditions,
            created_at=d.created_at
        ) for d in drugs
    ]

@router.post("/drugs", response_model=DrugResponse, status_code=201)
async def create_drug(
    req: DrugCreateRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "admin", "super_admin"]))
):
    await ensure_pharmacy_masters(db)
    existing = await db.execute(select(Drug).where(Drug.drug_code == req.drug_code))
    if existing.scalars().first():
        raise HTTPException(400, "Drug code already exists")
    
    d = Drug(
        drug_code=req.drug_code, generic_name=req.generic_name, scientific_name=req.scientific_name,
        is_controlled_substance=req.is_controlled_substance, requires_prescription=req.requires_prescription,
        storage_conditions=req.storage_conditions, description=req.description
    )
    db.add(d)
    await db.flush()

    store_res = await db.execute(select(PharmacyStore).limit(1))
    store = store_res.scalars().first()
    inv = PharmacyInventory(
        pharmacy_store_id=store.pharmacy_store_id if store else None,
        drug_id=d.drug_id, available_quantity=0, reserved_quantity=0, reorder_level=10
    )
    db.add(inv)
    await db.commit()
    await db.refresh(d)

    return DrugResponse(
        drug_id=d.drug_id, drug_code=d.drug_code, generic_name=d.generic_name,
        scientific_name=d.scientific_name, brand_name=req.brand_name, dosage_form=req.dosage_form,
        strength=req.strength, is_controlled_substance=d.is_controlled_substance,
        requires_prescription=d.requires_prescription, storage_conditions=d.storage_conditions,
        created_at=d.created_at
    )

# ----------------- Stock Batches & Inventory -----------------
@router.post("/batches", response_model=StockBatchResponse, status_code=201)
async def receive_stock_batch(
    req: StockBatchReceiveRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "admin", "super_admin"]))
):
    drug_res = await db.execute(select(Drug).where(Drug.drug_id == req.drug_id).with_for_update())
    drug = drug_res.scalars().first()
    if not drug: raise HTTPException(404, "Drug not found")

    inv_res = await db.execute(select(PharmacyInventory).where(PharmacyInventory.drug_id == req.drug_id).with_for_update())
    inv = inv_res.scalars().first()
    if not inv:
        store_res = await db.execute(select(PharmacyStore).limit(1))
        store = store_res.scalars().first()
        inv = PharmacyInventory(
            pharmacy_store_id=store.pharmacy_store_id if store else None,
            drug_id=req.drug_id, available_quantity=0, reserved_quantity=0, reorder_level=10
        )
        db.add(inv)
        await db.flush()

    batch = PharmacyStockBatch(
        inventory_id=inv.inventory_id,
        batch_number=req.batch_number,
        manufacturing_date=req.manufacturing_date,
        expiry_date=req.expiry_date,
        quantity_received=req.quantity_received,
        quantity_remaining=req.quantity_received,
        purchase_price=req.purchase_price,
        selling_price=req.selling_price
    )
    db.add(batch)
    inv.available_quantity = float(inv.available_quantity or 0) + float(req.quantity_received)
    await db.commit()
    await db.refresh(batch)

    return StockBatchResponse(
        batch_id=batch.batch_id, inventory_id=inv.inventory_id, drug_id=drug.drug_id,
        generic_name=drug.generic_name, batch_number=batch.batch_number,
        manufacturing_date=batch.manufacturing_date, expiry_date=batch.expiry_date,
        quantity_received=float(batch.quantity_received), quantity_remaining=float(batch.quantity_remaining),
        purchase_price=float(batch.purchase_price), selling_price=float(batch.selling_price),
        is_expired=batch.expiry_date < date.today()
    )

@router.get("/inventory", response_model=List[InventoryStatusResponse])
async def get_inventory(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "doctor", "nurse", "admin"]))
):
    inv_res = await db.execute(select(PharmacyInventory))
    inventories = inv_res.scalars().all()
    results = []
    for inv in inventories:
        d_res = await db.execute(select(Drug).where(Drug.drug_id == inv.drug_id))
        d = d_res.scalars().first()
        if not d: continue

        b_res = await db.execute(select(PharmacyStockBatch).where(PharmacyStockBatch.inventory_id == inv.inventory_id))
        batches_raw = b_res.scalars().all()
        batch_items = [
            StockBatchResponse(
                batch_id=b.batch_id, inventory_id=inv.inventory_id, drug_id=d.drug_id,
                generic_name=d.generic_name, batch_number=b.batch_number,
                manufacturing_date=b.manufacturing_date, expiry_date=b.expiry_date,
                quantity_received=float(b.quantity_received), quantity_remaining=float(b.quantity_remaining),
                purchase_price=float(b.purchase_price), selling_price=float(b.selling_price),
                is_expired=b.expiry_date < date.today()
            ) for b in batches_raw
        ]
        avail = sum(float(b.quantity_remaining) for b in batches_raw if b.expiry_date >= date.today())
        reorder = float(inv.reorder_level or 10)
        results.append(InventoryStatusResponse(
            inventory_id=inv.inventory_id, drug_id=d.drug_id, drug_code=d.drug_code,
            generic_name=d.generic_name, available_quantity=avail,
            reserved_quantity=float(inv.reserved_quantity or 0),
            reorder_level=reorder, is_low_stock=avail <= reorder,
            batches=batch_items
        ))
    return results

# ----------------- Dispensing -----------------
@router.post("/dispense", response_model=DispensingRecordResponse, status_code=201)
async def dispense_medication(
    req: DispensePrescriptionRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "admin", "super_admin"]))
):
    if await db.scalar(select(DispensingRecord.dispensing_record_id).where(
        DispensingRecord.dispensing_reference == req.dispensing_reference)):
        raise HTTPException(409, "This dispensing request was already processed")
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    prescription = None
    if req.prescription_id:
        prescription = (await db.execute(select(Prescription).where(
            Prescription.prescription_id == req.prescription_id).with_for_update())).scalars().first()
        if not prescription:
            raise HTTPException(404, "Prescription not found")
        if prescription.patient_id != req.patient_id:
            raise HTTPException(409, "Prescription does not belong to this patient")
        prescription_status = await db.get(PrescriptionStatus, prescription.prescription_status_id)
        if prescription_status and prescription_status.status_name in ("Dispensed", "Cancelled"):
            raise HTTPException(409, f"Prescription is already {prescription_status.status_name.lower()}")
        if any(item.prescription_item_id is None for item in req.items):
            raise HTTPException(422, "A prescription item is required for prescription dispensing")

    rec = DispensingRecord(
        patient_id=req.patient_id,
        prescription_id=req.prescription_id,
        dispensing_reference=req.dispensing_reference,
        dispensed_by=cu.user_id,
        dispensing_date=datetime.utcnow(),
        dispensing_status="Completed",
        notes=req.notes
    )
    db.add(rec)
    await db.flush()

    total_amount = Decimal("0.00")
    dispensed_items = []
    invoice_items = []
    touched_prescription_items = []

    for item in sorted(req.items, key=lambda item: str(item.batch_id)):
        batch_res = await db.execute(select(PharmacyStockBatch).where(PharmacyStockBatch.batch_id == item.batch_id).with_for_update())
        batch = batch_res.scalars().first()
        if not batch: raise HTTPException(404, f"Batch {item.batch_id} not found")

        prescription_item = None
        if item.prescription_item_id:
            prescription_item = (await db.execute(select(PrescriptionItem).where(
                PrescriptionItem.prescription_item_id == item.prescription_item_id).with_for_update())).scalars().first()
            if not prescription_item:
                raise HTTPException(404, "Prescription item not found")
            if not prescription or prescription_item.prescription_id != prescription.prescription_id:
                raise HTTPException(409, "Prescription item does not belong to this prescription")
            if prescription_item.drug_id != item.drug_id:
                raise HTTPException(409, "Dispensed drug does not match the prescription item")
            remaining = Decimal(str(prescription_item.quantity_prescribed or 0)) - Decimal(str(prescription_item.quantity_dispensed or 0))
            if Decimal(str(item.quantity_dispensed)) > remaining:
                raise HTTPException(409, f"Quantity exceeds the prescribed balance of {remaining}")

        if batch.expiry_date < date.today():
            raise HTTPException(400, "Cannot dispense expired stock")
        if float(batch.quantity_remaining) < item.quantity_dispensed:
            raise HTTPException(400, f"Insufficient quantity in batch {batch.batch_number}. Available: {batch.quantity_remaining}")

        batch.quantity_remaining = float(batch.quantity_remaining) - float(item.quantity_dispensed)

        inv_res = await db.execute(select(PharmacyInventory).where(PharmacyInventory.inventory_id == batch.inventory_id).with_for_update())
        inv = inv_res.scalars().first()
        if not inv or inv.drug_id != item.drug_id:
            raise HTTPException(400, "Selected batch does not belong to the selected drug")
        if inv:
            inv.available_quantity = max(0, float(inv.available_quantity or 0) - float(item.quantity_dispensed))

        di = DispensingItem(
            dispensing_record_id=rec.dispensing_record_id,
            prescription_item_id=item.prescription_item_id,
            batch_id=batch.batch_id,
            quantity_dispensed=item.quantity_dispensed
        )
        db.add(di)
        await db.flush()

        if prescription_item:
            prescription_item.quantity_dispensed = Decimal(str(prescription_item.quantity_dispensed or 0)) + Decimal(str(item.quantity_dispensed))
            prescribed = Decimal(str(prescription_item.quantity_prescribed or 0))
            prescription_item.item_status = "Dispensed" if prescription_item.quantity_dispensed >= prescribed else "Partially Dispensed"
            touched_prescription_items.append(prescription_item)

        d_res = await db.execute(select(Drug).where(Drug.drug_id == item.drug_id))
        drug = d_res.scalars().first()
        price = Decimal(str(batch.selling_price or 0))
        item_total = (price * Decimal(str(item.quantity_dispensed))).quantize(Decimal("0.01"))
        total_amount += item_total
        invoice_items.append({"source": di.dispensing_item_id, "name": drug.generic_name if drug else "Medication",
                              "quantity": item.quantity_dispensed, "price": price, "total": item_total})

        dispensed_items.append(DispensedItemResponse(
            dispensing_item_id=di.dispensing_item_id,
            drug_id=item.drug_id,
            generic_name=drug.generic_name if drug else "Medication",
            batch_number=batch.batch_number,
            quantity_dispensed=float(item.quantity_dispensed),
            unit_price=float(price),
            total_price=float(item_total)
        ))

    if prescription:
        all_items = (await db.execute(select(PrescriptionItem).where(
            PrescriptionItem.prescription_id == prescription.prescription_id))).scalars().all()
        fully_dispensed = all(Decimal(str(item.quantity_dispensed or 0)) >= Decimal(str(item.quantity_prescribed or 0)) for item in all_items)
        status_name = "Dispensed" if fully_dispensed else "Partially Dispensed"
        status_obj = await get_or_create_prescription_status(db, status_name)
        prescription.prescription_status_id = status_obj.prescription_status_id
        for item in all_items:
            if item.medication_record_id:
                medication = await db.get(MedicationRecord, item.medication_record_id)
                if medication:
                    medication.medication_status = item.item_status
    await create_dispensing_invoice(db, patient.patient_id, rec.dispensing_record_id, invoice_items, cu.user_id)
    await db.commit()

    return DispensingRecordResponse(
        dispensing_record_id=rec.dispensing_record_id,
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn,
        dispensing_date=rec.dispensing_date,
        dispensing_status=rec.dispensing_status,
        total_amount=float(total_amount),
        items=dispensed_items,
        notes=rec.notes
    )


@router.post("/prescriptions/{prescription_id}/substitute")
async def substitute_prescription_item(
    prescription_id: uuid.UUID,
    req: PrescriptionAmendRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"])),
):
    prescription = (await db.execute(select(Prescription).where(
        Prescription.prescription_id == prescription_id).with_for_update())).scalars().first()
    item = (await db.execute(select(PrescriptionItem).where(
        PrescriptionItem.prescription_item_id == req.prescription_item_id).with_for_update())).scalars().first()
    replacement = await db.get(Drug, req.replacement_drug_id)
    if not prescription or not item or item.prescription_id != prescription_id:
        raise HTTPException(404, "Prescription item not found")
    if not replacement:
        raise HTTPException(404, "Replacement drug not found")
    if Decimal(str(item.quantity_dispensed or 0)) > 0:
        raise HTTPException(409, "A dispensed item cannot be substituted; issue a new prescription")
    other_drug_ids = set((await db.execute(select(PrescriptionItem.drug_id).where(
        PrescriptionItem.prescription_id == prescription_id,
        PrescriptionItem.prescription_item_id != item.prescription_item_id,
        PrescriptionItem.item_status != "Cancelled",
    ))).scalars().all())
    if replacement.drug_id in other_drug_ids:
        raise HTTPException(409, "The replacement drug is already on this prescription")
    allergy_names = (await db.execute(select(AllergyRecord.allergen_name).where(
        AllergyRecord.patient_id == prescription.patient_id,
        func.lower(AllergyRecord.allergy_type).in_(["drug", "medication"]),
    ))).scalars().all()
    replacement_names = " ".join(filter(None, [replacement.generic_name, replacement.scientific_name])).lower()
    if any(name and name.lower() in replacement_names for name in allergy_names):
        raise HTTPException(409, f"Allergy alert: patient is allergic to {replacement.generic_name}")
    interaction = await db.execute(text("""SELECT d1.generic_name AS first_drug,
        d2.generic_name AS second_drug,di.interaction_severity,di.interaction_description
        FROM pharmacy.drug_interactions di JOIN pharmacy.drugs d1 ON d1.drug_id=di.drug_id
        JOIN pharmacy.drugs d2 ON d2.drug_id=di.interacting_drug_id
        WHERE (di.drug_id=:replacement AND di.interacting_drug_id=ANY(:others))
           OR (di.interacting_drug_id=:replacement AND di.drug_id=ANY(:others)) LIMIT 1"""),
        {"replacement": replacement.drug_id, "others": list(other_drug_ids)}) if other_drug_ids else None
    interaction_row = interaction.mappings().first() if interaction else None
    if interaction_row:
        raise HTTPException(409, f"Drug interaction ({interaction_row['interaction_severity'] or 'unspecified'}): "
                                     f"{interaction_row['first_drug']} + {interaction_row['second_drug']}. "
                                     f"{interaction_row['interaction_description'] or ''}".strip())
    old_drug = await db.get(Drug, item.drug_id)
    before = {"drug_id": str(item.drug_id), "drug_name": old_drug.generic_name if old_drug else None}
    item.drug_id = replacement.drug_id
    if item.medication_record_id:
        medication = await db.get(MedicationRecord, item.medication_record_id)
        if medication:
            medication.drug_id = replacement.drug_id
            medication.medicine_name = replacement.generic_name
    await db.execute(text("""INSERT INTO pharmacy.prescription_amendments
        (prescription_id,prescription_item_id,action,reason,before_value,after_value,amended_by)
        VALUES (:prescription,:item,'Substitution',:reason,CAST(:before AS jsonb),CAST(:after AS jsonb),:user)"""),
        {"prescription": prescription_id, "item": item.prescription_item_id, "reason": req.reason,
         "before": json.dumps(before), "after": json.dumps({"drug_id": str(replacement.drug_id),
         "drug_name": replacement.generic_name}), "user": cu.user_id})
    await db.commit()
    return {"message": "Prescription item substituted", "prescription_id": str(prescription_id),
            "prescription_item_id": str(item.prescription_item_id), "drug_id": str(replacement.drug_id),
            "drug_name": replacement.generic_name}


@router.post("/prescriptions/{prescription_id}/cancel")
async def cancel_prescription(
    prescription_id: uuid.UUID,
    req: PrescriptionCancelRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"])),
):
    prescription = (await db.execute(select(Prescription).where(
        Prescription.prescription_id == prescription_id).with_for_update())).scalars().first()
    if not prescription:
        raise HTTPException(404, "Prescription not found")
    items = (await db.execute(select(PrescriptionItem).where(
        PrescriptionItem.prescription_id == prescription_id).with_for_update())).scalars().all()
    if any(Decimal(str(item.quantity_dispensed or 0)) > 0 for item in items):
        raise HTTPException(409, "A partially or fully dispensed prescription cannot be cancelled")
    cancelled = (await db.execute(select(PrescriptionStatus).where(
        PrescriptionStatus.status_name == "Cancelled"))).scalars().first()
    if cancelled and prescription.prescription_status_id == cancelled.prescription_status_id:
        raise HTTPException(409, "Prescription is already cancelled")
    before_status = await db.get(PrescriptionStatus, prescription.prescription_status_id)
    if not cancelled:
        cancelled = PrescriptionStatus(status_name="Cancelled")
        db.add(cancelled)
        await db.flush()
    prescription.prescription_status_id = cancelled.prescription_status_id
    for item in items:
        item.item_status = "Cancelled"
        if item.medication_record_id:
            medication = await db.get(MedicationRecord, item.medication_record_id)
            if medication:
                medication.medication_status = "Cancelled"
                medication.ended_at = datetime.utcnow()
    await db.execute(text("""INSERT INTO pharmacy.prescription_amendments
        (prescription_id,action,reason,before_value,after_value,amended_by)
        VALUES (:prescription,'Cancellation',:reason,CAST(:before AS jsonb),CAST(:after AS jsonb),:user)"""),
        {"prescription": prescription_id, "reason": req.reason,
         "before": json.dumps({"status": before_status.status_name if before_status else None}),
         "after": json.dumps({"status": "Cancelled"}), "user": cu.user_id})
    await db.commit()
    return {"message": "Prescription cancelled", "prescription_id": str(prescription_id)}


@router.get("/prescriptions/{prescription_id}/amendments")
async def prescription_amendments(
    prescription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "doctor", "admin"])),
):
    rows = await db.execute(text("""SELECT amendment_id,prescription_item_id,action,reason,
        before_value,after_value,amended_by,amended_at FROM pharmacy.prescription_amendments
        WHERE prescription_id=:id ORDER BY amended_at"""), {"id": prescription_id})
    return [dict(row) for row in rows.mappings()]


# ----------------- Milestone 3: Bulk Dispensing & Pharmacist Review -----------------

@router.post("/dispense-bulk", response_model=BulkDispenseResponse, status_code=201)
async def dispense_bulk_prescription(
    req: BulkDispenseRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "admin", "super_admin"]))
):
    """Dispense multiple prescription line items in a single atomic transaction with consolidated billing."""
    # Check duplicate reference
    if await db.scalar(select(DispensingRecord.dispensing_record_id).where(
        DispensingRecord.dispensing_reference == req.dispensing_reference)):
        raise HTTPException(409, "This dispensing request reference was already processed")

    patient = await db.get(Patient, req.patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")

    prescription = (await db.execute(
        select(Prescription).where(Prescription.prescription_id == req.prescription_id).with_for_update()
    )).scalars().first()
    if not prescription:
        raise HTTPException(404, "Prescription not found")
    if prescription.patient_id != req.patient_id:
        raise HTTPException(409, "Prescription does not belong to this patient")

    status_obj = await db.get(PrescriptionStatus, prescription.prescription_status_id)
    if status_obj and status_obj.status_name in ("Dispensed", "Cancelled"):
        raise HTTPException(409, f"Prescription is already {status_obj.status_name.lower()}")

    # Create parent dispensing record
    rec = DispensingRecord(
        patient_id=req.patient_id,
        prescription_id=req.prescription_id,
        dispensing_reference=req.dispensing_reference,
        dispensed_by=cu.user_id,
        dispensing_date=datetime.utcnow(),
        dispensing_status="Completed",
        notes=req.notes
    )
    db.add(rec)
    await db.flush()

    total_amount = Decimal("0.00")
    invoice_items = []
    touched_items = []

    # Sort items by batch_id to avoid deadlocks
    for item in sorted(req.items, key=lambda x: str(x.batch_id)):
        batch = (await db.execute(
            select(PharmacyStockBatch).where(PharmacyStockBatch.batch_id == item.batch_id).with_for_update()
        )).scalars().first()
        if not batch:
            raise HTTPException(404, f"Batch {item.batch_id} not found")

        prescription_item = (await db.execute(
            select(PrescriptionItem).where(
                PrescriptionItem.prescription_item_id == item.prescription_item_id
            ).with_for_update()
        )).scalars().first()
        if not prescription_item:
            raise HTTPException(404, f"Prescription item {item.prescription_item_id} not found")
        if prescription_item.prescription_id != prescription.prescription_id:
            raise HTTPException(409, "Prescription item does not match current prescription")
        if prescription_item.drug_id != item.drug_id:
            raise HTTPException(409, "Dispensed drug does not match prescription item")

        remaining = Decimal(str(prescription_item.quantity_prescribed or 0)) - Decimal(str(prescription_item.quantity_dispensed or 0))
        if Decimal(str(item.quantity_dispensed)) > remaining:
            raise HTTPException(409, f"Quantity {item.quantity_dispensed} exceeds remaining balance of {remaining}")

        if batch.expiry_date < date.today():
            raise HTTPException(400, f"Cannot dispense expired stock from batch {batch.batch_number}")
        if float(batch.quantity_remaining) < float(item.quantity_dispensed):
            raise HTTPException(400, f"Insufficient stock in batch {batch.batch_number}. Available: {batch.quantity_remaining}")

        # Deduct stock
        batch.quantity_remaining = float(batch.quantity_remaining) - float(item.quantity_dispensed)
        inv = (await db.execute(
            select(PharmacyInventory).where(PharmacyInventory.inventory_id == batch.inventory_id).with_for_update()
        )).scalars().first()
        if inv:
            inv.available_quantity = max(0, float(inv.available_quantity or 0) - float(item.quantity_dispensed))

        # Add dispensing item
        di = DispensingItem(
            dispensing_record_id=rec.dispensing_record_id,
            prescription_item_id=item.prescription_item_id,
            batch_id=batch.batch_id,
            quantity_dispensed=item.quantity_dispensed
        )
        db.add(di)
        await db.flush()

        # Update prescription item dispensed quantity
        new_dispensed = Decimal(str(prescription_item.quantity_dispensed or 0)) + Decimal(str(item.quantity_dispensed))
        prescription_item.quantity_dispensed = new_dispensed
        prescription_item.item_status = "Dispensed" if new_dispensed >= Decimal(str(prescription_item.quantity_prescribed or 0)) else "Partially Dispensed"
        touched_items.append(prescription_item)

        # Compute pricing for invoice
        drug = await db.get(Drug, item.drug_id)
        unit_price = Decimal(str(batch.unit_selling_price if batch.unit_selling_price is not None else (drug.unit_price if drug and drug.unit_price is not None else 0)))
        line_total = (Decimal(str(item.quantity_dispensed)) * unit_price).quantize(Decimal("0.01"))
        total_amount += line_total
        invoice_items.append({
            "source": di.dispensing_item_id,
            "name": f"Prescription: {drug.generic_name if drug else 'Medication'}",
            "qty": item.quantity_dispensed,
            "price": unit_price,
            "total": line_total
        })

    # Update prescription overall status
    all_items = (await db.execute(
        select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.prescription_id)
    )).scalars().all()
    all_done = all(
        item.item_status == "Cancelled" or Decimal(str(item.quantity_dispensed or 0)) >= Decimal(str(item.quantity_prescribed or 0))
        for item in all_items
    )
    final_status_name = "Dispensed" if all_done else "Partially Dispensed"
    p_status = await db.scalar(select(PrescriptionStatus).where(PrescriptionStatus.status_name == final_status_name))
    if not p_status:
        p_status = PrescriptionStatus(status_name=final_status_name)
        db.add(p_status)
        await db.flush()
    prescription.prescription_status_id = p_status.prescription_status_id

    # Create consolidated invoice
    invoice_id = await create_dispensing_invoice(db, req.patient_id, rec.dispensing_record_id, invoice_items, cu.user_id)
    await db.commit()

    return BulkDispenseResponse(
        dispensing_record_id=rec.dispensing_record_id,
        prescription_id=req.prescription_id,
        dispensing_reference=req.dispensing_reference,
        dispensed_items_count=len(req.items),
        total_amount=total_amount,
        invoice_id=invoice_id,
        dispensing_status="Completed"
    )


@router.post("/prescriptions/{prescription_id}/review", response_model=PharmacistReviewResponse, status_code=201)
async def review_prescription(
    prescription_id: uuid.UUID,
    req: PharmacistReviewCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "admin", "super_admin"]))
):
    """Record pharmacist clinical review notes and intervention before dispensing."""
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(404, "Prescription not found")

    review = PharmacistReview(
        prescription_id=prescription_id,
        pharmacist_id=cu.user_id,
        review_status=req.review_status,
        intervention_type=req.intervention_type,
        clinical_notes=req.clinical_notes
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return PharmacistReviewResponse(
        review_id=review.review_id,
        prescription_id=review.prescription_id,
        pharmacist_id=review.pharmacist_id,
        review_status=review.review_status,
        intervention_type=review.intervention_type,
        clinical_notes=review.clinical_notes,
        reviewed_at=review.reviewed_at
    )


@router.get("/prescriptions/{prescription_id}/reviews", response_model=List[PharmacistReviewResponse])
async def list_prescription_reviews(
    prescription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pharmacist", "doctor", "admin"]))
):
    """List clinical pharmacist reviews for a prescription."""
    res = await db.execute(
        select(PharmacistReview).where(PharmacistReview.prescription_id == prescription_id).order_by(desc(PharmacistReview.reviewed_at))
    )
    reviews = res.scalars().all()
    return [
        PharmacistReviewResponse(
            review_id=r.review_id,
            prescription_id=r.prescription_id,
            pharmacist_id=r.pharmacist_id,
            review_status=r.review_status,
            intervention_type=r.intervention_type,
            clinical_notes=r.clinical_notes,
            reviewed_at=r.reviewed_at
        ) for r in reviews
    ]

