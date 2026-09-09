import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text

from app.config import get_db
from app.api.auth import get_current_user, require_roles, CurrentUser
from app.models.patient import Patient
from app.api.doctor import Doctor
from app.models.radiology_models import (
    ImagingModality, ImagingRoom, RadiologyTest,
    RadiologyOrderStatus, RadiologyPriority,
    RadiologyOrder, RadiologyOrderItem,
    RadiologyAppointment, ImagingStudy, Radiologist, RadiologyReport,
    ImagingStudyImage
)
from app.schemas.radiology import (
    ModalityResponse, ImagingRoomResponse,
    RadiologyTestCreateRequest, RadiologyTestResponse,
    RadiologyOrderCreateRequest, RadiologyOrderResponse, RadiologyOrderItemResponse,
    RadiologyScheduleRequest, RadiologyAppointmentResponse,
    ImagingStudyCreateRequest, ImagingStudyResponse,
    RadiologyReportCreateRequest, RadiologyReportResponse,
    ImagingStudyImageCreate, ImagingStudyImageResponse, PACSViewerResponse
)

router = APIRouter(prefix="/radiology", tags=["Radiology Information System (RIS/PACS)"])


async def create_radiology_invoice(db, patient_id, order_id, items, created_by):
    """Create one source-linked invoice for a radiology order."""
    existing = await db.scalar(text("""SELECT invoice_id FROM billing.invoice_items
        WHERE item_type='Radiology' AND item_reference_id=:source LIMIT 1"""), {"source": order_id})
    if existing:
        return existing
    account = await db.scalar(text("""SELECT billing_account_id FROM billing.billing_accounts
        WHERE patient_id=:patient ORDER BY created_at LIMIT 1 FOR UPDATE"""), {"patient": patient_id})
    if not account:
        account = uuid.uuid4()
        await db.execute(text("""INSERT INTO billing.billing_accounts
            (billing_account_id,patient_id,account_number,account_status,total_due,total_paid)
            VALUES (:id,:patient,:number,'Active',0,0)"""),
            {"id": account, "patient": patient_id, "number": f"ACC-{uuid.uuid4().hex}"})
    total = sum(float(item["price"]) for item in items)
    status_id = await db.scalar(text("""INSERT INTO billing.billing_statuses(status_name)
        VALUES (:name) ON CONFLICT(status_name) DO UPDATE SET status_name=EXCLUDED.status_name
        RETURNING billing_status_id"""), {"name": "Paid" if total == 0 else "Pending"})
    invoice_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO billing.invoices
        (invoice_id,invoice_number,billing_account_id,patient_id,billing_status_id,
         subtotal_amount,tax_amount,discount_amount,total_amount,paid_amount,balance_amount,notes,created_by)
        VALUES (:id,:number,:account,:patient,:status,:total,0,0,:total,0,:total,:notes,:user)"""),
        {"id": invoice_id, "number": f"INV-RAD-{uuid.uuid4().hex[:12].upper()}", "account": account,
         "patient": patient_id, "status": status_id, "total": total,
         "notes": "Automatically generated from radiology order", "user": created_by})
    for index, item in enumerate(items):
        await db.execute(text("""INSERT INTO billing.invoice_items
            (invoice_id,item_type,item_reference_id,item_name,quantity,unit_price,tax_amount,discount_amount,line_total)
            VALUES (:invoice,'Radiology',:source,:name,1,:price,0,0,:price)"""),
            {"invoice": invoice_id, "source": order_id if index == 0 else item["item_id"],
             "name": item["name"], "price": item["price"]})
    await db.execute(text("""UPDATE billing.billing_accounts SET total_due=COALESCE(total_due,0)+:total,
        updated_at=CURRENT_TIMESTAMP WHERE billing_account_id=:account"""),
        {"account": account, "total": total})
    return invoice_id

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
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "admin"]))
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
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "receptionist", "admin"]))
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
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "admin"]))
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
    billable_items = []
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
        billable_items.append({"item_id": order_item.order_item_id, "name": test.test_name,
                               "price": float(test.price or 0)})

        item_responses.append(RadiologyOrderItemResponse(
            order_item_id=order_item.order_item_id, radiology_test_id=test.radiology_test_id,
            test_code=test.test_code, test_name=test.test_name, order_status="Ordered"
        ))

    if not item_responses:
        raise HTTPException(422, "At least one valid radiology test is required")
    await create_radiology_invoice(db, patient.patient_id, order.radiology_order_id,
                                   billable_items, cu.user_id)
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
    if item.order_status != "Ordered":
        raise HTTPException(409, f"Only ordered examinations can be scheduled; current status is {item.order_status}")

    room_res = await db.execute(select(ImagingRoom).where(ImagingRoom.imaging_room_id == req.imaging_room_id))
    room = room_res.scalars().first()
    if not room: raise HTTPException(404, "Imaging room not found")
    if req.scheduled_end <= req.scheduled_start:
        raise HTTPException(422, "Scheduled end must be after scheduled start")
    conflict = await db.scalar(select(RadiologyAppointment.radiology_appointment_id).where(
        RadiologyAppointment.imaging_room_id == req.imaging_room_id,
        RadiologyAppointment.appointment_status != "Cancelled",
        RadiologyAppointment.scheduled_start < req.scheduled_end,
        RadiologyAppointment.scheduled_end > req.scheduled_start,
    ))
    if conflict:
        raise HTTPException(409, "The imaging room is already booked for this time")

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
    if appt.appointment_status != "Scheduled":
        raise HTTPException(409, "Only scheduled appointments can start a study")
    existing = await db.scalar(select(ImagingStudy.study_id).where(
        ImagingStudy.radiology_appointment_id == appt.radiology_appointment_id))
    if existing:
        raise HTTPException(409, "A study already exists for this appointment")

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
    existing = await db.scalar(select(RadiologyReport.report_id).where(RadiologyReport.study_id == study.study_id))
    if existing:
        raise HTTPException(409, "A final report already exists for this study")

    rad_row = (await db.execute(select(Radiologist).limit(1))).scalars().first()
    if not rad_row:
        rad_row = Radiologist(specialization="General Diagnostic Radiology")
        db.add(rad_row)
        await db.flush()

    report = RadiologyReport(
        study_id=study.study_id, radiologist_id=rad_row.radiologist_id,
        report_text=req.findings, impression=req.impression,
        report_status="Final", is_critical=req.is_critical,
        critical_alert_details=req.critical_alert_details,
        reported_at=datetime.utcnow(), approved_at=datetime.utcnow()
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
                    if order.created_by:
                        subject = f"🚨 CRITICAL RADIOLOGY ALERT: {order.order_number}" if req.is_critical else f"Radiology report ready: {order.order_number}"
                        body = f"CRITICAL FINDING: {req.critical_alert_details or req.impression}" if req.is_critical else f"The final report is available for {study.study_description or 'the imaging study'}."
                        await db.execute(text("""INSERT INTO core.notifications
                            (recipient_id,recipient_type,source_module,source_reference_id,subject,body,status,sent_at)
                            VALUES (:recipient,'User','Radiology',:source,:subject,:body,'sent',CURRENT_TIMESTAMP)"""),
                            {"recipient": order.created_by, "source": report.report_id,
                             "subject": subject, "body": body})

    await db.commit()
    await db.refresh(report)

    return RadiologyReportResponse(
        report_id=report.report_id, study_id=study.study_id,
        study_description=study.study_description or "Radiology Exam",
        radiologist_name=cu.name or "Attending Radiologist",
        findings=report.report_text, impression=report.impression,
        report_status=report.report_status,
        is_critical=report.is_critical or False,
        critical_alert_details=report.critical_alert_details,
        acknowledged_by=report.acknowledged_by,
        acknowledged_at=report.acknowledged_at,
        acknowledgement_notes=report.acknowledgement_notes,
        reported_at=report.reported_at,
        approved_at=report.approved_at
    )


# ----------------- PACS Images & Viewer -----------------

@router.post("/studies/{study_id}/images", response_model=ImagingStudyImageResponse, status_code=201)
async def add_study_image(
    study_id: uuid.UUID,
    req: ImagingStudyImageCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "admin", "super_admin"]))
):
    """Attach a captured/uploaded slice or key image to an imaging study."""
    s_res = await db.execute(select(ImagingStudy).where(ImagingStudy.study_id == study_id))
    study = s_res.scalars().first()
    if not study:
        raise HTTPException(404, "Imaging study not found")

    image = ImagingStudyImage(
        study_id=study_id,
        series_number=req.series_number,
        instance_number=req.instance_number,
        image_url=req.image_url,
        slice_description=req.slice_description,
        is_key_image=req.is_key_image,
        modality_code=req.modality_code,
        uploaded_at=datetime.utcnow()
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    return ImagingStudyImageResponse(
        image_id=image.image_id,
        study_id=image.study_id,
        series_number=image.series_number,
        instance_number=image.instance_number,
        image_url=image.image_url,
        slice_description=image.slice_description,
        is_key_image=image.is_key_image,
        modality_code=image.modality_code,
        uploaded_at=image.uploaded_at
    )


@router.get("/studies/{study_id}/images", response_model=List[ImagingStudyImageResponse])
async def list_study_images(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "surgeon", "nurse", "admin", "super_admin"]))
):
    """List all imaging series/slices for a study."""
    res = await db.execute(select(ImagingStudyImage).where(ImagingStudyImage.study_id == study_id).order_by(ImagingStudyImage.series_number, ImagingStudyImage.instance_number))
    rows = res.scalars().all()
    return [
        ImagingStudyImageResponse(
            image_id=r.image_id, study_id=r.study_id,
            series_number=r.series_number, instance_number=r.instance_number,
            image_url=r.image_url, slice_description=r.slice_description,
            is_key_image=r.is_key_image, modality_code=r.modality_code,
            uploaded_at=r.uploaded_at
        )
        for r in rows
    ]


@router.get("/studies/{study_id}/viewer", response_model=PACSViewerResponse)
async def get_pacs_viewer(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["radiologist", "doctor", "surgeon", "nurse", "admin", "super_admin"]))
):
    """Retrieve study DICOM / PACS viewer payload with patient details, series images, and final report."""
    s_res = await db.execute(select(ImagingStudy).where(ImagingStudy.study_id == study_id))
    study = s_res.scalars().first()
    if not study:
        raise HTTPException(404, "Imaging study not found")

    p_res = await db.execute(select(Patient).where(Patient.patient_id == study.patient_id))
    patient = p_res.scalars().first()

    modality_code = "XRAY"
    if study.modality_id:
        m_res = await db.execute(select(ImagingModality).where(ImagingModality.modality_id == study.modality_id))
        mod = m_res.scalars().first()
        if mod: modality_code = mod.modality_code

    # Images
    img_res = await db.execute(select(ImagingStudyImage).where(ImagingStudyImage.study_id == study_id).order_by(ImagingStudyImage.series_number, ImagingStudyImage.instance_number))
    images = [
        ImagingStudyImageResponse(
            image_id=r.image_id, study_id=r.study_id,
            series_number=r.series_number, instance_number=r.instance_number,
            image_url=r.image_url, slice_description=r.slice_description,
            is_key_image=r.is_key_image, modality_code=r.modality_code,
            uploaded_at=r.uploaded_at
        )
        for r in img_res.scalars().all()
    ]

    # Report if available
    rep_res = await db.execute(select(RadiologyReport).where(RadiologyReport.study_id == study_id))
    report_row = rep_res.scalars().first()
    report_resp = None
    if report_row:
        report_resp = RadiologyReportResponse(
            report_id=report_row.report_id, study_id=study_id,
            study_description=study.study_description or "Radiology Study",
            radiologist_name="Radiology Specialist",
            findings=report_row.report_text, impression=report_row.impression,
            report_status=report_row.report_status,
            is_critical=report_row.is_critical or False,
            critical_alert_details=report_row.critical_alert_details,
            acknowledged_by=report_row.acknowledged_by,
            acknowledged_at=report_row.acknowledged_at,
            acknowledgement_notes=report_row.acknowledgement_notes,
            reported_at=report_row.reported_at, approved_at=report_row.approved_at
        )

    return PACSViewerResponse(
        study_id=study.study_id,
        accession_number=study.accession_number,
        patient_id=study.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}" if patient else "Patient",
        mrn=patient.mrn if patient else "",
        study_description=study.study_description or "Diagnostic Study",
        modality_code=modality_code,
        study_date=study.study_date,
        images=images,
        report=report_resp
    )


@router.post("/reports/{report_id}/acknowledge")
async def acknowledge_radiology_report(
    report_id: uuid.UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["doctor", "surgeon", "admin", "super_admin"]))
):
    """Doctor digitally acknowledges review of finalized radiology report."""
    rep_res = await db.execute(select(RadiologyReport).where(RadiologyReport.report_id == report_id).with_for_update())
    report = rep_res.scalars().first()
    if not report:
        raise HTTPException(404, "Radiology report not found")

    report.acknowledged_by = cu.user_id
    report.acknowledged_at = datetime.utcnow()
    report.acknowledgement_notes = notes
    await db.commit()
    return {
        "message": "Radiology report acknowledged successfully",
        "report_id": str(report.report_id),
        "acknowledged_by": str(cu.user_id),
        "acknowledged_at": report.acknowledged_at.isoformat()
    }
