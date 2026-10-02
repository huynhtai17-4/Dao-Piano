"""Seeds realistic demo data for testing and demonstration."""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.enums import ClassType, AttendanceStatus
from backend.core.dates import today_date, get_week_days, format_date_iso
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
from scripts.reset_data import reset_all_data


def seed() -> None:
    print("[INFO] Đặt lại dữ liệu ban đầu...")
    reset_all_data()

    storage = JsonStorage(data_dir=PROJECT_ROOT / "data")
    student_repo = JsonStudentRepository(storage)
    class_repo = JsonClassRepository(storage)
    schedule_repo = JsonScheduleRepository(storage)
    attendance_repo = JsonAttendanceRepository(storage)
    payment_repo = JsonPaymentRepository(storage)

    student_service = StudentService(student_repo, class_repo)
    class_service = ClassService(class_repo, student_repo)
    schedule_service = ScheduleService(schedule_repo, student_repo, class_repo)
    attendance_service = AttendanceService(attendance_repo, student_repo, schedule_repo)
    payment_service = PaymentService(payment_repo, student_repo)

    print("[INFO] Tạo các lớp học...")
    # 3 Online classes
    c_on1 = class_service.create_class(ClassCreateDTO(name="Piano Nhập Môn Online", class_type=ClassType.ONLINE, max_students=6))
    c_on2 = class_service.create_class(ClassCreateDTO(name="Piano Nâng Cao Online", class_type=ClassType.ONLINE, max_students=4))
    c_on3 = class_service.create_class(ClassCreateDTO(name="Luyện Ngón Online Tối", class_type=ClassType.ONLINE, max_students=5))

    # 3 Offline classes
    c_off1 = class_service.create_class(ClassCreateDTO(name="Lớp Piano Nhí Cơ Bản", class_type=ClassType.OFFLINE, max_students=6))
    c_off2 = class_service.create_class(ClassCreateDTO(name="Lớp Đệm Hát Người Lớn", class_type=ClassType.OFFLINE, max_students=5))
    c_off3 = class_service.create_class(ClassCreateDTO(name="Lớp Cổ Điển Nhóm A", class_type=ClassType.OFFLINE, max_students=4))

    # 5 1-on-1 classes
    c_one1 = class_service.create_class(ClassCreateDTO(name="Piano Solo Thầy Đào 1", class_type=ClassType.ONE_ON_ONE, max_students=1))
    c_one2 = class_service.create_class(ClassCreateDTO(name="Piano Solo Thầy Đào 2", class_type=ClassType.ONE_ON_ONE, max_students=1))
    c_one3 = class_service.create_class(ClassCreateDTO(name="Piano Solo Thầy Đào 3", class_type=ClassType.ONE_ON_ONE, max_students=1))
    c_one4 = class_service.create_class(ClassCreateDTO(name="Piano Jazz Solo", class_type=ClassType.ONE_ON_ONE, max_students=1))
    c_one5 = class_service.create_class(ClassCreateDTO(name="Luyện Thi Nhạc Viện", class_type=ClassType.ONE_ON_ONE, max_students=1))

    print("[INFO] Tạo 15 học sinh mẫu...")
    demo_students = [
        ("Nguyễn Minh Anh", "0912345671", "2013-04-12", ClassType.ONE_ON_ONE, c_one1.id, 8),
        ("Trần Bảo Ngọc", "0987654321", "2014-08-20", ClassType.ONE_ON_ONE, c_one2.id, 1),   # Warning <=2
        ("Lê Hoàng Nam", "0934567890", "2011-01-15", ClassType.ONE_ON_ONE, c_one3.id, 0),   # Critical 0
        ("Phạm Gia Hưng", "0901234567", "2012-11-03", ClassType.ONE_ON_ONE, c_one4.id, 12),
        ("Đỗ Thảo Vy", "0978901234", "2015-06-25", ClassType.ONE_ON_ONE, c_one5.id, 6),

        ("Vũ Đức Trọng", "0918765432", "2010-09-10", ClassType.OFFLINE, c_off1.id, 10),
        ("Hoàng Mai Chi", "0982345678", "2012-03-14", ClassType.OFFLINE, c_off1.id, 2),    # Warning <=2
        ("Bùi Tuấn Kiệt", "0939876543", "2013-07-29", ClassType.OFFLINE, c_off2.id, 9),
        ("Đinh Phương Linh", "0908765432", "2009-12-05", ClassType.OFFLINE, c_off2.id, 7),
        ("Ngô Quang Huy", "0971234567", "2014-02-18", ClassType.OFFLINE, c_off3.id, 5),

        ("Dương Ngọc Ánh", "0916543210", "2011-05-22", ClassType.ONLINE, c_on1.id, 8),
        ("Lý Hải Đăng", "0981122334", "2013-10-30", ClassType.ONLINE, c_on1.id, 0),       # Critical 0
        ("Tạ Minh Khuê", "0933445566", "2015-08-14", ClassType.ONLINE, c_on2.id, 11),
        ("Hồ Tấn Phát", "0905566778", "2012-04-09", ClassType.ONLINE, c_on2.id, 4),
        ("Chu Kim Ngân", "0977889900", "2010-11-28", ClassType.ONLINE, c_on3.id, 6),
    ]

    created_students = []
    for name, phone, dob, ctype, cid, rem in demo_students:
        st = student_service.create_student(
            StudentCreateDTO(
                name=name,
                phone=phone,
                date_of_birth=dob,
                class_type=ctype,
                class_id=cid,
                remaining_lessons=rem,
            )
        )
        created_students.append(st)

    print("[INFO] Tạo lịch dạy cho tuần hiện tại...")
    week_days = get_week_days(today_date())

    # Schedule mapping
    s1 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id=c_one1.id,
            student_id=created_students[0].id,
            date=format_date_iso(week_days[0]),  # Monday
            start_time="08:00",
            end_time="09:00",
            lesson_title="Piano Solo - Minh Anh",
            location="Phòng Grand Piano 1",
        )
    )

    s2 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id=c_off1.id,
            date=format_date_iso(week_days[0]),  # Monday
            start_time="17:30",
            end_time="19:00",
            lesson_title="Lớp Piano Nhí Cơ Bản",
            location="Phòng Học Lớp 2",
        )
    )

    s3 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id=c_on1.id,
            date=format_date_iso(week_days[1]),  # Tuesday
            start_time="19:30",
            end_time="20:30",
            lesson_title="Piano Nhập Môn Online",
            online_url="https://meet.google.com/xyz-piano",
        )
    )

    s4 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id=c_one2.id,
            student_id=created_students[1].id,
            date=format_date_iso(week_days[2]),  # Wednesday
            start_time="09:30",
            end_time="10:30",
            lesson_title="Piano Solo - Bảo Ngọc",
            location="Phòng Upright 1",
        )
    )

    s5 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id=c_off2.id,
            date=format_date_iso(week_days[3]),  # Thursday
            start_time="18:00",
            end_time="19:30",
            lesson_title="Lớp Đệm Hát Người Lớn",
            location="Phòng Học Lớp 1",
        )
    )

    s6 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id=c_one4.id,
            student_id=created_students[3].id,
            date=format_date_iso(week_days[4]),  # Friday
            start_time="15:00",
            end_time="16:00",
            lesson_title="Piano Jazz Solo - Gia Hưng",
            location="Phòng Grand Piano 2",
        )
    )

    s7 = schedule_service.create_schedule(
        ScheduleCreateDTO(
            class_id=c_on2.id,
            date=format_date_iso(week_days[5]),  # Saturday
            start_time="08:30",
            end_time="10:00",
            lesson_title="Piano Nâng Cao Online",
            online_url="https://zoom.us/j/123456789",
        )
    )

    print("[INFO] Tự động xếp lịch cho các tuần tiếp theo từ ngày bắt đầu...")
    recur_count = schedule_service.ensure_recurring_class_schedules(horizon_weeks=12)
    print(f"[INFO] Đã tự động xếp thêm {recur_count} buổi học định kỳ cho các tuần sau.")

    print("[INFO] Tạo dữ liệu điểm danh và thanh toán mẫu...")
    # Mark attendance for Monday's solo
    attendance_service.mark_attendance(
        AttendanceCreateDTO(
            schedule_id=s1.id,
            student_id=created_students[0].id,
            attendance_date=s1.date,
            status=AttendanceStatus.PRESENT,
            note="Học sinh hoàn thành tốt bài Etude No. 1",
        )
    )

    # Tuition payments
    payment_service.record_payment(
        PaymentCreateDTO(
            student_id=created_students[0].id,
            amount=1600000,
            payment_date=format_date_iso(today_date() - timedelta(days=10)),
            lessons_added=8,
            note="Học phí Khóa Piano Solo Tháng 9",
        )
    )

    payment_service.record_payment(
        PaymentCreateDTO(
            student_id=created_students[3].id,
            amount=2400000,
            payment_date=format_date_iso(today_date() - timedelta(days=5)),
            lessons_added=12,
            note="Học phí Gói Jazz 12 buổi",
        )
    )

    payment_service.record_payment(
        PaymentCreateDTO(
            student_id=created_students[5].id,
            amount=1800000,
            payment_date=format_date_iso(today_date() - timedelta(days=2)),
            lessons_added=10,
            note="Học phí Lớp Nhí Tháng 10",
        )
    )

    print("[SUCCESS] Khởi tạo dữ liệu mẫu hoàn tất!")
    print(f"- 15 học sinh")
    print(f"- 11 lớp học (3 Online, 3 Offline, 5 1-on-1)")
    print(f"- 7 ca học trong tuần")
    print(f"- Doanh thu mẫu: 5.800.000 ₫")


if __name__ == "__main__":
    seed()
