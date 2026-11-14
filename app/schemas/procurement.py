from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RequestItem(BaseModel):
    inventory_item_id: UUID
    requested_quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    estimated_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    justification: str | None = Field(default=None, max_length=2000)


class PurchaseRequestCreate(BaseModel):
    requested_department: str = Field(min_length=2, max_length=255)
    required_by: date
    request_notes: str | None = Field(default=None, max_length=4000)
    items: list[RequestItem] = Field(min_length=1)


class DecisionCreate(BaseModel):
    approved: bool
    notes: str | None = Field(default=None, max_length=2000)


class CancelRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=2000)


class VendorCreate(BaseModel):
    vendor_code: str = Field(min_length=2, max_length=100)
    vendor_name: str = Field(min_length=2, max_length=255)
    vendor_type: str | None = Field(default=None, max_length=100)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    vendor_address: str | None = Field(default=None, max_length=2000)


class VendorUpdate(BaseModel):
    vendor_name: str | None = Field(default=None, min_length=2, max_length=255)
    vendor_type: str | None = Field(default=None, max_length=100)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    vendor_address: str | None = Field(default=None, max_length=2000)


class InventoryItemUpdate(BaseModel):
    item_name: str | None = Field(default=None, min_length=2, max_length=255)
    item_description: str | None = Field(default=None, max_length=4000)
    reorder_level: int | None = Field(default=None, ge=0)
    minimum_stock_level: int | None = Field(default=None, ge=0)
    maximum_stock_level: int | None = Field(default=None, ge=0)


class QuoteCreate(BaseModel):
    vendor_id: UUID
    quote_number: str = Field(min_length=2, max_length=100)
    quoted_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    delivery_days: int = Field(ge=0, le=3650)
    quote_notes: str | None = Field(default=None, max_length=2000)


class PurchaseOrderCreate(BaseModel):
    vendor_quote_id: UUID
    expected_delivery_date: date


class ReceiptItem(BaseModel):
    inventory_item_id: UUID
    received_quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    accepted_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    rejected_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def validate_quantities(self):
        if self.accepted_quantity + self.rejected_quantity != self.received_quantity:
            raise ValueError("Accepted and rejected quantities must equal received quantity")
        return self


class GoodsReceiptCreate(BaseModel):
    warehouse_id: UUID
    items: list[ReceiptItem] = Field(min_length=1)
