import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUser, require_roles
from app.config import get_db
from app.schemas.ambulance import AmbulanceUpdate, CancelCreate, DispatchAssign, DispatchCreate, DispatchStatusUpdate, DispatchUpdate, EquipmentCreate, EquipmentUpdate, LocationUpdate, MaintenanceCreate
from app.services.realtime import broker

router = APIRouter(prefix="/ambulance", tags=["Ambulance & Transport"])
dispatch_access = require_roles(["ambulance_staff", "emergency_staff", "admin", "super_admin"])
dispatch_control = require_roles(["ambulance_staff", "emergency_staff", "admin", "super_admin"])
STATUS_ORDER = ["Requested", "Assigned", "En Route", "At Scene", "Patient Onboard", "Arrived", "Completed"]


@router.get("/events")
async def events(_user: CurrentUser = Depends(dispatch_access)):
    return StreamingResponse(broker.stream("ambulance"), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_access)):
    row = (await db.execute(text("""SELECT
      (SELECT count(*) FROM ambulance.ambulances) fleet_total,
      (SELECT count(*) FROM ambulance.ambulances WHERE current_status='Available') fleet_available,
      (SELECT count(*) FROM ambulance.emergency_dispatch_requests WHERE dispatch_status='Requested') awaiting_dispatch,
      (SELECT count(*) FROM ambulance.dispatch_assignments WHERE assignment_status NOT IN ('Completed','Cancelled')) active_responses,
      (SELECT count(*) FROM ambulance.ambulance_maintenance WHERE maintenance_status NOT IN ('Completed','Cancelled')) maintenance_due"""))).mappings().one()
    return dict(row)


@router.get("/fleet")
async def fleet(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_access)):
    rows = await db.execute(text("""SELECT a.ambulance_id,a.vehicle_number,a.registration_number,a.current_status,a.gps_enabled,
      t.type_code,t.type_name,t.emergency_level,l.current_latitude,l.current_longitude,l.last_updated,
      (SELECT count(*) FROM ambulance.ambulance_equipments e WHERE e.ambulance_id=a.ambulance_id AND e.equipment_status<>'Ready') equipment_issues
      FROM ambulance.ambulances a LEFT JOIN ambulance.ambulance_types t USING(ambulance_type_id)
      LEFT JOIN LATERAL (SELECT * FROM ambulance.live_location_tracking x WHERE x.ambulance_id=a.ambulance_id ORDER BY last_updated DESC LIMIT 1) l ON TRUE
      WHERE a.is_active ORDER BY a.vehicle_number"""))
    return [dict(r) for r in rows.mappings()]


@router.get("/priorities")
async def priorities(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_access)):
    rows = await db.execute(text("SELECT * FROM ambulance.dispatch_priorities ORDER BY response_time_target_minutes"))
    return [dict(r) for r in rows.mappings()]


@router.get("/dispatches")
async def dispatches(active_only: bool = True, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_access)):
    rows = await db.execute(text("""SELECT r.emergency_dispatch_request_id,r.patient_id,r.request_source,r.emergency_type,r.pickup_location,
      r.destination_location,r.dispatch_status,r.requested_at,p.mrn,concat_ws(' ',p.first_name,p.last_name) patient_name,
      a.dispatch_assignment_id,a.assignment_status,a.assigned_at,v.ambulance_id,v.vehicle_number,pr.priority_code,pr.priority_name,
      l.current_latitude,l.current_longitude,l.last_updated
      FROM ambulance.emergency_dispatch_requests r JOIN patient.patients p USING(patient_id)
      LEFT JOIN ambulance.dispatch_assignments a ON a.emergency_dispatch_request_id=r.emergency_dispatch_request_id
        AND a.assignment_status NOT IN ('Completed','Cancelled')
      LEFT JOIN ambulance.ambulances v ON v.ambulance_id=a.ambulance_id
      LEFT JOIN ambulance.dispatch_priorities pr ON pr.dispatch_priority_id=a.dispatch_priority_id
      LEFT JOIN LATERAL (SELECT * FROM ambulance.live_location_tracking x WHERE x.ambulance_id=v.ambulance_id ORDER BY last_updated DESC LIMIT 1) l ON TRUE
      WHERE (:active=FALSE OR r.dispatch_status NOT IN ('Completed','Cancelled')) ORDER BY r.requested_at DESC"""), {"active":active_only})
    return [dict(r) for r in rows.mappings()]


@router.post("/dispatches", status_code=201)
async def create_dispatch(req: DispatchCreate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_control)):
    if not await db.scalar(text("SELECT 1 FROM patient.patients WHERE patient_id=:id"), {"id":req.patient_id}): raise HTTPException(404,"Patient not found")
    request_id=uuid.uuid4(); now=datetime.utcnow()
    await db.execute(text("""INSERT INTO ambulance.emergency_dispatch_requests
      (emergency_dispatch_request_id,patient_id,request_source,emergency_type,pickup_location,destination_location,dispatch_status,requested_at)
      VALUES(:id,:patient,:source,:type,:pickup,:destination,'Requested',:now)"""), {"id":request_id,"patient":req.patient_id,"source":req.request_source,"type":req.emergency_type,"pickup":req.pickup_location,"destination":req.destination_location,"now":now})
    await db.commit(); await broker.publish("ambulance","dispatch.created",{"request_id":request_id}); return {"emergency_dispatch_request_id":request_id,"status":"Requested"}


@router.patch("/dispatches/{request_id}")
async def update_dispatch(request_id: uuid.UUID, req: DispatchUpdate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(dispatch_control)):
    status=await db.scalar(text("SELECT dispatch_status FROM ambulance.emergency_dispatch_requests WHERE emergency_dispatch_request_id=:id FOR UPDATE"),{"id":request_id})
    if not status: raise HTTPException(404,"Dispatch request not found")
    if status not in ("Requested","Assigned"): raise HTTPException(409,"Dispatch details cannot be changed after response begins")
    values=req.model_dump(exclude_unset=True)
    if values:
        sets=",".join(f"{key}=:{key}" for key in values)
        await db.execute(text(f"UPDATE ambulance.emergency_dispatch_requests SET {sets},updated_at=:now,updated_by=:user WHERE emergency_dispatch_request_id=:id"),{**values,"now":datetime.utcnow(),"user":user.user_id,"id":request_id})
    await db.commit(); await broker.publish("ambulance","dispatch.updated",{"request_id":request_id}); return {"status":"Updated"}


@router.post("/dispatches/{request_id}/cancel")
async def cancel_dispatch(request_id: uuid.UUID, req: CancelCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(dispatch_control)):
    request=(await db.execute(text("SELECT * FROM ambulance.emergency_dispatch_requests WHERE emergency_dispatch_request_id=:id FOR UPDATE"),{"id":request_id})).mappings().first()
    if not request: raise HTTPException(404,"Dispatch request not found")
    if request["dispatch_status"] in ("Completed","Cancelled"): raise HTTPException(409,"Dispatch request is already closed")
    assignment=(await db.execute(text("SELECT * FROM ambulance.dispatch_assignments WHERE emergency_dispatch_request_id=:id AND assignment_status NOT IN ('Completed','Cancelled') FOR UPDATE"),{"id":request_id})).mappings().first()
    now=datetime.utcnow()
    await db.execute(text("UPDATE ambulance.emergency_dispatch_requests SET dispatch_status='Cancelled',cancellation_reason=:reason,updated_at=:now,updated_by=:user WHERE emergency_dispatch_request_id=:id"),{"reason":req.reason,"now":now,"user":user.user_id,"id":request_id})
    if assignment:
        await db.execute(text("UPDATE ambulance.dispatch_assignments SET assignment_status='Cancelled',completed_at=:now WHERE dispatch_assignment_id=:id"),{"now":now,"id":assignment["dispatch_assignment_id"]})
        await db.execute(text("UPDATE ambulance.ambulances SET current_status='Available' WHERE ambulance_id=:id"),{"id":assignment["ambulance_id"]})
    await db.commit(); await broker.publish("ambulance","dispatch.cancelled",{"request_id":request_id}); return {"status":"Cancelled"}


@router.post("/dispatches/{request_id}/assign", status_code=201)
async def assign_dispatch(request_id: uuid.UUID, req: DispatchAssign, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(dispatch_control)):
    request=(await db.execute(text("SELECT * FROM ambulance.emergency_dispatch_requests WHERE emergency_dispatch_request_id=:id FOR UPDATE"),{"id":request_id})).mappings().first()
    if not request: raise HTTPException(404,"Dispatch request not found")
    if request["dispatch_status"]!="Requested": raise HTTPException(409,"Dispatch request is not awaiting assignment")
    vehicle=(await db.execute(text("SELECT * FROM ambulance.ambulances WHERE ambulance_id=:id FOR UPDATE"),{"id":req.ambulance_id})).mappings().first()
    if not vehicle or vehicle["current_status"]!="Available": raise HTTPException(409,"Ambulance is unavailable")
    assignment=uuid.uuid4(); now=datetime.utcnow()
    await db.execute(text("""INSERT INTO ambulance.dispatch_assignments
      (dispatch_assignment_id,emergency_dispatch_request_id,ambulance_id,dispatch_priority_id,assigned_at,assignment_status,assigned_by)
      VALUES(:id,:request,:vehicle,:priority,:now,'Assigned',:user)"""),{"id":assignment,"request":request_id,"vehicle":req.ambulance_id,"priority":req.dispatch_priority_id,"now":now,"user":user.user_id})
    await db.execute(text("UPDATE ambulance.emergency_dispatch_requests SET dispatch_status='Assigned' WHERE emergency_dispatch_request_id=:id"),{"id":request_id})
    await db.execute(text("UPDATE ambulance.ambulances SET current_status='Dispatched' WHERE ambulance_id=:id"),{"id":req.ambulance_id})
    await db.execute(text("INSERT INTO ambulance.dispatch_tracking(dispatch_assignment_id,tracking_status,tracking_notes,tracked_at) VALUES(:id,'Assigned','Ambulance assigned',:now)"),{"id":assignment,"now":now})
    await db.commit(); await broker.publish("ambulance","dispatch.assigned",{"assignment_id":assignment}); return {"dispatch_assignment_id":assignment,"status":"Assigned"}


async def assignment_row(db: AsyncSession, assignment_id: uuid.UUID, lock=False):
    suffix=" FOR UPDATE" if lock else ""
    row=(await db.execute(text(f"""SELECT a.*,r.patient_id,r.emergency_type,r.pickup_location,r.destination_location,r.dispatch_status
      FROM ambulance.dispatch_assignments a JOIN ambulance.emergency_dispatch_requests r USING(emergency_dispatch_request_id)
      WHERE a.dispatch_assignment_id=:id{suffix}"""),{"id":assignment_id})).mappings().first()
    if not row: raise HTTPException(404,"Dispatch assignment not found")
    return row


@router.post("/assignments/{assignment_id}/status")
async def update_status(assignment_id: uuid.UUID, req: DispatchStatusUpdate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(dispatch_control)):
    row=await assignment_row(db,assignment_id,True); current=row["assignment_status"]
    if current in ("Completed","Cancelled"): raise HTTPException(409,"Dispatch assignment is closed")
    if req.status!="Cancelled":
        expected=STATUS_ORDER[min(STATUS_ORDER.index(current)+1,len(STATUS_ORDER)-1)] if current in STATUS_ORDER else None
        if req.status!=expected: raise HTTPException(409,f"Next valid status is {expected}")
    now=datetime.utcnow()
    completed_at = now if req.status in ("Completed", "Cancelled") else row["completed_at"]
    await db.execute(text("UPDATE ambulance.dispatch_assignments SET assignment_status=:status,completed_at=:completed_at WHERE dispatch_assignment_id=:id"),{"status":req.status,"completed_at":completed_at,"id":assignment_id})
    await db.execute(text("UPDATE ambulance.emergency_dispatch_requests SET dispatch_status=:status WHERE emergency_dispatch_request_id=:id"),{"status":req.status,"id":row["emergency_dispatch_request_id"]})
    await db.execute(text("INSERT INTO ambulance.dispatch_tracking(dispatch_assignment_id,tracking_status,tracking_notes,tracked_at) VALUES(:id,:status,:notes,:now)"),{"id":assignment_id,"status":req.status,"notes":req.notes,"now":now})
    if req.status=="En Route":
        trip=uuid.uuid4(); await db.execute(text("""INSERT INTO ambulance.ambulance_trip_records
          (ambulance_trip_record_id,ambulance_id,dispatch_assignment_id,trip_start_time,trip_status,recorded_by)
          VALUES(:trip,:vehicle,:assignment,:now,'In Progress',:user)"""),{"trip":trip,"vehicle":row["ambulance_id"],"assignment":assignment_id,"now":now,"user":user.user_id})
        await db.execute(text("INSERT INTO ambulance.trip_patients(ambulance_trip_record_id,patient_id,patient_condition) VALUES(:trip,:patient,:condition)"),{"trip":trip,"patient":row["patient_id"],"condition":req.patient_condition})
    if req.status=="Arrived":
        await db.execute(text("""INSERT INTO emergency.emergency_arrivals(patient_id,arrival_mode,arrival_time,brought_by,arrival_condition)
          VALUES(:patient,'Ambulance',:now,:vehicle,:condition)"""),{"patient":row["patient_id"],"now":now,"vehicle":str(row["ambulance_id"]),"condition":req.patient_condition or row["emergency_type"]})
    if req.status in ("Completed","Cancelled"):
        await db.execute(text("UPDATE ambulance.ambulances SET current_status='Available' WHERE ambulance_id=:id"),{"id":row["ambulance_id"]})
        await db.execute(text("UPDATE ambulance.ambulance_trip_records SET trip_end_time=:now,trip_distance_km=:distance,trip_status=:status WHERE dispatch_assignment_id=:id AND trip_end_time IS NULL"),{"now":now,"distance":req.distance_km,"status":req.status,"id":assignment_id})
    await db.commit(); await broker.publish("ambulance","dispatch.status",{"assignment_id":assignment_id,"status":req.status}); return {"dispatch_assignment_id":assignment_id,"status":req.status}


@router.post("/assignments/{assignment_id}/location", status_code=201)
async def update_location(assignment_id: uuid.UUID, req: LocationUpdate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_control)):
    row=await assignment_row(db,assignment_id); now=datetime.utcnow()
    await db.execute(text("INSERT INTO ambulance.gps_tracking_logs(ambulance_id,latitude,longitude,speed,recorded_at) VALUES(:id,:lat,:lng,:speed,:now)"),{"id":row["ambulance_id"],"lat":req.latitude,"lng":req.longitude,"speed":req.speed,"now":now})
    await db.execute(text("DELETE FROM ambulance.live_location_tracking WHERE ambulance_id=:id"),{"id":row["ambulance_id"]})
    await db.execute(text("INSERT INTO ambulance.live_location_tracking(ambulance_id,current_latitude,current_longitude,last_updated) VALUES(:id,:lat,:lng,:now)"),{"id":row["ambulance_id"],"lat":req.latitude,"lng":req.longitude,"now":now})
    await db.commit(); await broker.publish("ambulance","location.updated",{"assignment_id":assignment_id,"latitude":req.latitude,"longitude":req.longitude}); return {"status":"Location updated","recorded_at":now}


@router.patch("/fleet/{ambulance_id}")
async def update_ambulance(ambulance_id: uuid.UUID, req: AmbulanceUpdate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(dispatch_control)):
    values=req.model_dump(exclude_unset=True)
    if not values: return {"status":"Unchanged"}
    sets=",".join(f"{key}=:{key}" for key in values)
    result=await db.execute(text(f"UPDATE ambulance.ambulances SET {sets},updated_at=:now,updated_by=:user WHERE ambulance_id=:id AND is_active"),{**values,"now":datetime.utcnow(),"user":user.user_id,"id":ambulance_id})
    if result.rowcount!=1: raise HTTPException(404,"Active ambulance not found")
    await db.commit(); await broker.publish("ambulance","fleet.updated",{"ambulance_id":ambulance_id}); return {"status":"Updated"}


@router.delete("/fleet/{ambulance_id}")
async def archive_ambulance(ambulance_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(dispatch_control)):
    result=await db.execute(text("UPDATE ambulance.ambulances SET is_active=FALSE,current_status='Out of Service',updated_at=:now,updated_by=:user WHERE ambulance_id=:id AND is_active AND current_status IN ('Available','Out of Service')"),{"now":datetime.utcnow(),"user":user.user_id,"id":ambulance_id})
    if result.rowcount!=1: raise HTTPException(409,"Ambulance is missing, active on a response, or under maintenance")
    await db.commit(); await broker.publish("ambulance","fleet.archived",{"ambulance_id":ambulance_id}); return {"status":"Archived"}


@router.get("/fleet/{ambulance_id}/equipment")
async def equipment(ambulance_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_access)):
    rows=await db.execute(text("SELECT * FROM ambulance.ambulance_equipments WHERE ambulance_id=:id AND is_active ORDER BY equipment_name"),{"id":ambulance_id}); return [dict(r) for r in rows.mappings()]


@router.post("/fleet/{ambulance_id}/equipment", status_code=201)
async def add_equipment(ambulance_id: uuid.UUID, req: EquipmentCreate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_control)):
    if not await db.scalar(text("SELECT 1 FROM ambulance.ambulances WHERE ambulance_id=:id"), {"id": ambulance_id}):
        raise HTTPException(404, "Ambulance not found")
    item=uuid.uuid4(); await db.execute(text("INSERT INTO ambulance.ambulance_equipments(ambulance_equipment_id,ambulance_id,equipment_name,equipment_quantity,equipment_status) VALUES(:id,:vehicle,:equipment_name,:equipment_quantity,:equipment_status)"),{"id":item,"vehicle":ambulance_id,**req.model_dump()}); await db.commit(); return {"ambulance_equipment_id":item}


@router.post("/fleet/{ambulance_id}/maintenance", status_code=201)
async def add_maintenance(ambulance_id: uuid.UUID, req: MaintenanceCreate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(dispatch_control)):
    if not await db.scalar(text("SELECT 1 FROM ambulance.ambulances WHERE ambulance_id=:id"), {"id": ambulance_id}):
        raise HTTPException(404, "Ambulance not found")
    item=uuid.uuid4(); next_date=req.next_maintenance_date
    await db.execute(text("""INSERT INTO ambulance.ambulance_maintenance(ambulance_maintenance_id,ambulance_id,maintenance_type,maintenance_notes,maintenance_date,next_maintenance_date,maintenance_status)
      VALUES(:id,:vehicle,:type,:notes,CURRENT_DATE,:next,'Scheduled')"""),{"id":item,"vehicle":ambulance_id,"type":req.maintenance_type,"notes":req.maintenance_notes,"next":next_date})
    await db.execute(text("UPDATE ambulance.ambulances SET current_status='Maintenance' WHERE ambulance_id=:id AND current_status='Available'"),{"id":ambulance_id}); await db.commit(); return {"ambulance_maintenance_id":item,"status":"Scheduled"}
