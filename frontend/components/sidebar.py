"""Floating left sidebar navigation component."""

from __future__ import annotations
from typing import Callable, Dict
import customtkinter as ctk
from frontend.theme import Theme
from frontend.components.icon_loader import IconLoader


class Sidebar(ctk.CTkFrame):
    """Floating sidebar hosting exactly 5 primary navigation destinations."""

    NAV_ITEMS = [
        ("calendar", "Lịch trình dạy", "calendar"),
        ("students", "Học sinh & Học phí", "students"),
        ("classes", "Danh sách lớp học", "classes"),
        ("settings", "Cài đặt", "settings"),
    ]

    def __init__(self, master, on_navigate: Callable[[str], None], active_route: str = "calendar", **kwargs):
        super().__init__(
            master=master,
            fg_color=Theme.colors.BG_SIDEBAR,
            border_color=Theme.colors.BORDER_SUBTLE,
            border_width=1,
            corner_radius=Theme.radius.CARD,
            width=240,
            **kwargs,
        )
        self.on_navigate = on_navigate
        self.active_route = active_route
        self._buttons: Dict[str, ctk.CTkButton] = {}

        self.pack_propagate(False)

        # Brand / Logo Header
        self._build_header()

        # Nav items container
        self.nav_container = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_container.pack(fill="x", padx=12, pady=(10, 0))

        self._build_nav_buttons()

        # Footer version
        lbl_version = ctk.CTkLabel(
            self,
            text="v1.0 • Offline Ready",
            font=Theme.fonts.CAPTION,
            text_color=Theme.colors.TEXT_MUTED,
        )
        lbl_version.pack(side="bottom", pady=16)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(20, 16))

        piano_icon = IconLoader.get_icon("piano", size=26, color=Theme.colors.EMERALD)
        lbl_icon = ctk.CTkLabel(header, text="", image=piano_icon)
        lbl_icon.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        lbl_title = ctk.CTkLabel(
            title_box,
            text="DaoPiano",
            font=Theme.fonts.H1,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box,
            text="Studio Manager",
            font=Theme.fonts.CAPTION,
            text_color=Theme.colors.TEXT_MUTED,
            anchor="w",
        )
        lbl_sub.pack(anchor="w")

    def _build_nav_buttons(self) -> None:
        for route_id, label, icon_name in self.NAV_ITEMS:
            is_active = (route_id == self.active_route)
            btn = self._create_nav_button(route_id, label, icon_name, is_active)
            btn.pack(fill="x", pady=4)
            self._buttons[route_id] = btn

    def _create_nav_button(self, route_id: str, label: str, icon_name: str, is_active: bool) -> ctk.CTkButton:
        icon_color = Theme.colors.EMERALD if is_active else Theme.colors.TEXT_SECONDARY
        text_color = Theme.colors.EMERALD if is_active else Theme.colors.TEXT_PRIMARY
        fg_color = Theme.colors.EMERALD_LIGHT if is_active else "transparent"
        icon = IconLoader.get_icon(icon_name, size=20, color=icon_color)

        btn = ctk.CTkButton(
            self.nav_container,
            text=f"  {label}",
            image=icon,
            compound="left",
            anchor="w",
            height=44,
            corner_radius=10,
            fg_color=fg_color,
            hover_color=Theme.colors.BG_CARD_HOVER if not is_active else Theme.colors.EMERALD_LIGHT,
            text_color=text_color,
            font=Theme.fonts.BODY_BOLD if is_active else Theme.fonts.BODY,
            command=lambda r=route_id: self._handle_click(r),
        )
        return btn

    def _handle_click(self, route_id: str) -> None:
        self.set_active(route_id)
        self.on_navigate(route_id)

    def set_active(self, route_id: str) -> None:
        self.active_route = route_id
        for rid, btn in self._buttons.items():
            is_active = (rid == route_id)
            btn.configure(
                fg_color=Theme.colors.EMERALD_LIGHT if is_active else "transparent",
                text_color=Theme.colors.EMERALD if is_active else Theme.colors.TEXT_PRIMARY,
                font=Theme.fonts.BODY_BOLD if is_active else Theme.fonts.BODY,
            )
