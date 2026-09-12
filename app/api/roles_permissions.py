import uuid
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import get_db
from app.api.auth import require_roles, CurrentUser, get_current_user, Role, Permission, RolePermission, User, UserRole, EMPLOYEE_PORTAL_ROLES
from app.models.employee import Employee
from app.schemas.admin_compliance import (
    PermissionResponse, RolePermissionAssignRequest, RoleWithPermissionsResponse, PermissionAssignmentResult
)

router = APIRouter(prefix="/security", tags=["Security & Role-Permission Manager"])

class EmployeeRoleAssignment(BaseModel):
    roles: List[str]

@router.get("/employees/role-assignments")
async def list_employee_role_assignments(db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["super_admin", "admin", "hr_manager"]))):
    rows = (await db.execute(select(Employee, User).join(User, User.employee_id == Employee.employee_id).order_by(Employee.first_name, Employee.last_name))).all()
    result = []
    for employee, user in rows:
        roles = (await db.execute(select(Role.role_name).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user.user_id).order_by(Role.role_name))).scalars().all()
        result.append({"employee_id": str(employee.employee_id), "employee_number": employee.employee_number,
                       "employee_name": f"{employee.first_name or ''} {employee.last_name or ''}".strip(),
                       "department_id": str(employee.department_id) if employee.department_id else None,
                       "sub_department_id": str(employee.sub_department_id) if employee.sub_department_id else None,
                       "account_status": user.status, "roles": list(roles)})
    return {"employees": result, "available_roles": sorted(EMPLOYEE_PORTAL_ROLES)}

@router.put("/employees/{employee_id}/roles")
async def replace_employee_roles(employee_id: uuid.UUID, req: EmployeeRoleAssignment, db: AsyncSession = Depends(get_db), cu: CurrentUser = Depends(require_roles(["super_admin", "admin"]))):
    requested = set(req.roles)
    invalid = sorted(requested - EMPLOYEE_PORTAL_ROLES)
    if invalid:
        raise HTTPException(400, f"Roles do not have an employee portal: {', '.join(invalid)}")
    user = (await db.execute(select(User).where(User.employee_id == employee_id))).scalars().first()
    if not user:
        raise HTTPException(404, "Employee login account not found")
    current_roles = set((await db.execute(
        select(Role.role_name).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user.user_id)
    )).scalars().all())
    if "super_admin" not in cu.roles and ("super_admin" in requested or "super_admin" in current_roles):
        raise HTTPException(403, "Only a super administrator can assign or modify the super_admin role")
    if user.user_id == cu.user_id and not requested.intersection({"admin", "super_admin", "hr_manager"}):
        raise HTTPException(400, "You cannot remove your own final Admin Portal role")
    roles = (await db.execute(select(Role).where(Role.role_name.in_(requested)))).scalars().all() if requested else []
    if len(roles) != len(requested):
        raise HTTPException(400, "One or more requested roles do not exist")
    await db.execute(delete(UserRole).where(UserRole.user_id == user.user_id))
    for role in roles:
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    await db.commit()
    return {"employee_id": str(employee_id), "roles": sorted(requested), "message": "Employee roles updated successfully"}


@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """List all available system roles."""
    res = await db.execute(select(Role).order_by(Role.role_name))
    roles = res.scalars().all()
    return [{"role_id": str(r.role_id), "role_name": r.role_name} for r in roles]


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """List all granular system permissions."""
    res = await db.execute(select(Permission).order_by(Permission.module, Permission.permission_name))
    permissions = res.scalars().all()
    return permissions


@router.get("/roles/{role_id}/permissions", response_model=RoleWithPermissionsResponse)
async def get_role_permissions(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Get all permissions assigned to a specific role."""
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")

    res = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.module, Permission.permission_name)
    )
    perms = res.scalars().all()

    return RoleWithPermissionsResponse(
        role_id=role.role_id,
        role_name=role.role_name,
        permissions=perms
    )


@router.post("/roles/{role_id}/permissions", response_model=PermissionAssignmentResult)
async def assign_role_permissions(
    role_id: uuid.UUID,
    req: RolePermissionAssignRequest,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(require_roles(["super_admin", "admin"]))
):
    """Assign/update granted permissions for a role."""
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")

    # Clear current permissions
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))

    # Add selected permissions
    count = 0
    for pid in set(req.permission_ids):
        perm = await db.get(Permission, pid)
        if perm:
            rp = RolePermission(role_id=role_id, permission_id=pid)
            db.add(rp)
            count += 1

    await db.commit()

    return PermissionAssignmentResult(
        role_id=role.role_id,
        role_name=role.role_name,
        granted_permissions_count=count,
        message=f"Successfully assigned {count} permissions to role {role.role_name}"
    )
