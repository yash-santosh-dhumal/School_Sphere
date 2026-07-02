from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from ..models import NotificationType

class NotificationRead(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
