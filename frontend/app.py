"""Main CustomTkinter desktop application window shell."""

from __future__ import annotations
import customtkinter as ctk

from backend.config.constants import APP_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from frontend.theme import Theme
from backend.config.app_config import AppConfig
from backend.infrastructure.storage.backup_manager import BackupManager
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.services.schedule_service import ScheduleService
from backend.application.services.attendance_service import AttendanceService
from backend.application.services.payment_service import PaymentService
from backend.application.services.reminder_service import ReminderService
from backend.application.services.dashboard_service import DashboardService
from backend.application.services.holiday_service import HolidayService
from frontend.components.sidebar import Sidebar
from frontend.components.topbar import Topbar
from frontend.router import ViewRouter
from frontend.screens.calendar_screen import CalendarScreen
from frontend.screens.students_screen import StudentsScreen
from frontend.screens.classes_screen import ClassesScreen
from frontend.screens.settings_screen import SettingsScreen


class PianoApp(ctk.CTk):
    """Main desktop application window with responsive shell and view routing."""

    def __init__(
        self,
        student_service: StudentService,
        class_service: ClassService,
        schedule_service: ScheduleService,
        attendance_service: AttendanceService,
        payment_service: PaymentService,
        reminder_service: ReminderService,
        dashboard_service: DashboardService,
        holiday_service: HolidayService,
        app_config: AppConfig,
        backup_manager: BackupManager,
    ) -> None:
        super().__init__()

        self.student_service = student_service
        self.class_service = class_service
        self.schedule_service = schedule_service
        self.attendance_service = attendance_service
        self.payment_service = payment_service
        self.reminder_service = reminder_service
        self.dashboard_service = dashboard_service
        self.holiday_service = holiday_service
        self.app_config = app_config
        self.backup_manager = backup_manager

        self._configure_window()
        self._build_layout()
        self._initialize_router()

    def _configure_window(self) -> None:
        ctk.set_appearance_mode(self.app_config.theme_mode)
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=Theme.colors.BG_WINDOW)

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Floating Left Sidebar
        self.sidebar = Sidebar(
            master=self,
            on_navigate=self._on_navigate,
            active_route="calendar",
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(16, 0), pady=16)

        # 2. Main Work Area (Topbar + Content Area)
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        # Topbar
        self.topbar = Topbar(self.main_area, center_name=self.app_config.center_name)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        # View Screen Container
        self.content_container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

    def _initialize_router(self) -> None:
        self.router = ViewRouter(self.content_container)

        # 1. Calendar Screen
        calendar_screen = CalendarScreen(
            master=self.content_container,
            schedule_service=self.schedule_service,
            reminder_service=self.reminder_service,
            student_service=self.student_service,
            class_service=self.class_service,
            attendance_service=self.attendance_service,
            payment_service=self.payment_service,
            holiday_service=self.holiday_service,
        )
        self.router.register("calendar", calendar_screen)

        # 2. Students & Tuition Unified Screen
        students_screen = StudentsScreen(
            master=self.content_container,
            student_service=self.student_service,
            class_service=self.class_service,
            payment_service=self.payment_service,
            dashboard_service=self.dashboard_service,
            schedule_service=self.schedule_service,
        )
        self.router.register("students", students_screen)
        self.router.register("payments", students_screen)

        # 3. Classes Screen
        classes_screen = ClassesScreen(
            master=self.content_container,
            class_service=self.class_service,
            student_service=self.student_service,
            schedule_service=self.schedule_service,
        )
        self.router.register("classes", classes_screen)

        # 4. Settings Screen
        settings_screen = SettingsScreen(
            master=self.content_container,
            app_config=self.app_config,
            backup_manager=self.backup_manager,
            on_settings_updated=self._on_settings_changed,
        )
        self.router.register("settings", settings_screen)

        # Show initial screen
        self._on_navigate("calendar")

    def _on_navigate(self, route_id: str) -> None:
        title_map = {
            "calendar": "Lịch trình dạy",
            "students": "Học sinh & Học phí",
            "classes": "Danh sách lớp học",
            "payments": "Học sinh & Học phí",
            "settings": "Cài đặt & Sao lưu hệ thống",
        }
        self.topbar.set_title(title_map.get(route_id, "Piano Studio"))
        self.sidebar.set_active(route_id)
        self.router.navigate(route_id)

    def _on_settings_changed(self) -> None:
        self.topbar.set_center_name(self.app_config.center_name)
