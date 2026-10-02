# PIANO CENTER MANAGER 🎹
> Phần mềm quản lý trung tâm đào tạo piano & studio âm nhạc chuyên nghiệp, offline-first, chạy mượt mà trên macOS và Windows.

---

## 1. Giới thiệu tổng quan
**Piano Center Manager** được thiết kế theo kiến trúc **Layered Modular Monolith** với tiêu chuẩn phần mềm công nghiệp:
- **Offline-First:** Hoạt động độc lập hoàn toàn, không cần kết nối mạng.
- **Bảo toàn dữ liệu (Atomic Persistence):** Sử dụng cơ chế ghi tệp tạm, đồng bộ vật lý (`fsync`) và thay thế nguyên tử (`os.replace`) để chống hỏng file dữ liệu tuyệt đối ngay cả khi mất điện đột ngột hoặc tắt máy bất ngờ.
- **Quy tắc nghiệp vụ chặt chẽ:** Điểm danh có đối chiếu số dư buổi học, bảo vệ không trừ 2 lần (idempotent), hoàn trả buổi khi sửa điểm danh, kiểm tra trùng lịch (conflict engine), và áp dụng ràng buộc riêng biệt cho từng hình thức học (1 Kèm 1, Offline, Online).
- **Giao diện Modern Glass-Neumorphism:** Tông màu Mint Emerald, Ocean Blue, Soft Purple, bo góc mềm mại, độ phân giải cao (High-DPI Retina Ready).

---

## 2. Tính năng chính

### 📅 1. Lịch trình dạy (Weekly Calendar)
- Chế độ xem **Week View** chuyên biệt từ Thứ 2 đến Chủ Nhật.
- Header tự động tính toán ngày tháng theo thời gian thực, điều hướng: **Tuần trước**, **Tuần sau**, **Hôm nay**.
- Khung giờ từ **07:00 AM** đến **09:00 PM**.
- Thẻ ca học 3D phân màu trực quan:
  - **1 Kèm 1:** Màu xanh bạc hà (Mint Emerald).
  - **Lớp Offline:** Màu xanh đại dương (Ocean Blue).
  - **Lớp Online:** Màu tím mềm (Soft Purple) kèm link phòng học trực tuyến.
- **Nhắc nhở nhanh (Right Panel):** Tự động phát hiện và cảnh báo học sinh hết buổi (0 buổi - CRITICAL), sắp hết buổi (<= 2 buổi - WARNING), và lịch trình hôm nay.
- Nút nổi **+ Thêm ca học** kèm công cụ chống trùng lịch thông minh (Schedule Conflict Engine).

### 🏫 2. Quản lý lớp học (Classes Management)
- Phân nhóm thành 3 danh mục rõ rệt: **1-ON-1**, **OFFLINE**, **ONLINE**.
- Thanh đo sĩ số trực quan, cảnh báo khi lớp đầy.
- Ràng buộc nghiệp vụ độc quyền:
  - **Lớp 1 Kèm 1:** Sĩ số tối đa luôn cố định = 1.
  - **Lớp Offline:** Khi chỉnh sửa, chỉ cho phép đổi sĩ số tối đa; không cho phép đổi tên hoặc loại lớp nhằm bảo vệ lịch sử học tập.
  - **Lớp Online:** Cho phép thay đổi tên và sĩ số tối đa tùy biến.

### 👥 3. Quản lý học sinh (Student Management)
- Tìm kiếm tức thời theo tên hoặc số điện thoại.
- Bộ lọc nhanh theo hình thức học và theo lớp học.
- Bảng danh sách chi tiết: STT, Họ tên, SĐT, Ngày sinh, Lớp học, Loại lớp, Số buổi còn lại, Thao tác.
- Huy hiệu cảnh báo thông minh:
  - `Số buổi <= 2`: Huy hiệu cảnh báo màu vàng (Warning).
  - `Số buổi == 0`: Huy hiệu khẩn cấp màu đỏ (Critical).
- Phím tắt thu học phí nhanh ngay trên từng dòng học sinh.

### 💰 4. Quản lý học phí (Tuition & Financials)
- Thống kê thời gian thực: Tổng doanh thu, số lượt đóng, số học viên cần đóng tiếp.
- Thu học phí với các nút chọn nhanh mức tiền (+800k, +1.6tr, +2.4tr, +3.2tr) và cộng dồn tự động số buổi học khả dụng vào tài khoản học sinh.
- Hiển thị chuẩn định dạng tiền tệ Việt Nam: `1.600.000 ₫`.

### ⚙ 5. Cài đặt & Sao lưu dữ liệu (Settings & Backup)
- Cập nhật thông tin trung tâm, tên giáo viên phụ trách, số điện thoại, thời lượng buổi học mặc định.
- Quản lý sao lưu: Tạo snapshot sao lưu tức thời, xem lịch sử và khôi phục (Restore) an toàn với cơ chế kiểm tra tính toàn vẹn trước khi ghi đè.

---

## 3. Kiến trúc hệ thống (System Architecture)

```text
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                           │
│           (CustomTkinter 6.0+, Pillow 10.4+)                │
│                                                             │
│  App Shell • Sidebar (5 tabs) • Topbar • ViewRouter         │
│  CalendarScreen • StudentsScreen • ClassesScreen            │
│  PaymentsScreen • SettingsScreen                            │
│  Modal Dialogs (Student, Class, Schedule, Attendance, Pay)  │
│  Theme Design System (Mint Emerald, Ocean Blue, Soft Purple)│
└──────────────────────────┬──────────────────────────────────┘
                           │ Consumes DTOs & Invokes Services
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND APPLICATION                      │
│                                                             │
│  StudentService • ClassService • ScheduleService            │
│  AttendanceService • PaymentService • ReminderService       │
│  DashboardService • Conflict Engine • DTOs (Pydantic v2)   │
└──────────────────────────┬──────────────────────────────────┘
                           │ Orchestrates Models & Repositories
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND DOMAIN                         │
│                                                             │
│  Entities: Student, ClassModel, Schedule, Attendance, Pay   │
│  Enums: ClassType, AttendanceStatus, ScheduleStatus         │
│  Repository Interfaces (ABCs)                               │
└──────────────────────────┬──────────────────────────────────┘
                           ▲
                           │ Implements Contracts
┌──────────────────────────┴──────────────────────────────────┐
│                  BACKEND INFRASTRUCTURE                     │
│                                                             │
│  JsonStudentRepository • JsonClassRepository                │
│  JsonScheduleRepository • JsonAttendanceRepository          │
│  JsonPaymentRepository • JsonHolidayRepository              │
│  Atomic Writer (tempfile + fsync + os.replace)              │
│  BackupManager • DataInitializer                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                      data/*.json
```

---

## 4. Cấu trúc thư mục (Folder Tree)

```text
DaoPiano/
├── main.py                    # Điểm khởi chạy ứng dụng (Bootstrap & App Shell)
├── requirements.txt           # Danh sách thư viện phụ thuộc
├── pytest.ini                 # Cấu hình Pytest
├── README.md                  # Tài liệu hướng dẫn
├── .gitignore
│
├── frontend/                  # TOÀN BỘ GIAO DIỆN (FRONTEND GUI)
│   ├── app.py                 # Cửa sổ chính PianoApp
│   ├── router.py              # Bộ điều hướng chuyển màn hình ViewRouter
│   ├── theme.py               # Design System: Colors, Fonts, Geometry
│   ├── components/            # Các thành phần giao diện tái sử dụng
│   │   ├── icon_loader.py     # Quản lý & cache icon SVG/PNG
│   │   ├── sidebar.py         # Thanh điều hướng bên trái
│   │   ├── topbar.py          # Thanh tiêu đề và trạng thái
│   │   ├── buttons.py         # Nút bấm theo style neumorphism
│   │   ├── cards.py           # Khối hiển thị thẻ
│   │   ├── badges.py          # Huy hiệu trạng thái
│   │   ├── table.py           # Bảng dữ liệu tùy biến
│   │   ├── calendar_picker.py # Bộ chọn ngày lịch trực quan
│   │   ├── dialogs.py         # Khung popup cơ bản
│   │   ├── toast.py           # Thông báo nổi (Toasts)
│   │   ├── empty_state.py     # Giao diện khi danh sách trống
│   │   └── loading.py         # Vòng quay tải trang
│   ├── dialogs/               # Các cửa sổ thao tác chi tiết
│   │   ├── student_dialog.py  # Thêm / Sửa học sinh & chọn lịch tuần
│   │   ├── class_dialog.py    # Thêm / Sửa lớp học
│   │   ├── schedule_dialog.py # Thêm ca học đơn lẻ
│   │   ├── attendance_dialog.py # Điểm danh ca học
│   │   ├── payment_dialog.py  # Thu học phí & cộng buổi
│   │   ├── reschedule_dialog.py # Đổi lịch học bù cho học sinh
│   │   ├── quick_lessons_dialog.py # Điều chỉnh buổi học nhanh
│   │   └── holiday_dialog.py  # Quản lý ngày nghỉ lễ
│   └── screens/               # 5 Màn hình chức năng chính
│       ├── calendar_screen.py # Lịch biểu tuần (Weekly Calendar)
│       ├── students_screen.py # Quản lý học sinh
│       ├── classes_screen.py  # Quản lý lớp học
│       ├── payments_screen.py # Quản lý học phí
│       └── settings_screen.py # Cài đặt & Sao lưu dữ liệu
│
├── backend/                   # TOÀN BỘ LOGIC NGHIỆP VỤ & LƯU TRỮ (BACKEND)
│   ├── config/                # Cấu hình hệ thống
│   │   ├── app_config.py      # Đọc/ghi cấu hình trung tâm
│   │   ├── constants.py       # Hằng số ứng dụng
│   │   └── theme.py           # Re-export theme tương thích ngược
│   ├── core/                  # Tiện ích nền tảng (Shared Kernel)
│   │   ├── exceptions.py      # Hệ thống ngoại lệ tùy chỉnh
│   │   ├── result.py          # Kiểu Result (Ok / Err)
│   │   ├── enums.py           # Các enum định danh
│   │   ├── ids.py             # Sinh mã định danh ngẫu nhiên
│   │   ├── dates.py           # Tiện ích xử lý ngày tháng
│   │   ├── time_utils.py      # Tiện ích xử lý giờ & chống trùng lịch
│   │   ├── validators.py      # Tiện ích kiểm tra tính hợp lệ dữ liệu
│   │   └── event_bus.py       # Event Bus phân tách giao tiếp lỏng
│   ├── domain/                # Thực thể nghiệp vụ & Repository contracts
│   │   ├── models/            # Domain Entities (Pydantic v2)
│   │   │   ├── student.py
│   │   │   ├── class_model.py
│   │   │   ├── schedule.py
│   │   │   ├── attendance.py
│   │   │   ├── payment.py
│   │   │   ├── holiday.py
│   │   │   └── reminder.py
│   │   └── repositories/      # Abstract Repository Interfaces (ABCs)
│   │       ├── student_repository.py
│   │       ├── class_repository.py
│   │       ├── schedule_repository.py
│   │       ├── attendance_repository.py
│   │       ├── payment_repository.py
│   │       └── holiday_repository.py
│   ├── infrastructure/        # Tầng lưu trữ tệp tin nguyên tử & JSON
│   │   ├── storage/
│   │   │   ├── atomic_writer.py # Ghi file nguyên tử fsync + replace
│   │   │   ├── json_storage.py  # Cache in-memory & quản lý IO
│   │   │   ├── backup_manager.py # Sao lưu & Khôi phục snapshot
│   │   │   └── data_initializer.py # Khởi tạo dữ liệu mặc định
│   │   └── repositories/      # Triển khai Repository bằng JSON
│   │       ├── json_student_repository.py
│   │       ├── json_class_repository.py
│   │       ├── json_schedule_repository.py
│   │       ├── json_attendance_repository.py
│   │       ├── json_payment_repository.py
│   │       └── json_holiday_repository.py
│   └── application/           # Dịch vụ ứng dụng & DTOs
│       ├── dto/               # Data Transfer Objects
│       │   ├── student_dto.py
│       │   ├── class_dto.py
│       │   ├── schedule_dto.py
│       │   ├── attendance_dto.py
│       │   └── payment_dto.py
│       └── services/          # Application Services
│           ├── student_service.py
│           ├── class_service.py
│           ├── schedule_service.py
│           ├── attendance_service.py
│           ├── payment_service.py
│           ├── reminder_service.py
│           ├── holiday_service.py
│           └── dashboard_service.py
│
├── data/                      # Lưu trữ dữ liệu JSON (Tự khởi tạo)
│   ├── students.json
│   ├── classes.json
│   ├── schedules.json
│   ├── attendances.json
│   ├── payments.json
│   └── settings.json
│
├── backups/                   # Lưu trữ các bản sao lưu timestamped
├── scripts/                   # Script tạo dữ liệu mẫu và dọn dẹp
│   ├── seed_demo_data.py
│   └── reset_data.py
│
└── tests/                     # Bộ kiểm thử tự động
    ├── unit/
    │   ├── test_models.py
    │   ├── test_storage.py
    │   ├── test_students.py
    │   ├── test_classes.py
    │   ├── test_schedule.py
    │   ├── test_attendance.py
    │   ├── test_payment.py
    │   └── test_reminders.py
    └── integration/
        └── test_application_flow.py
```

---

## 5. Cài đặt & Khởi chạy

### Yêu cầu môi trường
- **Python 3.10+** (đã kiểm thử và tối ưu trên Python 3.12)
- Hỗ trợ đầy đủ macOS (Intel & Apple Silicon M1/M2/M3/M4) và Windows 10/11.

### Bước 1: Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 2: Tạo dữ liệu mẫu (Khuyến nghị cho lần chạy đầu)
```bash
python scripts/seed_demo_data.py
```
*Script sẽ tạo 15 học sinh mẫu, 11 lớp học (Online, Offline, 1-on-1), lịch học trong tuần hiện tại, điểm danh và các phiếu thu học phí mẫu.*

### Bước 3: Khởi chạy ứng dụng Desktop
```bash
python main.py
```

---

## 6. Chạy kiểm thử tự động (Testing)

Toàn bộ nghiệp vụ, công thức trừ buổi, kiểm tra xung đột thời gian và lưu trữ đều có thể chạy headless không cần mở GUI:

```bash
python -m pytest tests -v
```

Kết quả: **32/32 tests PASSED** bao gồm kiểm thử đơn vị (Unit Tests) và kiểm thử quy trình toàn diện (Integration Tests).

---

## 7. Đặt lại dữ liệu sạch (Reset Data)
Nếu cần đưa hệ thống về trạng thái ban đầu để bàn giao hoặc bắt đầu nhập liệu mới:
```bash
python scripts/reset_data.py
```

---

## 8. Đảm bảo an toàn dữ liệu & Chống hỏng tệp (Atomic Write)
Mỗi thao tác ghi dữ liệu vào thư mục `data/` đều tuân thủ các bước:
1. Ghi vào file tạm thời `.filename.tmp` cùng phân vùng đĩa.
2. Ép xả bộ nhớ đệm ứng dụng (`f.flush()`).
3. Gọi hàm đồng bộ phần cứng hệ điều hành (`os.fsync`) đảm bảo dữ liệu ghi vật lý xuống ổ cứng.
4. Thực hiện hàm đổi tên nguyên tử (`os.replace`) thay thế file đích trong tích tắc.
5. Nếu xảy ra lỗi hoặc ngắt nguồn, file tạm bị hủy và file gốc vẫn nguyên vẹn 100%.
#   D a o - P i a n o  
 