import uuid
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.models.inpatient_emergency_models import (
    BloodGroupType, BloodComponentType, BloodUnit, BloodRequest, CrossMatchTest, BloodTransfusion
)
from app.schemas.inpatient_emergency import (
    BloodUnitResponse, BloodRequestCreate, BloodRequestResponse,
    CrossMatchCreate, CrossMatchResponse, BloodTransfusionCreate, BloodTransfusionResponse
)

router = APIRouter(prefix="/blood-bank", tags=["Blood Bank & Transfusions"])

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
    cu: CurrentUser = Depends(get_current_user)
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
    cu: CurrentUser = Depends(require_roles(["lab_technician", "doctor", "admin", "super_admin"]))
):
    br_res = await db.execute(select(BloodRequest).where(BloodRequest.blood_request_id == req.blood_request_id))
    br = br_res.scalars().first()
    if not br: raise HTTPException(404, "Blood request not found")

    bu_res = await db.execute(select(BloodUnit).where(BloodUnit.blood_unit_id == req.blood_unit_id))
    bu = bu_res.scalars().first()
    if not bu: raise HTTPException(404, "Blood unit not found")

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

@router.post("/transfusions", response_model=BloodTransfusionResponse, status_code=201)
async def record_transfusion(
    req: BloodTransfusionCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["nurse", "doctor", "admin", "super_admin"]))
):
    br_res = await db.execute(select(BloodRequest).where(BloodRequest.blood_request_id == req.blood_request_id))
    br = br_res.scalars().first()
    if not br: raise HTTPException(404, "Blood request not found")

    bu_res = await db.execute(select(BloodUnit).where(BloodUnit.blood_unit_id == req.blood_unit_id))
    bu = bu_res.scalars().first()
    if not bu: raise HTTPException(404, "Blood unit not found")

    trans = BloodTransfusion(
        blood_request_id=br.blood_request_id,
        blood_unit_id=bu.blood_unit_id,
        patient_id=br.patient_id,
        administered_by=cu.user_id,
        start_time=datetime.utcnow(),
        volume_transfused=req.volume_transfused,
        status="completed",
        notes=req.notes
    )
    db.add(trans)
    bu.status = "transfused"
    br.status = "completed"

    await db.commit()
    await db.refresh(trans)

    return BloodTransfusionResponse(
        transfusion_id=trans.transfusion_id,
        patient_id=trans.patient_id,
        blood_unit_number=bu.unit_number,
        volume_transfused=trans.volume_transfused,
        status=trans.status,
        administered_at=trans.start_time,
        notes=trans.notes
    )
