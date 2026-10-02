"""Automated and on-demand local backup and recovery manager."""

from __future__ import annotations
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from backend.core.exceptions import BackupError, CorruptedDataError
from backend.infrastructure.storage.atomic_writer import write_atomic_json


class BackupManager:
    """Manages snapshot backups and safe rollbacks of all application JSON data."""

    def __init__(self, data_dir: Path | str = "data", backup_dir: Path | str = "backups", max_backups: int = 15) -> None:
        self.data_dir = Path(data_dir).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.max_backups = max_backups

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, reason: str = "manual") -> Path:
        """Create a timestamped snapshot of all current data files."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        target_folder = self.backup_dir / f"{timestamp}_{reason}"
        target_folder.mkdir(parents=True, exist_ok=True)

        try:
            copied_count = 0
            for json_file in self.data_dir.glob("*.json"):
                if json_file.is_file():
                    shutil.copy2(json_file, target_folder / json_file.name)
                    copied_count += 1

            # Write metadata manifest
            manifest = {
                "timestamp": timestamp,
                "reason": reason,
                "files_count": copied_count,
                "created_at": datetime.now().isoformat(),
            }
            write_atomic_json(target_folder / "manifest.json", manifest)

            # Cleanup older backups exceeding retention limit
            self._prune_old_backups()
            return target_folder
        except Exception as e:
            if target_folder.exists():
                shutil.rmtree(target_folder, ignore_errors=True)
            raise BackupError(f"Tạo bản sao lưu thất bại: {e}") from e

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backup snapshots ordered from newest to oldest."""
        backups: List[Dict[str, Any]] = []
        for folder in sorted(self.backup_dir.iterdir(), reverse=True):
            if folder.is_dir():
                manifest_file = folder / "manifest.json"
                manifest_data: Dict[str, Any] = {}
                if manifest_file.exists():
                    try:
                        with open(manifest_file, "r", encoding="utf-8") as f:
                            manifest_data = json.load(f)
                    except Exception:
                        pass
                backups.append({
                    "folder_name": folder.name,
                    "path": str(folder),
                    "created_at": manifest_data.get("created_at", folder.stat().st_ctime),
                    "reason": manifest_data.get("reason", "unknown"),
                    "files_count": manifest_data.get("files_count", len(list(folder.glob("*.json")))),
                })
        return backups

    def restore_backup(self, folder_name: str) -> None:
        """Restore all data files from a specified backup folder with integrity pre-check."""
        backup_folder = self.backup_dir / folder_name
        if not backup_folder.exists() or not backup_folder.is_dir():
            raise BackupError(f"Bản sao lưu '{folder_name}' không tồn tại.")

        # Step 1: Validate integrity of all JSON files in the backup folder first
        json_files = [f for f in backup_folder.glob("*.json") if f.name != "manifest.json"]
        if not json_files:
            raise BackupError(f"Bản sao lưu '{folder_name}' không chứa file dữ liệu hợp lệ.")

        for f in json_files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    json.load(fp)
            except Exception as e:
                raise CorruptedDataError(
                    f"Bản sao lưu bị lỗi định dạng file '{f.name}'. Hủy phục hồi để bảo vệ dữ liệu hiện tại."
                ) from e

        # Step 2: Create a safety checkpoint of current data before overwriting
        try:
            self.create_backup(reason="pre_restore_safety")
        except Exception as e:
            raise BackupError(f"Không thể tạo điểm an toàn trước khi khôi phục: {e}") from e

        # Step 3: Copy validated files atomically to data directory
        for f in json_files:
            target = self.data_dir / f.name
            try:
                with open(f, "r", encoding="utf-8") as src:
                    data = json.load(src)
                write_atomic_json(target, data)
            except Exception as e:
                raise BackupError(f"Lỗi khi phục hồi file '{f.name}': {e}") from e

    def _prune_old_backups(self) -> None:
        """Remove excess backup folders beyond maximum retention count."""
        subdirs = sorted([d for d in self.backup_dir.iterdir() if d.is_dir()], key=lambda p: p.stat().st_mtime)
        while len(subdirs) > self.max_backups:
            oldest = subdirs.pop(0)
            shutil.rmtree(oldest, ignore_errors=True)
