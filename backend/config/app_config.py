"""Application settings manager."""

from __future__ import annotations
from typing import Any, Dict
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.storage.data_initializer import DEFAULT_SETTINGS


class AppConfig:
    """Provides validated configuration properties and persistent settings."""

    FILE_NAME = "settings.json"

    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage
        self._settings: Dict[str, Any] = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        try:
            data = self.storage.read(self.FILE_NAME, default_factory=lambda: DEFAULT_SETTINGS.copy())
            if isinstance(data, dict):
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                return merged
        except Exception:
            pass
        return DEFAULT_SETTINGS.copy()

    def get_all(self) -> Dict[str, Any]:
        return self._settings.copy()

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def update(self, new_values: Dict[str, Any]) -> None:
        self._settings.update(new_values)
        self.storage.write(self.FILE_NAME, self._settings)

    @property
    def center_name(self) -> str:
        return str(self.get("center_name", "Melody Piano Studio"))

    @property
    def teacher_name(self) -> str:
        return str(self.get("teacher_name", "Thầy Đào"))

    @property
    def phone(self) -> str:
        return str(self.get("phone", "0912345678"))

    @property
    def theme_mode(self) -> str:
        return str(self.get("theme", "light"))
