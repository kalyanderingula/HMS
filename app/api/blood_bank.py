import uuid
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text, func

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.inpatient_emergency_models import (
    BloodGroupType, BloodComponentType, BloodUnit, BloodRequest, CrossMatchTest, BloodTransfusion
)
from app.schemas.inpatient_emergency import (
    BloodUnitResponse, BloodRequestCreate, BloodRequestResponse,
    CrossMatchCreate, CrossMatchResponse, BloodIssueCreate, BloodTransfusionCreate, BloodTransfusionResponse
)

router = APIRouter(prefix="/blood-bank", tags=["Blood Bank & Transfusions"])


async def create_blood_invoice(db, request, unit, component, created_by):
    existing = await db.scalar(text("""SELECT invoice_id FROM billing.invoice_items
        WHERE item_type='Procedure' AND item_reference_id=:source LIMIT 1"""), {"source": unit.blood_unit_id})
    if existing:
        return existing
    account = await db.scalar(text("""SELECT billing_account_id FROM billing.billing_accounts
        WHERE patient_id=:patient ORDER BY created_at LIMIT 1 FOR UPDATE"""), {"patient": request.patient_id})
    if not account:
        account = uuid.uuid4()
        await db.execute(text("""INSERT INTO billing.billing_accounts
            (billing_account_id,patient_id,account_number,account_status,total_due,total_paid)
            VALUES (:id,:patient,:number,'Active',0,0)"""),
            {"id": account, "patient": request.patient_id, "number": f"ACC-{uuid.uuid4().hex}"})
    price = component.unit_price or 0
    status_id = await db.scalar(text("""INSERT INTO billing.billing_statuses(status_name) VALUES (:name)
        ON CONFLICT(status_name) DO UPDATE SET status_name=EXCLUDED.status_name RETURNING billing_status_id"""),
        {"name": "Paid" if price == 0 else "Pending"})
    invoice_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO billing.invoices
        (invoice_id,invoice_number,billing_account_id,patient_id,billing_status_id,subtotal_amount,
         tax_amount,discount_amount,total_amount,paid_amount,balance_amount,notes,created_by)
        VALUES (:id,:number,:account,:patient,:status,:price,0,0,:price,0,:price,:notes,:user)"""),
        {"id": invoice_id, "number": f"INV-BB-{uuid.uuid4().hex[:12].upper()}", "account": account,
         "patient": request.patient_id, "status": status_id, "price": price,
         "notes": "Automatically generated when a blood unit was issued", "user": created_by})
    await db.execute(text("""INSERT INTO billing.invoice_items
        (invoice_id,item_type,item_reference_id,item_name,quantity,unit_price,tax_amount,discount_amount,line_total)
        VALUES (:invoice,'Procedure',:source,:name,1,:price,0,0,:price)"""),
        {"invoice": invoice_id, "source": unit.blood_unit_id,
         "name": f"Blood bank - {component.component_name}", "price": price})
    await db.execute(text("""UPDATE billing.billing_accounts SET total_due=COALESCE(total_due,0)+:price,
        updated_at=CURRENT_TIMESTAMP WHERE billing_account_id=:account"""),
        {"account": account, "price": price})
    return invoice_id

async def ensure_blood_masters(db: AsyncSession):
    groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    for g in groups:
        res = await db.execute(select(BloodGroupType).where(BloodGroupType.group_name == g))
        if not res.scalars().first():
            db.add(BloodGroupType(group_name=g))
            
    components = [("PRBC", 42), ("Whole Blood", 35), ("Platelets", 5), ("FFP", 365)]
    for c, shelf in components:
        res = await db.execute(select(BloodComponentType).where(BloodComponentType.component_name == c))
        if not res.scalars().first():
            db.add(BloodComponentType(component_name=c, shelf_life_days=shelf))
    await db.commit()

@router.get("/inventory", response_model=List[BloodUnitResponse])
async def list_blood_inventory(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "nurse", "admin"]))
):
    await ensure_blood_masters(db)
    res = await db.execute(select(BloodUnit).where(BloodUnit.status == "available"))
    units = res.scalars().all()
    results = []
    for u in units:
        bg_res = await db.execute(select(BloodGroupType).where(BloodGroupType.blood_group_type_id == u.blood_group_type_id))
        bg = bg_res.scalars().first()
        comp_res = await db.execute(select(BloodComponentType).where(BloodComponentType.blood_component_type_id == u.blood_component_type_id))
        comp = comp_res.scalars().first()
        results.append(BloodUnitResponse(
            blood_unit_id=u.blood_unit_id,
            unit_number=u.unit_number,
            blood_group=bg.group_name if bg else "Unknown",
            component_name=comp.component_name if comp else "PRBC",
            volume_ml=u.volume_ml or 350,
            expiry_date=u.expiry_date,
            status=u.status
        ))
    return results


@router.get("/requests")
async def list_blood_requests(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "nurse", "admin"]))
):
    condition = "AND br.status=:status" if status_filter else ""
    rows = await db.execute(text(f"""SELECT br.blood_request_id,br.patient_id,
        concat_ws(' ',p.first_name,p.last_name) patient_name,p.mrn,bg.group_name blood_group,
        bc.component_name,br.units_requested,br.urgency,br.clinical_indication,br.status,br.created_at,
        cm.cross_match_id,cm.blood_unit_id,bu.unit_number,cm.result compatibility_result
        FROM blood_bank.blood_requests br JOIN patient.patients p USING(patient_id)
        LEFT JOIN blood_bank.blood_group_types bg USING(blood_group_type_id)
        LEFT JOIN blood_bank.blood_component_types bc USING(blood_component_type_id)
        LEFT JOIN LATERAL (SELECT * FROM blood_bank.cross_match_tests x
            WHERE x.blood_request_id=br.blood_request_id ORDER BY x.tested_at DESC LIMIT 1) cm ON true
        LEFT JOIN blood_bank.blood_units bu ON bu.blood_unit_id=cm.blood_unit_id
        WHERE 1=1 {condition} ORDER BY CASE br.urgency WHEN 'STAT' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END,
        br.created_at DESC LIMIT 200"""), {"status": status_filter})
    return [dict(row) for row in rows.mappings()]

@router.post("/requests", response_model=BloodRequestResponse, status_code=201)
async def request_blood(
    req: BloodRequestCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"]))
):
    await ensure_blood_masters(db)
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    bg_res = await db.execute(select(BloodGroupType).where(BloodGroupType.group_name == req.blood_group))
    bg = bg_res.scalars().first()
    comp_res = await db.execute(select(BloodComponentType).where(BloodComponentType.component_name == req.component_name))
    comp = comp_res.scalars().first()
    if not bg or not comp:
        raise HTTPException(422, "Select a valid blood group and component")
    if req.units_requested < 1 or req.units_requested > 10:
        raise HTTPException(422, "Units requested must be between 1 and 10")
    if req.urgency not in ("Routine", "Urgent", "STAT") or not req.clinical_indication.strip():
        raise HTTPException(422, "A valid urgency and clinical indication are required")

    br = BloodRequest(
        patient_id=patient.patient_id,
        requested_by=cu.user_id,
        blood_group_type_id=bg.blood_group_type_id if bg else None,
        blood_component_type_id=comp.blood_component_type_id if comp else None,
        units_requested=req.units_requested,
        urgency=req.urgency,
        clinical_indication=req.clinical_indication,
        status="pending"
    )
    db.add(br)
    await db.flush()
    await db.execute(text("""INSERT INTO core.notifications
        (recipient_type,source_module,source_reference_id,subject,body,status)
        VALUES ('Role','BloodBank',:source,:subject,:body,'pending')"""),
        {"source": br.blood_request_id, "subject": f"New {req.urgency} blood request",
         "body": f"{req.units_requested} unit(s) of {req.blood_group} {req.component_name} requested."})
    await db.commit()
    await db.refresh(br)

    return BloodRequestResponse(
        blood_request_id=br.blood_request_id,
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        blood_group=req.blood_group,
        component_name=req.component_name,
        units_requested=br.units_requested,
        urgency=br.urgency,
        status=br.status,
        created_at=br.created_at
    )

@router.post("/cross-match", response_model=CrossMatchResponse, status_code=201)
async def perform_crossmatch(
    req: CrossMatchCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "lab_technician", "doctor", "admin"]))
):
    br_res = await db.execute(select(BloodRequest).where(
        BloodRequest.blood_request_id == req.blood_request_id).with_for_update())
    br = br_res.scalars().first()
    if not br: raise HTTPException(404, "Blood request not found")

    bu_res = await db.execute(select(BloodUnit).where(BloodUnit.blood_unit_id == req.blood_unit_id).with_for_update())
    bu = bu_res.scalars().first()
    if not bu: raise HTTPException(404, "Blood unit not found")
    if br.status not in ("pending", "crossmatched"):
        raise HTTPException(409, f"Request cannot be cross-matched in status {br.status}")
    if bu.status != "available" or bu.expiry_date < date.today():
        raise HTTPException(409, "Blood unit is unavailable or expired")
    if req.compatibility_result not in ("Compatible", "Incompatible"):
        raise HTTPException(422, "Compatibility result must be Compatible or Incompatible")
    if bu.blood_group_type_id != br.blood_group_type_id or bu.blood_component_type_id != br.blood_component_type_id:
        raise HTTPException(409, "Blood group or component does not match the request")
    existing = await db.scalar(select(CrossMatchTest.cross_match_id).where(
        CrossMatchTest.blood_request_id == br.blood_request_id,
        CrossMatchTest.blood_unit_id == bu.blood_unit_id))
    if existing:
        raise HTTPException(409, "This unit was already cross-matched for the request")
    reserved_count = await db.scalar(select(func.count(CrossMatchTest.cross_match_id)).where(
        CrossMatchTest.blood_request_id == br.blood_request_id, CrossMatchTest.result == "Compatible"))
    if req.compatibility_result == "Compatible" and reserved_count >= br.units_requested:
        raise HTTPException(409, "The requested number of units is already reserved")

    p_res = await db.execute(select(Patient).where(Patient.patient_id == br.patient_id))
    patient = p_res.scalars().first()

    cm = CrossMatchTest(
        blood_request_id=br.blood_request_id,
        blood_unit_id=bu.blood_unit_id,
        patient_id=br.patient_id,
        result=req.compatibility_result,
        tested_by=cu.user_id,
        tested_at=datetime.utcnow()
    )
    db.add(cm)
    if req.compatibility_result == "Compatible":
        bu.status = "crossmatched"
        br.status = "crossmatched"

    await db.commit()
    await db.refresh(cm)

    return CrossMatchResponse(
        cross_match_id=cm.cross_match_id,
        blood_request_id=br.blood_request_id,
        blood_unit_number=bu.unit_number,
        patient_name=f"{patient.first_name} {patient.last_name}",
        result=cm.result,
        tested_at=cm.tested_at
    )


@router.post("/issue", status_code=201)
async def issue_blood_unit(
    req: BloodIssueCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "admin"]))
):
    br = (await db.execute(select(BloodRequest).where(
        BloodRequest.blood_request_id == req.blood_request_id).with_for_update())).scalars().first()
    unit = (await db.execute(select(BloodUnit).where(
        BloodUnit.blood_unit_id == req.blood_unit_id).with_for_update())).scalars().first()
    if not br or not unit:
        raise HTTPException(404, "Blood request or unit not found")
    match = await db.scalar(select(CrossMatchTest.cross_match_id).where(
        CrossMatchTest.blood_request_id == br.blood_request_id,
        CrossMatchTest.blood_unit_id == unit.blood_unit_id,
        CrossMatchTest.result == "Compatible"))
    if not match or unit.status != "crossmatched":
        raise HTTPException(409, "Only a compatible reserved unit can be issued")
    component = await db.get(BloodComponentType, unit.blood_component_type_id)
    unit.status = "issued"
    br.status = "issued"
    invoice_id = await create_blood_invoice(db, br, unit, component, cu.user_id)
    await db.execute(text("""INSERT INTO core.notifications
        (recipient_id,recipient_type,source_module,source_reference_id,subject,body,status)
        VALUES (:recipient,'User','BloodBank',:source,'Blood unit issued',:body,'pending'),
               (NULL,'Role','BloodBank',:source,'Blood unit ready for transfusion',:body,'pending')"""),
        {"recipient": br.requested_by, "source": unit.blood_unit_id,
         "body": f"Blood unit {unit.unit_number} is issued and ready for the patient."})
    await db.commit()
    return {"blood_request_id": br.blood_request_id, "blood_unit_id": unit.blood_unit_id,
            "unit_number": unit.unit_number, "status": "issued", "invoice_id": invoice_id}

@router.post("/transfusions", response_model=BloodTransfusionResponse, status_code=201)
async def record_transfusion(
    req: BloodTransfusionCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    br_res = await db.execute(select(BloodRequest).where(
        BloodRequest.blood_request_id == req.blood_request_id).with_for_update())
    br = br_res.scalars().first()
    if not br: raise HTTPException(404, "Blood request not found")

    bu_res = await db.execute(select(BloodUnit).where(BloodUnit.blood_unit_id == req.blood_unit_id).with_for_update())
    bu = bu_res.scalars().first()
    if not bu: raise HTTPException(404, "Blood unit not found")
    if br.status != "issued" or bu.status != "issued":
        raise HTTPException(409, "Only an issued blood unit can be transfused")
    if req.volume_transfused <= 0 or req.volume_transfused > (bu.volume_ml or 450):
        raise HTTPException(422, "Transfused volume must be within the blood unit volume")
    if req.adverse_reaction and not req.reaction_details:
        raise HTTPException(422, "Reaction details are required when an adverse reaction is recorded")

    trans = BloodTransfusion(
        blood_request_id=br.blood_request_id,
        blood_unit_id=bu.blood_unit_id,
        patient_id=br.patient_id,
        administered_by=cu.user_id,
        start_time=datetime.utcnow(),
        volume_transfused=req.volume_transfused,
        status="completed",
        notes=req.notes
        ,adverse_reaction=req.adverse_reaction, reaction_details=req.reaction_details,
    )
    db.add(trans)
    bu.status = "transfused"
    br.status = "completed"

    await db.flush()
    await db.execute(text("""INSERT INTO core.notifications
        (recipient_id,recipient_type,source_module,source_reference_id,subject,body,status)
        VALUES (:recipient,'User','BloodBank',:source,:subject,:body,'pending')"""),
        {"recipient": br.requested_by, "source": trans.transfusion_id,
         "subject": "Blood transfusion completed" if not req.adverse_reaction else "Adverse transfusion reaction recorded",
         "body": req.reaction_details or f"Unit {bu.unit_number} transfusion was completed."})

    await db.commit()
    await db.refresh(trans)

    return BloodTransfusionResponse(
        transfusion_id=trans.transfusion_id,
        patient_id=trans.patient_id,
        blood_unit_number=bu.unit_number,
        volume_transfused=trans.volume_transfused,
        status=trans.status,
        administered_at=trans.start_time,
        notes=trans.notes, adverse_reaction=trans.adverse_reaction,
        reaction_details=trans.reaction_details
    )
