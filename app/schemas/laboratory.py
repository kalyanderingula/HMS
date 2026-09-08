from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# Parameter Schemas
class LabParameterCreate(BaseModel):
    parameter_name: str
    unit: str
    normal_range: str
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None

class LabParameterResponse(BaseModel):
    parameter_id: UUID
    parameter_name: str
    unit: str
    normal_range: str

# Lab Test Schemas
class LabTestCreateRequest(BaseModel):
    test_code: str
    test_name: str
    test_method: Optional[str] = "Automated Analyzer"
    turnaround_time_hours: int = 4
    fasting_required: bool = False
    price: float = 250.0
    parameters: List[LabParameterCreate] = []

class LabTestResponse(BaseModel):
    test_id: UUID
    test_code: str
    test_name: str
    test_method: Optional[str]
    turnaround_time_hours: int
    fasting_required: bool
    price: float
    parameters: List[LabParameterResponse] = []

# Lab Order Schemas
class LabOrderItemCreate(BaseModel):
    test_id: UUID

class LabOrderCreateRequest(BaseModel):
    patient_id: UUID
    encounter_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    priority: str = "Routine"  # Routine, Urgent, STAT
    clinical_notes: Optional[str] = None
    items: List[LabOrderItemCreate]

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
    result_flag: str = "Normal"  # Normal, High, Low, Critical

class LabResultEntryRequest(BaseModel):
    order_item_id: UUID
    technician_remarks: Optional[str] = None
    parameters: List[ParameterResultEntry]

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
