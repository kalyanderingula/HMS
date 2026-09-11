import uuid
from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text

from app.config import get_db
from app.api.auth import require_roles, CurrentUser, get_current_user
from app.models.employee import Employee, ShiftSchedule, EmployeeRoster
from app.models.department import Department
from app.schemas.admin_compliance import (
    ShiftScheduleResponse, DutyRosterCreate, DutyRosterResponse
)

router = APIRouter(prefix="/rosters", tags=["HR Shift Duty Rostering"])


@router.get("/shifts", response_model=List[ShiftScheduleResponse])
async def list_shifts(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """List all configured work shift schedules."""
    res = await db.execute(select(ShiftSchedule).order_by(ShiftSchedule.shift_start_time))
    shifts = res.scalars().all()
    return shifts


@router.get("", response_model=List[DutyRosterResponse])
async def list_duty_rosters(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    department_id: Optional[uuid.UUID] = None,
    employee_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """List employee shift duty rosters with optional filtering."""
    q = select(EmployeeRoster).order_by(desc(EmployeeRoster.roster_date))
    if date_from:
        q = q.where(EmployeeRoster.roster_date >= date_from)
    if date_to:
        q = q.where(EmployeeRoster.roster_date <= date_to)
    if department_id:
        q = q.where(EmployeeRoster.department_id == department_id)
    if employee_id:
        q = q.where(EmployeeRoster.employee_id == employee_id)

    res = await db.execute(q.limit(100))
    rosters = res.scalars().all()

    results = []
    for r in rosters:
        emp = await db.get(Employee, r.employee_id)
        shift = await db.get(ShiftSchedule, r.shift_schedule_id)
        dept = await db.get(Department, r.department_id) if r.department_id else None
        results.append(DutyRosterResponse(
            employee_roster_id=r.employee_roster_id,
            employee_id=r.employee_id,
            employee_name=f"{emp.first_name} {emp.last_name}" if emp else None,
            employee_number=emp.employee_number if emp else None,
            shift_schedule_id=r.shift_schedule_id,
            shift_name=shift.shift_name if shift else None,
            shift_code=shift.shift_code if shift else None,
            department_id=r.department_id,
            department_name=dept.department_name if dept else None,
            roster_date=r.roster_date,
            notes=r.notes,
            created_at=r.created_at
        ))
    return results


@router.post("", response_model=DutyRosterResponse, status_code=201)
async def assign_duty_roster(
    req: DutyRosterCreate,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["admin", "super_admin", "hr_manager"]))
):
    """Assign an employee to a duty shift with conflict & double-booking prevention."""
    emp = await db.get(Employee, req.employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")

    shift = await db.get(ShiftSchedule, req.shift_schedule_id)
    if not shift:
        raise HTTPException(404, "Shift schedule not found")

    # Conflict Check: verify employee is not already scheduled on this date
    existing = await db.scalar(
        select(EmployeeRoster).where(
            EmployeeRoster.employee_id == req.employee_id,
            EmployeeRoster.roster_date == req.roster_date
        )
    )
    if existing:
        ex_shift = await db.get(ShiftSchedule, existing.shift_schedule_id)
        shift_desc = ex_shift.shift_name if ex_shift else "another shift"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scheduling Conflict: {emp.first_name} {emp.last_name} is already scheduled for {shift_desc} on {req.roster_date}"
        )

    dept_id = req.department_id or emp.department_id
    roster = EmployeeRoster(
        employee_id=req.employee_id,
        shift_schedule_id=req.shift_schedule_id,
        department_id=dept_id,
        roster_date=req.roster_date,
        notes=req.notes
    )
    db.add(roster)
    await db.commit()
    await db.refresh(roster)

    dept = await db.get(Department, dept_id) if dept_id else None

    return DutyRosterResponse(
        employee_roster_id=roster.employee_roster_id,
        employee_id=roster.employee_id,
        employee_name=f"{emp.first_name} {emp.last_name}",
        employee_number=emp.employee_number,
        shift_schedule_id=roster.shift_schedule_id,
        shift_name=shift.shift_name,
        shift_code=shift.shift_code,
        department_id=roster.department_id,
        department_name=dept.department_name if dept else None,
        roster_date=roster.roster_date,
        notes=roster.notes,
        created_at=roster.created_at
    )


@router.delete("/{roster_id}")
async def delete_duty_roster(
    roster_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["admin", "super_admin", "hr_manager"]))
):
    """Remove a scheduled duty roster assignment."""
    roster = await db.get(EmployeeRoster, roster_id)
    if not roster:
        raise HTTPException(404, "Duty roster not found")

    await db.delete(roster)
    await db.commit()
    return {"message": "Duty roster assignment cancelled successfully"}
