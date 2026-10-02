"""Base modal dialog and confirmation dialog components."""

from __future__ import annotations
from typing import Optional, Callable
import customtkinter as ctk
from frontend.theme import Theme
from frontend.components.icon_loader import IconLoader
from frontend.components.buttons import PrimaryButton, OutlineButton, DangerButton, IconButton


class BaseModalDialog(ctk.CTkToplevel):
    """Reusable modal dialog container centered relative to parent window."""

    def __init__(
        self,
        parent,
        title: str,
        subtitle: Optional[str] = None,
        width: int = 500,
        height: int = 560,
    ):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.configure(fg_color=Theme.colors.BG_WINDOW)

        # Center on parent
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + max(0, (pw - width) // 2)
            y = py + max(0, (ph - height) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self.transient(parent)
        self.grab_set()

        # Layout Container (Glass Card)
        self.card = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.BG_CARD,
            border_color=Theme.colors.BORDER_SUBTLE,
            border_width=1,
            corner_radius=Theme.radius.MODAL,
        )
        self.card.pack(fill="both", expand=True, padx=16, pady=16)
        self.card.grid_rowconfigure(1, weight=1)
        self.card.grid_columnconfigure(0, weight=1)

        # Top Header Bar
        header = ctk.CTkFrame(self.card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")

        lbl_title = ctk.CTkLabel(
            title_box,
            text=title,
            font=Theme.fonts.TITLE,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(anchor="w")

        if subtitle:
            lbl_sub = ctk.CTkLabel(
                title_box,
                text=subtitle,
                font=Theme.fonts.CAPTION,
                text_color=Theme.colors.TEXT_SECONDARY,
                anchor="w",
            )
            lbl_sub.pack(anchor="w", pady=(2, 0))

        close_icon = IconLoader.get_icon("close", size=16, color=Theme.colors.TEXT_MUTED)
        btn_close = IconButton(header, icon=close_icon, command=self.destroy, size=32)
        btn_close.grid(row=0, column=1, sticky="e")

        # Body Container
        self.body = ctk.CTkFrame(self.card, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=20, pady=8)

        # Footer Actions Container
        self.footer = ctk.CTkFrame(self.card, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 16))
        self.footer.grid_columnconfigure(0, weight=1)


class ConfirmDialog(BaseModalDialog):
    """Simple confirmation dialog for destructive or state-changing actions."""

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        on_confirm: Callable[[], None],
        confirm_text: str = "Xác nhận",
        cancel_text: str = "Hủy bỏ",
        is_danger: bool = True,
    ):
        super().__init__(parent, title=title, width=440, height=220)
        self.on_confirm = on_confirm

        lbl = ctk.CTkLabel(
            self.body,
            text=message,
            font=Theme.fonts.BODY,
            text_color=Theme.colors.TEXT_SECONDARY,
            wraplength=380,
            justify="left",
        )
        lbl.pack(fill="both", expand=True, pady=10)

        # Buttons
        btn_cancel = OutlineButton(self.footer, text=cancel_text, command=self.destroy, width=100)
        btn_cancel.pack(side="right", padx=(8, 0))

        def _do_confirm():
            self.destroy()
            self.on_confirm()

        if is_danger:
            btn_confirm = DangerButton(self.footer, text=confirm_text, command=_do_confirm, width=130)
        else:
            btn_confirm = PrimaryButton(self.footer, text=confirm_text, command=_do_confirm, width=130)
        btn_confirm.pack(side="right")
