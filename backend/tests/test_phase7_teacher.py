"""Comprehensive Phase 7 Teacher Module Tests.

Tests cover:
- Authentication & Authorization (RBAC)
- Teacher dashboard
- Attendance: bulk marking, editing, class isolation
- Assignments: CRUD, ownership, cross-teacher isolation, submissions
- Examinations & Marks: create, bulk entry, ownership, duplicate rejection
- Notices: CRUD, ownership
- Response schema security (no password leaks)
"""
from __future__ import annotations

import json
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

os.environ["JWT_SECRET_KEY"] = "test-secret-key-must-be-at-least-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

from datetime import date, datetime, time, timedelta, timezone

from app.core.config import get_settings

get_settings.cache_clear()

from sqlalchemy import create_engine, event, StaticPool
from sqlalchemy.orm import sessionmaker

from app.admin_models import TeacherClassAssignment
from app.core.security import create_access_token
from app.db.base import Base
from app.models import (
    Assignment,
    Attendance,
    AttendanceStatus,
    Examination,
    Mark,
    Notice,
    SchoolClass,
    Student,
    Subject,
    Submission,
    Teacher,
    TimetableEntry,
    User,
    UserRole,
)

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

    school_class = SchoolClass(name="10", section="A", academic_year="2026")
    school_class_b = SchoolClass(name="11", section="B", academic_year="2026")
    subject = Subject(code="MATH101", name="Mathematics")
    subject2 = Subject(code="SCI101", name="Science")

    admin_user = User(name="Admin", email="admin@test.com", password_hash="x" * 64, role=UserRole.ADMIN)
    teacher_user_1 = User(name="Teacher One", email="t1@test.com", password_hash="x" * 64, role=UserRole.TEACHER)
    teacher_user_2 = User(name="Teacher Two", email="t2@test.com", password_hash="x" * 64, role=UserRole.TEACHER)
    student_user = User(name="Student One", email="s1@test.com", password_hash="x" * 64, role=UserRole.STUDENT)

    session.add_all([school_class, school_class_b, subject, subject2, admin_user, teacher_user_1, teacher_user_2, student_user])
    session.flush()

    teacher_1 = Teacher(user_id=teacher_user_1.id, department="Math", qualification="MSc", experience=5)
    teacher_2 = Teacher(user_id=teacher_user_2.id, department="Science", qualification="PhD", experience=10)
    student = Student(user_id=student_user.id, roll_no="10A-001", class_id=school_class.id, section="A", phone="1111", address="Addr1")

    session.add_all([teacher_1, teacher_2, student])
    session.flush()

    # Assign teacher 1 to class 10A, teacher 2 to class 11B
    tca1 = TeacherClassAssignment(teacher_id=teacher_1.id, class_id=school_class.id, subject_id=subject.id)
    tca2 = TeacherClassAssignment(teacher_id=teacher_2.id, class_id=school_class_b.id, subject_id=subject2.id)
    session.add_all([tca1, tca2])
    session.flush()

    # Pre-existing exam by teacher 1
    exam = Examination(subject_id=subject.id, class_id=school_class.id, teacher_id=teacher_1.id, exam_date=date(2026, 8, 1), title="Unit Test 1")
    session.add(exam)
    session.flush()

    session.commit()

    result = {
        "admin_id": admin_user.id,
        "teacher_1_id": teacher_user_1.id,
        "teacher_2_id": teacher_user_2.id,
        "student_id": student_user.id,
        "teacher_1_profile_id": teacher_1.id,
        "teacher_2_profile_id": teacher_2.id,
        "student_profile_id": student.id,
        "class_a_id": school_class.id,
        "class_b_id": school_class_b.id,
        "subject_id": subject.id,
        "subject2_id": subject2.id,
        "exam_id": exam.id,
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
print("=" * 65)
print("  PHASE 7 TEACHER MODULE - SECURITY & FUNCTIONAL TESTS")
print("=" * 65)

# ========================================
# 1. AUTHENTICATION
# ========================================
print()
print("-- Authentication --")

@test("Unauthenticated request returns 401")
def _():
    for ep in ["/api/v1/teacher/dashboard", "/api/v1/teacher/profile",
               "/api/v1/teacher/assignments", "/api/v1/teacher/examinations",
               "/api/v1/teacher/notices"]:
        r = client.get(ep)
        assert r.status_code in (401, 403), f"{ep} returned {r.status_code}"

@test("Invalid JWT returns 401")
def _():
    r = client.get("/api/v1/teacher/dashboard", headers={"Authorization": "Bearer bad.jwt.token"})
    assert r.status_code == 401

# ========================================
# 2. RBAC
# ========================================
print()
print("-- Authorization (RBAC) --")

@test("Student cannot access teacher endpoints")
def _():
    h = _auth_header(data["student_id"])
    r = client.get("/api/v1/teacher/dashboard", headers=h)
    assert r.status_code == 403

@test("Admin cannot access teacher endpoints")
def _():
    h = _auth_header(data["admin_id"])
    r = client.get("/api/v1/teacher/dashboard", headers=h)
    assert r.status_code == 403

# ========================================
# 3. DASHBOARD & PROFILE
# ========================================
print()
print("-- Dashboard & Profile --")

@test("Teacher 1 dashboard returns correct profile")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get("/api/v1/teacher/dashboard", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["name"] == "Teacher One"
    assert body["profile"]["department"] == "Math"
    assert len(body["classes"]) >= 1

@test("Teacher profile endpoint works")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get("/api/v1/teacher/profile", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "t1@test.com"

@test("Profile does not leak password_hash")
def _():
    h = _auth_header(data["teacher_1_id"])
    body_str = json.dumps(client.get("/api/v1/teacher/profile", headers=h).json()).lower()
    assert "password_hash" not in body_str
    assert "jwt_secret" not in body_str

# ========================================
# 4. ATTENDANCE
# ========================================
print()
print("-- Attendance --")

@test("Teacher 1 can bulk mark attendance for their class")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/attendance", headers=h, json={
        "class_id": data["class_a_id"],
        "date": str(date.today()),
        "entries": [{"student_id": data["student_profile_id"], "status": "present"}],
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    assert len(body["records"]) == 1
    assert body["records"][0]["status"] == "present"

@test("Duplicate attendance on same date rejected (409)")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/attendance", headers=h, json={
        "class_id": data["class_a_id"],
        "date": str(date.today()),
        "entries": [{"student_id": data["student_profile_id"], "status": "absent"}],
    })
    assert r.status_code == 409

@test("Teacher 1 cannot mark attendance for class they are not assigned to")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/attendance", headers=h, json={
        "class_id": data["class_b_id"],
        "date": str(date.today()),
        "entries": [{"student_id": data["student_profile_id"], "status": "present"}],
    })
    assert r.status_code == 403, f"SECURITY: Teacher accessed unassigned class! Got {r.status_code}"

@test("Teacher 1 can edit their own attendance record")
def _():
    h = _auth_header(data["teacher_1_id"])
    # Get existing records
    r = client.get(f"/api/v1/teacher/attendance?class_id={data['class_a_id']}", headers=h)
    assert r.status_code == 200
    records = r.json()
    assert len(records) >= 1
    att_id = records[0]["id"]
    # Edit it
    r2 = client.patch(f"/api/v1/teacher/attendance/{att_id}", headers=h, json={"status": "late"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "late"

@test("Teacher 2 cannot edit Teacher 1's attendance record")
def _():
    h1 = _auth_header(data["teacher_1_id"])
    r = client.get(f"/api/v1/teacher/attendance?class_id={data['class_a_id']}", headers=h1)
    att_id = r.json()[0]["id"]

    h2 = _auth_header(data["teacher_2_id"])
    r2 = client.patch(f"/api/v1/teacher/attendance/{att_id}", headers=h2, json={"status": "absent"})
    assert r2.status_code == 403, f"SECURITY: Teacher 2 edited Teacher 1's attendance! Got {r2.status_code}"

@test("Teacher 1 can list attendance for their class")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get(f"/api/v1/teacher/attendance?class_id={data['class_a_id']}", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1

# ========================================
# 5. ASSIGNMENTS
# ========================================
print()
print("-- Assignments --")

created_assignment_id = None

@test("Teacher 1 can create assignment for their class")
def _():
    global created_assignment_id
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/assignments", headers=h, json={
        "title": "Algebra Homework",
        "description": "Complete exercises 1-10",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "class_id": data["class_a_id"],
        "attachment_url": "https://example.com/algebra.pdf",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    created_assignment_id = r.json()["id"]
    assert r.json()["title"] == "Algebra Homework"

@test("Teacher 1 cannot create assignment for unassigned class")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/assignments", headers=h, json={
        "title": "Bad Assignment",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "class_id": data["class_b_id"],
    })
    assert r.status_code == 403, f"SECURITY: Teacher created assignment for unassigned class! Got {r.status_code}"

@test("Teacher 1 can update their assignment")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.patch(f"/api/v1/teacher/assignments/{created_assignment_id}", headers=h, json={
        "title": "Algebra Homework (Updated)",
    })
    assert r.status_code == 200
    assert r.json()["title"] == "Algebra Homework (Updated)"

@test("Teacher 2 cannot update Teacher 1's assignment")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.patch(f"/api/v1/teacher/assignments/{created_assignment_id}", headers=h, json={
        "title": "Hijacked!",
    })
    assert r.status_code == 403, f"SECURITY: Teacher 2 edited Teacher 1's assignment! Got {r.status_code}"

@test("Teacher 1 can list their assignments")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get("/api/v1/teacher/assignments", headers=h)
    assert r.status_code == 200
    titles = [a["title"] for a in r.json()]
    assert "Algebra Homework (Updated)" in titles

@test("Teacher 2 cannot see Teacher 1's assignments")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.get("/api/v1/teacher/assignments", headers=h)
    assert r.status_code == 200
    titles = [a["title"] for a in r.json()]
    assert "Algebra Homework (Updated)" not in titles, "SECURITY: Teacher 2 sees Teacher 1's assignments!"

@test("Teacher 1 can view submissions for their assignment")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get(f"/api/v1/teacher/assignments/{created_assignment_id}/submissions", headers=h)
    assert r.status_code == 200

@test("Teacher 2 cannot view submissions for Teacher 1's assignment")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.get(f"/api/v1/teacher/assignments/{created_assignment_id}/submissions", headers=h)
    assert r.status_code == 403

@test("Teacher 2 cannot delete Teacher 1's assignment")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.delete(f"/api/v1/teacher/assignments/{created_assignment_id}", headers=h)
    assert r.status_code == 403

@test("Teacher 1 can delete their assignment")
def _():
    # Create a throwaway assignment first
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/assignments", headers=h, json={
        "title": "To Delete",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "class_id": data["class_a_id"],
    })
    del_id = r.json()["id"]
    r2 = client.delete(f"/api/v1/teacher/assignments/{del_id}", headers=h)
    assert r2.status_code == 204

@test("Assignment title validation rejects empty title")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/assignments", headers=h, json={
        "title": "",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "class_id": data["class_a_id"],
    })
    assert r.status_code == 422

# ========================================
# 6. EXAMINATIONS & MARKS
# ========================================
print()
print("-- Examinations & Marks --")

created_exam_id = None

@test("Teacher 1 can create examination for their class")
def _():
    global created_exam_id
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/examinations", headers=h, json={
        "subject_id": data["subject_id"],
        "class_id": data["class_a_id"],
        "exam_date": "2026-08-15",
        "title": "Mid Term Math",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    created_exam_id = r.json()["id"]

@test("Teacher 1 cannot create exam for unassigned class")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/examinations", headers=h, json={
        "subject_id": data["subject_id"],
        "class_id": data["class_b_id"],
        "exam_date": "2026-08-15",
        "title": "Bad Exam",
    })
    assert r.status_code == 403

@test("Teacher 1 can bulk enter marks")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post(f"/api/v1/teacher/examinations/{created_exam_id}/marks", headers=h, json={
        "entries": [{"student_id": data["student_profile_id"], "marks": 85.0, "grade": "A"}],
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    assert len(r.json()["records"]) == 1
    assert r.json()["records"][0]["marks"] == 85.0

@test("Duplicate marks entry rejected (409)")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post(f"/api/v1/teacher/examinations/{created_exam_id}/marks", headers=h, json={
        "entries": [{"student_id": data["student_profile_id"], "marks": 90.0, "grade": "A+"}],
    })
    assert r.status_code == 409

@test("Teacher 2 cannot enter marks for Teacher 1's exam")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.post(f"/api/v1/teacher/examinations/{created_exam_id}/marks", headers=h, json={
        "entries": [{"student_id": data["student_profile_id"], "marks": 50.0}],
    })
    assert r.status_code == 403

@test("Teacher 1 can list marks for their exam")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get(f"/api/v1/teacher/examinations/{created_exam_id}/marks", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1

@test("Teacher 2 cannot list marks for Teacher 1's exam")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.get(f"/api/v1/teacher/examinations/{created_exam_id}/marks", headers=h)
    assert r.status_code == 403

@test("Teacher 1 can list their examinations")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get("/api/v1/teacher/examinations", headers=h)
    assert r.status_code == 200
    titles = [e["title"] for e in r.json()]
    assert "Mid Term Math" in titles

@test("Teacher 2 does not see Teacher 1's exams")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.get("/api/v1/teacher/examinations", headers=h)
    assert r.status_code == 200
    titles = [e["title"] for e in r.json()]
    assert "Mid Term Math" not in titles

# ========================================
# 7. NOTICES
# ========================================
print()
print("-- Notices --")

created_notice_id = None

@test("Teacher 1 can create a notice")
def _():
    global created_notice_id
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/notices", headers=h, json={
        "title": "Math Workshop",
        "body": "All students are invited to the math workshop.",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    created_notice_id = r.json()["id"]
    assert r.json()["published_at"] is not None  # auto-published

@test("Teacher 1 can update their notice")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.patch(f"/api/v1/teacher/notices/{created_notice_id}", headers=h, json={
        "title": "Math Workshop (Updated)",
    })
    assert r.status_code == 200
    assert r.json()["title"] == "Math Workshop (Updated)"

@test("Teacher 2 cannot update Teacher 1's notice")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.patch(f"/api/v1/teacher/notices/{created_notice_id}", headers=h, json={
        "title": "Hijacked!",
    })
    assert r.status_code == 403

@test("Teacher 2 cannot delete Teacher 1's notice")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.delete(f"/api/v1/teacher/notices/{created_notice_id}", headers=h)
    assert r.status_code == 403

@test("Teacher 1 can list their notices")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.get("/api/v1/teacher/notices", headers=h)
    assert r.status_code == 200
    titles = [n["title"] for n in r.json()]
    assert "Math Workshop (Updated)" in titles

@test("Teacher 2 does not see Teacher 1's notices")
def _():
    h = _auth_header(data["teacher_2_id"])
    r = client.get("/api/v1/teacher/notices", headers=h)
    assert r.status_code == 200
    titles = [n["title"] for n in r.json()]
    assert "Math Workshop (Updated)" not in titles

@test("Teacher 1 can delete their notice")
def _():
    # Create a throwaway
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/notices", headers=h, json={"title": "Delete Me", "body": "temp"})
    del_id = r.json()["id"]
    r2 = client.delete(f"/api/v1/teacher/notices/{del_id}", headers=h)
    assert r2.status_code == 204

@test("Notice title validation rejects empty title")
def _():
    h = _auth_header(data["teacher_1_id"])
    r = client.post("/api/v1/teacher/notices", headers=h, json={"title": "", "body": "content"})
    assert r.status_code == 422

# ========================================
# 8. RESPONSE SCHEMA SECURITY
# ========================================
print()
print("-- Response Schema Security --")

SENSITIVE_FIELDS = {"password_hash", "jwt_secret", "secret_key"}

@test("Dashboard response has no sensitive fields")
def _():
    h = _auth_header(data["teacher_1_id"])
    body_str = json.dumps(client.get("/api/v1/teacher/dashboard", headers=h).json()).lower()
    for field in SENSITIVE_FIELDS:
        assert field not in body_str, f"SECURITY: '{field}' found in dashboard response!"

@test("Assignments response has no sensitive fields")
def _():
    h = _auth_header(data["teacher_1_id"])
    body_str = json.dumps(client.get("/api/v1/teacher/assignments", headers=h).json()).lower()
    for field in SENSITIVE_FIELDS:
        assert field not in body_str, f"SECURITY: '{field}' found in assignments response!"

@test("Examinations response has no sensitive fields")
def _():
    h = _auth_header(data["teacher_1_id"])
    body_str = json.dumps(client.get("/api/v1/teacher/examinations", headers=h).json()).lower()
    for field in SENSITIVE_FIELDS:
        assert field not in body_str, f"SECURITY: '{field}' found in examinations response!"


# ========================================
# RESULTS
# ========================================

print()
print("=" * 65)
print(f"  RESULTS:  {passed} passed,  {failed} failed")
print("=" * 65)

if errors:
    print()
    print("  FAILURES:")
    for name, msg in errors:
        print(f"    X {name}")
        print(f"      {msg}")
        print()

sys.exit(1 if failed else 0)
