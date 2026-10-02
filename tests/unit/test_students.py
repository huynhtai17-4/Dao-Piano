"""Unit tests for StudentService and class assignment capacity."""

import tempfile
import pytest
from backend.core.enums import ClassType
from backend.core.exceptions import CapacityExceededError
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.dto.student_dto import StudentCreateDTO
from backend.application.dto.class_dto import ClassCreateDTO


@pytest.fixture
def services():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        student_repo = JsonStudentRepository(storage)
        class_repo = JsonClassRepository(storage)
        s_svc = StudentService(student_repo, class_repo)
        c_svc = ClassService(class_repo, student_repo)
        yield s_svc, c_svc


def test_create_student_and_assign_class(services):
    s_svc, c_svc = services
    c = c_svc.create_class(ClassCreateDTO(name="Lớp Solo 1", class_type=ClassType.ONE_ON_ONE, max_students=1))

    student = s_svc.create_student(
        StudentCreateDTO(
            name="Nguyễn Văn A",
            phone="0912345678",
            class_type=ClassType.ONE_ON_ONE,
            class_id=c.id,
            remaining_lessons=10,
        )
    )
    assert student.name == "Nguyễn Văn A"
    assert student.class_id == c.id

    # Verify class roster updated
    updated_c = c_svc.get_class_by_id(c.id)
    assert updated_c.current_student_count == 1
    assert student.id in updated_c.student_ids


def test_cannot_exceed_class_capacity(services):
    s_svc, c_svc = services
    # 1-on-1 class has capacity 1
    c = c_svc.create_class(ClassCreateDTO(name="Lớp Solo 1", class_type=ClassType.ONE_ON_ONE, max_students=1))

    # Add 1st student -> OK
    s_svc.create_student(
        StudentCreateDTO(name="Học sinh 1", phone="0911111111", class_id=c.id)
    )

    # Add 2nd student -> CapacityExceededError
    with pytest.raises(CapacityExceededError):
        s_svc.create_student(
            StudentCreateDTO(name="Học sinh 2", phone="0922222222", class_id=c.id)
        )


def test_student_phone_with_various_prefixes(services):
    s_svc, _ = services
    # Test valid phone numbers with 03, 05, 07, 08, 02 prefixes
    prefixes = ["0388123456", "0567123456", "0799123456", "0812345678", "0243123456", "+84388123456"]
    for idx, phone in enumerate(prefixes):
        st = s_svc.create_student(
            StudentCreateDTO(name=f"Học sinh {idx}", phone=phone, remaining_lessons=8)
        )
        assert st.id is not None
        assert st.phone.startswith("0") or st.phone.startswith("+84")


def test_edit_student_remaining_lessons(services):
    from backend.application.dto.student_dto import StudentUpdateDTO
    s_svc, _ = services
    st = s_svc.create_student(
        StudentCreateDTO(name="Trần Văn B", phone="0388123456", remaining_lessons=8)
    )
    assert st.remaining_lessons == 8

    # Edit remaining lessons to 15
    updated = s_svc.update_student(
        StudentUpdateDTO(
            id=st.id,
            name=st.name,
            phone=st.phone,
            class_type=st.class_type,
            remaining_lessons=15,
        )
    )
    assert updated.remaining_lessons == 15

    # Edit remaining lessons to 0
    updated_zero = s_svc.update_student(
        StudentUpdateDTO(
            id=st.id,
            name=st.name,
            phone=st.phone,
            class_type=st.class_type,
            remaining_lessons=0,
        )
    )
    assert updated_zero.remaining_lessons == 0


def test_adjust_remaining_lessons(services):
    s_svc, _ = services
    st = s_svc.create_student(
        StudentCreateDTO(name="Lê Thị C", phone="0987654321", remaining_lessons=5)
    )
    assert st.remaining_lessons == 5

    # Delta +3
    res1 = s_svc.adjust_remaining_lessons(st.id, 3, is_delta=True)
    assert res1.remaining_lessons == 8

    # Delta -2
    res2 = s_svc.adjust_remaining_lessons(st.id, -2, is_delta=True)
    assert res2.remaining_lessons == 6

    # Delta -10 (cannot be negative)
    res3 = s_svc.adjust_remaining_lessons(st.id, -10, is_delta=True)
    assert res3.remaining_lessons == 0

    # Absolute set to 12
    res4 = s_svc.adjust_remaining_lessons(st.id, 12, is_delta=False)
    assert res4.remaining_lessons == 12

