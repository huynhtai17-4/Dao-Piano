"""Abstract repository contract for Schedule persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.domain.models.schedule import Schedule


class ScheduleRepository(ABC):
    """Contract for schedule storage and query operations."""

    @abstractmethod
    def get_all(self) -> List[Schedule]:
        """Retrieve all schedule events."""

    @abstractmethod
    def get_by_id(self, schedule_id: str) -> Optional[Schedule]:
        """Retrieve schedule by unique ID."""

    @abstractmethod
    def get_by_date_range(self, start_date: str, end_date: str) -> List[Schedule]:
        """Retrieve schedules between two dates (inclusive, format YYYY-MM-DD)."""

    @abstractmethod
    def get_by_student_id(self, student_id: str) -> List[Schedule]:
        """Retrieve all schedules explicitly involving a specific student."""

    @abstractmethod
    def get_by_class_id(self, class_id: str) -> List[Schedule]:
        """Retrieve all schedules for a specific class."""

    @abstractmethod
    def create(self, schedule: Schedule) -> Schedule:
        """Persist a new schedule event."""

    @abstractmethod
    def update(self, schedule: Schedule) -> Schedule:
        """Update an existing schedule event."""

    @abstractmethod
    def delete(self, schedule_id: str) -> bool:
        """Delete a schedule event by ID."""
