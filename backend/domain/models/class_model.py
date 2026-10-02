"""Class domain entity representing a piano class group or 1-on-1 slot."""

from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from backend.core.enums import ClassType
from backend.core.ids import generate_id
from backend.core.dates import now_iso


class ClassModel(BaseModel):
    """Domain model representing a classroom or private instruction course."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: generate_id("cls"))
    name: str = Field(..., description="Tên lớp học")
    class_type: ClassType = Field(default=ClassType.ONE_ON_ONE, description="Loại lớp học")
    current_student_count: int = Field(default=0, ge=0, description="Sĩ số hiện tại")
    max_students: int = Field(default=1, ge=1, description="Sĩ số tối đa")
    student_ids: List[str] = Field(default_factory=list, description="Danh sách ID học sinh trong lớp")
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Tên lớp học không được để trống.")
        return s

    @model_validator(mode="after")
    def enforce_class_type_invariants(self) -> ClassModel:
        if self.class_type == ClassType.ONE_ON_ONE:
            object.__setattr__(self, "max_students", 1)
        elif self.max_students < 1:
            raise ValueError("Sĩ số tối đa của lớp học phải ít nhất là 1.")

        # Update current_student_count based on student_ids
        object.__setattr__(self, "current_student_count", len(self.student_ids))
        return self
