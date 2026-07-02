from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Assignment,
    Attendance,
    AttendanceStatus,
    Mark,
    Notice,
    SchoolClass,
    Student,
    Teacher,
    Submission,
    TimetableEntry,
    User,
)
from ..schemas.student import (
    AttendanceSummaryRead,
    StudentAssignmentRead,
    StudentAttendanceRead,
    StudentDashboardRead,
    StudentMarkRead,
    StudentNoticeRead,
    StudentProfileRead,
    StudentProfileUpdate,
    StudentAssignmentSubmissionRead,
    TimetableRead,
)


def get_student_for_user(session: Session, user: User) -> Student:
    student = session.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return student


def build_student_profile_read(student: Student) -> StudentProfileRead:
    return StudentProfileRead(
        id=student.id,
        user_id=student.user_id,
        name=student.user.name,
        email=student.user.email,
        roll_no=student.roll_no,
        class_id=student.class_id,
        class_name=student.school_class.name if student.school_class else None,
        section=student.section,
        phone=student.phone,
        address=student.address,
        created_at=student.created_at,
        updated_at=student.updated_at,
    )


def get_student_dashboard(session: Session, user: User) -> StudentDashboardRead:
    student = get_student_for_user(session, user)
    attendance_rows = list(
        session.scalars(
            select(Attendance).where(Attendance.student_id == student.id).order_by(Attendance.date.desc())
        ).all()
    )
    assignment_rows = list(
        session.scalars(
            select(Assignment)
            .where(Assignment.class_id == student.class_id)
            .order_by(Assignment.deadline.asc())
            .limit(5)
        ).all()
    )
    mark_rows = list(
        session.scalars(select(Mark).where(Mark.student_id == student.id).order_by(Mark.created_at.desc()).limit(5)).all()
    )
    notice_rows = list(
        session.scalars(
            select(Notice).order_by(Notice.published_at.desc().nullslast(), Notice.created_at.desc()).limit(5)
        ).all()
    )
    timetable_rows = list(
        session.scalars(
            select(TimetableEntry)
            .where(TimetableEntry.class_id == student.class_id)
            .order_by(TimetableEntry.day_of_week.asc(), TimetableEntry.start_time.asc())
        ).all()
    )

    return StudentDashboardRead(
        profile=build_student_profile_read(student),
        attendance_summary=build_attendance_summary(attendance_rows),
        upcoming_assignments=[build_assignment_read(session, student, assignment) for assignment in assignment_rows],
        recent_marks=[build_mark_read(session, row) for row in mark_rows],
        notices=[build_notice_read(notice) for notice in notice_rows],
        timetable=[build_timetable_read(entry) for entry in timetable_rows],
    )


def list_student_attendance(session: Session, user: User) -> list[StudentAttendanceRead]:
    student = get_student_for_user(session, user)
    rows = list(
        session.scalars(
            select(Attendance).where(Attendance.student_id == student.id).order_by(Attendance.date.desc())
        ).all()
    )
    return [
        StudentAttendanceRead(
            id=row.id,
            date=row.date,
            status=row.status,
            teacher_name=_teacher_name(session, row.teacher_id),
        )
        for row in rows
    ]


def list_student_assignments(session: Session, user: User) -> list[StudentAssignmentRead]:
    student = get_student_for_user(session, user)
    assignment_rows = list(
        session.scalars(
            select(Assignment)
            .where(Assignment.class_id == student.class_id)
            .order_by(Assignment.deadline.asc())
        ).all()
    )
    return [build_assignment_read(session, student, assignment) for assignment in assignment_rows]


def submit_assignment(session: Session, user: User, assignment_id: int, file_url: str) -> StudentAssignmentSubmissionRead:
    student = get_student_for_user(session, user)
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.class_id != student.class_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assignment does not belong to your class")

    existing = session.scalar(
        select(Submission).where(Submission.assignment_id == assignment_id, Submission.student_id == student.id)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assignment already submitted")

    submission = Submission(
        assignment_id=assignment_id,
        student_id=student.id,
        file_url=file_url,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(submission)
    session.flush()
    return StudentAssignmentSubmissionRead.model_validate(submission)


def list_student_marks(session: Session, user: User) -> list[StudentMarkRead]:
    student = get_student_for_user(session, user)
    rows = list(
        session.execute(
            select(Mark)
            .where(Mark.student_id == student.id)
            .order_by(Mark.created_at.desc())
        ).scalars().all()
    )
    return [build_mark_read(session, row) for row in rows]


def list_student_notices(session: Session, user: User) -> list[StudentNoticeRead]:
    get_student_for_user(session, user)
    notices = list(
        session.scalars(
            select(Notice).order_by(Notice.published_at.desc().nullslast(), Notice.created_at.desc())
        ).all()
    )
    return [build_notice_read(notice) for notice in notices]


def list_student_timetable(session: Session, user: User) -> list[TimetableRead]:
    student = get_student_for_user(session, user)
    entries = list(
        session.scalars(
            select(TimetableEntry)
            .where(TimetableEntry.class_id == student.class_id)
            .order_by(TimetableEntry.day_of_week.asc(), TimetableEntry.start_time.asc())
        ).all()
    )
    return [build_timetable_read(entry) for entry in entries]


def update_student_profile(session: Session, user: User, payload: StudentProfileUpdate) -> StudentProfileRead:
    student = get_student_for_user(session, user)

    if payload.name is not None:
        student.user.name = payload.name
    if payload.email is not None:
        duplicate = session.scalar(select(User).where(User.email == payload.email, User.id != user.id))
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        student.user.email = payload.email
    if payload.phone is not None:
        student.phone = payload.phone
    if payload.address is not None:
        student.address = payload.address

    session.commit()
    session.refresh(student)
    return build_student_profile_read(student)


def build_attendance_summary(rows: list[Attendance]) -> AttendanceSummaryRead:
    total_days = len(rows)
    present_days = sum(row.status == AttendanceStatus.PRESENT for row in rows)
    absent_days = sum(row.status == AttendanceStatus.ABSENT for row in rows)
    late_days = sum(row.status == AttendanceStatus.LATE for row in rows)
    attendance_percentage = round((present_days / total_days) * 100, 2) if total_days else 0.0
    return AttendanceSummaryRead(
        total_days=total_days,
        present_days=present_days,
        absent_days=absent_days,
        late_days=late_days,
        attendance_percentage=attendance_percentage,
    )


def build_assignment_read(session: Session, student: Student, assignment: Assignment) -> StudentAssignmentRead:
    submission = session.scalar(
        select(Submission).where(Submission.assignment_id == assignment.id, Submission.student_id == student.id)
    )
    return StudentAssignmentRead(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        deadline=assignment.deadline,
        teacher_name=assignment.teacher.user.name if assignment.teacher and assignment.teacher.user else None,
        class_name=assignment.school_class.name if assignment.school_class else None,
        submitted=submission is not None,
        submitted_at=submission.submitted_at if submission is not None else None,
        file_url=submission.file_url if submission is not None else None,
        attachment_url=assignment.attachment_url,
    )


def build_mark_read(session: Session, mark: Mark) -> StudentMarkRead:
    exam = mark.examination
    subject_name = exam.subject.name if exam and exam.subject else ""
    return StudentMarkRead(
        id=mark.id,
        exam_title=exam.title if exam else "",
        subject_name=subject_name,
        exam_date=exam.exam_date if exam else mark.created_at.date(),
        marks=mark.marks,
        grade=mark.grade,
    )


def _teacher_name(session: Session, teacher_id: int | None) -> str | None:
    if teacher_id is None:
        return None
    teacher = session.get(Teacher, teacher_id)
    return teacher.user.name if teacher and teacher.user else None


def build_notice_read(notice: Notice) -> StudentNoticeRead:
    return StudentNoticeRead(
        id=notice.id,
        title=notice.title,
        body=notice.body,
        scheduled_at=notice.scheduled_at,
        published_at=notice.published_at,
    )


def build_timetable_read(entry: TimetableEntry) -> TimetableRead:
    return TimetableRead(
        id=entry.id,
        day_of_week=entry.day_of_week,
        start_time=entry.start_time,
        end_time=entry.end_time,
        subject_name=entry.subject.name if entry.subject else "",
        teacher_name=entry.teacher.user.name if entry.teacher and entry.teacher.user else None,
        room=entry.room,
        notes=entry.notes,
    )
