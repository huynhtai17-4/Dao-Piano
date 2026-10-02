"""Holiday and Leave application service managing days off and schedule adjustments."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.holiday import Holiday
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.infrastructure.repositories.json_holiday_repository import JsonHolidayRepository
from backend.core.enums import ScheduleStatus
from backend.core.event_bus import event_bus


from backend.core.time_utils import is_time_overlap


class HolidayService:
    """Manages teacher and center day-off records and updates schedule statuses."""

    def __init__(
        self,
        holiday_repo: JsonHolidayRepository,
        schedule_repo: ScheduleRepository,
    ) -> None:
        self.holiday_repo = holiday_repo
        self.schedule_repo = schedule_repo

    def get_all_holidays(self) -> List[Holiday]:
        return self.holiday_repo.get_all()

    def get_holiday_by_id(self, holiday_id: str) -> Optional[Holiday]:
        return self.holiday_repo.get_by_id(holiday_id)

    def is_date_holiday(self, target_date: str) -> Optional[Holiday]:
        for h in self.holiday_repo.get_all():
            if h.start_date <= target_date <= h.end_date:
                return h
        return None

    def is_schedule_holiday(self, schedule_date: str, start_time: str, end_time: str) -> Optional[Holiday]:
        for h in self.holiday_repo.get_all():
            if h.start_date <= schedule_date <= h.end_date:
                if h.is_all_day or (h.start_time == "00:00" and h.end_time == "23:59"):
                    return h
                if is_time_overlap(start_time, end_time, h.start_time, h.end_time):
                    return h
        return None

    def get_holidays_in_range(self, start_date: str, end_date: str) -> List[Holiday]:
        return [
            h for h in self.holiday_repo.get_all()
            if not (h.end_date < start_date or h.start_date > end_date)
        ]

    def create_holiday(
        self,
        title: str = "Nghỉ dạy",
        start_date: str = "",
        end_date: str = "",
        start_time: str = "00:00",
        end_time: str = "23:59",
        is_all_day: bool = True,
    ) -> Holiday:
        """Create a holiday period and automatically mark affected schedules as HOLIDAY."""
        holiday = Holiday(
            title=title.strip() or "Nghỉ dạy",
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
        )
        persisted = self.holiday_repo.create(holiday)

        # Mark all overlapping scheduled sessions as HOLIDAY
        overlapping = self.schedule_repo.get_by_date_range(start_date, end_date)
        for s in overlapping:
            if s.status in (ScheduleStatus.SCHEDULED, ScheduleStatus.RESCHEDULED):
                if is_all_day or is_time_overlap(s.start_time, s.end_time, start_time, end_time):
                    s.status = ScheduleStatus.HOLIDAY
                    self.schedule_repo.update(s)

        event_bus.emit("schedules_changed", persisted.id)
        event_bus.emit("holidays_changed", persisted.id)
        return persisted

    def delete_holiday(self, holiday_id: str) -> bool:
        """Remove a holiday and restore HOLIDAY sessions back to SCHEDULED."""
        holiday = self.holiday_repo.get_by_id(holiday_id)
        if not holiday:
            return False

        # Revert schedules in this date range back to SCHEDULED
        overlapping = self.schedule_repo.get_by_date_range(holiday.start_date, holiday.end_date)
        for s in overlapping:
            if s.status == ScheduleStatus.HOLIDAY:
                if holiday.is_all_day or is_time_overlap(s.start_time, s.end_time, holiday.start_time, holiday.end_time):
                    s.status = ScheduleStatus.SCHEDULED
                    self.schedule_repo.update(s)

        result = self.holiday_repo.delete(holiday_id)
        event_bus.emit("schedules_changed", holiday_id)
        event_bus.emit("holidays_changed", holiday_id)
        return result

