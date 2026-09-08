import uuid
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.pharmacy_models import (
    Drug, PharmacyStore, PharmacyInventory, PharmacyStockBatch,
    Prescription, PrescriptionItem, PrescriptionStatus,
    DispensingRecord, DispensingItem
)
from app.schemas.pharmacy import (
    DrugCreateRequest, DrugResponse,
    StockBatchReceiveRequest, StockBatchResponse,
    InventoryStatusResponse, DispensePrescriptionRequest,
    DispensingRecordResponse, DispensedItemResponse
)

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy Management"])

async def ensure_pharmacy_masters(db: AsyncSession):
    for st in ["Pending", "Partially Dispensed", "Dispensed", "Cancelled"]:
        res = await db.execute(select(PrescriptionStatus).where(PrescriptionStatus.status_name == st))
        if not res.scalars().first():
            db.add(PrescriptionStatus(status_name=st))
    
    res_store = await db.execute(select(PharmacyStore).limit(1))
    if not res_store.scalars().first():
        db.add(PharmacyStore(store_code="PHARM-MAIN", store_name="Central Outpatient Pharmacy"))
    
    await db.commit()

# ----------------- Drugs -----------------
@router.get("/drugs", response_model=List[DrugResponse])
async def list_drugs(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
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
    drug_res = await db.execute(select(Drug).where(Drug.drug_id == req.drug_id))
    drug = drug_res.scalars().first()
    if not drug: raise HTTPException(404, "Drug not found")

    inv_res = await db.execute(select(PharmacyInventory).where(PharmacyInventory.drug_id == req.drug_id))
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
    cu: CurrentUser = Depends(get_current_user)
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
        avail = float(inv.available_quantity or 0)
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
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    rec = DispensingRecord(
        dispensed_by=cu.user_id,
        dispensing_date=datetime.utcnow(),
        dispensing_status="Completed",
        notes=req.notes
    )
    db.add(rec)
    await db.flush()

    total_amount = 0.0
    dispensed_items = []

    for item in req.items:
        batch_res = await db.execute(select(PharmacyStockBatch).where(PharmacyStockBatch.batch_id == item.batch_id))
        batch = batch_res.scalars().first()
        if not batch: raise HTTPException(404, f"Batch {item.batch_id} not found")

        if float(batch.quantity_remaining) < item.quantity_dispensed:
            raise HTTPException(400, f"Insufficient quantity in batch {batch.batch_number}. Available: {batch.quantity_remaining}")

        batch.quantity_remaining = float(batch.quantity_remaining) - float(item.quantity_dispensed)

        inv_res = await db.execute(select(PharmacyInventory).where(PharmacyInventory.inventory_id == batch.inventory_id))
        inv = inv_res.scalars().first()
        if inv:
            inv.available_quantity = max(0, float(inv.available_quantity or 0) - float(item.quantity_dispensed))

        di = DispensingItem(
            dispensing_record_id=rec.dispensing_record_id,
            batch_id=batch.batch_id,
            quantity_dispensed=item.quantity_dispensed
        )
        db.add(di)
        await db.flush()

        d_res = await db.execute(select(Drug).where(Drug.drug_id == item.drug_id))
        drug = d_res.scalars().first()
        price = float(batch.selling_price or 10.0)
        item_total = price * float(item.quantity_dispensed)
        total_amount += item_total

        dispensed_items.append(DispensedItemResponse(
            dispensing_item_id=di.dispensing_item_id,
            drug_id=item.drug_id,
            generic_name=drug.generic_name if drug else "Medication",
            batch_number=batch.batch_number,
            quantity_dispensed=float(item.quantity_dispensed),
            unit_price=price,
            total_price=item_total
        ))

    await db.commit()

    return DispensingRecordResponse(
        dispensing_record_id=rec.dispensing_record_id,
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn,
        dispensing_date=rec.dispensing_date,
        dispensing_status=rec.dispensing_status,
        total_amount=total_amount,
        items=dispensed_items,
        notes=rec.notes
    )
