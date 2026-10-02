"""Tuition payment status screen listing paid and unpaid students with class filters."""

from __future__ import annotations
from typing import Optional, List
import customtkinter as ctk

from frontend.theme import Theme
from backend.core.enums import ClassType
from backend.core.event_bus import event_bus
from backend.application.services.payment_service import PaymentService
from backend.application.services.student_service import StudentService
from backend.application.services.dashboard_service import DashboardService
from backend.application.dto.student_dto import StudentResponseDTO
from frontend.components.cards import GlassCard, StatCard
from frontend.components.badges import Badge
from frontend.components.icon_loader import IconLoader
from frontend.components.toast import ToastManager
from frontend.components.dialogs import ConfirmDialog


class PaymentsScreen(ctk.CTkFrame):
    """Simplified tuition screen listing paid and unpaid students with type filters."""

    def __init__(
        self,
        master,
        payment_service: PaymentService,
        student_service: StudentService,
        dashboard_service: DashboardService,
        **kwargs,
    ):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self.payment_service = payment_service
        self.student_service = student_service
        self.dashboard_service = dashboard_service

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_kpi_cards()
        self._build_top_controls()
        self._build_students_table()

        self._refresh_timer = None
        self._dirty = False

        event_bus.subscribe("payments_changed", self._on_data_invalidated)
        event_bus.subscribe("students_changed", self._on_data_invalidated)

        self.refresh()

    def _on_data_invalidated(self, _=None) -> None:
        if not self.winfo_exists():
            return
        if not self.winfo_viewable():
            self._dirty = True
            return
        self._request_refresh()

    def _request_refresh(self) -> None:
        if getattr(self, "_refresh_timer", None) is not None:
            try:
                self.after_cancel(self._refresh_timer)
            except Exception:
                pass
        self._refresh_timer = self.after(30, self._do_debounced_refresh)

    def _do_debounced_refresh(self) -> None:
        self._refresh_timer = None
        self._dirty = False
        self.refresh()

    def _build_kpi_cards(self) -> None:
        # Exactly 3 KPI cards: Total Revenue, Paid Students, Unpaid Students
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.kpi_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # 1. Monthly Revenue
        money_ic = IconLoader.get_icon("payment", size=24, color=Theme.colors.EMERALD)
        self.card_rev = StatCard(self.kpi_frame, title="DOANH THU THÁNG", value="0 ₫", icon=money_ic, accent_color=Theme.colors.EMERALD_LIGHT)
        self.card_rev.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # 2. Paid Students Count
        check_ic = IconLoader.get_icon("check", size=24, color=Theme.colors.OCEAN)
        self.card_paid = StatCard(self.kpi_frame, title="ĐÃ ĐÓNG HỌC PHÍ", value="0 bạn", icon=check_ic, accent_color=Theme.colors.OCEAN_LIGHT)
        self.card_paid.grid(row=0, column=1, sticky="ew", padx=4)

        # 3. Unpaid Students Count (remaining_lessons <= 1)
        warn_ic = IconLoader.get_icon("warning", size=24, color=Theme.colors.DANGER)
        self.card_unpaid = StatCard(self.kpi_frame, title="CHƯA ĐÓNG HỌC PHÍ", value="0 bạn", icon=warn_ic, accent_color=Theme.colors.DANGER_LIGHT)
        self.card_unpaid.grid(row=0, column=2, sticky="ew", padx=(8, 0))

    def _build_top_controls(self) -> None:
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        ctrl_frame.grid_columnconfigure(0, weight=1)

        # Left Filters: Search + Class Type + Payment Status
        left_filters = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        left_filters.grid(row=0, column=0, sticky="w")

        # Search Entry
        search_icon = IconLoader.get_icon("search", size=16, color=Theme.colors.TEXT_MUTED)
        self.entry_search = ctk.CTkEntry(
            left_filters,
            placeholder_text="Tìm học viên theo tên hoặc SĐT...",
            width=260,
            height=36,
            corner_radius=Theme.radius.INPUT,
            font=Theme.fonts.BODY,
        )
        self.entry_search.pack(side="left", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda e: self._render_table_rows())

        # Class Type Filter
        self.opt_class_type = ctk.CTkOptionMenu(
            left_filters,
            values=["Tất cả loại lớp", ClassType.ONE_ON_ONE.display_name, ClassType.OFFLINE.display_name, ClassType.ONLINE.display_name],
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.EMERALD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=lambda _: self._render_table_rows(),
        )
        self.opt_class_type.pack(side="left", padx=(0, 10))

        # Payment Status Filter
        self.opt_payment_status = ctk.CTkOptionMenu(
            left_filters,
            values=["Tất cả tình trạng", "Đã đóng học phí", "Chưa đóng học phí"],
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.OCEAN,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=lambda _: self._render_table_rows(),
        )
        self.opt_payment_status.pack(side="left", padx=(0, 10))

    def _build_students_table(self) -> None:
        self.table_card = GlassCard(self)
        self.table_card.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.table_card.grid_rowconfigure(1, weight=1)
        self.table_card.grid_columnconfigure(0, weight=1)

        # Header Frame (padx=(8, 24) compensates for vertical scrollbar)
        header = ctk.CTkFrame(self.table_card, fg_color=Theme.colors.BG_MUTED, corner_radius=10, height=44)
        header.grid(row=0, column=0, sticky="ew", padx=(8, 24), pady=(8, 4))

        # Standardized column specifications: (Title, minsize_px, weight)
        # ONLY fields requested: STT, Họ và Tên, Hình thức, Lớp học, Tình trạng học phí
        self.cols = [
            ("STT", 50, 0),
            ("Họ và Tên", 220, 1),
            ("Hình thức", 130, 0),
            ("Lớp học", 200, 0),
            ("Tình trạng học phí", 160, 0),
        ]
        for idx, (title, minsize, weight) in enumerate(self.cols):
            header.grid_columnconfigure(idx, minsize=minsize, weight=weight)
            lbl = ctk.CTkLabel(
                header,
                text=title,
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.TEXT_SECONDARY,
                anchor="w",
            )
            lbl.grid(row=0, column=idx, sticky="w", padx=10, pady=10)

        # Scrollable table body
        self.rows_scroll = ctk.CTkScrollableFrame(self.table_card, fg_color="transparent")
        self.rows_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))

    def refresh(self) -> None:
        summary = self.dashboard_service.get_summary()
        self._update_kpis(summary)
        self._render_table_rows()

    def _update_kpis(self, summary: dict) -> None:
        # Update Revenue Card
        for child in self.card_rev.winfo_children():
            if isinstance(child, ctk.CTkLabel) and child.cget("font") == Theme.fonts.TITLE:
                child.configure(text=summary["total_revenue_display"])

        # Update Paid Students Card
        for child in self.card_paid.winfo_children():
            if isinstance(child, ctk.CTkLabel) and child.cget("font") == Theme.fonts.TITLE:
                child.configure(text=f"{summary.get('paid_students_count', 0)} bạn")

        # Update Unpaid Students Card
        for child in self.card_unpaid.winfo_children():
            if isinstance(child, ctk.CTkLabel) and child.cget("font") == Theme.fonts.TITLE:
                child.configure(text=f"{summary.get('unpaid_students_count', 0)} bạn")

    def _render_table_rows(self) -> None:
        for w in self.rows_scroll.winfo_children():
            w.destroy()

        query = self.entry_search.get().strip().lower()
        selected_type_str = self.opt_class_type.get()
        selected_status_str = self.opt_payment_status.get()

        type_map = {
            ClassType.ONE_ON_ONE.display_name: ClassType.ONE_ON_ONE,
            ClassType.OFFLINE.display_name: ClassType.OFFLINE,
            ClassType.ONLINE.display_name: ClassType.ONLINE,
        }
        filter_type = type_map.get(selected_type_str)

        all_students = self.student_service.get_students(active_only=True)

        # Filter by class type
        if filter_type:
            all_students = [s for s in all_students if s.class_type == filter_type]

        # Filter by payment status (<= 1 is Chưa đóng, > 1 is Đã đóng)
        if selected_status_str == "Đã đóng học phí":
            all_students = [s for s in all_students if s.remaining_lessons > 1]
        elif selected_status_str == "Chưa đóng học phí":
            all_students = [s for s in all_students if s.remaining_lessons <= 1]

        # Filter by search query
        if query:
            all_students = [s for s in all_students if query in s.name.lower() or query in s.phone]

        if not all_students:
            lbl_empty = ctk.CTkLabel(
                self.rows_scroll,
                text="Không tìm thấy học viên nào phù hợp bộ lọc.",
                font=Theme.fonts.BODY,
                text_color=Theme.colors.TEXT_MUTED,
            )
            lbl_empty.pack(pady=30)
            return

        for idx, s in enumerate(all_students):
            self._render_student_tuition_row(idx + 1, s)

    def _render_student_tuition_row(self, index: int, s: StudentResponseDTO) -> None:
        bg_col = Theme.colors.BG_CARD if index % 2 == 1 else "#FBFBFC"
        row_frame = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=8, height=48)
        row_frame.pack(fill="x", padx=4, pady=2)
        for c_idx, (_, minsize, weight) in enumerate(self.cols):
            row_frame.grid_columnconfigure(c_idx, minsize=minsize, weight=weight)

        # 0. STT
        lbl_stt = ctk.CTkLabel(row_frame, text=str(index), font=Theme.fonts.BODY, text_color=Theme.colors.TEXT_MUTED)
        lbl_stt.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # 1. Họ và Tên
        lbl_name = ctk.CTkLabel(row_frame, text=s.name, font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY)
        lbl_name.grid(row=0, column=1, sticky="w", padx=10, pady=10)

        # 2. Hình thức
        badge_type = Badge.for_class_type(row_frame, s.class_type)
        badge_type.grid(row=0, column=2, sticky="w", padx=10, pady=6)

        # 3. Lớp học
        cname = s.class_name if s.class_name else "Chưa gán lớp"
        lbl_cname = ctk.CTkLabel(row_frame, text=cname, font=Theme.fonts.BODY, text_color=Theme.colors.TEXT_PRIMARY if s.class_name else Theme.colors.TEXT_MUTED)
        lbl_cname.grid(row=0, column=3, sticky="w", padx=10, pady=10)

        # 4. Tình trạng học phí: Interactive button to toggle status with confirmation
        if s.remaining_lessons <= 1:
            btn_tuition = ctk.CTkButton(
                row_frame,
                text="Chưa đóng",
                font=Theme.fonts.CAPTION_BOLD,
                width=110,
                height=28,
                fg_color="#FEE2E2",
                hover_color="#FECACA",
                text_color="#DC2626",
                border_color="#FCA5A5",
                border_width=1,
                corner_radius=Theme.radius.BADGE,
                command=lambda stu=s: self._prompt_mark_paid(stu),
            )
        else:
            btn_tuition = ctk.CTkButton(
                row_frame,
                text="Đã đóng",
                font=Theme.fonts.CAPTION_BOLD,
                width=110,
                height=28,
                fg_color=Theme.colors.EMERALD_LIGHT,
                hover_color="#A7F3D0",
                text_color="#047857",
                border_color=Theme.colors.EMERALD_BORDER,
                border_width=1,
                corner_radius=Theme.radius.BADGE,
                command=lambda stu=s: self._prompt_mark_unpaid(stu),
            )
        btn_tuition.grid(row=0, column=4, sticky="w", padx=10, pady=6)

    def _prompt_mark_paid(self, student: StudentResponseDTO) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Xác nhận đóng học phí",
            message=f"Xác nhận học sinh '{student.name}' đã hoàn tất đóng học phí?",
            confirm_text="Xác nhận",
            cancel_text="Hủy",
            is_danger=False,
            on_confirm=lambda: self._handle_tuition_toggle(student.id, True, student.name),
        )

    def _prompt_mark_unpaid(self, student: StudentResponseDTO) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Xác nhận chưa đóng học phí",
            message=f"Xác nhận chuyển học sinh '{student.name}' sang Chưa đóng học phí (do thao tác nhầm)?",
            confirm_text="Xác nhận",
            cancel_text="Hủy",
            is_danger=True,
            on_confirm=lambda: self._handle_tuition_toggle(student.id, False, student.name),
        )

    def _handle_tuition_toggle(self, student_id: str, mark_as_paid: bool, student_name: str) -> None:
        self.payment_service.toggle_tuition_status(student_id, mark_as_paid)
        if mark_as_paid:
            ToastManager.show(self.winfo_toplevel(), f"Đã ghi nhận đóng học phí cho {student_name} (+8 buổi).", level="success")
        else:
            ToastManager.show(self.winfo_toplevel(), f"Đã chuyển {student_name} về Chưa đóng học phí.", level="info")
        self.refresh()
