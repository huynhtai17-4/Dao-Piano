"""Top header bar component."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
import customtkinter as ctk
from frontend.theme import Theme
from backend.core.dates import format_date_display


class Topbar(ctk.CTkFrame):
    """Header bar displaying current screen title, today's date, and studio identity."""

    def __init__(self, master, center_name: str = "Melody Piano Studio", **kwargs):
        super().__init__(master=master, fg_color="transparent", height=54, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # Left Title Box
        self.title_box = ctk.CTkFrame(self, fg_color="transparent")
        self.title_box.grid(row=0, column=0, sticky="w", padx=4)

        self.lbl_screen_title = ctk.CTkLabel(
            self.title_box,
            text="Lịch trình dạy",
            font=Theme.fonts.TITLE,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_screen_title.pack(anchor="w")

        # Right Meta Box
        right_box = ctk.CTkFrame(self, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="e", padx=4)

        # Today date badge
        today_text = f"Hôm nay: {format_date_display(datetime.now().date())}"
        self.lbl_date = ctk.CTkLabel(
            right_box,
            text=today_text,
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_SECONDARY,
        )
        self.lbl_date.pack(side="left", padx=(0, 16))

        # Center name pill
        center_pill = ctk.CTkFrame(
            right_box,
            fg_color=Theme.colors.BG_CARD,
            border_color=Theme.colors.BORDER_SUBTLE,
            border_width=1,
            corner_radius=Theme.radius.BADGE,
            height=32,
        )
        center_pill.pack(side="left")

        self.lbl_center = ctk.CTkLabel(
            center_pill,
            text=center_name,
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        self.lbl_center.pack(padx=12, pady=4)

    def set_title(self, title: str) -> None:
        self.lbl_screen_title.configure(text=title)

    def set_center_name(self, name: str) -> None:
        self.lbl_center.configure(text=name)
