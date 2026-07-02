from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class AttendanceReportItem(BaseModel):
    student_id: int
    student_name: str
    roll_no: str
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    attendance_percentage: float

class PerformanceReportItem(BaseModel):
    student_id: int
    student_name: str
    roll_no: str
    subject: str
    exam_title: str
    marks: float
    grade: Optional[str]

class FeeReportItem(BaseModel):
    student_id: int
    student_name: str
    roll_no: str
    total_amount: float
    paid_amount: float
    due_amount: float
    status: str
    due_date: str

class ClassSummaryReport(BaseModel):
    class_id: int
    class_name: str
    section: str
    total_students: int
    average_attendance_percentage: float
    total_assignments: int
    total_exams: int

class TeacherSummaryReport(BaseModel):
    teacher_id: int
    teacher_name: str
    department: Optional[str]
    total_classes_assigned: int
    total_assignments_given: int
    total_exams_conducted: int

class ReportResponse(BaseModel):
    report_type: str
    data: List[dict]
