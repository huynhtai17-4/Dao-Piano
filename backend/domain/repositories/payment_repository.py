"""Abstract repository contract for Payment persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.domain.models.payment import Payment


class PaymentRepository(ABC):
    """Contract for payment storage and query operations."""

    @abstractmethod
    def get_all(self) -> List[Payment]:
        """Retrieve all payment records."""

    @abstractmethod
    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Retrieve payment by ID."""

    @abstractmethod
    def get_by_student_id(self, student_id: str) -> List[Payment]:
        """Retrieve all payment transactions for a given student."""

    @abstractmethod
    def get_by_date_range(self, start_date: str, end_date: str) -> List[Payment]:
        """Retrieve payment records within a date range."""

    @abstractmethod
    def create(self, payment: Payment) -> Payment:
        """Persist a new payment record."""

    @abstractmethod
    def delete(self, payment_id: str) -> bool:
        """Delete a payment record by ID."""
