"""JSON-backed implementation of AttendanceRepository."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.attendance import Attendance
from backend.domain.repositories.attendance_repository import AttendanceRepository
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.core.exceptions import NotFoundError, CorruptedDataError


class JsonAttendanceRepository(AttendanceRepository):
    """Repository storing and querying attendance records via atomic JSON storage."""

    FILE_NAME = "attendances.json"

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def _load_all(self) -> List[Attendance]:
        raw_list = self.storage.read(self.FILE_NAME, default_factory=list)
        try:
            return [Attendance.model_validate(item) for item in raw_list]
        except Exception as e:
            raise CorruptedDataError(f"Dữ liệu điểm danh không hợp lệ: {e}") from e

    def _save_all(self, attendances: List[Attendance]) -> None:
        payload = [a.model_dump() for a in attendances]
        self.storage.write(self.FILE_NAME, payload)

    def get_all(self) -> List[Attendance]:
        return self._load_all()

    def get_by_id(self, attendance_id: str) -> Optional[Attendance]:
        for a in self._load_all():
            if a.id == attendance_id:
                return a
        return None

    def get_by_schedule_and_student(self, schedule_id: str, student_id: str) -> Optional[Attendance]:
        for a in self._load_all():
            if a.schedule_id == schedule_id and a.student_id == student_id:
                return a
        return None

    def get_by_schedule_id(self, schedule_id: str) -> List[Attendance]:
        return [a for a in self._load_all() if a.schedule_id == schedule_id]

    def get_by_student_id(self, student_id: str) -> List[Attendance]:
        return [a for a in self._load_all() if a.student_id == student_id]

    def create(self, attendance: Attendance) -> Attendance:
        attendances = self._load_all()
        if any(a.id == attendance.id for a in attendances):
            raise ValueError(f"Bản ghi điểm danh ID '{attendance.id}' đã tồn tại.")
        attendances.append(attendance)
        self._save_all(attendances)
        return attendance

    def update(self, attendance: Attendance) -> Attendance:
        attendances = self._load_all()
        updated = False
        for idx, a in enumerate(attendances):
            if a.id == attendance.id:
                attendances[idx] = attendance
                updated = True
                break

        if not updated:
            raise NotFoundError(f"Không tìm thấy bản ghi điểm danh ID '{attendance.id}'.")

        self._save_all(attendances)
        return attendance

    def delete(self, attendance_id: str) -> bool:
        attendances = self._load_all()
        initial_len = len(attendances)
        attendances = [a for a in attendances if a.id != attendance_id]
        if len(attendances) == initial_len:
            return False
        self._save_all(attendances)
        return True
