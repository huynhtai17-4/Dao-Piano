"""Screen navigation router managing display transitions between main application views."""

from __future__ import annotations
from typing import Dict, Optional
import customtkinter as ctk


class ViewRouter:
    """Manages view caching, lifecycle, and display transitions."""

    def __init__(self, container: ctk.CTkFrame) -> None:
        self.container = container
        self._screens: Dict[str, ctk.CTkFrame] = {}
        self._current_screen: Optional[ctk.CTkFrame] = None
        self._current_route_id: Optional[str] = None

    def register(self, route_id: str, screen_instance: ctk.CTkFrame) -> None:
        """Register a screen widget associated with route_id."""
        self._screens[route_id] = screen_instance

    def navigate(self, route_id: str) -> None:
        """Switch active visible screen to the registered route_id."""
        if route_id not in self._screens:
            raise KeyError(f"Route '{route_id}' has not been registered in ViewRouter.")

        # Hide current screen
        if self._current_screen and self._current_screen.winfo_exists():
            self._current_screen.pack_forget()

        # Show target screen
        new_screen = self._screens[route_id]
        new_screen.pack(fill="both", expand=True)

        # Trigger refresh hook if available
        if hasattr(new_screen, "refresh") and callable(getattr(new_screen, "refresh")):
            new_screen.refresh()

        self._current_screen = new_screen
        self._current_route_id = route_id

    @property
    def current_route(self) -> Optional[str]:
        return self._current_route_id
