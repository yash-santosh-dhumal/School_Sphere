from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ...api.deps import get_current_user, get_database_session
from ...models import User
from ...schemas.notification import NotificationRead
from ...services.notification_service import (
    list_user_notifications,
    mark_all_as_read,
    mark_notification_as_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def get_notifications(
    unread_only: bool = Query(default=False),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_database_session),
) -> list[NotificationRead]:
    return list_user_notifications(session, user, unread_only)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_database_session),
) -> NotificationRead:
    result = mark_notification_as_read(session, notification_id, user)
    session.commit()
    return result


@router.post("/read-all", status_code=status.HTTP_200_OK)
def read_all_notifications(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_database_session),
) -> dict:
    result = mark_all_as_read(session, user)
    session.commit()
    return result
