from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db.base import Base


class UserRole(StrEnum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class NotificationType(StrEnum):
    ASSIGNMENT = "assignment"
    EXAM = "exam"
    FEE = "fee"
    ATTENDANCE = "attendance"
    ANNOUNCEMENT = "announcement"
    SYSTEM = "system"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)

    student_profile: Mapped[Student | None] = relationship(back_populates="user", uselist=False)
    teacher_profile: Mapped[Teacher | None] = relationship(back_populates="user", uselist=False)
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")


class SchoolClass(Base, TimestampMixin):
    __tablename__ = "school_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    section: Mapped[str] = mapped_column(String(20), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)

    students: Mapped[list[Student]] = relationship(back_populates="school_class")
    assignments: Mapped[list[Assignment]] = relationship(back_populates="school_class")
    examinations: Mapped[list[Examination]] = relationship(back_populates="school_class")
    timetable_entries: Mapped[list[TimetableEntry]] = relationship(back_populates="school_class")

    __table_args__ = (UniqueConstraint("name", "section", "academic_year", name="uq_school_class_identity"),)


class Teacher(Base, TimestampMixin):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))
    qualification: Mapped[str | None] = mapped_column(String(150))
    experience: Mapped[int | None] = mapped_column(Integer)

    user: Mapped[User] = relationship(back_populates="teacher_profile")
    assignments: Mapped[list[Assignment]] = relationship(back_populates="teacher")
    examinations: Mapped[list[Examination]] = relationship(back_populates="teacher")
    notices: Mapped[list[Notice]] = relationship(back_populates="author")
    timetable_entries: Mapped[list[TimetableEntry]] = relationship(back_populates="teacher")


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    roll_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True)
    section: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="student_profile")
    school_class: Mapped[SchoolClass | None] = relationship(back_populates="students")
    attendance_records: Mapped[list[Attendance]] = relationship(back_populates="student")
    submissions: Mapped[list[Submission]] = relationship(back_populates="student")
    marks: Mapped[list[Mark]] = relationship(back_populates="student")
    fee_records: Mapped[list[FeeRecord]] = relationship(back_populates="student")


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    examinations: Mapped[list[Examination]] = relationship(back_populates="subject")
    timetable_entries: Mapped[list[TimetableEntry]] = relationship(back_populates="subject")


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(500))

    teacher: Mapped[Teacher] = relationship(back_populates="assignments")
    school_class: Mapped[SchoolClass] = relationship(back_populates="assignments")
    submissions: Mapped[list[Submission]] = relationship(back_populates="assignment")


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
    student: Mapped[Student] = relationship(back_populates="submissions")

    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_submission_assignment_student"),)


class Examination(Base, TimestampMixin):
    __tablename__ = "examinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)

    subject: Mapped[Subject] = relationship(back_populates="examinations")
    school_class: Mapped[SchoolClass] = relationship(back_populates="examinations")
    teacher: Mapped[Teacher] = relationship(back_populates="examinations")
    marks: Mapped[list[Mark]] = relationship(back_populates="examination")


class Mark(Base, TimestampMixin):
    __tablename__ = "marks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(10))

    examination: Mapped[Examination] = relationship(back_populates="marks")
    student: Mapped[Student] = relationship(back_populates="marks")

    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_mark_exam_student"),)


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)

    student: Mapped[Student] = relationship(back_populates="attendance_records")

    __table_args__ = (UniqueConstraint("student_id", "date", name="uq_attendance_student_date"),)


class Notice(Base, TimestampMixin):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[Teacher | None] = relationship(back_populates="notices")


class FeeRecord(Base, TimestampMixin):
    __tablename__ = "fee_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    student: Mapped[Student] = relationship(back_populates="fee_records")


class TimetableEntry(Base, TimestampMixin):
    __tablename__ = "timetable_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

    school_class: Mapped[SchoolClass] = relationship(back_populates="timetable_entries")
    subject: Mapped[Subject] = relationship(back_populates="timetable_entries")
    teacher: Mapped[Teacher | None] = relationship(back_populates="timetable_entries")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="notifications")

