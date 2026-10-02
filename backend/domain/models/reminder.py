"""Reminder domain entity for alert tracking and notifications."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.core.enums import ReminderType, ReminderSeverity
from backend.core.ids import generate_id
from backend.core.dates import now_iso


class Reminder(BaseModel):
    """Domain model representing a system reminder or notification."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: generate_id("rem"))
    type: ReminderType = Field(..., description="Loại nhắc nhở")
    title: str = Field(..., description="Tiêu đề thông báo ngắn gọn")
    message: str = Field(..., description="Nội dung chi tiết nhắc nhở")
    severity: ReminderSeverity = Field(default=ReminderSeverity.INFO, description="Mức độ quan trọng")
    reference_id: Optional[str] = Field(default=None, description="ID tham chiếu tới học sinh hoặc lịch")
    created_at: str = Field(default_factory=now_iso)
