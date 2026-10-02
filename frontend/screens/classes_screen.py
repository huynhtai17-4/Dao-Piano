"""Class management screen organized into 3 instructional groups."""

from __future__ import annotations
from typing import List
import customtkinter as ctk
from frontend.theme import Theme
from backend.core.enums import ClassType
from backend.core.event_bus import event_bus
from backend.application.services.class_service import ClassService
from backend.application.services.student_service import StudentService
from backend.application.dto.class_dto import ClassResponseDTO
from frontend.components.cards import GlassCard
from frontend.components.buttons import PrimaryButton, IconButton
from frontend.components.badges import Badge
from frontend.components.icon_loader import IconLoader
from frontend.components.dialogs import ConfirmDialog
from frontend.components.toast import ToastManager
from frontend.dialogs.class_dialog import ClassDialog


class ClassesScreen(ctk.CTkFrame):
    """Overview and management of classrooms grouped by Online, Offline, and 1-on-1."""

    def __init__(
        self,
        master,
        class_service: ClassService,
        student_service: StudentService,
        schedule_service: Optional[ScheduleService] = None,
        **kwargs,
    ):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self.class_service = class_service
        self.student_service = student_service
        self.schedule_service = schedule_service

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_scroll_area()

        self._refresh_timer = None
        self._dirty = False

        event_bus.subscribe("classes_changed", self._on_data_invalidated)
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

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        lbl_desc = ctk.CTkLabel(
            header,
            text="Quản lý cấu trúc đào tạo và chỉ tiêu sĩ số từng lớp",
            font=Theme.fonts.BODY,
            text_color=Theme.colors.TEXT_SECONDARY,
        )
        lbl_desc.grid(row=0, column=0, sticky="w")

        plus_icon = IconLoader.get_icon("plus", size=16, color=Theme.colors.TEXT_WHITE)
        btn_add = PrimaryButton(
            header,
            text="Thêm lớp học",
            icon=plus_icon,
            command=self._open_add_class,
            width=140,
            height=36,
        )
        btn_add.grid(row=0, column=1, sticky="e")

    def _build_scroll_area(self) -> None:
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.scroll.grid_columnconfigure(0, weight=1)

    def refresh(self) -> None:
        for w in self.scroll.winfo_children():
            w.destroy()

        classes = self.class_service.get_classes()
        groups = {
            ClassType.ONE_ON_ONE: [c for c in classes if c.class_type == ClassType.ONE_ON_ONE],
            ClassType.OFFLINE: [c for c in classes if c.class_type == ClassType.OFFLINE],
            ClassType.ONLINE: [c for c in classes if c.class_type == ClassType.ONLINE],
        }

        # Render sections
        self._render_group_section("1 KÈM 1 (CÁ NHÂN HÓA)", groups[ClassType.ONE_ON_ONE], ClassType.ONE_ON_ONE)
        self._render_group_section("LỚP OFFLINE (TẠI TRUNG TÂM)", groups[ClassType.OFFLINE], ClassType.OFFLINE)
        self._render_group_section("LỚP ONLINE (TỪ XA)", groups[ClassType.ONLINE], ClassType.ONLINE)

    def _render_group_section(self, title: str, class_list: List[ClassResponseDTO], class_type: ClassType) -> None:
        section = ctk.CTkFrame(self.scroll, fg_color="transparent")
        section.pack(fill="x", pady=(0, 18))

        # Title bar
        lbl_sec = ctk.CTkLabel(
            section,
            text=f"{title} ({len(class_list)})",
            font=Theme.fonts.H2,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        lbl_sec.pack(anchor="w", padx=4, pady=(0, 8))

        # Grid of cards
        grid_frame = ctk.CTkFrame(section, fg_color="transparent")
        grid_frame.pack(fill="x")
        grid_frame.grid_columnconfigure((0, 1, 2), weight=1)

        if not class_list:
            lbl_empty = ctk.CTkLabel(
                grid_frame,
                text="Chưa có lớp học nào trong danh mục này.",
                font=Theme.fonts.CAPTION,
                text_color=Theme.colors.TEXT_MUTED,
            )
            lbl_empty.grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=8)
            return

        for idx, c in enumerate(class_list):
            row = idx // 3
            col = idx % 3
            self._render_class_card(grid_frame, c, row, col)

    def _render_class_card(self, parent: ctk.CTkFrame, c: ClassResponseDTO, row: int, col: int) -> None:
        card = GlassCard(parent)
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        # Header row: Class Name + Badge
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(14, 4))

        lbl_name = ctk.CTkLabel(
            top_row,
            text=c.name,
            font=Theme.fonts.H2,
            text_color=Theme.colors.TEXT_PRIMARY,
            anchor="w",
        )
        lbl_name.pack(side="left")

        badge = Badge.for_class_type(top_row, c.class_type)
        badge.pack(side="right")

        # Capacity Indicator
        cap_frame = ctk.CTkFrame(card, fg_color="transparent")
        cap_frame.pack(fill="x", padx=14, pady=4)

        ratio = c.current_student_count / max(1, c.max_students)
        lbl_cap = ctk.CTkLabel(
            cap_frame,
            text=f"Sĩ số: {c.current_student_count}/{c.max_students} học sinh",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.DANGER_TEXT if c.is_full else Theme.colors.TEXT_SECONDARY,
        )
        lbl_cap.pack(side="left")

        if c.is_full:
            lbl_full = ctk.CTkLabel(
                cap_frame,
                text="ĐÃ ĐẦY",
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.DANGER_TEXT,
            )
            lbl_full.pack(side="right")

        # Progress bar
        bar = ctk.CTkProgressBar(card, height=8, corner_radius=4)
        bar.pack(fill="x", padx=14, pady=6)
        bar.set(ratio)
        bar.configure(
            progress_color=Theme.colors.DANGER if c.is_full else Theme.colors.EMERALD,
            fg_color=Theme.colors.BG_MUTED,
        )

        # Recurring Slots indicator if available
        slots_text = None
        if self.schedule_service:
            slots = self.schedule_service.get_class_recurring_slots(c.id)
            if slots:
                slots_str = ", ".join(f"{s['day_name']} ({s['start_time']}-{s['end_time']})" for s in slots)
                slots_text = f"🗓️ Suất học: {slots_str}"

        if slots_text:
            lbl_slots = ctk.CTkLabel(
                card,
                text=slots_text,
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.OCEAN,
                anchor="w",
                wraplength=220,
                justify="left",
            )
            lbl_slots.pack(fill="x", padx=14, pady=(2, 4))

        # Enrolled Students list
        students = self.student_service.get_students(class_id=c.id)
        if students:
            s_names = ", ".join(s.name for s in students[:3])
            if len(students) > 3:
                s_names += f" và {len(students) - 3} bạn khác..."
            txt_roster = f"Học viên: {s_names}"
        else:
            txt_roster = "Chưa có học viên nào ghi danh."

        lbl_roster = ctk.CTkLabel(
            card,
            text=txt_roster,
            font=Theme.fonts.CAPTION,
            text_color=Theme.colors.TEXT_MUTED,
            anchor="w",
            wraplength=220,
            justify="left",
        )
        lbl_roster.pack(fill="x", padx=14, pady=(2, 10))

        # Bottom Actions: Edit and Delete
        action_bar = ctk.CTkFrame(card, fg_color="transparent")
        action_bar.pack(fill="x", padx=14, pady=(0, 14))

        edit_ic = IconLoader.get_icon("edit", size=14, color=Theme.colors.TEXT_SECONDARY)
        btn_edit = ctk.CTkButton(
            action_bar,
            text=" Chỉnh sửa",
            image=edit_ic,
            compound="left",
            font=Theme.fonts.CAPTION_BOLD,
            height=28,
            fg_color=Theme.colors.BG_CARD,
            hover_color=Theme.colors.BG_CARD_HOVER,
            border_width=1,
            border_color=Theme.colors.BORDER_SUBTLE,
            text_color=Theme.colors.TEXT_PRIMARY,
            corner_radius=6,
            command=lambda cl=c: self._open_edit_class(cl),
        )
        btn_edit.pack(side="left", padx=(0, 6))

        del_ic = IconLoader.get_icon("delete", size=14, color=Theme.colors.DANGER)
        btn_del = IconButton(
            action_bar,
            icon=del_ic,
            size=28,
            command=lambda cl=c: self._confirm_delete_class(cl),
        )
        btn_del.pack(side="left")

    def _open_add_class(self) -> None:
        ClassDialog(
            parent=self.winfo_toplevel(),
            class_service=self.class_service,
            schedule_service=self.schedule_service,
            on_saved=self.refresh,
        )

    def _open_edit_class(self, c: ClassResponseDTO) -> None:
        ClassDialog(
            parent=self.winfo_toplevel(),
            class_service=self.class_service,
            class_model=c,
            schedule_service=self.schedule_service,
            on_saved=self.refresh,
        )

    def _confirm_delete_class(self, c: ClassResponseDTO) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Xóa lớp học",
            message=f"Bạn có chắc muốn xóa lớp '{c.name}'? Các học sinh trong lớp sẽ được chuyển về trạng thái tự do.",
            on_confirm=lambda: self._delete_class(c.id),
        )

    def _delete_class(self, class_id: str) -> None:
        self.class_service.delete_class(class_id)
        ToastManager.show(self.winfo_toplevel(), "Đã xóa lớp học thành công.", level="success")
        self.refresh()
