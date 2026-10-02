"""Schedule domain entity for calendar lesson events."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from backend.core.enums import ScheduleStatus
from backend.core.ids import generate_id
from backend.core.dates import now_iso, parse_date, get_day_of_week_label
from backend.core.time_utils import validate_time_format, time_to_minutes


class Schedule(BaseModel):
    """Domain model representing a scheduled lesson session."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: generate_id("sch"))
    class_id: Optional[str] = Field(default=None, description="ID lớp học (nếu có)")
    student_id: Optional[str] = Field(default=None, description="ID học sinh (cho 1-kèm-1 hoặc riêng)")
    date: str = Field(..., description="Ngày học (YYYY-MM-DD)")
    day_of_week: str = Field(default="", description="Thứ trong tuần (MON..SUN hoặc Thứ 2..CN)")
    start_time: str = Field(..., description="Giờ bắt đầu (HH:MM)")
    end_time: str = Field(..., description="Giờ kết thúc (HH:MM)")
    location: Optional[str] = Field(default="Phòng học 1", description="Phòng học offline")
    online_url: Optional[str] = Field(default=None, description="Đường link học online (Zoom, Google Meet)")
    color: Optional[str] = Field(default=None, description="Mã màu thẻ lịch")
    lesson_title: str = Field(default="Buổi học đàn Piano", description="Tiêu đề buổi học")
    status: ScheduleStatus = Field(default=ScheduleStatus.SCHEDULED, description="Trạng thái buổi học")
    original_schedule_id: Optional[str] = Field(default=None, description="ID của ca học gốc nếu đây là ca đổi lịch/học bù")
    rescheduled_to_id: Optional[str] = Field(default=None, description="ID của ca học mới được đổi sang")
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        parse_date(v)  # raises ValueError if invalid
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_times(cls, v: str) -> str:
        s = v.strip()
        if not validate_time_format(s):
            raise ValueError(f"Giờ '{v}' không đúng định dạng HH:MM (24h).")
        return s

    @model_validator(mode="after")
    def validate_time_order_and_weekday(self) -> Schedule:
        # Check start_time < end_time
        start_m = time_to_minutes(self.start_time)
        end_m = time_to_minutes(self.end_time)
        if end_m <= start_m:
            raise ValueError(f"Giờ kết thúc ({self.end_time}) phải sau giờ bắt đầu ({self.start_time}).")

        # Auto-compute day_of_week if empty
        if not self.day_of_week:
            parsed = parse_date(self.date)
            object.__setattr__(self, "day_of_week", get_day_of_week_label(parsed, lang="en"))
        return self
