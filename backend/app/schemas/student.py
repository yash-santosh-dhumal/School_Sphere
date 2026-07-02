from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..models import AttendanceStatus


class StudentProfileRead(BaseModel):
    id: int
    user_id: int
    name: str
    email: EmailStr
    roll_no: str
    class_id: int | None
    class_name: str | None = None
    section: str | None = None
    phone: str | None = None
    address: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None


class AttendanceSummaryRead(BaseModel):
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    attendance_percentage: float


class StudentAttendanceRead(BaseModel):
    id: int
    date: date
    status: AttendanceStatus
    teacher_name: str | None = None


class StudentAssignmentRead(BaseModel):
    id: int
    title: str
    description: str | None = None
    deadline: datetime
    teacher_name: str | None = None
    class_name: str | None = None
    submitted: bool = False
    submitted_at: datetime | None = None
    file_url: str | None = None
    attachment_url: str | None = None


class StudentAssignmentSubmissionCreate(BaseModel):
    file_url: str = Field(min_length=1, max_length=500)


class StudentAssignmentSubmissionRead(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    file_url: str
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentMarkRead(BaseModel):
    id: int
    exam_title: str
    subject_name: str
    exam_date: date
    marks: float
    grade: str | None = None


class StudentNoticeRead(BaseModel):
    id: int
    title: str
    body: str
    scheduled_at: datetime | None = None
    published_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TimetableRead(BaseModel):
    id: int
    day_of_week: int
    start_time: time
    end_time: time
    subject_name: str
    teacher_name: str | None = None
    room: str | None = None
    notes: str | None = None


class StudentDashboardRead(BaseModel):
    profile: StudentProfileRead
    attendance_summary: AttendanceSummaryRead
    upcoming_assignments: list[StudentAssignmentRead]
    recent_marks: list[StudentMarkRead]
    notices: list[StudentNoticeRead]
    timetable: list[TimetableRead]
