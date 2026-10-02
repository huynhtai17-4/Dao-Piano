"""Unit tests for Holiday model, repository, and HolidayService."""

import tempfile
import pytest
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_holiday_repository import JsonHolidayRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.application.services.holiday_service import HolidayService
from backend.core.enums import ScheduleStatus, ClassType
from backend.domain.models.schedule import Schedule


def test_create_single_day_holiday():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        holiday_repo = JsonHolidayRepository(storage)
        schedule_repo = JsonScheduleRepository(storage)
        service = HolidayService(holiday_repo, schedule_repo)

        # Create schedule on 2026-10-10
        sch = Schedule(
            lesson_title="Lớp Piano",
            date="2026-10-10",
            start_time="09:00",
            end_time="10:00",
            class_type=ClassType.OFFLINE,
            status=ScheduleStatus.SCHEDULED,
        )
        schedule_repo.create(sch)

        # Add single day holiday on 2026-10-10
        hol = service.create_holiday("Nghỉ bận", "2026-10-10", "2026-10-10")
        assert hol.id is not None
        assert hol.title == "Nghỉ bận"
        assert hol.start_date == "2026-10-10"
        assert hol.end_date == "2026-10-10"

        assert service.is_date_holiday("2026-10-10") is not None
        assert service.is_date_holiday("2026-10-11") is None

        # Schedule should be converted to HOLIDAY
        updated_sch = schedule_repo.get_by_id(sch.id)
        assert updated_sch is not None
        assert updated_sch.status == ScheduleStatus.HOLIDAY


def test_create_multi_day_holiday_and_delete():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        holiday_repo = JsonHolidayRepository(storage)
        schedule_repo = JsonScheduleRepository(storage)
        service = HolidayService(holiday_repo, schedule_repo)

        sch1 = Schedule(
            lesson_title="Lớp 1",
            date="2026-10-10",
            start_time="09:00",
            end_time="10:00",
            class_type=ClassType.OFFLINE,
            status=ScheduleStatus.SCHEDULED,
        )
        sch2 = Schedule(
            lesson_title="Lớp 2",
            date="2026-10-12",
            start_time="09:00",
            end_time="10:00",
            class_type=ClassType.OFFLINE,
            status=ScheduleStatus.SCHEDULED,
        )
        schedule_repo.create(sch1)
        schedule_repo.create(sch2)

        # Holiday 2026-10-09 to 2026-10-13
        hol = service.create_holiday("Nghỉ lễ", "2026-10-09", "2026-10-13")
        assert len(service.get_all_holidays()) == 1

        assert schedule_repo.get_by_id(sch1.id).status == ScheduleStatus.HOLIDAY
        assert schedule_repo.get_by_id(sch2.id).status == ScheduleStatus.HOLIDAY

        # Delete holiday
        service.delete_holiday(hol.id)
        assert len(service.get_all_holidays()) == 0

        # Schedules should be restored to SCHEDULED
        assert schedule_repo.get_by_id(sch1.id).status == ScheduleStatus.SCHEDULED
        assert schedule_repo.get_by_id(sch2.id).status == ScheduleStatus.SCHEDULED


def test_invalid_date_order_raises():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        holiday_repo = JsonHolidayRepository(storage)
        schedule_repo = JsonScheduleRepository(storage)
        service = HolidayService(holiday_repo, schedule_repo)

        with pytest.raises(Exception):
            service.create_holiday("Lỗi", "2026-10-15", "2026-10-10")


def test_partial_day_holiday_time_range():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        holiday_repo = JsonHolidayRepository(storage)
        schedule_repo = JsonScheduleRepository(storage)
        service = HolidayService(holiday_repo, schedule_repo)

        # Morning schedule 08:30 - 09:30
        sch_morning = Schedule(
            lesson_title="Lớp Sáng",
            date="2026-10-20",
            start_time="08:30",
            end_time="09:30",
            class_type=ClassType.OFFLINE,
            status=ScheduleStatus.SCHEDULED,
        )
        # Evening schedule 18:00 - 19:30
        sch_evening = Schedule(
            lesson_title="Lớp Tối",
            date="2026-10-20",
            start_time="18:00",
            end_time="19:30",
            class_type=ClassType.OFFLINE,
            status=ScheduleStatus.SCHEDULED,
        )
        schedule_repo.create(sch_morning)
        schedule_repo.create(sch_evening)

        # Teacher is busy only in the morning: 08:00 - 12:00
        hol = service.create_holiday(
            title="Nghỉ dạy",
            start_date="2026-10-20",
            end_date="2026-10-20",
            start_time="08:00",
            end_time="12:00",
            is_all_day=False,
        )

        assert hol.title == "Nghỉ dạy"
        assert hol.is_all_day is False

        # Only morning schedule should be marked HOLIDAY
        assert schedule_repo.get_by_id(sch_morning.id).status == ScheduleStatus.HOLIDAY
        # Evening schedule remains SCHEDULED!
        assert schedule_repo.get_by_id(sch_evening.id).status == ScheduleStatus.SCHEDULED

