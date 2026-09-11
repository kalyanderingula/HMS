import uuid
from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== HR SHIFT ROSTERING SCHEMAS ====================

class ShiftScheduleResponse(BaseModel):
    shift_schedule_id: uuid.UUID
    shift_code: str
    shift_name: str
    shift_start_time: time
    shift_end_time: time
    is_night_shift: bool
    is_active: bool

    class Config:
        from_attributes = True


class DutyRosterCreate(BaseModel):
    employee_id: uuid.UUID
    shift_schedule_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    roster_date: date
    notes: Optional[str] = None


class DutyRosterResponse(BaseModel):
    employee_roster_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: Optional[str] = None
    employee_number: Optional[str] = None
    shift_schedule_id: uuid.UUID
    shift_name: Optional[str] = None
    shift_code: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    roster_date: date
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== ROLE & PERMISSION SCHEMAS ====================

class PermissionResponse(BaseModel):
    permission_id: uuid.UUID
    permission_code: str
    permission_name: str
    module: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RolePermissionAssignRequest(BaseModel):
    permission_ids: List[uuid.UUID]


class RoleWithPermissionsResponse(BaseModel):
    role_id: uuid.UUID
    role_name: str
    permissions: List[PermissionResponse]

    class Config:
        from_attributes = True


class PermissionAssignmentResult(BaseModel):
    role_id: uuid.UUID
    role_name: str
    granted_permissions_count: int
    message: str
