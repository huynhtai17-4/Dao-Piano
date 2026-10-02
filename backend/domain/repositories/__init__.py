"""Domain repository interface contracts."""

from backend.domain.repositories.student_repository import StudentRepository
from backend.domain.repositories.class_repository import ClassRepository
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.domain.repositories.attendance_repository import AttendanceRepository
from backend.domain.repositories.payment_repository import PaymentRepository

__all__ = [
    "StudentRepository",
    "ClassRepository",
    "ScheduleRepository",
    "AttendanceRepository",
    "PaymentRepository",
]
