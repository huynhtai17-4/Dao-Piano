"""Application entry point for Piano Center Manager."""

from __future__ import annotations
import sys
import logging
from pathlib import Path

# Add project root to sys.path to guarantee clean imports across platforms
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.storage.data_initializer import DataInitializer
from backend.infrastructure.storage.backup_manager import BackupManager
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.infrastructure.repositories.json_attendance_repository import JsonAttendanceRepository
from backend.infrastructure.repositories.json_payment_repository import JsonPaymentRepository
from backend.infrastructure.repositories.json_holiday_repository import JsonHolidayRepository
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.services.schedule_service import ScheduleService
from backend.application.services.attendance_service import AttendanceService
from backend.application.services.payment_service import PaymentService
from backend.application.services.reminder_service import ReminderService
from backend.application.services.dashboard_service import DashboardService
from backend.application.services.holiday_service import HolidayService
from backend.config.app_config import AppConfig
from frontend.app import PianoApp


def setup_logging() -> None:
    """Configure technical loggers and ensure logs directory exists."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_dir / "app.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        encoding="utf-8",
    )


def create_app() -> PianoApp:
    """Bootstrap storage, repositories, services, and construct the presentation shell."""
    # 1. Setup local logging
    setup_logging()
    logging.info("Starting Piano Center Manager bootstrap...")

    # 2. Infrastructure Storage & Initializer
    storage = JsonStorage(data_dir=PROJECT_ROOT / "data")
    initializer = DataInitializer(storage)
    initializer.initialize()

    # 3. Backup Manager & App Config
    backup_manager = BackupManager(
        data_dir=PROJECT_ROOT / "data",
        backup_dir=PROJECT_ROOT / "backups",
    )
    app_config = AppConfig(storage)

    # 4. Repositories
    student_repo = JsonStudentRepository(storage)
    class_repo = JsonClassRepository(storage)
    schedule_repo = JsonScheduleRepository(storage)
    attendance_repo = JsonAttendanceRepository(storage)
    payment_repo = JsonPaymentRepository(storage)
    holiday_repo = JsonHolidayRepository(storage)

    # 5. Application Services
    student_service = StudentService(student_repo, class_repo, schedule_repo)
    class_service = ClassService(class_repo, student_repo, schedule_repo)
    schedule_service = ScheduleService(schedule_repo, student_repo, class_repo, attendance_repo=attendance_repo)
    attendance_service = AttendanceService(attendance_repo, student_repo, schedule_repo)
    payment_service = PaymentService(payment_repo, student_repo)
    reminder_service = ReminderService(student_repo, schedule_repo)
    dashboard_service = DashboardService(student_repo, class_repo, schedule_repo, payment_repo)
    holiday_service = HolidayService(holiday_repo, schedule_repo)

    # 6. Instantiate Presentation Application
    app = PianoApp(
        student_service=student_service,
        class_service=class_service,
        schedule_service=schedule_service,
        attendance_service=attendance_service,
        payment_service=payment_service,
        reminder_service=reminder_service,
        dashboard_service=dashboard_service,
        holiday_service=holiday_service,
        app_config=app_config,
        backup_manager=backup_manager,
    )

    logging.info("Bootstrap completed successfully.")
    return app


def main() -> None:
    """Main execution function."""
    try:
        app = create_app()
        app.mainloop()
    except Exception as e:
        logging.critical(f"Fatal application error: {e}", exc_info=True)
        print(f"[FATAL ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
