"""Reset persistent JSON storage to clean default state."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.storage.data_initializer import DataInitializer, DEFAULT_SETTINGS


def reset_all_data() -> None:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    storage = JsonStorage(data_dir=data_dir)

    storage.write("students.json", [])
    storage.write("classes.json", [])
    storage.write("schedules.json", [])
    storage.write("attendances.json", [])
    storage.write("payments.json", [])
    storage.write("settings.json", DEFAULT_SETTINGS.copy())
    print("[SUCCESS] Đã xóa và đặt lại dữ liệu sạch cho Piano Center Manager.")


if __name__ == "__main__":
    reset_all_data()
