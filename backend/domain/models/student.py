"""Student domain entity with Pydantic v2 validation."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from backend.core.enums import ClassType
from backend.core.ids import generate_id
from backend.core.dates import now_iso
from backend.core.validators import validate_phone, sanitize_phone


class Student(BaseModel):
    """Domain model representing a piano student."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: generate_id("stu"))
    name: str = Field(..., description="Họ và tên học sinh")
    phone: str = Field(..., description="Số điện thoại liên hệ")
    date_of_birth: Optional[str] = Field(default="", description="Ngày sinh (tùy chọn)")
    class_type: ClassType = Field(default=ClassType.ONE_ON_ONE, description="Hình thức học")
    class_id: Optional[str] = Field(default=None, description="ID lớp học được gán")
    remaining_lessons: int = Field(default=0, ge=0, description="Số buổi học còn lại")
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    is_active: bool = Field(default=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Tên học sinh không được để trống.")
        return s

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        s = sanitize_phone(v)
        if not validate_phone(s):
            raise ValueError(f"Số điện thoại '{v}' không hợp lệ (yêu cầu 10 chữ số tiêu chuẩn VN).")
        return s

    @field_validator("remaining_lessons")
    @classmethod
    def validate_remaining(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Số buổi còn lại không được âm.")
        return v
