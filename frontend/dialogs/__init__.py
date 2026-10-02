"""Presentation Dialogs exports."""

from frontend.dialogs.student_dialog import StudentDialog
from frontend.dialogs.quick_lessons_dialog import QuickLessonsDialog
from frontend.dialogs.class_dialog import ClassDialog
from frontend.dialogs.schedule_dialog import ScheduleDialog
from frontend.dialogs.attendance_dialog import AttendanceDialog, ClassAttendanceDialog
from frontend.dialogs.reschedule_dialog import RescheduleDialog
from frontend.dialogs.payment_dialog import PaymentDialog
from frontend.dialogs.holiday_dialog import HolidayDialog

__all__ = [
    "StudentDialog",
    "QuickLessonsDialog",
    "ClassDialog",
    "ScheduleDialog",
    "AttendanceDialog",
    "ClassAttendanceDialog",
    "RescheduleDialog",
    "PaymentDialog",
    "HolidayDialog",
]
