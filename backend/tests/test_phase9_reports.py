"""Phase 9 Reports Tests.

Tests cover:
- Attendance reports (JSON/CSV)
- Performance reports (JSON/CSV)
- Fee reports (JSON/CSV)
- Class and Teacher summary reports (JSON/CSV)
- Role-based access control (Student accessing others' reports)
"""
from __future__ import annotations

import csv
import io
import os
import sys
from datetime import date, timedelta

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
    User, UserRole, SchoolClass, Student, Teacher, Subject, 
    Attendance, AttendanceStatus, Examination, Mark, FeeRecord, PaymentStatus
)
from app.admin_models import TeacherClassAssignment

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
    # Users
    admin_u = User(name="Admin", email="admin@test.com", password_hash="x", role=UserRole.ADMIN)
    teacher_u = User(name="Teacher One", email="t1@test.com", password_hash="x", role=UserRole.TEACHER)
    student_u1 = User(name="Student One", email="s1@test.com", password_hash="x", role=UserRole.STUDENT)
    student_u2 = User(name="Student Two", email="s2@test.com", password_hash="x", role=UserRole.STUDENT)
    
    session.add_all([admin_u, teacher_u, student_u1, student_u2])
    session.commit()

    # Profiles
    teacher = Teacher(user_id=teacher_u.id, department="Math")
    session.add(teacher)
    session.commit()

    cls = SchoolClass(name="Class 10", section="A", academic_year="2026")
    session.add(cls)
    session.commit()
    
    # Assignment
    tca = TeacherClassAssignment(teacher_id=teacher.id, class_id=cls.id)
    session.add(tca)
    
    student1 = Student(user_id=student_u1.id, roll_no="10A01", class_id=cls.id)
    student2 = Student(user_id=student_u2.id, roll_no="10A02", class_id=cls.id)
    session.add_all([student1, student2])
    session.commit()

    # Subject & Exam & Mark
    subj = Subject(code="MATH101", name="Mathematics")
    session.add(subj)
    session.commit()
    
    exam = Examination(subject_id=subj.id, class_id=cls.id, teacher_id=teacher.id, exam_date=date.today(), title="Midterm")
    session.add(exam)
    session.commit()
    
    mark = Mark(exam_id=exam.id, student_id=student1.id, marks=95.5, grade="A+")
    session.add(mark)
    
    # Attendance
    att1 = Attendance(student_id=student1.id, date=date.today(), status=AttendanceStatus.PRESENT, teacher_id=teacher.id)
    att2 = Attendance(student_id=student1.id, date=date.today() - timedelta(days=1), status=AttendanceStatus.ABSENT, teacher_id=teacher.id)
    session.add_all([att1, att2])
    
    # Fees
    fee = FeeRecord(student_id=student1.id, total_amount=1000.0, paid_amount=500.0, due_date=date.today(), status=PaymentStatus.PENDING)
    session.add(fee)
    
    session.commit()

    result = {
        "admin_u_id": admin_u.id,
        "teacher_u_id": teacher_u.id,
        "student_u1_id": student_u1.id,
        "student_u2_id": student_u2.id,
        "class_id": cls.id,
        "teacher_id": teacher.id,
        "student1_id": student1.id,
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
print("  PHASE 9 REPORTS TESTS")
print("=" * 60)


@test("GET /reports/attendance (JSON)")
def _():
    h = _auth_header(data["admin_u_id"])
    r = client.get(f"/api/v1/reports/attendance?class_id={data['class_id']}", headers=h)
    assert r.status_code == 200
    res = r.json()
    assert res["report_type"] == "attendance"
    items = res["data"]
    # Student 1 has 2 attendance records (1 present, 1 absent) => 50%
    s1_item = next(i for i in items if i["student_id"] == data["student1_id"])
    assert s1_item["total_days"] == 2
    assert s1_item["present_days"] == 1
    assert s1_item["attendance_percentage"] == 50.0

@test("GET /reports/attendance (CSV)")
def _():
    h = _auth_header(data["admin_u_id"])
    r = client.get(f"/api/v1/reports/attendance?class_id={data['class_id']}&format=csv", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    content = r.text
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) > 0
    s1_row = next(r for r in rows if int(r["student_id"]) == data["student1_id"])
    assert s1_row["attendance_percentage"] == "50.0"

@test("GET /reports/performance (JSON)")
def _():
    h = _auth_header(data["admin_u_id"])
    r = client.get(f"/api/v1/reports/performance?student_id={data['student1_id']}", headers=h)
    assert r.status_code == 200
    res = r.json()
    assert res["report_type"] == "performance"
    assert len(res["data"]) == 1
    assert res["data"][0]["marks"] == 95.5

@test("GET /reports/fees (JSON)")
def _():
    h = _auth_header(data["admin_u_id"])
    r = client.get("/api/v1/reports/fees?status=pending", headers=h)
    assert r.status_code == 200
    res = r.json()
    assert len(res["data"]) == 1
    assert res["data"][0]["due_amount"] == 500.0

@test("GET /reports/summary/class (JSON)")
def _():
    h = _auth_header(data["admin_u_id"])
    r = client.get(f"/api/v1/reports/summary/class?class_id={data['class_id']}", headers=h)
    assert r.status_code == 200
    res = r.json()
    assert len(res["data"]) == 1
    # total present (1) / total records (2) => 50% average
    assert res["data"][0]["average_attendance_percentage"] == 50.0
    assert res["data"][0]["total_exams"] == 1
    assert res["data"][0]["total_students"] == 2

@test("GET /reports/summary/teacher (JSON)")
def _():
    h = _auth_header(data["admin_u_id"])
    r = client.get(f"/api/v1/reports/summary/teacher?teacher_id={data['teacher_id']}", headers=h)
    assert r.status_code == 200
    res = r.json()
    assert len(res["data"]) == 1
    assert res["data"][0]["total_classes_assigned"] == 1

@test("RBAC: Student cannot fetch other student's reports")
def _():
    h = _auth_header(data["student_u2_id"])  # student 2
    r = client.get(f"/api/v1/reports/attendance?student_id={data['student1_id']}", headers=h)
    assert r.status_code == 403


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
