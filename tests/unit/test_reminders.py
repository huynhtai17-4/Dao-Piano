"""Unit tests for ReminderService alert generation."""

import tempfile
from backend.core.enums import ReminderSeverity, ReminderType
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.application.services.student_service import StudentService
from backend.application.services.reminder_service import ReminderService
from backend.application.dto.student_dto import StudentCreateDTO


def test_reminders_detect_low_and_zero_balance():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        stu_repo = JsonStudentRepository(storage)
        sch_repo = JsonScheduleRepository(storage)
        cls_repo = JsonClassRepository(storage)

        s_svc = StudentService(stu_repo, cls_repo)
        r_svc = ReminderService(stu_repo, sch_repo)

        # Student with 0 lessons
        s_svc.create_student(StudentCreateDTO(name="Học sinh Hết Buổi", phone="0911111111", remaining_lessons=0))
        # Student with 2 lessons
        s_svc.create_student(StudentCreateDTO(name="Học sinh Sắp Hết", phone="0922222222", remaining_lessons=2))
        # Student with 8 lessons
        s_svc.create_student(StudentCreateDTO(name="Học sinh Đủ Buổi", phone="0933333333", remaining_lessons=8))

        reminders = r_svc.get_all_reminders()
        assert len(reminders) >= 2

        # 1st must be CRITICAL (0 lessons)
        assert reminders[0].severity == ReminderSeverity.CRITICAL
        assert reminders[0].type == ReminderType.NO_LESSONS

        # 2nd must be WARNING (2 lessons)
        assert reminders[1].severity == ReminderSeverity.WARNING
        assert reminders[1].type == ReminderType.LOW_LESSONS
