import csv
import io
from datetime import date
from typing import List, Optional, Any

from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, and_, case
from sqlalchemy.orm import Session

from ..models import (
    Assignment,
    Attendance,
    AttendanceStatus,
    Examination,
    FeeRecord,
    Mark,
    SchoolClass,
    Student,
    Subject,
    Teacher,
    User,
)
from ..admin_models import TeacherClassAssignment
from ..schemas.report import (
    AttendanceReportItem,
    ClassSummaryReport,
    FeeReportItem,
    PerformanceReportItem,
    TeacherSummaryReport,
)


def export_csv(data: List[dict], filename: str) -> StreamingResponse:
    if not data:
        return StreamingResponse(iter([]), media_type="text/csv")
    
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    stream.seek(0)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


def generate_attendance_report(
    session: Session,
    class_id: Optional[int] = None,
    student_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[AttendanceReportItem]:
    
    # Query to count statuses per student
    stmt = (
        select(
            Student.id.label("student_id"),
            User.name.label("student_name"),
            Student.roll_no,
            func.count(Attendance.id).label("total_days"),
            func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_days"),
            func.sum(case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_days"),
            func.sum(case((Attendance.status == AttendanceStatus.LATE, 1), else_=0)).label("late_days"),
        )
        .select_from(Student)
        .join(User, Student.user_id == User.id)
        .outerjoin(Attendance, Student.id == Attendance.student_id)
        .group_by(Student.id, User.name, Student.roll_no)
    )

    if class_id:
        stmt = stmt.where(Student.class_id == class_id)
    if student_id:
        stmt = stmt.where(Student.id == student_id)
        
    if start_date or end_date:
        # We need to filter attendance records by date, but still keep students if they have no attendance in range?
        # Actually it's easier to just filter the Attendance join condition.
        # But for simplicity, we can apply where clause on Attendance.date if we only want students with records.
        date_filters = []
        if start_date:
            date_filters.append(Attendance.date >= start_date)
        if end_date:
            date_filters.append(Attendance.date <= end_date)
        
        # Modify the outerjoin to include date filters
        stmt = (
            select(
                Student.id.label("student_id"),
                User.name.label("student_name"),
                Student.roll_no,
                func.count(Attendance.id).label("total_days"),
                func.sum(case((Attendance.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_days"),
                func.sum(case((Attendance.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_days"),
                func.sum(case((Attendance.status == AttendanceStatus.LATE, 1), else_=0)).label("late_days"),
            )
            .select_from(Student)
            .join(User, Student.user_id == User.id)
            .outerjoin(Attendance, and_(Student.id == Attendance.student_id, *date_filters))
            .group_by(Student.id, User.name, Student.roll_no)
        )
        if class_id:
            stmt = stmt.where(Student.class_id == class_id)
        if student_id:
            stmt = stmt.where(Student.id == student_id)

    results = session.execute(stmt).all()
    
    report = []
    for row in results:
        total = row.total_days or 0
        present = row.present_days or 0
        percentage = (present / total * 100.0) if total > 0 else 0.0
        report.append(
            AttendanceReportItem(
                student_id=row.student_id,
                student_name=row.student_name,
                roll_no=row.roll_no,
                total_days=total,
                present_days=present,
                absent_days=row.absent_days or 0,
                late_days=row.late_days or 0,
                attendance_percentage=round(percentage, 2),
            )
        )
    return report


def generate_performance_report(
    session: Session,
    class_id: Optional[int] = None,
    student_id: Optional[int] = None,
) -> List[PerformanceReportItem]:
    stmt = (
        select(
            Student.id.label("student_id"),
            User.name.label("student_name"),
            Student.roll_no,
            Subject.name.label("subject"),
            Examination.title.label("exam_title"),
            Mark.marks,
            Mark.grade,
        )
        .select_from(Mark)
        .join(Student, Mark.student_id == Student.id)
        .join(User, Student.user_id == User.id)
        .join(Examination, Mark.exam_id == Examination.id)
        .join(Subject, Examination.subject_id == Subject.id)
    )

    if class_id:
        stmt = stmt.where(Student.class_id == class_id)
    if student_id:
        stmt = stmt.where(Student.id == student_id)

    results = session.execute(stmt).all()
    
    report = []
    for row in results:
        report.append(
            PerformanceReportItem(
                student_id=row.student_id,
                student_name=row.student_name,
                roll_no=row.roll_no,
                subject=row.subject,
                exam_title=row.exam_title,
                marks=row.marks,
                grade=row.grade,
            )
        )
    return report


def generate_fee_report(
    session: Session,
    status: Optional[str] = None,
    student_id: Optional[int] = None,
) -> List[FeeReportItem]:
    stmt = (
        select(
            Student.id.label("student_id"),
            User.name.label("student_name"),
            Student.roll_no,
            FeeRecord.total_amount,
            FeeRecord.paid_amount,
            FeeRecord.status,
            FeeRecord.due_date,
        )
        .select_from(FeeRecord)
        .join(Student, FeeRecord.student_id == Student.id)
        .join(User, Student.user_id == User.id)
    )

    if status:
        stmt = stmt.where(FeeRecord.status == status)
    if student_id:
        stmt = stmt.where(Student.id == student_id)

    results = session.execute(stmt).all()
    
    report = []
    for row in results:
        due = row.total_amount - row.paid_amount
        report.append(
            FeeReportItem(
                student_id=row.student_id,
                student_name=row.student_name,
                roll_no=row.roll_no,
                total_amount=row.total_amount,
                paid_amount=row.paid_amount,
                due_amount=due if due > 0 else 0.0,
                status=str(row.status.value) if hasattr(row.status, 'value') else str(row.status),
                due_date=str(row.due_date),
            )
        )
    return report


def generate_class_summary(session: Session, class_id: Optional[int] = None) -> List[ClassSummaryReport]:
    stmt = select(SchoolClass)
    if class_id:
        stmt = stmt.where(SchoolClass.id == class_id)
        
    classes = session.scalars(stmt).all()
    report = []
    
    for cls in classes:
        # Count students
        total_students = session.scalar(select(func.count(Student.id)).where(Student.class_id == cls.id)) or 0
        
        # Count assignments
        total_assignments = session.scalar(select(func.count(Assignment.id)).where(Assignment.class_id == cls.id)) or 0
        
        # Count exams
        total_exams = session.scalar(select(func.count(Examination.id)).where(Examination.class_id == cls.id)) or 0
        
        # Average attendance
        # Total present / total records for class
        present_stmt = select(func.count(Attendance.id)).join(Student).where(Student.class_id == cls.id, Attendance.status == AttendanceStatus.PRESENT)
        total_att_stmt = select(func.count(Attendance.id)).join(Student).where(Student.class_id == cls.id)
        
        present_count = session.scalar(present_stmt) or 0
        total_att_count = session.scalar(total_att_stmt) or 0
        avg_att = (present_count / total_att_count * 100.0) if total_att_count > 0 else 0.0
        
        report.append(
            ClassSummaryReport(
                class_id=cls.id,
                class_name=cls.name,
                section=cls.section,
                total_students=total_students,
                average_attendance_percentage=round(avg_att, 2),
                total_assignments=total_assignments,
                total_exams=total_exams,
            )
        )
    return report


def generate_teacher_summary(session: Session, teacher_id: Optional[int] = None) -> List[TeacherSummaryReport]:
    stmt = select(Teacher).join(User)
    if teacher_id:
        stmt = stmt.where(Teacher.id == teacher_id)
        
    teachers = session.scalars(stmt).all()
    report = []
    
    for t in teachers:
        # We need admin_models.TeacherClassAssignment but it's not imported.
        # Wait, TeacherClassAssignment is in admin_models.
        pass
        
    # We will import TeacherClassAssignment dynamically to avoid circular issues or just import it at top.
    # Ah, I see I already imported it at the top!
    
    for t in teachers:
        total_classes = session.scalar(select(func.count(TeacherClassAssignment.id)).where(TeacherClassAssignment.teacher_id == t.id)) or 0
        total_assignments = session.scalar(select(func.count(Assignment.id)).where(Assignment.teacher_id == t.id)) or 0
        total_exams = session.scalar(select(func.count(Examination.id)).where(Examination.teacher_id == t.id)) or 0
        
        report.append(
            TeacherSummaryReport(
                teacher_id=t.id,
                teacher_name=t.user.name,
                department=t.department,
                total_classes_assigned=total_classes,
                total_assignments_given=total_assignments,
                total_exams_conducted=total_exams,
            )
        )
        
    return report
