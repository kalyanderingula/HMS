from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# Modality & Room Schemas
class ModalityResponse(BaseModel):
    modality_id: UUID
    modality_code: str
    modality_name: str
    description: Optional[str]

class ImagingRoomResponse(BaseModel):
    imaging_room_id: UUID
    room_code: str
    room_name: str
    modality_code: str
    room_location: Optional[str]
    room_status: str

# Radiology Test Schemas
class RadiologyTestCreateRequest(BaseModel):
    test_code: str
    test_name: str
    modality_code: str
    body_part: Optional[str] = "General"
    duration_minutes: int = 30
    price: float = 600.0

class RadiologyTestResponse(BaseModel):
    radiology_test_id: UUID
    test_code: str
    test_name: str
    modality_id: UUID
    price: float
    is_active: bool

# Order Schemas
class RadiologyOrderItemCreate(BaseModel):
    radiology_test_id: UUID

class RadiologyOrderCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    priority: str = "Routine"  # Routine, Urgent, STAT
    clinical_indication: str
    items: List[RadiologyOrderItemCreate]

# Appointment & Scheduling
class RadiologyScheduleRequest(BaseModel):
    order_item_id: UUID
    imaging_room_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime

class RadiologyAppointmentResponse(BaseModel):
    radiology_appointment_id: UUID
    order_item_id: UUID
    imaging_room_id: UUID
    room_name: str
    scheduled_start: datetime
    scheduled_end: datetime
    appointment_status: str

# Imaging Study & PACS
class ImagingStudyCreateRequest(BaseModel):
    radiology_appointment_id: UUID
    study_description: str

class ImagingStudyResponse(BaseModel):
    study_id: UUID
    study_instance_uid: str
    accession_number: str
    patient_id: UUID
    patient_name: str
    mrn: str
    study_description: str
    study_date: datetime

# Reporting
class RadiologyReportCreateRequest(BaseModel):
    study_id: UUID
    findings: str
    impression: str
    is_critical: bool = False
    critical_alert_details: Optional[str] = None

class RadiologyReportResponse(BaseModel):
    report_id: UUID
    study_id: UUID
    study_description: str
    radiologist_name: str
    findings: str
    impression: str
    report_status: str
    is_critical: bool = False
    critical_alert_details: Optional[str] = None
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    acknowledgement_notes: Optional[str] = None
    reported_at: datetime
    approved_at: Optional[datetime]

# PACS Image Schemas
class ImagingStudyImageCreate(BaseModel):
    image_url: str
    slice_description: Optional[str] = None
    series_number: int = 1
    instance_number: int = 1
    is_key_image: bool = False
    modality_code: Optional[str] = None

class ImagingStudyImageResponse(BaseModel):
    image_id: UUID
    study_id: UUID
    series_number: int
    instance_number: int
    image_url: str
    slice_description: Optional[str]
    is_key_image: bool
    modality_code: Optional[str]
    uploaded_at: datetime

class PACSViewerResponse(BaseModel):
    study_id: UUID
    accession_number: str
    patient_id: UUID
    patient_name: str
    mrn: str
    study_description: str
    modality_code: str
    study_date: datetime
    images: List[ImagingStudyImageResponse] = []
    report: Optional[RadiologyReportResponse] = None

class RadiologyOrderItemResponse(BaseModel):
    order_item_id: UUID
    radiology_test_id: UUID
    test_code: str
    test_name: str
    order_status: str
    appointment: Optional[RadiologyAppointmentResponse] = None
    study: Optional[ImagingStudyResponse] = None
    report: Optional[RadiologyReportResponse] = None

class RadiologyOrderResponse(BaseModel):
    radiology_order_id: UUID
    order_number: str
    patient_id: UUID
    patient_name: str
    mrn: str
    doctor_name: str
    priority: str
    status: str
    clinical_indication: str
    ordered_at: datetime
    items: List[RadiologyOrderItemResponse] = []
