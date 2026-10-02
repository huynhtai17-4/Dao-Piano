"""Data Transfer Objects for Attendance operations."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.core.enums import AttendanceStatus


class AttendanceCreateDTO(BaseModel):
    """Input payload to record or update attendance."""

    schedule_id: str = Field(...)
    student_id: str = Field(...)
    attendance_date: str = Field(...)
    status: AttendanceStatus = Field(default=AttendanceStatus.PRESENT)
    note: str = Field(default="")


class AttendanceUpdateDTO(BaseModel):
    """Input payload to update an existing attendance."""

    id: str = Field(...)
    status: AttendanceStatus = Field(...)
    note: str = Field(default="")


class AttendanceResponseDTO(BaseModel):
    """Safe response model representing attendance record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    schedule_id: str
    student_id: str
    student_name: Optional[str] = None
    attendance_date: str
    status: AttendanceStatus
    status_display: str
    note: str
    created_at: str
