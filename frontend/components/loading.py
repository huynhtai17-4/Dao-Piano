"""Loading indicator component."""

from __future__ import annotations
import customtkinter as ctk
from frontend.theme import Theme


class LoadingIndicator(ctk.CTkFrame):
    """Subtle indeterminate progress bar and loading text."""

    def __init__(self, master, text: str = "Đang tải dữ liệu...", **kwargs):
        super().__init__(master=master, fg_color="transparent", **kwargs)

        self.bar = ctk.CTkProgressBar(
            self,
            width=200,
            height=6,
            mode="indeterminate",
            progress_color=Theme.colors.EMERALD,
        )
        self.bar.pack(pady=(20, 8))
        self.bar.start()

        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=Theme.fonts.CAPTION,
            text_color=Theme.colors.TEXT_MUTED,
        )
        self.label.pack()

    def stop(self) -> None:
        self.bar.stop()
