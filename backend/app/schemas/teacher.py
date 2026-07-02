from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from ..models import AttendanceStatus


# ── Teacher Profile & Dashboard ──


class TeacherProfileRead(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    department: str | None = None
    qualification: str | None = None
    experience: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClassSummary(BaseModel):
    class_id: int
    class_name: str
    section: str
    student_count: int


class TeacherDashboardRead(BaseModel):
    profile: TeacherProfileRead
    classes: list[ClassSummary]
    total_assignments: int
    total_examinations: int
    total_notices: int
    recent_attendance_count: int


# ── Attendance ──


class AttendanceEntry(BaseModel):
    student_id: int
    status: AttendanceStatus


class AttendanceBulkCreate(BaseModel):
    class_id: int
    date: date
    entries: list[AttendanceEntry] = Field(min_length=1)


class AttendanceRecordRead(BaseModel):
    id: int
    student_id: int
    student_name: str | None = None
    student_roll_no: str | None = None
    date: date
    status: AttendanceStatus
    teacher_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class AttendanceBulkRead(BaseModel):
    class_id: int
    date: date
    records: list[AttendanceRecordRead]


class AttendanceUpdateRequest(BaseModel):
    status: AttendanceStatus


# ── Assignments ──


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    deadline: datetime
    class_id: int
    attachment_url: str | None = Field(default=None, max_length=500)


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    deadline: datetime | None = None
    attachment_url: str | None = Field(default=None, max_length=500)


class AssignmentRead(BaseModel):
    id: int
    title: str
    description: str | None = None
    deadline: datetime
    class_id: int
    class_name: str | None = None
    attachment_url: str | None = None
    submission_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionRead(BaseModel):
    id: int
    student_id: int
    student_name: str | None = None
    student_roll_no: str | None = None
    file_url: str
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Examinations & Marks ──


class ExaminationCreate(BaseModel):
    subject_id: int
    class_id: int
    exam_date: date
    title: str = Field(min_length=1, max_length=150)


class ExaminationRead(BaseModel):
    id: int
    subject_id: int
    subject_name: str | None = None
    class_id: int
    class_name: str | None = None
    exam_date: date
    title: str
    mark_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkEntryCreate(BaseModel):
    student_id: int
    marks: float = Field(ge=0)
    grade: str | None = Field(default=None, max_length=10)


class MarksBulkCreate(BaseModel):
    entries: list[MarkEntryCreate] = Field(min_length=1)


class MarkRead(BaseModel):
    id: int
    exam_id: int
    student_id: int
    student_name: str | None = None
    student_roll_no: str | None = None
    marks: float
    grade: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarksBulkRead(BaseModel):
    exam_id: int
    records: list[MarkRead]


# ── Notices ──


class NoticeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    scheduled_at: datetime | None = None


class NoticeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    scheduled_at: datetime | None = None


class NoticeRead(BaseModel):
    id: int
    title: str
    body: str
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
