from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models import Notification, User
from ..schemas.notification import NotificationRead

def list_user_notifications(session: Session, user: User, unread_only: bool = False) -> list[NotificationRead]:
    query = select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    notifications = session.scalars(query).all()
    return notifications


def mark_notification_as_read(session: Session, notification_id: int, user: User) -> NotificationRead:
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this notification")
    
    notification.is_read = True
    session.flush()
    return notification


def mark_all_as_read(session: Session, user: User) -> dict:
    stmt = (
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    result = session.execute(stmt)
    session.flush()
    return {"status": "success", "updated_count": result.rowcount}
