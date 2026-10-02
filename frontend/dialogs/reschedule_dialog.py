"""Modal dialog for rescheduling offline classes: existing classes or creating a new offline class."""

from __future__ import annotations
import calendar
from datetime import date, timedelta
from typing import Optional, Callable, Dict, List
import customtkinter as ctk

from frontend.theme import Theme
from backend.core.dates import parse_date, format_date_iso, format_date_display, today_date, today_str, WEEKDAY_VN
from backend.core.time_utils import is_time_overlap, time_to_minutes
from backend.core.enums import ClassType, ScheduleStatus
from backend.application.services.schedule_service import ScheduleService
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.dto.schedule_dto import ScheduleCreateDTO, ScheduleResponseDTO
from backend.application.dto.class_dto import ClassCreateDTO
from frontend.components.dialogs import BaseModalDialog
from frontend.components.buttons import PrimaryButton, OutlineButton


calendar.setfirstweekday(calendar.MONDAY)


def get_upcoming_sessions_for_class(schedule_repo, class_id: Optional[str], ref_date_str: str) -> List[dict]:
    """Retrieve existing or projected upcoming recurring sessions for an offline class."""
    if not class_id:
        return []

    try:
        ref_d = parse_date(ref_date_str)
    except Exception:
        ref_d = today_date()

    all_schs = [s for s in schedule_repo.get_by_class_id(class_id) if s.status.value != "CANCELLED"]
    sessions = []

    # 1. Existing schedules from repo
    for s in all_schs:
        sessions.append({
            "date": s.date,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "location": s.location or "Phòng học 1",
            "is_persisted": True,
        })

    # 2. Project recurring sessions for the next 8 weeks from known patterns
    patterns = set(
        (parse_date(s.date).weekday(), s.start_time, s.end_time, s.location or "Phòng học 1")
        for s in all_schs
    )
    # Default pattern if class has no schedule yet: Thursday 18:00-19:30
    if not patterns:
        patterns = {(3, "18:00", "19:30", "Phòng học 1")}

    for w_day, st, et, loc in patterns:
        for week_idx in range(9):
            diff = (w_day - ref_d.weekday()) % 7 + (week_idx * 7)
            proj_d = ref_d + timedelta(days=diff)
            iso_d = format_date_iso(proj_d)
            sessions.append({
                "date": iso_d,
                "start_time": st,
                "end_time": et,
                "location": loc,
                "is_persisted": False,
            })

    # Deduplicate by (date, start_time)
    seen = set()
    deduped = []
    for s in sorted(sessions, key=lambda x: (x["date"], x["start_time"])):
        key = (s["date"], s["start_time"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    # Filter to upcoming or current dates
    upcoming = [s for s in deduped if s["date"] >= ref_date_str or s["date"] >= today_str()]
    return upcoming if upcoming else deduped


from frontend.components.calendar_picker import CalendarPickerFrame



class RescheduleDialog(BaseModalDialog):
    """Modal dialog allowing teacher to reschedule offline lessons: select existing class or create a new one."""

    def __init__(
        self,
        parent,
        schedule_service: ScheduleService,
        student_service: StudentService,
        class_service: ClassService,
        schedule: ScheduleResponseDTO,
        student_id: Optional[str] = None,
        on_rescheduled: Optional[Callable[[dict], None]] = None,
    ):
        self.schedule_service = schedule_service
        self.student_service = student_service
        self.class_service = class_service
        self.schedule = schedule
        self.target_student_id = student_id or schedule.student_id
        self.on_rescheduled = on_rescheduled

        self.student = None
        if self.target_student_id:
            try:
                self.student = self.student_service.get_student_by_id(self.target_student_id)
            except Exception:
                pass

        self.student_name = self.student.name if self.student else (schedule.student_name or "Học sinh")
        class_title = schedule.class_name or schedule.lesson_title

        super().__init__(
            parent=parent,
            title=f"Đổi lịch học (Lớp Offline): {self.student_name}",
            subtitle=f"Buổi gốc: {schedule.date} ({schedule.start_time} - {schedule.end_time}) • {class_title}",
            width=580,
            height=680,
        )

        self._load_offline_classes()
        self._build_ui()

    def _load_offline_classes(self) -> None:
        # Load ALL offline classes
        self.offline_classes = self.class_service.get_classes(class_type=ClassType.OFFLINE)
        self.class_map: Dict[str, Optional[str]] = {}
        self.class_options: List[str] = []
        self.class_capacity_info: Dict[str, dict] = {}

        # Option: Keep current class
        if self.schedule.class_id:
            curr_name = self.schedule.class_name or "Lớp hiện tại"
            curr_opt = f"-- Giữ nguyên lớp ({curr_name}) --"
            self.class_map[curr_opt] = self.schedule.class_id
            self.class_options.append(curr_opt)
            self.class_capacity_info[curr_opt] = {"is_full": False, "text": f"Giữ nguyên lớp học hiện tại ({curr_name})"}

        # All offline classes: Available vs Full
        for c in self.offline_classes:
            is_full = c.current_student_count >= c.max_students
            rem = max(0, c.max_students - c.current_student_count)

            if is_full:
                # Lớp đã đủ số lượng học sinh -> Có màu khác / tag đỏ
                opt = f"🔴 [ĐÃ ĐỦ SĨ SỐ] {c.name} ({c.current_student_count}/{c.max_students})"
                self.class_capacity_info[opt] = {
                    "is_full": True,
                    "class_id": c.id,
                    "class_name": c.name,
                    "count": c.current_student_count,
                    "max": c.max_students,
                    "text": f"⛔ Lớp '{c.name}' đã ĐỦ sĩ số ({c.current_student_count}/{c.max_students}). Không thể chọn lớp này!",
                }
            else:
                opt = f"🟢 {c.name} (Còn {rem}/{c.max_students} chỗ)"
                self.class_capacity_info[opt] = {
                    "is_full": False,
                    "class_id": c.id,
                    "class_name": c.name,
                    "count": c.current_student_count,
                    "max": c.max_students,
                    "rem": rem,
                    "text": f"✓ Lớp '{c.name}' còn {rem} chỗ trống ({c.current_student_count}/{c.max_students}) - Có thể chuyển vào",
                }

            self.class_map[opt] = c.id
            self.class_options.append(opt)

        if not self.class_options:
            empty_opt = "-- Chưa có lớp offline nào --"
            self.class_map[empty_opt] = None
            self.class_options.append(empty_opt)

    def _build_ui(self) -> None:
        # Scrollable container for whole dialog content
        self.body_scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent", height=490)
        self.body_scroll.pack(fill="both", expand=True)

        # Mode Switcher: "Chuyển vào lớp có sẵn" VS "+ Tạo lớp mới (Chưa có sẵn)"
        self.mode_var = ctk.StringVar(value="EXISTING")
        self.seg_mode = ctk.CTkSegmentedButton(
            self.body_scroll,
            values=["Chuyển vào lớp có sẵn", "+ Tạo lớp mới (Chưa có)"],
            variable=self.mode_var,
            font=Theme.fonts.BODY_BOLD,
            height=34,
            selected_color=Theme.colors.EMERALD,
            selected_hover_color=Theme.colors.EMERALD_HOVER,
            command=self._on_mode_switched,
        )
        self.seg_mode.pack(fill="x", padx=4, pady=(2, 12))

        # Mode 1 Container: Existing Classes
        self.frame_existing = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        self.frame_existing.pack(fill="x", padx=4)
        self._build_existing_mode_ui()

        # Mode 2 Container: Create New Class
        self.frame_new_class = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        self._build_new_class_mode_ui()

        # Footer Area
        self.lbl_error = ctk.CTkLabel(
            self.footer,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.DANGER,
            wraplength=340,
            justify="left",
        )
        self.lbl_error.pack(side="left", padx=4)

        self.btn_cancel = OutlineButton(self.footer, text="Hủy", command=self.destroy, width=90)
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_confirm = PrimaryButton(self.footer, text="Xác nhận đổi lịch", command=self._confirm, width=160)
        self.btn_confirm.pack(side="right")

        # Initial selection
        self._on_class_selected(self.opt_class.get())

    def _build_existing_mode_ui(self) -> None:
        # 1. Class Selection
        ctk.CTkLabel(
            self.frame_existing,
            text="Chuyển qua lớp Offline nào? *",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(4, 2))

        self.opt_class = ctk.CTkOptionMenu(
            self.frame_existing,
            values=self.class_options,
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.BORDER_SUBTLE,
            text_color=Theme.colors.TEXT_PRIMARY,
            dropdown_text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_class_selected,
        )
        self.opt_class.pack(fill="x", pady=(0, 4))
        self.opt_class.set(self.class_options[0])

        # All Offline Classes Quick Badges (Màu xanh nếu còn chỗ, Màu đỏ nếu đã đủ số lượng)
        badges_container = ctk.CTkFrame(self.frame_existing, fg_color="transparent")
        badges_container.pack(fill="x", pady=(2, 6))

        for opt_key, info in self.class_capacity_info.items():
            if "-- Giữ nguyên lớp" in opt_key:
                continue
            is_full = info.get("is_full", False)
            c_name = info.get("class_name", opt_key)
            c_count = info.get("count", 0)
            c_max = info.get("max", 0)

            if is_full:
                b_text = f"🔴 {c_name} (ĐÃ ĐỦ: {c_count}/{c_max})"
                b_fg = "#FEF2F2"
                b_border = "#EF4444"
                b_tc = "#DC2626"
            else:
                rem = info.get("rem", 0)
                b_text = f"🟢 {c_name} (Còn {rem}/{c_max})"
                b_fg = "#ECFDF5"
                b_border = "#10B981"
                b_tc = "#065F46"

            badge_btn = ctk.CTkButton(
                badges_container,
                text=b_text,
                font=Theme.fonts.CAPTION_BOLD,
                height=26,
                fg_color=b_fg,
                border_color=b_border,
                border_width=1,
                text_color=b_tc,
                hover_color=b_fg,
                corner_radius=6,
                command=lambda k=opt_key: self._select_class_by_key(k),
            )
            badge_btn.pack(side="left", padx=(0, 6), pady=2)

        # Class Capacity Status Card (Màu khác hoàn toàn khi đủ học sinh)
        self.status_card = ctk.CTkFrame(self.frame_existing, corner_radius=8, border_width=1)
        self.status_card.pack(fill="x", pady=(2, 10))

        self.lbl_status_card = ctk.CTkLabel(
            self.status_card,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            wraplength=480,
            justify="left",
        )
        self.lbl_status_card.pack(anchor="w", padx=12, pady=8)

        # 2. Sổ cái lịch ngày học của lớp nớ xuống để chọn (Mặc định lớp gần nhất)
        ctk.CTkLabel(
            self.frame_existing,
            text="Lịch ngày học của lớp: *",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(4, 2))

        self.session_date_map: Dict[str, dict] = {}
        self.opt_session_date = ctk.CTkOptionMenu(
            self.frame_existing,
            values=["-- Đang tải lịch học --"],
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.BORDER_SUBTLE,
            text_color=Theme.colors.TEXT_PRIMARY,
            dropdown_text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_session_date_selected,
        )
        self.opt_session_date.pack(fill="x", pady=(0, 6))

        # 3. Khung giờ sẽ tự hiển thị theo khung giờ lớp đó
        ctk.CTkLabel(
            self.frame_existing,
            text="Khung giờ học (Tự động theo lớp):",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(4, 2))

        time_box = ctk.CTkFrame(self.frame_existing, fg_color=Theme.colors.BG_CARD, border_color=Theme.colors.BORDER_SUBTLE, border_width=1, corner_radius=8)
        time_box.pack(fill="x", pady=(0, 8))

        self.lbl_time_display = ctk.CTkLabel(
            time_box,
            text="⏰ 17:30 - 19:00",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        self.lbl_time_display.pack(anchor="w", padx=12, pady=8)


    def _build_new_class_mode_ui(self) -> None:
        # Trường 1: Tên lớp
        ctk.CTkLabel(
            self.frame_new_class,
            text="Tên lớp mới: *",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(4, 2))

        self.entry_new_name = ctk.CTkEntry(
            self.frame_new_class,
            placeholder_text="Ví dụ: Lớp Piano Nhí Cơ Bản K2",
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
        )
        self.entry_new_name.pack(fill="x", pady=(0, 8))

        # Trường 2: Ngày thứ học - Bảng chọn ngày (Calendar Picker)
        ctk.CTkLabel(
            self.frame_new_class,
            text="Ngày / thứ học: * (Chọn ngày trên bảng bên dưới)",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(4, 2))

        try:
            init_d = parse_date(self.schedule.date) + timedelta(days=7)
        except Exception:
            init_d = today_date() + timedelta(days=1)

        self.calendar_picker = CalendarPickerFrame(
            self.frame_new_class,
            initial_date=init_d,
            on_date_selected=self._on_new_date_selected,
        )

        # Trường 3: Giờ học (Tuyệt đối không trùng các lớp đã có sẵn)
        ctk.CTkLabel(
            self.frame_new_class,
            text="Giờ học: * (Tuyệt đối không trùng các lớp đã có sẵn)",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(6, 2))

        t_row = ctk.CTkFrame(self.frame_new_class, fg_color="transparent")
        t_row.pack(fill="x", pady=(0, 4))
        t_row.grid_columnconfigure(0, weight=1)
        t_row.grid_columnconfigure(2, weight=1)

        self.entry_new_start = ctk.CTkEntry(t_row, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_new_start.grid(row=0, column=0, sticky="ew")
        self.entry_new_start.insert(0, self.schedule.start_time)
        self.entry_new_start.bind("<KeyRelease>", lambda e: self._check_new_class_conflict())

        ctk.CTkLabel(t_row, text="  đến  ", font=Theme.fonts.BODY).grid(row=0, column=1)

        self.entry_new_end = ctk.CTkEntry(t_row, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT)
        self.entry_new_end.grid(row=0, column=2, sticky="ew")
        self.entry_new_end.insert(0, self.schedule.end_time)
        self.entry_new_end.bind("<KeyRelease>", lambda e: self._check_new_class_conflict())

        # Shortcut time slot buttons
        qtime_frame = ctk.CTkFrame(self.frame_new_class, fg_color="transparent")
        qtime_frame.pack(anchor="w", pady=(0, 6))

        slots = [
            ("08:30-09:30", "08:30", "09:30"),
            ("14:00-15:30", "14:00", "15:30"),
            ("17:30-19:00", "17:30", "19:00"),
            ("19:30-20:30", "19:30", "20:30"),
        ]
        for label, s_val, e_val in slots:
            ctk.CTkButton(
                qtime_frame,
                text=label,
                font=Theme.fonts.CAPTION,
                height=24,
                width=80,
                fg_color=Theme.colors.BG_MUTED,
                text_color=Theme.colors.TEXT_PRIMARY,
                hover_color=Theme.colors.BORDER_SUBTLE,
                command=lambda s=s_val, e=e_val: self._set_new_time_slot(s, e),
            ).pack(side="left", padx=(0, 4))

        # Real-time Conflict Feedback Banner
        self.lbl_conflict_feedback = ctk.CTkLabel(
            self.frame_new_class,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.EMERALD,
            wraplength=480,
            justify="left",
        )
        self.lbl_conflict_feedback.pack(anchor="w", pady=(2, 6))

    def _on_mode_switched(self, mode_str: str) -> None:
        self.lbl_error.configure(text="")
        if mode_str == "Chuyển vào lớp có sẵn":
            self.frame_new_class.pack_forget()
            self.frame_existing.pack(fill="x", padx=4)
            self.btn_confirm.configure(text="Xác nhận đổi lịch")
            self._on_class_selected(self.opt_class.get())
        else:
            self.frame_existing.pack_forget()
            self.frame_new_class.pack(fill="x", padx=4)
            self.btn_confirm.configure(text="Xác nhận tạo lớp & đổi lịch", state="normal", fg_color=Theme.colors.EMERALD)
            self._check_new_class_conflict()

    def _select_class_by_key(self, opt_key: str) -> None:
        self.opt_class.set(opt_key)
        self._on_class_selected(opt_key)

    def _on_class_selected(self, class_choice: str) -> None:
        self.lbl_error.configure(text="")
        info = self.class_capacity_info.get(class_choice, {})
        is_full = info.get("is_full", False)
        status_text = info.get("text", "")

        # 1. Update Class Status Card with distinct colors
        if is_full:
            # Màu đỏ khi lớp đã đủ học sinh
            self.status_card.configure(fg_color="#FEF2F2", border_color="#EF4444", border_width=2)
            self.lbl_status_card.configure(text=status_text, text_color="#DC2626")
            self.btn_confirm.configure(state="disabled", fg_color=Theme.colors.TEXT_MUTED)
            self.lbl_error.configure(text="Lớp này đã đủ số lượng học sinh. Vui lòng chọn lớp khác còn chỗ!")
        else:
            # Màu xanh khi lớp còn chỗ
            self.status_card.configure(fg_color="#ECFDF5", border_color="#10B981", border_width=1)
            self.lbl_status_card.configure(text=status_text, text_color="#065F46")
            self.btn_confirm.configure(state="normal", fg_color=Theme.colors.EMERALD)

        # 2. Sổ danh sách ngày học của lớp nớ xuống để chọn
        target_class_id = self.class_map.get(class_choice)
        sessions = get_upcoming_sessions_for_class(
            self.schedule_service.schedule_repo,
            target_class_id,
            self.schedule.date,
        )

        self.session_date_map.clear()
        date_options = []

        # Find nearest upcoming session relative to reschedule date
        nearest_session_label = None
        min_diff = 9999
        ref_d = parse_date(self.schedule.date)

        for s in sessions:
            try:
                s_d = parse_date(s["date"])
                w_vn = WEEKDAY_VN[s_d.weekday()]
                lbl = f"{w_vn}, {format_date_display(s_d)} ({s['start_time']} - {s['end_time']})"
                self.session_date_map[lbl] = s
                date_options.append(lbl)

                diff = (s_d - ref_d).days
                if 0 <= diff < min_diff:
                    min_diff = diff
                    nearest_session_label = lbl
            except Exception:
                pass

        if not date_options:
            fallback = f"Buổi tiếp theo ({self.schedule.date})"
            self.session_date_map[fallback] = {
                "date": self.schedule.date,
                "start_time": self.schedule.start_time,
                "end_time": self.schedule.end_time,
                "location": self.schedule.location or "Phòng học 1",
            }
            date_options.append(fallback)
            nearest_session_label = fallback

        self.opt_session_date.configure(values=date_options)
        # Mặc định để lớp gần nhất so với ngày đổi lịch học
        default_lbl = nearest_session_label or date_options[0]
        self.opt_session_date.set(default_lbl)
        self._on_session_date_selected(default_lbl)

    def _on_session_date_selected(self, session_lbl: str) -> None:
        session = self.session_date_map.get(session_lbl)
        if not session:
            return

        # Khung giờ sẽ tự hiển thị theo khung giờ lớp đó
        st = session["start_time"]
        et = session["end_time"]
        try:
            dur = time_to_minutes(et) - time_to_minutes(st)
        except Exception:
            dur = 60

        self.lbl_time_display.configure(text=f"⏰ {st}  đến  {et}  ({dur} phút)")

    def _on_new_date_selected(self, d: date) -> None:
        self._check_new_class_conflict()

    def _set_new_time_slot(self, s: str, e: str) -> None:
        self.entry_new_start.delete(0, "end")
        self.entry_new_start.insert(0, s)
        self.entry_new_end.delete(0, "end")
        self.entry_new_end.insert(0, e)
        self._check_new_class_conflict()

    def _check_new_class_conflict(self) -> None:
        """Check in real-time that new class time slot absolutely does not conflict with existing classes."""
        sel_date = self.calendar_picker.get_date()
        s_time = self.entry_new_start.get().strip()
        e_time = self.entry_new_end.get().strip()

        if len(s_time) != 5 or len(e_time) != 5 or s_time >= e_time:
            self.lbl_conflict_feedback.configure(
                text="⚠️ Giờ học không hợp lệ (HH:MM) hoặc giờ kết thúc trước giờ bắt đầu.",
                text_color=Theme.colors.WARNING,
            )
            return

        day_schs = self.schedule_service.schedule_repo.get_by_date_range(sel_date, sel_date)
        conflicts = []
        for existing in day_schs:
            if existing.status.value != "CANCELLED":
                try:
                    if is_time_overlap(s_time, e_time, existing.start_time, existing.end_time):
                        c_title = existing.lesson_title or existing.class_name or "Ca học khác"
                        conflicts.append(f"'{c_title}' ({existing.start_time}-{existing.end_time})")
                except Exception:
                    pass

        if conflicts:
            self.lbl_conflict_feedback.configure(
                text=f"❌ Trùng giờ với: {', '.join(conflicts)}! Vui lòng chọn giờ khác.",
                text_color=Theme.colors.DANGER,
            )
            self.btn_confirm.configure(state="disabled", fg_color=Theme.colors.TEXT_MUTED)
        else:
            self.lbl_conflict_feedback.configure(
                text="✓ Khung giờ học trống, tuyệt đối không bị trùng lớp nào.",
                text_color=Theme.colors.EMERALD,
            )
            self.btn_confirm.configure(state="normal", fg_color=Theme.colors.EMERALD)

    def _confirm(self) -> None:
        self.lbl_error.configure(text="")
        current_mode = self.mode_var.get()

        if current_mode == "Chuyển vào lớp có sẵn":
            self._confirm_existing_class()
        else:
            self._confirm_new_class()

    def _confirm_existing_class(self) -> None:
        class_choice = self.opt_class.get()
        info = self.class_capacity_info.get(class_choice, {})

        if info.get("is_full", False):
            self.lbl_error.configure(text="Lớp này đã đủ số lượng học sinh, không thể chuyển vào!")
            return

        target_class_id = self.class_map.get(class_choice)
        if not target_class_id:
            self.lbl_error.configure(text="Vui lòng chọn một lớp học offline hợp lệ.")
            return

        session_choice = self.opt_session_date.get()
        session = self.session_date_map.get(session_choice)
        if not session:
            self.lbl_error.configure(text="Vui lòng chọn một ngày học từ danh sách của lớp.")
            return

        target_date = session["date"]
        target_start = session["start_time"]
        target_end = session["end_time"]
        loc_val = session.get("location") or "Phòng học 1"

        if class_choice.startswith("-- Giữ nguyên lớp"):
            target_class_name = self.schedule.class_name or "Lớp gốc"
        else:
            target_class_name = info.get("class_name") or class_choice.split(" (")[0].replace("🟢 ", "").replace("🔴 ", "").strip()

        # Conflict verification for student
        if self.target_student_id:
            try:
                self.schedule_service.check_conflicts(
                    target_date=target_date,
                    start_time=target_start,
                    end_time=target_end,
                    student_id=self.target_student_id,
                    class_id=None,
                    ignore_schedule_id=self.schedule.id,
                )
            except Exception as e:
                self.lbl_error.configure(text=str(e))
                return

        reschedule_data = {
            "student_id": self.target_student_id,
            "student_name": self.student_name,
            "target_class_id": target_class_id,
            "target_class_name": target_class_name,
            "date": target_date,
            "start_time": target_start,
            "end_time": target_end,
            "location": loc_val,
            "online_url": None,
            "note": f"Đổi sang lớp {target_class_name}",
            "lesson_title": f"[Học bù] {self.student_name} - {target_class_name}" if self.target_student_id else f"[Đổi lịch] {target_class_name}",
        }

        if self.on_rescheduled:
            self.on_rescheduled(reschedule_data)
            self.destroy()
            return

        # Direct creation if standalone
        try:
            dto = ScheduleCreateDTO(
                class_id=target_class_id,
                student_id=None,
                date=target_date,
                start_time=target_start,
                end_time=target_end,
                location=loc_val,
                online_url=None,
                lesson_title=reschedule_data["lesson_title"],
                original_schedule_id=self.schedule.id,
            )
            created_sch = self.schedule_service.create_schedule(dto)
            orig_m = self.schedule_service.schedule_repo.get_by_id(self.schedule.id)
            if orig_m:
                orig_m.status = ScheduleStatus.RESCHEDULED
                orig_m.rescheduled_to_id = created_sch.id
                self.schedule_service.schedule_repo.update(orig_m)
            self.destroy()
        except Exception as e:
            self.lbl_error.configure(text=str(e))

    def _confirm_new_class(self) -> None:
        new_name = self.entry_new_name.get().strip()
        if not new_name:
            self.lbl_error.configure(text="Vui lòng nhập tên cho lớp học mới.")
            return

        target_date = self.calendar_picker.get_date()
        target_start = self.entry_new_start.get().strip()
        target_end = self.entry_new_end.get().strip()

        if len(target_start) != 5 or len(target_end) != 5 or target_start >= target_end:
            self.lbl_error.configure(text="Giờ học không hợp lệ (HH:MM).")
            return

        # Tuyệt đối không trùng các lớp đã có sẵn
        day_schs = self.schedule_service.schedule_repo.get_by_date_range(target_date, target_date)
        for existing in day_schs:
            if existing.status.value != "CANCELLED":
                try:
                    if is_time_overlap(target_start, target_end, existing.start_time, existing.end_time):
                        c_title = existing.lesson_title or existing.class_name or "lớp khác"
                        self.lbl_error.configure(
                            text=f"❌ Trùng lịch: Khung giờ {target_start}-{target_end} ngày {target_date} đã có lớp '{c_title}' ({existing.start_time}-{existing.end_time})!"
                        )
                        return
                except Exception:
                    pass

        # 1. Create the new offline class entity
        try:
            dto_c = ClassCreateDTO(name=new_name, class_type=ClassType.OFFLINE, max_students=6)
            created_class = self.class_service.create_class(dto_c)
        except Exception as e:
            self.lbl_error.configure(text=f"Không thể tạo lớp mới: {str(e)}")
            return

        # 2. Assign student to new class if individual student
        if self.target_student_id:
            try:
                c_model = self.class_service.class_repo.get_by_id(created_class.id)
                if c_model and self.target_student_id not in c_model.student_ids:
                    c_model.student_ids.append(self.target_student_id)
                    self.class_service.class_repo.update(c_model)
            except Exception:
                pass

        # 3. Create schedule for the new class on calendar
        lesson_title = f"[Học bù] {self.student_name} - {new_name}" if self.target_student_id else f"{new_name}"
        try:
            dto_sch = ScheduleCreateDTO(
                class_id=created_class.id,
                student_id=None,
                date=target_date,
                start_time=target_start,
                end_time=target_end,
                location="Phòng học 1",
                online_url=None,
                lesson_title=lesson_title,
                original_schedule_id=self.schedule.id,
            )
            created_sch = self.schedule_service.create_schedule(dto_sch)
            if not self.on_rescheduled:
                orig_m = self.schedule_service.schedule_repo.get_by_id(self.schedule.id)
                if orig_m:
                    orig_m.status = ScheduleStatus.RESCHEDULED
                    orig_m.rescheduled_to_id = created_sch.id
                    self.schedule_service.schedule_repo.update(orig_m)
        except Exception as e:
            self.lbl_error.configure(text=f"Không thể tạo lịch học: {str(e)}")
            return

        reschedule_data = {
            "student_id": self.target_student_id,
            "student_name": self.student_name,
            "target_class_id": created_class.id,
            "target_class_name": new_name,
            "date": target_date,
            "start_time": target_start,
            "end_time": target_end,
            "location": "Phòng học 1",
            "online_url": None,
            "note": f"Đổi sang lớp mới: {new_name}",
            "lesson_title": lesson_title,
        }

        if self.on_rescheduled:
            self.on_rescheduled(reschedule_data)

        self.destroy()
