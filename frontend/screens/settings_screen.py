"""Settings and Local Backup Recovery Management screen."""

from __future__ import annotations
import customtkinter as ctk
from frontend.theme import Theme
from backend.config.app_config import AppConfig
from backend.infrastructure.storage.backup_manager import BackupManager
from frontend.components.cards import GlassCard
from frontend.components.buttons import PrimaryButton, OutlineButton, DangerButton
from frontend.components.icon_loader import IconLoader
from frontend.components.toast import ToastManager
from frontend.components.dialogs import ConfirmDialog


class SettingsScreen(ctk.CTkFrame):
    """Studio profile configuration and production-grade local backup/restore panel."""

    def __init__(
        self,
        master,
        app_config: AppConfig,
        backup_manager: BackupManager,
        on_settings_updated: None | callable = None,
        **kwargs,
    ):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self.app_config = app_config
        self.backup_manager = backup_manager
        self.on_settings_updated = on_settings_updated

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        self._build_profile_card()
        self._build_backup_card()

        self.refresh()

    def _build_profile_card(self) -> None:
        self.card_profile = GlassCard(self)
        self.card_profile.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))

        # Title
        lbl_head = ctk.CTkLabel(
            self.card_profile,
            text="THÔNG TIN TRUNG TÂM & CẤU HÌNH",
            font=Theme.fonts.H2,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        lbl_head.pack(anchor="w", padx=20, pady=(20, 14))

        # Form fields
        form = ctk.CTkFrame(self.card_profile, fg_color="transparent")
        form.pack(fill="x", padx=20)
        form.grid_columnconfigure(1, weight=1)

        row = 0
        # 1. Center Name
        ctk.CTkLabel(form, text="Tên Trung tâm / Studio", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=10)
        self.entry_center = ctk.CTkEntry(form, height=36, corner_radius=Theme.radius.INPUT, font=Theme.fonts.BODY)
        self.entry_center.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=10)

        row += 1
        # 2. Teacher Name
        ctk.CTkLabel(form, text="Giáo viên phụ trách", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=10)
        self.entry_teacher = ctk.CTkEntry(form, height=36, corner_radius=Theme.radius.INPUT, font=Theme.fonts.BODY)
        self.entry_teacher.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=10)

        row += 1
        # 3. Phone
        ctk.CTkLabel(form, text="Số điện thoại liên hệ", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=10)
        self.entry_phone = ctk.CTkEntry(form, height=36, corner_radius=Theme.radius.INPUT, font=Theme.fonts.BODY)
        self.entry_phone.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=10)

        row += 1
        # 4. Default Duration
        ctk.CTkLabel(form, text="Thời lượng buổi học (phút)", font=Theme.fonts.BODY_BOLD, text_color=Theme.colors.TEXT_PRIMARY).grid(row=row, column=0, sticky="w", pady=10)
        self.entry_duration = ctk.CTkEntry(form, height=36, corner_radius=Theme.radius.INPUT, font=Theme.fonts.BODY)
        self.entry_duration.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=10)

        # Save Button
        btn_save = PrimaryButton(self.card_profile, text="Lưu cấu hình", command=self._save_profile, width=140)
        btn_save.pack(anchor="w", padx=20, pady=20)

    def _build_backup_card(self) -> None:
        self.card_backup = GlassCard(self)
        self.card_backup.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        self.card_backup.grid_rowconfigure(2, weight=1)
        self.card_backup.grid_columnconfigure(0, weight=1)

        # Header
        head_box = ctk.CTkFrame(self.card_backup, fg_color="transparent")
        head_box.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        head_box.grid_columnconfigure(0, weight=1)

        lbl_head = ctk.CTkLabel(
            head_box,
            text="SAO LƯU & PHỤC HỒI DỮ LIỆU",
            font=Theme.fonts.H2,
            text_color=Theme.colors.TEXT_PRIMARY,
        )
        lbl_head.grid(row=0, column=0, sticky="w")

        # Snapshot button
        btn_snapshot = PrimaryButton(
            head_box,
            text="Tạo bản sao lưu ngay",
            command=self._create_backup,
            width=160,
            height=34,
        )
        btn_snapshot.grid(row=0, column=1, sticky="e")

        lbl_sub = ctk.CTkLabel(
            self.card_backup,
            text="Dữ liệu JSON được sao lưu an toàn độc lập trước mọi thao tác ghi quan trọng.",
            font=Theme.fonts.CAPTION,
            text_color=Theme.colors.TEXT_SECONDARY,
        )
        lbl_sub.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        # Backup History Scroll Frame
        self.backup_scroll = ctk.CTkScrollableFrame(self.card_backup, fg_color=Theme.colors.BG_MUTED, corner_radius=10)
        self.backup_scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

    def refresh(self) -> None:
        # Load profile settings
        self.entry_center.delete(0, "end")
        self.entry_center.insert(0, self.app_config.center_name)

        self.entry_teacher.delete(0, "end")
        self.entry_teacher.insert(0, self.app_config.teacher_name)

        self.entry_phone.delete(0, "end")
        self.entry_phone.insert(0, self.app_config.phone)

        self.entry_duration.delete(0, "end")
        self.entry_duration.insert(0, str(self.app_config.get("default_lesson_duration", 60)))

        self._render_backup_list()

    def _render_backup_list(self) -> None:
        for w in self.backup_scroll.winfo_children():
            w.destroy()

        backups = self.backup_manager.list_backups()
        if not backups:
            lbl_empty = ctk.CTkLabel(
                self.backup_scroll,
                text="Chưa có bản sao lưu nào được tạo.",
                font=Theme.fonts.BODY,
                text_color=Theme.colors.TEXT_MUTED,
            )
            lbl_empty.pack(pady=30)
            return

        for b in backups:
            item_frame = ctk.CTkFrame(self.backup_scroll, fg_color=Theme.colors.BG_CARD, corner_radius=8)
            item_frame.pack(fill="x", padx=6, pady=4)

            info_box = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_box.pack(side="left", padx=12, pady=10)

            lbl_time = ctk.CTkLabel(
                info_box,
                text=b["folder_name"],
                font=Theme.fonts.BODY_BOLD,
                text_color=Theme.colors.TEXT_PRIMARY,
                anchor="w",
            )
            lbl_time.pack(anchor="w")

            lbl_meta = ctk.CTkLabel(
                info_box,
                text=f"Lý do: {b['reason']} • {b['files_count']} files",
                font=Theme.fonts.CAPTION,
                text_color=Theme.colors.TEXT_SECONDARY,
                anchor="w",
            )
            lbl_meta.pack(anchor="w")

            btn_restore = OutlineButton(
                item_frame,
                text="Khôi phục",
                height=30,
                width=90,
                command=lambda bname=b["folder_name"]: self._confirm_restore(bname),
            )
            btn_restore.pack(side="right", padx=12, pady=10)

    def _save_profile(self) -> None:
        try:
            duration = int(self.entry_duration.get().strip())
        except ValueError:
            duration = 60

        new_settings = {
            "center_name": self.entry_center.get().strip(),
            "teacher_name": self.entry_teacher.get().strip(),
            "phone": self.entry_phone.get().strip(),
            "default_lesson_duration": duration,
        }
        self.app_config.update(new_settings)
        ToastManager.show(self.winfo_toplevel(), "Đã lưu thông tin cấu hình studio!", level="success")
        if self.on_settings_updated:
            self.on_settings_updated()

    def _create_backup(self) -> None:
        try:
            self.backup_manager.create_backup(reason="manual_user")
            ToastManager.show(self.winfo_toplevel(), "Đã tạo bản sao lưu thành công!", level="success")
            self._render_backup_list()
        except Exception as e:
            ToastManager.show(self.winfo_toplevel(), f"Lỗi tạo sao lưu: {e}", level="error")

    def _confirm_restore(self, folder_name: str) -> None:
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Khôi phục dữ liệu",
            message=f"Bạn có chắc muốn khôi phục dữ liệu từ bản sao lưu '{folder_name}'? Dữ liệu hiện tại sẽ được tự động sao lưu an toàn trước khi thay thế.",
            confirm_text="Xác nhận khôi phục",
            on_confirm=lambda: self._restore_backup(folder_name),
        )

    def _restore_backup(self, folder_name: str) -> None:
        try:
            self.backup_manager.restore_backup(folder_name)
            ToastManager.show(self.winfo_toplevel(), "Đã khôi phục dữ liệu an toàn thành công!", level="success")
            self.refresh()
            if self.on_settings_updated:
                self.on_settings_updated()
        except Exception as e:
            ToastManager.show(self.winfo_toplevel(), f"Lỗi khôi phục: {e}", level="error")
