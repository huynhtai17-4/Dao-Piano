"""Generic Result type for explicit success and error handling without unwrapped exceptions."""

from __future__ import annotations
from typing import Generic, TypeVar, Optional, Callable

T = TypeVar("T")
E = TypeVar("E")


class Result(Generic[T]):
    """Represents either a success with a value of type T, or a failure with an error message or exception."""

    __slots__ = ("_is_success", "_value", "_error")

    def __init__(self, is_success: bool, value: Optional[T] = None, error: Optional[str] = None) -> None:
        self._is_success = is_success
        self._value = value
        self._error = error

    @classmethod
    def ok(cls, value: T) -> Result[T]:
        """Create a successful Result."""
        return cls(is_success=True, value=value, error=None)

    @classmethod
    def fail(cls, error: str) -> Result[T]:
        """Create a failed Result with an error message."""
        return cls(is_success=False, value=None, error=error)

    @property
    def is_success(self) -> bool:
        return self._is_success

    @property
    def is_failure(self) -> bool:
        return not self._is_success

    @property
    def value(self) -> T:
        if not self._is_success:
            raise ValueError(f"Cannot access value on failed Result: {self._error}")
        return self._value  # type: ignore[return-value]

    @property
    def error(self) -> str:
        if self._is_success:
            raise ValueError("Cannot access error on successful Result")
        return self._error or "Unknown error"

    def value_or(self, default: T) -> T:
        """Return the value if successful, otherwise return default."""
        return self._value if self._is_success else default  # type: ignore[return-value]

    def map(self, fn: Callable[[T], E]) -> Result[E]:
        """Transform successful value, or propagate failure."""
        if self._is_success:
            return Result.ok(fn(self.value))
        return Result.fail(self.error)

    def __repr__(self) -> str:
        if self._is_success:
            return f"Result.ok({self._value!r})"
        return f"Result.fail({self._error!r})"
