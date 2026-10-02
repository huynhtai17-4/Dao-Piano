"""Abstract repository contract for Student persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.domain.models.student import Student
from backend.core.enums import ClassType


class StudentRepository(ABC):
    """Contract for student storage and query operations."""

    @abstractmethod
    def get_all(self, active_only: bool = True) -> List[Student]:
        """Retrieve all students, optionally filtered to active only."""

    @abstractmethod
    def get_by_id(self, student_id: str) -> Optional[Student]:
        """Retrieve a student by unique ID."""

    @abstractmethod
    def get_by_class_id(self, class_id: str) -> List[Student]:
        """Retrieve all students assigned to a specific class."""

    @abstractmethod
    def get_by_class_type(self, class_type: ClassType) -> List[Student]:
        """Retrieve students filtered by class instructional type."""

    @abstractmethod
    def create(self, student: Student) -> Student:
        """Persist a new student entity."""

    @abstractmethod
    def update(self, student: Student) -> Student:
        """Update an existing student entity."""

    @abstractmethod
    def delete(self, student_id: str) -> bool:
        """Delete or deactivate a student by ID."""
