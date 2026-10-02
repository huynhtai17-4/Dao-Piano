"""Abstract repository contract for Attendance persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.domain.models.attendance import Attendance


class AttendanceRepository(ABC):
    """Contract for attendance storage and query operations."""

    @abstractmethod
    def get_all(self) -> List[Attendance]:
        """Retrieve all attendance records."""

    @abstractmethod
    def get_by_id(self, attendance_id: str) -> Optional[Attendance]:
        """Retrieve attendance record by ID."""

    @abstractmethod
    def get_by_schedule_and_student(self, schedule_id: str, student_id: str) -> Optional[Attendance]:
        """Retrieve specific attendance entry for a student in a schedule."""

    @abstractmethod
    def get_by_schedule_id(self, schedule_id: str) -> List[Attendance]:
        """Retrieve all attendance entries for a schedule."""

    @abstractmethod
    def get_by_student_id(self, student_id: str) -> List[Attendance]:
        """Retrieve attendance history for a student."""

    @abstractmethod
    def create(self, attendance: Attendance) -> Attendance:
        """Persist a new attendance record."""

    @abstractmethod
    def update(self, attendance: Attendance) -> Attendance:
        """Update an existing attendance record."""

    @abstractmethod
    def delete(self, attendance_id: str) -> bool:
        """Delete an attendance record by ID."""
