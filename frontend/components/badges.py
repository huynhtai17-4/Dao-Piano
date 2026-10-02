"""Color-coded status badges and pill indicators."""

from __future__ import annotations
import customtkinter as ctk
from frontend.theme import Theme
from backend.core.enums import ClassType, AttendanceStatus


class Badge(ctk.CTkFrame):
    """Pill badge displaying status text with high-contrast background."""

    def __init__(self, master, text: str, bg_color: str, text_color: str, border_color: str | None = None, **kwargs):
        super().__init__(
            master=master,
            fg_color=bg_color,
            border_color=border_color or bg_color,
            border_width=1 if border_color else 0,
            corner_radius=Theme.radius.BADGE,
            height=26,
            **kwargs,
        )
        lbl = ctk.CTkLabel(
            self,
            text=text,
            font=Theme.fonts.CAPTION_BOLD,
            text_color=text_color,
        )
        lbl.pack(padx=10, pady=3)

    @classmethod
    def for_class_type(cls, master, class_type: ClassType) -> Badge:
        match class_type:
            case ClassType.ONE_ON_ONE:
                return cls(master, "1 Kèm 1", Theme.colors.EMERALD_LIGHT, "#047857", Theme.colors.EMERALD_BORDER)
            case ClassType.OFFLINE:
                return cls(master, "Offline", Theme.colors.OCEAN_LIGHT, "#0369A1", "#7DD3FC")
            case ClassType.ONLINE:
                return cls(master, "Online", Theme.colors.PURPLE_LIGHT, "#6D28D9", "#C4B5FD")

    @classmethod
    def for_lessons_count(cls, master, count: int) -> Badge:
        if count == 0:
            return cls(master, "Hết buổi (0)", Theme.colors.DANGER_LIGHT, Theme.colors.DANGER_TEXT, "#FCA5A5")
        if count <= 2:
            return cls(master, f"Sắp hết ({count})", Theme.colors.WARNING_LIGHT, Theme.colors.WARNING_TEXT, "#FCD34D")
        return cls(master, f"Còn {count} buổi", Theme.colors.EMERALD_LIGHT, "#047857", Theme.colors.EMERALD_BORDER)

    @classmethod
    def for_attendance(cls, master, status: AttendanceStatus) -> Badge:
        match status:
            case AttendanceStatus.PRESENT:
                return cls(master, "Có mặt", Theme.colors.EMERALD_LIGHT, "#047857", Theme.colors.EMERALD_BORDER)
            case AttendanceStatus.ABSENT:
                return cls(master, "Vắng mặt", Theme.colors.WARNING_LIGHT, Theme.colors.WARNING_TEXT, "#FCD34D")
            case AttendanceStatus.RESCHEDULED:
                return cls(master, "Đổi lịch", Theme.colors.PURPLE_LIGHT, "#6D28D9", "#C4B5FD")
