"""Data Transfer Objects for Schedule events."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from backend.core.enums import ScheduleStatus, ClassType
from backend.core.time_utils import validate_time_format


class ScheduleCreateDTO(BaseModel):
    """Input payload to create a new calendar schedule."""

    class_id: Optional[str] = None
    student_id: Optional[str] = None
    date: str = Field(..., description="Ngày học (YYYY-MM-DD)")
    start_time: str = Field(..., description="Giờ bắt đầu (HH:MM)")
    end_time: str = Field(..., description="Giờ kết thúc (HH:MM)")
    location: Optional[str] = "Phòng học 1"
    online_url: Optional[str] = None
    lesson_title: str = "Học đàn Piano"
    color: Optional[str] = None
    original_schedule_id: Optional[str] = None
    rescheduled_to_id: Optional[str] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_times(cls, v: str) -> str:
        s = v.strip()
        if not validate_time_format(s):
            raise ValueError(f"Giờ '{v}' không đúng định dạng HH:MM.")
        return s


class ScheduleUpdateDTO(BaseModel):
    """Input payload to update an existing schedule."""

    id: str = Field(...)
    class_id: Optional[str] = None
    student_id: Optional[str] = None
    date: str = Field(...)
    start_time: str = Field(...)
    end_time: str = Field(...)
    location: Optional[str] = None
    online_url: Optional[str] = None
    lesson_title: str = "Học đàn Piano"
    status: ScheduleStatus = ScheduleStatus.SCHEDULED
    color: Optional[str] = None
    original_schedule_id: Optional[str] = None
    rescheduled_to_id: Optional[str] = None


class ScheduleResponseDTO(BaseModel):
    """Safe response model representing a schedule lesson event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    class_id: Optional[str]
    class_name: Optional[str] = None
    class_type: Optional[ClassType] = None
    student_id: Optional[str]
    student_name: Optional[str] = None
    date: str
    day_of_week: str
    start_time: str
    end_time: str
    duration_minutes: int
    location: Optional[str]
    online_url: Optional[str]
    color: Optional[str]
    lesson_title: str
    status: ScheduleStatus
    status_display: str
    original_schedule_id: Optional[str] = None
    rescheduled_to_id: Optional[str] = None
    created_at: str
    updated_at: str
