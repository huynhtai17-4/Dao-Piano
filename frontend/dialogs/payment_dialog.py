"""Modal dialog for recording tuition payments and adding lesson credits."""

from __future__ import annotations
from typing import Optional, Callable
import customtkinter as ctk
from frontend.theme import Theme
from backend.core.dates import today_str
from backend.core.time_utils import format_currency_vnd
from backend.application.services.payment_service import PaymentService
from backend.application.services.student_service import StudentService
from backend.application.dto.payment_dto import PaymentCreateDTO
from frontend.components.dialogs import BaseModalDialog
from frontend.components.buttons import PrimaryButton, OutlineButton


class PaymentDialog(BaseModalDialog):
    """Modal form for collecting and logging tuition fees."""

    def __init__(
        self,
        parent,
        payment_service: PaymentService,
        student_service: StudentService,
        preselected_student_id: Optional[str] = None,
        on_saved: Optional[Callable] = None,
    ):
        self.payment_service = payment_service
        self.student_service = student_service
        self.preselected_student_id = preselected_student_id
        self.on_saved = on_saved

        super().__init__(
            parent=parent,
            title="Thu học phí",
            subtitle="Ghi nhận học phí và cộng thêm số buổi học cho học viên",
            width=500,
            height=580,
        )

        self._load_students()
        self._build_form()

    def _load_students(self) -> None:
        self.students = self.student_service.get_students(active_only=True)
        self.student_map = {f"{s.name} ({s.phone})": s.id for s in self.students}
        self.student_options = ["-- Chọn học sinh --"] + list(self.student_map.keys())

    def _build_form(self) -> None:
        self.body.grid_columnconfigure(1, weight=1)

        row = 0
        # 1. Student selection
        ctk.CTkLabel(self.body, text="Học sinh *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=8)
        self.opt_student = ctk.CTkOptionMenu(
            self.body,
            values=self.student_options,
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.EMERALD,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        self.opt_student.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)

        if self.preselected_student_id:
            for opt_text, sid in self.student_map.items():
                if sid == self.preselected_student_id:
                    self.opt_student.set(opt_text)
                    break
        else:
            self.opt_student.set(self.student_options[0])

        row += 1
        # 2. Payment Amount
        ctk.CTkLabel(self.body, text="Số tiền (VNĐ) *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=8)
        self.entry_amount = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_amount.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)
        self.entry_amount.insert(0, "1600000")

        row += 1
        # Quick amount buttons
        quick_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        quick_frame.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(0, 8))
        for amt in [800000, 1600000, 2400000, 3200000]:
            btn_amt = ctk.CTkButton(
                quick_frame,
                text=format_currency_vnd(amt),
                font=Theme.fonts.CAPTION_BOLD,
                height=26,
                width=76,
                fg_color=Theme.colors.BG_MUTED,
                hover_color=Theme.colors.EMERALD_LIGHT,
                text_color=Theme.colors.TEXT_PRIMARY,
                command=lambda a=amt: self._set_amount(a),
            )
            btn_amt.pack(side="left", padx=(0, 6))

        row += 1
        # 3. Lessons Added
        ctk.CTkLabel(self.body, text="Số buổi cộng thêm *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=8)
        self.entry_lessons = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_lessons.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)
        self.entry_lessons.insert(0, "8")

        row += 1
        # 4. Payment Date
        ctk.CTkLabel(self.body, text="Ngày nộp tiền *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=8)
        self.entry_date = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_date.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)
        self.entry_date.insert(0, today_str())

        row += 1
        # 5. Note
        ctk.CTkLabel(self.body, text="Ghi chú khóa học", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=8)
        self.entry_note = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_note.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)
        self.entry_note.insert(0, "Học phí khóa Piano cơ bản")

        # Inline error
        self.lbl_error = ctk.CTkLabel(self.footer, text="", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.DANGER, wraplength=260, justify="left")
        self.lbl_error.pack(side="left", padx=4)

        # Buttons
        btn_cancel = OutlineButton(self.footer, text="Hủy", command=self.destroy, width=90)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = PrimaryButton(self.footer, text="Xác nhận thu tiền", command=self._save, width=150)
        btn_save.pack(side="right")

    def _set_amount(self, amt: int) -> None:
        self.entry_amount.delete(0, "end")
        self.entry_amount.insert(0, str(amt))

    def _save(self) -> None:
        self.lbl_error.configure(text="")
        sel_student = self.opt_student.get()
        student_id = self.student_map.get(sel_student)

        if not student_id:
            self.lbl_error.configure(text="Vui lòng chọn học sinh nộp tiền.")
            return

        date_str = self.entry_date.get().strip()
        note = self.entry_note.get().strip()

        try:
            amt = int(self.entry_amount.get().strip())
        except ValueError:
            self.lbl_error.configure(text="Số tiền phải là số nguyên.")
            return

        try:
            lessons = int(self.entry_lessons.get().strip())
        except ValueError:
            self.lbl_error.configure(text="Số buổi học phải là số nguyên.")
            return

        try:
            dto = PaymentCreateDTO(
                student_id=student_id,
                amount=amt,
                payment_date=date_str,
                lessons_added=lessons,
                note=note,
            )
            self.payment_service.record_payment(dto)
            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.lbl_error.configure(text=str(e))
