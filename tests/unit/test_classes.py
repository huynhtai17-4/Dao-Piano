"""Unit tests for ClassService and capacity / editing invariants."""

import tempfile
import pytest
from backend.core.enums import ClassType
from backend.core.exceptions import ClassEditRestrictedError, BusinessRuleViolationError
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.application.services.class_service import ClassService
from backend.application.dto.class_dto import ClassCreateDTO, ClassUpdateDTO


@pytest.fixture
def class_service():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        class_repo = JsonClassRepository(storage)
        student_repo = JsonStudentRepository(storage)
        yield ClassService(class_repo, student_repo)


def test_create_one_on_one_enforces_max_1(class_service):
    dto = ClassCreateDTO(name="Piano Solo", class_type=ClassType.ONE_ON_ONE, max_students=10)
    created = class_service.create_class(dto)
    assert created.max_students == 1


def test_offline_class_cannot_change_name_or_type(class_service):
    created = class_service.create_class(ClassCreateDTO(name="Lớp Nhí A", class_type=ClassType.OFFLINE, max_students=5))

    # Attempt to change name on OFFLINE class
    with pytest.raises(ClassEditRestrictedError):
        class_service.update_class(
            ClassUpdateDTO(
                id=created.id,
                name="Lớp Nhí Đổi Tên",
                class_type=ClassType.OFFLINE,
                max_students=5,
            )
        )

    # Attempt to change class_type on OFFLINE class
    with pytest.raises(ClassEditRestrictedError):
        class_service.update_class(
            ClassUpdateDTO(
                id=created.id,
                name="Lớp Nhí A",
                class_type=ClassType.ONLINE,
                max_students=5,
            )
        )

    # Allowed: changing max_students on OFFLINE class
    updated = class_service.update_class(
        ClassUpdateDTO(
            id=created.id,
            name="Lớp Nhí A",
            class_type=ClassType.OFFLINE,
            max_students=8,
        )
    )
    assert updated.max_students == 8


def test_online_class_can_edit_name_and_capacity(class_service):
    created = class_service.create_class(ClassCreateDTO(name="Online Cơ Bản", class_type=ClassType.ONLINE, max_students=4))
    updated = class_service.update_class(
        ClassUpdateDTO(
            id=created.id,
            name="Online Nâng Cao",
            class_type=ClassType.ONLINE,
            max_students=6,
        )
    )
    assert updated.name == "Online Nâng Cao"
    assert updated.max_students == 6
