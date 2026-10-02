"""Class management application service enforcing capacity and editing restrictions."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.class_model import ClassModel
from backend.domain.repositories.class_repository import ClassRepository
from backend.domain.repositories.student_repository import StudentRepository
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.application.dto.class_dto import ClassCreateDTO, ClassUpdateDTO, ClassResponseDTO
from backend.core.enums import ClassType
from backend.core.exceptions import NotFoundError, ClassEditRestrictedError, BusinessRuleViolationError
from backend.core.event_bus import event_bus


class ClassService:
    """Orchestrates classroom lifecycle and rules."""

    def __init__(
        self,
        class_repo: ClassRepository,
        student_repo: StudentRepository,
        schedule_repo: Optional[ScheduleRepository] = None,
    ) -> None:
        self.class_repo = class_repo
        self.student_repo = student_repo
        self.schedule_repo = schedule_repo

    def _to_response_dto(self, c: ClassModel) -> ClassResponseDTO:
        count = len(c.student_ids)
        return ClassResponseDTO(
            id=c.id,
            name=c.name,
            class_type=c.class_type,
            class_type_display=c.class_type.display_name,
            current_student_count=count,
            max_students=c.max_students,
            student_ids=list(c.student_ids),
            created_at=c.created_at,
            updated_at=c.updated_at,
            is_full=count >= c.max_students,
        )

    def get_classes(self, class_type: Optional[ClassType] = None) -> List[ClassResponseDTO]:
        if class_type:
            classes = self.class_repo.get_by_type(class_type)
        else:
            classes = self.class_repo.get_all()
        return [self._to_response_dto(c) for c in classes]

    def get_class_by_id(self, class_id: str) -> ClassResponseDTO:
        c = self.class_repo.get_by_id(class_id)
        if not c:
            raise NotFoundError(f"Không tìm thấy lớp học ID '{class_id}'.")
        return self._to_response_dto(c)

    def create_class(self, dto: ClassCreateDTO) -> ClassResponseDTO:
        max_stu = 1 if dto.class_type == ClassType.ONE_ON_ONE else max(1, dto.max_students)
        new_class = ClassModel(
            name=dto.name.strip(),
            class_type=dto.class_type,
            max_students=max_stu,
            student_ids=[],
        )
        persisted = self.class_repo.create(new_class)
        event_bus.emit("classes_changed", persisted.id)
        return self._to_response_dto(persisted)

    def update_class(self, dto: ClassUpdateDTO) -> ClassResponseDTO:
        existing = self.class_repo.get_by_id(dto.id)
        if not existing:
            raise NotFoundError(f"Không tìm thấy lớp học ID '{dto.id}'.")

        # Business Rule: OFFLINE class editing constraint
        if existing.class_type == ClassType.OFFLINE:
            if dto.name.strip() != existing.name:
                raise ClassEditRestrictedError(
                    "Lớp Offline chỉ cho phép sửa sĩ số tối đa, không thể đổi tên lớp."
                )
            if dto.class_type != existing.class_type:
                raise ClassEditRestrictedError(
                    "Không thể thay đổi loại lớp của lớp Offline."
                )

        # Business Rule: ONE_ON_ONE always max_students = 1
        if existing.class_type == ClassType.ONE_ON_ONE:
            new_max = 1
        else:
            new_max = max(1, dto.max_students)

        # Invariant: max_students cannot be less than enrolled students
        if new_max < len(existing.student_ids):
            raise BusinessRuleViolationError(
                f"Sĩ số tối đa ({new_max}) không được nhỏ hơn số học sinh hiện có ({len(existing.student_ids)})."
            )

        existing.name = dto.name.strip()
        existing.max_students = new_max
        updated = self.class_repo.update(existing)
        event_bus.emit("classes_changed", updated.id)
        return self._to_response_dto(updated)

    def delete_class(self, class_id: str) -> bool:
        existing = self.class_repo.get_by_id(class_id)
        if not existing:
            return False

        # Clear class assignment for all students currently in this class
        for s in self.student_repo.get_by_class_id(class_id):
            s.class_id = None
            self.student_repo.update(s)

        # Cascade delete all schedules for this class
        if self.schedule_repo:
            all_schedules = self.schedule_repo.get_all()
            for s in all_schedules:
                if s.class_id == class_id:
                    self.schedule_repo.delete(s.id)

        result = self.class_repo.delete(class_id)
        event_bus.emit("classes_changed", class_id)
        event_bus.emit("schedules_changed", class_id)
        return result
