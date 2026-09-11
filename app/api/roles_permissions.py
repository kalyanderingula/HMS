import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import get_db
from app.api.auth import require_roles, CurrentUser, get_current_user, Role, Permission, RolePermission
from app.schemas.admin_compliance import (
    PermissionResponse, RolePermissionAssignRequest, RoleWithPermissionsResponse, PermissionAssignmentResult
)

router = APIRouter(prefix="/security", tags=["Security & Role-Permission Manager"])


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
