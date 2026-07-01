from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..core.security import hash_password
from ..models import (
    Assignment,
    Attendance,
    AttendanceStatus,
    Examination,
    FeeRecord,
    Mark,
    Notice,
    PaymentStatus,
    SchoolClass,
    Student,
    Subject,
    Teacher,
    User,
    UserRole,
)


def seed_demo_data(session: Session) -> None:
    admin = session.query(User).filter(User.email == "admin@schoolsphere.local").one_or_none()
    if admin is not None:
        return

    school_class = SchoolClass(name="10", section="A", academic_year="2026-2027")
    subject = Subject(code="MATH101", name="Mathematics")

    admin_user = User(
        name="System Admin",
        email="admin@schoolsphere.local",
        password_hash=hash_password("Admin@12345"),
        role=UserRole.ADMIN,
    )
    teacher_user = User(
        name="Teacher One",
        email="teacher@schoolsphere.local",
        password_hash=hash_password("Teacher@12345"),
        role=UserRole.TEACHER,
    )
    student_user = User(
        name="Student One",
        email="student@schoolsphere.local",
        password_hash=hash_password("Student@12345"),
        role=UserRole.STUDENT,
    )

    teacher = Teacher(
        user=teacher_user,
        department="Mathematics",
        qualification="M.Sc Mathematics",
        experience=5,
    )
    student = Student(
        user=student_user,
        roll_no="10A-001",
        school_class=school_class,
        section="A",
        phone="9999999999",
        address="Demo Address",
    )

    assignment = Assignment(
        title="Algebra Basics",
        description="Solve the attached algebra worksheet.",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        teacher=teacher,
        school_class=school_class,
        attachment_url="https://example.com/resources/algebra.pdf",
    )
    exam = Examination(
        subject=subject,
        school_class=school_class,
        teacher=teacher,
        exam_date=date(2026, 7, 15),
        title="Mid Term Mathematics",
    )

    session.add_all([admin_user, teacher_user, student_user, school_class, subject, teacher, student, assignment, exam])
    session.flush()

    session.add_all(
        [
            Attendance(student=student, date=date.today(), status=AttendanceStatus.PRESENT, teacher_id=teacher.id),
            Mark(examination=exam, student=student, marks=92.0, grade="A+"),
            Notice(author=teacher, title="Welcome to School Sphere", body="Demo notice for the seeded database."),
            FeeRecord(
                student=student,
                total_amount=15000.0,
                paid_amount=5000.0,
                due_date=date.today() + timedelta(days=30),
                status=PaymentStatus.PENDING,
            ),
        ]
    )

    session.commit()
