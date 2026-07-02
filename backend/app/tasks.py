import logging

from sqlalchemy.exc import SQLAlchemyError

from .core.celery_app import celery_app
from .db.session import SessionLocal
from .models import Notification, NotificationType

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def send_notification(self, user_id: int, title: str, message: str, notification_type: str) -> dict:
    """
    Background task to send a notification to a user.
    In a real-world scenario, this might trigger an email or push notification via an external service.
    For this phase, it simply persists the notification in the database.
    """
    logger.info(f"Sending {notification_type} notification to user {user_id}: {title}")
    
    db = SessionLocal()
    try:
        # Validate notification type
        try:
            ntype = NotificationType(notification_type)
        except ValueError:
            logger.error(f"Invalid notification type: {notification_type}")
            return {"status": "failed", "reason": "invalid notification type"}

        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=ntype,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        logger.info(f"Notification {notification.id} saved to database for user {user_id}")
        return {"status": "success", "notification_id": notification.id}
    except SQLAlchemyError as e:
        logger.error(f"Database error while saving notification for user {user_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Unexpected error while sending notification: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
