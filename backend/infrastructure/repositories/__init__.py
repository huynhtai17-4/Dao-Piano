"""Infrastructure repository implementations using JsonStorage."""

from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.infrastructure.repositories.json_attendance_repository import JsonAttendanceRepository
from backend.infrastructure.repositories.json_payment_repository import JsonPaymentRepository

__all__ = [
    "JsonStudentRepository",
    "JsonClassRepository",
    "JsonScheduleRepository",
    "JsonAttendanceRepository",
    "JsonPaymentRepository",
]
