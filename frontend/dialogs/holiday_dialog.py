"""Dialog for scheduling teacher day-offs and holidays with interactive calendar picker and deletion management."""

from __future__ import annotations
from datetime import date, timedelta
from typing import Optional, Callable, List
import customtkinter as ctk

from frontend.theme import Theme
from backend.core.dates import today_date, today_str, format_date_iso, format_date_display, parse_date, WEEKDAY_VN
from backend.core.time_utils import validate_time_format, time_to_minutes
from backend.application.services.holiday_service import HolidayService
from frontend.components.dialogs import BaseModalDialog, ConfirmDialog
from frontend.components.buttons import PrimaryButton, OutlineButton
from frontend.components.toast import ToastManager
from frontend.components.calendar_picker import CalendarPickerFrame


class HolidayDialog(BaseModalDialog):
    """Modal dialog for scheduling and managing holidays with interactive calendar picker and delete capabilities."""

    def __init__(
        self,
        parent,
        holiday_service: HolidayService,
        initial_date: Optional[str] = None,
        initial_tab: str = "create",
        on_saved: Optional[Callable] = None,
    ):
        self.holiday_service = holiday_service
        try:
            self.initial_d = parse_date(initial_date) if initial_date else today_date()
        except Exception:
            self.initial_d = today_date()
        self.initial_tab = initial_tab
        self.on_saved = on_saved

        super().__init__(
            parent=parent,
            title="🏖️ Đặt lịch nghỉ dạy",
            subtitle="Tạm hoãn ca dạy khi bận / nghỉ lễ và quản lý xóa lịch nghỉ",
            width=560,
            height=680,
        )

        self._build_ui()

    def _build_ui(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)

        # 1. Top Segmented Tab (Đặt lịch mới vs Danh sách & Xóa lịch nghỉ)
        all_holidays = self.holiday_service.get_all_holidays()
        tab_list_title = f"📋 Danh sách lịch nghỉ ({len(all_holidays)})"
        tab_create_title = "➕ Đặt lịch nghỉ mới"

        self.seg_tabs = ctk.CTkSegmentedButton(
            self.body,
            values=[tab_create_title, tab_list_title],
            font=Theme.fonts.BODY_BOLD,
            height=34,
            selected_color=Theme.colors.EMERALD,
            selected_hover_color=Theme.colors.EMERALD_HOVER,
            command=self._on_tab_switched,
        )
        self.seg_tabs.pack(fill="x", pady=(2, 8))

        # 2. Main Frame Containers
        self.frame_create = ctk.CTkFrame(self.body, fg_color="transparent")
        self.frame_list = ctk.CTkFrame(self.body, fg_color="transparent")

        self._build_create_tab()
        self._build_list_tab()

        # 3. Footer setup
        self.lbl_error = ctk.CTkLabel(
            self.footer, text="", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.DANGER, wraplength=260, justify="left"
        )
        self.lbl_error.pack(side="left", padx=4)

        self.btn_cancel = OutlineButton(self.footer, text="Đóng", command=self.destroy, width=90)
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_save = PrimaryButton(self.footer, text="Xác nhận đặt lịch nghỉ", command=self._save, width=170)
        self.btn_save.pack(side="right")

        # Initial Tab Selection
        if self.initial_tab == "list":
            self.seg_tabs.set(tab_list_title)
        else:
            self.seg_tabs.set(tab_create_title)
        self._on_tab_switched(self.seg_tabs.get())

    def _build_create_tab(self) -> None:
        # Type selector (Nghỉ 1 ngày vs Nghỉ nhiều ngày)
        top_row = ctk.CTkFrame(self.frame_create, fg_color="transparent")
        top_row.pack(fill="x", pady=(2, 6))

        ctk.CTkLabel(
            top_row, text="Hình thức nghỉ: *", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 16))

        self.type_var = ctk.StringVar(value="SINGLE")

        rb_single = ctk.CTkRadioButton(
            top_row,
            text="Nghỉ 1 ngày",
            variable=self.type_var,
            value="SINGLE",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_type_changed,
        )
        rb_single.pack(side="left", padx=(0, 16))

        rb_range = ctk.CTkRadioButton(
            top_row,
            text="Nghỉ nhiều ngày",
            variable=self.type_var,
            value="RANGE",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_type_changed,
        )
        rb_range.pack(side="left")

        # Range target selector (Only shown in RANGE mode)
        self.range_target_frame = ctk.CTkFrame(self.frame_create, fg_color="transparent")
        self.btn_pick_start = ctk.CTkButton(
            self.range_target_frame,
            text="🟢 Chọn Từ ngày",
            font=Theme.fonts.CAPTION_BOLD,
            height=28,
            fg_color=Theme.colors.EMERALD,
            text_color="#FFFFFF",
            corner_radius=6,
            command=lambda: self._set_range_target("start"),
        )
        self.btn_pick_start.pack(side="left", padx=(0, 8))

        self.btn_pick_end = ctk.CTkButton(
            self.range_target_frame,
            text="🔴 Chọn Đến ngày",
            font=Theme.fonts.CAPTION_BOLD,
            height=28,
            fg_color=Theme.colors.BG_MUTED,
            text_color=Theme.colors.TEXT_PRIMARY,
            corner_radius=6,
            command=lambda: self._set_range_target("end"),
        )
        self.btn_pick_end.pack(side="left")

        # Interactive Calendar Picker
        self.cal_picker = CalendarPickerFrame(
            self.frame_create,
            initial_date=self.initial_d,
            initial_end_date=self.initial_d + timedelta(days=2),
            on_date_selected=self._on_single_date_selected,
            on_range_selected=self._on_range_dates_selected,
        )

        # Time Frame Section (Khung giờ nghỉ)
        time_container = ctk.CTkFrame(self.frame_create, fg_color=Theme.colors.BG_CARD, border_color=Theme.colors.BORDER_SUBTLE, border_width=1, corner_radius=8)
        time_container.pack(fill="x", pady=(6, 4), padx=2)

        t_head = ctk.CTkFrame(time_container, fg_color="transparent")
        t_head.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            t_head,
            text="⏰ Khung giờ nghỉ:",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 12))

        self.all_day_var = ctk.BooleanVar(value=True)
        cb_allday = ctk.CTkCheckBox(
            t_head,
            text="Nghỉ cả ngày",
            variable=self.all_day_var,
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_allday_toggled,
        )
        cb_allday.pack(side="left")

        # Time inputs frame
        self.f_time_inputs = ctk.CTkFrame(time_container, fg_color="transparent")
        self.f_time_inputs.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(self.f_time_inputs, text="Từ giờ:", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.TEXT_SECONDARY).pack(side="left", padx=(0, 4))
        self.entry_st = ctk.CTkEntry(self.f_time_inputs, font=Theme.fonts.BODY, width=64, height=28, corner_radius=Theme.radius.INPUT)
        self.entry_st.pack(side="left", padx=(0, 6))
        self.entry_st.insert(0, "08:00")

        ctk.CTkLabel(self.f_time_inputs, text="Đến giờ:", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.TEXT_SECONDARY).pack(side="left", padx=(0, 4))
        self.entry_et = ctk.CTkEntry(self.f_time_inputs, font=Theme.fonts.BODY, width=64, height=28, corner_radius=Theme.radius.INPUT)
        self.entry_et.pack(side="left", padx=(0, 10))
        self.entry_et.insert(0, "12:00")

        # Preset chips
        preset_chips = [
            ("Sáng", "08:00", "12:00"),
            ("Chiều", "14:00", "17:30"),
            ("Tối", "17:30", "21:00"),
        ]
        for label, s_t, e_t in preset_chips:
            btn_chip = ctk.CTkButton(
                self.f_time_inputs,
                text=f"{label} ({s_t}-{e_t})",
                font=Theme.fonts.CAPTION,
                height=24,
                fg_color=Theme.colors.BG_MUTED,
                hover_color=Theme.colors.EMERALD_LIGHT,
                text_color=Theme.colors.TEXT_PRIMARY,
                corner_radius=4,
                command=lambda s=s_t, e=e_t: self._apply_time_preset(s, e),
            )
            btn_chip.pack(side="left", padx=2)

        self._on_allday_toggled()

        # Info callout
        info_box = ctk.CTkFrame(self.frame_create, fg_color="#FEF2F2", corner_radius=8, border_color="#EF4444", border_width=1)
        info_box.pack(fill="x", pady=(4, 6))
        lbl_info = ctk.CTkLabel(
            info_box,
            text="ℹ️ Các ca học trong khung thời gian nghỉ sẽ tạm ngưng. Học sinh không bị trừ số buổi học.",
            font=Theme.fonts.CAPTION,
            text_color="#B91C1C",
            wraplength=480,
            justify="left",
        )
        lbl_info.pack(padx=10, pady=6)

    def _build_list_tab(self) -> None:
        self.scroll_list = ctk.CTkScrollableFrame(self.frame_list, fg_color="transparent", height=450)
        self.scroll_list.pack(fill="both", expand=True)

    def _render_holiday_list(self) -> None:
        for w in self.scroll_list.winfo_children():
            w.destroy()

        holidays = self.holiday_service.get_all_holidays()

        # Update tab label count
        tab_list_title = f"📋 Danh sách lịch nghỉ ({len(holidays)})"
        tab_create_title = "➕ Đặt lịch nghỉ mới"
        self.seg_tabs.configure(values=[tab_create_title, tab_list_title])

        if not holidays:
            lbl_none = ctk.CTkLabel(
                self.scroll_list,
                text="Hiện chưa có lịch nghỉ dạy nào.\nBạn có thể sang tab 'Đặt lịch nghỉ mới' để tạo thêm.",
                font=Theme.fonts.BODY,
                text_color=Theme.colors.TEXT_MUTED,
                justify="center",
            )
            lbl_none.pack(pady=40)
            return

        for h in holidays:
            card = ctk.CTkFrame(
                self.scroll_list,
                fg_color="#FEF2F2",
                border_color="#EF4444",
                border_width=1.5,
                corner_radius=10,
            )
            card.pack(fill="x", padx=4, pady=6)

            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)

            # Left Details Box
            left_box = ctk.CTkFrame(card, fg_color="transparent")
            left_box.grid(row=0, column=0, sticky="w", padx=12, pady=10)

            ctk.CTkLabel(
                left_box,
                text=f"🏖️ LỊCH NGHỈ DẠY",
                font=Theme.fonts.BODY_BOLD,
                text_color="#DC2626",
            ).pack(anchor="w")

            if h.start_date == h.end_date:
                try:
                    d_disp = format_date_display(parse_date(h.start_date))
                    date_lbl = f"📅 Ngày nghỉ: {d_disp} ({h.start_date})"
                except Exception:
                    date_lbl = f"📅 Ngày nghỉ: {h.start_date}"
            else:
                try:
                    s_disp = format_date_display(parse_date(h.start_date))
                    e_disp = format_date_display(parse_date(h.end_date))
                    date_lbl = f"📅 Từ ngày: {s_disp} đến {e_disp}"
                except Exception:
                    date_lbl = f"📅 Từ {h.start_date} đến {h.end_date}"

            ctk.CTkLabel(
                left_box,
                text=date_lbl,
                font=Theme.fonts.CAPTION_BOLD,
                text_color="#991B1B",
            ).pack(anchor="w", pady=(2, 0))

            time_text = "Cả ngày" if getattr(h, "is_all_day", True) else f"{h.start_time} - {h.end_time}"
            ctk.CTkLabel(
                left_box,
                text=f"⏰ Khung giờ: {time_text}",
                font=Theme.fonts.CAPTION,
                text_color="#7F1D1D",
            ).pack(anchor="w", pady=(2, 0))

            # Right Delete Button
            btn_del = ctk.CTkButton(
                card,
                text="🗑️ Xóa",
                font=Theme.fonts.CAPTION_BOLD,
                width=75,
                height=32,
                fg_color="#DC2626",
                hover_color="#B91C1C",
                text_color="#FFFFFF",
                corner_radius=6,
                command=lambda hid=h.id: self._confirm_delete_holiday(hid),
            )
            btn_del.grid(row=0, column=1, sticky="e", padx=12, pady=10)

    def _confirm_delete_holiday(self, holiday_id: str) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Xóa lịch nghỉ",
            message="Bạn có chắc muốn xóa lịch nghỉ này? Tất cả các ca dạy trong thời gian này sẽ được kích hoạt lại bình thường.",
            on_confirm=lambda: self._do_delete_holiday(holiday_id),
        )

    def _do_delete_holiday(self, holiday_id: str) -> None:
        self.holiday_service.delete_holiday(holiday_id)
        ToastManager.show(self.parent, "Đã xóa lịch nghỉ và khôi phục các ca dạy thành công.", level="success")
        self._render_holiday_list()
        if self.on_saved:
            self.on_saved()

    def _on_tab_switched(self, selected_value: str) -> None:
        self.lbl_error.configure(text="")
        if "Đặt lịch nghỉ mới" in selected_value:
            self.frame_list.pack_forget()
            self.frame_create.pack(fill="both", expand=True)
            self.btn_save.pack(side="right")
        else:
            self.frame_create.pack_forget()
            self.frame_list.pack(fill="both", expand=True)
            self.btn_save.pack_forget()
            self._render_holiday_list()

    def _on_type_changed(self) -> None:
        is_range = self.type_var.get() == "RANGE"
        self.cal_picker.set_range_mode(is_range)
        if is_range:
            self.range_target_frame.pack(fill="x", pady=(0, 4), before=self.cal_picker)
            self._set_range_target("start")
        else:
            self.range_target_frame.pack_forget()

    def _set_range_target(self, target: str) -> None:
        self.cal_picker.set_active_target(target)
        if target == "start":
            self.btn_pick_start.configure(fg_color=Theme.colors.EMERALD, text_color="#FFFFFF")
            self.btn_pick_end.configure(fg_color=Theme.colors.BG_MUTED, text_color=Theme.colors.TEXT_PRIMARY)
        else:
            self.btn_pick_start.configure(fg_color=Theme.colors.BG_MUTED, text_color=Theme.colors.TEXT_PRIMARY)
            self.btn_pick_end.configure(fg_color=Theme.colors.EMERALD, text_color="#FFFFFF")

    def _on_single_date_selected(self, d: date) -> None:
        self.lbl_error.configure(text="")

    def _on_range_dates_selected(self, start_d: date, end_d: date) -> None:
        self.lbl_error.configure(text="")
        self.btn_pick_start.configure(text=f"🟢 Từ: {format_date_display(start_d)}")
        self.btn_pick_end.configure(text=f"🔴 Đến: {format_date_display(end_d)}")

    def _on_allday_toggled(self) -> None:
        if self.all_day_var.get():
            self.f_time_inputs.pack_forget()
        else:
            self.f_time_inputs.pack(fill="x", padx=10, pady=(0, 6))

    def _apply_time_preset(self, st: str, et: str) -> None:
        self.entry_st.delete(0, "end")
        self.entry_st.insert(0, st)
        self.entry_et.delete(0, "end")
        self.entry_et.insert(0, et)

    def _save(self) -> None:
        self.lbl_error.configure(text="")
        is_range = self.type_var.get() == "RANGE"
        is_all_day = self.all_day_var.get()

        if not is_range:
            start_date_str = self.cal_picker.get_date()
            end_date_str = start_date_str
        else:
            start_date_str, end_date_str = self.cal_picker.get_range()

        st = "00:00"
        et = "23:59"

        if not is_all_day:
            st = self.entry_st.get().strip()
            et = self.entry_et.get().strip()

            if not validate_time_format(st) or not validate_time_format(et):
                self.lbl_error.configure(text="Định dạng giờ không hợp lệ (HH:MM).")
                return

            if start_date_str == end_date_str and time_to_minutes(et) <= time_to_minutes(st):
                self.lbl_error.configure(text="Giờ kết thúc phải sau giờ bắt đầu.")
                return

        try:
            holiday = self.holiday_service.create_holiday(
                title="Nghỉ dạy",
                start_date=start_date_str,
                end_date=end_date_str,
                start_time=st,
                end_time=et,
                is_all_day=is_all_day,
            )

            time_desc = "cả ngày" if is_all_day else f"{st} - {et}"
            if start_date_str == end_date_str:
                msg = f"Đã đặt lịch nghỉ ngày {format_date_display(parse_date(start_date_str))} ({time_desc})."
            else:
                msg = f"Đã đặt lịch nghỉ từ {format_date_display(parse_date(start_date_str))} đến {format_date_display(parse_date(end_date_str))}."

            ToastManager.show(self.parent, f"🏖️ {msg}", level="success")
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as e:
            self.lbl_error.configure(text=f"Lỗi: {e}")
