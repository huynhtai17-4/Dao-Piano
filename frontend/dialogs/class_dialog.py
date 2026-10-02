"""Dialog for adding or updating classes with type-specific editing constraints and weekly slot scheduling."""

from __future__ import annotations
from typing import Optional, Callable, List, Dict
import customtkinter as ctk
from frontend.theme import Theme
from backend.core.enums import ClassType
from backend.application.services.class_service import ClassService
from backend.application.services.schedule_service import ScheduleService
from backend.application.dto.class_dto import ClassCreateDTO, ClassUpdateDTO, ClassResponseDTO
from frontend.components.dialogs import BaseModalDialog
from frontend.components.buttons import PrimaryButton, OutlineButton

WEEKDAY_NAMES = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
WEEKDAY_INDEX_MAP = {name: idx for idx, name in enumerate(WEEKDAY_NAMES)}


class ClassDialog(BaseModalDialog):
    """Modal dialog managing class creation and constraint-compliant updates with recurring slots."""

    def __init__(
        self,
        parent,
        class_service: ClassService,
        class_model: Optional[ClassResponseDTO] = None,
        initial_type: ClassType = ClassType.OFFLINE,
        on_saved: Optional[Callable] = None,
        schedule_service: Optional[ScheduleService] = None,
    ):
        self.class_service = class_service
        self.schedule_service = schedule_service
        self.class_model = class_model
        self.initial_type = class_model.class_type if class_model else initial_type
        self.on_saved = on_saved
        self.slot_widgets: List[Dict] = []
        is_edit = class_model is not None

        super().__init__(
            parent=parent,
            title="Chỉnh sửa lớp học" if is_edit else "Thêm lớp học mới",
            subtitle="Quy định sĩ số, hình thức giảng dạy và xếp lịch suất học cố định",
            width=520,
            height=620,
        )

        self._build_form()

    def _build_form(self) -> None:
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        is_edit = self.class_model is not None
        row = 0

        # 1. Class Type
        ctk.CTkLabel(
            self.scroll_frame, text="Loại lớp:", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).grid(row=row, column=0, sticky="w", pady=8)
        self.opt_type = ctk.CTkOptionMenu(
            self.scroll_frame,
            values=[ClassType.OFFLINE.display_name, ClassType.ONLINE.display_name, ClassType.ONE_ON_ONE.display_name],
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.OCEAN,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_type_changed,
        )
        self.opt_type.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)
        self.opt_type.set(self.initial_type.display_name)

        if is_edit:
            self.opt_type.configure(state="disabled")

        row += 1
        # 2. Class Name
        ctk.CTkLabel(
            self.scroll_frame, text="Tên lớp *:", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).grid(row=row, column=0, sticky="w", pady=8)
        self.entry_name = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="Ví dụ: Lớp Piano Nhí Cơ Bản 1",
            font=Theme.fonts.BODY,
            height=36,
            corner_radius=Theme.radius.INPUT,
        )
        self.entry_name.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)
        if self.class_model:
            self.entry_name.insert(0, self.class_model.name)
            if self.class_model.class_type == ClassType.OFFLINE:
                self.entry_name.configure(state="disabled")

        row += 1
        # 3. Max Students
        ctk.CTkLabel(
            self.scroll_frame, text="Sĩ số tối đa *:", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY
        ).grid(row=row, column=0, sticky="w", pady=8)
        self.entry_max = ctk.CTkEntry(
            self.scroll_frame, font=Theme.fonts.BODY, height=36, corner_radius=Theme.radius.INPUT
        )
        self.entry_max.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=8)

        initial_max = self.class_model.max_students if self.class_model else (1 if self.initial_type == ClassType.ONE_ON_ONE else 6)
        self.entry_max.insert(0, str(initial_max))
        if self.initial_type == ClassType.ONE_ON_ONE:
            self.entry_max.configure(state="disabled")

        row += 1
        # Hint label for rules
        self.lbl_rule_hint = ctk.CTkLabel(
            self.scroll_frame,
            text="* Lớp 1-Kèm-1 luôn có sĩ số tối đa là 1.",
            font=Theme.fonts.CAPTION,
            text_color=Theme.colors.TEXT_MUTED,
            wraplength=460,
            justify="left",
        )
        self.lbl_rule_hint.grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 8))

        row += 1
        # 4. Recurring Slots Section (Schedule for this class)
        self.frame_slots_section = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_slots_section.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self.frame_slots_section.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.frame_slots_section,
            text="🗓️ Suất học trong tuần:",
            font=Theme.fonts.BODY_BOLD,
            text_color=Theme.colors.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", pady=4)

        self.opt_slot_count = ctk.CTkOptionMenu(
            self.frame_slots_section,
            values=["Chưa xếp lịch suất học", "1 buổi / tuần", "2 buổi / tuần", "3 buổi / tuần"],
            font=Theme.fonts.BODY,
            height=32,
            corner_radius=Theme.radius.INPUT,
            fg_color=Theme.colors.BG_CARD,
            button_color=Theme.colors.EMERALD,
            text_color=Theme.colors.TEXT_PRIMARY,
            command=self._on_slot_count_changed,
        )
        self.opt_slot_count.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        self.container_slots = ctk.CTkFrame(self.frame_slots_section, fg_color="transparent")
        self.container_slots.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 4))
        self.container_slots.grid_columnconfigure(0, weight=1)

        # Inline error label
        self.lbl_error = ctk.CTkLabel(self.footer, text="", font=Theme.fonts.CAPTION_BOLD, text_color=Theme.colors.DANGER, wraplength=280, justify="left")
        self.lbl_error.pack(side="left", padx=4)

        # Buttons
        btn_cancel = OutlineButton(self.footer, text="Hủy", command=self.destroy, width=90)
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = PrimaryButton(self.footer, text="Lưu lớp học", command=self._save, width=120)
        btn_save.pack(side="right")

        self._init_slots()
        self._update_rule_hint()

    def _init_slots(self) -> None:
        """Load existing class recurring slots if editing."""
        if self.class_model and self.schedule_service:
            existing = self.schedule_service.get_class_recurring_slots(self.class_model.id)
            if existing:
                cnt = min(3, len(existing))
                self.opt_slot_count.set(f"{cnt} buổi / tuần")
                self._render_slot_inputs(existing)
                return

        # Default for new offline class: 2 sessions per week
        if not self.class_model and self.initial_type == ClassType.OFFLINE:
            self.opt_slot_count.set("2 buổi / tuần")
            self._render_slot_inputs()
        else:
            self.opt_slot_count.set("Chưa xếp lịch suất học")

    def _on_slot_count_changed(self, _=None) -> None:
        self._render_slot_inputs()

    def _render_slot_inputs(self, prefill: Optional[List[dict]] = None) -> None:
        for child in self.container_slots.winfo_children():
            child.destroy()
        self.slot_widgets.clear()

        choice = self.opt_slot_count.get()
        if "Chưa xếp lịch" in choice:
            return

        try:
            count = int(choice.split(" ")[0])
        except Exception:
            count = 2

        default_days = ["Thứ 2", "Thứ 5", "Thứ 4", "Thứ 7"]
        default_times = [("17:30", "19:00"), ("17:30", "19:00"), ("19:00", "20:30")]

        for i in range(count):
            card = ctk.CTkFrame(
                self.container_slots,
                fg_color=Theme.colors.BG_MUTED,
                border_color=Theme.colors.BORDER_SUBTLE,
                border_width=1,
                corner_radius=8,
            )
            card.pack(fill="x", pady=4)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=8, pady=4)

            init_day = default_days[i % len(default_days)]
            init_st = default_times[i % len(default_times)][0]
            init_et = default_times[i % len(default_times)][1]
            init_loc = "Phòng học 1"

            if prefill and i < len(prefill):
                init_day = prefill[i].get("day_name", init_day)
                init_st = prefill[i].get("start_time", init_st)
                init_et = prefill[i].get("end_time", init_et)
                init_loc = prefill[i].get("location", init_loc)

            lbl = ctk.CTkLabel(top, text=f"Suất {i + 1}:", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY)
            lbl.pack(side="left", padx=(0, 8))

            opt_day = ctk.CTkOptionMenu(
                top,
                values=WEEKDAY_NAMES,
                font=Theme.fonts.BODY,
                height=30,
                corner_radius=Theme.radius.INPUT,
                fg_color=Theme.colors.BG_CARD,
                button_color=Theme.colors.EMERALD,
                text_color=Theme.colors.TEXT_PRIMARY,
                width=110,
            )
            opt_day.pack(side="left", padx=(0, 8))
            opt_day.set(init_day)

            ctk.CTkLabel(top, text="Từ:", font=Theme.fonts.CAPTION, text_color=Theme.colors.TEXT_MUTED).pack(side="left", padx=(0, 4))
            entry_st = ctk.CTkEntry(top, font=Theme.fonts.BODY, width=64, height=30, corner_radius=Theme.radius.INPUT)
            entry_st.pack(side="left")
            entry_st.insert(0, init_st)

            ctk.CTkLabel(top, text="đến", font=Theme.fonts.CAPTION, text_color=Theme.colors.TEXT_MUTED).pack(side="left", padx=4)

            entry_et = ctk.CTkEntry(top, font=Theme.fonts.BODY, width=64, height=30, corner_radius=Theme.radius.INPUT)
            entry_et.pack(side="left", padx=(0, 6))
            entry_et.insert(0, init_et)

            self.slot_widgets.append({
                "opt_day": opt_day,
                "entry_st": entry_st,
                "entry_et": entry_et,
            })

    def _on_type_changed(self, choice: str) -> None:
        if choice == ClassType.ONE_ON_ONE.display_name:
            self.entry_max.configure(state="normal")
            self.entry_max.delete(0, "end")
            self.entry_max.insert(0, "1")
            self.entry_max.configure(state="disabled")
            self.frame_slots_section.grid_remove()
        else:
            self.entry_max.configure(state="normal")
            if self.entry_max.get() == "1":
                self.entry_max.delete(0, "end")
                self.entry_max.insert(0, "6")
            self.frame_slots_section.grid()
        self._update_rule_hint()

    def _update_rule_hint(self) -> None:
        choice = self.opt_type.get()
        if self.class_model and self.class_model.class_type == ClassType.OFFLINE:
            self.lbl_rule_hint.configure(text="* Quy tắc: Lớp Offline chỉ cho phép sửa sĩ số tối đa, không thể đổi tên.")
        elif choice == ClassType.ONE_ON_ONE.display_name:
            self.lbl_rule_hint.configure(text="* Quy tắc: Lớp 1-Kèm-1 luôn cố định sĩ số tối đa = 1.")
        else:
            self.lbl_rule_hint.configure(text="* Lớp học nhóm cho phép điều chỉnh sĩ số theo phòng và các suất học.")

    def _save(self) -> None:
        self.lbl_error.configure(text="")
        name = self.entry_name.get().strip()
        if not name:
            self.lbl_error.configure(text="Tên lớp học không được để trống.")
            return

        type_str = self.opt_type.get()
        type_map = {
            ClassType.ONE_ON_ONE.display_name: ClassType.ONE_ON_ONE,
            ClassType.OFFLINE.display_name: ClassType.OFFLINE,
            ClassType.ONLINE.display_name: ClassType.ONLINE,
        }
        class_type = type_map.get(type_str, ClassType.OFFLINE)

        try:
            max_stu = int(self.entry_max.get().strip())
            if max_stu <= 0:
                self.lbl_error.configure(text="Sĩ số tối đa phải lớn hơn 0.")
                return
        except ValueError:
            self.lbl_error.configure(text="Sĩ số tối đa phải là số nguyên.")
            return

        # Validate slots if any
        parsed_slots = []
        from backend.core.time_utils import validate_time_format, time_to_minutes
        for w in self.slot_widgets:
            d_name = w["opt_day"].get()
            d_idx = WEEKDAY_INDEX_MAP.get(d_name, 0)
            st = w["entry_st"].get().strip()
            et = w["entry_et"].get().strip()
            loc = "Phòng học"

            if not validate_time_format(st) or not validate_time_format(et):
                self.lbl_error.configure(text=f"Giờ học '{st} - {et}' không đúng định dạng HH:MM.")
                return
            if time_to_minutes(et) <= time_to_minutes(st):
                self.lbl_error.configure(text="Giờ kết thúc phải sau giờ bắt đầu.")
                return
            parsed_slots.append({
                "day_idx": d_idx,
                "start_time": st,
                "end_time": et,
                "location": loc,
            })

        try:
            if self.class_model:
                dto_update = ClassUpdateDTO(
                    id=self.class_model.id,
                    name=name,
                    class_type=class_type,
                    max_students=max_stu,
                )
                saved_class = self.class_service.update_class(dto_update)
            else:
                dto_create = ClassCreateDTO(
                    name=name,
                    class_type=class_type,
                    max_students=max_stu,
                )
                saved_class = self.class_service.create_class(dto_create)

            # Generate/update recurring schedules for class if schedule_service available
            if self.schedule_service and parsed_slots:
                # Remove future unstarted schedules for this class before regenerating
                from backend.core.dates import today_str
                from backend.core.enums import ScheduleStatus
                today_s = today_str()
                existing_s = self.schedule_service.schedule_repo.get_by_class_id(saved_class.id)
                for s in existing_s:
                    if s.date >= today_s and s.status == ScheduleStatus.SCHEDULED:
                        self.schedule_service.delete_schedule(s.id)

                self.schedule_service.create_class_recurring_schedules(
                    saved_class.id, parsed_slots, num_weeks=8
                )

            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.lbl_error.configure(text=str(e))
