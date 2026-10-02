"""Unit tests for Pydantic domain models."""

import pytest
from backend.core.enums import ClassType, ScheduleStatus, AttendanceStatus
from backend.domain.models.student import Student
from backend.domain.models.class_model import ClassModel
from backend.domain.models.schedule import Schedule
from backend.domain.models.attendance import Attendance
from backend.domain.models.payment import Payment


def test_valid_student():
    student = Student(
        name="Lê Văn A",
        phone="0912345678",
        date_of_birth="2012-04-10",
        class_type=ClassType.ONE_ON_ONE,
        remaining_lessons=8,
    )
    assert student.name == "Lê Văn A"
    assert student.remaining_lessons == 8
    assert student.is_active is True


def test_student_invalid_phone():
    with pytest.raises(ValueError):
        Student(name="Lê Văn A", phone="12345", class_type=ClassType.ONE_ON_ONE)


def test_student_negative_lessons():
    with pytest.raises(ValueError):
        Student(name="Lê Văn A", phone="0912345678", remaining_lessons=-1)


def test_student_blank_name():
    with pytest.raises(ValueError):
        Student(name="   ", phone="0912345678")


def test_class_one_on_one_enforces_capacity_one():
    c = ClassModel(name="Lớp Solo", class_type=ClassType.ONE_ON_ONE, max_students=10)
    assert c.max_students == 1


def test_class_offline_allows_capacity():
    c = ClassModel(name="Lớp Offline A", class_type=ClassType.OFFLINE, max_students=6)
    assert c.max_students == 6


def test_schedule_valid_and_time_order():
    sch = Schedule(
        date="2026-10-01",
        start_time="08:00",
        end_time="09:30",
        lesson_title="Piano Lesson",
    )
    assert sch.day_of_week == "THU"
    assert sch.status == ScheduleStatus.SCHEDULED


def test_schedule_invalid_time_order():
    with pytest.raises(ValueError):
        Schedule(
            date="2026-10-01",
            start_time="10:00",
            end_time="09:00",
            lesson_title="Inverted Times",
        )


def test_payment_amount_must_be_positive():
    with pytest.raises(ValueError):
        Payment(
            student_id="stu_123",
            amount=0,
            payment_date="2026-10-01",
            lessons_added=8,
        )


def test_attendance_valid():
    att = Attendance(
        schedule_id="sch_123",
        student_id="stu_123",
        attendance_date="2026-10-01",
        status=AttendanceStatus.PRESENT,
    )
    assert att.status == AttendanceStatus.PRESENT
