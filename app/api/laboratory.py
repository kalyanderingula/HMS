import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.api.doctor import Doctor
from app.models.laboratory_models import (
    LabTest, LabTestParameter, LabOrder, LabOrderItem,
    LabOrderStatus, LabOrderPriority, SampleType, LabSample,
    LabResultEntry, LabResultParameter
)
from app.schemas.laboratory import (
    LabTestCreateRequest, LabTestResponse, LabParameterResponse,
    LabOrderCreateRequest, LabOrderResponse, LabOrderItemResponse,
    SampleCollectionRequest, SampleResponse,
    LabResultEntryRequest, LabResultResponse, ParameterResultResponse
)

router = APIRouter(prefix="/laboratory", tags=["Laboratory Information System"])

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
    cu: CurrentUser = Depends(get_current_user)
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
            fasting_required=t.fasting_required or False, price=float(t.price or 0),
            parameters=[LabParameterResponse(
                parameter_id=p.parameter_id, parameter_name=p.parameter_name,
                unit=p.unit or "", normal_range=p.normal_range or ""
            ) for p in params]
        ))
    return results

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
        price=req.price, is_active=True
    )
    db.add(t)
    await db.flush()

    param_responses = []
    for p in req.parameters:
        param = LabTestParameter(
            test_id=t.test_id, parameter_name=p.parameter_name, unit=p.unit,
            normal_range=p.normal_range, critical_low=p.critical_low, critical_high=p.critical_high
        )
        db.add(param)
        await db.flush()
        param_responses.append(LabParameterResponse(
            parameter_id=param.parameter_id, parameter_name=param.parameter_name,
            unit=param.unit, normal_range=param.normal_range
        ))

    await db.commit()
    await db.refresh(t)
    return LabTestResponse(
        test_id=t.test_id, test_code=t.test_code, test_name=t.test_name,
        test_method=t.test_method, turnaround_time_hours=t.turnaround_time_hours,
        fasting_required=t.fasting_required, price=float(t.price),
        parameters=param_responses
    )

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
    for it in req.items:
        t_res = await db.execute(select(LabTest).where(LabTest.test_id == it.test_id))
        test = t_res.scalars().first()
        if not test: raise HTTPException(404, "Requested lab test not found")

        order_item = LabOrderItem(lab_order_id=order.lab_order_id, test_id=test.test_id, order_status="Ordered")
        db.add(order_item)
        await db.flush()

        item_responses.append(LabOrderItemResponse(
            order_item_id=order_item.order_item_id, test_id=test.test_id,
            test_code=test.test_code, test_name=test.test_name, order_status="Ordered"
        ))

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
            result_value=pr.result_value, result_flag=pr.result_flag
        )
        db.add(rp)
        param_results.append(ParameterResultResponse(
            parameter_name=param.parameter_name, unit=param.unit or "",
            normal_range=param.normal_range or "", result_value=pr.result_value,
            result_flag=pr.result_flag
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
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"]))
):
    re_res = await db.execute(select(LabResultEntry).where(LabResultEntry.result_entry_id == result_entry_id))
    entry = re_res.scalars().first()
    if not entry: raise HTTPException(404, "Result entry not found")

    entry.approved_by = cu.user_id
    entry.approved_at = datetime.utcnow()
    entry.result_status = "Approved"

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
