"""Modal dialog for marking student attendance and managing lesson balance adjustments."""

from __future__ import annotations
from typing import Optional, Callable, Dict
import customtkinter as ctk
from datetime import date, timedelta
from frontend.theme import Theme
from backend.core.enums import AttendanceStatus, ScheduleStatus
from backend.core.event_bus import event_bus
from backend.core.dates import parse_date, format_date_display, today_date, WEEKDAY_VN
from backend.core.time_utils import is_time_overlap, time_to_minutes, validate_time_format
from backend.application.services.attendance_service import AttendanceService
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.services.schedule_service import ScheduleService
from backend.application.dto.attendance_dto import AttendanceCreateDTO
from backend.application.dto.schedule_dto import ScheduleResponseDTO, ScheduleCreateDTO
from frontend.components.dialogs import BaseModalDialog
from frontend.components.buttons import PrimaryButton, OutlineButton
from frontend.components.calendar_picker import CalendarPickerFrame
from frontend.components.toast import ToastManager


class AttendanceDialog(BaseModalDialog):
    """Modal for registering attendance for 1-on-1 and online classes with rescheduling support."""

    def __init__(
        self,
        parent,
        attendance_service: AttendanceService,
        student_service: StudentService,
        schedule: ScheduleResponseDTO,
        schedule_service: Optional[ScheduleService] = None,
        student_id: Optional[str] = None,
        on_saved: Optional[Callable] = None,
    ):
        self.attendance_service = attendance_service
        self.student_service = student_service
        self.schedule_service = schedule_service
        self.schedule = schedule
        self.target_student_id = student_id or schedule.student_id
        self.on_saved = on_saved

        super().__init__(
            parent=parent,
            title="Điểm danh buổi học",
            subtitle=f"{schedule.lesson_title} • Ngày {schedule.date} ({schedule.start_time} - {schedule.end_time})",
            width=540,
            height=680,
        )

        self._load_data()
        self._build_form()

    def _load_data(self) -> None:
        self.student = None
        if self.target_student_id:
            try:
                self.student = self.student_service.get_student_by_id(self.target_student_id)
            except Exception:
                pass

        # Existing record
        self.existing_records = self.attendance_service.get_attendance_for_schedule(self.schedule.id)
        self.current_record = next((r for r in self.existing_records if r.student_id == self.target_student_id), None)

    def _build_form(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)

        # Scrollable container inside modal body
        self.scroll_body = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self.scroll_body.pack(fill="both", expand=True, padx=2, pady=2)
        self.scroll_body.grid_columnconfigure(0, weight=1)

        # 1. Student Name & Balance info card
        card_info = ctk.CTkFrame(self.scroll_body, fg_color=Theme.colors.EMERALD_LIGHT, corner_radius=10)
        card_info.pack(fill="x", pady=(0, 10))

        student_name = self.student.name if self.student else (self.schedule.student_name or "Học sinh")
        student_phone = f" • SĐT: {self.student.phone}" if self.student and self.student.phone else ""
        lessons_left = self.student.remaining_lessons if self.student else 0

        lbl_sname = ctk.CTkLabel(
            card_info,
            text=f"Học sinh: {student_name}{student_phone}",
            font=Theme.fonts.BODY_BOLD,
            text_color="#065F46",
        )
        lbl_sname.pack(anchor="w", padx=14, pady=(10, 2))

        lbl_sbalance = ctk.CTkLabel(
            card_info,
            text=f"Số buổi học hiện có: {lessons_left} buổi",
            font=Theme.fonts.CAPTION_BOLD,
            text_color="#047857",
        )
        lbl_sbalance.pack(anchor="w", padx=14, pady=(0, 10))

        # 2. Attendance Status Selection
        ctk.CTkLabel(self.scroll_body, text="Trạng thái buổi học: *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).pack(anchor="w", pady=(4, 4))
        
        self.status_var = ctk.StringVar(value=self.current_record.status.value if self.current_record else AttendanceStatus.PRESENT.value)

        opts_frame = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        opts_frame.pack(fill="x", pady=(0, 8))

        rb1 = ctk.CTkRadioButton(
            opts_frame,
            text="Có mặt (Trừ 1 buổi)",
            variable=self.status_var,
            value=AttendanceStatus.PRESENT.value,
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            fg_color=Theme.colors.EMERALD,
            command=self._on_status_changed,
        )
        rb1.pack(anchor="w", pady=4)

        rb2 = ctk.CTkRadioButton(
            opts_frame,
            text="Vắng mặt (Không trừ buổi)",
            variable=self.status_var,
            value=AttendanceStatus.ABSENT.value,
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            fg_color=Theme.colors.WARNING,
            command=self._on_status_changed,
        )
        rb2.pack(anchor="w", pady=4)

        rb3 = ctk.CTkRadioButton(
            opts_frame,
            text="Đổi lịch học (Chuyển sang ngày / giờ khác)",
            variable=self.status_var,
            value=AttendanceStatus.RESCHEDULED.value,
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            fg_color=Theme.colors.PURPLE,
            command=self._on_status_changed,
        )
        rb3.pack(anchor="w", pady=4)

        # 3. Reschedule Container (Only visible when RESCHEDULED is chosen)
        self.resched_container = ctk.CTkFrame(
            self.scroll_body,
            fg_color=Theme.colors.BG_CARD,
            border_color=Theme.colors.PURPLE,
            border_width=1.5,
            corner_radius=10,
        )

        r_title_box = ctk.CTkFrame(self.resched_container, fg_color="transparent")
        r_title_box.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            r_title_box,
            text="🔄 Chọn ngày và khung giờ học mới:",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.PURPLE,
        ).pack(side="left")

        # Calendar picker table
        try:
            init_d = parse_date(self.schedule.date) + timedelta(days=1)
        except Exception:
            init_d = today_date()

        self.cal_picker = CalendarPickerFrame(
            self.resched_container,
            initial_date=init_d,
            on_date_selected=self._on_resched_date_selected,
        )

        # Time inputs row
        t_row = ctk.CTkFrame(self.resched_container, fg_color="transparent")
        t_row.pack(fill="x", padx=12, pady=(4, 4))

        ctk.CTkLabel(t_row, text="Khung giờ mới: *", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.TEXT_PRIMARY).pack(side="left", padx=(0, 8))

        self.entry_new_st = ctk.CTkEntry(t_row, font=Theme.fonts.BODY, width=64, height=30, corner_radius=Theme.radius.INPUT)
        self.entry_new_st.pack(side="left", padx=(0, 4))
        self.entry_new_st.insert(0, self.schedule.start_time)
        self.entry_new_st.bind("<KeyRelease>", lambda e: self._check_resched_conflicts())

        ctk.CTkLabel(t_row, text=" - ", font=Theme.fonts.BODY_BOLD).pack(side="left", padx=2)

        self.entry_new_et = ctk.CTkEntry(t_row, font=Theme.fonts.BODY, width=64, height=30, corner_radius=Theme.radius.INPUT)
        self.entry_new_et.pack(side="left", padx=(0, 8))
        self.entry_new_et.insert(0, self.schedule.end_time)
        self.entry_new_et.bind("<KeyRelease>", lambda e: self._check_resched_conflicts())

        # Busy hours row on selected weekday
        self.busy_row = ctk.CTkFrame(self.resched_container, fg_color="transparent")
        self.busy_row.pack(fill="x", padx=12, pady=(2, 4))

        # Real-time conflict label
        self.lbl_conflict_fb = ctk.CTkLabel(
            self.resched_container,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.EMERALD,
            wraplength=460,
            justify="left",
        )
        self.lbl_conflict_fb.pack(fill="x", padx=12, pady=(2, 10))

        # 4. Note input
        ctk.CTkLabel(self.scroll_body, text="Ghi chú buổi học (tùy chọn):", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).pack(anchor="w", pady=(6, 2))
        self.entry_note = ctk.CTkEntry(self.scroll_body, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_note.pack(fill="x", pady=(0, 8))
        if self.current_record and self.current_record.note:
            self.entry_note.insert(0, self.current_record.note)

        # Inline error
        self.lbl_error = ctk.CTkLabel(self.footer, text="", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.DANGER, wraplength=260, justify="left")
        self.lbl_error.pack(side="left", padx=4)

        # Buttons
        if getattr(self.schedule, "original_schedule_id", None):
            btn_del_resched = ctk.CTkButton(
                self.footer,
                text="🗑️ Hủy đổi lịch (Khôi phục ca cũ)",
                font=Theme.fonts.CAPTION_BOLD,
                fg_color=Theme.colors.DANGER,
                hover_color="#DC2626",
                text_color=Theme.colors.TEXT_WHITE,
                height=34,
                corner_radius=Theme.radius.BUTTON,
                command=self._confirm_delete_rescheduled,
            )
            btn_del_resched.pack(side="left", padx=4)

        btn_cancel = OutlineButton(self.footer, text="Đóng", command=self.destroy, width=90)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = PrimaryButton(self.footer, text="Xác nhận điểm danh", command=self._save, width=160)
        btn_save.pack(side="right")

        self._on_status_changed()

    def _confirm_delete_rescheduled(self) -> None:
        """Allow deleting an accidentally placed makeup/rescheduled session and restore the original."""
        from frontend.components.dialogs import ConfirmDialog
        from frontend.components.toast import ToastManager

        def _on_confirm():
            if self.schedule_service:
                self.schedule_service.delete_schedule(self.schedule.id)
                ToastManager.show(self.parent, "Đã xóa ca đổi lịch và khôi phục ca học cũ.", level="success")
            self.destroy()
            if self.on_saved:
                self.on_saved()

        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Hủy ca đổi lịch",
            message="Bạn có chắc muốn xóa ca đổi lịch này?\nCa học cũ sẽ được tự động khôi phục lại trên lịch.",
            on_confirm=_on_confirm,
        )

    def _on_status_changed(self) -> None:
        if self.status_var.get() == AttendanceStatus.RESCHEDULED.value:
            self.resched_container.pack(fill="x", pady=(4, 10))
            self._on_resched_date_selected(self.cal_picker.selected_date)
        else:
            self.resched_container.pack_forget()

    def _on_resched_date_selected(self, d: date) -> None:
        self._update_resched_busy_hours(d.weekday())
        self._check_resched_conflicts()

    def _update_resched_busy_hours(self, weekday_idx: int) -> None:
        for c in self.busy_row.winfo_children():
            c.destroy()

        day_name = WEEKDAY_VN[weekday_idx]
        all_schedules = self.schedule_service.schedule_repo.get_all() if self.schedule_service else []
        busy_slots = []
        seen = set()

        for s in all_schedules:
            if s.status.value == "CANCELLED" or s.id == self.schedule.id:
                continue
            try:
                if parse_date(s.date).weekday() == weekday_idx:
                    key = (s.start_time, s.end_time)
                    if key not in seen:
                        seen.add(key)
                        busy_slots.append((s.start_time, s.end_time))
            except Exception:
                continue

        busy_slots.sort(key=lambda x: x[0])

        lbl_header = ctk.CTkLabel(
            self.busy_row,
            text=f"Đã có lịch ({day_name}):",
            font=Theme.fonts.CAPTION_BOLD,
            text_color="#B91C1C",
        )
        lbl_header.pack(side="left", padx=(0, 6))

        if not busy_slots:
            ctk.CTkLabel(
                self.busy_row,
                text="✓ Chưa có lịch nào (trống cả ngày)",
                font=Theme.fonts.CAPTION,
                text_color=Theme.colors.EMERALD,
            ).pack(side="left")
        else:
            for st, et in busy_slots[:4]:
                tag = ctk.CTkFrame(self.busy_row, fg_color="#FEE2E2", border_color="#FCA5A5", border_width=1, corner_radius=4)
                tag.pack(side="left", padx=2)
                ctk.CTkLabel(tag, text=f"🔒 {st}-{et}", font=Theme.fonts.CAPTION_BOLD, text_color="#DC2626").pack(padx=5, pady=1)
            if len(busy_slots) > 4:
                ctk.CTkLabel(self.busy_row, text=f"+{len(busy_slots)-4} ca", font=Theme.fonts.CAPTION, text_color=Theme.colors.TEXT_MUTED).pack(side="left", padx=2)

    def _check_resched_conflicts(self) -> bool:
        new_date = self.cal_picker.get_date()
        st = self.entry_new_st.get().strip()
        et = self.entry_new_et.get().strip()

        if not validate_time_format(st) or not validate_time_format(et):
            self.lbl_conflict_fb.configure(text="⚠️ Định dạng giờ không hợp lệ (HH:MM).", text_color=Theme.colors.WARNING)
            return False

        try:
            if time_to_minutes(et) <= time_to_minutes(st):
                self.lbl_conflict_fb.configure(text="⚠️ Giờ kết thúc phải sau giờ bắt đầu.", text_color=Theme.colors.WARNING)
                return False
        except Exception:
            return False

        if not self.schedule_service:
            return True

        day_schs = self.schedule_service.schedule_repo.get_by_date_range(new_date, new_date)
        conflicts = [
            s for s in day_schs
            if s.status.value != "CANCELLED" and s.id != self.schedule.id and is_time_overlap(st, et, s.start_time, s.end_time)
        ]

        if conflicts:
            c_desc = ", ".join(f"'{c.lesson_title}' ({c.start_time}-{c.end_time})" for c in conflicts[:2])
            self.lbl_conflict_fb.configure(
                text=f"❌ Trùng giờ với: {c_desc}! Vui lòng chọn giờ khác.",
                text_color=Theme.colors.DANGER,
            )
            return False

        self.lbl_conflict_fb.configure(
            text="✓ Khung giờ học trống, không bị trùng lịch.",
            text_color=Theme.colors.EMERALD,
        )
        return True

    def _save(self) -> None:
        self.lbl_error.configure(text="")
        if not self.target_student_id:
            self.lbl_error.configure(text="Lịch học này chưa gán học sinh cụ thể.")
            return

        status_str = self.status_var.get()
        status = AttendanceStatus(status_str)
        note = self.entry_note.get().strip()

        if status == AttendanceStatus.RESCHEDULED:
            if not self._check_resched_conflicts():
                self.lbl_error.configure(text="Vui lòng chọn khung giờ học hợp lệ và không bị trùng.")
                return

            new_date = self.cal_picker.get_date()
            new_st = self.entry_new_st.get().strip()
            new_et = self.entry_new_et.get().strip()

            try:
                new_sch = None
                if self.schedule_service:
                    dto_sch = ScheduleCreateDTO(
                        class_id=self.schedule.class_id,
                        student_id=self.target_student_id,
                        date=new_date,
                        start_time=new_st,
                        end_time=new_et,
                        location=self.schedule.location,
                        online_url=self.schedule.online_url,
                        lesson_title=self.schedule.lesson_title,
                        original_schedule_id=self.schedule.id,
                    )
                    new_sch = self.schedule_service.create_schedule(dto_sch)

                resched_note = f"Đổi sang ngày {format_date_display(parse_date(new_date))} ({new_st} - {new_et})"
                if note:
                    resched_note += f": {note}"

                dto = AttendanceCreateDTO(
                    schedule_id=self.schedule.id,
                    student_id=self.target_student_id,
                    attendance_date=self.schedule.date,
                    status=status,
                    note=resched_note,
                )
                self.attendance_service.mark_attendance(dto)

                # Cập nhật ca cũ thành RESCHEDULED và liên kết ca mới để ẩn ca cũ khỏi lịch tuần
                if self.schedule_service:
                    orig_m = self.schedule_service.schedule_repo.get_by_id(self.schedule.id)
                    if orig_m:
                        orig_m.status = ScheduleStatus.RESCHEDULED
                        if new_sch:
                            orig_m.rescheduled_to_id = new_sch.id
                        self.schedule_service.schedule_repo.update(orig_m)
                        event_bus.emit("schedules_changed", orig_m.id)

                sname = self.student.name if self.student else "học sinh"
                ToastManager.show(self.parent, f"🔄 Đã đổi lịch học cho {sname} sang ngày {format_date_display(parse_date(new_date))} ({new_st}-{new_et}).", level="success")
                self.destroy()
                if self.on_saved:
                    self.on_saved()
                return
            except Exception as e:
                self.lbl_error.configure(text=f"Lỗi đổi lịch: {e}")
                return

        # PRESENT or ABSENT
        try:
            dto = AttendanceCreateDTO(
                schedule_id=self.schedule.id,
                student_id=self.target_student_id,
                attendance_date=self.schedule.date,
                status=status,
                note=note,
            )
            self.attendance_service.mark_attendance(dto)

            sname = self.student.name if self.student else "học sinh"
            if status == AttendanceStatus.PRESENT:
                ToastManager.show(self.parent, f"✓ Đã điểm danh Có mặt cho {sname} (-1 buổi).", level="success")
            else:
                ToastManager.show(self.parent, f"Đã ghi nhận Vắng mặt cho {sname}.", level="info")

            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.lbl_error.configure(text=str(e))



class ClassAttendanceDialog(BaseModalDialog):
    """Modal dialog displaying student list for offline classroom attendance with rescheduling support."""

    def __init__(
        self,
        parent,
        attendance_service: AttendanceService,
        student_service: StudentService,
        class_service: ClassService,
        schedule_service: ScheduleService,
        schedule: ScheduleResponseDTO,
        on_saved: Optional[Callable] = None,
    ):
        self.attendance_service = attendance_service
        self.student_service = student_service
        self.class_service = class_service
        self.schedule_service = schedule_service
        self.schedule = schedule
        self.on_saved = on_saved
        self.student_vars: Dict[str, ctk.StringVar] = {}
        self.reschedule_data: Dict[str, dict] = {}
        self.resched_labels: Dict[str, ctk.CTkLabel] = {}

        class_title = schedule.class_name or schedule.lesson_title
        super().__init__(
            parent=parent,
            title=f"Điểm danh: {class_title}",
            subtitle=f"Lớp Offline • Ngày {schedule.date} ({schedule.start_time} - {schedule.end_time}) • {schedule.location or 'Phòng học 1'}",
            width=620,
            height=630,
        )

        self._load_data()
        self._build_form()

    def _load_data(self) -> None:
        self.students = []
        if self.schedule.class_id:
            try:
                c = self.class_service.get_class_by_id(self.schedule.class_id)
                for sid in c.student_ids:
                    st = self.student_service.get_student_by_id(sid)
                    if st:
                        self.students.append(st)
            except Exception:
                pass

        # Fallback if no class_id but student_id exists
        if not self.students and self.schedule.student_id:
            try:
                st = self.student_service.get_student_by_id(self.schedule.student_id)
                if st:
                    self.students.append(st)
            except Exception:
                pass

        # Existing records mapped by student_id
        records = self.attendance_service.get_attendance_for_schedule(self.schedule.id)
        self.existing_records = {r.student_id: r for r in records}

    def _build_form(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)

        # 1. Quick Action ToolBar
        toolbar = ctk.CTkFrame(self.body, fg_color=Theme.colors.BG_MUTED, corner_radius=8, height=44)
        toolbar.pack(fill="x", pady=(0, 10))

        lbl_count = ctk.CTkLabel(
            toolbar,
            text=f"📋 Sĩ số: {len(self.students)} học sinh",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        lbl_count.pack(side="left", padx=12, pady=8)

        btn_all_resched = ctk.CTkButton(
            toolbar,
            text="🔄 Đổi lịch cả lớp",
            font=Theme.fonts.CAPTION_BOLD,
            fg_color=Theme.colors.PURPLE,
            hover_color=Theme.colors.PURPLE_HOVER,
            height=28,
            corner_radius=6,
            command=self._open_class_reschedule_dialog,
        )
        btn_all_resched.pack(side="right", padx=(4, 10), pady=8)

        btn_all_absent = ctk.CTkButton(
            toolbar,
            text="✕ Tất cả vắng",
            font=Theme.fonts.CAPTION_BOLD,
            fg_color=Theme.colors.WARNING,
            hover_color="#D97706",
            height=28,
            corner_radius=6,
            command=self._mark_all_absent,
        )
        btn_all_absent.pack(side="right", padx=4, pady=8)

        btn_all_present = ctk.CTkButton(
            toolbar,
            text="✓ Tất cả có mặt",
            font=Theme.fonts.CAPTION_BOLD,
            fg_color=Theme.colors.EMERALD,
            hover_color=Theme.colors.EMERALD_HOVER,
            height=28,
            corner_radius=6,
            command=self._mark_all_present,
        )
        btn_all_present.pack(side="right", padx=4, pady=8)

        # 2. Scrollable student list
        self.scroll_list = ctk.CTkScrollableFrame(self.body, fg_color="transparent", height=380)
        self.scroll_list.pack(fill="both", expand=True)

        if not self.students:
            lbl_empty = ctk.CTkLabel(
                self.scroll_list,
                text="Lớp học này hiện chưa có học sinh nào.\nVui lòng thêm học sinh vào lớp trong màn hình 'Danh sách lớp học'.",
                font=Theme.fonts.BODY,
                text_color=Theme.colors.TEXT_MUTED,
                justify="center",
            )
            lbl_empty.pack(pady=40)
            return

        for st in self.students:
            self._create_student_row(st)

        # Error label in footer
        self.lbl_error = ctk.CTkLabel(
            self.footer,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.DANGER,
            wraplength=340,
            justify="left",
        )
        self.lbl_error.pack(side="left", padx=4)

        # Footer Buttons
        if getattr(self.schedule, "original_schedule_id", None):
            btn_del_resched = ctk.CTkButton(
                self.footer,
                text="🗑️ Hủy đổi lịch (Khôi phục ca cũ)",
                font=Theme.fonts.CAPTION_BOLD,
                fg_color=Theme.colors.DANGER,
                hover_color="#DC2626",
                text_color=Theme.colors.TEXT_WHITE,
                height=34,
                corner_radius=Theme.radius.BUTTON,
                command=self._confirm_delete_rescheduled,
            )
            btn_del_resched.pack(side="left", padx=4)

        btn_cancel = OutlineButton(self.footer, text="Đóng", command=self.destroy, width=90)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = PrimaryButton(self.footer, text="Lưu điểm danh", command=self._save_all, width=150)
        btn_save.pack(side="right")

    def _create_student_row(self, student) -> None:
        row_frame = ctk.CTkFrame(
            self.scroll_list,
            fg_color=Theme.colors.BG_CARD,
            border_color=Theme.colors.BORDER_SUBTLE,
            border_width=1,
            corner_radius=8,
        )
        row_frame.pack(fill="x", pady=4, padx=2)

        # Left Info
        info_col = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_col.pack(side="left", padx=12, pady=8, fill="x", expand=True)

        lbl_name = ctk.CTkLabel(
            info_col,
            text=student.name,
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_name.pack(anchor="w")

        # Balance warning
        bal = student.remaining_lessons
        bal_color = Theme.colors.DANGER if bal <= 1 else Theme.colors.TEXT_SECONDARY
        bal_text = f"SĐT: {student.phone or '---'}  •  Còn lại: {bal} buổi"
        lbl_sub = ctk.CTkLabel(
            info_col,
            text=bal_text,
            font=Theme.fonts.CAPTION,
            text_color=bal_color,
            anchor="w",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Reschedule preview info container
        lbl_resched = ctk.CTkLabel(
            info_col,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.PURPLE,
            anchor="w",
            wraplength=280,
            justify="left",
        )
        lbl_resched.pack(anchor="w", pady=(2, 0))
        self.resched_labels[student.id] = lbl_resched

        # Right status options (Radio buttons Có mặt / Vắng mặt / Đổi lịch)
        rec = self.existing_records.get(student.id)
        default_status = rec.status.value if rec else AttendanceStatus.PRESENT.value
        status_var = ctk.StringVar(value=default_status)
        self.student_vars[student.id] = status_var

        opts = ctk.CTkFrame(row_frame, fg_color="transparent")
        opts.pack(side="right", padx=10, pady=8)

        rb_present = ctk.CTkRadioButton(
            opts,
            text="Có mặt",
            variable=status_var,
            value=AttendanceStatus.PRESENT.value,
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            fg_color=Theme.colors.EMERALD,
            width=70,
            command=lambda s=student: self._on_status_changed(s, AttendanceStatus.PRESENT),
        )
        rb_present.pack(side="left", padx=3)

        rb_absent = ctk.CTkRadioButton(
            opts,
            text="Vắng",
            variable=status_var,
            value=AttendanceStatus.ABSENT.value,
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            fg_color=Theme.colors.WARNING,
            width=60,
            command=lambda s=student: self._on_status_changed(s, AttendanceStatus.ABSENT),
        )
        rb_absent.pack(side="left", padx=3)

        rb_resched = ctk.CTkRadioButton(
            opts,
            text="Đổi lịch",
            variable=status_var,
            value=AttendanceStatus.RESCHEDULED.value,
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            fg_color=Theme.colors.PURPLE,
            width=70,
            command=lambda s=student: self._open_reschedule_dialog(s),
        )
        rb_resched.pack(side="left", padx=3)

    def _on_status_changed(self, student, status: AttendanceStatus) -> None:
        # Clear reschedule info if user switches back to present or absent
        if student.id in self.reschedule_data:
            del self.reschedule_data[student.id]
        lbl = self.resched_labels.get(student.id)
        if lbl:
            lbl.configure(text="")

    def _open_reschedule_dialog(self, student) -> None:
        """Open RescheduleDialog to pick target class, date and time slot for this student."""
        from frontend.dialogs.reschedule_dialog import RescheduleDialog

        def on_done(data: dict):
            self.reschedule_data[student.id] = data
            lbl = self.resched_labels.get(student.id)
            if lbl:
                lbl.configure(
                    text=f"🔄 Đổi sang: {data['target_class_name']} • Ngày {data['date']} ({data['start_time']} - {data['end_time']})"
                )
            self.student_vars[student.id].set(AttendanceStatus.RESCHEDULED.value)

        RescheduleDialog(
            parent=self.winfo_toplevel(),
            schedule_service=self.schedule_service,
            student_service=self.student_service,
            class_service=self.class_service,
            schedule=self.schedule,
            student_id=student.id,
            on_rescheduled=on_done,
        )

    def _open_class_reschedule_dialog(self) -> None:
        """Open RescheduleDialog to reschedule the entire class together."""
        from frontend.dialogs.reschedule_dialog import RescheduleDialog

        def on_done(data: dict):
            for st in self.students:
                st_data = dict(data)
                st_data["student_id"] = st.id
                st_data["student_name"] = st.name
                self.reschedule_data[st.id] = st_data
                lbl = self.resched_labels.get(st.id)
                if lbl:
                    lbl.configure(
                        text=f"🔄 Đổi sang: {data['target_class_name']} • Ngày {data['date']} ({data['start_time']} - {data['end_time']})"
                    )
                self.student_vars[st.id].set(AttendanceStatus.RESCHEDULED.value)

        RescheduleDialog(
            parent=self.winfo_toplevel(),
            schedule_service=self.schedule_service,
            student_service=self.student_service,
            class_service=self.class_service,
            schedule=self.schedule,
            student_id=None,
            on_rescheduled=on_done,
        )

    def _mark_all_present(self) -> None:
        self.reschedule_data.clear()
        for lbl in self.resched_labels.values():
            lbl.configure(text="")
        for var in self.student_vars.values():
            var.set(AttendanceStatus.PRESENT.value)

    def _mark_all_absent(self) -> None:
        self.reschedule_data.clear()
        for lbl in self.resched_labels.values():
            lbl.configure(text="")
        for var in self.student_vars.values():
            var.set(AttendanceStatus.ABSENT.value)

    def _save_all(self) -> None:
        self.lbl_error.configure(text="")
        if not self.students:
            self.destroy()
            return

        success_count = 0
        errors = []
        created_schedules = set()
        created_new_sch_ids = []

        for st in self.students:
            val = self.student_vars.get(st.id)
            if not val:
                continue
            status = AttendanceStatus(val.get())

            note = ""
            # If RESCHEDULED and user selected a new class & time slot
            if status == AttendanceStatus.RESCHEDULED and st.id in self.reschedule_data:
                data = self.reschedule_data[st.id]
                note = f"Đổi sang lớp {data['target_class_name']}, ngày {data['date']} ({data['start_time']} - {data['end_time']})"
                
                # Check if this new schedule has already been created (for group class reschedule)
                sch_key = (
                    data["target_class_id"],
                    None if data["target_class_id"] else st.id,
                    data["date"],
                    data["start_time"],
                    data["end_time"],
                )
                day_schs = self.schedule_service.schedule_repo.get_by_date_range(data["date"], data["date"])
                exact_session = any(
                    s.class_id == data["target_class_id"] and s.start_time == data["start_time"] and s.end_time == data["end_time"] and s.status.value != "CANCELLED"
                    for s in day_schs
                )

                if not exact_session and sch_key not in created_schedules:
                    try:
                        dto_sch = ScheduleCreateDTO(
                            class_id=data["target_class_id"],
                            student_id=None if data["target_class_id"] else st.id,
                            date=data["date"],
                            start_time=data["start_time"],
                            end_time=data["end_time"],
                            location=data["location"],
                            online_url=data["online_url"],
                            lesson_title=data["lesson_title"],
                            original_schedule_id=self.schedule.id,
                        )
                        new_sch = self.schedule_service.create_schedule(dto_sch)
                        created_schedules.add(sch_key)
                        created_new_sch_ids.append(new_sch.id)
                    except Exception as e:
                        errors.append(f"Không thể tạo ca học mới: {str(e)}")

            try:
                dto = AttendanceCreateDTO(
                    schedule_id=self.schedule.id,
                    student_id=st.id,
                    attendance_date=self.schedule.date,
                    status=status,
                    note=note,
                )
                self.attendance_service.mark_attendance(dto)
                success_count += 1
            except Exception as e:
                errors.append(f"{st.name}: {str(e)}")

        if errors:
            self.lbl_error.configure(text="; ".join(errors[:2]))
            return

        # Khi đổi lịch: Cập nhật ca cũ thành RESCHEDULED để ẩn khỏi bảng lịch tuần
        resched_students_count = sum(
            1 for st in self.students
            if self.student_vars.get(st.id) and self.student_vars[st.id].get() == AttendanceStatus.RESCHEDULED.value
        )
        if resched_students_count > 0 and (resched_students_count == len(self.students) or len(self.students) <= 1):
            orig_m = self.schedule_service.schedule_repo.get_by_id(self.schedule.id)
            if orig_m:
                orig_m.status = ScheduleStatus.RESCHEDULED
                if created_new_sch_ids:
                    orig_m.rescheduled_to_id = created_new_sch_ids[0]
                self.schedule_service.schedule_repo.update(orig_m)
                event_bus.emit("schedules_changed", orig_m.id)

        self.destroy()
        if self.on_saved:
            self.on_saved()

    def _confirm_delete_rescheduled(self) -> None:
        """Allow deleting an accidentally placed makeup/rescheduled session and restore the original."""
        from frontend.components.dialogs import ConfirmDialog
        from frontend.components.toast import ToastManager

        def _on_confirm():
            self.schedule_service.delete_schedule(self.schedule.id)
            ToastManager.show(self.winfo_toplevel(), "Đã xóa ca đổi lịch và khôi phục ca học cũ.", level="success")
            self.destroy()
            if self.on_saved:
                self.on_saved()

        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Hủy ca đổi lịch",
            message=f"Bạn có chắc muốn xóa ca đổi lịch này?\nCa học cũ sẽ được tự động khôi phục lại trên lịch.",
            on_confirm=_on_confirm,
        )
