"""Student management application service enforcing domain invariants."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.student import Student
from backend.domain.repositories.student_repository import StudentRepository
from backend.domain.repositories.class_repository import ClassRepository
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.application.dto.student_dto import StudentCreateDTO, StudentUpdateDTO, StudentResponseDTO
from backend.core.enums import ClassType
from backend.core.exceptions import NotFoundError, CapacityExceededError
from backend.core.event_bus import event_bus


class StudentService:
    """Orchestrates student registrations, class assignments, and balance tracking."""

    def __init__(
        self,
        student_repo: StudentRepository,
        class_repo: ClassRepository,
        schedule_repo: Optional[ScheduleRepository] = None,
    ) -> None:
        self.student_repo = student_repo
        self.class_repo = class_repo
        self.schedule_repo = schedule_repo

    def _to_response_dto(self, student: Student, class_cache: Optional[dict] = None) -> StudentResponseDTO:
        class_name = None
        if student.class_id:
            if class_cache is not None and student.class_id in class_cache:
                c = class_cache[student.class_id]
                class_name = c.name if c else None
            else:
                c = self.class_repo.get_by_id(student.class_id)
                class_name = c.name if c else None

        if student.remaining_lessons == 0:
            status_level = "critical"
        elif student.remaining_lessons <= 2:
            status_level = "warning"
        else:
            status_level = "normal"

        return StudentResponseDTO(
            id=student.id,
            name=student.name,
            phone=student.phone,
            date_of_birth=student.date_of_birth,
            class_type=student.class_type,
            class_type_display=student.class_type.display_name,
            class_id=student.class_id,
            class_name=class_name,
            remaining_lessons=student.remaining_lessons,
            created_at=student.created_at,
            updated_at=student.updated_at,
            is_active=student.is_active,
            status_level=status_level,
        )

    def get_students(
        self,
        active_only: bool = True,
        class_type: Optional[ClassType] = None,
        class_id: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[StudentResponseDTO]:
        students = self.student_repo.get_all(active_only=active_only)

        if class_type:
            students = [s for s in students if s.class_type == class_type]
        if class_id:
            students = [s for s in students if s.class_id == class_id]
        if search_query:
            q = search_query.strip().lower()
            students = [s for s in students if q in s.name.lower() or q in s.phone]

        # Cache classes for fast DTO building
        all_classes = {c.id: c for c in self.class_repo.get_all()}
        return [self._to_response_dto(s, all_classes) for s in students]

    def get_student_by_id(self, student_id: str) -> StudentResponseDTO:
        student = self.student_repo.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Không tìm thấy học sinh với ID '{student_id}'.")
        return self._to_response_dto(student)

    def create_student(self, dto: StudentCreateDTO) -> StudentResponseDTO:
        # Check class capacity if assigned to a class
        if dto.class_id:
            target_class = self.class_repo.get_by_id(dto.class_id)
            if not target_class:
                raise NotFoundError(f"Lớp học ID '{dto.class_id}' không tồn tại.")
            if len(target_class.student_ids) >= target_class.max_students:
                raise CapacityExceededError(
                    f"Lớp '{target_class.name}' đã đầy sĩ số ({target_class.max_students}/{target_class.max_students})."
                )

        new_student = Student(
            name=dto.name,
            phone=dto.phone,
            date_of_birth=dto.date_of_birth,
            class_type=dto.class_type,
            class_id=dto.class_id,
            remaining_lessons=dto.remaining_lessons,
        )

        persisted = self.student_repo.create(new_student)

        # Update class roster if assigned
        if dto.class_id and target_class:
            if persisted.id not in target_class.student_ids:
                target_class.student_ids.append(persisted.id)
                self.class_repo.update(target_class)

        event_bus.emit("students_changed", persisted.id)
        return self._to_response_dto(persisted)

    def update_student(self, dto: StudentUpdateDTO) -> StudentResponseDTO:
        student = self.student_repo.get_by_id(dto.id)
        if not student:
            raise NotFoundError(f"Không tìm thấy học sinh ID '{dto.id}'.")

        old_class_id = student.class_id
        new_class_id = dto.class_id

        # If changing class, verify new class capacity and update rosters
        if old_class_id != new_class_id:
            if new_class_id:
                new_class = self.class_repo.get_by_id(new_class_id)
                if not new_class:
                    raise NotFoundError(f"Lớp học ID '{new_class_id}' không tồn tại.")
                if len(new_class.student_ids) >= new_class.max_students:
                    raise CapacityExceededError(
                        f"Lớp '{new_class.name}' đã đầy sĩ số ({new_class.max_students}/{new_class.max_students})."
                    )
                new_class.student_ids.append(student.id)
                self.class_repo.update(new_class)

            if old_class_id:
                old_class = self.class_repo.get_by_id(old_class_id)
                if old_class and student.id in old_class.student_ids:
                    old_class.student_ids.remove(student.id)
                    self.class_repo.update(old_class)

        student.name = dto.name
        student.phone = dto.phone
        student.date_of_birth = dto.date_of_birth
        student.class_type = dto.class_type
        student.class_id = dto.class_id
        student.remaining_lessons = dto.remaining_lessons
        student.is_active = dto.is_active

        updated = self.student_repo.update(student)
        event_bus.emit("students_changed", updated.id)
        return self._to_response_dto(updated)

    def delete_student(self, student_id: str) -> bool:
        student = self.student_repo.get_by_id(student_id)
        if not student:
            return False

        # Remove from assigned class roster
        if student.class_id:
            target_class = self.class_repo.get_by_id(student.class_id)
            if target_class and student.id in target_class.student_ids:
                target_class.student_ids.remove(student.id)
                self.class_repo.update(target_class)

        # Cascade delete schedules specifically for this student
        if self.schedule_repo:
            all_schedules = self.schedule_repo.get_all()
            for s in all_schedules:
                if s.student_id == student_id:
                    self.schedule_repo.delete(s.id)

        result = self.student_repo.delete(student_id)
        event_bus.emit("students_changed", student_id)
        event_bus.emit("schedules_changed", student_id)
        return result

    def adjust_remaining_lessons(self, student_id: str, value: int, is_delta: bool = False) -> StudentResponseDTO:
        """Directly adjust remaining lessons for a student either by absolute value or delta."""
        student = self.student_repo.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Không tìm thấy học sinh ID '{student_id}'.")

        if is_delta:
            new_lessons = max(0, student.remaining_lessons + value)
        else:
            new_lessons = max(0, value)

        student.remaining_lessons = new_lessons
        updated = self.student_repo.update(student)
        event_bus.emit("students_changed", updated.id)
        return self._to_response_dto(updated)
