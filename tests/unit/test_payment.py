"""Unit tests for PaymentService and lesson crediting."""

import tempfile
import pytest
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_payment_repository import JsonPaymentRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.application.services.student_service import StudentService
from backend.application.services.payment_service import PaymentService
from backend.application.dto.student_dto import StudentCreateDTO
from backend.application.dto.payment_dto import PaymentCreateDTO


@pytest.fixture
def setup_payment():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        stu_repo = JsonStudentRepository(storage)
        cls_repo = JsonClassRepository(storage)
        pay_repo = JsonPaymentRepository(storage)

        s_svc = StudentService(stu_repo, cls_repo)
        p_svc = PaymentService(pay_repo, stu_repo)
        yield s_svc, p_svc


def test_payment_adds_lessons_to_student(setup_payment):
    s_svc, p_svc = setup_payment
    st = s_svc.create_student(StudentCreateDTO(name="Học Viên A", phone="0912345678", remaining_lessons=2))

    # Pay for 8 lessons
    tx = p_svc.record_payment(
        PaymentCreateDTO(
            student_id=st.id,
            amount=1600000,
            payment_date="2026-10-01",
            lessons_added=8,
        )
    )
    assert tx.amount == 1600000
    assert tx.amount_display == "1.600.000 ₫"

    # Check student balance increased: 2 + 8 = 10
    updated_st = s_svc.get_student_by_id(st.id)
    assert updated_st.remaining_lessons == 10


def test_invalid_payment_amount(setup_payment):
    s_svc, p_svc = setup_payment
    st = s_svc.create_student(StudentCreateDTO(name="Học Viên B", phone="0912345678", remaining_lessons=0))

    with pytest.raises(Exception):
        p_svc.record_payment(
            PaymentCreateDTO(
                student_id=st.id,
                amount=-500000,
                payment_date="2026-10-01",
                lessons_added=8,
            )
        )


def test_toggle_tuition_status_paid_and_unpaid(setup_payment):
    s_svc, p_svc = setup_payment
    st = s_svc.create_student(StudentCreateDTO(name="Học Viên C", phone="0988776655", remaining_lessons=0))

    # Mark paid
    p_svc.toggle_tuition_status(st.id, mark_as_paid=True)
    updated = s_svc.get_student_by_id(st.id)
    assert updated.remaining_lessons == 8
    assert p_svc.get_total_revenue() == 1600000

    # Mark unpaid (revert mistake)
    p_svc.toggle_tuition_status(st.id, mark_as_paid=False)
    reverted = s_svc.get_student_by_id(st.id)
    assert reverted.remaining_lessons == 0
    assert p_svc.get_total_revenue() == 0


def test_dashboard_monthly_revenue_calculation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        stu_repo = JsonStudentRepository(storage)
        cls_repo = JsonClassRepository(storage)
        sch_repo = JsonScheduleRepository(storage)
        pay_repo = JsonPaymentRepository(storage)

        from backend.application.services.dashboard_service import DashboardService
        from backend.domain.models.payment import Payment
        from backend.core.dates import today_str

        dash_svc = DashboardService(stu_repo, cls_repo, sch_repo, pay_repo)

        today = today_str()
        current_month = today[:7]

        # Payment in current month
        pay1 = Payment(student_id="s1", amount=1500000, payment_date=f"{current_month}-05", lessons_added=8)
        pay_repo.create(pay1)

        # Payment in last year / past month
        pay2 = Payment(student_id="s2", amount=2000000, payment_date="2020-01-01", lessons_added=8)
        pay_repo.create(pay2)

        summary = dash_svc.get_summary()
        # Only pay1 should be included
        assert summary["total_revenue"] == 1500000
        assert summary["total_revenue_display"] == "1.500.000 ₫"
        assert summary["current_month_display"] == f"Tháng {today[5:7]}/{today[:4]}"

