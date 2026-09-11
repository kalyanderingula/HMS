import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ==================== BLOOD BANK SCHEMAS ====================

class BloodDonorCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    blood_group_name: str = Field(min_length=1, max_length=10)  # e.g., 'A+', 'O-'
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None


class BloodDonorResponse(BaseModel):
    blood_donor_id: uuid.UUID
    donor_number: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    blood_group: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    total_donations: int
    is_eligible: bool
    created_at: datetime


class DonorEligibilityCreate(BaseModel):
    hemoglobin: Decimal = Field(ge=5.0, le=25.0)  # Standard eligibility >= 12.5
    weight: Decimal = Field(ge=30.0, le=250.0)    # Standard eligibility >= 50.0
    blood_pressure: str = Field(max_length=20)   # e.g., "120/80"
    temperature: Optional[Decimal] = Field(None, ge=95.0, le=105.0)
    pulse: Optional[int] = Field(None, ge=40, le=180)
    screening_passed: bool = True
    rejection_reason: Optional[str] = None


class DonorEligibilityResponse(BaseModel):
    eligibility_check_id: uuid.UUID
    blood_donor_id: uuid.UUID
    check_date: datetime
    hemoglobin: Decimal
    weight: Decimal
    blood_pressure: str
    is_eligible: bool
    rejection_reason: Optional[str]


class BloodDonationCreate(BaseModel):
    blood_donor_id: uuid.UUID
    donation_type: str = "Voluntary"
    volume_ml: int = Field(default=450, ge=300, le=500)
    notes: Optional[str] = None


class BloodDonationResponse(BaseModel):
    blood_donation_id: uuid.UUID
    blood_donor_id: uuid.UUID
    bag_number: str
    volume_ml: int
    donation_type: str
    status: str
    donation_date: datetime


class ComponentSeparationRequest(BaseModel):
    components: List[Literal["PRBC", "FFP", "Platelets", "Cryoprecipitate"]] = ["PRBC", "FFP", "Platelets"]


class SeparatedUnitItem(BaseModel):
    blood_unit_id: uuid.UUID
    unit_number: str
    component_name: str
    volume_ml: int
    expiry_date: date
    status: str


class ComponentSeparationResponse(BaseModel):
    blood_donation_id: uuid.UUID
    source_bag_number: str
    separated_units: List[SeparatedUnitItem]


class BloodUnitTestCreate(BaseModel):
    test_name: Literal["HIV 1&2", "Hepatitis B (HBsAg)", "Hepatitis C (HCV)", "Syphilis (VDRL)", "Malaria"]
    result: Literal["Negative", "Reactive", "Indeterminate"]
    notes: Optional[str] = None


class BloodUnitTestResponse(BaseModel):
    unit_test_id: uuid.UUID
    blood_unit_id: uuid.UUID
    test_name: str
    result: str
    tested_at: datetime
    unit_status_now: str


# ==================== PHARMACY SCHEMAS ====================

class BulkDispenseItem(BaseModel):
    prescription_item_id: uuid.UUID
    drug_id: uuid.UUID
    batch_id: uuid.UUID
    quantity_dispensed: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class BulkDispenseRequest(BaseModel):
    patient_id: uuid.UUID
    prescription_id: uuid.UUID
    dispensing_reference: str = Field(min_length=3, max_length=255)
    items: List[BulkDispenseItem] = Field(min_length=1)
    notes: Optional[str] = None


class BulkDispenseResponse(BaseModel):
    dispensing_record_id: uuid.UUID
    prescription_id: uuid.UUID
    dispensing_reference: str
    dispensed_items_count: int
    total_amount: Decimal
    invoice_id: Optional[uuid.UUID]
    dispensing_status: str


class PharmacistReviewCreate(BaseModel):
    review_status: Literal["Approved", "Flagged", "Modified", "Rejected"] = "Approved"
    intervention_type: Literal[
        "Routine Cleared", "Dose Adjustment", "Drug Substitution",
        "Allergy Override", "Interaction Override"
    ] = "Routine Cleared"
    clinical_notes: Optional[str] = None


class PharmacistReviewResponse(BaseModel):
    review_id: uuid.UUID
    prescription_id: uuid.UUID
    pharmacist_id: uuid.UUID
    review_status: str
    intervention_type: str
    clinical_notes: Optional[str]
    reviewed_at: datetime


# ==================== BILLING / PAYMENT GATEWAY SCHEMAS ====================

class CheckoutSessionCreate(BaseModel):
    invoice_id: uuid.UUID
    gateway_provider: Literal["Stripe", "Razorpay", "UPI"] = "Stripe"
    currency: str = Field(default="INR", max_length=10)
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    transaction_id: uuid.UUID
    invoice_id: uuid.UUID
    gateway_provider: str
    gateway_session_id: str
    checkout_url: str
    amount: Decimal
    currency: str
    status: str


class PaymentWebhookPayload(BaseModel):
    gateway_session_id: str
    gateway_reference: str
    event_type: Literal["payment.succeeded", "payment.failed", "checkout.session.completed"]
    signature: str
    paid_amount: Decimal


class PaymentWebhookResponse(BaseModel):
    status: str
    transaction_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_settled: bool
    message: str


class InsurancePreauthCreate(BaseModel):
    patient_id: uuid.UUID
    insurance_provider: str = Field(min_length=2, max_length=255)
    policy_number: str = Field(min_length=2, max_length=255)
    authorized_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    copay_percentage: Decimal = Field(default=0, ge=0, le=100)
    valid_from: date
    valid_until: date


class InsurancePreauthResponse(BaseModel):
    preauth_id: uuid.UUID
    patient_id: uuid.UUID
    insurance_provider: str
    policy_number: str
    approval_code: str
    authorized_amount: Decimal
    copay_percentage: Decimal
    valid_from: date
    valid_until: date
    status: str


# ==================== TELEMEDICINE SCHEMAS ====================

class VideoRoomResponse(BaseModel):
    room_id: uuid.UUID
    virtual_appointment_id: uuid.UUID
    room_name: str
    room_url: str
    host_token: str
    participant_token: str
    is_active: bool


class InSessionOrderRequest(BaseModel):
    virtual_appointment_id: uuid.UUID
    order_type: Literal["prescription", "laboratory", "radiology"]
    details: str
    item_catalog_ids: List[uuid.UUID] = []


class InSessionOrderResponse(BaseModel):
    order_type: str
    linked_encounter_id: Optional[uuid.UUID]
    reference_id: uuid.UUID
    message: str
