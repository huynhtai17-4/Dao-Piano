"""Unified Student and Tuition management screen with rich aesthetics, full-width responsive layout, and perfect alignment."""

from __future__ import annotations
from typing import Optional, List, Tuple
import customtkinter as ctk

from frontend.theme import Theme
from backend.core.enums import ClassType
from backend.core.event_bus import event_bus
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.services.payment_service import PaymentService
from backend.application.services.dashboard_service import DashboardService
from backend.application.services.schedule_service import ScheduleService
from backend.application.dto.student_dto import StudentResponseDTO
from frontend.components.cards import GlassCard, StatCard
from frontend.components.buttons import PrimaryButton, IconButton
from frontend.components.badges import Badge
from frontend.components.icon_loader import IconLoader
from frontend.components.toast import ToastManager
from frontend.components.dialogs import ConfirmDialog
from frontend.dialogs.student_dialog import StudentDialog
from frontend.dialogs.quick_lessons_dialog import QuickLessonsDialog


class StudentsScreen(ctk.CTkFrame):
    """Merged view for Student directory and Tuition tracking with premium full-width aesthetics and pixel-perfect alignment."""

    # Column specifications: (Title, weight, alignment)
    COL_DEFS: List[Tuple[str, int, str]] = [
        ("STT", 1, "center"),
        ("Họ và tên", 6, "w"),
        ("Số điện thoại", 3, "w"),
        ("Hình thức", 2, "center"),
        ("Lớp học", 6, "w"),
        ("Số buổi còn", 3, "center"),
        ("Tình trạng học phí", 3, "center"),
        ("Thao tác", 2, "center"),
    ]

    def __init__(
        self,
        master,
        student_service: StudentService,
        class_service: ClassService,
        payment_service: PaymentService,
        dashboard_service: Optional[DashboardService] = None,
        schedule_service: Optional[ScheduleService] = None,
        **kwargs,
    ):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self.student_service = student_service
        self.class_service = class_service
        self.payment_service = payment_service
        self.dashboard_service = dashboard_service
        self.schedule_service = schedule_service

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_kpi_cards()
        self._build_top_controls()
        self._build_table_container()

        self._refresh_timer = None
        self._dirty = False

        event_bus.subscribe("students_changed", self._on_data_invalidated)
        event_bus.subscribe("payments_changed", self._on_data_invalidated)
        event_bus.subscribe("classes_changed", self._on_data_invalidated)

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
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # 1. Total Students
        stu_ic = IconLoader.get_icon("students", size=24, color="#7C3AED")
        self.card_total = StatCard(self.kpi_frame, title="TỔNG HỌC VIÊN", value="0 bạn", icon=stu_ic, accent_color=Theme.colors.PURPLE_LIGHT)
        self.card_total.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        # 2. Paid Students
        check_ic = IconLoader.get_icon("check", size=24, color=Theme.colors.EMERALD)
        self.card_paid = StatCard(self.kpi_frame, title="ĐÃ ĐÓNG HỌC PHÍ", value="0 bạn", icon=check_ic, accent_color=Theme.colors.EMERALD_LIGHT)
        self.card_paid.grid(row=0, column=1, sticky="ew", padx=3)

        # 3. Unpaid Students
        warn_ic = IconLoader.get_icon("warning", size=24, color=Theme.colors.DANGER)
        self.card_unpaid = StatCard(self.kpi_frame, title="CHƯA ĐÓNG HỌC PHÍ", value="0 bạn", icon=warn_ic, accent_color=Theme.colors.DANGER_LIGHT)
        self.card_unpaid.grid(row=0, column=2, sticky="ew", padx=3)

        # 4. Monthly Revenue
        rev_ic = IconLoader.get_icon("payment", size=24, color=Theme.colors.OCEAN)
        self.card_rev = StatCard(self.kpi_frame, title="DOANH THU THÁNG", value="0 ₫", icon=rev_ic, accent_color=Theme.colors.OCEAN_LIGHT)
        self.card_rev.grid(row=0, column=3, sticky="ew", padx=(6, 0))

    def _build_top_controls(self) -> None:
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        ctrl_frame.grid_columnconfigure(0, weight=1)

        # Left: Search & Filter Controls
        filter_box = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        filter_box.grid(row=0, column=0, sticky="w")

        # Search Entry
        search_icon = IconLoader.get_icon("search", size=16, color=Theme.colors.TEXT_MUTED)
        self.entry_search = ctk.CTkEntry(
            filter_box,
            placeholder_text="Tìm theo tên hoặc số điện thoại...",
            width=260,
            height=36,
            corner_radius=Theme.radius.INPUT,
            font=Theme.fonts.BODY,
        )
        self.entry_search.pack(side="left", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda e: self.refresh())

        # Class Type Filter
        self.opt_type_filter = ctk.CTkOptionMenu(
            filter_box,
            values=["Tất cả hình thức", ClassType.ONE_ON_ONE.display_name, ClassType.OFFLINE.display_name, ClassType.ONLINE.display_name],
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.EMERALD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=lambda _: self.refresh(),
        )
        self.opt_type_filter.pack(side="left", padx=(0, 10))

        # Tuition Status Filter
        self.opt_payment_status = ctk.CTkOptionMenu(
            filter_box,
            values=["Tất cả học phí", "Đã đóng học phí", "Chưa đóng học phí"],
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.OCEAN,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=lambda _: self.refresh(),
        )
        self.opt_payment_status.pack(side="left", padx=(0, 10))

        # Right: Add Student Button
        plus_icon = IconLoader.get_icon("plus", size=16, color=Theme.colors.TEXT_WHITE)
        btn_add = PrimaryButton(
            ctrl_frame,
            text="Thêm học sinh",
            icon=plus_icon,
            command=self._open_add_student,
            width=150,
            height=36,
        )
        btn_add.grid(row=0, column=1, sticky="e")

    def _build_table_container(self) -> None:
        self.table_card = GlassCard(self)
        self.table_card.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.table_card.grid_rowconfigure(0, weight=1)
        self.table_card.grid_columnconfigure(0, weight=1)

        # Scrollable table container hosting single cohesive grid
        self.rows_scroll = ctk.CTkScrollableFrame(self.table_card, fg_color="transparent")
        self.rows_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def refresh(self) -> None:
        # Update KPI cards if dashboard_service is available
        if self.dashboard_service:
            summary = self.dashboard_service.get_summary()
            self.card_total.update_value(f"{summary['total_students']} bạn")
            self.card_paid.update_value(f"{summary['paid_students_count']} bạn")
            self.card_unpaid.update_value(f"{summary['unpaid_students_count']} bạn")
            self.card_rev.update_value(summary['total_revenue_display'])

        for w in self.rows_scroll.winfo_children():
            w.destroy()

        # Configure responsive grid column weights on the scrollable container
        for c, (_, weight, _) in enumerate(self.COL_DEFS):
            self.rows_scroll.grid_columnconfigure(c, weight=weight)

        # 1. Render Header Row at Row 0 for 100% pixel-perfect vertical alignment with all rows
        for c, (title, _, align) in enumerate(self.COL_DEFS):
            h_cell = ctk.CTkFrame(self.rows_scroll, fg_color="#F1F5F9", corner_radius=6, height=44)
            h_cell.grid(row=0, column=c, sticky="nsew", padx=2, pady=(2, 6))
            lbl = ctk.CTkLabel(
                h_cell,
                text=title,
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.TEXT_SECONDARY,
                anchor=align,
            )
            lbl.pack(fill="both", expand=True, padx=12, pady=10)

        # 2. Filter students
        query = self.entry_search.get().strip().lower()
        selected_type_str = self.opt_type_filter.get()
        selected_pay_str = self.opt_payment_status.get()

        type_map = {
            ClassType.ONE_ON_ONE.display_name: ClassType.ONE_ON_ONE,
            ClassType.OFFLINE.display_name: ClassType.OFFLINE,
            ClassType.ONLINE.display_name: ClassType.ONLINE,
        }
        filter_type = type_map.get(selected_type_str)

        students = self.student_service.get_students(
            active_only=True,
            class_type=filter_type,
            search_query=query if query else None,
        )

        if selected_pay_str == "Đã đóng học phí":
            students = [s for s in students if s.remaining_lessons > 1]
        elif selected_pay_str == "Chưa đóng học phí":
            students = [s for s in students if s.remaining_lessons <= 1]

        if not students:
            lbl_empty = ctk.CTkLabel(
                self.rows_scroll,
                text="Không tìm thấy học sinh nào phù hợp bộ lọc.",
                font=Theme.fonts.BODY,
                text_color=Theme.colors.TEXT_MUTED,
            )
            lbl_empty.grid(row=1, column=0, columnspan=len(self.COL_DEFS), pady=40)
            return

        # 3. Render student rows (Rows 1..N)
        for idx, student in enumerate(students, start=1):
            self._render_student_grid_row(idx, student)

    def _render_student_grid_row(self, row_idx: int, s: StudentResponseDTO) -> None:
        bg_col = "#FFFFFF" if row_idx % 2 == 1 else "#F8FAFC"

        # 0. STT (Centered)
        c0 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c0.grid(row=row_idx, column=0, sticky="nsew", padx=2, pady=1)
        ctk.CTkLabel(c0, text=str(row_idx), font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_MUTED).pack(fill="both", expand=True)

        # 1. Họ và tên (Left-aligned, prominent bold text)
        c1 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c1.grid(row=row_idx, column=1, sticky="nsew", padx=2, pady=1)
        lbl_name = ctk.CTkLabel(c1, text=s.name, font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY, anchor="w")
        lbl_name.pack(fill="both", expand=True, padx=12)

        # 2. Số điện thoại (Left-aligned)
        c2 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c2.grid(row=row_idx, column=2, sticky="nsew", padx=2, pady=1)
        lbl_phone = ctk.CTkLabel(c2, text=s.phone, font=Theme.fonts.BODY, text_color=Theme.colors.TEXT_SECONDARY, anchor="w")
        lbl_phone.pack(fill="both", expand=True, padx=10)

        # 3. Hình thức (Centered Badge)
        c3 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c3.grid(row=row_idx, column=3, sticky="nsew", padx=2, pady=1)
        badge_type = Badge.for_class_type(c3, s.class_type)
        badge_type.pack(expand=True, pady=8)

        # 4. Lớp học (Left-aligned)
        c4 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c4.grid(row=row_idx, column=4, sticky="nsew", padx=2, pady=1)
        cname = s.class_name if s.class_name else "Chưa gán lớp"
        lbl_cname = ctk.CTkLabel(
            c4,
            text=cname,
            font=Theme.fonts.BODY,
            text_color=Theme.colors.TEXT_PRIMARY if s.class_name else Theme.colors.TEXT_MUTED,
            anchor="w",
        )
        lbl_cname.pack(fill="both", expand=True, padx=10)

        # 5. Số buổi còn (Centered Interactive Box)
        c5 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c5.grid(row=row_idx, column=5, sticky="nsew", padx=2, pady=1)
        box_lessons = ctk.CTkFrame(c5, fg_color="transparent")
        box_lessons.pack(expand=True, pady=8)

        badge_lessons = Badge.for_lessons_count(box_lessons, s.remaining_lessons)
        badge_lessons.pack(side="left")
        badge_lessons.configure(cursor="hand2")
        badge_lessons.bind("<Button-1>", lambda e, stu=s: self._open_quick_adjust_lessons(stu))
        for child in badge_lessons.winfo_children():
            child.configure(cursor="hand2")
            child.bind("<Button-1>", lambda e, stu=s: self._open_quick_adjust_lessons(stu))

        adj_ic = IconLoader.get_icon("edit", size=11, color=Theme.colors.TEXT_MUTED)
        btn_adj = IconButton(box_lessons, icon=adj_ic, size=22, command=lambda stu=s: self._open_quick_adjust_lessons(stu))
        btn_adj.pack(side="left", padx=(4, 0))

        # 6. Học phí (Centered Interactive Button)
        c6 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c6.grid(row=row_idx, column=6, sticky="nsew", padx=2, pady=1)
        if s.remaining_lessons <= 1:
            btn_tuition = ctk.CTkButton(
                c6,
                text="Chưa đóng",
                font=Theme.fonts.CAPTION_BOLD,
                width=100,
                height=28,
                fg_color="#FEF2F2",
                hover_color="#FEE2E2",
                text_color="#DC2626",
                border_color="#FECACA",
                border_width=1,
                corner_radius=Theme.radius.BADGE,
                command=lambda stu=s: self._prompt_mark_paid(stu),
            )
        else:
            btn_tuition = ctk.CTkButton(
                c6,
                text="Đã đóng",
                font=Theme.fonts.CAPTION_BOLD,
                width=100,
                height=28,
                fg_color=Theme.colors.EMERALD_LIGHT,
                hover_color="#A7F3D0",
                text_color="#047857",
                border_color=Theme.colors.EMERALD_BORDER,
                border_width=1,
                corner_radius=Theme.radius.BADGE,
                command=lambda stu=s: self._prompt_mark_unpaid(stu),
            )
        btn_tuition.pack(expand=True, pady=8)

        # 7. Thao tác: Sửa, Xóa (Centered Action Box)
        c7 = ctk.CTkFrame(self.rows_scroll, fg_color=bg_col, corner_radius=4, height=50)
        c7.grid(row=row_idx, column=7, sticky="nsew", padx=2, pady=1)
        act_box = ctk.CTkFrame(c7, fg_color="transparent")
        act_box.pack(expand=True, pady=8)

        edit_ic = IconLoader.get_icon("edit", size=14, color=Theme.colors.TEXT_SECONDARY)
        btn_edit = IconButton(act_box, icon=edit_ic, size=28, command=lambda stu=s: self._open_edit_student(stu))
        btn_edit.pack(side="left", padx=(0, 4))

        del_ic = IconLoader.get_icon("delete", size=14, color=Theme.colors.DANGER)
        btn_del = IconButton(act_box, icon=del_ic, size=28, command=lambda stu=s: self._confirm_delete_student(stu))
        btn_del.pack(side="left")

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

    def _open_add_student(self) -> None:
        StudentDialog(
            parent=self.winfo_toplevel(),
            student_service=self.student_service,
            class_service=self.class_service,
            schedule_service=self.schedule_service,
            on_saved=self.refresh,
        )

    def _open_edit_student(self, student: StudentResponseDTO) -> None:
        StudentDialog(
            parent=self.winfo_toplevel(),
            student_service=self.student_service,
            class_service=self.class_service,
            schedule_service=self.schedule_service,
            student=student,
            on_saved=self.refresh,
        )

    def _open_quick_adjust_lessons(self, student: StudentResponseDTO) -> None:
        QuickLessonsDialog(
            parent=self.winfo_toplevel(),
            student_service=self.student_service,
            student=student,
            on_saved=self.refresh,
        )

    def _confirm_delete_student(self, student: StudentResponseDTO) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Xóa học sinh",
            message=f"Bạn có chắc muốn xóa học sinh '{student.name}' ({student.phone})? Dữ liệu điểm danh và học phí cũ vẫn được lưu trữ.",
            on_confirm=lambda: self._delete_student(student.id),
        )

    def _delete_student(self, student_id: str) -> None:
        self.student_service.delete_student(student_id)
        ToastManager.show(self.winfo_toplevel(), "Đã xóa học sinh thành công.", level="success")
        self.refresh()
