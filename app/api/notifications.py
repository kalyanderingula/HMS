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
    sql = """
        SELECT notifications.notification_id, notifications.recipient_id,
               notifications.recipient_type, notifications.source_module,
               notifications.source_reference_id, notifications.subject,
               notifications.body, notifications.status, notifications.sent_at,
               notifications.created_at,
               CASE WHEN notifications.recipient_type='Role' THEN receipt.read_at ELSE notifications.read_at END AS read_at
        FROM core.notifications
        LEFT JOIN core.notification_read_receipts receipt
          ON receipt.notification_id=notifications.notification_id AND receipt.user_id=:user_id
        WHERE (recipient_type = 'User' AND recipient_id = :user_id)
           OR (recipient_type = 'Role' AND recipient_id IN (
                SELECT r.role_id FROM security.roles r WHERE lower(r.role_name) = ANY(CAST(:roles AS text[]))
              ))
        ORDER BY notifications.created_at DESC
        LIMIT 50
    """
    rows = (await db.execute(text(sql), {"user_id": cu.user_id, "roles": user_roles})).mappings().all()

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
    roles = [role.lower() for role in (cu.roles or [])]
    recipient_type = await db.scalar(text("""SELECT recipient_type FROM core.notifications
        WHERE notification_id=:id AND (
            (recipient_type='User' AND recipient_id=:user_id)
            OR (recipient_type='Role' AND recipient_id IN (
                SELECT role_id FROM security.roles WHERE lower(role_name)=ANY(CAST(:roles AS text[]))
            )))"""), {"id": notification_id, "user_id": cu.user_id, "roles": roles})
    if not recipient_type:
        raise HTTPException(404, "Notification not found")
    if recipient_type == "Role":
        await db.execute(text("""INSERT INTO core.notification_read_receipts(notification_id,user_id)
            VALUES(:id,:user_id) ON CONFLICT(notification_id,user_id)
            DO UPDATE SET read_at=CURRENT_TIMESTAMP"""), {"id": notification_id, "user_id": cu.user_id})
    else:
        await db.execute(text("""UPDATE core.notifications SET status='read',read_at=CURRENT_TIMESTAMP
            WHERE notification_id=:id AND recipient_type='User' AND recipient_id=:user_id"""),
            {"id": notification_id, "user_id": cu.user_id})
    await db.commit()
    return {"message": "Notification marked as read", "notification_id": str(notification_id)}


@router.post("/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    cu: CurrentUser = Depends(get_current_user)
):
    """Mark all active notifications for the current user/role as read."""
    roles = [role.lower() for role in (cu.roles or [])]
    await db.execute(
        text("""UPDATE core.notifications SET status='read',read_at=CURRENT_TIMESTAMP
                WHERE recipient_type='User' AND recipient_id=:user_id
                  AND (status!='read' OR read_at IS NULL)"""), {"user_id": cu.user_id}
    )
    await db.execute(
        text("""INSERT INTO core.notification_read_receipts(notification_id,user_id)
                SELECT notification_id,:user_id FROM core.notifications
                WHERE recipient_type='Role' AND recipient_id IN (
                    SELECT role_id FROM security.roles WHERE lower(role_name)=ANY(CAST(:roles AS text[])))
                ON CONFLICT(notification_id,user_id) DO UPDATE SET read_at=CURRENT_TIMESTAMP"""),
        {"user_id": cu.user_id, "roles": roles}
    )
    await db.commit()
    return {"message": "All notifications marked as read"}

