"""Payment domain entity representing tuition and package transactions."""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, ConfigDict

from backend.core.ids import generate_id
from backend.core.dates import now_iso, parse_date


class Payment(BaseModel):
    """Domain model tracking a tuition fee payment."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: generate_id("pay"))
    student_id: str = Field(..., description="ID học sinh nộp học phí")
    amount: int = Field(..., gt=0, description="Số tiền nộp (VNĐ, lưu số nguyên)")
    payment_date: str = Field(..., description="Ngày nộp học phí (YYYY-MM-DD)")
    lessons_added: int = Field(default=0, ge=0, description="Số buổi học được cộng thêm")
    note: str = Field(default="", description="Ghi chú đóng tiền / khóa học")
    created_at: str = Field(default_factory=now_iso)

    @field_validator("payment_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        parse_date(v)
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Số tiền học phí phải lớn hơn 0.")
        return v
