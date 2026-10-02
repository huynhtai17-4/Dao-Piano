"""Thread-safe JSON persistence storage manager with high-speed in-memory cache."""

from __future__ import annotations
import copy
import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from backend.core.exceptions import StorageError, CorruptedDataError
from backend.infrastructure.storage.atomic_writer import write_atomic_json


class JsonStorage:
    """Safely manages reading and atomic writing of local JSON data with mtime-based memory cache."""

    def __init__(self, data_dir: Path | str = "data") -> None:
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def get_path(self, filename: str) -> Path:
        """Resolve full path to a file inside data directory."""
        if not filename.endswith(".json"):
            filename = f"{filename}.json"
        return self.data_dir / filename

    def read(self, filename: str, default_factory: Optional[Callable[[], Any]] = None) -> Any:
        """Read and parse JSON content from target file with mtime-based memory cache."""
        file_path = self.get_path(filename)
        with self._lock:
            if not file_path.exists():
                if default_factory is not None:
                    default_data = default_factory()
                    self.write(filename, default_data)
                    return copy.deepcopy(default_data)
                raise StorageError(f"Không tìm thấy file dữ liệu: {file_path.name}")

            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                mtime = 0.0

            if filename in self._cache:
                cached_mtime, cached_data = self._cache[filename]
                if cached_mtime == mtime:
                    return copy.deepcopy(cached_data)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        # Empty file handled gracefully
                        val = default_factory() if default_factory is not None else []
                        self._cache[filename] = (mtime, val)
                        return copy.deepcopy(val)
                    data = json.loads(content)
                    self._cache[filename] = (mtime, data)
                    return copy.deepcopy(data)
            except json.JSONDecodeError as err:
                raise CorruptedDataError(
                    f"File dữ liệu '{file_path.name}' bị hỏng (JSON format error): {err}"
                ) from err
            except OSError as err:
                raise StorageError(f"Lỗi đọc file dữ liệu '{file_path.name}': {err}") from err

    def write(self, filename: str, data: Any) -> None:
        """Atomically persist data structure to target JSON file and update cache."""
        file_path = self.get_path(filename)
        with self._lock:
            write_atomic_json(file_path, data)
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                mtime = 0.0
            self._cache[filename] = (mtime, copy.deepcopy(data))

    def clear_cache(self) -> None:
        """Evict all cached entries."""
        with self._lock:
            self._cache.clear()

    def file_exists(self, filename: str) -> bool:
        """Check whether a specific data file exists."""
        return self.get_path(filename).exists()
