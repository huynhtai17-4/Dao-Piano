"""Empty state placeholder component."""

from __future__ import annotations
from typing import Optional, Callable
import customtkinter as ctk
from frontend.theme import Theme
from frontend.components.icon_loader import IconLoader
from frontend.components.buttons import PrimaryButton


class EmptyState(ctk.CTkFrame):
    """Illustration and message displayed when a screen or list has no records."""

    def __init__(
        self,
        master,
        title: str = "Chưa có dữ liệu",
        description: str = "Bắt đầu bằng việc thêm mới một mục vào hệ thống.",
        action_label: Optional[str] = None,
        action_command: Optional[Callable] = None,
        icon_name: str = "search",
        **kwargs,
    ):
        super().__init__(master=master, fg_color="transparent", **kwargs)

        icon = IconLoader.get_icon(icon_name, size=48, color=Theme.colors.TEXT_MUTED)
        lbl_icon = ctk.CTkLabel(self, text="", image=icon)
        lbl_icon.pack(pady=(30, 12))

        lbl_title = ctk.CTkLabel(
            self,
            text=title,
            font=Theme.fonts.H1,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        lbl_title.pack(pady=(0, 6))

        lbl_desc = ctk.CTkLabel(
            self,
            text=description,
            font=Theme.fonts.BODY,
            text_color=Theme.colors.TEXT_SECONDARY,
        )
        lbl_desc.pack(pady=(0, 20))

        if action_label and action_command:
            btn = PrimaryButton(self, text=action_label, command=action_command)
            btn.pack(pady=(0, 20))
