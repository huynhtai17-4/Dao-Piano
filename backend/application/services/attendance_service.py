"""Attendance tracking service enforcing lesson balance invariance and idempotency."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.attendance import Attendance
from backend.domain.repositories.attendance_repository import AttendanceRepository
from backend.domain.repositories.student_repository import StudentRepository
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.application.dto.attendance_dto import AttendanceCreateDTO, AttendanceUpdateDTO, AttendanceResponseDTO
from backend.core.enums import AttendanceStatus
from backend.core.exceptions import NotFoundError, InsufficientLessonsError
from backend.core.event_bus import event_bus


class AttendanceService:
    """Manages attendance records and transactional remaining lesson adjustments."""

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        student_repo: StudentRepository,
        schedule_repo: ScheduleRepository,
    ) -> None:
        self.attendance_repo = attendance_repo
        self.student_repo = student_repo
        self.schedule_repo = schedule_repo

    def _to_response_dto(self, a: Attendance) -> AttendanceResponseDTO:
        student = self.student_repo.get_by_id(a.student_id)
        student_name = student.name if student else None
        return AttendanceResponseDTO(
            id=a.id,
            schedule_id=a.schedule_id,
            student_id=a.student_id,
            student_name=student_name,
            attendance_date=a.attendance_date,
            status=a.status,
            status_display=a.status.display_name,
            note=a.note,
            created_at=a.created_at,
        )

    def get_attendance_for_schedule(self, schedule_id: str) -> List[AttendanceResponseDTO]:
        records = self.attendance_repo.get_by_schedule_id(schedule_id)
        return [self._to_response_dto(a) for a in records]

    def get_attendance_for_student(self, student_id: str) -> List[AttendanceResponseDTO]:
        records = self.attendance_repo.get_by_student_id(student_id)
        return [self._to_response_dto(a) for a in records]

    def mark_attendance(self, dto: AttendanceCreateDTO) -> AttendanceResponseDTO:
        """Record or update attendance with transactional lesson balance adjustments."""
        student = self.student_repo.get_by_id(dto.student_id)
        if not student:
            raise NotFoundError(f"Không tìm thấy học sinh ID '{dto.student_id}'.")

        existing = self.attendance_repo.get_by_schedule_and_student(
            schedule_id=dto.schedule_id, student_id=dto.student_id
        )

        old_status = existing.status if existing else None
        new_status = dto.status

        # Calculate exact lesson balance delta:
        # None / ABSENT / RESCHEDULED -> PRESENT  => -1
        # PRESENT -> ABSENT / RESCHEDULED         => +1 (refund)
        # PRESENT -> PRESENT                      =>  0 (idempotent, no double deduction)
        # ABSENT -> ABSENT                        =>  0
        delta = 0
        if old_status != AttendanceStatus.PRESENT and new_status == AttendanceStatus.PRESENT:
            delta = -1
        elif old_status == AttendanceStatus.PRESENT and new_status != AttendanceStatus.PRESENT:
            delta = 1

        # Check balance invariant
        if delta < 0 and student.remaining_lessons + delta < 0:
            raise InsufficientLessonsError(
                f"Học sinh '{student.name}' không còn buổi học khả dụng (số buổi hiện tại: {student.remaining_lessons}). Vui lòng nạp thêm học phí."
            )

        # Apply delta to student if changed
        if delta != 0:
            student.remaining_lessons += delta
            self.student_repo.update(student)

        # Save or update attendance entity
        if existing:
            existing.status = new_status
            existing.note = dto.note
            persisted = self.attendance_repo.update(existing)
        else:
            new_record = Attendance(
                schedule_id=dto.schedule_id,
                student_id=dto.student_id,
                attendance_date=dto.attendance_date,
                status=new_status,
                note=dto.note,
            )
            persisted = self.attendance_repo.create(new_record)

        event_bus.emit("attendance_changed", persisted.id)
        event_bus.emit("students_changed", student.id)
        return self._to_response_dto(persisted)

    def delete_attendance(self, attendance_id: str) -> bool:
        """Delete an attendance record and refund the deducted lesson if status was PRESENT."""
        record = self.attendance_repo.get_by_id(attendance_id)
        if not record:
            return False

        if record.status == AttendanceStatus.PRESENT:
            student = self.student_repo.get_by_id(record.student_id)
            if student:
                student.remaining_lessons += 1
                self.student_repo.update(student)
                event_bus.emit("students_changed", student.id)

        result = self.attendance_repo.delete(attendance_id)
        event_bus.emit("attendance_changed", attendance_id)
        return result
