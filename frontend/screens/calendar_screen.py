"""Weekly Calendar Screen with time-grid, floating event cards, and quick reminder sidebar."""

from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, List, Optional
import webbrowser
import customtkinter as ctk

from frontend.theme import Theme
from backend.core.enums import ClassType, ReminderSeverity, AttendanceStatus, ScheduleStatus
from backend.core.dates import today_date, get_week_days, format_date_display, get_day_of_week_label, format_date_iso
from backend.core.event_bus import event_bus
from backend.application.services.schedule_service import ScheduleService
from backend.application.services.reminder_service import ReminderService
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.services.attendance_service import AttendanceService
from backend.application.services.payment_service import PaymentService
from backend.application.services.holiday_service import HolidayService
from backend.application.dto.schedule_dto import ScheduleResponseDTO
from frontend.components.cards import GlassCard
from frontend.components.buttons import PrimaryButton, OutlineButton, IconButton
from frontend.components.icon_loader import IconLoader
from frontend.components.dialogs import ConfirmDialog, BaseModalDialog
from frontend.dialogs.schedule_dialog import ScheduleDialog
from frontend.dialogs.attendance_dialog import AttendanceDialog
from frontend.dialogs.payment_dialog import PaymentDialog
from frontend.dialogs.holiday_dialog import HolidayDialog
from frontend.components.toast import ToastManager


CLASS_PALETTES = [
    {
        "bg": "#ECFDF5",        # Mint / Emerald
        "border": "#10B981",
        "hover": "#059669",
        "tag_bg": "#D1FAE5",
        "tag_text": "#047857",
    },
    {
        "bg": "#EFF6FF",        # Sky Blue
        "border": "#3B82F6",
        "hover": "#2563EB",
        "tag_bg": "#DBEAFE",
        "tag_text": "#1D4ED8",
    },
    {
        "bg": "#F5F3FF",        # Violet Lavender
        "border": "#8B5CF6",
        "hover": "#7C3AED",
        "tag_bg": "#EDE9FE",
        "tag_text": "#6D28D9",
    },
    {
        "bg": "#FFFBEB",        # Amber Gold
        "border": "#F59E0B",
        "hover": "#D97706",
        "tag_bg": "#FEF3C7",
        "tag_text": "#B45309",
    },
    {
        "bg": "#FFF1F2",        # Rose Coral
        "border": "#F43F5E",
        "hover": "#E11D48",
        "tag_bg": "#FFE4E6",
        "tag_text": "#BE123C",
    },
    {
        "bg": "#F0FDFA",        # Teal Aqua
        "border": "#14B8A6",
        "hover": "#0D9488",
        "tag_bg": "#CCFBF1",
        "tag_text": "#0F766E",
    },
    {
        "bg": "#EEF2FF",        # Indigo
        "border": "#6366F1",
        "hover": "#4F46E5",
        "tag_bg": "#E0E7FF",
        "tag_text": "#4338CA",
    },
    {
        "bg": "#FFF7ED",        # Warm Orange
        "border": "#EA580C",
        "hover": "#C2410C",
        "tag_bg": "#FFEDD5",
        "tag_text": "#9A3412",
    },
    {
        "bg": "#FDF4FF",        # Fuchsia
        "border": "#D946EF",
        "hover": "#C026D3",
        "tag_bg": "#FAE8FF",
        "tag_text": "#A21CAF",
    },
    {
        "bg": "#ECFEFF",        # Cyan
        "border": "#0891B2",
        "hover": "#0E7490",
        "tag_bg": "#CFFAFE",
        "tag_text": "#155E75",
    },
]


def get_class_palette(event: ScheduleResponseDTO) -> dict:
    """Return distinct color palette based on unique class or student."""
    key = event.class_id or event.student_id or event.class_name or event.lesson_title or event.id
    h = 0
    for ch in key:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return CLASS_PALETTES[h % len(CLASS_PALETTES)]


class SingleSessionOptionsDialog(BaseModalDialog):
    """Action modal when clicking on a 1-on-1 or online lesson card."""

    def __init__(
        self,
        parent,
        event: ScheduleResponseDTO,
        is_present: bool,
        on_mark_present: Callable,
        on_mark_absent: Callable,
    ):
        self.event = event
        self.is_present = is_present
        self.on_mark_present = on_mark_present
        self.on_mark_absent = on_mark_absent

        title_name = event.student_name or event.lesson_title
        super().__init__(
            parent=parent,
            title=f"Điểm danh: {title_name}",
            subtitle=f"{event.date} ({event.start_time} - {event.end_time}) • {event.location or 'Online'}",
            width=420,
            height=280,
        )
        self._build_content()

    def _build_content(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)

        status_text = "Đã điểm danh CÓ MẶT" if self.is_present else "Chưa điểm danh"
        status_color = Theme.colors.EMERALD if self.is_present else Theme.colors.TEXT_SECONDARY

        lbl_st = ctk.CTkLabel(
            self.body,
            text=f"Trạng thái: {status_text}",
            font=Theme.fonts.BODY_BOLD,
            text_color=status_color,
        )
        lbl_st.pack(pady=(6, 16))

        # 1. Option: Mark Present (if not present)
        if not self.is_present:
            btn_present = PrimaryButton(
                self.body,
                text="✓ Điểm danh Có mặt (-1 buổi)",
                command=self._do_present,
                height=38,
            )
            btn_present.pack(fill="x", pady=4)

        # 2. Option: Mark Absent
        btn_absent = OutlineButton(
            self.body,
            text="✕ Đánh dấu Vắng mặt (Hoàn lại 1 buổi)" if self.is_present else "✕ Đánh dấu Vắng mặt",
            command=self._do_absent,
            height=36,
        )
        btn_absent.pack(fill="x", pady=4)

        # Cancel button in footer
        btn_close = OutlineButton(self.footer, text="Đóng", command=self.destroy, width=90)
        btn_close.pack(side="right")

    def _do_present(self) -> None:
        self.destroy()
        self.on_mark_present()

    def _do_absent(self) -> None:
        self.destroy()
        self.on_mark_absent()


class CalendarScreen(ctk.CTkFrame):
    """Weekly calendar screen with 7-day columns and instant reminder feed."""

    def __init__(
        self,
        master,
        schedule_service: ScheduleService,
        reminder_service: ReminderService,
        student_service: StudentService,
        class_service: ClassService,
        attendance_service: AttendanceService,
        payment_service: PaymentService,
        holiday_service: Optional[HolidayService] = None,
        **kwargs,
    ):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self.schedule_service = schedule_service
        self.reminder_service = reminder_service
        self.student_service = student_service
        self.class_service = class_service
        self.attendance_service = attendance_service
        self.payment_service = payment_service
        self.holiday_service = holiday_service

        self.current_week_date: date = today_date()
        self._refresh_timer: Optional[str] = None
        self._dirty: bool = False
        self._last_rem_sig: Optional[str] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)  # Right sidebar fixed width

        self._build_header()
        self._build_calendar_area()
        self._build_reminder_sidebar()

        # Listen to event bus for auto-refresh
        event_bus.subscribe("schedules_changed", self._on_data_invalidated)
        event_bus.subscribe("attendance_changed", self._on_data_invalidated)
        event_bus.subscribe("payments_changed", self._on_data_invalidated)
        event_bus.subscribe("students_changed", self._on_data_invalidated)
        event_bus.subscribe("holidays_changed", self._on_data_invalidated)

        self.refresh()

    def _on_data_invalidated(self, _=None) -> None:
        if not self.winfo_exists():
            return
        if not self.winfo_viewable():
            self._dirty = True
            return
        self._request_refresh()

    def _request_refresh(self) -> None:
        if self._refresh_timer is not None:
            try:
                self.after_cancel(self._refresh_timer)
            except Exception:
                pass
        self._refresh_timer = self.after(25, self._do_debounced_refresh)

    def _do_debounced_refresh(self) -> None:
        self._refresh_timer = None
        self._dirty = False
        self.refresh()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=42)
        header.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=(0, 12))

        # Nav Buttons (Prev, Today, Next)
        nav_box = ctk.CTkFrame(header, fg_color="transparent")
        nav_box.pack(side="left")

        arrow_l = IconLoader.get_icon("arrow_left", size=16, color=Theme.colors.TEXT_PRIMARY)
        arrow_r = IconLoader.get_icon("arrow_right", size=16, color=Theme.colors.TEXT_PRIMARY)

        btn_prev = IconButton(nav_box, icon=arrow_l, command=self._prev_week, size=36)
        btn_prev.pack(side="left", padx=(0, 6))

        btn_today = OutlineButton(nav_box, text="Hôm nay", command=self._go_today, width=80, height=36)
        btn_today.pack(side="left", padx=(0, 6))

        btn_next = IconButton(nav_box, icon=arrow_r, command=self._next_week, size=36)
        btn_next.pack(side="left")

        # Current Week Label (Positioned dead center of the entire row)
        self.lbl_week_range = ctk.CTkLabel(
            header,
            text="",
            font=Theme.fonts.H1,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="center",
        )
        self.lbl_week_range.place(relx=0.5, rely=0.5, anchor="center")

    def _build_calendar_area(self) -> None:
        # Outer Card
        self.cal_card = GlassCard(self)
        self.cal_card.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        self.cal_card.grid_rowconfigure(0, weight=1)
        self.cal_card.grid_columnconfigure(0, weight=1)

        # Scrollable 7-day columns container
        self.cal_scroll = ctk.CTkScrollableFrame(self.cal_card, fg_color="transparent")
        self.cal_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        # Pre-build persistent 7 day columns to avoid tearing/reloading whole UI
        self.day_columns: List[ctk.CTkFrame] = []
        self.day_headers: List[ctk.CTkFrame] = []
        self.day_header_labels: List[ctk.CTkLabel] = []
        self.day_cards_containers: List[ctk.CTkFrame] = []

        for col_idx in range(7):
            self.cal_scroll.grid_columnconfigure(col_idx, weight=1, uniform="cal_col")

            day_column = ctk.CTkFrame(
                self.cal_scroll,
                fg_color="#FAFAFA",
                border_color=Theme.colors.BORDER_SUBTLE,
                border_width=1,
                corner_radius=10,
            )
            day_column.grid(row=0, column=col_idx, sticky="nsew", padx=3, pady=2)
            day_column.grid_columnconfigure(0, weight=1)

            head_cell = ctk.CTkFrame(
                day_column,
                fg_color=Theme.colors.BG_MUTED,
                corner_radius=8,
                height=42,
            )
            head_cell.pack(fill="x", padx=4, pady=(4, 6))

            lbl_head = ctk.CTkLabel(
                head_cell,
                text="",
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.TEXT_PRIMARY,
            )
            lbl_head.place(relx=0.5, rely=0.5, anchor="center")

            cards_container = ctk.CTkFrame(day_column, fg_color="transparent")
            cards_container.pack(fill="both", expand=True)

            self.day_columns.append(day_column)
            self.day_headers.append(head_cell)
            self.day_header_labels.append(lbl_head)
            self.day_cards_containers.append(cards_container)

    def _build_reminder_sidebar(self) -> None:
        # Right reminder panel
        self.reminder_card = GlassCard(self, width=285)
        self.reminder_card.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        self.reminder_card.grid_propagate(False)
        self.reminder_card.grid_rowconfigure(2, weight=1)
        self.reminder_card.grid_columnconfigure(0, weight=1)

        # Nút Đặt lịch nghỉ ngay trên chữ NHẮC NHỞ NHANH
        self.btn_holiday = ctk.CTkButton(
            self.reminder_card,
            text="🏖️ Đặt lịch nghỉ dạy",
            font=Theme.fonts.CAPTION_BOLD,
            height=34,
            fg_color=Theme.colors.EMERALD,
            hover_color=Theme.colors.EMERALD_HOVER,
            corner_radius=Theme.radius.BUTTON,
            command=self._open_holiday_dialog,
        )
        self.btn_holiday.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))

        # Header NHẮC NHỞ NHANH
        r_head = ctk.CTkFrame(self.reminder_card, fg_color="transparent")
        r_head.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 6))

        warn_icon = IconLoader.get_icon("warning", size=20, color=Theme.colors.WARNING)
        lbl_wicon = ctk.CTkLabel(r_head, text="", image=warn_icon)
        lbl_wicon.pack(side="left", padx=(0, 8))

        lbl_rtitle = ctk.CTkLabel(
            r_head,
            text="NHẮC NHỞ NHANH",
            font=Theme.fonts.H2,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        lbl_rtitle.pack(side="left")

        # Reminder scrollable list
        self.reminder_scroll = ctk.CTkScrollableFrame(self.reminder_card, fg_color="transparent")
        self.reminder_scroll.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 12))

    def _prev_week(self) -> None:
        self.current_week_date -= timedelta(days=7)
        self.refresh()

    def _next_week(self) -> None:
        self.current_week_date += timedelta(days=7)
        self.refresh()

    def _go_today(self) -> None:
        self.current_week_date = today_date()
        self.refresh()

    def refresh(self) -> None:
        """Reload weekly schedules and active reminders."""
        if not self.winfo_exists():
            return
        week_days = get_week_days(self.current_week_date)
        start_str = format_date_display(week_days[0])
        end_str = format_date_display(week_days[-1])
        new_range_text = f"Tuần: {start_str} - {end_str}"
        if self.lbl_week_range.cget("text") != new_range_text:
            self.lbl_week_range.configure(text=new_range_text)

        self._render_week_grid(week_days)
        self._render_reminders()

    def _render_week_grid(self, week_days: List[date]) -> None:
        schedules = self.schedule_service.get_week_schedules(self.current_week_date)
        schedules_by_date: Dict[str, List[ScheduleResponseDTO]] = {}
        for s in schedules:
            schedules_by_date.setdefault(s.date, []).append(s)

        # Batch load attendances and classes map once for ultra-fast card rendering
        all_attendances = self.attendance_service.attendance_repo.get_all()
        attendances_by_sch: Dict[str, list] = {}
        for a in all_attendances:
            attendances_by_sch.setdefault(a.schedule_id, []).append(a)

        classes_map = {c.id: c for c in self.class_service.get_classes()}

        today_s = format_date_iso(today_date())

        for col_idx, d in enumerate(week_days):
            d_str = format_date_iso(d)
            is_today = (d_str == today_s)
            day_name = get_day_of_week_label(d, lang="en")
            day_str = d.strftime("%d/%m")

            holiday_for_day = self.holiday_service.is_date_holiday(d_str) if self.holiday_service else None
            is_holiday = holiday_for_day is not None

            col_bg = "#FEF2F2" if is_holiday else ("#F0FDF4" if is_today else "#FAFAFA")
            col_border = "#EF4444" if is_holiday else (Theme.colors.EMERALD_BORDER if is_today else Theme.colors.BORDER_SUBTLE)
            col_bw = 1.5 if (is_today or is_holiday) else 1

            head_bg = "#FEE2E2" if is_holiday else (Theme.colors.EMERALD_LIGHT if is_today else Theme.colors.BG_MUTED)
            head_text_color = "#DC2626" if is_holiday else (Theme.colors.EMERALD if is_today else Theme.colors.TEXT_PRIMARY)
            lbl_txt = f"{day_name}  {day_str}" + ("  🏖️ NGHỈ" if is_holiday else "")

            day_column = self.day_columns[col_idx]
            head_cell = self.day_headers[col_idx]
            lbl_head = self.day_header_labels[col_idx]
            cards_container = self.day_cards_containers[col_idx]

            day_column.configure(fg_color=col_bg, border_color=col_border, border_width=col_bw)
            head_cell.configure(fg_color=head_bg)
            lbl_head.configure(
                text=lbl_txt,
                text_color=head_text_color,
                font=Theme.fonts.BODY_BOLD if (is_today or is_holiday) else Theme.fonts.CAPTION_BOLD,
            )

            # Clear ONLY event cards in this column container
            for w in cards_container.winfo_children():
                w.destroy()

            # Events in day
            if is_holiday:
                holiday_card = ctk.CTkFrame(
                    cards_container,
                    fg_color="#FEE2E2",
                    border_color="#EF4444",
                    border_width=1.5,
                    corner_radius=10,
                    cursor="hand2",
                )
                holiday_card.pack(fill="x", padx=6, pady=12)
                holiday_card.bind("<Button-1>", lambda e: self._open_holiday_dialog(initial_tab="list"))

                lbl_h_title = ctk.CTkLabel(
                    holiday_card,
                    text="🏖️ NGHỈ HỌC",
                    font=Theme.fonts.H2,
                    text_color="#DC2626",
                    cursor="hand2",
                )
                lbl_h_title.pack(pady=(16, 2))
                lbl_h_title.bind("<Button-1>", lambda e: self._open_holiday_dialog(initial_tab="list"))

                time_note = "Cả ngày" if holiday_for_day.is_all_day else f"Từ {holiday_for_day.start_time} đến {holiday_for_day.end_time}"
                lbl_h_time = ctk.CTkLabel(
                    holiday_card,
                    text=f"({time_note})",
                    font=Theme.fonts.CAPTION_BOLD,
                    text_color="#B91C1C",
                    cursor="hand2",
                )
                lbl_h_time.pack(pady=(0, 4))
                lbl_h_time.bind("<Button-1>", lambda e: self._open_holiday_dialog(initial_tab="list"))

                lbl_h_sub = ctk.CTkLabel(
                    holiday_card,
                    text="Tất cả ca dạy tạm ngưng",
                    font=Theme.fonts.CAPTION,
                    text_color=Theme.colors.TEXT_MUTED,
                    cursor="hand2",
                )
                lbl_h_sub.pack(pady=(0, 16))
                lbl_h_sub.bind("<Button-1>", lambda e: self._open_holiday_dialog(initial_tab="list"))
            else:
                day_events = sorted(schedules_by_date.get(d_str, []), key=lambda s: s.start_time)
                if not day_events:
                    lbl_empty = ctk.CTkLabel(
                        cards_container,
                        text="Trống lịch",
                        font=Theme.fonts.CAPTION,
                        text_color=Theme.colors.TEXT_MUTED,
                    )
                    lbl_empty.pack(pady=24)
                else:
                    for event in day_events:
                        event_atts = attendances_by_sch.get(event.id, [])
                        self._create_event_card(cards_container, event, event_atts, classes_map)

    def _create_event_card(
        self,
        parent: ctk.CTkFrame,
        event: ScheduleResponseDTO,
        attendances: Optional[List[Any]] = None,
        classes_map: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Determine background and accent colors based on unique class identity
        palette = get_class_palette(event)
        bg_card = palette["bg"]
        border_c = palette["border"]
        hover_c = palette["hover"]
        tag_bg = palette["tag_bg"]
        tag_col = palette["tag_text"]

        is_rescheduled = bool(getattr(event, "original_schedule_id", None))

        if event.status == ScheduleStatus.HOLIDAY:
            bg_card = "#FFFBEB"
            border_c = "#F59E0B"
            hover_c = "#FDE68A"
            tag_bg = "#FEF3C7"
            tag_col = "#B45309"
            tag_text = "🏖️ NGHỈ HỌC"
        elif event.class_type == ClassType.ONE_ON_ONE:
            tag_text = "1 KÈM 1" + (" • ĐỔI LỊCH" if is_rescheduled else "")
        elif event.class_type == ClassType.ONLINE:
            tag_text = "ONLINE" + (" • ĐỔI LỊCH" if is_rescheduled else "")
        else:
            tag_text = "OFFLINE" + (" • ĐỔI LỊCH" if is_rescheduled else "")

        card = ctk.CTkFrame(
            parent,
            fg_color=bg_card,
            border_color=border_c,
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="x", padx=4, pady=4)

        # 1. Time (Dedicated line) & Quick Delete Button for rescheduled session
        time_row = ctk.CTkFrame(card, fg_color="transparent")
        time_row.pack(fill="x", padx=8, pady=(8, 2))

        time_str = f"{event.start_time} - {event.end_time}"
        lbl_time = ctk.CTkLabel(
            time_row,
            text=time_str,
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_time.pack(side="left")

        if is_rescheduled:
            btn_del_card = ctk.CTkButton(
                time_row,
                text="🗑️",
                width=24,
                height=20,
                font=("Segoe UI", 11),
                fg_color="transparent",
                hover_color="#FEE2E2",
                text_color=Theme.colors.DANGER,
                corner_radius=4,
                command=lambda ev=event: self._confirm_delete_rescheduled(ev),
            )
            btn_del_card.pack(side="right")

        # 2. Tag badge pill (1 KÈM 1 / ONLINE / OFFLINE)
        tag_frame = ctk.CTkFrame(
            card,
            fg_color=tag_bg,
            border_color=border_c,
            border_width=1,
            corner_radius=4,
            height=20,
        )
        tag_frame.pack(anchor="w", padx=8, pady=(0, 4))
        lbl_tag = ctk.CTkLabel(
            tag_frame,
            text=f" {tag_text} ",
            font=("Segoe UI", 9, "bold"),
            text_color=tag_col,
            height=18,
        )
        lbl_tag.pack(padx=3, pady=0)

        # 3. Lesson title / Student or Class Name
        display_name = event.student_name or event.class_name or event.lesson_title
        lbl_name = ctk.CTkLabel(
            card,
            text=display_name,
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
            wraplength=95,
            justify="left",
        )
        lbl_name.pack(anchor="w", padx=8, pady=(0, 3), fill="x")

        # 4. Location or Online Link
        # RULE: Phần học online và 1 kèm 1 thì không cần hiển thị địa chỉ với google meet
        is_online_or_1on1 = (event.class_type in (ClassType.ONE_ON_ONE, ClassType.ONLINE)) or (event.student_id is not None and event.class_type != ClassType.OFFLINE)
        lbl_loc = None
        if not is_online_or_1on1:
            if event.online_url:
                raw_url = event.online_url.strip()
                if "meet.google" in raw_url.lower():
                    loc_text = "🌐 Google Meet"
                elif "zoom.us" in raw_url.lower():
                    loc_text = "🌐 Zoom Meeting"
                elif "teams" in raw_url.lower():
                    loc_text = "🌐 MS Teams"
                else:
                    loc_text = "🌐 Học Online"

                lbl_loc = ctk.CTkLabel(
                    card,
                    text=loc_text,
                    font=Theme.fonts.CAPTION_BOLD,
                    text_color=tag_col,
                    anchor="w",
                    wraplength=95,
                    justify="left",
                    cursor="hand2",
                )
                lbl_loc.pack(anchor="w", padx=8, pady=(0, 6), fill="x")

                def _open_url(url=raw_url):
                    try:
                        webbrowser.open(url)
                    except Exception:
                        pass

                lbl_loc.bind("<Button-1>", lambda e, u=raw_url: _open_url(u))
            else:
                loc_val = event.location or "Phòng học 1"
                lbl_loc = ctk.CTkLabel(
                    card,
                    text=f"📍 {loc_val}",
                    font=Theme.fonts.CAPTION,
                    text_color=Theme.colors.TEXT_SECONDARY,
                    anchor="w",
                    wraplength=95,
                    justify="left",
                )
                lbl_loc.pack(anchor="w", padx=8, pady=(0, 6), fill="x")

        # 5. Dynamic wraplength based on card width
        def _on_card_configure(e, n_lbl=lbl_name, l_lbl=lbl_loc):
            w = e.width - 18
            if w > 60:
                n_lbl.configure(wraplength=w)
                if l_lbl is not None:
                    l_lbl.configure(wraplength=w)

        card.bind("<Configure>", _on_card_configure)

        # Cursor pointer for card
        card.configure(cursor="hand2")
        time_row.configure(cursor="hand2")
        lbl_time.configure(cursor="hand2")
        lbl_name.configure(cursor="hand2")
        tag_frame.configure(cursor="hand2")
        lbl_tag.configure(cursor="hand2")

        # Click on card body to open options / reschedule
        card.bind("<Button-1>", lambda e, ev=event: self._on_card_clicked(ev))
        time_row.bind("<Button-1>", lambda e, ev=event: self._on_card_clicked(ev))
        lbl_time.bind("<Button-1>", lambda e, ev=event: self._on_card_clicked(ev))
        lbl_name.bind("<Button-1>", lambda e, ev=event: self._on_card_clicked(ev))
        tag_frame.bind("<Button-1>", lambda e, ev=event: self._on_card_clicked(ev))
        lbl_tag.bind("<Button-1>", lambda e, ev=event: self._on_card_clicked(ev))
        if lbl_loc is not None and not event.online_url:
            lbl_loc.configure(cursor="hand2")
            lbl_loc.bind("<Button-1>", lambda e, ev=event: self._on_card_clicked(ev))

        # Right-click on card body to also open options / reschedule
        card.bind("<Button-3>", lambda e, ev=event: self._on_card_clicked(ev))
        time_row.bind("<Button-3>", lambda e, ev=event: self._on_card_clicked(ev))
        lbl_time.bind("<Button-3>", lambda e, ev=event: self._on_card_clicked(ev))
        lbl_name.bind("<Button-3>", lambda e, ev=event: self._on_card_clicked(ev))

        # 6. Action Button: Attendance Logic
        if event.status == ScheduleStatus.HOLIDAY:
            btn_att = ctk.CTkButton(
                card,
                text="🏖️ Nghỉ học",
                font=Theme.fonts.CAPTION_BOLD,
                height=28,
                fg_color="#F59E0B",
                hover_color="#D97706",
                text_color=Theme.colors.TEXT_WHITE,
                corner_radius=6,
                command=lambda ev=event: ToastManager.show(self.winfo_toplevel(), f"Ca học '{ev.lesson_title}' tạm nghỉ do ngày nghỉ của giáo viên.", level="info"),
            )
            btn_att.pack(fill="x", padx=8, pady=(2, 8))
            return

        if attendances is None:
            attendances = self.attendance_service.get_attendance_for_schedule(event.id)
        if classes_map is None:
            classes_map = {c.id: c for c in self.class_service.get_classes()}

        is_1on1_or_online = (event.class_type in (ClassType.ONE_ON_ONE, ClassType.ONLINE)) or bool(event.student_id)

        if is_1on1_or_online:
            # 1 kèm 1 và online: Bấm điểm danh sẽ mở hộp thoại điểm danh, nút luôn có chữ "Điểm danh"
            is_present = any(a.status == AttendanceStatus.PRESENT for a in attendances)
            is_rescheduled = any(a.status == AttendanceStatus.RESCHEDULED for a in attendances)
            is_absent = any(a.status == AttendanceStatus.ABSENT for a in attendances)

            if is_present:
                btn_bg = Theme.colors.EMERALD
                btn_hover = Theme.colors.EMERALD_HOVER
            elif is_rescheduled:
                btn_bg = Theme.colors.PURPLE
                btn_hover = Theme.colors.PURPLE_HOVER
            elif is_absent:
                btn_bg = Theme.colors.WARNING
                btn_hover = "#D97706"
            else:
                btn_bg = border_c
                btn_hover = hover_c

            btn_att = ctk.CTkButton(
                card,
                text="Điểm danh",
                font=Theme.fonts.CAPTION_BOLD,
                height=28,
                fg_color=btn_bg,
                hover_color=btn_hover,
                text_color=Theme.colors.TEXT_WHITE,
                corner_radius=6,
                command=lambda ev=event: self._open_single_attendance(ev),
            )
        else:
            # Lớp offline: Nhấn điểm danh sẽ hiện ra danh sách học sinh để điểm danh
            total_students = 0
            if event.class_id:
                c_info = classes_map.get(event.class_id)
                if c_info:
                    total_students = len(c_info.student_ids)

            present_count = len([a for a in attendances if a.status == AttendanceStatus.PRESENT])
            resched_count = len([a for a in attendances if a.status == AttendanceStatus.RESCHEDULED])
            recorded_count = len(attendances)

            if total_students > 0 and recorded_count >= total_students:
                if resched_count == total_students:
                    btn_text = f"🔄 Đổi lịch cả lớp ({total_students})"
                    btn_bg = Theme.colors.PURPLE
                    btn_hover = Theme.colors.PURPLE_HOVER
                else:
                    btn_text = f"✓ Đã điểm danh ({present_count}/{total_students})"
                    btn_bg = Theme.colors.EMERALD
                    btn_hover = Theme.colors.EMERALD_HOVER
            else:
                btn_text = f"Điểm danh ({present_count}/{total_students})" if total_students > 0 else "Điểm danh"
                btn_bg = border_c
                btn_hover = hover_c

            btn_att = ctk.CTkButton(
                card,
                text=btn_text,
                font=Theme.fonts.CAPTION_BOLD,
                height=28,
                fg_color=btn_bg,
                hover_color=btn_hover,
                text_color=Theme.colors.TEXT_WHITE,
                corner_radius=6,
                command=lambda ev=event: self._open_offline_attendance(ev),
            )

        btn_att.pack(fill="x", padx=8, pady=(2, 8))

    def _render_reminders(self) -> None:
        reminders = self.reminder_service.get_all_reminders()

        # Signature check to prevent clearing and rebuilding sidebar if nothing changed
        rem_sig = "|".join(f"{r.title}_{r.message}_{r.severity.value}" for r in reminders)
        if getattr(self, "_last_rem_sig", None) == rem_sig:
            return
        self._last_rem_sig = rem_sig

        for w in self.reminder_scroll.winfo_children():
            w.destroy()

        if not reminders:
            lbl_none = ctk.CTkLabel(
                self.reminder_scroll,
                text="Không có cảnh báo nào.",
                font=Theme.fonts.BODY,
                text_color=Theme.colors.TEXT_MUTED,
            )
            lbl_none.pack(pady=20)
            return

        # Render reminders (information only, without quick pay button)
        for r in reminders:
            if r.severity == ReminderSeverity.CRITICAL:
                bg = Theme.colors.DANGER_LIGHT
                border = Theme.colors.DANGER
            elif r.severity == ReminderSeverity.WARNING:
                bg = Theme.colors.WARNING_LIGHT
                border = Theme.colors.WARNING
            else:
                bg = Theme.colors.INFO_LIGHT
                border = Theme.colors.INFO

            rcard = ctk.CTkFrame(
                self.reminder_scroll,
                fg_color=bg,
                border_color=border,
                border_width=1,
                corner_radius=10,
            )
            rcard.pack(fill="x", padx=4, pady=4)

            lbl_title = ctk.CTkLabel(
                rcard,
                text=r.title,
                font=Theme.fonts.BODY_BOLD,
                text_color=Theme.colors.TEXT_PRIMARY,
                anchor="w",
            )
            lbl_title.pack(anchor="w", padx=10, pady=(8, 2))

            lbl_msg = ctk.CTkLabel(
                rcard,
                text=r.message,
                font=Theme.fonts.CAPTION,
                text_color=Theme.colors.TEXT_SECONDARY,
                anchor="w",
                wraplength=220,
                justify="left",
            )
            lbl_msg.pack(anchor="w", padx=10, pady=(0, 8))

    def _open_holiday_dialog(self, initial_tab: str = "create") -> None:
        if not self.holiday_service:
            ToastManager.show(self.winfo_toplevel(), "Dịch vụ lịch nghỉ chưa sẵn sàng.", level="error")
            return
        HolidayDialog(
            parent=self.winfo_toplevel(),
            holiday_service=self.holiday_service,
            initial_tab=initial_tab,
            on_saved=self._request_refresh,
        )

    def _cancel_holiday(self, holiday_id: str) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Hủy lịch nghỉ",
            message="Bạn có chắc muốn hủy lịch nghỉ này? Các ca học trong khoảng thời gian này sẽ được kích hoạt lại.",
            on_confirm=lambda: self._do_cancel_holiday(holiday_id),
        )

    def _do_cancel_holiday(self, holiday_id: str) -> None:
        if self.holiday_service:
            self.holiday_service.delete_holiday(holiday_id)
            ToastManager.show(self.winfo_toplevel(), "Đã hủy lịch nghỉ thành công.", level="success")
            self._request_refresh()

    def _open_add_schedule(self) -> None:
        ScheduleDialog(
            parent=self.winfo_toplevel(),
            schedule_service=self.schedule_service,
            student_service=self.student_service,
            class_service=self.class_service,
            initial_date=format_date_iso(self.current_week_date),
            on_saved=self._request_refresh,
        )

    def _open_edit_schedule(self, event: ScheduleResponseDTO) -> None:
        ScheduleDialog(
            parent=self.winfo_toplevel(),
            schedule_service=self.schedule_service,
            student_service=self.student_service,
            class_service=self.class_service,
            schedule=event,
            on_saved=self._request_refresh,
        )

    def _confirm_delete_schedule(self, event: ScheduleResponseDTO) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Xóa buổi học",
            message=f"Bạn có chắc muốn xóa ca học '{event.lesson_title}' ({event.start_time} - {event.end_time}) ngày {event.date}?",
            on_confirm=lambda: self._delete_schedule(event.id),
        )

    def _delete_schedule(self, schedule_id: str) -> None:
        self.schedule_service.delete_schedule(schedule_id)
        ToastManager.show(self.winfo_toplevel(), "Đã xóa ca học thành công.", level="success")
        self._request_refresh()

    def _confirm_delete_rescheduled(self, event: ScheduleResponseDTO) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Hủy ca đổi lịch",
            message=f"Bạn có chắc muốn xóa ca đổi lịch này?\nCa học cũ sẽ được tự động khôi phục lại trên bảng lịch.",
            on_confirm=lambda: self._do_delete_rescheduled(event.id),
        )

    def _do_delete_rescheduled(self, schedule_id: str) -> None:
        self.schedule_service.delete_schedule(schedule_id)
        ToastManager.show(self.winfo_toplevel(), "Đã xóa ca đổi lịch và khôi phục ca học cũ thành công.", level="success")
        self._request_refresh()

    def _open_offline_attendance(self, event: ScheduleResponseDTO) -> None:
        self._open_single_attendance(event)

    def _open_single_attendance(self, event: ScheduleResponseDTO) -> None:
        """Open attendance dialog for 1-on-1 and online classes with rescheduling support."""
        if event.status == ScheduleStatus.HOLIDAY:
            ToastManager.show(self.winfo_toplevel(), "Ca học này thuộc ngày nghỉ học, không thể điểm danh.", level="warning")
            return
        AttendanceDialog(
            parent=self.winfo_toplevel(),
            attendance_service=self.attendance_service,
            student_service=self.student_service,
            schedule_service=self.schedule_service,
            schedule=event,
            on_saved=self._request_refresh,
        )

    def _on_card_clicked(self, event: ScheduleResponseDTO) -> None:
        """Handle click on card body to view options or attendance."""
        if event.status == ScheduleStatus.HOLIDAY:
            ToastManager.show(self.winfo_toplevel(), "Ca học này thuộc ngày nghỉ học.", level="info")
            return
        if event.class_type == ClassType.OFFLINE:
            self._open_offline_attendance(event)
        else:
            self._open_single_attendance(event)

    def _open_attendance(self, event: ScheduleResponseDTO) -> None:
        """General attendance dispatching."""
        if event.class_type == ClassType.OFFLINE:
            self._open_offline_attendance(event)
        else:
            self._open_single_attendance(event)

    def _open_payment_for_student(self, student_id: str) -> None:
        PaymentDialog(
            parent=self.winfo_toplevel(),
            payment_service=self.payment_service,
            student_service=self.student_service,
            preselected_student_id=student_id,
            on_saved=self._request_refresh,
        )
