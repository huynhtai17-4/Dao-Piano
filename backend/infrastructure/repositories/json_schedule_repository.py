"""JSON-backed implementation of ScheduleRepository."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.schedule import Schedule
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.core.dates import now_iso
from backend.core.exceptions import NotFoundError, CorruptedDataError


class JsonScheduleRepository(ScheduleRepository):
    """Repository storing and querying calendar schedules via atomic JSON storage."""

    FILE_NAME = "schedules.json"

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def _load_all(self) -> List[Schedule]:
        raw_list = self.storage.read(self.FILE_NAME, default_factory=list)
        try:
            return [Schedule.model_validate(item) for item in raw_list]
        except Exception as e:
            raise CorruptedDataError(f"Dữ liệu lịch dạy không hợp lệ: {e}") from e

    def _save_all(self, schedules: List[Schedule]) -> None:
        payload = [s.model_dump() for s in schedules]
        self.storage.write(self.FILE_NAME, payload)

    def get_all(self) -> List[Schedule]:
        return self._load_all()

    def get_by_id(self, schedule_id: str) -> Optional[Schedule]:
        for s in self._load_all():
            if s.id == schedule_id:
                return s
        return None

    def get_by_date_range(self, start_date: str, end_date: str) -> List[Schedule]:
        # Lexicographical comparison works because format is YYYY-MM-DD
        return [s for s in self._load_all() if start_date <= s.date <= end_date]

    def get_by_student_id(self, student_id: str) -> List[Schedule]:
        return [s for s in self._load_all() if s.student_id == student_id]

    def get_by_class_id(self, class_id: str) -> List[Schedule]:
        return [s for s in self._load_all() if s.class_id == class_id]

    def create(self, schedule: Schedule) -> Schedule:
        schedules = self._load_all()
        if any(s.id == schedule.id for s in schedules):
            raise ValueError(f"Lịch học ID '{schedule.id}' đã tồn tại.")
        schedules.append(schedule)
        self._save_all(schedules)
        return schedule

    def update(self, schedule: Schedule) -> Schedule:
        schedules = self._load_all()
        updated = False
        schedule.updated_at = now_iso()
        for idx, s in enumerate(schedules):
            if s.id == schedule.id:
                schedules[idx] = schedule
                updated = True
                break

        if not updated:
            raise NotFoundError(f"Không tìm thấy buổi lịch với ID '{schedule.id}'.")

        self._save_all(schedules)
        return schedule

    def delete(self, schedule_id: str) -> bool:
        schedules = self._load_all()
        initial_len = len(schedules)
        schedules = [s for s in schedules if s.id != schedule_id]
        if len(schedules) == initial_len:
            return False
        self._save_all(schedules)
        return True
