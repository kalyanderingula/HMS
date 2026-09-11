import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Literal, Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUser, require_roles
from app.api.doctor import Doctor
from app.config import get_db
from app.models.inpatient_emergency_models import (
    SurgeryRequest, SurgerySchedule, OTCSSDTray, OTImplant, OTRecoveryRecord
)
from app.models.patient import Patient
from app.schemas.inpatient_emergency import (
    SurgeryRequestCreate, SurgeryScheduleCreate, SurgeryScheduleResponse,
    OTCSSDTrayCreate, OTCSSDTrayResponse, OTImplantCreate, OTImplantResponse
)

surgery_access = require_roles(["surgeon", "doctor", "ot_nurse", "anesthesiologist", "nurse", "admin"])
surgeon_access = require_roles(["surgeon", "doctor", "admin"])
router = APIRouter(prefix="/surgery", tags=["Surgery & Operation Theatre"], dependencies=[Depends(surgery_access)])


class PreoperativeChecklist(BaseModel):
    consent_verified: bool
    identity_verified: bool
    surgical_site_verified: bool
    allergies_reviewed: bool
    investigations_reviewed: bool
    fasting_confirmed: bool
    anesthesia_cleared: bool
    asa_classification: str = Field(min_length=1, max_length=20)
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def require_all_checks(self):
        if not all((self.consent_verified, self.identity_verified, self.surgical_site_verified,
                    self.allergies_reviewed, self.investigations_reviewed, self.fasting_confirmed,
                    self.anesthesia_cleared)):
            raise ValueError("Every pre-operative safety check must be completed")
        return self


class CaseStart(BaseModel):
    anesthesia_type: str = Field(min_length=2, max_length=100)


class ConsumableCreate(BaseModel):
    item_name: str = Field(min_length=2, max_length=255)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class OperationComplete(BaseModel):
    surgical_findings: str = Field(min_length=2, max_length=8000)
    outcome: str = Field(min_length=2, max_length=4000)
    complications: str = Field(default="None", max_length=4000)


class RecoveryCreate(BaseModel):
    recovery_status: Literal["Stable", "Needs Observation", "Critical"]
    pain_score: int = Field(ge=0, le=10)
    observations: str = Field(min_length=2, max_length=4000)
    disposition: Literal["Ward", "ICU", "Discharged"]
    aldrete_score: Optional[int] = Field(default=None, ge=0, le=10)
    aldrete_criteria: Optional[dict] = None


async def locked_schedule(db, schedule_id):
    schedule = (await db.execute(select(SurgerySchedule).where(
        SurgerySchedule.surgery_schedule_id == schedule_id).with_for_update())).scalars().first()
    if not schedule:
        raise HTTPException(404, "Surgery schedule not found")
    return schedule


@router.get("/worklist")
async def surgery_worklist(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""SELECT sr.surgery_request_id,ss.surgery_schedule_id,p.patient_id,p.mrn,
        concat_ws(' ',p.first_name,p.last_name) patient_name,sr.procedure_name,sr.procedure_code,
        sr.request_priority,sr.request_reason,sr.request_status,sr.requested_date,sr.estimated_charge,
        ss.ot_room_number,ss.scheduled_start,ss.scheduled_end,ss.schedule_status,
        concat_ws(' ',d.first_name,d.last_name) primary_surgeon_name,
        EXISTS(SELECT 1 FROM surgery.ot_preoperative_checklists pc WHERE pc.surgery_request_id=sr.surgery_request_id) preop_complete,
        EXISTS(SELECT 1 FROM surgery.ot_recovery_records rr WHERE rr.surgery_schedule_id=ss.surgery_schedule_id) recovery_complete
        FROM surgery.surgery_requests sr JOIN patient.patients p USING(patient_id)
        LEFT JOIN surgery.surgery_scheduling ss USING(surgery_request_id)
        LEFT JOIN doctor.doctors d ON d.doctor_id=ss.primary_surgeon_id
        ORDER BY CASE sr.request_priority WHEN 'Emergency' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END,
                 COALESCE(ss.scheduled_start,sr.requested_date)"""))
    return [dict(row) for row in rows.mappings()]


@router.get("/options")
async def surgery_options(db: AsyncSession = Depends(get_db)):
    doctors = [dict(row) for row in (await db.execute(text("""SELECT doctor_id,
        concat('Dr. ',first_name,' ',last_name) label FROM doctor.doctors
        WHERE deleted_at IS NULL ORDER BY first_name,last_name"""))).mappings()]
    return {"doctors": doctors, "rooms": ["OT Suite 1", "OT Suite 2", "Emergency OT"]}


@router.post("/requests", status_code=201)
async def create_surgery_request(req: SurgeryRequestCreate, db: AsyncSession = Depends(get_db),
                                 user: CurrentUser = Depends(surgeon_access)):
    patient = await db.scalar(select(Patient).where(Patient.patient_id == req.patient_id))
    if not patient: raise HTTPException(404, "Patient not found")
    if req.urgency not in {"Emergency", "Urgent", "Elective"}: raise HTTPException(422, "Invalid surgery urgency")
    surgery_request = SurgeryRequest(patient_id=req.patient_id, requested_by=user.user_id,
        procedure_name=req.procedure_name, procedure_code=req.procedure_code,
        request_priority=req.urgency, request_reason=req.clinical_indication,
        estimated_charge=req.estimated_charge, request_status="Requested")
    db.add(surgery_request); await db.commit(); await db.refresh(surgery_request)
    return {"surgery_request_id": surgery_request.surgery_request_id, "status": "Requested"}


@router.post("/schedule", response_model=SurgeryScheduleResponse, status_code=201)
async def schedule_surgery(req: SurgeryScheduleCreate, db: AsyncSession = Depends(get_db),
                           _user: CurrentUser = Depends(surgery_access)):
    if req.scheduled_end <= req.scheduled_start: raise HTTPException(422, "Scheduled end must be after the start")
    surgery_request = (await db.execute(select(SurgeryRequest).where(
        SurgeryRequest.surgery_request_id == req.surgery_request_id).with_for_update())).scalars().first()
    if not surgery_request: raise HTTPException(404, "Surgery request not found")
    if surgery_request.request_status != "Requested": raise HTTPException(409, "Surgery request is not awaiting scheduling")
    doctor = await db.scalar(select(Doctor).where(Doctor.doctor_id == req.primary_surgeon_id))
    if not doctor: raise HTTPException(404, "Primary surgeon not found")
    overlap = await db.scalar(text("""SELECT surgery_schedule_id FROM surgery.surgery_scheduling
        WHERE schedule_status NOT IN ('Cancelled','Completed') AND scheduled_start<:finish AND scheduled_end>:start
        AND (ot_room_number=:room OR primary_surgeon_id=:surgeon) LIMIT 1"""),
        {"finish":req.scheduled_end,"start":req.scheduled_start,"room":req.ot_room_number,"surgeon":req.primary_surgeon_id})
    if overlap: raise HTTPException(409, "Operating theatre or surgeon is already booked for that time")
    schedule = SurgerySchedule(surgery_request_id=req.surgery_request_id, ot_room_number=req.ot_room_number,
        primary_surgeon_id=req.primary_surgeon_id, anesthesiologist_name=req.anesthesiologist_name,
        scheduled_start=req.scheduled_start, scheduled_end=req.scheduled_end, schedule_status="Scheduled")
    db.add(schedule); surgery_request.request_status = "Scheduled"
    await db.commit(); await db.refresh(schedule)
    patient = await db.get(Patient, surgery_request.patient_id)
    return SurgeryScheduleResponse(surgery_schedule_id=schedule.surgery_schedule_id,
        patient_name=f"{patient.first_name} {patient.last_name}", procedure_name=surgery_request.procedure_name,
        ot_room_number=schedule.ot_room_number, scheduled_start=schedule.scheduled_start,
        scheduled_end=schedule.scheduled_end, primary_surgeon_name=f"Dr. {doctor.first_name} {doctor.last_name}",
        schedule_status=schedule.schedule_status)


@router.post("/requests/{request_id}/preoperative-checklist", status_code=201)
async def complete_preop(request_id: uuid.UUID, req: PreoperativeChecklist, db: AsyncSession = Depends(get_db),
                         user: CurrentUser = Depends(surgery_access)):
    surgery_request = (await db.execute(select(SurgeryRequest).where(
        SurgeryRequest.surgery_request_id == request_id).with_for_update())).scalars().first()
    if not surgery_request: raise HTTPException(404, "Surgery request not found")
    if surgery_request.request_status != "Scheduled": raise HTTPException(409, "Surgery must be scheduled before pre-operative clearance")
    if await db.scalar(text("SELECT checklist_id FROM surgery.ot_preoperative_checklists WHERE surgery_request_id=:id"),{"id":request_id}): raise HTTPException(409, "Pre-operative checklist is already complete")
    await db.execute(text("""INSERT INTO surgery.ot_preoperative_checklists
        (surgery_request_id,consent_verified,identity_verified,surgical_site_verified,allergies_reviewed,
         investigations_reviewed,fasting_confirmed,anesthesia_cleared,asa_classification,notes,completed_by)
        VALUES(:id,true,true,true,true,true,true,true,:asa,:notes,:user)"""),
        {"id":request_id,"asa":req.asa_classification,"notes":req.notes,"user":user.user_id})
    surgery_request.request_status = "Pre-op Cleared"; await db.commit()
    return {"surgery_request_id":request_id,"status":"Pre-op Cleared"}


@router.post("/cases/{schedule_id}/start")
async def start_case(schedule_id: uuid.UUID, req: CaseStart, db: AsyncSession = Depends(get_db),
                     _user: CurrentUser = Depends(surgery_access)):
    schedule = await locked_schedule(db, schedule_id); surgery_request = await db.get(SurgeryRequest, schedule.surgery_request_id)
    if schedule.schedule_status != "Scheduled" or surgery_request.request_status != "Pre-op Cleared": raise HTTPException(409, "A scheduled case requires completed pre-operative clearance")
    schedule.schedule_status="In Progress"; schedule.actual_start=datetime.utcnow(); schedule.anesthesia_type=req.anesthesia_type; surgery_request.request_status="In Progress"
    await db.commit(); return {"surgery_schedule_id":schedule_id,"status":"In Progress"}


@router.post("/cases/{schedule_id}/consumables", status_code=201)
async def add_consumable(schedule_id: uuid.UUID, req: ConsumableCreate, db: AsyncSession = Depends(get_db),
                         _user: CurrentUser = Depends(surgery_access)):
    schedule = await locked_schedule(db, schedule_id)
    if schedule.schedule_status != "In Progress": raise HTTPException(409, "Consumables can only be recorded during surgery")
    item_id = uuid.uuid4()
    await db.execute(text("INSERT INTO surgery.ot_consumables(consumable_id,surgery_schedule_id,item_name,quantity,unit_price) VALUES(:id,:schedule,:name,:quantity,:price)"), {"id": item_id, "schedule": schedule_id, "name": req.item_name, "quantity": req.quantity, "price": req.unit_price})
    await db.commit()
    return {"consumable_id": item_id, "line_total": req.quantity * req.unit_price}


# CSSD (Central Sterile Services Department) Tray Tracking
@router.post("/cases/{schedule_id}/cssd-trays", response_model=OTCSSDTrayResponse, status_code=201)
async def verify_cssd_tray(
    schedule_id: uuid.UUID,
    req: OTCSSDTrayCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(surgery_access)
):
    schedule = await locked_schedule(db, schedule_id)
    if req.sterile_expiry_date < date.today():
        raise HTTPException(status_code=400, detail="Sterile expiry date has passed. Unsterile CSSD tray cannot be used.")
    if not req.is_indicator_passed:
        raise HTTPException(status_code=400, detail="Autoclave chemical/biological indicator check failed. Tray is unsterile.")

    tray = OTCSSDTray(
        surgery_schedule_id=schedule_id,
        tray_name=req.tray_name,
        tray_barcode=req.tray_barcode,
        autoclave_batch_number=req.autoclave_batch_number,
        sterilization_date=req.sterilization_date,
        sterile_expiry_date=req.sterile_expiry_date,
        is_indicator_passed=req.is_indicator_passed,
        verified_by=user.user_id,
        created_at=datetime.utcnow()
    )
    db.add(tray)
    await db.commit()
    await db.refresh(tray)

    return OTCSSDTrayResponse(
        tray_id=tray.tray_id,
        surgery_schedule_id=tray.surgery_schedule_id,
        tray_name=tray.tray_name,
        tray_barcode=tray.tray_barcode,
        autoclave_batch_number=tray.autoclave_batch_number,
        sterilization_date=tray.sterilization_date,
        sterile_expiry_date=tray.sterile_expiry_date,
        is_indicator_passed=tray.is_indicator_passed,
        created_at=tray.created_at
    )


@router.get("/cases/{schedule_id}/cssd-trays", response_model=List[OTCSSDTrayResponse])
async def list_case_cssd_trays(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(surgery_access)
):
    res = await db.execute(
        select(OTCSSDTray).where(OTCSSDTray.surgery_schedule_id == schedule_id).order_by(OTCSSDTray.created_at)
    )
    trays = res.scalars().all()
    return [
        OTCSSDTrayResponse(
            tray_id=t.tray_id,
            surgery_schedule_id=t.surgery_schedule_id,
            tray_name=t.tray_name,
            tray_barcode=t.tray_barcode,
            autoclave_batch_number=t.autoclave_batch_number,
            sterilization_date=t.sterilization_date,
            sterile_expiry_date=t.sterile_expiry_date,
            is_indicator_passed=t.is_indicator_passed,
            created_at=t.created_at
        )
        for t in trays
    ]


# Surgical Implants & Prosthetics Tracking
@router.post("/cases/{schedule_id}/implants", response_model=OTImplantResponse, status_code=201)
async def record_surgical_implant(
    schedule_id: uuid.UUID,
    req: OTImplantCreate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(surgery_access)
):
    schedule = await locked_schedule(db, schedule_id)
    if schedule.schedule_status not in ("In Progress", "Recovery", "Completed"):
        raise HTTPException(409, "Implants can only be recorded during or post-procedure")

    implant = OTImplant(
        surgery_schedule_id=schedule_id,
        implant_name=req.implant_name,
        manufacturer=req.manufacturer,
        serial_number=req.serial_number,
        lot_number=req.lot_number,
        expiry_date=req.expiry_date,
        created_at=datetime.utcnow()
    )
    db.add(implant)
    await db.commit()
    await db.refresh(implant)

    return OTImplantResponse(
        implant_id=implant.implant_id,
        surgery_schedule_id=implant.surgery_schedule_id,
        implant_name=implant.implant_name,
        manufacturer=implant.manufacturer,
        serial_number=implant.serial_number,
        lot_number=implant.lot_number,
        expiry_date=implant.expiry_date,
        created_at=implant.created_at
    )


@router.get("/cases/{schedule_id}/implants", response_model=List[OTImplantResponse])
async def list_case_implants(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(surgery_access)
):
    res = await db.execute(
        select(OTImplant).where(OTImplant.surgery_schedule_id == schedule_id).order_by(OTImplant.created_at)
    )
    implants = res.scalars().all()
    return [
        OTImplantResponse(
            implant_id=i.implant_id,
            surgery_schedule_id=i.surgery_schedule_id,
            implant_name=i.implant_name,
            manufacturer=i.manufacturer,
            serial_number=i.serial_number,
            lot_number=i.lot_number,
            expiry_date=i.expiry_date,
            created_at=i.created_at
        )
        for i in implants
    ]


async def create_surgery_invoice(db, schedule, surgery_request, user_id):
    existing = await db.scalar(text("SELECT invoice_id FROM billing.invoice_items WHERE item_type='Procedure' AND item_reference_id=:source"), {"source": schedule.surgery_schedule_id})
    if existing: return existing
    account = await db.scalar(text("SELECT billing_account_id FROM billing.billing_accounts WHERE patient_id=:patient ORDER BY created_at LIMIT 1 FOR UPDATE"), {"patient": surgery_request.patient_id})
    if not account:
        account = uuid.uuid4()
        await db.execute(text("INSERT INTO billing.billing_accounts(billing_account_id,patient_id,account_number,account_status,total_due,total_paid) VALUES(:id,:patient,:number,'Active',0,0)"), {"id": account, "patient": surgery_request.patient_id, "number": f"ACC-{uuid.uuid4().hex}"})
    consumables = await db.scalar(text("SELECT COALESCE(sum(quantity*unit_price),0) FROM surgery.ot_consumables WHERE surgery_schedule_id=:id"), {"id": schedule.surgery_schedule_id})
    charge = Decimal(surgery_request.estimated_charge or 0) + Decimal(consumables or 0)
    invoice = uuid.uuid4()
    status_id = await db.scalar(text("INSERT INTO billing.billing_statuses(status_name) VALUES('Pending') ON CONFLICT(status_name) DO UPDATE SET status_name=EXCLUDED.status_name RETURNING billing_status_id"))
    await db.execute(text("""INSERT INTO billing.invoices(invoice_id,invoice_number,billing_account_id,patient_id,billing_status_id,subtotal_amount,tax_amount,discount_amount,total_amount,paid_amount,balance_amount,notes,created_by)
        VALUES(:id,:number,:account,:patient,:status,:charge,0,0,:charge,0,:charge,'Automatic surgery charge',:user)"""), {"id": invoice, "number": f"INV-{uuid.uuid4().hex[:16].upper()}", "account": account, "patient": surgery_request.patient_id, "status": status_id, "charge": charge, "user": user_id})
    await db.execute(text("INSERT INTO billing.invoice_items(invoice_id,item_type,item_reference_id,item_name,quantity,unit_price,tax_amount,discount_amount,line_total) VALUES(:invoice,'Procedure',:source,:name,1,:charge,0,0,:charge)"), {"invoice": invoice, "source": schedule.surgery_schedule_id, "name": surgery_request.procedure_name, "charge": charge})
    await db.execute(text("UPDATE billing.billing_accounts SET total_due=COALESCE(total_due,0)+:charge WHERE billing_account_id=:id"), {"charge": charge, "id": account})
    return invoice


@router.post("/cases/{schedule_id}/complete")
async def complete_surgery(schedule_id: uuid.UUID, req: OperationComplete, db: AsyncSession = Depends(get_db),
                           user: CurrentUser = Depends(surgeon_access)):
    schedule = await locked_schedule(db, schedule_id)
    if schedule.schedule_status != "In Progress": raise HTTPException(409, "Only an in-progress surgery can be completed")
    surgery_request = await db.get(SurgeryRequest, schedule.surgery_request_id)
    schedule.schedule_status = "Recovery"
    schedule.actual_end = datetime.utcnow()
    schedule.surgical_findings = req.surgical_findings
    schedule.outcome = req.outcome
    schedule.complications = req.complications
    schedule.completed_by = user.user_id
    surgery_request.request_status = "Recovery"
    invoice_id = await create_surgery_invoice(db, schedule, surgery_request, user.user_id)
    await db.execute(text("INSERT INTO core.notifications(recipient_id,recipient_type,source_module,source_reference_id,subject,body,status) VALUES(:recipient,'User','Surgery',:source,'Surgery completed',:body,'pending')"), {"recipient": surgery_request.requested_by, "source": schedule_id, "body": f"{surgery_request.procedure_name} completed; patient transferred to recovery."})
    await db.commit()
    return {"surgery_schedule_id": schedule_id, "status": "Recovery", "invoice_id": invoice_id}


@router.post("/cases/{schedule_id}/recovery", status_code=201)
async def record_recovery(schedule_id: uuid.UUID, req: RecoveryCreate, db: AsyncSession = Depends(get_db),
                          user: CurrentUser = Depends(surgery_access)):
    schedule = await locked_schedule(db, schedule_id)
    if schedule.schedule_status != "Recovery": raise HTTPException(409, "Case is not awaiting recovery assessment")

    # Aldrete Safety Gate check
    if req.disposition == "Ward" and req.aldrete_score is not None and req.aldrete_score < 9:
        obs_lower = req.observations.lower()
        if not any(k in obs_lower for k in ["override", "cleared", "physician", "anesthesiologist", "approved"]):
            raise HTTPException(
                status_code=400,
                detail=f"Aldrete post-anesthesia recovery score of {req.aldrete_score}/10 is below the discharge threshold (>= 9). Clinical override documentation is required in observations to transfer patient to Ward."
            )

    recovery_id = uuid.uuid4()
    criteria_json = json.dumps(req.aldrete_criteria) if req.aldrete_criteria else None
    await db.execute(text("""
        INSERT INTO surgery.ot_recovery_records
        (recovery_id, surgery_schedule_id, recovery_status, pain_score, observations, disposition, aldrete_score, aldrete_criteria, recorded_by)
        VALUES (:id, :schedule, :status, :pain, :observations, :disposition, :aldrete, :criteria, :user)
    """), {
        "id": recovery_id,
        "schedule": schedule_id,
        "status": req.recovery_status,
        "pain": req.pain_score,
        "observations": req.observations,
        "disposition": req.disposition,
        "aldrete": req.aldrete_score,
        "criteria": criteria_json,
        "user": user.user_id
    })
    surgery_request = await db.get(SurgeryRequest, schedule.surgery_request_id)
    schedule.schedule_status = "Completed"
    surgery_request.request_status = "Completed"
    await db.commit()
    return {
        "recovery_id": recovery_id,
        "status": "Completed",
        "disposition": req.disposition,
        "aldrete_score": req.aldrete_score
    }
