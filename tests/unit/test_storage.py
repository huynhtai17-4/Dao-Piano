"""Unit tests for atomic JSON storage and backup manager."""

import tempfile
import pytest
from pathlib import Path
from backend.infrastructure.storage.atomic_writer import write_atomic_json
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.storage.backup_manager import BackupManager
from backend.core.exceptions import CorruptedDataError, StorageError


def test_atomic_write_and_read():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        sample_data = [{"id": 1, "name": "Test Item"}]

        storage.write("test_items.json", sample_data)
        loaded = storage.read("test_items.json")
        assert loaded == sample_data


def test_corrupted_json_raises_custom_error():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        bad_file = Path(tmp_dir) / "corrupt.json"
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("{invalid json syntax,,}")

        with pytest.raises(CorruptedDataError):
            storage.read("corrupt.json")


def test_missing_file_with_default_factory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        loaded = storage.read("new_file.json", default_factory=list)
        assert loaded == []
        assert (Path(tmp_dir) / "new_file.json").exists()


def test_backup_and_restore():
    with tempfile.TemporaryDirectory() as tmp_data_dir:
        with tempfile.TemporaryDirectory() as tmp_backup_dir:
            storage = JsonStorage(tmp_data_dir)
            bm = BackupManager(tmp_data_dir, tmp_backup_dir)

            storage.write("students.json", [{"id": "s1", "name": "Original"}])

            # Create backup
            backup_folder = bm.create_backup("test_snapshot")
            assert backup_folder.exists()

            # Overwrite original data
            storage.write("students.json", [{"id": "s1", "name": "Modified"}])
            assert storage.read("students.json")[0]["name"] == "Modified"

            # Restore
            bm.restore_backup(backup_folder.name)
            restored = storage.read("students.json")
            assert restored[0]["name"] == "Original"
