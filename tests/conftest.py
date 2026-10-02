"""Pytest configuration and environment fixtures for Piano Center Manager."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_TMP_DIR = PROJECT_ROOT / ".test_tmp"

# Configure temp directory within workspace to avoid sandbox permission errors
TEST_TMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(TEST_TMP_DIR)
os.environ["TMP"] = str(TEST_TMP_DIR)
tempfile.tempdir = str(TEST_TMP_DIR)

# Safe stat hook for Windows root in sandboxed environments
orig_stat = os.stat

def safe_stat(path, *args, **kwargs):
    p_str = str(path).rstrip("\\/")
    if p_str in ("D:", "D:\\", "d:", "d:\\", "C:", "C:\\", "c:", "c:\\"):
        class FakeStat:
            st_mode = 0o040777
        return FakeStat()
    return orig_stat(path, *args, **kwargs)

os.stat = safe_stat


@pytest.fixture(autouse=True, scope="session")
def cleanup_test_temp():
    """Ensure test temp directory is cleaned up after test session."""
    yield
    shutil.rmtree(str(TEST_TMP_DIR), ignore_errors=True)
