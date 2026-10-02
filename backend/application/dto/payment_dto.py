"""Data Transfer Objects for Payment operations."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PaymentCreateDTO(BaseModel):
    """Input payload to record a tuition payment."""

    student_id: str = Field(...)
    amount: int = Field(..., gt=0, description="Số tiền thanh toán")
    payment_date: str = Field(..., description="Ngày thanh toán (YYYY-MM-DD)")
    lessons_added: int = Field(default=0, ge=0, description="Số buổi học được cộng")
    note: str = Field(default="")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Số tiền học phí phải lớn hơn 0.")
        return v


class PaymentResponseDTO(BaseModel):
    """Safe response model representing a payment transaction."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    student_name: Optional[str] = None
    amount: int
    amount_display: str
    payment_date: str
    payment_date_display: str
    lessons_added: int
    note: str
    created_at: str
