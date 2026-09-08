from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, time


# --- Dashboard ---
class RecentActivityItem(BaseModel):
    activity_type: str  # 'registration', 'appointment', 'check_in', 'visitor_pass'
    title: str
    description: str
    timestamp: datetime
    badge: str


class DashboardSummaryResponse(BaseModel):
    total_patients_today: int
    total_appointments_today: int
    checked_in_today: int
    active_doctors_count: int
    waiting_tokens_count: int
    today_collections_amount: float
    recent_activities: List[RecentActivityItem] = []


# --- Duplicate Check ---
class DuplicateCheckRequest(BaseModel):
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None


class DuplicatePatientMatch(BaseModel):
    patient_id: UUID
    mrn: str
    patient_code: str
    full_name: str
    phone: Optional[str]
    date_of_birth: date
    match_reason: str


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    matches: List[DuplicatePatientMatch] = []


# --- Doctor Availability & OPD Roster ---
class DoctorRosterItem(BaseModel):
    doctor_id: UUID
    doctor_code: str
    doctor_name: str
    department_name: str
    specialization_name: str
    room_number: str
    consultation_fee: float
    status: str
    shift_timings: str
    tokens_issued_today: int
    waiting_queue_count: int


# --- Appointment Booking & OPD Visit Slip ---
class AppointmentBookRequest(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    department_id: Optional[UUID] = None
    appointment_type: str = "Walk-in"  # 'Walk-in' | 'Scheduled' | 'Follow-Up' | 'Emergency'
    appointment_date: Optional[date] = None
    time_slot: Optional[str] = "Immediate"
    chief_complaint: Optional[str] = None
    consultation_fee: float = 500.0
    payment_method: str = "Cash"  # 'Cash' | 'Card' | 'UPI' | 'Insurance'


class OPDVisitSlipResponse(BaseModel):
    appointment_id: UUID
    appointment_number: str
    token_number: str
    patient_id: UUID
    patient_name: str
    mrn: str
    phone: Optional[str]
    doctor_name: str
    department_name: str
    specialization_name: str
    room_number: str
    appointment_date: date
    appointment_time: str
    appointment_type: str
    consultation_fee: float
    payment_method: str
    payment_status: str
    queue_status: str
    issued_at: datetime


# --- Check-In ---
class CheckInResponse(BaseModel):
    appointment_id: UUID
    appointment_number: str
    patient_name: str
    mrn: str
    doctor_name: str
    room_number: str
    token_number: str
    status: str
    checked_in_at: datetime


# --- Live Queue ---
class QueueTokenItem(BaseModel):
    token_id: UUID
    appointment_id: Optional[UUID] = None
    token_number: str
    patient_id: Optional[UUID]
    patient_name: str
    mrn: str
    doctor_name: str
    doctor_id: Optional[UUID] = None
    department_name: str
    room_number: str
    token_type: str
    priority: int
    status: str  # 'waiting', 'called', 'in_consultation', 'completed', 'no_show'
    issued_at: datetime
    called_at: Optional[datetime] = None


class QueueLiveResponse(BaseModel):
    total_in_queue: int
    waiting_count: int
    in_consultation_count: int
    completed_count: int
    tokens: List[QueueTokenItem] = []


class IssueTokenRequest(BaseModel):
    patient_id: UUID
    doctor_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    service_point_name: str = "OPD General Counter"
    token_type: str = "walk_in"  # 'walk_in' | 'priority' | 'emergency'
    priority: int = 0


# --- Inpatient Enquiry ---
class InpatientEnquiryItem(BaseModel):
    admission_id: UUID
    admission_number: str
    patient_name: str
    mrn: str
    gender: str
    age_or_dob: str
    ward_name: str
    room_number: str
    bed_number: str
    floor_number: str
    attending_doctor: str
    department_name: str
    admission_date: datetime
    admission_status: str  # 'Admitted', 'Discharged'


# --- Visitor Pass ---
class VisitorPassRequest(BaseModel):
    patient_id: Optional[UUID] = None
    patient_mrn_or_name: str
    visitor_name: str
    visitor_phone: str
    relationship: str
    id_proof_number: Optional[str] = None
    ward_or_room: Optional[str] = None
    purpose: Optional[str] = "Patient Visit"
    valid_hours: int = 4


class VisitorPassResponse(BaseModel):
    pass_id: UUID
    pass_number: str
    visitor_name: str
    visitor_phone: str
    patient_name: str
    patient_mrn: str
    ward_or_room: str
    issued_at: datetime
    valid_until: datetime
    status: str
