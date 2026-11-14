from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DispatchCreate(BaseModel):
    patient_id: UUID
    request_source: str = Field(min_length=2, max_length=255)
    emergency_type: str = Field(min_length=2, max_length=255)
    pickup_location: str = Field(min_length=2, max_length=2000)
    destination_location: str = Field(min_length=2, max_length=2000)


class DispatchUpdate(BaseModel):
    request_source: str | None = Field(default=None, min_length=2, max_length=255)
    emergency_type: str | None = Field(default=None, min_length=2, max_length=255)
    pickup_location: str | None = Field(default=None, min_length=2, max_length=2000)
    destination_location: str | None = Field(default=None, min_length=2, max_length=2000)


class CancelCreate(BaseModel):
    reason: str = Field(min_length=2, max_length=2000)


class AmbulanceUpdate(BaseModel):
    registration_number: str | None = Field(default=None, max_length=100)
    current_status: Literal["Available", "Maintenance", "Out of Service"] | None = None
    gps_enabled: bool | None = None


class EquipmentUpdate(BaseModel):
    equipment_name: str | None = Field(default=None, min_length=2, max_length=255)
    equipment_quantity: int | None = Field(default=None, ge=0, le=10000)
    equipment_status: str | None = Field(default=None, min_length=2, max_length=100)


class DispatchAssign(BaseModel):
    ambulance_id: UUID
    dispatch_priority_id: UUID


class DispatchStatusUpdate(BaseModel):
    status: Literal["Assigned", "En Route", "At Scene", "Patient Onboard", "Arrived", "Completed", "Cancelled"]
    notes: str | None = Field(default=None, max_length=4000)
    patient_condition: str | None = Field(default=None, max_length=1000)
    distance_km: float | None = Field(default=None, ge=0, le=10000)


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed: float | None = Field(default=None, ge=0, le=300)


class EquipmentCreate(BaseModel):
    equipment_name: str = Field(min_length=2, max_length=255)
    equipment_quantity: int = Field(ge=0, le=10000)
    equipment_status: str = Field(min_length=2, max_length=100)


class MaintenanceCreate(BaseModel):
    maintenance_type: str = Field(min_length=2, max_length=100)
    maintenance_notes: str = Field(min_length=2, max_length=4000)
    next_maintenance_date: date | None = None
