"""Dashboard aggregate analytics service."""

from __future__ import annotations
from typing import Dict, Any
from backend.domain.repositories.student_repository import StudentRepository
from backend.domain.repositories.class_repository import ClassRepository
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.domain.repositories.payment_repository import PaymentRepository
from backend.core.dates import today_str
from backend.core.time_utils import format_currency_vnd


class DashboardService:
    """Computes high-level key performance metrics for the studio."""

    def __init__(
        self,
        student_repo: StudentRepository,
        class_repo: ClassRepository,
        schedule_repo: ScheduleRepository,
        payment_repo: PaymentRepository,
    ) -> None:
        self.student_repo = student_repo
        self.class_repo = class_repo
        self.schedule_repo = schedule_repo
        self.payment_repo = payment_repo

    def get_summary(self) -> Dict[str, Any]:
        """Aggregate KPIs across students, classes, schedule, and financials."""
        today = today_str()
        active_students = self.student_repo.get_all(active_only=True)
        total_students = len(active_students)
        total_classes = len(self.class_repo.get_all())

        today_schedules = self.schedule_repo.get_by_date_range(today, today)
        today_lessons_count = len(today_schedules)

        low_lessons_count = sum(1 for s in active_students if 0 < s.remaining_lessons <= 2)
        zero_lessons_count = sum(1 for s in active_students if s.remaining_lessons == 0)

        paid_students_count = sum(1 for s in active_students if s.remaining_lessons > 1)
        unpaid_students_count = sum(1 for s in active_students if s.remaining_lessons <= 1)

        all_payments = self.payment_repo.get_all()
        # Doanh thu chỉ tính trong tháng hiện tại (hết tháng reset lại)
        current_month = today[:7]
        monthly_payments = [p for p in all_payments if p.payment_date.startswith(current_month)]
        total_revenue = sum(p.amount for p in monthly_payments)

        return {
            "total_students": total_students,
            "total_classes": total_classes,
            "today_lessons_count": today_lessons_count,
            "low_lessons_count": low_lessons_count,
            "zero_lessons_count": zero_lessons_count,
            "attention_needed_count": low_lessons_count + zero_lessons_count,
            "paid_students_count": paid_students_count,
            "unpaid_students_count": unpaid_students_count,
            "total_revenue": total_revenue,
            "total_revenue_display": format_currency_vnd(total_revenue),
            "current_month_display": f"Tháng {today[5:7]}/{today[:4]}",
        }

