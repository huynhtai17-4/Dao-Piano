"""End-to-end integration test validating full business workflow in isolated environment."""

import tempfile
from backend.core.enums import ClassType, AttendanceStatus
from backend.infrastructure.storage.json_storage import JsonStorage
from backend.infrastructure.repositories.json_student_repository import JsonStudentRepository
from backend.infrastructure.repositories.json_class_repository import JsonClassRepository
from backend.infrastructure.repositories.json_schedule_repository import JsonScheduleRepository
from backend.infrastructure.repositories.json_attendance_repository import JsonAttendanceRepository
from backend.infrastructure.repositories.json_payment_repository import JsonPaymentRepository
from backend.application.services.student_service import StudentService
from backend.application.services.class_service import ClassService
from backend.application.services.schedule_service import ScheduleService
from backend.application.services.attendance_service import AttendanceService
from backend.application.services.payment_service import PaymentService
from backend.application.dto.class_dto import ClassCreateDTO
from backend.application.dto.student_dto import StudentCreateDTO
from backend.application.dto.schedule_dto import ScheduleCreateDTO
from backend.application.dto.attendance_dto import AttendanceCreateDTO
from backend.application.dto.payment_dto import PaymentCreateDTO


def test_complete_studio_workflow():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Step 0: Setup isolated infrastructure
        storage = JsonStorage(tmp_dir)
        stu_repo = JsonStudentRepository(storage)
        cls_repo = JsonClassRepository(storage)
        sch_repo = JsonScheduleRepository(storage)
        att_repo = JsonAttendanceRepository(storage)
        pay_repo = JsonPaymentRepository(storage)

        s_svc = StudentService(stu_repo, cls_repo)
        c_svc = ClassService(cls_repo, stu_repo)
        sch_svc = ScheduleService(sch_repo, stu_repo, cls_repo)
        a_svc = AttendanceService(att_repo, stu_repo, sch_repo)
        p_svc = PaymentService(pay_repo, stu_repo)

        # 1. Create class (Offline group class, max 6 students)
        created_class = c_svc.create_class(
            ClassCreateDTO(name="Lớp Piano Trẻ Em A", class_type=ClassType.OFFLINE, max_students=6)
        )
        assert created_class.name == "Lớp Piano Trẻ Em A"
        assert created_class.current_student_count == 0

        # 2. Create student with 8 initial lessons
        created_student = s_svc.create_student(
            StudentCreateDTO(
                name="Trần Đức Nam",
                phone="0918765432",
                date_of_birth="2014-06-15",
                class_type=ClassType.OFFLINE,
                class_id=created_class.id,
                remaining_lessons=8,
            )
        )
        assert created_student.name == "Trần Đức Nam"
        assert created_student.remaining_lessons == 8
        assert created_student.class_id == created_class.id

        # 3. Verify class roster now contains student
        cls_check = c_svc.get_class_by_id(created_class.id)
        assert cls_check.current_student_count == 1
        assert created_student.id in cls_check.student_ids

        # 4. Create calendar schedule
        created_schedule = sch_svc.create_schedule(
            ScheduleCreateDTO(
                class_id=created_class.id,
                student_id=created_student.id,
                date="2026-10-05",
                start_time="17:00",
                end_time="18:30",
                lesson_title="Bài học Gam Đô Trưởng",
                location="Phòng Học Lớp 1",
            )
        )
        assert created_schedule.date == "2026-10-05"

        # 5. Mark attendance PRESENT
        att_record = a_svc.mark_attendance(
            AttendanceCreateDTO(
                schedule_id=created_schedule.id,
                student_id=created_student.id,
                attendance_date="2026-10-05",
                status=AttendanceStatus.PRESENT,
                note="Học sinh tập trung tốt",
            )
        )
        assert att_record.status == AttendanceStatus.PRESENT

        # 6. Verify remaining_lessons decreased: 8 -> 7
        stu_after_att = s_svc.get_student_by_id(created_student.id)
        assert stu_after_att.remaining_lessons == 7

        # 7. Record tuition payment (Add 8 lessons for 1.600.000 ₫)
        p_svc.record_payment(
            PaymentCreateDTO(
                student_id=created_student.id,
                amount=1600000,
                payment_date="2026-10-06",
                lessons_added=8,
                note="Gia hạn khóa học",
            )
        )

        # 8. Verify remaining_lessons increased: 7 + 8 = 15
        stu_after_pay = s_svc.get_student_by_id(created_student.id)
        assert stu_after_pay.remaining_lessons == 15

        # 9. Update attendance: PRESENT -> ABSENT (Teacher corrects mistake)
        a_svc.mark_attendance(
            AttendanceCreateDTO(
                schedule_id=created_schedule.id,
                student_id=created_student.id,
                attendance_date="2026-10-05",
                status=AttendanceStatus.ABSENT,
                note="Phụ huynh xin nghỉ có phép",
            )
        )

        # 10. Verify lesson is refunded: 15 + 1 = 16
        stu_after_refund = s_svc.get_student_by_id(created_student.id)
        assert stu_after_refund.remaining_lessons == 16

        # 11. Fresh load from disk into completely new repository and service instances
        fresh_storage = JsonStorage(tmp_dir)
        fresh_stu_repo = JsonStudentRepository(fresh_storage)
        fresh_cls_repo = JsonClassRepository(fresh_storage)
        fresh_sch_repo = JsonScheduleRepository(fresh_storage)
        fresh_att_repo = JsonAttendanceRepository(fresh_storage)
        fresh_pay_repo = JsonPaymentRepository(fresh_storage)

        fresh_stu_svc = StudentService(fresh_stu_repo, fresh_cls_repo)
        fresh_cls_svc = ClassService(fresh_cls_repo, fresh_stu_repo)

        # 12. Verify persisted data integrity across all files
        reloaded_student = fresh_stu_svc.get_student_by_id(created_student.id)
        assert reloaded_student.name == "Trần Đức Nam"
        assert reloaded_student.remaining_lessons == 16
        assert reloaded_student.class_id == created_class.id

        reloaded_class = fresh_cls_svc.get_class_by_id(created_class.id)
        assert reloaded_class.current_student_count == 1
        assert created_student.id in reloaded_class.student_ids

        all_fresh_schedules = fresh_sch_repo.get_all()
        assert len(all_fresh_schedules) == 1
        assert all_fresh_schedules[0].id == created_schedule.id

        all_fresh_payments = fresh_pay_repo.get_all()
        assert len(all_fresh_payments) == 1
        assert all_fresh_payments[0].amount == 1600000

        all_fresh_att = fresh_att_repo.get_all()
        assert len(all_fresh_att) == 1
        assert all_fresh_att[0].status == AttendanceStatus.ABSENT


def test_student_flow_with_online_and_offline_scheduling():
    """Verify online/1-on-1 weekly slot scheduling and offline class slot assignment."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = JsonStorage(tmp_dir)
        stu_repo = JsonStudentRepository(storage)
        cls_repo = JsonClassRepository(storage)
        sch_repo = JsonScheduleRepository(storage)

        s_svc = StudentService(stu_repo, cls_repo, sch_repo)
        c_svc = ClassService(cls_repo, stu_repo, sch_repo)
        sch_svc = ScheduleService(sch_repo, stu_repo, cls_repo)

        # 1. Flow A: Create 1-on-1 Student with recurring weekly slots
        stu_1on1 = s_svc.create_student(
            StudentCreateDTO(
                name="Phạm Hoàng Long",
                phone="0988776655",
                class_type=ClassType.ONE_ON_ONE,
                remaining_lessons=8,
            )
        )
        assert stu_1on1.remaining_lessons == 8

        # Generate weekly slots for this student
        slots_1on1 = [
            {"day_idx": 0, "start_time": "18:00", "end_time": "19:00", "location": "Phòng Piano 1"},
            {"day_idx": 3, "start_time": "18:00", "end_time": "19:00", "location": "Phòng Piano 1"},
        ]
        created_sch_count = sch_svc.create_student_recurring_schedules(
            stu_1on1.id, slots_1on1, ClassType.ONE_ON_ONE, num_weeks=4
        )
        assert created_sch_count > 0
        stu_schedules = sch_repo.get_by_student_id(stu_1on1.id)
        assert len(stu_schedules) == created_sch_count

        # 2. Flow B: Create Offline Class with slots, then add student to that class
        off_class = c_svc.create_class(
            ClassCreateDTO(name="Lớp Piano Nhí T2-T5", class_type=ClassType.OFFLINE, max_students=5)
        )
        class_slots = [
            {"day_idx": 0, "start_time": "17:30", "end_time": "19:00", "location": "Phòng 2"},
            {"day_idx": 3, "start_time": "17:30", "end_time": "19:00", "location": "Phòng 2"},
        ]
        sch_svc.create_class_recurring_schedules(off_class.id, class_slots, num_weeks=4)

        # Retrieve recurring slots of this offline class
        extracted_slots = sch_svc.get_class_recurring_slots(off_class.id)
        assert len(extracted_slots) == 2
        assert extracted_slots[0]["day_name"] == "Thứ 2"

        # Enroll offline student into this desired class
        stu_off = s_svc.create_student(
            StudentCreateDTO(
                name="Đỗ Mai Chi",
                phone="0911223344",
                class_type=ClassType.OFFLINE,
                class_id=off_class.id,
                remaining_lessons=12,
            )
        )
        assert stu_off.class_id == off_class.id
        assert stu_off.class_name == off_class.name
        updated_off_cls = c_svc.get_class_by_id(off_class.id)
        assert stu_off.id in updated_off_cls.student_ids

        # 3. Flow C: Edit remaining lessons
        # Direct adjustment
        s_svc.adjust_remaining_lessons(stu_off.id, 20, is_delta=False)
        reloaded = s_svc.get_student_by_id(stu_off.id)
        assert reloaded.remaining_lessons == 20

        # Delta adjustment: -5 lessons
        s_svc.adjust_remaining_lessons(stu_off.id, -5, is_delta=True)
        reloaded2 = s_svc.get_student_by_id(stu_off.id)
        assert reloaded2.remaining_lessons == 15
