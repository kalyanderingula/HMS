from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ICUAdmissionCreate(BaseModel):
    patient_id: UUID
    icu_bed_id: UUID
    triage_level_id: UUID | None = None
    criticality_level: str = Field(min_length=2, max_length=100)
    primary_diagnosis: str = Field(min_length=2, max_length=4000)
    admission_source: str = Field(min_length=2, max_length=255)
    admission_reason: str = Field(min_length=2, max_length=4000)
    referring_doctor_id: UUID | None = None
    attending_doctor_id: UUID | None = None


class ICUAdmissionUpdate(BaseModel):
    triage_level_id: UUID | None = None
    referring_doctor_id: UUID | None = None
    attending_doctor_id: UUID | None = None
    criticality_level: str | None = Field(default=None, min_length=2, max_length=100)
    primary_diagnosis: str | None = Field(default=None, min_length=2, max_length=4000)
    admission_source: str | None = Field(default=None, min_length=2, max_length=255)
    admission_reason: str | None = Field(default=None, min_length=2, max_length=4000)


class ICUCancellationCreate(BaseModel):
    reason: str = Field(min_length=2, max_length=4000)


class ICUVitalsAmend(BaseModel):
    temperature: float | None = Field(default=None, ge=25, le=45)
    pulse_rate: int | None = Field(default=None, ge=0, le=300)
    respiratory_rate: int | None = Field(default=None, ge=0, le=100)
    systolic_bp: int | None = Field(default=None, ge=0, le=300)
    diastolic_bp: int | None = Field(default=None, ge=0, le=200)
    oxygen_saturation: float | None = Field(default=None, ge=0, le=100)
    amendment_reason: str = Field(min_length=2, max_length=1000)


class ICUVoidCreate(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class ICUVitalsCreate(BaseModel):
    temperature: float | None = Field(default=None, ge=25, le=45)
    pulse_rate: int | None = Field(default=None, ge=0, le=300)
    respiratory_rate: int | None = Field(default=None, ge=0, le=100)
    systolic_bp: int | None = Field(default=None, ge=0, le=300)
    diastolic_bp: int | None = Field(default=None, ge=0, le=200)
    oxygen_saturation: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def require_measurement(self):
        if all(getattr(self, name) is None for name in type(self).model_fields):
            raise ValueError("At least one vital-sign measurement is required")
        return self


class ICUVentilatorCreate(BaseModel):
    ventilator_device_id: str = Field(min_length=1, max_length=255)
    ventilation_mode: str = Field(min_length=1, max_length=255)


class ICURoundCreate(BaseModel):
    round_notes: str = Field(min_length=2, max_length=8000)


class ICUAlertCreate(BaseModel):
    alert_type: str = Field(min_length=2, max_length=255)
    alert_message: str = Field(min_length=2, max_length=4000)
    source: Literal["clinical", "device"] = "clinical"
    device_identifier: str | None = Field(default=None, max_length=255)


class ICUDispositionCreate(BaseModel):
    discharge_condition: str = Field(min_length=2, max_length=255)
    discharge_summary: str = Field(min_length=2, max_length=8000)


class ICUDischargeRequestCreate(BaseModel):
    proposed_condition: str = Field(min_length=2, max_length=255)
    proposed_summary: str = Field(min_length=2, max_length=8000)
    request_notes: str | None = Field(default=None, max_length=4000)


class ICUDischargeReview(BaseModel):
    approved: bool
    review_notes: str | None = Field(default=None, max_length=4000)


class ICUTransferCreate(BaseModel):
    to_unit_id: UUID
    to_bed_id: UUID
    transfer_reason: str = Field(min_length=2, max_length=4000)
