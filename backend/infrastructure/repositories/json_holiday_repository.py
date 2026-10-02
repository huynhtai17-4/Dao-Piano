"""JSON-backed implementation of Holiday repository."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.holiday import Holiday
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.core.exceptions import CorruptedDataError


class JsonHolidayRepository:
    """Repository storing and querying holidays via atomic JSON storage."""

    FILE_NAME = "holidays.json"

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def _load_all(self) -> List[Holiday]:
        raw_list = self.storage.read(self.FILE_NAME, default_factory=list)
        try:
            return [Holiday.model_validate(item) for item in raw_list]
        except Exception as e:
            raise CorruptedDataError(f"Dữ liệu lịch nghỉ không hợp lệ: {e}") from e

    def _save_all(self, holidays: List[Holiday]) -> None:
        payload = [h.model_dump() for h in holidays]
        self.storage.write(self.FILE_NAME, payload)

    def get_all(self) -> List[Holiday]:
        return sorted(self._load_all(), key=lambda h: h.start_date)

    def get_by_id(self, holiday_id: str) -> Optional[Holiday]:
        for h in self._load_all():
            if h.id == holiday_id:
                return h
        return None

    def create(self, holiday: Holiday) -> Holiday:
        holidays = self._load_all()
        holidays.append(holiday)
        self._save_all(holidays)
        return holiday

    def delete(self, holiday_id: str) -> bool:
        holidays = self._load_all()
        initial_len = len(holidays)
        remaining = [h for h in holidays if h.id != holiday_id]
        if len(remaining) < initial_len:
            self._save_all(remaining)
            return True
        return False
