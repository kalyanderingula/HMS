from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

# ==================== EMERGENCY & TRIAGE ====================
class EmergencyArrivalCreate(BaseModel):
    patient_id: UUID
    arrival_mode: str = "Walk-in"  # Walk-in, Ambulance, Trauma Helicopter
    brought_by: Optional[str] = "Family"
    arrival_condition: str

class EmergencyArrivalResponse(BaseModel):
    emergency_arrival_id: UUID
    patient_id: UUID
    patient_name: str
    mrn: str
    arrival_mode: str
    arrival_time: datetime
    arrival_condition: str

class TriageAssessmentCreate(BaseModel):
    emergency_arrival_id: UUID
    esi_level: int  # 1 (Resuscitation), 2 (Emergent), 3 (Urgent), 4 (Less Urgent), 5 (Non-urgent)
    chief_complaint: str
    vital_signs_summary: Optional[str] = None
    trauma_bay_code: Optional[str] = None

class TriageAssessmentResponse(BaseModel):
    triage_id: UUID
    emergency_arrival_id: UUID
    patient_name: str
    mrn: str
    esi_level: int
    triage_category: str
    response_time_minutes: int
    trauma_bay_code: Optional[str]
    assessed_at: datetime

# ==================== INPATIENT & BEDS ====================
class BedStatusResponse(BaseModel):
    bed_id: UUID
    bed_number: str
    ward_name: str
    room_number: str
    bed_type: str
    status: str  # Available, Occupied, Cleaning, Maintenance

class AdmissionCreate(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    bed_id: UUID
    admission_type: str = "Emergency"  # Emergency, Elective, Transfer
    admission_reason: str

class AdmissionResponse(BaseModel):
    admission_id: UUID
    admission_number: str
    patient_id: UUID
    patient_name: str
    mrn: str
    doctor_name: str
    ward_name: str
    room_number: str
    bed_number: str
    admission_date: datetime
    status: str

class BedTransferRequest(BaseModel):
    admission_id: UUID
    new_bed_id: UUID
    transfer_reason: str

class DischargeRequest(BaseModel):
    admission_id: UUID
    discharge_summary: str
    discharge_disposition: str = "Home"  # Home, Transferred, Deceased

# ==================== NURSING & MAR ====================
class NursingRoundCreate(BaseModel):
    patient_id: UUID
    round_notes: str
    vital_signs_summary: Optional[str] = None

class NursingRoundResponse(BaseModel):
    round_id: UUID
    patient_id: UUID
    patient_name: str
    nurse_name: str
    round_time: datetime
    round_notes: str

class MARItemResponse(BaseModel):
    prescription_item_id: UUID
    medicine_name: str
    dosage: str
    frequency: str
    route: str
    instructions: Optional[str]

class MedicationAdministrationCreate(BaseModel):
    mar_id: Optional[UUID] = None
    patient_id: UUID
    prescription_item_id: Optional[UUID] = None
    medicine_name: str
    dosage_given: str
    route: str = "Oral"
    notes: Optional[str] = None
    administration_status: str = "Administered"
    exception_reason: Optional[str] = None

class MedicationAdministrationResponse(BaseModel):
    administration_id: UUID
    patient_id: UUID
    medicine_name: str
    dosage_given: str
    route: str
    administered_by_name: str
    administered_at: datetime
    notes: Optional[str]
    administration_status: str = "Administered"
    exception_reason: Optional[str] = None

# ==================== SURGERY & OT ====================
class SurgeryRequestCreate(BaseModel):
    patient_id: UUID
    procedure_name: str
    procedure_code: str
    urgency: str = "Elective"  # Emergency, Elective, Urgent
    clinical_indication: str
    estimated_charge: float = 0

class SurgeryScheduleCreate(BaseModel):
    surgery_request_id: UUID
    ot_room_number: str
    scheduled_start: datetime
    scheduled_end: datetime
    primary_surgeon_id: UUID
    anesthesiologist_name: Optional[str] = "Dr. Anesthesiologist"

class SurgeryScheduleResponse(BaseModel):
    surgery_schedule_id: UUID
    patient_name: str
    procedure_name: str
    ot_room_number: str
    scheduled_start: datetime
    scheduled_end: datetime
    primary_surgeon_name: str
    schedule_status: str

class SurgeryCompleteRequest(BaseModel):
    surgical_findings: str
    anesthesia_type: str = "General Anesthesia"
    outcome: str = "Successful - Transferred to PACU"

# ==================== BLOOD BANK ====================
class BloodUnitResponse(BaseModel):
    blood_unit_id: UUID
    unit_number: str
    blood_group: str
    component_name: str
    volume_ml: int
    expiry_date: date
    status: str

class BloodRequestCreate(BaseModel):
    patient_id: UUID
    blood_group: str
    component_name: str = "PRBC"
    units_requested: int = 1
    urgency: str = "Routine"
    clinical_indication: str

class BloodRequestResponse(BaseModel):
    blood_request_id: UUID
    patient_id: UUID
    patient_name: str
    blood_group: str
    component_name: str
    units_requested: int
    urgency: str
    status: str
    created_at: datetime

class CrossMatchCreate(BaseModel):
    blood_request_id: UUID
    blood_unit_id: UUID
    compatibility_result: str = "Compatible"  # Compatible, Incompatible

class CrossMatchResponse(BaseModel):
    cross_match_id: UUID
    blood_request_id: UUID
    blood_unit_number: str
    patient_name: str
    result: str
    tested_at: datetime

class BloodTransfusionCreate(BaseModel):
    blood_request_id: UUID
    blood_unit_id: UUID
    volume_transfused: int = 350
    notes: Optional[str] = "No immediate adverse transfusion reactions observed."
    adverse_reaction: bool = False
    reaction_details: Optional[str] = None

class BloodIssueCreate(BaseModel):
    blood_request_id: UUID
    blood_unit_id: UUID

class BloodTransfusionResponse(BaseModel):
    transfusion_id: UUID
    patient_id: UUID
    blood_unit_number: str
    volume_transfused: int
    status: str
    administered_at: datetime
    notes: Optional[str]
    adverse_reaction: bool = False
    reaction_details: Optional[str] = None
