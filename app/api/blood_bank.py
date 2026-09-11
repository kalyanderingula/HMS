import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text, func

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.inpatient_emergency_models import (
    BloodGroupType, BloodComponentType, BloodUnit, BloodRequest, CrossMatchTest, BloodTransfusion,
    BloodDonor, DonorEligibilityCheck, BloodDonation, BloodUnitTest
)
from app.schemas.inpatient_emergency import (
    BloodUnitResponse, BloodRequestCreate, BloodRequestResponse,
    CrossMatchCreate, CrossMatchResponse, BloodIssueCreate, BloodTransfusionCreate, BloodTransfusionResponse
)
from app.schemas.specialized_operations import (
    BloodDonorCreate, BloodDonorResponse, DonorEligibilityCreate, DonorEligibilityResponse,
    BloodDonationCreate, BloodDonationResponse, ComponentSeparationRequest, ComponentSeparationResponse,
    SeparatedUnitItem, BloodUnitTestCreate, BloodUnitTestResponse
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


# ----------------- Milestone 3: Donor Lifecycle & Supply Chain -----------------

@router.post("/donors", response_model=BloodDonorResponse, status_code=201)
async def register_blood_donor(
    req: BloodDonorCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "admin", "super_admin"]))
):
    """Register a new voluntary or replacement blood donor."""
    # Lookup blood group
    bg = await db.scalar(select(BloodGroupType).where(BloodGroupType.group_name == req.blood_group_name))
    if not bg:
        raise HTTPException(400, f"Unknown blood group: {req.blood_group_name}")

    donor = BloodDonor(
        donor_number=f"DON-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        first_name=req.first_name,
        last_name=req.last_name,
        date_of_birth=req.date_of_birth,
        gender=req.gender,
        blood_group_type_id=bg.blood_group_type_id,
        phone=req.phone,
        email=req.email,
        address=req.address,
        is_eligible=True
    )
    db.add(donor)
    await db.commit()
    await db.refresh(donor)

    return BloodDonorResponse(
        blood_donor_id=donor.blood_donor_id,
        donor_number=donor.donor_number,
        first_name=donor.first_name,
        last_name=donor.last_name,
        date_of_birth=donor.date_of_birth,
        gender=donor.gender,
        blood_group=req.blood_group_name,
        phone=donor.phone,
        email=donor.email,
        total_donations=donor.total_donations or 0,
        is_eligible=donor.is_eligible,
        created_at=donor.created_at
    )


@router.get("/donors", response_model=List[BloodDonorResponse])
async def list_blood_donors(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "admin", "super_admin"]))
):
    """List registered blood donors."""
    res = await db.execute(select(BloodDonor).order_by(desc(BloodDonor.created_at)).limit(50))
    donors = res.scalars().all()
    results = []
    for d in donors:
        bg_name = None
        if d.blood_group_type_id:
            bg = await db.get(BloodGroupType, d.blood_group_type_id)
            if bg:
                bg_name = bg.group_name
        results.append(BloodDonorResponse(
            blood_donor_id=d.blood_donor_id,
            donor_number=d.donor_number,
            first_name=d.first_name,
            last_name=d.last_name,
            date_of_birth=d.date_of_birth,
            gender=d.gender,
            blood_group=bg_name,
            phone=d.phone,
            email=d.email,
            total_donations=d.total_donations or 0,
            is_eligible=d.is_eligible,
            created_at=d.created_at
        ))
    return results


@router.post("/donors/{donor_id}/eligibility", response_model=DonorEligibilityResponse, status_code=201)
async def check_donor_eligibility(
    donor_id: uuid.UUID,
    req: DonorEligibilityCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "admin", "super_admin"]))
):
    """Conduct pre-donation medical physical and questionnaire screening."""
    donor = await db.get(BloodDonor, donor_id)
    if not donor:
        raise HTTPException(404, "Blood donor not found")

    # Standard donor eligibility criteria: Hb >= 12.5 g/dL, Weight >= 50.0 kg
    is_eligible = True
    rejection_reasons = []

    if req.hemoglobin < 12.5:
        is_eligible = False
        rejection_reasons.append(f"Hemoglobin {req.hemoglobin} g/dL is below required 12.5 g/dL minimum")
    if req.weight < 50.0:
        is_eligible = False
        rejection_reasons.append(f"Body weight {req.weight} kg is below required 50.0 kg minimum")
    if not req.screening_passed:
        is_eligible = False
        if req.rejection_reason:
            rejection_reasons.append(req.rejection_reason)
        else:
            rejection_reasons.append("Failed health history screening questionnaire")

    rejection_text = "; ".join(rejection_reasons) if rejection_reasons else None

    check = DonorEligibilityCheck(
        blood_donor_id=donor_id,
        hemoglobin=req.hemoglobin,
        blood_pressure=req.blood_pressure,
        weight=req.weight,
        temperature=req.temperature,
        pulse=req.pulse,
        is_eligible=is_eligible,
        rejection_reason=rejection_text,
        checked_by=cu.user_id
    )
    db.add(check)
    donor.is_eligible = is_eligible
    await db.commit()
    await db.refresh(check)

    return DonorEligibilityResponse(
        eligibility_check_id=check.eligibility_check_id,
        blood_donor_id=check.blood_donor_id,
        check_date=check.check_date,
        hemoglobin=check.hemoglobin,
        weight=check.weight,
        blood_pressure=check.blood_pressure,
        is_eligible=check.is_eligible,
        rejection_reason=check.rejection_reason
    )


@router.post("/donations", response_model=BloodDonationResponse, status_code=201)
async def collect_blood_donation(
    req: BloodDonationCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "admin", "super_admin"]))
):
    """Collect whole blood donation bag from an eligible donor."""
    donor = await db.get(BloodDonor, req.blood_donor_id)
    if not donor:
        raise HTTPException(404, "Blood donor not found")
    if not donor.is_eligible:
        raise HTTPException(400, "Donor is currently not marked eligible for donation. Conduct an eligibility screening check first.")

    bag_number = f"WB-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    donation = BloodDonation(
        blood_donor_id=donor.blood_donor_id,
        donation_type=req.donation_type,
        bag_number=bag_number,
        volume_ml=req.volume_ml,
        collected_by=cu.user_id,
        notes=req.notes,
        status="collected"
    )
    db.add(donation)
    donor.last_donation_date = date.today()
    donor.total_donations = (donor.total_donations or 0) + 1

    await db.commit()
    await db.refresh(donation)

    return BloodDonationResponse(
        blood_donation_id=donation.blood_donation_id,
        blood_donor_id=donation.blood_donor_id,
        bag_number=donation.bag_number,
        volume_ml=donation.volume_ml,
        donation_type=donation.donation_type,
        status=donation.status,
        donation_date=donation.donation_date
    )


@router.post("/donations/{donation_id}/separate", response_model=ComponentSeparationResponse)
async def separate_donation_components(
    donation_id: uuid.UUID,
    req: ComponentSeparationRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "admin", "super_admin"]))
):
    """Centrifuge and separate whole blood into clinical components (PRBC, FFP, Platelets)."""
    donation = await db.get(BloodDonation, donation_id)
    if not donation:
        raise HTTPException(404, "Donation record not found")
    if donation.status == "separated":
        raise HTTPException(409, "Donation has already undergone component separation")

    donor = await db.get(BloodDonor, donation.blood_donor_id)
    if not donor:
        raise HTTPException(404, "Donor record not found")

    separated_items = []
    # Standard parameters:
    # PRBC: 42 days, 250ml, 2-6C
    # FFP: 365 days, 200ml, -18C
    # Platelets: 5 days, 50ml, 20-24C
    comp_specs = {
        "PRBC": {"days": 42, "vol": 250, "storage": "Refrigerated 2-6C"},
        "FFP": {"days": 365, "vol": 200, "storage": "Deep Freezer -18C"},
        "Platelets": {"days": 5, "vol": 50, "storage": "Agitator Incubator 20-24C"},
        "Cryoprecipitate": {"days": 365, "vol": 20, "storage": "Deep Freezer -18C"}
    }

    for cname in req.components:
        spec = comp_specs.get(cname, {"days": 35, "vol": 100, "storage": "Refrigerator"})
        comp_type = await db.scalar(select(BloodComponentType).where(BloodComponentType.component_name == cname))
        if not comp_type:
            comp_type = BloodComponentType(
                component_name=cname,
                shelf_life_days=spec["days"],
                storage_temperature=spec["storage"],
                unit_price=1000
            )
            db.add(comp_type)
            await db.flush()

        unit_number = f"U-{cname[:3]}-{donation.bag_number[-8:]}"
        exp_date = date.today() + timedelta(days=spec["days"])
        unit = BloodUnit(
            blood_donation_id=donation.blood_donation_id,
            blood_component_type_id=comp_type.blood_component_type_id,
            unit_number=unit_number,
            blood_group_type_id=donor.blood_group_type_id,
            volume_ml=spec["vol"],
            collection_date=donation.donation_date.date() if donation.donation_date else date.today(),
            expiry_date=exp_date,
            status="quarantine",  # Under quarantine until infectious viral screening passes
            storage_location=spec["storage"]
        )
        db.add(unit)
        await db.flush()

        separated_items.append(SeparatedUnitItem(
            blood_unit_id=unit.blood_unit_id,
            unit_number=unit.unit_number,
            component_name=cname,
            volume_ml=unit.volume_ml,
            expiry_date=unit.expiry_date,
            status=unit.status
        ))

    donation.status = "separated"
    await db.commit()

    return ComponentSeparationResponse(
        blood_donation_id=donation.blood_donation_id,
        source_bag_number=donation.bag_number,
        separated_units=separated_items
    )


@router.post("/units/{unit_id}/test", response_model=BloodUnitTestResponse, status_code=201)
async def test_blood_unit_screening(
    unit_id: uuid.UUID,
    req: BloodUnitTestCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["blood_bank_technician", "doctor", "admin", "super_admin"]))
):
    """Infectious disease viral screening (HIV, Hep B, Hep C, Syphilis, Malaria). Auto-discards reactive units."""
    unit = await db.get(BloodUnit, unit_id)
    if not unit:
        raise HTTPException(404, "Blood unit not found")
    if unit.status == "discarded":
        raise HTTPException(409, "Blood unit is already discarded as biohazard")

    test_entry = BloodUnitTest(
        blood_unit_id=unit_id,
        test_name=req.test_name,
        result=req.result,
        tested_by=cu.user_id,
        notes=req.notes
    )
    db.add(test_entry)

    if req.result == "Reactive":
        unit.status = "discarded"
        unit.discard_reason = f"Biohazard: Reactive for {req.test_name}"
        unit.discarded_by = cu.user_id
        unit.discarded_at = datetime.utcnow()
    elif req.result == "Negative":
        # If in quarantine, check if we can release it to available
        if unit.status == "quarantine":
            unit.status = "available"

    await db.commit()
    await db.refresh(test_entry)

    return BloodUnitTestResponse(
        unit_test_id=test_entry.unit_test_id,
        blood_unit_id=test_entry.blood_unit_id,
        test_name=test_entry.test_name,
        result=test_entry.result,
        tested_at=test_entry.tested_at,
        unit_status_now=unit.status
    )

