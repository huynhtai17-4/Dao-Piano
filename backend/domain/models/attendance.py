"""Attendance domain entity for tracking student attendance and lesson deductions."""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, ConfigDict

from backend.core.enums import AttendanceStatus
from backend.core.ids import generate_id
from backend.core.dates import now_iso, parse_date


class Attendance(BaseModel):
    """Domain model tracking a student's attendance on a given schedule/date."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: generate_id("att"))
    schedule_id: str = Field(..., description="ID buổi lịch học tương ứng")
    student_id: str = Field(..., description="ID học sinh được điểm danh")
    attendance_date: str = Field(..., description="Ngày điểm danh (YYYY-MM-DD)")
    status: AttendanceStatus = Field(default=AttendanceStatus.PRESENT, description="Trạng thái điểm danh")
    note: str = Field(default="", description="Ghi chú giáo viên")
    created_at: str = Field(default_factory=now_iso)

    @field_validator("attendance_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        parse_date(v)
        return v
