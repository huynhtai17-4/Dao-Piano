"""Modal form for creating and updating lesson schedules with real-time conflict checking."""

from __future__ import annotations
from typing import Optional, Callable
import customtkinter as ctk
from frontend.theme import Theme
from backend.core.enums import ClassType, ScheduleStatus
from backend.application.services.schedule_service import ScheduleService
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.dto.schedule_dto import ScheduleCreateDTO, ScheduleUpdateDTO, ScheduleResponseDTO
from frontend.components.dialogs import BaseModalDialog
from frontend.components.buttons import PrimaryButton, OutlineButton


class ScheduleDialog(BaseModalDialog):
    """Modal for booking calendar lessons."""

    def __init__(
        self,
        parent,
        schedule_service: ScheduleService,
        student_service: StudentService,
        class_service: ClassService,
        schedule: Optional[ScheduleResponseDTO] = None,
        initial_date: Optional[str] = None,
        initial_start_time: str = "08:00",
        initial_end_time: str = "09:00",
        on_saved: Optional[Callable] = None,
    ):
        self.schedule_service = schedule_service
        self.student_service = student_service
        self.class_service = class_service
        self.schedule = schedule
        self.initial_date = initial_date or (schedule.date if schedule else "2026-10-01")
        self.on_saved = on_saved
        is_edit = schedule is not None

        super().__init__(
            parent=parent,
            title="Chỉnh sửa ca học" if is_edit else "Thêm ca học mới",
            subtitle="Chọn thời gian và học sinh hoặc lớp học",
            width=500,
            height=620,
        )

        self._load_options()
        self._build_form(initial_start_time, initial_end_time)

    def _load_options(self) -> None:
        self.students = self.student_service.get_students(active_only=True)
        self.student_map = {f"{s.name} ({s.phone})": s.id for s in self.students}
        self.student_options = ["-- Chọn học sinh 1-kèm-1 --"] + list(self.student_map.keys())

        self.classes = self.class_service.get_classes()
        self.class_map = {f"{c.name} ({c.class_type_display})": c.id for c in self.classes}
        self.class_options = ["-- Chọn lớp học --"] + list(self.class_map.keys())

    def _build_form(self, default_start: str, default_end: str) -> None:
        self.body.grid_columnconfigure(1, weight=1)

        row = 0
        # 1. Lesson Title
        ctk.CTkLabel(self.body, text="Tiêu đề buổi học *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=6)
        self.entry_title = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_title.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        self.entry_title.insert(0, self.schedule.lesson_title if self.schedule else "Buổi học đàn Piano")

        row += 1
        # 2. Date
        ctk.CTkLabel(self.body, text="Ngày học (YYYY-MM-DD) *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=6)
        self.entry_date = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_date.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        self.entry_date.insert(0, self.schedule.date if self.schedule else self.initial_date)

        row += 1
        # 3. Start & End Time
        ctk.CTkLabel(self.body, text="Thời gian (HH:MM) *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=6)
        time_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        time_frame.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        time_frame.grid_columnconfigure(0, weight=1)
        time_frame.grid_columnconfigure(2, weight=1)

        self.entry_start = ctk.CTkEntry(time_frame, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_start.grid(row=0, column=0, sticky="ew")
        self.entry_start.insert(0, self.schedule.start_time if self.schedule else default_start)

        ctk.CTkLabel(time_frame, text="  đến  ", font=Theme.fonts.BODY).grid(row=0, column=1)

        self.entry_end = ctk.CTkEntry(time_frame, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_end.grid(row=0, column=2, sticky="ew")
        self.entry_end.insert(0, self.schedule.end_time if self.schedule else default_end)

        row += 1
        # 4. Target Class
        ctk.CTkLabel(self.body, text="Lớp học", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=6)
        self.opt_class = ctk.CTkOptionMenu(
            self.body,
            values=self.class_options,
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.OCEAN,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        self.opt_class.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)

        # Preselect existing class
        if self.schedule and self.schedule.class_id:
            for opt_text, cid in self.class_map.items():
                if cid == self.schedule.class_id:
                    self.opt_class.set(opt_text)
                    break
        else:
            self.opt_class.set(self.class_options[0])

        row += 1
        # 5. Target Student (for 1-on-1 or individual lesson)
        ctk.CTkLabel(self.body, text="Học sinh (1-Kèm-1)", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=6)
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
        self.opt_student.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)

        if self.schedule and self.schedule.student_id:
            for opt_text, sid in self.student_map.items():
                if sid == self.schedule.student_id:
                    self.opt_student.set(opt_text)
                    break
        else:
            self.opt_student.set(self.student_options[0])

        row += 1
        # 6. Location / Room
        ctk.CTkLabel(self.body, text="Địa điểm / Phòng", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=6)
        self.entry_location = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_location.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        self.entry_location.insert(0, (self.schedule.location or "Phòng học 1") if self.schedule else "Phòng học 1")

        row += 1
        # 7. Online Link
        ctk.CTkLabel(self.body, text="Link học Online", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=6)
        self.entry_link = ctk.CTkEntry(self.body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_link.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        if self.schedule and self.schedule.online_url:
            self.entry_link.insert(0, self.schedule.online_url)

        # Inline error label
        self.lbl_error = ctk.CTkLabel(self.footer, text="", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.DANGER, wraplength=260, justify="left")
        self.lbl_error.pack(side="left", padx=4)

        # Buttons
        btn_cancel = OutlineButton(self.footer, text="Hủy", command=self.destroy, width=90)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = PrimaryButton(self.footer, text="Lưu lịch học", command=self._save, width=120)
        btn_save.pack(side="right")

    def _save(self) -> None:
        self.lbl_error.configure(text="")
        title = self.entry_title.get().strip()
        date_str = self.entry_date.get().strip()
        start_t = self.entry_start.get().strip()
        end_t = self.entry_end.get().strip()
        location = self.entry_location.get().strip() or None
        online_url = self.entry_link.get().strip() or None

        sel_class = self.opt_class.get()
        class_id = self.class_map.get(sel_class) if sel_class != self.class_options[0] else None

        sel_student = self.opt_student.get()
        student_id = self.student_map.get(sel_student) if sel_student != self.student_options[0] else None

        if not title:
            self.lbl_error.configure(text="Tiêu đề buổi học không được để trống.")
            return

        try:
            from backend.core.dates import parse_date
            parse_date(date_str)
        except Exception:
            self.lbl_error.configure(text="Định dạng ngày học không hợp lệ (YYYY-MM-DD).")
            return

        from backend.core.time_utils import validate_time_format, time_to_minutes
        if not validate_time_format(start_t) or not validate_time_format(end_t):
            self.lbl_error.configure(text="Giờ học không đúng định dạng HH:MM (ví dụ: 08:30).")
            return

        try:
            if time_to_minutes(end_t) <= time_to_minutes(start_t):
                self.lbl_error.configure(text="Giờ kết thúc phải sau giờ bắt đầu.")
                return
        except Exception:
            self.lbl_error.configure(text="Giờ học không hợp lệ.")
            return

        if not class_id and not student_id:
            self.lbl_error.configure(text="Vui lòng chọn ít nhất một Lớp học hoặc Học sinh.")
            return

        try:
            if self.schedule:
                dto_update = ScheduleUpdateDTO(
                    id=self.schedule.id,
                    class_id=class_id,
                    student_id=student_id,
                    date=date_str,
                    start_time=start_t,
                    end_time=end_t,
                    location=location,
                    online_url=online_url,
                    lesson_title=title,
                    status=self.schedule.status,
                )
                self.schedule_service.update_schedule(dto_update)
            else:
                dto_create = ScheduleCreateDTO(
                    class_id=class_id,
                    student_id=student_id,
                    date=date_str,
                    start_time=start_t,
                    end_time=end_t,
                    location=location,
                    online_url=online_url,
                    lesson_title=title,
                )
                self.schedule_service.create_schedule(dto_create)

            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.lbl_error.configure(text=str(e))
