import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUser, require_roles
from app.config import get_db
from app.services.realtime import broker
from app.schemas.icu import (
    ICUAdmissionCreate,
    ICUAdmissionUpdate,
    ICUCancellationCreate,
    ICUAlertCreate,
    ICUDispositionCreate,
    ICUDischargeRequestCreate,
    ICUDischargeReview,
    ICURoundCreate,
    ICUTransferCreate,
    ICUVentilatorCreate,
    ICUVitalsCreate,
    ICUVitalsAmend,
    ICUVoidCreate,
)

router = APIRouter(prefix="/icu", tags=["ICU & Critical Care"])
icu_access = require_roles(["icu_viewer", "icu_nurse", "icu_doctor", "icu_coordinator", "admin", "super_admin"])
icu_clinical = require_roles(["icu_nurse", "icu_doctor", "icu_coordinator", "admin", "super_admin"])
icu_doctor = require_roles(["icu_doctor", "icu_coordinator", "admin", "super_admin"])
icu_nursing = require_roles(["icu_nurse", "icu_doctor", "icu_coordinator", "admin", "super_admin"])
icu_authorizer = require_roles(["icu_doctor", "admin", "super_admin"])


@router.get("/events")
async def events(_user: CurrentUser = Depends(icu_access)):
    return StreamingResponse(broker.stream("icu"), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


async def active_admission(db: AsyncSession, admission_id: uuid.UUID, lock: bool = False):
    suffix = " FOR UPDATE" if lock else ""
    row = (await db.execute(text(f"""SELECT a.*,c.patient_id FROM intensive_care_unit.icu_admissions a
        JOIN intensive_care_unit.critical_care_patients c USING(critical_care_patient_id)
        WHERE a.icu_admission_id=:id{suffix}"""), {"id": admission_id})).mappings().first()
    if not row:
        raise HTTPException(404, "ICU admission not found")
    if row["admission_status"] != "Active":
        raise HTTPException(409, "ICU admission is no longer active")
    return row


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    metrics = (await db.execute(text("""SELECT
        (SELECT count(*) FROM intensive_care_unit.icu_beds) total_beds,
        (SELECT count(*) FROM intensive_care_unit.icu_beds WHERE bed_status='Available') available_beds,
        (SELECT count(*) FROM intensive_care_unit.icu_admissions WHERE admission_status='Active') active_patients,
        (SELECT count(*) FROM intensive_care_unit.ventilator_management WHERE ended_at IS NULL) ventilated_patients,
        ((SELECT count(*) FROM intensive_care_unit.critical_lab_alerts WHERE NOT acknowledged) +
         (SELECT count(*) FROM intensive_care_unit.device_alerts WHERE NOT acknowledged)) open_alerts"""))).mappings().one()
    return dict(metrics)


@router.get("/units")
async def units(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    rows = await db.execute(text("""SELECT u.icu_unit_id,u.unit_code,u.unit_name,u.unit_type,u.floor_number,
        count(b.icu_bed_id) total_beds,count(b.icu_bed_id) FILTER(WHERE b.bed_status='Available') available_beds
        FROM intensive_care_unit.icu_units u LEFT JOIN intensive_care_unit.icu_beds b USING(icu_unit_id)
        GROUP BY u.icu_unit_id ORDER BY u.unit_name"""))
    return [dict(r) for r in rows.mappings()]


@router.get("/beds")
async def beds(available_only: bool = False, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    rows = await db.execute(text("""SELECT b.icu_bed_id,b.bed_number,b.bed_type,b.bed_status,
        b.ventilator_supported,b.isolation_supported,u.icu_unit_id,u.unit_name,u.unit_type
        FROM intensive_care_unit.icu_beds b JOIN intensive_care_unit.icu_units u USING(icu_unit_id)
        WHERE (:available=FALSE OR b.bed_status='Available') ORDER BY u.unit_name,b.bed_number"""), {"available": available_only})
    return [dict(r) for r in rows.mappings()]


@router.get("/triage-levels")
async def triage_levels(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    rows = await db.execute(text("SELECT * FROM intensive_care_unit.icu_triage_levels ORDER BY severity_rank"))
    return [dict(r) for r in rows.mappings()]


@router.get("/doctors")
async def doctors(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    rows = await db.execute(text("""SELECT d.doctor_id,d.doctor_code,
        concat_ws(' ',e.first_name,e.middle_name,e.last_name) doctor_name
        FROM doctor.doctors d JOIN human_resources.employees e USING(employee_id)
        ORDER BY e.first_name,e.last_name"""))
    return [dict(r) for r in rows.mappings()]


@router.get("/admissions")
async def admissions(active_only: bool = True, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    rows = await db.execute(text("""SELECT a.icu_admission_id,a.triage_level_id,a.admission_time,a.admission_reason,a.admission_status,
        c.patient_id,c.criticality_level,c.primary_diagnosis,c.admission_source,p.mrn,
        concat_ws(' ',p.first_name,p.last_name) patient_name,b.bed_number,u.unit_name,t.level_name triage_level,
        a.referring_doctor_id,a.attending_doctor_id,
        concat_ws(' ',re.first_name,re.middle_name,re.last_name) referring_doctor_name,
        concat_ws(' ',ae.first_name,ae.middle_name,ae.last_name) attending_doctor_name,
        v.temperature,v.pulse_rate,v.respiratory_rate,v.systolic_bp,v.diastolic_bp,v.oxygen_saturation,v.recorded_at,
        EXISTS(SELECT 1 FROM intensive_care_unit.ventilator_management vm WHERE vm.icu_admission_id=a.icu_admission_id AND vm.ended_at IS NULL) ventilated,
        EXISTS(SELECT 1 FROM intensive_care_unit.icu_discharge_requests dr WHERE dr.icu_admission_id=a.icu_admission_id AND dr.request_status='Pending') discharge_requested
        FROM intensive_care_unit.icu_admissions a
        JOIN intensive_care_unit.critical_care_patients c USING(critical_care_patient_id)
        JOIN patient.patients p USING(patient_id)
        JOIN intensive_care_unit.icu_beds b USING(icu_bed_id)
        JOIN intensive_care_unit.icu_units u USING(icu_unit_id)
        LEFT JOIN intensive_care_unit.icu_triage_levels t USING(triage_level_id)
        LEFT JOIN doctor.doctors rd ON rd.doctor_id=a.referring_doctor_id
        LEFT JOIN human_resources.employees re ON re.employee_id=rd.employee_id
        LEFT JOIN doctor.doctors ad ON ad.doctor_id=a.attending_doctor_id
        LEFT JOIN human_resources.employees ae ON ae.employee_id=ad.employee_id
        LEFT JOIN LATERAL (SELECT * FROM intensive_care_unit.icu_vital_signs x
            WHERE x.icu_admission_id=a.icu_admission_id ORDER BY recorded_at DESC LIMIT 1) v ON TRUE
        WHERE (:active=FALSE OR a.admission_status='Active') ORDER BY a.admission_time DESC"""), {"active": active_only})
    return [dict(r) for r in rows.mappings()]


@router.post("/admissions", status_code=201)
async def admit(req: ICUAdmissionCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_doctor)):
    if not await db.scalar(text("SELECT 1 FROM patient.patients WHERE patient_id=:id"), {"id": req.patient_id}):
        raise HTTPException(404, "Patient not found")
    bed = (await db.execute(text("SELECT * FROM intensive_care_unit.icu_beds WHERE icu_bed_id=:id FOR UPDATE"), {"id": req.icu_bed_id})).mappings().first()
    if not bed or bed["bed_status"] != "Available":
        raise HTTPException(409, "ICU bed is unavailable")
    existing = await db.scalar(text("""SELECT 1 FROM intensive_care_unit.icu_admissions a
        JOIN intensive_care_unit.critical_care_patients c USING(critical_care_patient_id)
        WHERE c.patient_id=:patient AND a.admission_status='Active'"""), {"patient": req.patient_id})
    if existing:
        raise HTTPException(409, "Patient already has an active ICU admission")
    for doctor_id in (req.referring_doctor_id, req.attending_doctor_id):
        if doctor_id and not await db.scalar(text("SELECT 1 FROM doctor.doctors WHERE doctor_id=:id"), {"id": doctor_id}):
            raise HTTPException(404, "Selected doctor not found")
    patient_link = uuid.uuid4(); admission_id = uuid.uuid4(); now = datetime.utcnow()
    await db.execute(text("""INSERT INTO intensive_care_unit.critical_care_patients
        (critical_care_patient_id,patient_id,criticality_level,primary_diagnosis,admission_source)
        VALUES(:id,:patient,:level,:diagnosis,:source)"""), {"id": patient_link,"patient": req.patient_id,"level": req.criticality_level,"diagnosis": req.primary_diagnosis,"source": req.admission_source})
    await db.execute(text("""INSERT INTO intensive_care_unit.icu_admissions
        (icu_admission_id,critical_care_patient_id,icu_bed_id,triage_level_id,admitted_by,admission_time,admission_reason,admission_status,referring_doctor_id,attending_doctor_id)
        VALUES(:id,:link,:bed,:triage,:user,:now,:reason,'Active',:referring,:attending)"""), {"id": admission_id,"link": patient_link,"bed": req.icu_bed_id,"triage": req.triage_level_id,"user": user.user_id,"now": now,"reason": req.admission_reason,"referring":req.referring_doctor_id,"attending":req.attending_doctor_id})
    await db.execute(text("""INSERT INTO intensive_care_unit.icu_bed_assignments
        (icu_admission_id,icu_bed_id,assigned_from,assignment_status) VALUES(:admission,:bed,:now,'Active')"""), {"admission": admission_id,"bed": req.icu_bed_id,"now": now})
    await db.execute(text("UPDATE intensive_care_unit.icu_beds SET bed_status='Occupied' WHERE icu_bed_id=:id"), {"id": req.icu_bed_id})
    await db.commit(); await broker.publish("icu","admission.created",{"admission_id":admission_id})
    return {"icu_admission_id": admission_id, "status": "Active"}


@router.patch("/admissions/{admission_id}")
async def update_admission(admission_id: uuid.UUID, req: ICUAdmissionUpdate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_doctor)):
    admission = await active_admission(db, admission_id, True)
    values = req.model_dump(exclude_unset=True)
    for key in ("referring_doctor_id", "attending_doctor_id"):
        if values.get(key) and not await db.scalar(text("SELECT 1 FROM doctor.doctors WHERE doctor_id=:id"), {"id": values[key]}):
            raise HTTPException(404, "Selected doctor not found")
    critical_updates = {k: values.pop(k) for k in ("criticality_level", "primary_diagnosis") if k in values}
    if critical_updates:
        sets = ",".join(f"{key}=:{key}" for key in critical_updates)
        await db.execute(text(f"UPDATE intensive_care_unit.critical_care_patients SET {sets} WHERE critical_care_patient_id=:link"), {**critical_updates, "link": admission["critical_care_patient_id"]})
    if values:
        sets = ",".join(f"{key}=:{key}" for key in values)
        await db.execute(text(f"UPDATE intensive_care_unit.icu_admissions SET {sets},updated_at=:now,updated_by=:user WHERE icu_admission_id=:id"), {**values,"now":datetime.utcnow(),"user":user.user_id,"id":admission_id})
    await db.commit(); await broker.publish("icu","admission.updated",{"admission_id":admission_id}); return {"status":"Updated"}


@router.post("/admissions/{admission_id}/cancel")
async def cancel_admission(admission_id: uuid.UUID, req: ICUCancellationCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_doctor)):
    admission=await active_admission(db,admission_id,True); now=datetime.utcnow()
    await db.execute(text("UPDATE intensive_care_unit.icu_admissions SET admission_status='Cancelled',cancellation_reason=:reason,updated_at=:now,updated_by=:user WHERE icu_admission_id=:id"),{"reason":req.reason,"now":now,"user":user.user_id,"id":admission_id})
    await db.execute(text("UPDATE intensive_care_unit.icu_bed_assignments SET assigned_to=:now,assignment_status='Cancelled' WHERE icu_admission_id=:id AND assignment_status='Active'"),{"now":now,"id":admission_id})
    await db.execute(text("UPDATE intensive_care_unit.icu_beds SET bed_status='Available' WHERE icu_bed_id=:id"),{"id":admission["icu_bed_id"]})
    await db.commit(); await broker.publish("icu","admission.cancelled",{"admission_id":admission_id}); return {"status":"Cancelled"}


@router.get("/admissions/{admission_id}")
async def admission_detail(admission_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    admission = await active_admission(db, admission_id)
    vitals = await db.execute(text("SELECT * FROM intensive_care_unit.icu_vital_signs WHERE icu_admission_id=:id AND voided_at IS NULL ORDER BY recorded_at DESC LIMIT 50"), {"id": admission_id})
    rounds = await db.execute(text("SELECT * FROM intensive_care_unit.icu_rounds WHERE icu_admission_id=:id ORDER BY rounded_at DESC LIMIT 50"), {"id": admission_id})
    alerts = await db.execute(text("""SELECT critical_lab_alert_id alert_id,'clinical' source,alert_type,alert_message,alert_time,acknowledged FROM intensive_care_unit.critical_lab_alerts WHERE icu_admission_id=:id
        UNION ALL SELECT device_alert_id,'device',alert_type,alert_message,alert_time,acknowledged FROM intensive_care_unit.device_alerts WHERE icu_admission_id=:id ORDER BY alert_time DESC"""), {"id": admission_id})
    return {"admission": dict(admission), "vitals": [dict(r) for r in vitals.mappings()], "rounds": [dict(r) for r in rounds.mappings()], "alerts": [dict(r) for r in alerts.mappings()]}


@router.post("/admissions/{admission_id}/vitals", status_code=201)
async def record_vitals(admission_id: uuid.UUID, req: ICUVitalsCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_clinical)):
    await active_admission(db, admission_id)
    values = req.model_dump(); values.update({"id": uuid.uuid4(), "admission": admission_id, "user": user.user_id, "now": datetime.utcnow()})
    await db.execute(text("""INSERT INTO intensive_care_unit.icu_vital_signs
        (icu_vital_sign_id,icu_admission_id,temperature,pulse_rate,respiratory_rate,systolic_bp,diastolic_bp,oxygen_saturation,recorded_at,recorded_by)
        VALUES(:id,:admission,:temperature,:pulse_rate,:respiratory_rate,:systolic_bp,:diastolic_bp,:oxygen_saturation,:now,:user)"""), values)
    critical = (values["oxygen_saturation"] is not None and values["oxygen_saturation"] < 90) or (values["systolic_bp"] is not None and values["systolic_bp"] < 80)
    if critical:
        await db.execute(text("""INSERT INTO intensive_care_unit.critical_lab_alerts
            (icu_admission_id,alert_type,alert_message,alert_time,acknowledged)
            VALUES(:id,'Critical vital signs','Critical oxygen saturation or systolic blood pressure recorded',:now,FALSE)"""), {"id": admission_id,"now": values["now"]})
    await db.commit(); await broker.publish("icu","vitals.created",{"admission_id":admission_id,"vital_id":values["id"]})
    return {"icu_vital_sign_id": values["id"], "critical_alert_created": critical}


@router.patch("/vitals/{vital_id}")
async def amend_vitals(vital_id: uuid.UUID, req: ICUVitalsAmend, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_clinical)):
    vital = (await db.execute(text("SELECT 1 FROM intensive_care_unit.icu_vital_signs WHERE icu_vital_sign_id=:id AND voided_at IS NULL FOR UPDATE"), {"id": vital_id})).first()
    if not vital: raise HTTPException(404,"Active vital-sign record not found")
    values=req.model_dump(exclude_unset=True); reason=values.pop("amendment_reason")
    if not values: raise HTTPException(422,"At least one measurement is required")
    sets=",".join(f"{key}=:{key}" for key in values)
    await db.execute(text(f"UPDATE intensive_care_unit.icu_vital_signs SET {sets},amended_at=:now,amended_by=:user,amendment_reason=:reason WHERE icu_vital_sign_id=:id"),{**values,"now":datetime.utcnow(),"user":user.user_id,"reason":reason,"id":vital_id})
    await db.commit(); await broker.publish("icu","vitals.amended",{"vital_id":vital_id}); return {"status":"Amended"}


@router.post("/vitals/{vital_id}/void")
async def void_vitals(vital_id: uuid.UUID, req: ICUVoidCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_doctor)):
    result=await db.execute(text("UPDATE intensive_care_unit.icu_vital_signs SET voided_at=:now,voided_by=:user,void_reason=:reason WHERE icu_vital_sign_id=:id AND voided_at IS NULL"),{"now":datetime.utcnow(),"user":user.user_id,"reason":req.reason,"id":vital_id})
    if result.rowcount!=1: raise HTTPException(404,"Active vital-sign record not found")
    await db.commit(); await broker.publish("icu","vitals.voided",{"vital_id":vital_id}); return {"status":"Voided"}


@router.post("/admissions/{admission_id}/rounds", status_code=201)
async def record_round(admission_id: uuid.UUID, req: ICURoundCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_clinical)):
    await active_admission(db, admission_id)
    round_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO intensive_care_unit.icu_rounds
        (icu_round_id,icu_admission_id,rounded_by,round_notes,rounded_at) VALUES(:id,:admission,:user,:notes,:now)"""), {"id": round_id,"admission": admission_id,"user": user.user_id,"notes": req.round_notes,"now": datetime.utcnow()})
    await db.commit(); return {"icu_round_id": round_id}


@router.post("/admissions/{admission_id}/ventilator", status_code=201)
async def start_ventilator(admission_id: uuid.UUID, req: ICUVentilatorCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_doctor)):
    await active_admission(db, admission_id)
    if await db.scalar(text("SELECT 1 FROM intensive_care_unit.ventilator_management WHERE icu_admission_id=:id AND ended_at IS NULL"), {"id": admission_id}):
        raise HTTPException(409, "Active ventilator support already exists")
    support_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO intensive_care_unit.ventilator_management
        (ventilator_management_id,icu_admission_id,ventilator_device_id,ventilation_mode,started_at,managed_by)
        VALUES(:id,:admission,:device,:mode,:now,:user)"""), {"id": support_id,"admission": admission_id,"device": req.ventilator_device_id,"mode": req.ventilation_mode,"now": datetime.utcnow(),"user": user.user_id})
    await db.commit(); return {"ventilator_management_id": support_id, "status": "Active"}


@router.post("/admissions/{admission_id}/alerts", status_code=201)
async def create_alert(admission_id: uuid.UUID, req: ICUAlertCreate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_clinical)):
    await active_admission(db, admission_id); alert_id = uuid.uuid4(); now = datetime.utcnow()
    if req.source == "device":
        await db.execute(text("""INSERT INTO intensive_care_unit.device_alerts
            (device_alert_id,icu_admission_id,device_identifier,alert_type,alert_message,alert_time,acknowledged)
            VALUES(:id,:admission,:device,:type,:message,:now,FALSE)"""), {"id":alert_id,"admission":admission_id,"device":req.device_identifier,"type":req.alert_type,"message":req.alert_message,"now":now})
    else:
        await db.execute(text("""INSERT INTO intensive_care_unit.critical_lab_alerts
            (critical_lab_alert_id,icu_admission_id,alert_type,alert_message,alert_time,acknowledged)
            VALUES(:id,:admission,:type,:message,:now,FALSE)"""), {"id":alert_id,"admission":admission_id,"type":req.alert_type,"message":req.alert_message,"now":now})
    await db.commit(); return {"alert_id": alert_id, "source": req.source}


@router.post("/alerts/{source}/{alert_id}/acknowledge")
async def acknowledge_alert(source: str, alert_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_clinical)):
    table, key = ("device_alerts", "device_alert_id") if source == "device" else ("critical_lab_alerts", "critical_lab_alert_id")
    result = await db.execute(text(f"UPDATE intensive_care_unit.{table} SET acknowledged=TRUE,acknowledged_by=:user,acknowledged_at=:now WHERE {key}=:id AND NOT acknowledged"), {"user":user.user_id,"now":datetime.utcnow(),"id":alert_id})
    if result.rowcount != 1: raise HTTPException(404, "Open alert not found")
    await db.commit(); return {"status": "Acknowledged"}


@router.post("/admissions/{admission_id}/transfer")
async def transfer(admission_id: uuid.UUID, req: ICUTransferCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_doctor)):
    admission = await active_admission(db, admission_id, True)
    bed = (await db.execute(text("SELECT * FROM intensive_care_unit.icu_beds WHERE icu_bed_id=:id FOR UPDATE"), {"id":req.to_bed_id})).mappings().first()
    if not bed or bed["icu_unit_id"] != req.to_unit_id or bed["bed_status"] != "Available": raise HTTPException(409,"Destination ICU bed is unavailable")
    from_unit = await db.scalar(text("SELECT icu_unit_id FROM intensive_care_unit.icu_beds WHERE icu_bed_id=:id"), {"id":admission["icu_bed_id"]}); now=datetime.utcnow()
    await db.execute(text("INSERT INTO intensive_care_unit.icu_transfers(icu_admission_id,from_unit_id,to_unit_id,transfer_reason,transferred_at) VALUES(:id,:from,:to,:reason,:now)"), {"id":admission_id,"from":from_unit,"to":req.to_unit_id,"reason":req.transfer_reason,"now":now})
    await db.execute(text("UPDATE intensive_care_unit.icu_bed_assignments SET assigned_to=:now,assignment_status='Transferred' WHERE icu_admission_id=:id AND assignment_status='Active'"), {"now":now,"id":admission_id})
    await db.execute(text("INSERT INTO intensive_care_unit.icu_bed_assignments(icu_admission_id,icu_bed_id,assigned_from,assignment_status) VALUES(:id,:bed,:now,'Active')"), {"id":admission_id,"bed":req.to_bed_id,"now":now})
    await db.execute(text("UPDATE intensive_care_unit.icu_beds SET bed_status='Available' WHERE icu_bed_id=:id"), {"id":admission["icu_bed_id"]})
    await db.execute(text("UPDATE intensive_care_unit.icu_beds SET bed_status='Occupied' WHERE icu_bed_id=:id"), {"id":req.to_bed_id})
    await db.execute(text("UPDATE intensive_care_unit.icu_admissions SET icu_bed_id=:bed WHERE icu_admission_id=:id"), {"bed":req.to_bed_id,"id":admission_id})
    await db.commit(); return {"status":"Transferred","icu_bed_id":req.to_bed_id,"transferred_by":user.user_id}


@router.post("/admissions/{admission_id}/discharge")
async def discharge(admission_id: uuid.UUID, req: ICUDispositionCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_authorizer)):
    await finalize_discharge(db, admission_id, req.discharge_condition, req.discharge_summary)
    await db.commit(); await broker.publish("icu","admission.discharged",{"admission_id":admission_id})
    return {"status":"Discharged","discharged_by":user.user_id}


async def finalize_discharge(db: AsyncSession, admission_id: uuid.UUID, condition: str, summary: str):
    admission = await active_admission(db, admission_id, True); now=datetime.utcnow()
    open_alerts = await db.scalar(text("""SELECT (SELECT count(*) FROM intensive_care_unit.critical_lab_alerts WHERE icu_admission_id=:id AND NOT acknowledged)+
        (SELECT count(*) FROM intensive_care_unit.device_alerts WHERE icu_admission_id=:id AND NOT acknowledged)"""), {"id":admission_id})
    if open_alerts: raise HTTPException(409,"Acknowledge all ICU alerts before discharge")
    await db.execute(text("INSERT INTO intensive_care_unit.icu_discharges(icu_admission_id,discharge_time,discharge_condition,discharge_summary) VALUES(:id,:now,:condition,:summary)"), {"id":admission_id,"now":now,"condition":condition,"summary":summary})
    await db.execute(text("UPDATE intensive_care_unit.icu_admissions SET admission_status='Discharged' WHERE icu_admission_id=:id"), {"id":admission_id})
    await db.execute(text("UPDATE intensive_care_unit.icu_bed_assignments SET assigned_to=:now,assignment_status='Completed' WHERE icu_admission_id=:id AND assignment_status='Active'"), {"now":now,"id":admission_id})
    await db.execute(text("UPDATE intensive_care_unit.icu_beds SET bed_status='Available' WHERE icu_bed_id=:id"), {"id":admission["icu_bed_id"]})
    await db.execute(text("UPDATE intensive_care_unit.ventilator_management SET ended_at=:now WHERE icu_admission_id=:id AND ended_at IS NULL"), {"now":now,"id":admission_id})


@router.post("/admissions/{admission_id}/discharge-request", status_code=201)
async def request_discharge(admission_id: uuid.UUID, req: ICUDischargeRequestCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_nursing)):
    await active_admission(db,admission_id)
    if await db.scalar(text("SELECT 1 FROM intensive_care_unit.icu_discharge_requests WHERE icu_admission_id=:id AND request_status='Pending'"),{"id":admission_id}):
        raise HTTPException(409,"A discharge request is already pending")
    request_id=uuid.uuid4()
    await db.execute(text("""INSERT INTO intensive_care_unit.icu_discharge_requests
      (icu_discharge_request_id,icu_admission_id,requested_by,proposed_condition,proposed_summary,request_notes)
      VALUES(:request,:admission,:user,:condition,:summary,:notes)"""),{"request":request_id,"admission":admission_id,"user":user.user_id,"condition":req.proposed_condition,"summary":req.proposed_summary,"notes":req.request_notes})
    await db.commit(); await broker.publish("icu","discharge.requested",{"admission_id":admission_id,"request_id":request_id})
    return {"icu_discharge_request_id":request_id,"status":"Pending doctor approval"}


@router.get("/discharge-requests")
async def discharge_requests(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(icu_access)):
    rows=await db.execute(text("""SELECT r.*,p.mrn,concat_ws(' ',p.first_name,p.last_name) patient_name
      FROM intensive_care_unit.icu_discharge_requests r
      JOIN intensive_care_unit.icu_admissions a USING(icu_admission_id)
      JOIN intensive_care_unit.critical_care_patients c USING(critical_care_patient_id)
      JOIN patient.patients p USING(patient_id) WHERE r.request_status='Pending' ORDER BY r.requested_at"""))
    return [dict(row) for row in rows.mappings()]


@router.post("/discharge-requests/{request_id}/review")
async def review_discharge(request_id: uuid.UUID, req: ICUDischargeReview, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(icu_authorizer)):
    request=(await db.execute(text("SELECT * FROM intensive_care_unit.icu_discharge_requests WHERE icu_discharge_request_id=:id AND request_status='Pending' FOR UPDATE"),{"id":request_id})).mappings().first()
    if not request: raise HTTPException(404,"Pending discharge request not found")
    status="Approved" if req.approved else "Rejected"; now=datetime.utcnow()
    if req.approved:
        await finalize_discharge(db,request["icu_admission_id"],request["proposed_condition"],request["proposed_summary"])
    await db.execute(text("UPDATE intensive_care_unit.icu_discharge_requests SET request_status=:status,reviewed_by=:user,reviewed_at=:now,review_notes=:notes WHERE icu_discharge_request_id=:id"),{"status":status,"user":user.user_id,"now":now,"notes":req.review_notes,"id":request_id})
    await db.commit(); await broker.publish("icu","discharge.reviewed",{"admission_id":request["icu_admission_id"],"status":status})
    return {"status":status}
