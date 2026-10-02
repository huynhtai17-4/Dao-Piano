"""Holiday and Leave domain entity representing teacher day-offs and school holidays."""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from backend.core.ids import generate_id
from backend.core.dates import now_iso, parse_date


class Holiday(BaseModel):
    """Domain model representing a holiday or leave period."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: generate_id("hol"))
    title: str = Field(default="Nghỉ dạy", description="Tiêu đề hoặc lý do nghỉ")
    start_date: str = Field(..., description="Ngày bắt đầu nghỉ (YYYY-MM-DD)")
    end_date: str = Field(..., description="Ngày kết thúc nghỉ (YYYY-MM-DD)")
    start_time: str = Field(default="00:00", description="Giờ bắt đầu nghỉ (HH:MM)")
    end_time: str = Field(default="23:59", description="Giờ kết thúc nghỉ (HH:MM)")
    is_all_day: bool = Field(default=True, description="Nghỉ cả ngày")
    created_at: str = Field(default_factory=now_iso)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        parse_date(v)
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> Holiday:
        s = parse_date(self.start_date)
        e = parse_date(self.end_date)
        if e < s:
            raise ValueError(f"Ngày kết thúc ({self.end_date}) phải sau hoặc cùng ngày với ngày bắt đầu ({self.start_date}).")
        return self

