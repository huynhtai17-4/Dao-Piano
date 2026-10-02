"""Quick modal dialog to adjust remaining lessons for a student without opening the full form."""

from __future__ import annotations
from typing import Optional, Callable
import customtkinter as ctk

from frontend.theme import Theme
from backend.application.services.student_service import StudentService
from backend.application.dto.student_dto import StudentResponseDTO
from frontend.components.dialogs import BaseModalDialog
from frontend.components.buttons import PrimaryButton, OutlineButton


class QuickLessonsDialog(BaseModalDialog):
    """Compact dialog for fast adjustment of remaining lessons."""

    def __init__(
        self,
        parent,
        student_service: StudentService,
        student: StudentResponseDTO,
        on_saved: Optional[Callable] = None,
    ):
        self.student_service = student_service
        self.student = student
        self.on_saved = on_saved

        super().__init__(
            parent=parent,
            title=f"Số buổi học: {student.name}",
            subtitle=f"Hiện tại: {student.remaining_lessons} buổi • SĐT: {student.phone}",
            width=400,
            height=320,
        )
        self._build_content()

    def _build_content(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)

        # Main Stepper Card
        card = ctk.CTkFrame(
            self.body,
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            border_width=1,
            corner_radius=8,
        )
        card.pack(fill="x", padx=6, pady=8)

        # Stepper Row
        step_row = ctk.CTkFrame(card, fg_color="transparent")
        step_row.pack(fill="x", padx=12, pady=(12, 6))

        btn_minus = ctk.CTkButton(
            step_row,
            text="➖",
            width=40,
            height=40,
            font=Theme.fonts.H2,
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#334155",
            corner_radius=6,
            command=lambda: self._adjust(-1),
        )
        btn_minus.pack(side="left", padx=(0, 8))

        self.entry_val = ctk.CTkEntry(
            step_row,
            width=90,
            height=40,
            font=Theme.fonts.H1,
            justify="center",
            corner_radius=Theme.radius.INPUT,
        )
        self.entry_val.pack(side="left", padx=(0, 8))
        self.entry_val.insert(0, str(self.student.remaining_lessons))
        self.entry_val.bind("<KeyRelease>", lambda e: self._update_hint())

        btn_plus = ctk.CTkButton(
            step_row,
            text="➕",
            width=40,
            height=40,
            font=Theme.fonts.H2,
            fg_color=Theme.colors.EMERALD_LIGHT,
            hover_color="#A7F3D0",
            text_color="#047857",
            corner_radius=6,
            command=lambda: self._adjust(1),
        )
        btn_plus.pack(side="left", padx=(0, 10))

        self.lbl_hint = ctk.CTkLabel(
            step_row,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            anchor="w",
        )
        self.lbl_hint.pack(side="left", fill="x", expand=True)

        # Preset Buttons Row
        preset_row = ctk.CTkFrame(card, fg_color="transparent")
        preset_row.pack(fill="x", padx=12, pady=(0, 12))

        for txt, val, is_delta in [
            ("+1", 1, True),
            ("-1", -1, True),
            ("+8 (1 khóa)", 8, True),
            ("+16", 16, True),
            ("Về 0", 0, False),
        ]:
            b = ctk.CTkButton(
                preset_row,
                text=txt,
                font=Theme.fonts.CAPTION_BOLD,
                height=28,
                fg_color="#FFFFFF",
                hover_color="#F1F5F9",
                text_color=Theme.colors.TEXT_SECONDARY,
                border_color="#CBD5E1",
                border_width=1,
                corner_radius=4,
                command=lambda v=val, d=is_delta: self._set_or_delta(v, d),
            )
            b.pack(side="left", padx=2)

        # Inline Error
        self.lbl_err = ctk.CTkLabel(self.footer, text="", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.DANGER)
        self.lbl_err.pack(side="left", padx=4)

        # Footer Buttons
        btn_cancel = OutlineButton(self.footer, text="Hủy", command=self.destroy, width=80)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = PrimaryButton(self.footer, text="Cập nhật", command=self._save, width=100)
        btn_save.pack(side="right")

        self._update_hint()

    def _adjust(self, delta: int) -> None:
        try:
            curr = int(self.entry_val.get().strip())
        except Exception:
            curr = 0
        new_val = max(0, curr + delta)
        self.entry_val.delete(0, "end")
        self.entry_val.insert(0, str(new_val))
        self._update_hint()

    def _set_or_delta(self, val: int, is_delta: bool) -> None:
        if is_delta:
            self._adjust(val)
        else:
            self.entry_val.delete(0, "end")
            self.entry_val.insert(0, str(max(0, val)))
            self._update_hint()

    def _update_hint(self) -> None:
        try:
            val = int(self.entry_val.get().strip())
        except Exception:
            val = 0

        if val == 0:
            self.lbl_hint.configure(text="⚠️ Đã hết buổi", text_color=Theme.colors.DANGER)
        elif val <= 2:
            self.lbl_hint.configure(text=f"⚡ Sắp hết ({val} buổi)", text_color=Theme.colors.WARNING)
        else:
            self.lbl_hint.configure(text=f"✓ Còn {val} buổi", text_color=Theme.colors.EMERALD)

    def _save(self) -> None:
        self.lbl_err.configure(text="")
        try:
            val = int(self.entry_val.get().strip())
            if val < 0:
                raise ValueError("Số buổi không được âm.")
        except Exception:
            self.lbl_err.configure(text="Số buổi phải là số nguyên >= 0.")
            return

        try:
            self.student_service.adjust_remaining_lessons(self.student.id, val, is_delta=False)
            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.lbl_err.configure(text=str(e))
