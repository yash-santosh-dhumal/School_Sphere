import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, StaticPool
from app.models import User, UserRole, SchoolClass, Subject, Teacher, Student
from app.db.base import Base
from app.main import app
from app.api.deps import get_database_session
from app.core.security import create_access_token

@pytest.fixture(scope="function")
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    def override_get_database_session():
        yield db_session

    app.dependency_overrides[get_database_session] = override_get_database_session
    
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def admin_headers(db_session: Session) -> dict:
    admin = User(name="Admin", email="admin@school.com", password_hash="hash", role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    token = create_access_token(str(admin.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
def student_headers(db_session: Session) -> dict:
    student = User(name="Student", email="student@school.com", password_hash="hash", role=UserRole.STUDENT)
    db_session.add(student)
    db_session.commit()
    token = create_access_token(str(student.id))
    return {"Authorization": f"Bearer {token}"}

def test_admin_dashboard_rbac(client: TestClient, admin_headers: dict, student_headers: dict):
    # Admin can access
    res = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert res.status_code == 200
    
    # Student cannot access
    res = client.get("/api/v1/admin/dashboard", headers=student_headers)
    assert res.status_code == 403

def test_classes_crud(client: TestClient, admin_headers: dict):
    # Create class
    res = client.post("/api/v1/admin/classes", headers=admin_headers, json={
        "name": "10",
        "section": "A",
        "academic_year": "2026-2027"
    })
    assert res.status_code == 201
    class_id = res.json()["id"]

    # List classes
    res = client.get("/api/v1/admin/classes", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["name"] == "10"

    # Update class
    res = client.put(f"/api/v1/admin/classes/{class_id}", headers=admin_headers, json={
        "name": "10",
        "section": "B",
        "academic_year": "2026-2027"
    })
    assert res.status_code == 200
    assert res.json()["section"] == "B"

    # Delete class
    res = client.delete(f"/api/v1/admin/classes/{class_id}", headers=admin_headers)
    assert res.status_code == 204

def test_assign_teacher(client: TestClient, db_session: Session, admin_headers: dict):
    # Setup data
    school_class = SchoolClass(name="9", section="A", academic_year="2026")
    subject = Subject(name="Math", code="M1")
    teacher_user = User(name="T1", email="t1@school.com", password_hash="hash", role=UserRole.TEACHER)
    db_session.add_all([school_class, subject, teacher_user])
    db_session.commit()
    
    teacher = Teacher(user_id=teacher_user.id)
    db_session.add(teacher)
    db_session.commit()

    res = client.post(f"/api/v1/admin/classes/{school_class.id}/assign-teacher", headers=admin_headers, json={
        "teacher_id": teacher.id,
        "subject_id": subject.id,
        "notes": "Main math teacher"
    })
    assert res.status_code == 200
    assert res.json()["teacher_id"] == teacher.id

def test_assign_student(client: TestClient, db_session: Session, admin_headers: dict):
    school_class = SchoolClass(name="9", section="A", academic_year="2026")
    student_user = User(name="S1", email="s1@school.com", password_hash="hash", role=UserRole.STUDENT)
    db_session.add_all([school_class, student_user])
    db_session.commit()
    
    student = Student(user_id=student_user.id, roll_no="123")
    db_session.add(student)
    db_session.commit()

    res = client.post(f"/api/v1/admin/classes/{school_class.id}/assign-student", headers=admin_headers, json={
        "student_id": student.id
    })
    assert res.status_code == 200
    assert res.json()["class_id"] == school_class.id

def test_settings_crud(client: TestClient, admin_headers: dict):
    res = client.put("/api/v1/admin/settings/SCHOOL_NAME", headers=admin_headers, json={
        "value": "EduPulse High",
        "description": "Name of the school"
    })
    assert res.status_code == 200
    assert res.json()["value"] == "EduPulse High"

    res = client.get("/api/v1/admin/settings", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1
