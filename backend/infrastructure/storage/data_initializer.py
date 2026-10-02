"""Data directory and initial schema bootstrapping."""

from backend.infrastructure.storage.json_storage import JsonStorage

DEFAULT_SETTINGS = {
    "center_name": "Melody Piano Studio",
    "teacher_name": "Thầy Đào",
    "phone": "0912345678",
    "theme": "light",
    "first_day_of_week": "MON",
    "default_lesson_duration": 60,
    "default_start_hour": 7,
    "default_end_hour": 20,
    "backup_enabled": True,
    "backup_frequency": "daily",
}


class DataInitializer:
    """Ensures presence and initialization of all persistent data files."""

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def initialize(self) -> None:
        """Create necessary default JSON files if absent."""
        self.storage.read("students.json", default_factory=list)
        self.storage.read("classes.json", default_factory=list)
        self.storage.read("schedules.json", default_factory=list)
        self.storage.read("attendances.json", default_factory=list)
        self.storage.read("payments.json", default_factory=list)
        self.storage.read("settings.json", default_factory=lambda: DEFAULT_SETTINGS.copy())
