"""Data Transfer Objects for Student workflows."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from backend.core.enums import ClassType
from backend.core.validators import validate_phone, sanitize_phone


class StudentCreateDTO(BaseModel):
    """Input payload to register a new student."""

    name: str = Field(..., min_length=1, description="Tên học sinh")
    phone: str = Field(..., description="Số điện thoại")
    date_of_birth: Optional[str] = Field(default="", description="Ngày sinh")
    class_type: ClassType = Field(default=ClassType.ONE_ON_ONE)
    class_id: Optional[str] = Field(default=None)
    remaining_lessons: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Tên học sinh không được để trống.")
        return s

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        cleaned = sanitize_phone(v)
        if not validate_phone(cleaned):
            raise ValueError(f"Số điện thoại '{v}' không hợp lệ (cần 10 chữ số).")
        return cleaned


class StudentUpdateDTO(BaseModel):
    """Input payload to update an existing student."""

    id: str = Field(...)
    name: str = Field(..., min_length=1)
    phone: str = Field(...)
    date_of_birth: Optional[str] = Field(default="")
    class_type: ClassType = Field(...)
    class_id: Optional[str] = Field(default=None)
    remaining_lessons: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Tên học sinh không được để trống.")
        return s

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        cleaned = sanitize_phone(v)
        if not validate_phone(cleaned):
            raise ValueError(f"Số điện thoại '{v}' không hợp lệ (cần 10 chữ số).")
        return cleaned


class StudentResponseDTO(BaseModel):
    """Safe response model representing a student."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    date_of_birth: Optional[str] = ""
    class_type: ClassType
    class_type_display: str
    class_id: Optional[str]
    class_name: Optional[str] = None
    remaining_lessons: int
    created_at: str
    updated_at: str
    is_active: bool
    status_level: str  # "normal", "warning" (<=2), "critical" (0)
