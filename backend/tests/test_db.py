import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.models import User, UserRole, SchoolClass, Student
from app.db.base import Base

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_user_email_unique_constraint(db_session):
    user1 = User(name="User 1", email="unique@school.com", password_hash="hash", role=UserRole.STUDENT)
    db_session.add(user1)
    db_session.commit()
    
    user2 = User(name="User 2", email="unique@school.com", password_hash="hash", role=UserRole.STUDENT)
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_relationship_class_students(db_session):
    school_class = SchoolClass(name="10", section="A", academic_year="2026")
    db_session.add(school_class)
    db_session.commit()

    user = User(name="Student", email="s@s.com", password_hash="hash", role=UserRole.STUDENT)
    db_session.add(user)
    db_session.commit()

    student = Student(user_id=user.id, class_id=school_class.id, roll_no="123")
    db_session.add(student)
    db_session.commit()

    assert len(school_class.students) == 1
    assert school_class.students[0].id == student.id
    assert student.school_class.id == school_class.id
