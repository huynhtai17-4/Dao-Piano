"""JSON-backed implementation of PaymentRepository."""

from __future__ import annotations
from typing import List, Optional
from backend.domain.models.payment import Payment
from backend.domain.repositories.payment_repository import PaymentRepository
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.core.exceptions import CorruptedDataError


class JsonPaymentRepository(PaymentRepository):
    """Repository storing and querying payments via atomic JSON storage."""

    FILE_NAME = "payments.json"

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def _load_all(self) -> List[Payment]:
        raw_list = self.storage.read(self.FILE_NAME, default_factory=list)
        try:
            return [Payment.model_validate(item) for item in raw_list]
        except Exception as e:
            raise CorruptedDataError(f"Dữ liệu học phí không hợp lệ: {e}") from e

    def _save_all(self, payments: List[Payment]) -> None:
        payload = [p.model_dump() for p in payments]
        self.storage.write(self.FILE_NAME, payload)

    def get_all(self) -> List[Payment]:
        return self._load_all()

    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        for p in self._load_all():
            if p.id == payment_id:
                return p
        return None

    def get_by_student_id(self, student_id: str) -> List[Payment]:
        return [p for p in self._load_all() if p.student_id == student_id]

    def get_by_date_range(self, start_date: str, end_date: str) -> List[Payment]:
        return [p for p in self._load_all() if start_date <= p.payment_date <= end_date]

    def create(self, payment: Payment) -> Payment:
        payments = self._load_all()
        if any(p.id == payment.id for p in payments):
            raise ValueError(f"Phiếu thu học phí ID '{payment.id}' đã tồn tại.")
        payments.append(payment)
        self._save_all(payments)
        return payment

    def delete(self, payment_id: str) -> bool:
        payments = self._load_all()
        initial_len = len(payments)
        payments = [p for p in payments if p.id != payment_id]
        if len(payments) == initial_len:
            return False
        self._save_all(payments)
        return True
