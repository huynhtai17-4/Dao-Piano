"""Core exception hierarchy for Piano Center Manager."""


class PianoAppError(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__

    def __str__(self) -> str:
        return self.message


class ValidationError(PianoAppError):
    """Raised when data fails domain or input validation rules."""


class NotFoundError(PianoAppError):
    """Raised when a requested entity cannot be found."""


class ConflictError(PianoAppError):
    """Raised when an operation encounters state conflict."""


class ScheduleConflictError(ConflictError):
    """Raised when a proposed schedule overlaps with an existing student or class booking."""


class BusinessRuleViolationError(PianoAppError):
    """Raised when an operation violates a domain invariant."""


class CapacityExceededError(BusinessRuleViolationError):
    """Raised when attempting to add students beyond class capacity."""


class InsufficientLessonsError(BusinessRuleViolationError):
    """Raised when deducting lessons from a student with zero or insufficient balance."""


class ClassEditRestrictedError(BusinessRuleViolationError):
    """Raised when attempting to modify immutable class properties."""


class StorageError(PianoAppError):
    """Base class for infrastructure persistence failures."""


class CorruptedDataError(StorageError):
    """Raised when stored JSON contains unparsable or malformed content."""


class BackupError(StorageError):
    """Raised when backup creation or restoration fails."""
