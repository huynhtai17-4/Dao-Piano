"""Automated reminder generator for balance alerts and daily agenda."""

from __future__ import annotations
from typing import List
from backend.domain.models.reminder import Reminder
from backend.domain.repositories.student_repository import StudentRepository
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.core.enums import ReminderType, ReminderSeverity, ScheduleStatus
from backend.core.dates import today_str, format_date_display


class ReminderService:
    """Evaluates business conditions to produce actionable alerts."""

    def __init__(
        self,
        student_repo: StudentRepository,
        schedule_repo: ScheduleRepository,
    ) -> None:
        self.student_repo = student_repo
        self.schedule_repo = schedule_repo

    def get_all_reminders(self) -> List[Reminder]:
        """Generate high-priority notifications sorted by urgency."""
        reminders: List[Reminder] = []
        today = today_str()

        # 1. Audit student lesson balances
        active_students = self.student_repo.get_all(active_only=True)
        for s in active_students:
            if s.remaining_lessons == 0:
                reminders.append(
                    Reminder(
                        type=ReminderType.NO_LESSONS,
                        title=f"{s.name} đã hết buổi",
                        message=f"Học sinh {s.name} ({s.phone}) còn 0 buổi học. Cần nhắc đóng học phí.",
                        severity=ReminderSeverity.CRITICAL,
                        reference_id=s.id,
                    )
                )
            elif s.remaining_lessons <= 2:
                reminders.append(
                    Reminder(
                        type=ReminderType.LOW_LESSONS,
                        title=f"{s.name} còn {s.remaining_lessons} buổi",
                        message=f"Học sinh {s.name} sắp hết số buổi học ({s.remaining_lessons} buổi còn lại).",
                        severity=ReminderSeverity.WARNING,
                        reference_id=s.id,
                    )
                )

        # 2. Check today's lesson itinerary
        today_schedules = self.schedule_repo.get_by_date_range(today, today)
        scheduled_count = sum(1 for sch in today_schedules if sch.status == ScheduleStatus.SCHEDULED)
        if scheduled_count > 0:
            reminders.append(
                Reminder(
                    type=ReminderType.TODAY_SCHEDULE,
                    title=f"Lịch hôm nay: {scheduled_count} ca học",
                    message=f"Hôm nay ({format_date_display(today)}) có {scheduled_count} ca học cần giảng dạy.",
                    severity=ReminderSeverity.INFO,
                )
            )

        # Sort: CRITICAL first, then WARNING, then INFO
        severity_order = {
            ReminderSeverity.CRITICAL: 0,
            ReminderSeverity.WARNING: 1,
            ReminderSeverity.INFO: 2,
        }
        return sorted(reminders, key=lambda r: severity_order.get(r.severity, 99))
