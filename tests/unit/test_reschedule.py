"""Unit tests for offline rescheduling, upcoming sessions, and new class creation constraints."""

import tempfile
import pytest
from backend.core.enums import ClassType
from backend.core.time_utils import is_time_overlap
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.application.services.class_service import ClassService
from backend.application.services.schedule_service import ScheduleService
from backend.application.dto.class_dto import ClassCreateDTO
from backend.application.dto.schedule_dto import ScheduleCreateDTO
from frontend.dialogs.reschedule_dialog import get_upcoming_sessions_for_class


def test_reschedule_class_filtering_rules():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        cls_repo = JsonClassRepository(storage)
        stu_repo = JsonStudentRepository(storage)
        sch_repo = JsonScheduleRepository(storage)

        class_svc = ClassService(cls_repo, stu_repo)

        # 1. Offline Class A: Full (max_students=2, student_ids=["s1", "s2"])
        c_full = class_svc.create_class(
            ClassCreateDTO(name="Lớp Offline Đầy", class_type=ClassType.OFFLINE, max_students=2)
        )
        model_full = cls_repo.get_by_id(c_full.id)
        model_full.student_ids = ["s1", "s2"]
        cls_repo.update(model_full)

        # 2. Offline Class B: Available (max_students=4, student_ids=["s3"])
        c_avail = class_svc.create_class(
            ClassCreateDTO(name="Lớp Offline Còn Chỗ", class_type=ClassType.OFFLINE, max_students=4)
        )
        model_avail = cls_repo.get_by_id(c_avail.id)
        model_avail.student_ids = ["s3"]
        cls_repo.update(model_avail)

        # 3. Online Class C (Must be excluded from offline reschedule)
        class_svc.create_class(
            ClassCreateDTO(name="Lớp Online Nhóm", class_type=ClassType.ONLINE, max_students=6)
        )

        # Query only OFFLINE classes
        offline_classes = class_svc.get_classes(class_type=ClassType.OFFLINE)
        assert len(offline_classes) == 2

        # Verify capacity check
        full_names = [c.name for c in offline_classes if c.current_student_count >= c.max_students]
        avail_names = [c.name for c in offline_classes if c.current_student_count < c.max_students]

        assert "Lớp Offline Đầy" in full_names
        assert "Lớp Offline Còn Chỗ" in avail_names


def test_get_upcoming_sessions_for_class():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        cls_repo = JsonClassRepository(storage)
        stu_repo = JsonStudentRepository(storage)
        sch_repo = JsonScheduleRepository(storage)
        sch_svc = ScheduleService(sch_repo, stu_repo, cls_repo)

        # Create schedule for class on Monday 2026-09-28 17:30 - 19:00
        sch_svc.create_schedule(
            ScheduleCreateDTO(
                class_id="cls_test_off",
                date="2026-09-28",
                start_time="17:30",
                end_time="19:00",
                location="Phòng Học 2",
                lesson_title="Lớp Offline Test",
            )
        )

        sessions = get_upcoming_sessions_for_class(sch_repo, "cls_test_off", "2026-09-28")
        assert len(sessions) > 0

        # Nearest session to 2026-09-28
        first_s = sessions[0]
        assert first_s["start_time"] == "17:30"
        assert first_s["end_time"] == "19:00"
        assert first_s["location"] == "Phòng Học 2"


def test_new_class_strict_conflict_check():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        cls_repo = JsonClassRepository(storage)
        stu_repo = JsonStudentRepository(storage)
        sch_repo = JsonScheduleRepository(storage)
        sch_svc = ScheduleService(sch_repo, stu_repo, cls_repo)

        # Existing class schedule on 2026-10-05 18:00 - 19:30
        sch_svc.create_schedule(
            ScheduleCreateDTO(
                class_id="cls_existing",
                date="2026-10-05",
                start_time="18:00",
                end_time="19:30",
                lesson_title="Lớp Đã Có",
            )
        )

        day_schs = sch_repo.get_by_date_range("2026-10-05", "2026-10-05")

        # Overlapping slot: 18:30 - 20:00 -> CONFLICT
        has_overlap = any(
            is_time_overlap("18:30", "20:00", s.start_time, s.end_time)
            for s in day_schs
        )
        assert has_overlap is True

        # Non-overlapping slot: 14:00 - 15:30 -> NO CONFLICT
        no_overlap = any(
            is_time_overlap("14:00", "15:30", s.start_time, s.end_time)
            for s in day_schs
        )
        assert no_overlap is False
