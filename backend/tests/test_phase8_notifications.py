"""Phase 8 Notification System Tests.

Tests cover:
- Background task execution for notifications
- DB persistence via task
- GET /notifications (all and unread only)
- PATCH /notifications/{id}/read
- POST /notifications/read-all
- Security and ownership checks
"""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

os.environ["JWT_SECRET_KEY"] = "test-secret-key-must-be-at-least-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

from app.core.config import get_settings

get_settings.cache_clear()

from sqlalchemy import create_engine, event, StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.db.base import Base
from app.models import (
    Notification,
    User,
    UserRole,
)
from app.core.celery_app import celery_app

# Run celery tasks synchronously in the same thread
celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

# -- Shared in-memory SQLite --
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


def get_test_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


from app.api.deps import get_database_session  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

app.dependency_overrides[get_database_session] = get_test_db
app.dependency_overrides[get_db] = get_test_db

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)


def _auth_header(user_id: int) -> dict[str, str]:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _seed():
    session = TestSession()
    user1 = User(name="User One", email="u1@test.com", password_hash="x", role=UserRole.STUDENT)
    user2 = User(name="User Two", email="u2@test.com", password_hash="x", role=UserRole.STUDENT)

    session.add_all([user1, user2])
    session.commit()

    result = {
        "user1_id": user1.id,
        "user2_id": user2.id,
    }
    session.close()
    return result


data = _seed()

passed = 0
failed = 0
errors = []


def test(name):
    def decorator(fn):
        global passed, failed
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"  FAIL  {name}: {e}")
    return decorator


print()
print("=" * 60)
print("  PHASE 8 NOTIFICATION SYSTEM TESTS")
print("=" * 60)

print()
print("-- Background Task --")

@test("Celery task creates notification in database")
def _():
    from app.tasks import send_notification

    # Patch SessionLocal to use TestSession for the background task
    with patch("app.tasks.SessionLocal", new=TestSession):
        res = send_notification.delay(
            user_id=data["user1_id"],
            title="New Assignment",
            message="Check out the new assignment.",
            notification_type="assignment"
        )
        assert res.successful()
        result = res.get()
        assert result["status"] == "success"
        
        session = TestSession()
        notif = session.get(Notification, result["notification_id"])
        assert notif is not None
        assert notif.title == "New Assignment"
        assert notif.type == "assignment"
        assert notif.user_id == data["user1_id"]
        assert notif.is_read is False
        session.close()


print()
print("-- API Endpoints --")

@test("GET /notifications returns user notifications")
def _():
    h = _auth_header(data["user1_id"])
    r = client.get("/api/v1/notifications", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "New Assignment"

@test("GET /notifications?unread_only=true returns unread notifications")
def _():
    h = _auth_header(data["user1_id"])
    r = client.get("/api/v1/notifications?unread_only=true", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

@test("PATCH /notifications/{id}/read marks notification as read")
def _():
    h = _auth_header(data["user1_id"])
    r = client.get("/api/v1/notifications", headers=h)
    notif_id = r.json()[0]["id"]
    
    r2 = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=h)
    assert r2.status_code == 200
    assert r2.json()["is_read"] is True

@test("Unread only filter works after marking read")
def _():
    h = _auth_header(data["user1_id"])
    r = client.get("/api/v1/notifications?unread_only=true", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 0  # Should be 0 since we marked it read

@test("Cannot mark another user's notification as read")
def _():
    # User 1 has the notification
    h1 = _auth_header(data["user1_id"])
    r1 = client.get("/api/v1/notifications", headers=h1)
    notif_id = r1.json()[0]["id"]

    # User 2 tries to mark it
    h2 = _auth_header(data["user2_id"])
    r2 = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=h2)
    assert r2.status_code == 403

@test("POST /notifications/read-all marks all unread as read")
def _():
    from app.tasks import send_notification

    # Create two more notifications for User 2
    with patch("app.tasks.SessionLocal", new=TestSession):
        send_notification.delay(data["user2_id"], "N1", "M1", "system")
        send_notification.delay(data["user2_id"], "N2", "M2", "system")
        
    h = _auth_header(data["user2_id"])
    r = client.get("/api/v1/notifications?unread_only=true", headers=h)
    assert len(r.json()) == 2
    
    r2 = client.post("/api/v1/notifications/read-all", headers=h)
    assert r2.status_code == 200
    assert r2.json()["updated_count"] == 2
    
    r3 = client.get("/api/v1/notifications?unread_only=true", headers=h)
    assert len(r3.json()) == 0

print()
print("=" * 60)
print(f"  RESULTS:  {passed} passed,  {failed} failed")
print("=" * 60)

if errors:
    print()
    print("  FAILURES:")
    for name, msg in errors:
        print(f"    X {name}")
        print(f"      {msg}")
        print()

sys.exit(1 if failed else 0)
