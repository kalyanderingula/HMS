from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

# Drug Schemas
class DrugCreateRequest(BaseModel):
    drug_code: str
    generic_name: str
    scientific_name: Optional[str] = None
    brand_name: Optional[str] = None
    dosage_form: str = "Tablet"  # Tablet, Capsule, Syrup, Injection, Ointment
    strength: str = "500mg"
    is_controlled_substance: bool = False
    requires_prescription: bool = True
    storage_conditions: Optional[str] = "Store below 25C"
    description: Optional[str] = None

class DrugResponse(BaseModel):
    drug_id: UUID
    drug_code: str
    generic_name: str
    scientific_name: Optional[str]
    brand_name: Optional[str]
    dosage_form: Optional[str]
    strength: Optional[str]
    is_controlled_substance: bool
    requires_prescription: bool
    storage_conditions: Optional[str]
    created_at: datetime

# Stock Batch Schemas
class StockBatchReceiveRequest(BaseModel):
    drug_id: UUID
    batch_number: str
    manufacturing_date: Optional[date] = None
    expiry_date: date
    quantity_received: float = Field(gt=0, allow_inf_nan=False)
    purchase_price: float = Field(ge=0, allow_inf_nan=False)
    selling_price: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.expiry_date < date.today():
            raise ValueError("Cannot receive expired stock")
        if self.manufacturing_date and self.manufacturing_date > self.expiry_date:
            raise ValueError("Manufacturing date must precede expiry")
        return self

class StockBatchResponse(BaseModel):
    batch_id: UUID
    inventory_id: UUID
    drug_id: UUID
    generic_name: str
    batch_number: str
    manufacturing_date: Optional[date]
    expiry_date: date
    quantity_received: float
    quantity_remaining: float
    purchase_price: float
    selling_price: float
    is_expired: bool = False

# Inventory Schemas
class InventoryStatusResponse(BaseModel):
    inventory_id: UUID
    drug_id: UUID
    drug_code: str
    generic_name: str
    available_quantity: float
    reserved_quantity: float
    reorder_level: float
    is_low_stock: bool
    batches: List[StockBatchResponse] = []

# Dispensing Schemas
class DispenseItemRequest(BaseModel):
    drug_id: UUID
    batch_id: UUID
    prescription_item_id: Optional[UUID] = None
    quantity_dispensed: float = Field(gt=0, allow_inf_nan=False)
    instructions: Optional[str] = None

class DispensePrescriptionRequest(BaseModel):
    patient_id: UUID
    prescription_id: Optional[UUID] = None
    encounter_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    items: List[DispenseItemRequest] = Field(min_length=1, max_length=100)
    notes: Optional[str] = None
    dispensing_reference: str = Field(min_length=8, max_length=100)


class PrescriptionAmendRequest(BaseModel):
    prescription_item_id: UUID
    replacement_drug_id: UUID
    reason: str = Field(min_length=3, max_length=1000)


class PrescriptionCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)

class DispensedItemResponse(BaseModel):
    dispensing_item_id: UUID
    drug_id: UUID
    generic_name: str
    batch_number: str
    quantity_dispensed: float
    unit_price: float
    total_price: float

class DispensingRecordResponse(BaseModel):
    dispensing_record_id: UUID
    patient_id: UUID
    patient_name: str
    mrn: str
    dispensing_date: datetime
    dispensing_status: str
    total_amount: float
    items: List[DispensedItemResponse] = []
    notes: Optional[str] = None
