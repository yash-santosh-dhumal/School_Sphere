from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..admin_models import TeacherClassAssignment
from ..models import (
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
    User,
)
from ..schemas.teacher import (
    AssignmentRead,
    AttendanceBulkRead,
    AttendanceEntry,
    AttendanceRecordRead,
    ClassSummary,
    ExaminationRead,
    MarkRead,
    MarksBulkRead,
    NoticeRead,
    SubmissionRead,
    TeacherDashboardRead,
    TeacherProfileRead,
)


# ── Helpers ──


def get_teacher_for_user(session: Session, user: User) -> Teacher:
    """Fetch the Teacher profile linked to this user, or 404."""
    teacher = session.scalar(select(Teacher).where(Teacher.user_id == user.id))
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")
    return teacher


def _assert_teacher_owns_class(session: Session, teacher: Teacher, class_id: int) -> SchoolClass:
    """Verify the teacher is assigned to the given class."""
    school_class = session.get(SchoolClass, class_id)
    if school_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    assigned = session.scalar(
        select(TeacherClassAssignment).where(
            TeacherClassAssignment.teacher_id == teacher.id,
            TeacherClassAssignment.class_id == class_id,
        )
    )
    if assigned is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this class")
    return school_class


def _student_info(session: Session, student_id: int) -> tuple[str | None, str | None]:
    """Return (student_name, roll_no) for a student id."""
    student = session.get(Student, student_id)
    if student is None:
        return None, None
    name = student.user.name if student.user else None
    return name, student.roll_no


# ── Dashboard ──


def build_teacher_profile_read(teacher: Teacher) -> TeacherProfileRead:
    return TeacherProfileRead(
        id=teacher.id,
        user_id=teacher.user_id,
        name=teacher.user.name,
        email=teacher.user.email,
        department=teacher.department,
        qualification=teacher.qualification,
        experience=teacher.experience,
        created_at=teacher.created_at,
        updated_at=teacher.updated_at,
    )


def _get_teacher_classes(session: Session, teacher: Teacher) -> list[ClassSummary]:
    assignments = list(
        session.scalars(
            select(TeacherClassAssignment).where(TeacherClassAssignment.teacher_id == teacher.id)
        ).all()
    )
    seen_class_ids: set[int] = set()
    summaries: list[ClassSummary] = []
    for a in assignments:
        if a.class_id in seen_class_ids:
            continue
        seen_class_ids.add(a.class_id)
        sc = a.school_class
        student_count = session.scalar(
            select(func.count()).select_from(Student).where(Student.class_id == a.class_id)
        ) or 0
        summaries.append(ClassSummary(
            class_id=sc.id, class_name=sc.name, section=sc.section, student_count=student_count,
        ))
    return summaries


def get_teacher_dashboard(session: Session, user: User) -> TeacherDashboardRead:
    teacher = get_teacher_for_user(session, user)
    profile = build_teacher_profile_read(teacher)
    classes = _get_teacher_classes(session, teacher)

    total_assignments = session.scalar(
        select(func.count()).select_from(Assignment).where(Assignment.teacher_id == teacher.id)
    ) or 0
    total_examinations = session.scalar(
        select(func.count()).select_from(Examination).where(Examination.teacher_id == teacher.id)
    ) or 0
    total_notices = session.scalar(
        select(func.count()).select_from(Notice).where(Notice.author_id == teacher.id)
    ) or 0
    recent_attendance_count = session.scalar(
        select(func.count()).select_from(Attendance).where(Attendance.teacher_id == teacher.id)
    ) or 0

    return TeacherDashboardRead(
        profile=profile,
        classes=classes,
        total_assignments=total_assignments,
        total_examinations=total_examinations,
        total_notices=total_notices,
        recent_attendance_count=recent_attendance_count,
    )


# ── Attendance ──


def mark_attendance_bulk(
    session: Session,
    teacher: Teacher,
    class_id: int,
    attendance_date: date,
    entries: list[AttendanceEntry],
) -> AttendanceBulkRead:
    _assert_teacher_owns_class(session, teacher, class_id)

    # Validate all students belong to this class
    student_ids = [e.student_id for e in entries]
    students = list(
        session.scalars(
            select(Student).where(Student.id.in_(student_ids), Student.class_id == class_id)
        ).all()
    )
    found_ids = {s.id for s in students}
    missing = set(student_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Students not in this class: {sorted(missing)}",
        )

    # Check for existing attendance on this date for these students
    existing = list(
        session.scalars(
            select(Attendance).where(
                Attendance.student_id.in_(student_ids),
                Attendance.date == attendance_date,
            )
        ).all()
    )
    if existing:
        dup_ids = [a.student_id for a in existing]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attendance already exists for students: {dup_ids}",
        )

    records: list[AttendanceRecordRead] = []
    for entry in entries:
        att = Attendance(
            student_id=entry.student_id,
            date=attendance_date,
            status=entry.status,
            teacher_id=teacher.id,
        )
        session.add(att)
        session.flush()
        name, roll_no = _student_info(session, entry.student_id)
        records.append(AttendanceRecordRead(
            id=att.id,
            student_id=att.student_id,
            student_name=name,
            student_roll_no=roll_no,
            date=att.date,
            status=att.status,
            teacher_id=att.teacher_id,
        ))

    return AttendanceBulkRead(class_id=class_id, date=attendance_date, records=records)


def update_attendance(
    session: Session,
    teacher: Teacher,
    attendance_id: int,
    new_status: AttendanceStatus,
) -> AttendanceRecordRead:
    att = session.get(Attendance, attendance_id)
    if att is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
    if att.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You did not create this attendance record")

    att.status = new_status
    session.flush()

    name, roll_no = _student_info(session, att.student_id)
    return AttendanceRecordRead(
        id=att.id,
        student_id=att.student_id,
        student_name=name,
        student_roll_no=roll_no,
        date=att.date,
        status=att.status,
        teacher_id=att.teacher_id,
    )


def list_attendance_for_class(
    session: Session,
    teacher: Teacher,
    class_id: int,
    attendance_date: date | None = None,
) -> list[AttendanceRecordRead]:
    _assert_teacher_owns_class(session, teacher, class_id)

    student_ids_q = select(Student.id).where(Student.class_id == class_id)
    query = select(Attendance).where(Attendance.student_id.in_(student_ids_q)).order_by(Attendance.date.desc())
    if attendance_date is not None:
        query = query.where(Attendance.date == attendance_date)

    rows = list(session.scalars(query).all())
    results: list[AttendanceRecordRead] = []
    for row in rows:
        name, roll_no = _student_info(session, row.student_id)
        results.append(AttendanceRecordRead(
            id=row.id,
            student_id=row.student_id,
            student_name=name,
            student_roll_no=roll_no,
            date=row.date,
            status=row.status,
            teacher_id=row.teacher_id,
        ))
    return results


# ── Assignments ──


def create_assignment(
    session: Session,
    teacher: Teacher,
    *,
    title: str,
    description: str | None,
    deadline: datetime,
    class_id: int,
    attachment_url: str | None,
) -> AssignmentRead:
    _assert_teacher_owns_class(session, teacher, class_id)

    assignment = Assignment(
        title=title,
        description=description,
        deadline=deadline,
        teacher_id=teacher.id,
        class_id=class_id,
        attachment_url=attachment_url,
    )
    session.add(assignment)
    session.flush()
    return _build_assignment_read(session, assignment)


def update_assignment(
    session: Session,
    teacher: Teacher,
    assignment_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    deadline: datetime | None = None,
    attachment_url: str | None = None,
) -> AssignmentRead:
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this assignment")

    if title is not None:
        assignment.title = title
    if description is not None:
        assignment.description = description
    if deadline is not None:
        assignment.deadline = deadline
    if attachment_url is not None:
        assignment.attachment_url = attachment_url

    session.flush()
    return _build_assignment_read(session, assignment)


def delete_assignment(session: Session, teacher: Teacher, assignment_id: int) -> None:
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this assignment")
    session.delete(assignment)
    session.flush()


def list_teacher_assignments(session: Session, teacher: Teacher) -> list[AssignmentRead]:
    rows = list(
        session.scalars(
            select(Assignment)
            .where(Assignment.teacher_id == teacher.id)
            .order_by(Assignment.deadline.asc())
        ).all()
    )
    return [_build_assignment_read(session, a) for a in rows]


def list_assignment_submissions(
    session: Session, teacher: Teacher, assignment_id: int,
) -> list[SubmissionRead]:
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this assignment")

    rows = list(
        session.scalars(
            select(Submission)
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.submitted_at.desc())
        ).all()
    )
    results: list[SubmissionRead] = []
    for sub in rows:
        name, roll_no = _student_info(session, sub.student_id)
        results.append(SubmissionRead(
            id=sub.id,
            student_id=sub.student_id,
            student_name=name,
            student_roll_no=roll_no,
            file_url=sub.file_url,
            submitted_at=sub.submitted_at,
        ))
    return results


def _build_assignment_read(session: Session, assignment: Assignment) -> AssignmentRead:
    submission_count = session.scalar(
        select(func.count()).select_from(Submission).where(Submission.assignment_id == assignment.id)
    ) or 0
    class_name = assignment.school_class.name if assignment.school_class else None
    return AssignmentRead(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        deadline=assignment.deadline,
        class_id=assignment.class_id,
        class_name=class_name,
        attachment_url=assignment.attachment_url,
        submission_count=submission_count,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


# ── Examinations & Marks ──


def create_examination(
    session: Session,
    teacher: Teacher,
    *,
    subject_id: int,
    class_id: int,
    exam_date: date,
    title: str,
) -> ExaminationRead:
    _assert_teacher_owns_class(session, teacher, class_id)

    subject = session.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    exam = Examination(
        subject_id=subject_id,
        class_id=class_id,
        teacher_id=teacher.id,
        exam_date=exam_date,
        title=title,
    )
    session.add(exam)
    session.flush()
    return _build_examination_read(session, exam)


def list_teacher_examinations(session: Session, teacher: Teacher) -> list[ExaminationRead]:
    rows = list(
        session.scalars(
            select(Examination)
            .where(Examination.teacher_id == teacher.id)
            .order_by(Examination.exam_date.desc())
        ).all()
    )
    return [_build_examination_read(session, e) for e in rows]


def enter_marks_bulk(
    session: Session,
    teacher: Teacher,
    exam_id: int,
    entries: list,
) -> MarksBulkRead:
    exam = session.get(Examination, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found")
    if exam.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this examination")

    student_ids = [e.student_id for e in entries]

    # Check for duplicates
    existing = list(
        session.scalars(
            select(Mark).where(Mark.exam_id == exam_id, Mark.student_id.in_(student_ids))
        ).all()
    )
    if existing:
        dup_ids = [m.student_id for m in existing]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Marks already exist for students: {dup_ids}",
        )

    records: list[MarkRead] = []
    for entry in entries:
        mark = Mark(
            exam_id=exam_id,
            student_id=entry.student_id,
            marks=entry.marks,
            grade=entry.grade,
        )
        session.add(mark)
        session.flush()
        name, roll_no = _student_info(session, entry.student_id)
        records.append(MarkRead(
            id=mark.id,
            exam_id=mark.exam_id,
            student_id=mark.student_id,
            student_name=name,
            student_roll_no=roll_no,
            marks=mark.marks,
            grade=mark.grade,
            created_at=mark.created_at,
        ))

    return MarksBulkRead(exam_id=exam_id, records=records)


def list_exam_marks(session: Session, teacher: Teacher, exam_id: int) -> list[MarkRead]:
    exam = session.get(Examination, exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found")
    if exam.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this examination")

    rows = list(
        session.scalars(
            select(Mark).where(Mark.exam_id == exam_id).order_by(Mark.student_id)
        ).all()
    )
    results: list[MarkRead] = []
    for m in rows:
        name, roll_no = _student_info(session, m.student_id)
        results.append(MarkRead(
            id=m.id,
            exam_id=m.exam_id,
            student_id=m.student_id,
            student_name=name,
            student_roll_no=roll_no,
            marks=m.marks,
            grade=m.grade,
            created_at=m.created_at,
        ))
    return results


def _build_examination_read(session: Session, exam: Examination) -> ExaminationRead:
    mark_count = session.scalar(
        select(func.count()).select_from(Mark).where(Mark.exam_id == exam.id)
    ) or 0
    subject_name = exam.subject.name if exam.subject else None
    class_name = exam.school_class.name if exam.school_class else None
    return ExaminationRead(
        id=exam.id,
        subject_id=exam.subject_id,
        subject_name=subject_name,
        class_id=exam.class_id,
        class_name=class_name,
        exam_date=exam.exam_date,
        title=exam.title,
        mark_count=mark_count,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
    )


# ── Notices ──


def create_notice(
    session: Session,
    teacher: Teacher,
    *,
    title: str,
    body: str,
    scheduled_at: datetime | None = None,
) -> NoticeRead:
    published_at = None if scheduled_at else datetime.now(timezone.utc)
    notice = Notice(
        author_id=teacher.id,
        title=title,
        body=body,
        scheduled_at=scheduled_at,
        published_at=published_at,
    )
    session.add(notice)
    session.flush()
    return _build_notice_read(notice)


def update_notice(
    session: Session,
    teacher: Teacher,
    notice_id: int,
    *,
    title: str | None = None,
    body: str | None = None,
    scheduled_at: datetime | None = None,
) -> NoticeRead:
    notice = session.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")
    if notice.author_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this notice")

    if title is not None:
        notice.title = title
    if body is not None:
        notice.body = body
    if scheduled_at is not None:
        notice.scheduled_at = scheduled_at

    session.flush()
    return _build_notice_read(notice)


def delete_notice(session: Session, teacher: Teacher, notice_id: int) -> None:
    notice = session.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")
    if notice.author_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this notice")
    session.delete(notice)
    session.flush()


def list_teacher_notices(session: Session, teacher: Teacher) -> list[NoticeRead]:
    rows = list(
        session.scalars(
            select(Notice)
            .where(Notice.author_id == teacher.id)
            .order_by(Notice.created_at.desc())
        ).all()
    )
    return [_build_notice_read(n) for n in rows]


def _build_notice_read(notice: Notice) -> NoticeRead:
    return NoticeRead(
        id=notice.id,
        title=notice.title,
        body=notice.body,
        scheduled_at=notice.scheduled_at,
        published_at=notice.published_at,
        created_at=notice.created_at,
        updated_at=notice.updated_at,
    )
