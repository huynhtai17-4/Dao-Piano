"""Atomic JSON file writer to guarantee crash-resilient data persistence."""

from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from backend.core.exceptions import StorageError


def write_atomic_json(target_path: Path | str, data: Any, indent: int = 2) -> None:
    """Atomically write Python data structure to a target JSON file.

    Guarantees:
    1. Parent directories are created if missing.
    2. Data is written to a temporary file in the same folder.
    3. File buffer is flushed and synced to physical storage (fsync).
    4. Sibling temp file replaces target atomically via os.replace.
    5. Clean teardown: Temporary files are discarded if write fails.
    """
    path = Path(target_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        # Create temp file in same directory so it shares the same filesystem volume
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
            temp_path = Path(tmp_file.name)
            json.dump(data, tmp_file, ensure_ascii=False, indent=indent, default=str)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        # Atomic rename/replace operation
        os.replace(temp_path, path)
    except Exception as e:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise StorageError(f"Lỗi ghi dữ liệu atomic vào file '{path.name}': {e}") from e
