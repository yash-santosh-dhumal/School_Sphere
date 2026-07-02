from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from ...api.deps import get_database_session, require_roles
from ...models import User, UserRole
from ...schemas.teacher import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
    AttendanceBulkCreate,
    AttendanceBulkRead,
    AttendanceRecordRead,
    AttendanceUpdateRequest,
    ExaminationCreate,
    ExaminationRead,
    MarkRead,
    MarksBulkCreate,
    MarksBulkRead,
    NoticeCreate,
    NoticeRead,
    NoticeUpdate,
    SubmissionRead,
    TeacherDashboardRead,
    TeacherProfileRead,
)
from ...services.teacher_service import (
    build_teacher_profile_read,
    create_assignment,
    create_examination,
    create_notice,
    delete_assignment,
    delete_notice,
    enter_marks_bulk,
    get_teacher_dashboard,
    get_teacher_for_user,
    list_assignment_submissions,
    list_attendance_for_class,
    list_exam_marks,
    list_teacher_assignments,
    list_teacher_examinations,
    list_teacher_notices,
    mark_attendance_bulk,
    update_assignment,
    update_attendance,
    update_notice,
)


router = APIRouter(prefix="/teacher", tags=["teacher"])


# ── Dashboard & Profile ──


@router.get("/dashboard", response_model=TeacherDashboardRead)
def dashboard(
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> TeacherDashboardRead:
    return get_teacher_dashboard(session, user)


@router.get("/profile", response_model=TeacherProfileRead)
def profile(
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> TeacherProfileRead:
    teacher = get_teacher_for_user(session, user)
    return build_teacher_profile_read(teacher)


# ── Attendance ──


@router.get("/attendance", response_model=list[AttendanceRecordRead])
def get_attendance(
    class_id: int = Query(...),
    attendance_date: date | None = Query(default=None, alias="date"),
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> list[AttendanceRecordRead]:
    teacher = get_teacher_for_user(session, user)
    return list_attendance_for_class(session, teacher, class_id, attendance_date)


@router.post("/attendance", response_model=AttendanceBulkRead, status_code=status.HTTP_201_CREATED)
def post_attendance(
    payload: AttendanceBulkCreate,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> AttendanceBulkRead:
    teacher = get_teacher_for_user(session, user)
    result = mark_attendance_bulk(session, teacher, payload.class_id, payload.date, payload.entries)
    session.commit()
    return result


@router.patch("/attendance/{attendance_id}", response_model=AttendanceRecordRead)
def patch_attendance(
    attendance_id: int,
    payload: AttendanceUpdateRequest,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> AttendanceRecordRead:
    teacher = get_teacher_for_user(session, user)
    result = update_attendance(session, teacher, attendance_id, payload.status)
    session.commit()
    return result


# ── Assignments ──


@router.get("/assignments", response_model=list[AssignmentRead])
def get_assignments(
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> list[AssignmentRead]:
    teacher = get_teacher_for_user(session, user)
    return list_teacher_assignments(session, teacher)


@router.post("/assignments", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def post_assignment(
    payload: AssignmentCreate,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> AssignmentRead:
    teacher = get_teacher_for_user(session, user)
    result = create_assignment(
        session, teacher,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        class_id=payload.class_id,
        attachment_url=payload.attachment_url,
    )
    session.commit()
    return result


@router.patch("/assignments/{assignment_id}", response_model=AssignmentRead)
def patch_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> AssignmentRead:
    teacher = get_teacher_for_user(session, user)
    result = update_assignment(
        session, teacher, assignment_id,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        attachment_url=payload.attachment_url,
    )
    session.commit()
    return result


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_assignment(
    assignment_id: int,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> Response:
    teacher = get_teacher_for_user(session, user)
    delete_assignment(session, teacher, assignment_id)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionRead])
def get_submissions(
    assignment_id: int,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> list[SubmissionRead]:
    teacher = get_teacher_for_user(session, user)
    return list_assignment_submissions(session, teacher, assignment_id)


# ── Examinations & Marks ──


@router.get("/examinations", response_model=list[ExaminationRead])
def get_examinations(
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> list[ExaminationRead]:
    teacher = get_teacher_for_user(session, user)
    return list_teacher_examinations(session, teacher)


@router.post("/examinations", response_model=ExaminationRead, status_code=status.HTTP_201_CREATED)
def post_examination(
    payload: ExaminationCreate,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> ExaminationRead:
    teacher = get_teacher_for_user(session, user)
    result = create_examination(
        session, teacher,
        subject_id=payload.subject_id,
        class_id=payload.class_id,
        exam_date=payload.exam_date,
        title=payload.title,
    )
    session.commit()
    return result


@router.post("/examinations/{exam_id}/marks", response_model=MarksBulkRead, status_code=status.HTTP_201_CREATED)
def post_marks(
    exam_id: int,
    payload: MarksBulkCreate,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> MarksBulkRead:
    teacher = get_teacher_for_user(session, user)
    result = enter_marks_bulk(session, teacher, exam_id, payload.entries)
    session.commit()
    return result


@router.get("/examinations/{exam_id}/marks", response_model=list[MarkRead])
def get_marks(
    exam_id: int,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> list[MarkRead]:
    teacher = get_teacher_for_user(session, user)
    return list_exam_marks(session, teacher, exam_id)


# ── Notices ──


@router.get("/notices", response_model=list[NoticeRead])
def get_notices(
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> list[NoticeRead]:
    teacher = get_teacher_for_user(session, user)
    return list_teacher_notices(session, teacher)


@router.post("/notices", response_model=NoticeRead, status_code=status.HTTP_201_CREATED)
def post_notice(
    payload: NoticeCreate,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> NoticeRead:
    teacher = get_teacher_for_user(session, user)
    result = create_notice(
        session, teacher,
        title=payload.title,
        body=payload.body,
        scheduled_at=payload.scheduled_at,
    )
    session.commit()
    return result


@router.patch("/notices/{notice_id}", response_model=NoticeRead)
def patch_notice(
    notice_id: int,
    payload: NoticeUpdate,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> NoticeRead:
    teacher = get_teacher_for_user(session, user)
    result = update_notice(
        session, teacher, notice_id,
        title=payload.title,
        body=payload.body,
        scheduled_at=payload.scheduled_at,
    )
    session.commit()
    return result


@router.delete("/notices/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_notice(
    notice_id: int,
    user: User = Depends(require_roles(UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
) -> Response:
    teacher = get_teacher_for_user(session, user)
    delete_notice(session, teacher, notice_id)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
