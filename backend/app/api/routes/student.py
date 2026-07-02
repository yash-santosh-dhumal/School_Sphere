from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ...api.deps import get_database_session, require_roles
from ...models import User, UserRole
from ...schemas.student import (
    StudentAssignmentRead,
    StudentAssignmentSubmissionCreate,
    StudentAssignmentSubmissionRead,
    StudentAttendanceRead,
    StudentDashboardRead,
    StudentMarkRead,
    StudentNoticeRead,
    StudentProfileRead,
    StudentProfileUpdate,
    TimetableRead,
)
from ...services.student_service import (
    get_student_dashboard,
    list_student_assignments,
    list_student_attendance,
    list_student_marks,
    list_student_notices,
    list_student_timetable,
    submit_assignment,
    update_student_profile,
    build_student_profile_read,
    get_student_for_user,
)


router = APIRouter(prefix="/student", tags=["student"])


@router.get("/dashboard", response_model=StudentDashboardRead)
def dashboard(
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> StudentDashboardRead:
    return get_student_dashboard(session, user)


@router.get("/profile", response_model=StudentProfileRead)
def profile(
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> StudentProfileRead:
    student = get_student_for_user(session, user)
    return build_student_profile_read(student)


@router.patch("/profile", response_model=StudentProfileRead)
def edit_profile(
    payload: StudentProfileUpdate,
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> StudentProfileRead:
    return update_student_profile(session, user, payload)


@router.get("/attendance", response_model=list[StudentAttendanceRead])
def attendance(
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> list[StudentAttendanceRead]:
    return list_student_attendance(session, user)


@router.get("/assignments", response_model=list[StudentAssignmentRead])
def assignments(
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> list[StudentAssignmentRead]:
    return list_student_assignments(session, user)


@router.post("/assignments/{assignment_id}/submit", response_model=StudentAssignmentSubmissionRead, status_code=status.HTTP_201_CREATED)
def submit(
    assignment_id: int,
    payload: StudentAssignmentSubmissionCreate,
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> StudentAssignmentSubmissionRead:
    submission = submit_assignment(session, user, assignment_id, payload.file_url)
    session.commit()
    return submission


@router.get("/marks", response_model=list[StudentMarkRead])
def marks(
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> list[StudentMarkRead]:
    return list_student_marks(session, user)


@router.get("/notices", response_model=list[StudentNoticeRead])
def notices(
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> list[StudentNoticeRead]:
    return list_student_notices(session, user)


@router.get("/timetable", response_model=list[TimetableRead])
def timetable(
    user: User = Depends(require_roles(UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
) -> list[TimetableRead]:
    return list_student_timetable(session, user)
