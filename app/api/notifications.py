import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from pydantic import BaseModel

from app.config import get_db
from app.api.auth import get_current_user, CurrentUser

router = APIRouter(prefix="/notifications", tags=["Global Staff Notifications"])


class NotificationItem(BaseModel):
    notification_id: str
    source_module: str
    source_reference_id: Optional[str] = None
    subject: str
    body: Optional[str] = None
    status: str
    is_urgent: bool = False
    created_at: Optional[str] = None
    read_at: Optional[str] = None


class NotificationListResponse(BaseModel):
    unread_count: int
    notifications: List[NotificationItem]


@router.get("/my", response_model=NotificationListResponse)
async def get_my_notifications(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Retrieve all notifications targeted to the logged-in user or their roles."""
    user_roles = [r.lower() for r in (cu.roles or [])]
    # Check if admin/super_admin
    is_admin = any(r in ["admin", "super_admin"] for r in user_roles)

    sql = """
        SELECT notification_id, recipient_id, recipient_type, source_module,
               source_reference_id, subject, body, status, sent_at, created_at, read_at
        FROM core.notifications
        WHERE (recipient_id = :user_id)
           OR (recipient_type = 'User' AND recipient_id = :user_id)
           OR (recipient_type = 'Role')
           OR (:is_admin = true)
        ORDER BY created_at DESC
        LIMIT 50
    """
    rows = (await db.execute(text(sql), {"user_id": cu.user_id, "is_admin": is_admin})).mappings().all()

    items = []
    unread = 0
    for r in rows:
        is_read = r["status"] == "read" or r["read_at"] is not None
        if not is_read:
            unread += 1
        subj = r["subject"] or ""
        is_urgent = "critical" in subj.lower() or "urgent" in subj.lower() or "alert" in subj.lower()
        items.append(NotificationItem(
            notification_id=str(r["notification_id"]),
            source_module=r["source_module"],
            source_reference_id=str(r["source_reference_id"]) if r["source_reference_id"] else None,
            subject=subj,
            body=r["body"],
            status="read" if is_read else (r["status"] or "pending"),
            is_urgent=is_urgent,
            created_at=r["created_at"].isoformat() if r["created_at"] else None,
            read_at=r["read_at"].isoformat() if r["read_at"] else None
        ))

    return NotificationListResponse(unread_count=unread, notifications=items)


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Mark a specific notification as read."""
    await db.execute(
        text("UPDATE core.notifications SET status = 'read', read_at = CURRENT_TIMESTAMP WHERE notification_id = :id"),
        {"id": notification_id}
    )
    await db.commit()
    return {"message": "Notification marked as read", "notification_id": str(notification_id)}


@router.post("/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Mark all active notifications for the current user/role as read."""
    is_admin = any(r in ["admin", "super_admin"] for r in (cu.roles or []))
    await db.execute(
        text("""UPDATE core.notifications
                SET status = 'read', read_at = CURRENT_TIMESTAMP
                WHERE (recipient_id = :user_id OR recipient_type = 'Role' OR :is_admin = true)
                  AND (status != 'read' OR read_at IS NULL)"""),
        {"user_id": cu.user_id, "is_admin": is_admin}
    )
    await db.commit()
    return {"message": "All notifications marked as read"}

