"""Unit tests for Calendar Conflict Detection Engine."""

import tempfile
import pytest
from backend.core.exceptions import ScheduleConflictError
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.application.services.schedule_service import ScheduleService
from backend.application.dto.schedule_dto import ScheduleCreateDTO


@pytest.fixture
def schedule_service():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        sch_repo = JsonScheduleRepository(storage)
        stu_repo = JsonStudentRepository(storage)
        cls_repo = JsonClassRepository(storage)
        yield ScheduleService(sch_repo, stu_repo, cls_repo)


def test_conflict_exact_overlap(schedule_service):
    # Schedule 1: Student A from 18:00 to 19:00 on 2026-10-01
    schedule_service.create_schedule(
        ScheduleCreateDTO(
            student_id="stu_A",
            date="2026-10-01",
            start_time="18:00",
            end_time="19:00",
        )
    )

    # Attempt exact overlap for Student A
    with pytest.raises(ScheduleConflictError):
        schedule_service.create_schedule(
            ScheduleCreateDTO(
                student_id="stu_A",
                date="2026-10-01",
                start_time="18:00",
                end_time="19:00",
            )
        )


def test_conflict_partial_overlap(schedule_service):
    # Schedule 1: 18:00 - 19:00
    schedule_service.create_schedule(
        ScheduleCreateDTO(
            student_id="stu_A",
            date="2026-10-01",
            start_time="18:00",
            end_time="19:00",
        )
    )

    # Partial overlap: 18:30 - 19:30
    with pytest.raises(ScheduleConflictError):
        schedule_service.create_schedule(
            ScheduleCreateDTO(
                student_id="stu_A",
                date="2026-10-01",
                start_time="18:30",
                end_time="19:30",
            )
        )


def test_adjacent_schedules_do_not_conflict(schedule_service):
    # Schedule 1: 18:00 - 19:00
    schedule_service.create_schedule(
        ScheduleCreateDTO(
            student_id="stu_A",
            date="2026-10-01",
            start_time="18:00",
            end_time="19:00",
        )
    )

    # Adjacent: 19:00 - 20:00 (Should succeed!)
    s2 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            student_id="stu_A",
            date="2026-10-01",
            start_time="19:00",
            end_time="20:00",
        )
    )
    assert s2.start_time == "19:00"


def test_different_students_at_same_time_do_not_conflict(schedule_service):
    # Student A: 18:00 - 19:00
    schedule_service.create_schedule(
        ScheduleCreateDTO(
            student_id="stu_A",
            date="2026-10-01",
            start_time="18:00",
            end_time="19:00",
        )
    )

    # Student B: 18:00 - 19:00 (Should succeed because student_id is different)
    s_b = schedule_service.create_schedule(
        ScheduleCreateDTO(
            student_id="stu_B",
            date="2026-10-01",
            start_time="18:00",
            end_time="19:00",
        )
    )
    assert s_b.student_id == "stu_B"


def test_class_conflict_at_same_time(schedule_service):
    # Class C: 15:00 - 16:30
    schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id="cls_PianoRoom1",
            date="2026-10-02",
            start_time="15:00",
            end_time="16:30",
        )
    )

    # Same class at overlapping time
    with pytest.raises(ScheduleConflictError):
        schedule_service.create_schedule(
            ScheduleCreateDTO(
                class_id="cls_PianoRoom1",
                date="2026-10-02",
                start_time="16:00",
                end_time="17:00",
            )
        )


def test_ensure_recurring_class_schedules(schedule_service):
    # Create fixed class schedule on Monday 2026-10-05
    schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id="cls_PianoNhi",
            date="2026-10-05",  # Monday
            start_time="17:30",
            end_time="19:00",
            lesson_title="Lớp Piano Nhí Cơ Bản",
        )
    )

    # Project for 4 upcoming weeks
    count = schedule_service.ensure_recurring_class_schedules(horizon_weeks=4)
    assert count >= 1

    # Verify that Monday of next week has this class scheduled
    next_monday_schedules = schedule_service.schedule_repo.get_by_date_range("2026-10-12", "2026-10-12")
    assert len(next_monday_schedules) == 1
    assert next_monday_schedules[0].class_id == "cls_PianoNhi"
    assert next_monday_schedules[0].start_time == "17:30"
    assert next_monday_schedules[0].end_time == "19:00"

    # Calling it again should not duplicate
    count2 = schedule_service.ensure_recurring_class_schedules(horizon_weeks=4)
    assert count2 == 0


def test_class_recurring_slots_and_generation(schedule_service):
    from backend.domain.models.class_model import ClassModel
    from backend.domain.models.student import Student
    from backend.core.enums import ClassType

    cl = schedule_service.class_repo.create(ClassModel(name="Lớp Offline Demo", class_type=ClassType.OFFLINE, max_students=6))

    slots = [
        {"day_idx": 0, "day_name": "Thứ 2", "start_time": "17:30", "end_time": "19:00", "location": "Phòng 1"},
        {"day_idx": 3, "day_name": "Thứ 5", "start_time": "17:30", "end_time": "19:00", "location": "Phòng 1"},
    ]

    created_count = schedule_service.create_class_recurring_schedules(cl.id, slots, num_weeks=4)
    assert created_count > 0

    # Retrieve recurring slots
    extracted_slots = schedule_service.get_class_recurring_slots(cl.id)
    assert len(extracted_slots) == 2
    assert extracted_slots[0]["day_name"] == "Thứ 2"
    assert extracted_slots[1]["day_name"] == "Thứ 5"

    # Test student recurring schedule creation
    st = schedule_service.student_repo.create(Student(name="Học sinh 1-1", phone="0987654321", class_type=ClassType.ONE_ON_ONE))
    st_slots = [
        {"day_idx": 1, "day_name": "Thứ 3", "start_time": "18:00", "end_time": "19:00", "location": "Phòng Piano 1"},
    ]
    st_count = schedule_service.create_student_recurring_schedules(st.id, st_slots, ClassType.ONE_ON_ONE, num_weeks=4)
    assert st_count > 0

