"""Enumerations representing domain constants across Piano Center Manager."""

from enum import Enum


class StrEnum(str, Enum):
    """String enumeration for JSON serializability."""

    def __str__(self) -> str:
        return self.value


class ClassType(StrEnum):
    """Instructional format for a class or student assignment."""

    ONE_ON_ONE = "ONE_ON_ONE"
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"

    @property
    def display_name(self) -> str:
        match self:
            case ClassType.ONE_ON_ONE:
                return "1 Kèm 1"
            case ClassType.OFFLINE:
                return "Lớp Offline"
            case ClassType.ONLINE:
                return "Lớp Online"


class ScheduleStatus(StrEnum):
    """Lifecycle status of a calendar lesson event."""

    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    HOLIDAY = "HOLIDAY"

    @property
    def display_name(self) -> str:
        match self:
            case ScheduleStatus.SCHEDULED:
                return "Đã lên lịch"
            case ScheduleStatus.COMPLETED:
                return "Đã hoàn thành"
            case ScheduleStatus.CANCELLED:
                return "Đã hủy"
            case ScheduleStatus.RESCHEDULED:
                return "Đã đổi lịch"
            case ScheduleStatus.HOLIDAY:
                return "Nghỉ học"


class AttendanceStatus(StrEnum):
    """Student attendance outcome for a lesson."""

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    RESCHEDULED = "RESCHEDULED"

    @property
    def display_name(self) -> str:
        match self:
            case AttendanceStatus.PRESENT:
                return "Có mặt"
            case AttendanceStatus.ABSENT:
                return "Vắng mặt"
            case AttendanceStatus.RESCHEDULED:
                return "Đổi lịch"


class ReminderType(StrEnum):
    """Category of system reminder or alert."""

    LOW_LESSONS = "LOW_LESSONS"
    NO_LESSONS = "NO_LESSONS"
    PAYMENT_DUE = "PAYMENT_DUE"
    RESCHEDULE_REQUEST = "RESCHEDULE_REQUEST"
    TODAY_SCHEDULE = "TODAY_SCHEDULE"


class ReminderSeverity(StrEnum):
    """Visual priority level for reminders."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

