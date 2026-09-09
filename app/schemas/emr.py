from pydantic import BaseModel, validator
from pydantic import Field, model_validator
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime


# ============================================================
# ENCOUNTER SCHEMAS
# ============================================================

class StartEncounterRequest(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    appointment_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    encounter_type: str = "OPD"  # OPD | IPD | Emergency | Teleconsultation
    chief_complaint: str


class EncounterResponse(BaseModel):
    encounter_id: UUID
    encounter_number: str
    patient_id: UUID
    patient_name: str
    mrn: str
    doctor_id: UUID
    doctor_name: str
    encounter_type: str
    chief_complaint: str
    encounter_status: str
    encounter_date: datetime
    created_at: datetime


class EncounterClinicalRecord(BaseModel):
    encounter: EncounterResponse
    vitals: List["VitalSignsResponse"] = []
    soap_notes: List["SOAPNoteResponse"] = []
    diagnoses: List["DiagnosisResponse"] = []
    prescriptions: List["PrescriptionResponse"] = []


# ============================================================
# VITAL SIGNS SCHEMAS
# ============================================================

class VitalSignsRequest(BaseModel):
    temperature: Optional[float] = None          # Celsius
    systolic_bp: Optional[int] = None            # mmHg
    diastolic_bp: Optional[int] = None           # mmHg
    heart_rate: Optional[int] = None             # bpm
    respiratory_rate: Optional[int] = None       # breaths/min
    oxygen_saturation: Optional[float] = None    # SpO2 %
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    pain_score: Optional[int] = Field(default=None, ge=0, le=10)  # 0-10 VAS scale

    @model_validator(mode="after")
    def validate_measurements(self):
        limits = {
            "temperature": (25, 50), "systolic_bp": (40, 300),
            "diastolic_bp": (20, 200), "heart_rate": (20, 300),
            "respiratory_rate": (1, 100), "oxygen_saturation": (0, 100),
            "height_cm": (30, 275), "weight_kg": (0.5, 700),
        }
        for name, (low, high) in limits.items():
            value = getattr(self, name)
            if value is not None and not low <= value <= high:
                raise ValueError(f"{name} must be between {low} and {high}")
        return self


class VitalSignsResponse(BaseModel):
    vital_sign_id: UUID
    encounter_id: UUID
    patient_id: UUID
    temperature: Optional[float]
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    heart_rate: Optional[int]
    respiratory_rate: Optional[int]
    oxygen_saturation: Optional[float]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    bmi: Optional[float]
    pain_score: Optional[int]
    # Computed alerts
    bp_status: Optional[str] = None
    bmi_status: Optional[str] = None
    spo2_status: Optional[str] = None
    recorded_at: datetime


# ============================================================
# SOAP CLINICAL NOTES SCHEMAS
# ============================================================

class SOAPNoteRequest(BaseModel):
    subjective: str   # Patient's own words - chief complaint, symptoms history
    objective: str    # Clinical findings - physical exam, lab/test results
    assessment: str   # Doctor's diagnosis and clinical reasoning
    plan: str         # Treatment plan, prescriptions, referrals, follow-up
    is_confidential: bool = False


class SOAPNoteResponse(BaseModel):
    note_id: UUID
    encounter_id: UUID
    doctor_id: UUID
    note_type: str
    subjective: str
    objective: str
    assessment: str
    plan: str
    is_confidential: bool
    created_at: datetime


# ============================================================
# DIAGNOSIS SCHEMAS
# ============================================================

class DiagnosisRequest(BaseModel):
    diagnosis_code: str            # ICD-10 code e.g. "I10", "J06.9", "E11.9"
    diagnosis_name: str            # Human readable: "Hypertension", "Common Cold"
    diagnosis_description: Optional[str] = None
    diagnosis_type: str = "Primary"   # Primary | Secondary | Differential
    severity: str = "Moderate"        # Mild | Moderate | Severe | Critical


class DiagnosisResponse(BaseModel):
    diagnosis_id: UUID
    encounter_id: UUID
    patient_id: UUID
    doctor_id: UUID
    diagnosis_code: str
    diagnosis_name: str
    diagnosis_description: Optional[str]
    diagnosis_type: str
    severity: str
    diagnosed_at: datetime


# ============================================================
# PRESCRIPTION / MEDICATION SCHEMAS
# ============================================================

class PrescriptionItemRequest(BaseModel):
    drug_id: UUID
    medicine_name: Optional[str] = None
    dosage: str                    # e.g. "500mg", "10mg"
    frequency: str                 # e.g. "TDS" (3x/day), "BD" (2x/day), "OD" (once daily)
    route: str = "Oral"            # Oral | IV | IM | Topical | Inhalation
    duration: str                  # e.g. "5 days", "2 weeks"
    instructions: Optional[str] = None  # e.g. "Take with food", "Avoid alcohol"
    quantity_prescribed: float = Field(gt=0, allow_inf_nan=False)


class PrescriptionResponse(BaseModel):
    medication_record_id: UUID
    encounter_id: UUID
    patient_id: UUID
    doctor_id: UUID
    medicine_name: str
    drug_id: Optional[UUID] = None
    quantity_prescribed: Optional[float] = None
    medication_status: str = "Draft"
    dosage: str
    frequency: str
    route: str
    duration: str
    instructions: Optional[str]
    created_at: datetime


class BulkPrescriptionRequest(BaseModel):
    medications: List[PrescriptionItemRequest] = Field(min_length=1, max_length=50)


# ============================================================
# ALLERGY SCHEMAS
# ============================================================

class AllergyRequest(BaseModel):
    allergen_name: str              # e.g. "Penicillin", "Peanuts", "Ibuprofen"
    allergy_type: str = "Drug"      # Drug | Food | Environmental | Latex
    reaction_description: str       # e.g. "Anaphylaxis", "Hives", "Nausea"
    severity: str = "Moderate"      # Mild | Moderate | Severe | Life-threatening


class AllergyResponse(BaseModel):
    allergy_record_id: UUID
    patient_id: UUID
    allergen_name: str
    allergy_type: str
    reaction_description: str
    severity: str
    created_at: datetime


# ============================================================
# REFERRAL SCHEMAS
# ============================================================

class ReferralRequest(BaseModel):
    referred_doctor_id: Optional[UUID] = None
    referred_department_id: Optional[UUID] = None
    referral_reason: str


class ReferralResponse(BaseModel):
    referral_id: UUID
    encounter_id: UUID
    referring_doctor_id: Optional[UUID]
    referred_department_id: Optional[UUID]
    referred_doctor_id: Optional[UUID]
    referral_reason: str
    referral_status: str
    referred_at: datetime


# ============================================================
# PATIENT 360° EMR SUMMARY
# ============================================================

class PatientEMRSummaryResponse(BaseModel):
    patient_id: UUID
    patient_name: str
    mrn: str
    date_of_birth: date
    gender: str
    blood_group: str
    # Active Alerts
    active_allergies: List[AllergyResponse] = []
    # Latest Vitals
    latest_vitals: Optional[VitalSignsResponse] = None
    vital_signs_timeline: List[VitalSignsResponse] = []
    # Active Diagnoses
    active_diagnoses: List[DiagnosisResponse] = []
    # Current Medications
    current_medications: List[PrescriptionResponse] = []
    # Past Encounters (summary)
    past_encounters: List[dict] = []
    # Pending Referrals
    pending_referrals: List[ReferralResponse] = []
    radiology_reports: List[dict] = []
    blood_transfusions: List[dict] = []
    laboratory_results: List[dict] = []
    medication_administration_history: List[dict] = []
    emergency_visits: List[dict] = []
    surgery_history: List[dict] = []


# ============================================================
# COMPLETE ENCOUNTER
# ============================================================

class CompleteEncounterRequest(BaseModel):
    clinical_summary: Optional[str] = None
    followup_date: Optional[date] = None
    followup_instructions: Optional[str] = None


# ============================================================
# TELEMEDICINE SCHEMAS
# ============================================================

class TeleAppointmentRequest(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    appointment_datetime: datetime
    meeting_platform: str = "HMS Telehealth"  # HMS Telehealth | Zoom | Teams
    chief_complaint: Optional[str] = None


class TeleAppointmentResponse(BaseModel):
    virtual_appointment_id: UUID
    patient_name: str
    mrn: str
    doctor_name: str
    appointment_datetime: datetime
    consultation_link: str
    meeting_platform: str
    status: str
    chief_complaint: Optional[str] = None
    emr_encounter_id: Optional[UUID] = None
    created_at: datetime


class TeleSessionRequest(BaseModel):
    virtual_appointment_id: UUID


class TeleSessionResponse(BaseModel):
    session_id: UUID
    virtual_appointment_id: UUID
    session_status: str
    session_start_time: Optional[datetime]
    session_end_time: Optional[datetime]
    duration_minutes: Optional[int] = None


class TeleSessionCompleteRequest(BaseModel):
    clinical_notes: str
