"""student module

Revision ID: 0004_student_module
Revises: 0003_admin_module
Create Date: 2026-07-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_student_module"
down_revision = "0003_admin_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timetable_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("teachers.id", ondelete="SET NULL")),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("room", sa.String(length=50)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_timetable_entries_class_id", "timetable_entries", ["class_id"])
    op.create_index("ix_timetable_entries_day_of_week", "timetable_entries", ["day_of_week"])


def downgrade() -> None:
    op.drop_index("ix_timetable_entries_day_of_week", table_name="timetable_entries")
    op.drop_index("ix_timetable_entries_class_id", table_name="timetable_entries")
    op.drop_table("timetable_entries")
