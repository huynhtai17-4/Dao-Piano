"""Dialog for registering or editing a student with multi-session offline class selection and automatic 1-on-1/Online class creation."""

from __future__ import annotations
from typing import Optional, Callable, List, Dict, Tuple
import customtkinter as ctk

from frontend.theme import Theme
from backend.core.enums import ClassType, ScheduleStatus
from backend.core.dates import today_date, today_str, parse_date
from backend.core.time_utils import is_time_overlap, time_to_minutes, validate_time_format
from backend.core.validators import validate_phone, sanitize_phone, validate_non_empty_str
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.services.schedule_service import ScheduleService
from backend.application.dto.student_dto import StudentCreateDTO, StudentUpdateDTO, StudentResponseDTO
from backend.application.dto.class_dto import ClassCreateDTO
from frontend.components.dialogs import BaseModalDialog
from frontend.components.buttons import PrimaryButton, OutlineButton
from frontend.dialogs.class_dialog import ClassDialog

WEEKDAY_NAMES = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
WEEKDAY_INDEX_MAP = {name: idx for idx, name in enumerate(WEEKDAY_NAMES)}

TIME_SLOT_PRESETS = [
    "17:30 - 18:30",
    "18:00 - 19:00",
    "18:30 - 19:30",
    "19:00 - 20:00",
    "19:30 - 20:30",
    "20:00 - 21:00",
    "08:00 - 09:00",
    "09:00 - 10:00",
    "10:00 - 11:00",
    "14:00 - 15:00",
    "15:00 - 16:00",
    "16:00 - 17:00",
    "Tự nhập giờ...",
]


class StudentDialog(BaseModalDialog):
    """Modal form for adding and modifying student details with per-session class choices and auto-class creation."""

    def __init__(
        self,
        parent,
        student_service: StudentService,
        class_service: ClassService,
        schedule_service: Optional[ScheduleService] = None,
        student: Optional[StudentResponseDTO] = None,
        on_saved: Optional[Callable] = None,
    ):
        self.student_service = student_service
        self.class_service = class_service
        self.schedule_service = schedule_service
        self.student = student
        self.on_saved = on_saved
        self.is_edit = student is not None
        self.slot_widgets: List[Dict] = []
        self.offline_session_widgets: List[Dict] = []

        super().__init__(
            parent=parent,
            title="Chỉnh sửa thông tin học sinh" if self.is_edit else "Thêm học sinh mới",
            subtitle="Cập nhật số buổi học còn lại, hình thức học và xếp lịch ca học",
            width=620,
            height=700,
        )

        self._load_classes()
        self._build_form()

    def _load_classes(self) -> None:
        """Load and inspect classes specifically for offline selection with their recurring slots."""
        all_classes = self.class_service.get_classes()
        self.offline_classes = [c for c in all_classes if c.class_type == ClassType.OFFLINE]

        self.offline_class_map = {}
        self.offline_class_options = ["-- Chọn lớp offline mong muốn --"]

        for c in self.offline_classes:
            slots_summary = ""
            if self.schedule_service:
                slots = self.schedule_service.get_class_recurring_slots(c.id)
                if slots:
                    slots_summary = " • " + ", ".join(f"{s['day_name']} {s['start_time']}-{s['end_time']}" for s in slots)
                else:
                    slots_summary = " • (Chưa có suất học)"

            cap_str = f"[{len(c.student_ids)}/{c.max_students} bạn]"
            label = f"{c.name} {cap_str}{slots_summary}"
            self.offline_class_map[label] = c.id
            self.offline_class_options.append(label)

    def _build_form(self) -> None:
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        # Scrollable container inside modal body
        self.scroll_frame = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        row = 0
        # 1. Full Name
        ctk.CTkLabel(
            self.scroll_frame, text="Họ và tên: *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).grid(row=row, column=0, sticky="w", pady=6)
        self.entry_name = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="Ví dụ: Nguyễn Văn An",
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
        )
        self.entry_name.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        if self.student:
            self.entry_name.insert(0, self.student.name)

        row += 1
        # 2. Phone Number
        ctk.CTkLabel(
            self.scroll_frame, text="Số điện thoại: *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).grid(row=row, column=0, sticky="w", pady=6)
        self.entry_phone = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="Ví dụ: 0987654321, 0388123456...",
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
        )
        self.entry_phone.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        if self.student:
            self.entry_phone.insert(0, self.student.phone)

        row += 1
        # 3. PROMINENT REMAINING LESSONS CONTROLLER (Không có phần chỉnh nhanh theo yêu cầu)
        lbl_rem_title = "Số buổi còn lại: *" if self.is_edit else "Số buổi đăng ký: *"
        ctk.CTkLabel(
            self.scroll_frame, text=lbl_rem_title, font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).grid(row=row, column=0, sticky="w", pady=(8, 4))

        # Lessons Control Panel Frame
        lessons_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="#F8FAFC",
            border_color="#CBD5E1",
            border_width=1,
            corner_radius=8,
        )
        lessons_card.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=(8, 4))
        lessons_card.grid_columnconfigure(1, weight=1)

        # Stepper Row [-] [Input] [+] [Status Tag]
        stepper_row = ctk.CTkFrame(lessons_card, fg_color="transparent")
        stepper_row.pack(fill="x", padx=8, pady=8)

        # Minus button
        btn_minus = ctk.CTkButton(
            stepper_row,
            text="➖",
            width=36,
            height=36,
            font=Theme.fonts.BODY_BOLD,
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#334155",
            corner_radius=6,
            command=lambda: self._adjust_lessons(-1),
        )
        btn_minus.pack(side="left", padx=(0, 6))

        # Lessons Entry (centered, bold)
        self.entry_lessons = ctk.CTkEntry(
            stepper_row,
            width=80,
            height=36,
            font=Theme.fonts.H2,
            justify="center",
            corner_radius=Theme.radius.INPUT,
        )
        self.entry_lessons.pack(side="left", padx=(0, 6))
        init_lessons = self.student.remaining_lessons if self.student else 8
        self.entry_lessons.insert(0, str(init_lessons))
        self.entry_lessons.bind("<KeyRelease>", lambda e: self._update_lessons_status_label())

        # Plus button
        btn_plus = ctk.CTkButton(
            stepper_row,
            text="➕",
            width=36,
            height=36,
            font=Theme.fonts.BODY_BOLD,
            fg_color=Theme.colors.EMERALD_LIGHT,
            hover_color="#A7F3D0",
            text_color="#047857",
            corner_radius=6,
            command=lambda: self._adjust_lessons(1),
        )
        btn_plus.pack(side="left", padx=(0, 10))

        # Status badge label
        self.lbl_lessons_status = ctk.CTkLabel(
            stepper_row,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            anchor="w",
        )
        self.lbl_lessons_status.pack(side="left", fill="x", expand=True)

        self._update_lessons_status_label()

        row += 1
        # 4. Class Type Selection
        ctk.CTkLabel(
            self.scroll_frame, text="Hình thức học: *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).grid(row=row, column=0, sticky="w", pady=8)

        self.opt_type = ctk.CTkOptionMenu(
            self.scroll_frame,
            values=[
                ClassType.OFFLINE.display_name,
                ClassType.ONE_ON_ONE.display_name,
                ClassType.ONLINE.display_name,
            ],
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.EMERALD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_type_changed,
        )
        self.opt_type.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)
        if self.student:
            self.opt_type.set(self.student.class_type_display)
        else:
            self.opt_type.set(ClassType.OFFLINE.display_name)

        row += 1
        # 5. OFFLINE CLASS SELECTION FRAME (Học 2 buổi/tuần thì Buổi 1 chọn lớp nào, Buổi 2 chọn lớp nào)
        self.frame_offline = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_offline.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        self.frame_offline.grid_columnconfigure(0, weight=1)

        # Header with action button
        off_header = ctk.CTkFrame(self.frame_offline, fg_color="transparent")
        off_header.pack(fill="x", pady=(2, 6))

        ctk.CTkLabel(
            off_header,
            text="🏫 Chọn lớp Offline theo từng buổi học trong tuần: *",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(side="left")

        btn_new_class = ctk.CTkButton(
            off_header,
            text="➕ Mở lớp Offline mới",
            font=Theme.fonts.CAPTION_BOLD,
            height=28,
            fg_color="#EEF2FF",
            hover_color="#E0E7FF",
            text_color="#4F46E5",
            border_color="#C7D2FE",
            border_width=1,
            corner_radius=6,
            command=self._open_create_offline_class_modal,
        )
        btn_new_class.pack(side="right")

        # Number of sessions per week selector
        off_count_row = ctk.CTkFrame(self.frame_offline, fg_color="transparent")
        off_count_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            off_count_row,
            text="Số buổi học Offline / tuần:",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(side="left")

        self.opt_offline_sessions_count = ctk.CTkOptionMenu(
            off_count_row,
            values=["1 buổi / tuần", "2 buổi / tuần", "3 buổi / tuần"],
            font=Theme.fonts.BODY,
            height=32,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.OCEAN,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_offline_sessions_count_changed,
            width=130,
        )
        self.opt_offline_sessions_count.pack(side="left", padx=(10, 0))
        self.opt_offline_sessions_count.set("2 buổi / tuần")

        # Container for per-session class selectors (Buổi 1 chọn lớp nào, Buổi 2 chọn lớp nào)
        self.container_offline_sessions = ctk.CTkFrame(self.frame_offline, fg_color="transparent")
        self.container_offline_sessions.pack(fill="x", pady=(2, 6))

        self._render_offline_sessions_pickers()

        row += 1
        # 6. WEEKLY SCHEDULE FRAME (For 1-on-1 and Online: Tạo ra ca học trong tuần)
        self.frame_schedule = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_schedule.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        self.frame_schedule.grid_columnconfigure(1, weight=1)

        # Informational badge explaining auto-class creation
        info_cls_badge = ctk.CTkFrame(self.frame_schedule, fg_color="#F0FDF4", border_color="#BBF7D0", border_width=1, corner_radius=6)
        info_cls_badge.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            info_cls_badge,
            text="✨ Hệ thống sẽ tự động tạo lớp học trong Danh sách lớp và xếp lịch dạy tương ứng.",
            font=Theme.fonts.CAPTION_BOLD,
            text_color="#047857",
        ).pack(anchor="w", padx=10, pady=6)

        # In Edit mode: optional checkbox whether to update weekly schedule
        self.var_update_schedule = ctk.BooleanVar(value=not self.is_edit)
        if self.is_edit:
            self.chk_frame = ctk.CTkFrame(self.frame_schedule, fg_color="#F1F5F9", corner_radius=6)
            self.chk_frame.pack(fill="x", pady=(0, 6), padx=2)
            self.chk_update_sched = ctk.CTkCheckBox(
                self.chk_frame,
                text="☑ Cập nhật lại ca học trong tuần cho học sinh này",
                variable=self.var_update_schedule,
                font=Theme.fonts.BODY_BOLD,
                command=self._on_toggle_schedule_update,
            )
            self.chk_update_sched.pack(anchor="w", padx=10, pady=8)

        # Sub-container for schedule controls
        self.frame_schedule_controls = ctk.CTkFrame(self.frame_schedule, fg_color="transparent")
        self.frame_schedule_controls.pack(fill="x")

        sched_lbl_row = ctk.CTkFrame(self.frame_schedule_controls, fg_color="transparent")
        sched_lbl_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            sched_lbl_row,
            text="🗓️ Số ca học / tuần:",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(side="left")

        self.opt_lessons_per_week = ctk.CTkOptionMenu(
            sched_lbl_row,
            values=["1 buổi / tuần", "2 buổi / tuần", "3 buổi / tuần", "4 buổi / tuần"],
            font=Theme.fonts.BODY,
            height=32,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.EMERALD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_lessons_per_week_changed,
            width=130,
        )
        self.opt_lessons_per_week.pack(side="left", padx=(10, 0))
        self.opt_lessons_per_week.set("2 buổi / tuần")

        # Container for dynamic slot rows
        self.container_slots = ctk.CTkFrame(self.frame_schedule_controls, fg_color="transparent")
        self.container_slots.pack(fill="x", pady=(4, 8))

        row += 1
        # Hint label
        ctk.CTkLabel(
            self.scroll_frame,
            text="* Hệ thống tự động trừ 1 buổi khi điểm danh Có mặt và cộng thêm khi ghi nhận học phí.",
            font=Theme.fonts.CAPTION,
            text_color=Theme.colors.TEXT_MUTED,
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 8))

        # Inline error banner
        self.lbl_error = ctk.CTkLabel(
            self.footer, text="", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.DANGER, wraplength=320, justify="left"
        )
        self.lbl_error.pack(side="left", padx=4)

        # Buttons
        btn_cancel = OutlineButton(self.footer, text="Hủy", command=self.destroy, width=90)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = PrimaryButton(self.footer, text="Lưu học sinh", command=self._save, width=130)
        btn_save.pack(side="right")

        # Initial layout setup based on current type
        self._on_type_changed(self.opt_type.get())

    def _adjust_lessons(self, delta: int) -> None:
        try:
            curr = int(self.entry_lessons.get().strip())
        except Exception:
            curr = 0
        new_val = max(0, curr + delta)
        self.entry_lessons.delete(0, "end")
        self.entry_lessons.insert(0, str(new_val))
        self._update_lessons_status_label()

    def _update_lessons_status_label(self) -> None:
        try:
            rem = int(self.entry_lessons.get().strip())
        except Exception:
            rem = 0

        if rem == 0:
            self.lbl_lessons_status.configure(
                text="⚠️ Hết số buổi (Chưa đóng)",
                text_color=Theme.colors.DANGER,
            )
        elif rem <= 2:
            self.lbl_lessons_status.configure(
                text=f"⚡ Sắp hết ({rem} buổi)",
                text_color=Theme.colors.WARNING,
            )
        else:
            self.lbl_lessons_status.configure(
                text=f"✓ Còn {rem} buổi học",
                text_color=Theme.colors.EMERALD,
            )

    def _on_type_changed(self, choice: str) -> None:
        """Toggle between Offline class selection and 1-on-1/Online weekly schedule slots."""
        if choice == ClassType.OFFLINE.display_name:
            self.frame_offline.grid()
            self.frame_schedule.grid_remove()
            self._render_offline_sessions_pickers()
        else:
            self.frame_offline.grid_remove()
            self.frame_schedule.grid()
            self._on_toggle_schedule_update()

    def _on_offline_sessions_count_changed(self, _=None) -> None:
        self._render_offline_sessions_pickers()

    def _render_offline_sessions_pickers(self) -> None:
        """Render distinct class pickers for each session (e.g. Buổi 1 chọn lớp nào, Buổi 2 chọn lớp nào)."""
        for child in self.container_offline_sessions.winfo_children():
            child.destroy()
        self.offline_session_widgets.clear()

        try:
            cnt = int(self.opt_offline_sessions_count.get().split(" ")[0])
        except Exception:
            cnt = 2

        for i in range(cnt):
            card = ctk.CTkFrame(
                self.container_offline_sessions,
                fg_color="#F8FAFC",
                border_color="#CBD5E1",
                border_width=1,
                corner_radius=8,
            )
            card.pack(fill="x", pady=4)

            # Header row
            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=10, pady=(8, 4))

            lbl_b = ctk.CTkLabel(
                hdr,
                text=f"🗓️ Buổi {i + 1} trong tuần: Chọn lớp Offline mong muốn *",
                font=Theme.fonts.BODY_BOLD,
                text_color=Theme.colors.TEXT_PRIMARY,
            )
            lbl_b.pack(side="left")

            # Option menu for this session's class
            opt_menu = ctk.CTkOptionMenu(
                card,
                values=self.offline_class_options,
                font=Theme.fonts.BODY,
                height=34,
                corner_radius=Theme.radius.INPUT,
                fg_color=Theme.colors.BG_CARD,
                button_color=Theme.colors.OCEAN,
                text_color=Theme.colors.TEXT_PRIMARY,
                command=lambda _, idx=i: self._on_session_class_changed(idx),
            )
            opt_menu.pack(fill="x", padx=10, pady=(0, 4))

            # Default selection
            if len(self.offline_class_options) > 1:
                # Pre-fill with different classes if available
                default_idx = min(i + 1, len(self.offline_class_options) - 1)
                opt_menu.set(self.offline_class_options[default_idx])

            # Detail label showing slots and capacity for this session's class
            lbl_detail = ctk.CTkLabel(
                card,
                text="",
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.TEXT_SECONDARY,
                anchor="w",
                justify="left",
            )
            lbl_detail.pack(fill="x", padx=10, pady=(0, 8))

            self.offline_session_widgets.append({
                "opt_menu": opt_menu,
                "lbl_detail": lbl_detail,
            })
            self._update_session_class_detail(i)

    def _on_session_class_changed(self, idx: int) -> None:
        self._update_session_class_detail(idx)

    def _update_session_class_detail(self, idx: int) -> None:
        if idx >= len(self.offline_session_widgets):
            return
        w = self.offline_session_widgets[idx]
        sel_label = w["opt_menu"].get()
        class_id = self.offline_class_map.get(sel_label)
        if not class_id:
            w["lbl_detail"].configure(text="⚠️ Chưa chọn lớp cho buổi này.", text_color=Theme.colors.WARNING)
            return

        try:
            cl = self.class_service.get_class_by_id(class_id)
            slots = self.schedule_service.get_class_recurring_slots(cl.id) if self.schedule_service else []
            if slots:
                s_str = ", ".join(f"{s['day_name']} {s['start_time']}-{s['end_time']}" for s in slots)
                txt = f"✓ Suất học của lớp: {s_str} • Sĩ số: {cl.current_student_count}/{cl.max_students} bạn"
                col = Theme.colors.EMERALD
            else:
                txt = f"⚠️ Lớp '{cl.name}' chưa xếp lịch suất học trên thời khóa biểu. Sĩ số: {cl.current_student_count}/{cl.max_students}"
                col = Theme.colors.WARNING
            w["lbl_detail"].configure(text=txt, text_color=col)
        except Exception:
            pass

    def _on_toggle_schedule_update(self) -> None:
        """When in edit mode, enable/disable schedule slots editing based on checkbox."""
        if self.is_edit and not self.var_update_schedule.get():
            self.frame_schedule_controls.pack_forget()
        else:
            self.frame_schedule_controls.pack(fill="x")
            self._render_slot_pickers()

    def _open_create_offline_class_modal(self) -> None:
        """Open class dialog to quickly create a new offline class with recurring slots, then select it."""
        def on_class_created():
            self._load_classes()
            for w in self.offline_session_widgets:
                w["opt_menu"].configure(values=self.offline_class_options)
            if len(self.offline_class_options) > 1 and self.offline_session_widgets:
                self.offline_session_widgets[-1]["opt_menu"].set(self.offline_class_options[-1])
                self._update_session_class_detail(len(self.offline_session_widgets) - 1)

        ClassDialog(
            parent=self.winfo_toplevel(),
            class_service=self.class_service,
            schedule_service=self.schedule_service,
            initial_type=ClassType.OFFLINE,
            on_saved=on_class_created,
        )

    def _on_lessons_per_week_changed(self, _=None) -> None:
        self._render_slot_pickers()

    def _get_lessons_per_week_count(self) -> int:
        val = self.opt_lessons_per_week.get()
        try:
            return int(val.split(" ")[0])
        except Exception:
            return 2

    def _get_existing_student_slots(self) -> List[Tuple[str, str, str]]:
        """If editing, extract existing student recurring slots (day_name, start_time, end_time)."""
        if not self.student or not self.schedule_service:
            return []
        all_s = self.schedule_service.schedule_repo.get_by_student_id(self.student.id)
        seen = set()
        slots = []
        for s in all_s:
            if s.status != ScheduleStatus.CANCELLED:
                try:
                    w_idx = parse_date(s.date).weekday()
                    d_name = WEEKDAY_NAMES[w_idx]
                    key = (d_name, s.start_time, s.end_time)
                    if key not in seen:
                        seen.add(key)
                        slots.append(key)
                except Exception:
                    pass
        return slots

    def _render_slot_pickers(self) -> None:
        """Render dynamic weekday & time slot selectors for 1-on-1 and online students."""
        for child in self.container_slots.winfo_children():
            child.destroy()
        self.slot_widgets.clear()

        existing_slots = self._get_existing_student_slots() if self.is_edit else []
        count = self._get_lessons_per_week_count()

        default_days = ["Thứ 2", "Thứ 5", "Thứ 4", "Thứ 7", "Thứ 3", "Thứ 6", "Chủ Nhật"]
        default_slots = [("18:00", "19:00"), ("18:00", "19:00"), ("19:30", "20:30"), ("08:30", "09:30")]

        for i in range(count):
            card = ctk.CTkFrame(
                self.container_slots,
                fg_color=Theme.colors.BG_MUTED,
                border_color=Theme.colors.BORDER_SUBTLE,
                border_width=1,
                corner_radius=8,
            )
            card.pack(fill="x", pady=4, padx=2)

            lbl_title = ctk.CTkLabel(
                card,
                text=f"🗓️ Buổi học {i + 1} trong tuần:",
                font=Theme.fonts.BODY_BOLD,
                text_color=Theme.colors.TEXT_PRIMARY,
            )
            lbl_title.pack(anchor="w", padx=10, pady=(6, 4))

            ctrl_row = ctk.CTkFrame(card, fg_color="transparent")
            ctrl_row.pack(fill="x", padx=10, pady=(0, 4))

            init_day = existing_slots[i][0] if i < len(existing_slots) else default_days[i % len(default_days)]
            init_st = existing_slots[i][1] if i < len(existing_slots) else default_slots[i % len(default_slots)][0]
            init_et = existing_slots[i][2] if i < len(existing_slots) else default_slots[i % len(default_slots)][1]

            # 1. Day selector
            ctk.CTkLabel(ctrl_row, text="Thứ:", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.TEXT_SECONDARY).pack(side="left", padx=(0, 4))
            opt_day = ctk.CTkOptionMenu(
                ctrl_row,
                values=WEEKDAY_NAMES,
                font=Theme.fonts.BODY,
                height=32,
                corner_radius=Theme.radius.INPUT,
                fg_color=Theme.colors.BG_CARD,
                button_color=Theme.colors.EMERALD,
                text_color=Theme.colors.TEXT_PRIMARY,
                width=100,
                command=lambda _, idx=i: self._on_slot_changed(idx),
            )
            opt_day.pack(side="left", padx=(0, 10))
            opt_day.set(init_day)

            # 2. Time Slot Dropdown (Chọn khung giờ học)
            ctk.CTkLabel(ctrl_row, text="Khung giờ:", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.TEXT_SECONDARY).pack(side="left", padx=(0, 4))
            
            init_preset = f"{init_st} - {init_et}"
            if init_preset not in TIME_SLOT_PRESETS:
                init_preset = "Tự nhập giờ..."

            opt_time_slot = ctk.CTkOptionMenu(
                ctrl_row,
                values=TIME_SLOT_PRESETS,
                font=Theme.fonts.BODY,
                height=32,
                corner_radius=Theme.radius.INPUT,
                fg_color=Theme.colors.BG_CARD,
                button_color=Theme.colors.OCEAN,
                text_color=Theme.colors.TEXT_PRIMARY,
                width=135,
                command=lambda choice, idx=i: self._on_slot_preset_selected(choice, idx),
            )
            opt_time_slot.pack(side="left", padx=(0, 8))
            opt_time_slot.set(init_preset)

            # 3. Fine-tuning start / end time inputs
            ctk.CTkLabel(ctrl_row, text="Từ:", font=Theme.fonts.CAPTION, text_color=Theme.colors.TEXT_MUTED).pack(side="left", padx=(0, 2))
            entry_st = ctk.CTkEntry(ctrl_row, font=Theme.fonts.BODY, width=54, height=32, justify="center", corner_radius=Theme.radius.INPUT)
            entry_st.pack(side="left", padx=(0, 4))
            entry_st.insert(0, init_st)
            entry_st.bind("<KeyRelease>", lambda e, idx=i: self._on_slot_time_typed(idx))

            ctk.CTkLabel(ctrl_row, text="đến", font=Theme.fonts.CAPTION, text_color=Theme.colors.TEXT_MUTED).pack(side="left", padx=(0, 4))

            entry_et = ctk.CTkEntry(ctrl_row, font=Theme.fonts.BODY, width=54, height=32, justify="center", corner_radius=Theme.radius.INPUT)
            entry_et.pack(side="left")
            entry_et.insert(0, init_et)
            entry_et.bind("<KeyRelease>", lambda e, idx=i: self._on_slot_time_typed(idx))

            busy_row = ctk.CTkFrame(card, fg_color="transparent")
            busy_row.pack(fill="x", padx=10, pady=(2, 4))

            lbl_feedback = ctk.CTkLabel(
                card,
                text="✓ Khung giờ học trống, không bị trùng lịch.",
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.EMERALD,
                anchor="w",
                wraplength=520,
                justify="left",
            )
            lbl_feedback.pack(fill="x", padx=10, pady=(2, 6))

            self.slot_widgets.append({
                "opt_day": opt_day,
                "opt_time_slot": opt_time_slot,
                "entry_st": entry_st,
                "entry_et": entry_et,
                "busy_row": busy_row,
                "lbl_feedback": lbl_feedback,
            })
            self._update_busy_hours(i)

        self._check_all_slot_conflicts()

    def _on_slot_preset_selected(self, choice: str, idx: int) -> None:
        """When teacher picks a preset time slot from dropdown, auto-fill start & end times."""
        if idx >= len(self.slot_widgets):
            return
        w = self.slot_widgets[idx]
        if choice != "Tự nhập giờ...":
            parts = choice.split(" - ")
            if len(parts) == 2:
                st, et = parts[0].strip(), parts[1].strip()
                w["entry_st"].delete(0, "end")
                w["entry_st"].insert(0, st)
                w["entry_et"].delete(0, "end")
                w["entry_et"].insert(0, et)
        self._on_slot_changed(idx)

    def _on_slot_time_typed(self, idx: int) -> None:
        """When teacher manually edits start/end time, synchronize preset menu."""
        if idx >= len(self.slot_widgets):
            return
        w = self.slot_widgets[idx]
        st = w["entry_st"].get().strip()
        et = w["entry_et"].get().strip()
        curr_preset = f"{st} - {et}"
        if curr_preset in TIME_SLOT_PRESETS:
            w["opt_time_slot"].set(curr_preset)
        else:
            w["opt_time_slot"].set("Tự nhập giờ...")
        self._on_slot_changed(idx)

    def _update_busy_hours(self, slot_idx: int) -> None:
        """Display already scheduled hours on chosen weekday."""
        if slot_idx >= len(self.slot_widgets):
            return
        w = self.slot_widgets[slot_idx]
        busy_row = w["busy_row"]
        for child in busy_row.winfo_children():
            child.destroy()

        day_name = w["opt_day"].get()
        day_idx = WEEKDAY_INDEX_MAP.get(day_name, 0)

        all_schedules = self.schedule_service.schedule_repo.get_all() if self.schedule_service else []
        busy_slots: List[Tuple[str, str, str]] = []
        seen = set()

        for s in all_schedules:
            status_val = s.status.value if hasattr(s.status, "value") else str(s.status)
            if status_val == "CANCELLED":
                continue
            if self.student and s.student_id == self.student.id:
                continue
            try:
                if parse_date(s.date).weekday() == day_idx:
                    key = (s.start_time, s.end_time)
                    if key not in seen:
                        seen.add(key)
                        busy_slots.append((s.start_time, s.end_time, s.lesson_title))
            except Exception:
                continue

        busy_slots.sort(key=lambda x: x[0])

        lbl_header = ctk.CTkLabel(
            busy_row,
            text=f"Đã có lịch ({day_name}):",
            font=Theme.fonts.CAPTION_BOLD,
            text_color="#B91C1C",
        )
        lbl_header.pack(side="left", padx=(0, 6))

        if not busy_slots:
            lbl_free = ctk.CTkLabel(
                busy_row,
                text="✓ Chưa có lịch nào (trống cả ngày)",
                font=Theme.fonts.CAPTION,
                text_color=Theme.colors.EMERALD,
            )
            lbl_free.pack(side="left")
        else:
            shown_slots = busy_slots[:4]
            for st, et, title in shown_slots:
                tag = ctk.CTkFrame(
                    busy_row,
                    fg_color="#FEE2E2",
                    border_color="#FCA5A5",
                    border_width=1,
                    corner_radius=4,
                )
                tag.pack(side="left", padx=2)

                lbl_tag = ctk.CTkLabel(
                    tag,
                    text=f"🔒 {st}-{et}",
                    font=Theme.fonts.CAPTION_BOLD,
                    text_color="#DC2626",
                )
                lbl_tag.pack(padx=6, pady=1)

            if len(busy_slots) > 4:
                ctk.CTkLabel(
                    busy_row,
                    text=f"+{len(busy_slots) - 4} ca khác",
                    font=Theme.fonts.CAPTION,
                    text_color=Theme.colors.TEXT_MUTED,
                ).pack(side="left", padx=4)

    def _on_slot_changed(self, slot_idx: int) -> None:
        self._update_busy_hours(slot_idx)
        self._check_all_slot_conflicts()

    def _check_all_slot_conflicts(self) -> bool:
        """Verify real-time that none of the chosen slots conflict with existing sessions or each other."""
        has_any_conflict = False
        all_schedules = self.schedule_service.schedule_repo.get_all() if self.schedule_service else []
        chosen_slots: List[Tuple[int, str, str]] = []

        for i, w in enumerate(self.slot_widgets):
            day_name = w["opt_day"].get()
            day_idx = WEEKDAY_INDEX_MAP.get(day_name, 0)
            st = w["entry_st"].get().strip()
            et = w["entry_et"].get().strip()

            if not validate_time_format(st) or not validate_time_format(et):
                w["lbl_feedback"].configure(
                    text="⚠️ Giờ học phải có định dạng HH:MM (ví dụ: 18:00).",
                    text_color=Theme.colors.WARNING,
                )
                has_any_conflict = True
                continue

            try:
                if time_to_minutes(et) <= time_to_minutes(st):
                    w["lbl_feedback"].configure(
                        text="⚠️ Giờ kết thúc phải sau giờ bắt đầu.",
                        text_color=Theme.colors.WARNING,
                    )
                    has_any_conflict = True
                    continue
            except Exception:
                has_any_conflict = True
                continue

            # Check overlap against other chosen slots in this dialog
            slot_conflict = False
            for prev_idx, (p_day, p_st, p_et) in enumerate(chosen_slots):
                if p_day == day_idx and is_time_overlap(st, et, p_st, p_et):
                    w["lbl_feedback"].configure(
                        text=f"❌ Trùng giờ với Buổi {prev_idx + 1} bạn đã chọn trong tuần!",
                        text_color=Theme.colors.DANGER,
                    )
                    has_any_conflict = True
                    slot_conflict = True
                    break

            if slot_conflict:
                continue

            # Check conflict against existing calendar schedules
            conflicts = []
            seen_conflicts = set()
            for s in all_schedules:
                if s.status != ScheduleStatus.CANCELLED:
                    if self.student and s.student_id == self.student.id:
                        continue
                    try:
                        s_weekday = parse_date(s.date).weekday()
                        if s_weekday == day_idx and is_time_overlap(st, et, s.start_time, s.end_time):
                            c_title = s.lesson_title or s.class_name or "Ca học khác"
                            entry = f"'{c_title}' ({s.start_time}-{s.end_time})"
                            if entry not in seen_conflicts:
                                seen_conflicts.add(entry)
                                conflicts.append(entry)
                    except Exception:
                        pass

            if conflicts:
                w["lbl_feedback"].configure(
                    text=f"❌ Trùng giờ với: {', '.join(conflicts)}! Vui lòng chọn giờ khác.",
                    text_color=Theme.colors.DANGER,
                )
                has_any_conflict = True
            else:
                w["lbl_feedback"].configure(
                    text="✓ Khung giờ học trống, tuyệt đối không bị trùng.",
                    text_color=Theme.colors.EMERALD,
                )

            chosen_slots.append((day_idx, st, et))

        return not has_any_conflict

    def _save(self) -> None:
        """Validate all inputs and persist student, auto-create classes and appropriate schedules."""
        self.lbl_error.configure(text="")

        try:
            # 1. Full name validation
            raw_name = self.entry_name.get()
            name = validate_non_empty_str(raw_name, "Họ và tên")

            # 2. Phone validation
            raw_phone = self.entry_phone.get()
            phone = sanitize_phone(raw_phone)
            if not validate_phone(phone):
                raise ValueError("Số điện thoại không hợp lệ (yêu cầu 10 chữ số tiêu chuẩn VN).")

            # 3. Remaining lessons validation
            raw_lessons = self.entry_lessons.get().strip()
            try:
                lessons = int(raw_lessons)
            except ValueError:
                raise ValueError("Số buổi học còn lại phải là số nguyên.")
            if lessons < 0:
                raise ValueError("Số buổi học còn lại không được là số âm.")

            # 4. Class Type & Class Assignment
            type_str = self.opt_type.get()
            type_map = {
                ClassType.OFFLINE.display_name: ClassType.OFFLINE,
                ClassType.ONE_ON_ONE.display_name: ClassType.ONE_ON_ONE,
                ClassType.ONLINE.display_name: ClassType.ONLINE,
            }
            class_type = type_map.get(type_str, ClassType.OFFLINE)
            class_id = None
            selected_offline_class_ids: List[str] = []

            # 4. Slot validation if 1-on-1 or Online student (must validate BEFORE creating any class entity)
            scheduled_slots: List[Dict] = []
            should_update_schedule = self.var_update_schedule.get() if (self.is_edit and class_type in (ClassType.ONE_ON_ONE, ClassType.ONLINE)) else (not self.is_edit and class_type in (ClassType.ONE_ON_ONE, ClassType.ONLINE))

            if should_update_schedule:
                if not self._check_all_slot_conflicts():
                    raise ValueError("Có khung giờ bị trùng lịch hoặc không hợp lệ. Vui lòng kiểm tra lại.")

                for w in self.slot_widgets:
                    d_name = w["opt_day"].get()
                    d_idx = WEEKDAY_INDEX_MAP.get(d_name, 0)
                    st = w["entry_st"].get().strip()
                    et = w["entry_et"].get().strip()
                    scheduled_slots.append({
                        "day_idx": d_idx,
                        "start_time": st,
                        "end_time": et,
                    })

            # 5. Class assignment or creation
            if class_type == ClassType.OFFLINE:
                for idx, w in enumerate(self.offline_session_widgets):
                    sel_opt = w["opt_menu"].get()
                    cid = self.offline_class_map.get(sel_opt)
                    if not cid:
                        raise ValueError(f"Vui lòng chọn lớp Offline cho Buổi {idx + 1}.")
                    selected_offline_class_ids.append(cid)

                class_id = selected_offline_class_ids[0]

            elif not self.is_edit and class_type in (ClassType.ONE_ON_ONE, ClassType.ONLINE):
                # RULE: Tự động thêm vào danh sách lớp khi thêm học sinh 1 kèm 1 và online
                auto_name = f"1 Kèm 1 - {name}" if class_type == ClassType.ONE_ON_ONE else f"Online - {name}"
                existing_classes = self.class_service.get_classes(class_type=class_type)
                reusable_class = next((c for c in existing_classes if c.name == auto_name and len(c.student_ids) == 0), None)
                if reusable_class:
                    class_id = reusable_class.id
                else:
                    cls_dto = ClassCreateDTO(
                        name=auto_name,
                        class_type=class_type,
                        max_students=1,
                    )
                    auto_created_cls = self.class_service.create_class(cls_dto)
                    class_id = auto_created_cls.id

            # 6. Execute persistence
            if self.is_edit:
                # If editing student and class_id wasn't changed
                final_cid = class_id or self.student.class_id
                dto_update = StudentUpdateDTO(
                    id=self.student.id,
                    name=name,
                    phone=phone,
                    date_of_birth=self.student.date_of_birth or "",
                    class_type=class_type,
                    class_id=final_cid,
                    remaining_lessons=lessons,
                    is_active=self.student.is_active,
                )
                self.student_service.update_student(dto_update)

                # Update offline class enrollments if offline
                if class_type == ClassType.OFFLINE and selected_offline_class_ids:
                    for cid in set(selected_offline_class_ids):
                        cl = self.class_service.class_repo.get_by_id(cid)
                        if cl and self.student.id not in cl.student_ids:
                            cl.student_ids.append(self.student.id)
                            self.class_service.class_repo.update(cl)

                # Only recreate recurring schedules if teacher explicitly chose to update schedule
                if should_update_schedule and self.schedule_service and scheduled_slots:
                    today = today_date()
                    today_s = today_str()
                    existing_s = self.schedule_service.schedule_repo.get_by_student_id(self.student.id)
                    for s in existing_s:
                        if s.date >= today_s and s.status == ScheduleStatus.SCHEDULED:
                            self.schedule_service.delete_schedule(s.id)

                    self.schedule_service.create_student_recurring_schedules(
                        self.student.id, scheduled_slots, class_type, num_weeks=8, class_id=final_cid
                    )
            else:
                dto_create = StudentCreateDTO(
                    name=name,
                    phone=phone,
                    date_of_birth="",
                    class_type=class_type,
                    class_id=class_id,
                    remaining_lessons=lessons,
                )
                created_student = self.student_service.create_student(dto_create)

                # Ensure student is enrolled in all selected offline classes (Buổi 1, Buổi 2...)
                if class_type == ClassType.OFFLINE and selected_offline_class_ids:
                    for cid in set(selected_offline_class_ids):
                        cl = self.class_service.class_repo.get_by_id(cid)
                        if cl and created_student.id not in cl.student_ids:
                            cl.student_ids.append(created_student.id)
                            self.class_service.class_repo.update(cl)

                # Generate recurring weekly schedules for new 1-on-1 or Online student
                if class_type in (ClassType.ONE_ON_ONE, ClassType.ONLINE) and self.schedule_service and scheduled_slots:
                    self.schedule_service.create_student_recurring_schedules(
                        created_student.id, scheduled_slots, class_type, num_weeks=8, class_id=class_id
                    )

            self.destroy()
            if self.on_saved:
                self.on_saved()

        except ValueError as ve:
            self.lbl_error.configure(text=str(ve))
        except Exception as e:
            self.lbl_error.configure(text=str(e))
