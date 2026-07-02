from datetime import date
from typing import Optional, Union

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from ...api.deps import get_current_user, get_database_session, require_roles
from ...models import User, UserRole
from ...schemas.report import (
    AttendanceReportItem,
    ClassSummaryReport,
    FeeReportItem,
    PerformanceReportItem,
    ReportResponse,
    TeacherSummaryReport,
)
from ...services.report_service import (
    export_csv,
    generate_attendance_report,
    generate_class_summary,
    generate_fee_report,
    generate_performance_report,
    generate_teacher_summary,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/attendance", response_model=ReportResponse)
def get_attendance_report(
    class_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER, UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
):
    # Students can only see their own report
    if user.role == UserRole.STUDENT:
        if student_id != user.student_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own report")

    data = generate_attendance_report(session, class_id, student_id, start_date, end_date)
    
    if format == "csv":
        return export_csv([item.model_dump() for item in data], "attendance_report.csv")
    return ReportResponse(report_type="attendance", data=[item.model_dump() for item in data])


@router.get("/performance", response_model=ReportResponse)
def get_performance_report(
    class_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER, UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
):
    if user.role == UserRole.STUDENT:
        if student_id != user.student_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own report")

    data = generate_performance_report(session, class_id, student_id)
    
    if format == "csv":
        return export_csv([item.model_dump() for item in data], "performance_report.csv")
    return ReportResponse(report_type="performance", data=[item.model_dump() for item in data])


@router.get("/fees", response_model=ReportResponse)
def get_fee_report(
    fee_status: Optional[str] = Query(None, alias="status"),
    student_id: Optional[int] = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STUDENT)),
    session: Session = Depends(get_database_session),
):
    if user.role == UserRole.STUDENT:
        if student_id != user.student_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own report")

    data = generate_fee_report(session, fee_status, student_id)
    
    if format == "csv":
        return export_csv([item.model_dump() for item in data], "fee_report.csv")
    return ReportResponse(report_type="fees", data=[item.model_dump() for item in data])


@router.get("/summary/class", response_model=ReportResponse)
def get_class_summary_report(
    class_id: Optional[int] = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
    session: Session = Depends(get_database_session),
):
    data = generate_class_summary(session, class_id)
    
    if format == "csv":
        return export_csv([item.model_dump() for item in data], "class_summary_report.csv")
    return ReportResponse(report_type="class_summary", data=[item.model_dump() for item in data])


@router.get("/summary/teacher", response_model=ReportResponse)
def get_teacher_summary_report(
    teacher_id: Optional[int] = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    user: User = Depends(require_roles(UserRole.ADMIN)),
    session: Session = Depends(get_database_session),
):
    data = generate_teacher_summary(session, teacher_id)
    
    if format == "csv":
        return export_csv([item.model_dump() for item in data], "teacher_summary_report.csv")
    return ReportResponse(report_type="teacher_summary", data=[item.model_dump() for item in data])
