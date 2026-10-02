"""Non-blocking floating toast notification."""

from __future__ import annotations
import customtkinter as ctk
from frontend.theme import Theme
from frontend.components.icon_loader import IconLoader


class ToastManager:
    """Manages spawning self-dismissing notification toasts on a parent window."""

    _active_toast: ctk.CTkFrame | None = None

    @classmethod
    def show(cls, parent: ctk.CTk, message: str, level: str = "success", duration_ms: int = 3200) -> None:
        # Dismiss existing toast if still visible
        if cls._active_toast and cls._active_toast.winfo_exists():
            cls._active_toast.destroy()

        colors = {
            "success": (Theme.colors.EMERALD_LIGHT, "#065F46", Theme.colors.EMERALD, "check"),
            "error": (Theme.colors.DANGER_LIGHT, Theme.colors.DANGER_TEXT, Theme.colors.DANGER, "close"),
            "warning": (Theme.colors.WARNING_LIGHT, Theme.colors.WARNING_TEXT, Theme.colors.WARNING, "warning"),
            "info": (Theme.colors.INFO_LIGHT, Theme.colors.INFO_TEXT, Theme.colors.INFO, "info"),
        }

        bg, text_col, border_col, icon_name = colors.get(level, colors["info"])

        toast = ctk.CTkFrame(
            parent,
            fg_color=bg,
            border_color=border_col,
            border_width=1,
            corner_radius=Theme.radius.CARD,
            height=44,
        )
        cls._active_toast = toast

        icon = IconLoader.get_icon(icon_name, size=18, color=text_col)
        lbl_icon = ctk.CTkLabel(toast, text="", image=icon)
        lbl_icon.pack(side="left", padx=(14, 8), pady=10)

        lbl_msg = ctk.CTkLabel(
            toast,
            text=message,
            font=Theme.fonts.BODY_BOLD,
            text_color=text_col,
        )
        lbl_msg.pack(side="left", padx=(0, 16), pady=10)

        # Position toast floating at top right
        toast.place(relx=0.98, rely=0.03, anchor="ne")
        toast.lift()

        # Schedule automatic dismissal
        def _dismiss():
            if toast.winfo_exists():
                toast.destroy()
                if cls._active_toast is toast:
                    cls._active_toast = None

        parent.after(duration_ms, _dismiss)
