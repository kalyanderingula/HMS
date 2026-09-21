import uuid
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, time, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.api.doctor import Doctor
from app.models.laboratory_models import (
    LabTest, LabTestParameter, LabTestReferenceRange, LabParameterInterpretationRule,
    LabOrder, LabOrderItem,
    LabOrderStatus, LabOrderPriority, SampleType, LabSample,
    LabResultEntry, LabResultParameter
)
from app.schemas.laboratory import (
    LabTestCreateRequest, LabTestResponse, LabParameterResponse,
    LabOrderCreateRequest, LabOrderResponse, LabOrderItemResponse, LabBookingCreateRequest, LabReferenceRangeCreate,
    SampleCollectionRequest, SampleResponse,
    LabResultEntryRequest, LabResultResponse, ParameterResultResponse
)

router = APIRouter(prefix="/laboratory", tags=["Laboratory Information System"])

async def create_lab_invoice(db, patient_id, order_id, items, user_id):
    if await db.scalar(text("SELECT invoice_id FROM billing.invoice_items WHERE item_type='Laboratory' AND item_reference_id=:id LIMIT 1"),{"id":order_id}): return
    account=await db.scalar(text("SELECT billing_account_id FROM billing.billing_accounts WHERE patient_id=:p LIMIT 1 FOR UPDATE"),{"p":patient_id})
    if not account:
        account=uuid.uuid4();await db.execute(text("INSERT INTO billing.billing_accounts(billing_account_id,patient_id,account_number,account_status,total_due,total_paid) VALUES(:id,:p,:n,'Active',0,0)"),{"id":account,"p":patient_id,"n":f"ACC-{uuid.uuid4().hex}"})
    total=sum(float(x["price"]) for x in items); sid=await db.scalar(text("INSERT INTO billing.billing_statuses(status_name) VALUES(:n) ON CONFLICT(status_name) DO UPDATE SET status_name=EXCLUDED.status_name RETURNING billing_status_id"),{"n":"Paid" if not total else "Pending"});invoice=uuid.uuid4()
    await db.execute(text("INSERT INTO billing.invoices(invoice_id,invoice_number,billing_account_id,patient_id,billing_status_id,subtotal_amount,tax_amount,discount_amount,total_amount,paid_amount,balance_amount,notes,created_by) VALUES(:id,:n,:a,:p,:s,:t,0,0,:t,0,:t,'Automatically generated from laboratory order',:u)"),{"id":invoice,"n":f"INV-LAB-{uuid.uuid4().hex[:12].upper()}","a":account,"p":patient_id,"s":sid,"t":total,"u":user_id})
    for i,x in enumerate(items): await db.execute(text("INSERT INTO billing.invoice_items(invoice_id,item_type,item_reference_id,item_name,quantity,unit_price,tax_amount,discount_amount,line_total) VALUES(:i,'Laboratory',:r,:n,1,:p,0,0,:p)"),{"i":invoice,"r":order_id if i==0 else x["item_id"],"n":x["name"],"p":x["price"]})
    await db.execute(text("UPDATE billing.billing_accounts SET total_due=COALESCE(total_due,0)+:t WHERE billing_account_id=:a"),{"t":total,"a":account})

async def ensure_lab_masters(db: AsyncSession):
    for st in ["Ordered", "Sample Collected", "In Analysis", "Completed", "Cancelled"]:
        res = await db.execute(select(LabOrderStatus).where(LabOrderStatus.status_name == st))
        if not res.scalars().first():
            db.add(LabOrderStatus(status_name=st))
    for p, rank in [("Routine", 1), ("Urgent", 2), ("STAT", 3)]:
        res = await db.execute(select(LabOrderPriority).where(LabOrderPriority.priority_name == p))
        if not res.scalars().first():
            db.add(LabOrderPriority(priority_name=p, priority_level=rank))
    for stp in ["Venous Blood", "Serum", "Plasma", "Urine", "Sputum", "Swab"]:
        res = await db.execute(select(SampleType).where(SampleType.sample_type_name == stp))
        if not res.scalars().first():
            db.add(SampleType(sample_type_name=stp))
    await db.commit()

# ----------------- Lab Tests -----------------
@router.get("/tests", response_model=List[LabTestResponse])
async def list_lab_tests(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["lab_technician", "doctor", "nurse", "patient", "receptionist", "admin"]))
):
    query = select(LabTest).where(LabTest.is_active == True)
    if q:
        query = query.where(LabTest.test_name.ilike(f"%{q}%") | LabTest.test_code.ilike(f"%{q}%"))
    res = await db.execute(query.order_by(LabTest.test_name).limit(50))
    tests = res.scalars().all()
    results = []
    for t in tests:
        p_res = await db.execute(select(LabTestParameter).where(LabTestParameter.test_id == t.test_id))
        params = p_res.scalars().all()
        results.append(LabTestResponse(
            test_id=t.test_id, test_code=t.test_code, test_name=t.test_name,
            test_method=t.test_method, turnaround_time_hours=t.turnaround_time_hours or 4,
            fasting_required=t.fasting_required or False, sample_volume=t.sample_volume,
            specimen_type=t.specimen_type, performing_department=t.performing_department,
            approving_specialty=t.approving_specialty,
            price=float(t.price or 0),
            parameters=[LabParameterResponse(
                parameter_id=p.parameter_id, parameter_name=p.parameter_name,
                unit=p.unit or "", normal_range=p.normal_range or "",
                critical_low=float(p.critical_low) if p.critical_low is not None else None,
                critical_high=float(p.critical_high) if p.critical_high is not None else None,
                parameter_code=p.parameter_code, result_type=p.result_type,
                specimen_type=p.specimen_type, method=p.method,
                display_order=p.display_order, is_required=p.is_required,
                allowed_values=p.allowed_values,
            ) for p in params]
        ))
    return results

@router.get("/tests/{test_id}/parameter-rules")
async def laboratory_parameter_rules(
    test_id: uuid.UUID,
    sex: Optional[str] = None,
    age: Optional[float] = Query(default=None, ge=0, le=150),
    pregnancy_status: Optional[str] = None,
    trimester: Optional[int] = Query(default=None, ge=1, le=3),
    menstrual_phase: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["lab_technician", "doctor", "nurse", "receptionist", "admin", "super_admin"])),
):
    test = await db.get(LabTest, test_id)
    if not test:
        raise HTTPException(404, "Laboratory test not found")
    parameters = (await db.execute(select(LabTestParameter).where(
        LabTestParameter.test_id == test_id).order_by(LabTestParameter.display_order,
                                                       LabTestParameter.parameter_name))).scalars().all()
    output = []
    for parameter in parameters:
        effective = await effective_reference_range(
            db, parameter.parameter_id, sex, age, pregnancy_status, trimester, menstrual_phase)
        matched = [effective] if effective else []
        interpretations = (await db.execute(select(LabParameterInterpretationRule).where(
            LabParameterInterpretationRule.parameter_id == parameter.parameter_id,
            LabParameterInterpretationRule.is_active.is_(True),
            (LabParameterInterpretationRule.effective_from.is_(None) | (LabParameterInterpretationRule.effective_from <= date.today())),
            (LabParameterInterpretationRule.effective_to.is_(None) | (LabParameterInterpretationRule.effective_to >= date.today())),
        ).order_by(LabParameterInterpretationRule.priority))).scalars().all()
        output.append({
            "parameter_id": parameter.parameter_id, "parameter_code": parameter.parameter_code,
            "parameter_name": parameter.parameter_name, "result_type": parameter.result_type,
            "unit": parameter.unit, "allowed_values": parameter.allowed_values,
            "reference_ranges": [{
                "reference_range_id": rule.reference_range_id, "reference_rule": rule.reference_rule,
                "sex": rule.sex, "age_min": rule.age_min, "age_max": rule.age_max,
                "age_unit": rule.age_unit, "pregnancy_status": rule.pregnancy_status,
                "trimester": rule.trimester, "menstrual_phase": rule.menstrual_phase,
                "low": rule.min_value, "high": rule.max_value,
                "critical_low": rule.critical_low, "critical_high": rule.critical_high,
                "reference_text": rule.reference_text, "unit": rule.unit,
                "method": rule.method, "analyzer": rule.analyzer, "source": rule.source,
                "version": rule.version,
            } for rule in matched],
            "interpretation_rules": [{
                "code": rule.rule_code, "label": rule.label, "operator": rule.operator,
                "lower": rule.lower_value, "upper": rule.upper_value,
                "qualitative_value": rule.qualitative_value, "interpretation": rule.interpretation,
                "version": rule.version,
            } for rule in interpretations],
        })
    return {"test_id": test.test_id, "test_code": test.test_code, "test_name": test.test_name,
            "approving_specialty": test.approving_specialty, "parameters": output}

@router.post("/tests", response_model=LabTestResponse, status_code=201)
async def create_lab_test(
    req: LabTestCreateRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["lab_technician", "doctor", "admin", "super_admin"]))
):
    existing = await db.execute(select(LabTest).where(LabTest.test_code == req.test_code))
    if existing.scalars().first():
        raise HTTPException(400, "Test code already exists")

    t = LabTest(
        test_code=req.test_code, test_name=req.test_name, test_method=req.test_method,
        turnaround_time_hours=req.turnaround_time_hours, fasting_required=req.fasting_required,
        sample_volume=req.sample_volume, price=req.price, is_active=True
    )
    db.add(t)
    await db.flush()

    param_responses = []
    for p in req.parameters:
        param = LabTestParameter(
            test_id=t.test_id, parameter_name=p.parameter_name, unit=p.unit,
            normal_range=p.normal_range, critical_low=p.critical_low, critical_high=p.critical_high,
            parameter_code=p.parameter_code, result_type=p.result_type.upper(),
            specimen_type=p.specimen_type, method=p.method,
            display_order=p.display_order, is_required=p.is_required,
            allowed_values=p.allowed_values, interpretation=p.interpretation
        )
        db.add(param)
        await db.flush()
        param_responses.append(LabParameterResponse(
            parameter_id=param.parameter_id, parameter_name=param.parameter_name,
            unit=param.unit, normal_range=param.normal_range,
            critical_low=float(param.critical_low) if param.critical_low is not None else None,
            critical_high=float(param.critical_high) if param.critical_high is not None else None,
        ))

    await db.commit()
    await db.refresh(t)
    return LabTestResponse(
        test_id=t.test_id, test_code=t.test_code, test_name=t.test_name,
        test_method=t.test_method, turnaround_time_hours=t.turnaround_time_hours,
        fasting_required=t.fasting_required, sample_volume=t.sample_volume, price=float(t.price),
        parameters=param_responses
    )

@router.post("/parameters/{parameter_id}/reference-ranges", status_code=201)
async def create_reference_range(
    parameter_id: uuid.UUID, req: LabReferenceRangeCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["admin", "super_admin"])),
):
    if not await db.get(LabTestParameter, parameter_id):
        raise HTTPException(404, "Laboratory parameter not found")
    row = LabTestReferenceRange(
        parameter_id=parameter_id, reference_rule="CONFIGURED", sex=req.sex,
        age_min=req.age_min, age_max=req.age_max, age_unit=req.age_unit.upper(),
        pregnancy_status=req.pregnancy_status, trimester=req.trimester,
        menstrual_phase=req.menstrual_phase, clinical_condition=req.clinical_condition,
        min_value=req.min_value, max_value=req.max_value,
        critical_low=req.critical_low, critical_high=req.critical_high,
        reference_text=req.reference_text, unit=req.unit,
        effective_from=req.effective_from, effective_to=req.effective_to,
        version=req.version, source="HMS administration", is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"reference_range_id": row.reference_range_id, "parameter_id": row.parameter_id,
            "version": row.version, "status": "active"}

# ----------------- Lab Orders -----------------
@router.post("/orders", response_model=LabOrderResponse, status_code=201)
async def create_lab_order(
    req: LabOrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"]))
):
    await ensure_lab_masters(db)
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    st_res = await db.execute(select(LabOrderStatus).where(LabOrderStatus.status_name == "Ordered"))
    st = st_res.scalars().first()

    pr_res = await db.execute(select(LabOrderPriority).where(LabOrderPriority.priority_name == req.priority))
    pr = pr_res.scalars().first()

    seq_res = await db.execute(select(func.count(LabOrder.lab_order_id)))
    seq = (seq_res.scalar() or 0) + 1
    order_num = f"LAB-{uuid.uuid4().hex[:16].upper()}"

    order = LabOrder(
        order_number=order_num, patient_id=patient.patient_id, encounter_id=req.encounter_id,
        doctor_id=req.doctor_id, lab_order_status_id=st.lab_order_status_id if st else None,
        priority_id=pr.priority_id if pr else None, clinical_notes=req.clinical_notes,
        created_by=cu.user_id, ordered_at=datetime.utcnow()
    )
    db.add(order)
    await db.flush()

    item_responses = []
    billable_items = []
    for it in req.items:
        t_res = await db.execute(select(LabTest).where(LabTest.test_id == it.test_id))
        test = t_res.scalars().first()
        if not test: raise HTTPException(404, "Requested lab test not found")

        order_item = LabOrderItem(lab_order_id=order.lab_order_id, test_id=test.test_id, order_status="Ordered")
        db.add(order_item)
        await db.flush()
        billable_items.append({"item_id":order_item.order_item_id,"name":test.test_name,"price":float(test.price or 0)})

        item_responses.append(LabOrderItemResponse(
            order_item_id=order_item.order_item_id, test_id=test.test_id,
            test_code=test.test_code, test_name=test.test_name, order_status="Ordered"
        ))

    await create_lab_invoice(db,patient.patient_id,order.lab_order_id,billable_items,cu.user_id)
    await db.commit()
    await db.refresh(order)

    doc_name = "Attending Physician"
    if req.doctor_id:
        d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id))
        doc = d_res.scalars().first()
        if doc: doc_name = f"Dr. {doc.first_name} {doc.last_name}"

    return LabOrderResponse(
        lab_order_id=order.lab_order_id, order_number=order.order_number,
        patient_id=patient.patient_id, patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn, doctor_name=doc_name, priority=req.priority, status="Ordered",
        ordered_at=order.ordered_at, clinical_notes=order.clinical_notes, items=item_responses
    )

# ----------------- Patient / Front-desk Laboratory Booking -----------------
@router.get("/booking-slots")
async def laboratory_booking_slots(
    day: date = Query(...), db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["patient", "receptionist", "admin", "super_admin"])),
):
    """Return 15-minute collection slots. Each slot supports four patients."""
    start = datetime.combine(day, time(7, 0))
    end = datetime.combine(day, time(19, 0))
    counts = (await db.execute(text("""
        SELECT scheduled_at, count(*) AS booked FROM laboratory.lab_orders
        WHERE scheduled_at >= :start AND scheduled_at < :end
          AND COALESCE((SELECT status_name FROM laboratory.lab_order_statuses s
              WHERE s.lab_order_status_id=lab_orders.lab_order_status_id),'Ordered') <> 'Cancelled'
        GROUP BY scheduled_at
    """), {"start": start, "end": end})).mappings().all()
    occupancy = {row["scheduled_at"]: row["booked"] for row in counts}
    now = datetime.now()
    slots = []
    cursor = start
    while cursor < end:
        booked = int(occupancy.get(cursor, 0))
        slots.append({
            "scheduled_at": cursor.isoformat(), "start_time": cursor.strftime("%H:%M"),
            "end_time": (cursor + timedelta(minutes=15)).strftime("%H:%M"),
            "booked": booked, "capacity": 4, "available": cursor > now and booked < 4,
        })
        cursor += timedelta(minutes=15)
    return {"day": day.isoformat(), "slot_minutes": 15, "slots": slots}


@router.get("/bookings")
async def list_laboratory_bookings(
    patient_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["patient", "receptionist", "lab_technician", "doctor", "admin", "super_admin"])),
):
    if "patient" in cu.roles:
        if not cu.patient_id:
            raise HTTPException(403, "Patient identity is not linked")
        patient_id = cu.patient_id
    where = "WHERE o.patient_id=:patient" if patient_id else ""
    result = await db.execute(text(f"""
        SELECT o.lab_order_id,o.order_number,o.patient_id,p.mrn,
          concat_ws(' ',p.first_name,p.last_name) patient_name,o.scheduled_at,
          o.booking_source,o.referral_type,o.referral_doctor_name,o.clinical_notes,
          s.status_name, string_agg(t.test_name, ', ' ORDER BY t.test_name) tests
        FROM laboratory.lab_orders o JOIN patient.patients p USING(patient_id)
        LEFT JOIN laboratory.lab_order_statuses s USING(lab_order_status_id)
        JOIN laboratory.lab_order_items i USING(lab_order_id)
        JOIN laboratory.lab_tests t USING(test_id) {where}
        GROUP BY o.lab_order_id,p.mrn,p.first_name,p.last_name,s.status_name
        ORDER BY COALESCE(o.scheduled_at,o.ordered_at) DESC LIMIT 200
    """), {"patient": patient_id} if patient_id else {})
    return [dict(row) for row in result.mappings()]


@router.post("/bookings", status_code=201)
async def create_laboratory_booking(
    req: LabBookingCreateRequest, db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["patient", "receptionist", "admin", "super_admin"])),
):
    await ensure_lab_masters(db)
    is_patient = "patient" in cu.roles
    patient_id = cu.patient_id if is_patient else req.patient_id
    if not patient_id or not await db.get(Patient, patient_id):
        raise HTTPException(404, "Patient record not found")
    if req.scheduled_at <= datetime.now() or req.scheduled_at.minute not in {0, 15, 30, 45} or req.scheduled_at.second:
        raise HTTPException(422, "Choose a future 15-minute laboratory slot")
    referral_type = req.referral_type.strip().title()
    if referral_type not in {"Doctor Referral", "Voluntary"}:
        raise HTTPException(422, "Referral type must be Doctor Referral or Voluntary")
    referral_doctor = await db.get(Doctor, req.referral_doctor_id) if req.referral_doctor_id else None
    if referral_type == "Doctor Referral" and not referral_doctor and not (req.referral_doctor_name or "").strip():
        raise HTTPException(422, "Select a hospital doctor or enter an external referring doctor")
    referral_doctor_name = (
        f"Dr. {referral_doctor.first_name} {referral_doctor.last_name}" if referral_doctor
        else (req.referral_doctor_name or "").strip() or None
    )
    # Serialize bookings for one collection slot so simultaneous requests cannot
    # exceed capacity. The lock is released automatically at transaction end.
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:slot))"), {"slot": req.scheduled_at.isoformat()})
    same_patient = await db.scalar(text("""SELECT count(*) FROM laboratory.lab_orders o
        LEFT JOIN laboratory.lab_order_statuses s USING(lab_order_status_id)
        WHERE o.patient_id=:patient AND o.scheduled_at=:slot
          AND COALESCE(s.status_name,'Ordered') <> 'Cancelled'"""),
        {"patient": patient_id, "slot": req.scheduled_at})
    if same_patient:
        raise HTTPException(409, "Patient already has a laboratory booking at this time")
    occupied = await db.scalar(text("""SELECT count(*) FROM laboratory.lab_orders o
        LEFT JOIN laboratory.lab_order_statuses s USING(lab_order_status_id)
        WHERE o.scheduled_at=:slot AND COALESCE(s.status_name,'Ordered') <> 'Cancelled'"""),
        {"slot": req.scheduled_at})
    if int(occupied or 0) >= 4:
        raise HTTPException(409, "This laboratory collection slot is full")
    status_obj = (await db.execute(select(LabOrderStatus).where(LabOrderStatus.status_name == "Ordered"))).scalars().first()
    priority = (await db.execute(select(LabOrderPriority).where(LabOrderPriority.priority_name == "Routine"))).scalars().first()
    booking_source = "Patient Portal" if is_patient else "Reception Desk"
    order = LabOrder(
        order_number=f"LAB-{req.scheduled_at:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        patient_id=patient_id, doctor_id=referral_doctor.doctor_id if referral_doctor else None,
        lab_order_status_id=status_obj.lab_order_status_id,
        priority_id=priority.priority_id, scheduled_at=req.scheduled_at,
        booking_source=booking_source, referral_type=referral_type,
        referral_doctor_name=referral_doctor_name,
        clinical_notes=req.clinical_notes, created_by=cu.user_id,
    )
    db.add(order)
    await db.flush()
    billable_items = []
    test_names = []
    for requested in req.items:
        test = await db.get(LabTest, requested.test_id)
        if not test or not test.is_active:
            raise HTTPException(404, "One of the selected laboratory tests is unavailable")
        item = LabOrderItem(lab_order_id=order.lab_order_id, test_id=test.test_id, order_status="Ordered")
        db.add(item)
        await db.flush()
        test_names.append(test.test_name)
        billable_items.append({"item_id": item.order_item_id, "name": test.test_name, "price": float(test.price or 0)})
    await create_lab_invoice(db, patient_id, order.lab_order_id, billable_items, cu.user_id)
    await db.commit()
    return {"lab_order_id": order.lab_order_id, "order_number": order.order_number,
            "scheduled_at": order.scheduled_at, "booking_source": booking_source,
            "referral_type": referral_type, "referral_doctor_name": order.referral_doctor_name,
            "tests": test_names, "status": "Ordered"}

async def effective_reference_range(db, parameter_id, sex=None, age=None,
                                    pregnancy_status=None, trimester=None, menstrual_phase=None):
    today = date.today()
    rules = (await db.execute(select(LabTestReferenceRange).where(
        LabTestReferenceRange.parameter_id == parameter_id,
        LabTestReferenceRange.is_active.is_(True),
        (LabTestReferenceRange.effective_from.is_(None) | (LabTestReferenceRange.effective_from <= today)),
        (LabTestReferenceRange.effective_to.is_(None) | (LabTestReferenceRange.effective_to >= today)),
    ))).scalars().all()
    def matches(rule):
        if rule.sex and rule.sex.upper() != "ALL" and rule.sex.upper() != (sex or "").upper(): return False
        if rule.age_min is not None and (age is None or age < float(rule.age_min)): return False
        if rule.age_max is not None and (age is None or age > float(rule.age_max)): return False
        if rule.pregnancy_status and rule.pregnancy_status.upper() != (pregnancy_status or "").upper(): return False
        if rule.trimester and rule.trimester != trimester: return False
        if rule.menstrual_phase and rule.menstrual_phase.upper() != (menstrual_phase or "").upper(): return False
        return True
    candidates = [rule for rule in rules if matches(rule)]
    def rank(rule):
        specificity = sum(value is not None for value in (
            rule.sex if rule.sex and rule.sex.upper() != "ALL" else None,
            rule.age_min, rule.age_max, rule.pregnancy_status, rule.trimester,
            rule.menstrual_phase, rule.clinical_condition,
        ))
        return (specificity, rule.version, rule.effective_from or date.min)
    return max(candidates, key=rank) if candidates else None

def calculated_result_flag(value, reference):
    if reference is None or value is None: return "Normal"
    if reference.critical_low is not None and value < reference.critical_low: return "Critical"
    if reference.critical_high is not None and value > reference.critical_high: return "Critical"
    if reference.min_value is not None and value < reference.min_value: return "Low"
    if reference.max_value is not None and value > reference.max_value: return "High"
    return "Normal"

# ----------------- Sample Collection -----------------
@router.post("/collect-sample", response_model=SampleResponse, status_code=201)
async def collect_sample(
    req: SampleCollectionRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["lab_technician", "nurse", "admin", "super_admin"]))
):
    await ensure_lab_masters(db)
    it_res = await db.execute(select(LabOrderItem).where(LabOrderItem.order_item_id == req.order_item_id).with_for_update())
    item = it_res.scalars().first()
    if not item: raise HTTPException(404, "Lab order item not found")
    if item.order_status != "Ordered":
        raise HTTPException(409, "Sample has already been collected or order is closed")

    st_res = await db.execute(select(SampleType).where(SampleType.sample_type_name == req.sample_type))
    st = st_res.scalars().first()

    barcode = f"SMP-{str(uuid.uuid4())[:8].upper()}"
    sample = LabSample(
        sample_barcode=barcode, order_item_id=item.order_item_id,
        sample_type_id=st.sample_type_id if st else None, collected_at=datetime.utcnow()
    )
    db.add(sample)
    item.order_status = "Sample Collected"

    ord_res = await db.execute(select(LabOrder).where(LabOrder.lab_order_id == item.lab_order_id))
    order = ord_res.scalars().first()
    if order:
        st_coll = await db.execute(select(LabOrderStatus).where(LabOrderStatus.status_name == "Sample Collected"))
        st_obj = st_coll.scalars().first()
        if st_obj: order.lab_order_status_id = st_obj.lab_order_status_id

    await db.commit()
    await db.refresh(sample)

    return SampleResponse(
        sample_id=sample.sample_id, order_item_id=item.order_item_id,
        sample_barcode=sample.sample_barcode, sample_type=req.sample_type,
        collected_at=sample.collected_at
    )

# ----------------- Result Entry & Approval -----------------
@router.get("/results/{result_entry_id}", response_model=LabResultResponse)
async def get_lab_result(
    result_entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["lab_technician", "doctor", "nurse", "admin"]))
):
    entry = (await db.execute(select(LabResultEntry).where(
        LabResultEntry.result_entry_id == result_entry_id))).scalars().first()
    if not entry:
        raise HTTPException(404, "Result entry not found")
    item = await db.get(LabOrderItem, entry.order_item_id)
    test = await db.get(LabTest, item.test_id) if item else None
    values = (await db.execute(select(LabResultParameter).where(
        LabResultParameter.result_entry_id == entry.result_entry_id))).scalars().all()
    parameters = []
    for value in values:
        definition = await db.get(LabTestParameter, value.parameter_id)
        parameters.append(ParameterResultResponse(
            parameter_name=definition.parameter_name if definition else "Parameter",
            unit=(definition.unit or "") if definition else "",
            normal_range=(definition.normal_range or "") if definition else "",
            result_value=value.result_value, result_flag=value.result_flag,
        ))
    return LabResultResponse(
        result_entry_id=entry.result_entry_id, order_item_id=entry.order_item_id,
        test_name=test.test_name if test else "Laboratory test", result_status=entry.result_status,
        entered_at=entry.entered_at, approved_at=entry.approved_at,
        approved_by=entry.approved_by, remarks=entry.remarks, parameters=parameters,
    )

@router.post("/results", response_model=LabResultResponse, status_code=201)
async def enter_lab_results(
    req: LabResultEntryRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["lab_technician", "doctor", "admin", "super_admin"]))
):
    it_res = await db.execute(select(LabOrderItem).where(LabOrderItem.order_item_id == req.order_item_id).with_for_update())
    item = it_res.scalars().first()
    if not item: raise HTTPException(404, "Lab order item not found")
    if item.order_status != "Sample Collected":
        raise HTTPException(409, "Collect a sample before results; existing results cannot be overwritten")
    if len({p.parameter_id for p in req.parameters}) != len(req.parameters):
        raise HTTPException(422, "Duplicate result parameters")

    t_res = await db.execute(select(LabTest).where(LabTest.test_id == item.test_id))
    test = t_res.scalars().first()
    demographics = (await db.execute(text("""
        SELECT upper(g.gender_name) AS sex,
               extract(year FROM age(current_date,p.date_of_birth))::int AS age
        FROM laboratory.lab_order_items i
        JOIN laboratory.lab_orders o USING(lab_order_id)
        JOIN patient.patients p USING(patient_id)
        JOIN patient.genders g USING(gender_id)
        WHERE i.order_item_id=:item
    """), {"item": item.order_item_id})).mappings().first() or {}

    entry = LabResultEntry(
        order_item_id=item.order_item_id, technician_id=cu.user_id,
        result_status="Entered", entered_at=datetime.utcnow(), remarks=req.technician_remarks
    )
    db.add(entry)
    await db.flush()

    param_results = []
    for pr in req.parameters:
        param_res = await db.execute(select(LabTestParameter).where(LabTestParameter.parameter_id == pr.parameter_id))
        param = param_res.scalars().first()
        if not param or param.test_id != item.test_id:
            raise HTTPException(422, "Parameter does not belong to this test")

        rp = LabResultParameter(
            result_entry_id=entry.result_entry_id, parameter_id=param.parameter_id,
            result_value=pr.result_value, result_flag="Normal"
        )
        if param.result_type in {"NUMERIC", "CALCULATED"}:
            try:
                rp.numeric_value = Decimal(pr.result_value.strip())
            except (InvalidOperation, AttributeError):
                raise HTTPException(422, f"{param.parameter_name} requires a numeric result")
        elif param.result_type == "BOOLEAN":
            normalized = pr.result_value.strip().lower()
            if normalized not in {"true", "false", "positive", "negative", "present", "absent"}:
                raise HTTPException(422, f"{param.parameter_name} requires a boolean result")
            rp.boolean_value = normalized in {"true", "positive", "present"}
        elif param.result_type in {"ENUM", "QUALITATIVE"}:
            if param.allowed_values and pr.result_value not in param.allowed_values:
                raise HTTPException(422, f"{param.parameter_name} must be one of: {', '.join(param.allowed_values)}")
            rp.coded_value = pr.result_value
        else:
            rp.text_value = pr.result_value
        reference = await effective_reference_range(
            db, param.parameter_id, demographics.get("sex"), demographics.get("age"),
            req.pregnancy_status, req.trimester, req.menstrual_phase,
        )
        rp.reference_range_id = reference.reference_range_id if reference else None
        rp.result_flag = calculated_result_flag(rp.numeric_value, reference)
        db.add(rp)
        param_results.append(ParameterResultResponse(
            parameter_name=param.parameter_name, unit=param.unit or "",
            normal_range=param.normal_range or "", result_value=pr.result_value,
            result_flag=rp.result_flag
        ))

    item.order_status = "In Analysis"
    await db.commit()
    await db.refresh(entry)

    return LabResultResponse(
        result_entry_id=entry.result_entry_id, order_item_id=item.order_item_id,
        test_name=test.test_name if test else "Diagnostic Test", result_status="Entered",
        entered_at=entry.entered_at, approved_at=None, approved_by=None,
        remarks=entry.remarks, parameters=param_results
    )

@router.post("/results/{result_entry_id}/approve", response_model=LabResultResponse)
async def approve_lab_results(
    result_entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["pathologist"]))
):
    if "pathologist" not in cu.roles:
        raise HTTPException(403, "Only a pathologist may approve laboratory reports")
    re_res = await db.execute(select(LabResultEntry).where(LabResultEntry.result_entry_id == result_entry_id))
    entry = re_res.scalars().first()
    if not entry: raise HTTPException(404, "Result entry not found")
    if entry.result_status == "Approved": raise HTTPException(409, "Results are already approved")

    entry.approved_by = cu.user_id
    entry.approved_at = datetime.utcnow()
    entry.result_status = "Approved"
    await db.execute(text("""
        INSERT INTO laboratory.lab_result_approvals
          (result_entry_id,approved_by,approval_status,approval_notes,approved_at)
        VALUES (:result,:doctor,'APPROVED','Approved and released in doctor portal',:approved_at)
    """), {"result": entry.result_entry_id, "doctor": cu.user_id,
           "approved_at": entry.approved_at})

    it_res = await db.execute(select(LabOrderItem).where(LabOrderItem.order_item_id == entry.order_item_id))
    item = it_res.scalars().first()
    if item:
        item.order_status = "Completed"
        ord_res = await db.execute(select(LabOrder).where(LabOrder.lab_order_id == item.lab_order_id))
        order = ord_res.scalars().first()
        if order:
            st_comp = await db.execute(select(LabOrderStatus).where(LabOrderStatus.status_name == "Completed"))
            st_obj = st_comp.scalars().first()
            unfinished = await db.scalar(select(LabOrderItem).where(LabOrderItem.lab_order_id == item.lab_order_id, LabOrderItem.order_status != "Completed"))
            if st_obj and not unfinished: order.lab_order_status_id = st_obj.lab_order_status_id
            flags=await db.scalar(select(func.count(LabResultParameter.result_parameter_id)).where(LabResultParameter.result_entry_id==entry.result_entry_id,LabResultParameter.result_flag.in_(["Critical","High","Low"])))
            if order.created_by:
                await db.execute(text("INSERT INTO core.notifications(recipient_id,recipient_type,source_module,source_reference_id,subject,body,status) VALUES(:r,'User','Laboratory',:src,:s,:b,'pending')"),{"r":order.created_by,"src":entry.result_entry_id,"s":"Critical laboratory result" if flags else "Laboratory result approved","b":f"{test.test_name if 'test' in locals() and test else 'Laboratory'} results are ready."})

    p_res = await db.execute(select(LabResultParameter).where(LabResultParameter.result_entry_id == entry.result_entry_id))
    params = p_res.scalars().all()
    param_results = []
    for p in params:
        param_def = await db.execute(select(LabTestParameter).where(LabTestParameter.parameter_id == p.parameter_id))
        pdef = param_def.scalars().first()
        param_results.append(ParameterResultResponse(
            parameter_name=pdef.parameter_name if pdef else "Parameter",
            unit=pdef.unit or "" if pdef else "",
            normal_range=pdef.normal_range or "" if pdef else "",
            result_value=p.result_value, result_flag=p.result_flag
        ))

    t_res = await db.execute(select(LabTest).where(LabTest.test_id == item.test_id))
    test = t_res.scalars().first()

    await db.commit()

    return LabResultResponse(
        result_entry_id=entry.result_entry_id, order_item_id=entry.order_item_id,
        test_name=test.test_name if test else "Diagnostic Test", result_status="Approved",
        entered_at=entry.entered_at, approved_at=entry.approved_at, approved_by=entry.approved_by,
        remarks=entry.remarks, parameters=param_results
    )


@router.post("/results/{result_entry_id}/acknowledge")
async def acknowledge_lab_result(
    result_entry_id: uuid.UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "surgeon", "admin", "super_admin"]))
):
    """Doctor digitally acknowledges review of an approved laboratory result."""
    res = await db.execute(select(LabResultEntry).where(LabResultEntry.result_entry_id == result_entry_id).with_for_update())
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(404, "Lab result entry not found")
    if entry.result_status != "Approved":
        raise HTTPException(400, "Only approved lab results can be acknowledged")

    entry.acknowledged_by = cu.user_id
    entry.acknowledged_at = datetime.utcnow()
    entry.acknowledgement_notes = notes
    await db.commit()
    return {
        "message": "Laboratory result acknowledged successfully",
        "result_entry_id": str(entry.result_entry_id),
        "acknowledged_by": str(cu.user_id),
        "acknowledged_at": entry.acknowledged_at.isoformat()
    }
