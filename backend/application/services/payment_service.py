"""Tuition payment processing service with balance increments."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.payment import Payment
from backend.domain.repositories.payment_repository import PaymentRepository
from backend.domain.repositories.student_repository import StudentRepository
from backend.application.dto.payment_dto import PaymentCreateDTO, PaymentResponseDTO
from backend.core.time_utils import format_currency_vnd
from backend.core.dates import format_date_display, today_str
from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.event_bus import event_bus


class PaymentService:
    """Manages tuition records and automated student lesson credits."""

    def __init__(self, payment_repo: PaymentRepository, student_repo: StudentRepository) -> None:
        self.payment_repo = payment_repo
        self.student_repo = student_repo

    def _to_response_dto(self, p: Payment, student_cache: Optional[dict] = None) -> PaymentResponseDTO:
        student_name = None
        if student_cache and p.student_id in student_cache:
            st = student_cache[p.student_id]
            student_name = st.name if st else None
        else:
            st = self.student_repo.get_by_id(p.student_id)
            student_name = st.name if st else None

        return PaymentResponseDTO(
            id=p.id,
            student_id=p.student_id,
            student_name=student_name,
            amount=p.amount,
            amount_display=format_currency_vnd(p.amount),
            payment_date=p.payment_date,
            payment_date_display=format_date_display(p.payment_date),
            lessons_added=p.lessons_added,
            note=p.note,
            created_at=p.created_at,
        )

    def get_payments(self, student_id: Optional[str] = None) -> List[PaymentResponseDTO]:
        if student_id:
            payments = self.payment_repo.get_by_student_id(student_id)
        else:
            payments = self.payment_repo.get_all()

        # Sort payments newest first
        payments = sorted(payments, key=lambda p: p.payment_date, reverse=True)
        students = {s.id: s for s in self.student_repo.get_all(active_only=False)}
        return [self._to_response_dto(p, students) for p in payments]

    def record_payment(self, dto: PaymentCreateDTO) -> PaymentResponseDTO:
        if dto.amount <= 0:
            raise ValidationError("Số tiền nộp học phí phải lớn hơn 0.")

        student = self.student_repo.get_by_id(dto.student_id)
        if not student:
            raise NotFoundError(f"Không tìm thấy học sinh ID '{dto.student_id}'.")

        new_payment = Payment(
            student_id=dto.student_id,
            amount=dto.amount,
            payment_date=dto.payment_date,
            lessons_added=dto.lessons_added,
            note=dto.note.strip(),
        )

        persisted = self.payment_repo.create(new_payment)

        # Credit lessons to student
        if dto.lessons_added > 0:
            student.remaining_lessons += dto.lessons_added
            self.student_repo.update(student)

        event_bus.emit("payments_changed", persisted.id)
        event_bus.emit("students_changed", student.id)
        return self._to_response_dto(persisted)

    def get_total_revenue(self) -> int:
        """Calculate aggregate revenue across all recorded payments."""
        return sum(p.amount for p in self.payment_repo.get_all())

    def get_total_paid_by_student(self, student_id: str) -> int:
        """Calculate total amount paid by a specific student."""
        return sum(p.amount for p in self.payment_repo.get_by_student_id(student_id))

    def toggle_tuition_status(self, student_id: str, mark_as_paid: bool) -> None:
        """Toggle student tuition status with confirmation:
        - If mark_as_paid=True: credits 8 lessons and creates a standard payment record.
        - If mark_as_paid=False (revert mistake): sets remaining_lessons to 0 and removes the last payment record.
        """
        student = self.student_repo.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Không tìm thấy học sinh ID '{student_id}'.")

        if mark_as_paid:
            lessons_to_add = 8
            new_payment = Payment(
                student_id=student.id,
                amount=1600000,
                payment_date=today_str(),
                lessons_added=lessons_to_add,
                note="Đóng học phí (Chu kỳ 8 buổi)",
            )
            persisted = self.payment_repo.create(new_payment)
            student.remaining_lessons += lessons_to_add
            self.student_repo.update(student)
            event_bus.emit("payments_changed", persisted.id)
            event_bus.emit("students_changed", student.id)
        else:
            # Revert mistake: remove last payment if present
            student_payments = self.payment_repo.get_by_student_id(student.id)
            if student_payments:
                latest_p = max(student_payments, key=lambda p: p.created_at)
                self.payment_repo.delete(latest_p.id)
                event_bus.emit("payments_changed", latest_p.id)
            student.remaining_lessons = 0
            self.student_repo.update(student)
            event_bus.emit("students_changed", student.id)

