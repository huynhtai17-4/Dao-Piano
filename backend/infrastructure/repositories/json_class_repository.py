"""JSON-backed implementation of ClassRepository."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.class_model import ClassModel
from backend.domain.repositories.class_repository import ClassRepository
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.core.enums import ClassType
from backend.core.dates import now_iso
from backend.core.exceptions import NotFoundError, CorruptedDataError


class JsonClassRepository(ClassRepository):
    """Repository storing and querying classes via atomic JSON storage."""

    FILE_NAME = "classes.json"

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def _load_all(self) -> List[ClassModel]:
        raw_list = self.storage.read(self.FILE_NAME, default_factory=list)
        try:
            return [ClassModel.model_validate(item) for item in raw_list]
        except Exception as e:
            raise CorruptedDataError(f"Dữ liệu lớp học không hợp lệ: {e}") from e

    def _save_all(self, classes: List[ClassModel]) -> None:
        payload = [c.model_dump() for c in classes]
        self.storage.write(self.FILE_NAME, payload)

    def get_all(self) -> List[ClassModel]:
        return self._load_all()

    def get_by_id(self, class_id: str) -> Optional[ClassModel]:
        for c in self._load_all():
            if c.id == class_id:
                return c
        return None

    def get_by_type(self, class_type: ClassType) -> List[ClassModel]:
        return [c for c in self._load_all() if c.class_type == class_type]

    def create(self, class_model: ClassModel) -> ClassModel:
        classes = self._load_all()
        if any(c.id == class_model.id for c in classes):
            raise ValueError(f"Lớp học ID '{class_model.id}' đã tồn tại.")
        classes.append(class_model)
        self._save_all(classes)
        return class_model

    def update(self, class_model: ClassModel) -> ClassModel:
        classes = self._load_all()
        updated = False
        class_model.updated_at = now_iso()
        for idx, c in enumerate(classes):
            if c.id == class_model.id:
                classes[idx] = class_model
                updated = True
                break

        if not updated:
            raise NotFoundError(f"Không tìm thấy lớp học với ID '{class_model.id}'.")

        self._save_all(classes)
        return class_model

    def delete(self, class_id: str) -> bool:
        classes = self._load_all()
        initial_len = len(classes)
        classes = [c for c in classes if c.id != class_id]
        if len(classes) == initial_len:
            return False
        self._save_all(classes)
        return True
