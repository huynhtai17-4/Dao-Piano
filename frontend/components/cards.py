"""Layered floating glass-card components."""

from __future__ import annotations
from typing import Optional
import customtkinter as ctk
from frontend.theme import Theme


class GlassCard(ctk.CTkFrame):
    """Floating white surface card with rounded corners and subtle border."""

    def __init__(self, master, fg_color: Optional[str] = None, border_color: Optional[str] = None, corner_radius: Optional[int] = None, **kwargs):
        super().__init__(
            master=master,
            fg_color=fg_color or Theme.colors.BG_CARD,
            border_color=border_color or Theme.colors.BORDER_SUBTLE,
            border_width=1,
            corner_radius=corner_radius or Theme.radius.CARD,
            **kwargs,
        )


class StatCard(GlassCard):
    """KPI statistic card displaying metric value, title, and icon."""

    def __init__(self, master, title: str, value: str, icon: Optional[ctk.CTkImage] = None, subtitle: Optional[str] = None, accent_color: Optional[str] = None, **kwargs):
        super().__init__(master=master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        # Icon pill
        icon_box = ctk.CTkFrame(
            self,
            width=48,
            height=48,
            corner_radius=12,
            fg_color=accent_color or Theme.colors.EMERALD_LIGHT,
        )
        icon_box.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=16)
        icon_box.grid_propagate(False)

        if icon:
            lbl_icon = ctk.CTkLabel(icon_box, text="", image=icon)
            lbl_icon.place(relx=0.5, rely=0.5, anchor="center")

        # Metric Value
        self.lbl_val = ctk.CTkLabel(
            self,
            text=value,
            font=Theme.fonts.TITLE,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_val.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=(14, 0))

        # Metric Title
        self.lbl_title = ctk.CTkLabel(
            self,
            text=title,
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.TEXT_SECONDARY,
            anchor="w",
        )
        self.lbl_title.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=(0, 14))

    def update_value(self, val: str) -> None:
        """Update displayed metric value."""
        self.lbl_val.configure(text=val)
