"""Data Transfer Objects for Class operations."""

from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from backend.core.enums import ClassType


class ClassCreateDTO(BaseModel):
    """Input payload to create a new class."""

    name: str = Field(..., min_length=1, description="Tên lớp học")
    class_type: ClassType = Field(default=ClassType.ONE_ON_ONE)
    max_students: int = Field(default=1, ge=1, description="Sĩ số tối đa")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Tên lớp không được để trống.")
        return s


class ClassUpdateDTO(BaseModel):
    """Input payload to update an existing class."""

    id: str = Field(...)
    name: str = Field(...)
    class_type: ClassType = Field(...)
    max_students: int = Field(..., ge=1)


class ClassResponseDTO(BaseModel):
    """Safe response model representing a classroom."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    class_type: ClassType
    class_type_display: str
    current_student_count: int
    max_students: int
    student_ids: List[str]
    created_at: str
    updated_at: str
    is_full: bool
