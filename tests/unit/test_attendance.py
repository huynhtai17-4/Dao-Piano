"""Unit tests for AttendanceService lesson delta math and double-deduction prevention."""

import tempfile
import pytest
from backend.core.enums import AttendanceStatus
from backend.core.exceptions import InsufficientLessonsError
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.infrastructure.repositories.json_attendance_repository import JsonAttendanceRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.application.services.student_service import StudentService
from backend.application.services.attendance_service import AttendanceService
from backend.application.dto.student_dto import StudentCreateDTO
from backend.application.dto.attendance_dto import AttendanceCreateDTO


@pytest.fixture
def setup_services():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        stu_repo = JsonStudentRepository(storage)
        sch_repo = JsonScheduleRepository(storage)
        att_repo = JsonAttendanceRepository(storage)
        cls_repo = JsonClassRepository(storage)

        s_svc = StudentService(stu_repo, cls_repo)
        a_svc = AttendanceService(att_repo, stu_repo, sch_repo)
        yield s_svc, a_svc


def test_attendance_present_deducts_one_lesson(setup_services):
    s_svc, a_svc = setup_services
    st = s_svc.create_student(StudentCreateDTO(name="Minh Anh", phone="0912345678", remaining_lessons=10))

    # Mark PRESENT
    a_svc.mark_attendance(
        AttendanceCreateDTO(
            schedule_id="sch_1",
            student_id=st.id,
            attendance_date="2026-10-01",
            status=AttendanceStatus.PRESENT,
        )
    )

    updated_st = s_svc.get_student_by_id(st.id)
    assert updated_st.remaining_lessons == 9


def test_attendance_idempotent_present_to_present(setup_services):
    s_svc, a_svc = setup_services
    st = s_svc.create_student(StudentCreateDTO(name="Minh Anh", phone="0912345678", remaining_lessons=10))

    # 1st PRESENT -> 9
    a_svc.mark_attendance(
        AttendanceCreateDTO(
            schedule_id="sch_1",
            student_id=st.id,
            attendance_date="2026-10-01",
            status=AttendanceStatus.PRESENT,
        )
    )
    assert s_svc.get_student_by_id(st.id).remaining_lessons == 9

    # 2nd update with PRESENT -> still 9 (DO NOT deduct to 8!)
    a_svc.mark_attendance(
        AttendanceCreateDTO(
            schedule_id="sch_1",
            student_id=st.id,
            attendance_date="2026-10-01",
            status=AttendanceStatus.PRESENT,
        )
    )
    assert s_svc.get_student_by_id(st.id).remaining_lessons == 9


def test_attendance_present_to_absent_refunds_lesson(setup_services):
    s_svc, a_svc = setup_services
    st = s_svc.create_student(StudentCreateDTO(name="Minh Anh", phone="0912345678", remaining_lessons=10))

    # Mark PRESENT -> 9
    a_svc.mark_attendance(
        AttendanceCreateDTO(
            schedule_id="sch_1",
            student_id=st.id,
            attendance_date="2026-10-01",
            status=AttendanceStatus.PRESENT,
        )
    )
    assert s_svc.get_student_by_id(st.id).remaining_lessons == 9

    # Switch to ABSENT -> refunded back to 10
    a_svc.mark_attendance(
        AttendanceCreateDTO(
            schedule_id="sch_1",
            student_id=st.id,
            attendance_date="2026-10-01",
            status=AttendanceStatus.ABSENT,
        )
    )
    assert s_svc.get_student_by_id(st.id).remaining_lessons == 10


def test_attendance_zero_lessons_cannot_deduct(setup_services):
    s_svc, a_svc = setup_services
    st = s_svc.create_student(StudentCreateDTO(name="Hết Buổi", phone="0912345678", remaining_lessons=0))

    with pytest.raises(InsufficientLessonsError):
        a_svc.mark_attendance(
            AttendanceCreateDTO(
                schedule_id="sch_1",
                student_id=st.id,
                attendance_date="2026-10-01",
                status=AttendanceStatus.PRESENT,
            )
        )
