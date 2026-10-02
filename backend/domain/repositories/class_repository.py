"""Abstract repository contract for ClassModel persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.domain.models.class_model import ClassModel
from backend.core.enums import ClassType


class ClassRepository(ABC):
    """Contract for class storage and query operations."""

    @abstractmethod
    def get_all(self) -> List[ClassModel]:
        """Retrieve all class models."""

    @abstractmethod
    def get_by_id(self, class_id: str) -> Optional[ClassModel]:
        """Retrieve class by unique ID."""

    @abstractmethod
    def get_by_type(self, class_type: ClassType) -> List[ClassModel]:
        """Retrieve classes matching a specific type."""

    @abstractmethod
    def create(self, class_model: ClassModel) -> ClassModel:
        """Persist a new class entity."""

    @abstractmethod
    def update(self, class_model: ClassModel) -> ClassModel:
        """Update an existing class entity."""

    @abstractmethod
    def delete(self, class_id: str) -> bool:
        """Delete a class by ID."""
