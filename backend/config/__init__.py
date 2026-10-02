"""Configuration package for Piano Center Manager."""

from backend.config.constants import APP_NAME, VERSION
from frontend.theme import Theme
from backend.config.app_config import AppConfig

__all__ = ["APP_NAME", "VERSION", "Theme", "AppConfig"]
