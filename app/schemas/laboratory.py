from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

# Parameter Schemas
class LabParameterCreate(BaseModel):
    parameter_name: str
    unit: str
    normal_range: str
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    parameter_code: Optional[str] = None
    result_type: str = "NUMERIC"
    specimen_type: Optional[str] = None
    method: Optional[str] = None
    display_order: int = 0
    is_required: bool = True
    allowed_values: Optional[list[str]] = None
    interpretation: Optional[str] = None

class LabParameterResponse(BaseModel):
    parameter_id: UUID
    parameter_name: str
    unit: str
    normal_range: str
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    parameter_code: Optional[str] = None
    result_type: str = "NUMERIC"
    specimen_type: Optional[str] = None
    method: Optional[str] = None
    display_order: int = 0
    is_required: bool = True
    allowed_values: Optional[list[str]] = None
    interpretation: Optional[str] = None

# Lab Test Schemas
class LabTestCreateRequest(BaseModel):
    test_code: str
    test_name: str
    test_method: Optional[str] = "Automated Analyzer"
    turnaround_time_hours: int = 4
    fasting_required: bool = False
    sample_volume: Optional[str] = None
    price: float = 250.0
    parameters: List[LabParameterCreate] = []

class LabTestResponse(BaseModel):
    test_id: UUID
    test_code: str
    test_name: str
    test_method: Optional[str]
    turnaround_time_hours: int
    fasting_required: bool
    sample_volume: Optional[str] = None
    specimen_type: Optional[str] = None
    performing_department: str = "Laboratory"
    approving_specialty: str = "Pathology / Laboratory Medicine"
    price: float
    parameters: List[LabParameterResponse] = []

class LabReferenceRangeCreate(BaseModel):
    sex: Optional[str] = "ALL"
    age_min: Optional[float] = None
    age_max: Optional[float] = None
    age_unit: str = "YEARS"
    pregnancy_status: Optional[str] = None
    trimester: Optional[int] = Field(default=None, ge=1, le=3)
    menstrual_phase: Optional[str] = None
    clinical_condition: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    reference_text: Optional[str] = None
    unit: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    version: int = Field(default=1, ge=1)

# Lab Order Schemas
class LabOrderItemCreate(BaseModel):
    test_id: UUID

class LabOrderCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    priority: str = "Routine"  # Routine, Urgent, STAT
    clinical_notes: Optional[str] = None
    items: List[LabOrderItemCreate] = Field(min_length=1, max_length=100)

class LabBookingCreateRequest(BaseModel):
    patient_id: Optional[UUID] = None
    scheduled_at: datetime
    referral_type: str = "Voluntary"
    referral_doctor_id: Optional[UUID] = None
    referral_doctor_name: Optional[str] = None
    clinical_notes: Optional[str] = None
    items: List[LabOrderItemCreate] = Field(min_length=1, max_length=25)

class SampleCollectionRequest(BaseModel):
    order_item_id: UUID
    sample_type: str = "Venous Blood"  # Blood, Serum, Urine, Sputum, Swab

class SampleResponse(BaseModel):
    sample_id: UUID
    order_item_id: UUID
    sample_barcode: str
    sample_type: str
    collected_at: datetime

# Result Entry Schemas
class ParameterResultEntry(BaseModel):
    parameter_id: UUID
    result_value: str
    result_flag: Optional[str] = None  # Ignored; calculated from effective rules.

class LabResultEntryRequest(BaseModel):
    order_item_id: UUID
    technician_remarks: Optional[str] = None
    pregnancy_status: Optional[str] = None
    trimester: Optional[int] = Field(default=None, ge=1, le=3)
    menstrual_phase: Optional[str] = None
    parameters: List[ParameterResultEntry] = Field(min_length=1, max_length=100)

class ParameterResultResponse(BaseModel):
    parameter_name: str
    unit: str
    normal_range: str
    result_value: str
    result_flag: str

class LabResultResponse(BaseModel):
    result_entry_id: UUID
    order_item_id: UUID
    test_name: str
    result_status: str
    entered_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[UUID]
    remarks: Optional[str]
    parameters: List[ParameterResultResponse] = []

class LabOrderItemResponse(BaseModel):
    order_item_id: UUID
    test_id: UUID
    test_code: str
    test_name: str
    order_status: str
    sample: Optional[SampleResponse] = None
    result: Optional[LabResultResponse] = None

class LabOrderResponse(BaseModel):
    lab_order_id: UUID
    order_number: str
    patient_id: UUID
    patient_name: str
    mrn: str
    doctor_name: str
    priority: str
    status: str
    ordered_at: datetime
    clinical_notes: Optional[str]
    items: List[LabOrderItemResponse] = []
