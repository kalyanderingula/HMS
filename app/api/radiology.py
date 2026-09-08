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
from app.models.radiology_models import (
    ImagingModality, ImagingRoom, RadiologyTest,
    RadiologyOrderStatus, RadiologyPriority,
    RadiologyOrder, RadiologyOrderItem,
    RadiologyAppointment, ImagingStudy, Radiologist, RadiologyReport
)
from app.schemas.radiology import (
    ModalityResponse, ImagingRoomResponse,
    RadiologyTestCreateRequest, RadiologyTestResponse,
    RadiologyOrderCreateRequest, RadiologyOrderResponse, RadiologyOrderItemResponse,
    RadiologyScheduleRequest, RadiologyAppointmentResponse,
    ImagingStudyCreateRequest, ImagingStudyResponse,
    RadiologyReportCreateRequest, RadiologyReportResponse
)

router = APIRouter(prefix="/radiology", tags=["Radiology Information System (RIS/PACS)"])

async def ensure_radiology_masters(db: AsyncSession):
    modalities = [
        ("XRAY", "Digital Radiography (X-Ray)", "Standard skeletal and chest plain radiographs"),
        ("CT", "Computed Tomography (CT Scan)", "High-resolution multi-slice CT scanning"),
        ("MRI", "Magnetic Resonance Imaging (MRI)", "Soft tissue and neuro-imaging magnetic resonance"),
        ("USG", "Ultrasonography (Ultrasound)", "Diagnostic ultrasound and Doppler flow studies")
    ]
    for code, name, desc in modalities:
        res = await db.execute(select(ImagingModality).where(ImagingModality.modality_code == code))
        if not res.scalars().first():
            db.add(ImagingModality(modality_code=code, modality_name=name, description=desc))
    
    await db.flush()
    xray_m = (await db.execute(select(ImagingModality).where(ImagingModality.modality_code == "XRAY"))).scalars().first()
    if xray_m:
        r_res = await db.execute(select(ImagingRoom).where(ImagingRoom.room_code == "RAD-ROOM-1"))
        if not r_res.scalars().first():
            db.add(ImagingRoom(room_code="RAD-ROOM-1", room_name="General X-Ray Suite A", modality_id=xray_m.modality_id, room_location="Ground Floor - Imaging Wing"))

    for st in ["Ordered", "Scheduled", "In Progress", "Completed", "Cancelled"]:
        res = await db.execute(select(RadiologyOrderStatus).where(RadiologyOrderStatus.status_name == st))
        if not res.scalars().first():
            db.add(RadiologyOrderStatus(status_name=st))
            
    for p, rank in [("Routine", 1), ("Urgent", 2), ("STAT", 3)]:
        res = await db.execute(select(RadiologyPriority).where(RadiologyPriority.priority_name == p))
        if not res.scalars().first():
            db.add(RadiologyPriority(priority_name=p, priority_level=rank))

    await db.commit()

# ----------------- Modalities & Rooms -----------------
@router.get("/modalities", response_model=List[ModalityResponse])
async def list_modalities(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    await ensure_radiology_masters(db)
    res = await db.execute(select(ImagingModality).order_by(ImagingModality.modality_code))
    return [
        ModalityResponse(
            modality_id=m.modality_id, modality_code=m.modality_code,
            modality_name=m.modality_name, description=m.description
        ) for m in res.scalars().all()
    ]

@router.get("/rooms", response_model=List[ImagingRoomResponse])
async def list_imaging_rooms(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    await ensure_radiology_masters(db)
    res = await db.execute(select(ImagingRoom))
    rooms = res.scalars().all()
    results = []
    for r in rooms:
        m_res = await db.execute(select(ImagingModality).where(ImagingModality.modality_id == r.modality_id))
        mod = m_res.scalars().first()
        results.append(ImagingRoomResponse(
            imaging_room_id=r.imaging_room_id, room_code=r.room_code, room_name=r.room_name,
            modality_code=mod.modality_code if mod else "RAD",
            room_location=r.room_location, room_status=r.room_status or "Available"
        ))
    return results

# ----------------- Radiology Tests -----------------
@router.get("/tests", response_model=List[RadiologyTestResponse])
async def list_radiology_tests(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    query = select(RadiologyTest).where(RadiologyTest.is_active == True)
    if q:
        query = query.where(RadiologyTest.test_name.ilike(f"%{q}%") | RadiologyTest.test_code.ilike(f"%{q}%"))
    res = await db.execute(query.order_by(RadiologyTest.test_name).limit(50))
    return [
        RadiologyTestResponse(
            radiology_test_id=t.radiology_test_id, test_code=t.test_code,
            test_name=t.test_name, modality_id=t.modality_id, price=float(t.price or 0),
            is_active=t.is_active or True
        ) for t in res.scalars().all()
    ]

@router.post("/tests", response_model=RadiologyTestResponse, status_code=201)
async def create_radiology_test(
    req: RadiologyTestCreateRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "admin", "super_admin"]))
):
    await ensure_radiology_masters(db)
    m_res = await db.execute(select(ImagingModality).where(ImagingModality.modality_code == req.modality_code))
    mod = m_res.scalars().first()
    if not mod: raise HTTPException(404, f"Modality {req.modality_code} not found")

    existing = await db.execute(select(RadiologyTest).where(RadiologyTest.test_code == req.test_code))
    if existing.scalars().first():
        raise HTTPException(400, "Test code already exists")

    t = RadiologyTest(
        test_code=req.test_code, test_name=req.test_name, modality_id=mod.modality_id,
        price=req.price, is_active=True
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)

    return RadiologyTestResponse(
        radiology_test_id=t.radiology_test_id, test_code=t.test_code,
        test_name=t.test_name, modality_id=t.modality_id, price=float(t.price),
        is_active=t.is_active
    )

# ----------------- Orders -----------------
@router.post("/orders", response_model=RadiologyOrderResponse, status_code=201)
async def create_radiology_order(
    req: RadiologyOrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "admin", "super_admin"]))
):
    await ensure_radiology_masters(db)
    p_res = await db.execute(select(Patient).where(Patient.patient_id == req.patient_id))
    patient = p_res.scalars().first()
    if not patient: raise HTTPException(404, "Patient not found")

    st_res = await db.execute(select(RadiologyOrderStatus).where(RadiologyOrderStatus.status_name == "Ordered"))
    st = st_res.scalars().first()

    pr_res = await db.execute(select(RadiologyPriority).where(RadiologyPriority.priority_name == req.priority))
    pr = pr_res.scalars().first()

    seq_res = await db.execute(select(func.count(RadiologyOrder.radiology_order_id)))
    seq = (seq_res.scalar() or 0) + 1
    order_num = f"RAD-{datetime.utcnow().year}-{seq:05d}"

    order = RadiologyOrder(
        order_number=order_num, patient_id=patient.patient_id, encounter_id=req.encounter_id,
        doctor_id=req.doctor_id, radiology_order_status_id=st.radiology_order_status_id if st else None,
        priority_id=pr.priority_id if pr else None, clinical_indication=req.clinical_indication,
        created_by=cu.user_id, ordered_at=datetime.utcnow()
    )
    db.add(order)
    await db.flush()

    item_responses = []
    for it in req.items:
        t_res = await db.execute(select(RadiologyTest).where(RadiologyTest.radiology_test_id == it.radiology_test_id))
        test = t_res.scalars().first()
        if not test: continue

        order_item = RadiologyOrderItem(
            radiology_order_id=order.radiology_order_id,
            radiology_test_id=test.radiology_test_id, order_status="Ordered"
        )
        db.add(order_item)
        await db.flush()

        item_responses.append(RadiologyOrderItemResponse(
            order_item_id=order_item.order_item_id, radiology_test_id=test.radiology_test_id,
            test_code=test.test_code, test_name=test.test_name, order_status="Ordered"
        ))

    await db.commit()
    await db.refresh(order)

    doc_name = "Ordering Physician"
    if req.doctor_id:
        d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == req.doctor_id))
        doc = d_res.scalars().first()
        if doc: doc_name = f"Dr. {doc.first_name} {doc.last_name}"

    return RadiologyOrderResponse(
        radiology_order_id=order.radiology_order_id, order_number=order.order_number,
        patient_id=patient.patient_id, patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn, doctor_name=doc_name, priority=req.priority, status="Ordered",
        clinical_indication=order.clinical_indication or "", ordered_at=order.ordered_at,
        items=item_responses
    )

# ----------------- Scheduling & Studies -----------------
@router.post("/schedule", response_model=RadiologyAppointmentResponse, status_code=201)
async def schedule_radiology_exam(
    req: RadiologyScheduleRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "receptionist", "admin", "super_admin"]))
):
    it_res = await db.execute(select(RadiologyOrderItem).where(RadiologyOrderItem.order_item_id == req.order_item_id))
    item = it_res.scalars().first()
    if not item: raise HTTPException(404, "Radiology order item not found")

    room_res = await db.execute(select(ImagingRoom).where(ImagingRoom.imaging_room_id == req.imaging_room_id))
    room = room_res.scalars().first()
    if not room: raise HTTPException(404, "Imaging room not found")

    appt = RadiologyAppointment(
        order_item_id=item.order_item_id, imaging_room_id=room.imaging_room_id,
        scheduled_start=req.scheduled_start, scheduled_end=req.scheduled_end,
        appointment_status="Scheduled"
    )
    db.add(appt)
    item.order_status = "Scheduled"

    ord_res = await db.execute(select(RadiologyOrder).where(RadiologyOrder.radiology_order_id == item.radiology_order_id))
    order = ord_res.scalars().first()
    if order:
        st_res = await db.execute(select(RadiologyOrderStatus).where(RadiologyOrderStatus.status_name == "Scheduled"))
        st_obj = st_res.scalars().first()
        if st_obj: order.radiology_order_status_id = st_obj.radiology_order_status_id

    await db.commit()
    await db.refresh(appt)

    return RadiologyAppointmentResponse(
        radiology_appointment_id=appt.radiology_appointment_id,
        order_item_id=item.order_item_id, imaging_room_id=room.imaging_room_id,
        room_name=room.room_name, scheduled_start=appt.scheduled_start,
        scheduled_end=appt.scheduled_end, appointment_status=appt.appointment_status
    )

@router.post("/studies", response_model=ImagingStudyResponse, status_code=201)
async def record_imaging_study(
    req: ImagingStudyCreateRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "admin", "super_admin"]))
):
    apt_res = await db.execute(select(RadiologyAppointment).where(RadiologyAppointment.radiology_appointment_id == req.radiology_appointment_id))
    appt = apt_res.scalars().first()
    if not appt: raise HTTPException(404, "Radiology appointment not found")

    it_res = await db.execute(select(RadiologyOrderItem).where(RadiologyOrderItem.order_item_id == appt.order_item_id))
    item = it_res.scalars().first()
    ord_res = await db.execute(select(RadiologyOrder).where(RadiologyOrder.radiology_order_id == item.radiology_order_id))
    order = ord_res.scalars().first()

    p_res = await db.execute(select(Patient).where(Patient.patient_id == order.patient_id))
    patient = p_res.scalars().first()

    study_uid = f"1.2.840.10008.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{str(uuid.uuid4())[:6]}"
    accession = f"ACC-{datetime.utcnow().year}-{str(uuid.uuid4())[:6].upper()}"

    study = ImagingStudy(
        study_instance_uid=study_uid, radiology_appointment_id=appt.radiology_appointment_id,
        patient_id=patient.patient_id, study_description=req.study_description,
        study_date=datetime.utcnow(), accession_number=accession
    )
    db.add(study)
    item.order_status = "In Progress"
    appt.appointment_status = "Completed"

    await db.commit()
    await db.refresh(study)

    return ImagingStudyResponse(
        study_id=study.study_id, study_instance_uid=study.study_instance_uid,
        accession_number=study.accession_number, patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        mrn=patient.mrn, study_description=study.study_description or "",
        study_date=study.study_date
    )

# ----------------- Reporting -----------------
@router.post("/reports", response_model=RadiologyReportResponse, status_code=201)
async def submit_radiology_report(
    req: RadiologyReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "admin", "super_admin"]))
):
    s_res = await db.execute(select(ImagingStudy).where(ImagingStudy.study_id == req.study_id))
    study = s_res.scalars().first()
    if not study: raise HTTPException(404, "Imaging study not found")

    rad_row = (await db.execute(select(Radiologist).limit(1))).scalars().first()
    if not rad_row:
        rad_row = Radiologist(specialization="General Diagnostic Radiology")
        db.add(rad_row)
        await db.flush()

    report = RadiologyReport(
        study_id=study.study_id, radiologist_id=rad_row.radiologist_id,
        report_text=req.findings, impression=req.impression,
        report_status="Final", reported_at=datetime.utcnow(), approved_at=datetime.utcnow()
    )
    db.add(report)

    if study.radiology_appointment_id:
        apt_res = await db.execute(select(RadiologyAppointment).where(RadiologyAppointment.radiology_appointment_id == study.radiology_appointment_id))
        appt = apt_res.scalars().first()
        if appt:
            it_res = await db.execute(select(RadiologyOrderItem).where(RadiologyOrderItem.order_item_id == appt.order_item_id))
            item = it_res.scalars().first()
            if item:
                item.order_status = "Completed"
                ord_res = await db.execute(select(RadiologyOrder).where(RadiologyOrder.radiology_order_id == item.radiology_order_id))
                order = ord_res.scalars().first()
                if order:
                    st_res = await db.execute(select(RadiologyOrderStatus).where(RadiologyOrderStatus.status_name == "Completed"))
                    st_obj = st_res.scalars().first()
                    if st_obj: order.radiology_order_status_id = st_obj.radiology_order_status_id

    await db.commit()
    await db.refresh(report)

    return RadiologyReportResponse(
        report_id=report.report_id, study_id=study.study_id,
        study_description=study.study_description or "Radiology Exam",
        radiologist_name=cu.name or "Attending Radiologist",
        findings=report.report_text, impression=report.impression,
        report_status=report.report_status, reported_at=report.reported_at,
        approved_at=report.approved_at
    )
