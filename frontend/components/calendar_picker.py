"""Interactive calendar date picker component supporting both single-date and date-range selection."""

from __future__ import annotations
import calendar
from datetime import date
from typing import Optional, Callable, Tuple
import customtkinter as ctk

from frontend.theme import Theme
from backend.core.dates import format_date_iso, format_date_display, today_date, WEEKDAY_VN

calendar.setfirstweekday(calendar.MONDAY)


class CalendarPickerFrame(ctk.CTkFrame):
    """Interactive calendar date picker table displaying days of the month with clean highlight.
    Supports both single-date selection and date-range selection modes.
    """

    def __init__(
        self,
        parent,
        initial_date: Optional[date] = None,
        on_date_selected: Optional[Callable[[date], None]] = None,
        is_range_mode: bool = False,
        initial_end_date: Optional[date] = None,
        on_range_selected: Optional[Callable[[date, date], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color=Theme.colors.BG_CARD,
            border_color=Theme.colors.BORDER_SUBTLE,
            border_width=1,
            corner_radius=10,
            **kwargs,
        )
        self.is_range_mode = is_range_mode
        self.selected_date: date = initial_date or today_date()
        self.start_date: date = initial_date or today_date()
        self.end_date: date = initial_end_date or self.start_date
        self.active_range_target: str = "start"  # "start" or "end"

        self.view_year: int = self.selected_date.year
        self.view_month: int = self.selected_date.month
        self.on_date_selected = on_date_selected
        self.on_range_selected = on_range_selected

        self._build_ui()
        self._render_month()

    def _build_ui(self) -> None:
        self.pack_configure(padx=2, pady=4, fill="x")

        # 1. Month Navigation Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 4))

        self.btn_prev = ctk.CTkButton(
            header,
            text="◀",
            width=28,
            height=28,
            font=Theme.fonts.CAPTION_BOLD,
            fg_color=Theme.colors.BG_MUTED,
            text_color=Theme.colors.TEXT_PRIMARY,
            hover_color=Theme.colors.BORDER_SUBTLE,
            corner_radius=6,
            command=self._prev_month,
        )
        self.btn_prev.pack(side="left")

        self.lbl_month = ctk.CTkLabel(
            header,
            text="",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        self.lbl_month.pack(side="left", expand=True)

        self.btn_next = ctk.CTkButton(
            header,
            text="▶",
            width=28,
            height=28,
            font=Theme.fonts.CAPTION_BOLD,
            fg_color=Theme.colors.BG_MUTED,
            text_color=Theme.colors.TEXT_PRIMARY,
            hover_color=Theme.colors.BORDER_SUBTLE,
            corner_radius=6,
            command=self._next_month,
        )
        self.btn_next.pack(side="right")

        # 2. Weekday Header (T2 -> CN)
        days_header = ctk.CTkFrame(self, fg_color="transparent")
        days_header.pack(fill="x", padx=10, pady=(2, 2))
        short_weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        for i, sw in enumerate(short_weekdays):
            days_header.grid_columnconfigure(i, weight=1)
            c = Theme.colors.DANGER if i == 6 else Theme.colors.TEXT_MUTED
            ctk.CTkLabel(days_header, text=sw, font=Theme.fonts.CAPTION_BOLD, text_color=c, width=36).grid(row=0, column=i, pady=2)

        # 3. Days Grid Frame
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=10, pady=(2, 6))
        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1)

        # 4. Selected Date Display Badge
        self.lbl_selected = ctk.CTkLabel(
            self,
            text="",
            font=Theme.fonts.CAPTION_BOLD,
            text_color=Theme.colors.EMERALD,
        )
        self.lbl_selected.pack(padx=10, pady=(0, 8))

    def _render_month(self) -> None:
        self.lbl_month.configure(text=f"Tháng {self.view_month:02d} / {self.view_year}")

        # Clear existing grid
        for w in self.grid_frame.winfo_children():
            w.destroy()

        weeks = calendar.monthcalendar(self.view_year, self.view_month)
        for r_idx, week in enumerate(weeks):
            for c_idx, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(self.grid_frame, text="", width=36, height=26).grid(row=r_idx, column=c_idx, padx=1, pady=1)
                else:
                    curr_d = date(self.view_year, self.view_month, day)
                    bg, text_c, is_bold = self._get_day_style(curr_d)

                    btn = ctk.CTkButton(
                        self.grid_frame,
                        text=str(day),
                        font=Theme.fonts.CAPTION_BOLD if is_bold else Theme.fonts.CAPTION,
                        width=36,
                        height=26,
                        fg_color=bg,
                        text_color=text_c,
                        hover_color=Theme.colors.EMERALD_HOVER if is_bold else Theme.colors.BG_MUTED,
                        corner_radius=6,
                        command=lambda d=day: self._on_day_clicked(d),
                    )
                    btn.grid(row=r_idx, column=c_idx, padx=1, pady=1)

        self._update_selected_label()

    def _get_day_style(self, curr_d: date) -> Tuple[str, str, bool]:
        if not self.is_range_mode:
            is_active = curr_d == self.selected_date
            if is_active:
                return Theme.colors.EMERALD, "#FFFFFF", True
            return "transparent", Theme.colors.TEXT_PRIMARY, False
        else:
            # Range mode
            is_start = curr_d == self.start_date
            is_end = curr_d == self.end_date
            if is_start or is_end:
                return Theme.colors.EMERALD, "#FFFFFF", True
            if self.start_date < curr_d < self.end_date:
                return "#D1FAE5", "#065F46", True  # Mint green highlight for range
            return "transparent", Theme.colors.TEXT_PRIMARY, False

    def _on_day_clicked(self, day: int) -> None:
        curr_d = date(self.view_year, self.view_month, day)
        if not self.is_range_mode:
            self.selected_date = curr_d
            self._render_month()
            if self.on_date_selected:
                self.on_date_selected(self.selected_date)
        else:
            if self.active_range_target == "start":
                self.start_date = curr_d
                if self.end_date < self.start_date:
                    self.end_date = self.start_date
                # Switch active target to end for convenience
                self.active_range_target = "end"
            else:
                self.end_date = curr_d
                if self.end_date < self.start_date:
                    self.start_date = self.end_date
            self._render_month()
            if self.on_range_selected:
                self.on_range_selected(self.start_date, self.end_date)

    def _prev_month(self) -> None:
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._render_month()

    def _next_month(self) -> None:
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self._render_month()

    def _update_selected_label(self) -> None:
        if not self.is_range_mode:
            w_vn = WEEKDAY_VN[self.selected_date.weekday()]
            d_str = format_date_display(self.selected_date)
            self.lbl_selected.configure(
                text=f"📅 Ngày đã chọn: {w_vn}, ngày {d_str} ({format_date_iso(self.selected_date)})",
                text_color=Theme.colors.EMERALD,
            )
        else:
            s_str = format_date_display(self.start_date)
            e_str = format_date_display(self.end_date)
            num_days = (self.end_date - self.start_date).days + 1
            self.lbl_selected.configure(
                text=f"📅 Thời gian nghỉ: Từ {s_str} đến {e_str} ({num_days} ngày)",
                text_color=Theme.colors.EMERALD,
            )

    def set_range_mode(self, is_range: bool) -> None:
        self.is_range_mode = is_range
        self._render_month()

    def set_active_target(self, target: str) -> None:
        self.active_range_target = target
        self._render_month()

    def get_date(self) -> str:
        return format_date_iso(self.selected_date)

    def get_range(self) -> Tuple[str, str]:
        return format_date_iso(self.start_date), format_date_iso(self.end_date)

    def set_date(self, d: date) -> None:
        self.selected_date = d
        self.view_year = d.year
        self.view_month = d.month
        self._render_month()

    def set_range(self, start_d: date, end_d: date) -> None:
        self.start_date = start_d
        self.end_date = end_d
        self.view_year = start_d.year
        self.view_month = start_d.month
        self._render_month()
