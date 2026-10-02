"""JSON-backed implementation of StudentRepository."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.student import Student
from backend.domain.repositories.student_repository import StudentRepository
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.core.enums import ClassType
from backend.core.dates import now_iso
from backend.core.exceptions import NotFoundError, CorruptedDataError


class JsonStudentRepository(StudentRepository):
    """Repository storing and querying students via atomic JSON storage."""

    FILE_NAME = "students.json"

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def _load_all(self) -> List[Student]:
        raw_list = self.storage.read(self.FILE_NAME, default_factory=list)
        try:
            return [Student.model_validate(item) for item in raw_list]
        except Exception as e:
            raise CorruptedDataError(f"Dữ liệu học sinh không hợp lệ: {e}") from e

    def _save_all(self, students: List[Student]) -> None:
        payload = [s.model_dump() for s in students]
        self.storage.write(self.FILE_NAME, payload)

    def get_all(self, active_only: bool = True) -> List[Student]:
        students = self._load_all()
        if active_only:
            return [s for s in students if s.is_active]
        return students

    def get_by_id(self, student_id: str) -> Optional[Student]:
        students = self._load_all()
        for s in students:
            if s.id == student_id:
                return s
        return None

    def get_by_class_id(self, class_id: str) -> List[Student]:
        students = self._load_all()
        return [s for s in students if s.is_active and s.class_id == class_id]

    def get_by_class_type(self, class_type: ClassType) -> List[Student]:
        students = self._load_all()
        return [s for s in students if s.is_active and s.class_type == class_type]

    def create(self, student: Student) -> Student:
        students = self._load_all()
        if any(s.id == student.id for s in students):
            raise ValueError(f"Học sinh có ID '{student.id}' đã tồn tại.")
        students.append(student)
        self._save_all(students)
        return student

    def update(self, student: Student) -> Student:
        students = self._load_all()
        updated = False
        student.updated_at = now_iso()
        for idx, s in enumerate(students):
            if s.id == student.id:
                students[idx] = student
                updated = True
                break

        if not updated:
            raise NotFoundError(f"Không tìm thấy học sinh với ID '{student.id}' để cập nhật.")

        self._save_all(students)
        return student

    def delete(self, student_id: str) -> bool:
        students = self._load_all()
        initial_len = len(students)
        students = [s for s in students if s.id != student_id]
        if len(students) == initial_len:
            return False
        self._save_all(students)
        return True
