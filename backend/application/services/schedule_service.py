"""Schedule management and calendar conflict detection engine."""

from __future__ import annotations
from datetime import date, timedelta
from typing import List, Optional
from backend.domain.models.schedule import Schedule
from backend.domain.repositories.schedule_repository import ScheduleRepository
from backend.domain.repositories.student_repository import StudentRepository
from backend.domain.repositories.class_repository import ClassRepository
from backend.domain.repositories.attendance_repository import AttendanceRepository
from backend.application.dto.schedule_dto import ScheduleCreateDTO, ScheduleUpdateDTO, ScheduleResponseDTO
from backend.core.dates import parse_date, format_date_iso, get_week_bounds
from backend.core.time_utils import is_time_overlap, time_to_minutes
from backend.core.enums import ClassType, ScheduleStatus, AttendanceStatus
from backend.core.exceptions import NotFoundError, ScheduleConflictError
from backend.core.event_bus import event_bus


COLOR_MAP = {
    ClassType.ONE_ON_ONE: "#10B981",  # Mint Emerald
    ClassType.OFFLINE: "#0284C7",     # Ocean Blue
    ClassType.ONLINE: "#8B5CF6",      # Soft Purple
}


class ScheduleService:
    """Manages lesson scheduling, calendar week queries, and conflict detection."""

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
        student_repo: StudentRepository,
        class_repo: ClassRepository,
        attendance_repo: Optional[AttendanceRepository] = None,
    ) -> None:
        self.schedule_repo = schedule_repo
        self.student_repo = student_repo
        self.class_repo = class_repo
        self.attendance_repo = attendance_repo

    def _to_response_dto(
        self,
        s: Schedule,
        student_cache: Optional[dict] = None,
        class_cache: Optional[dict] = None,
    ) -> ScheduleResponseDTO:
        student_name = None
        if s.student_id:
            if student_cache and s.student_id in student_cache:
                st = student_cache[s.student_id]
                student_name = st.name if st else None
            else:
                st = self.student_repo.get_by_id(s.student_id)
                student_name = st.name if st else None

        class_name = None
        class_type = None
        if s.class_id:
            if class_cache and s.class_id in class_cache:
                cl = class_cache[s.class_id]
            else:
                cl = self.class_repo.get_by_id(s.class_id)
            if cl:
                class_name = cl.name
                class_type = cl.class_type

        # Color assignment
        color = s.color
        if not color and class_type:
            color = COLOR_MAP.get(class_type, "#0284C7")
        elif not color:
            color = "#10B981"

        duration = time_to_minutes(s.end_time) - time_to_minutes(s.start_time)

        return ScheduleResponseDTO(
            id=s.id,
            class_id=s.class_id,
            class_name=class_name,
            class_type=class_type,
            student_id=s.student_id,
            student_name=student_name,
            date=s.date,
            day_of_week=s.day_of_week,
            start_time=s.start_time,
            end_time=s.end_time,
            duration_minutes=duration,
            location=s.location,
            online_url=s.online_url,
            color=color,
            lesson_title=s.lesson_title,
            status=s.status,
            status_display=s.status.display_name,
            original_schedule_id=s.original_schedule_id,
            rescheduled_to_id=s.rescheduled_to_id,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )

    def check_conflicts(
        self,
        target_date: str,
        start_time: str,
        end_time: str,
        student_id: Optional[str] = None,
        class_id: Optional[str] = None,
        ignore_schedule_id: Optional[str] = None,
    ) -> None:
        """Verify no schedule overlap for the student or class on the target date."""
        day_schedules = self.schedule_repo.get_by_date_range(target_date, target_date)

        for existing in day_schedules:
            if ignore_schedule_id and existing.id == ignore_schedule_id:
                continue
            if existing.status == ScheduleStatus.CANCELLED:
                continue

            # Check time overlap
            if is_time_overlap(start_time, end_time, existing.start_time, existing.end_time):
                # 1. Student conflict check
                if student_id and existing.student_id == student_id:
                    st = self.student_repo.get_by_id(student_id)
                    s_name = st.name if st else student_id
                    raise ScheduleConflictError(
                        f"Trùng lịch học: Học sinh '{s_name}' đã có buổi học lúc {existing.start_time} - {existing.end_time}."
                    )

                # 2. Class conflict check
                if class_id and existing.class_id == class_id:
                    cl = self.class_repo.get_by_id(class_id)
                    c_name = cl.name if cl else class_id
                    raise ScheduleConflictError(
                        f"Trùng lịch lớp: Lớp '{c_name}' đã có lịch dạy lúc {existing.start_time} - {existing.end_time}."
                    )

    def create_schedule(self, dto: ScheduleCreateDTO) -> ScheduleResponseDTO:
        # Check conflict
        self.check_conflicts(
            target_date=dto.date,
            start_time=dto.start_time,
            end_time=dto.end_time,
            student_id=dto.student_id,
            class_id=dto.class_id,
        )

        new_schedule = Schedule(
            class_id=dto.class_id,
            student_id=dto.student_id,
            date=dto.date,
            start_time=dto.start_time,
            end_time=dto.end_time,
            location=dto.location,
            online_url=dto.online_url,
            lesson_title=dto.lesson_title,
            color=dto.color,
            original_schedule_id=dto.original_schedule_id,
            rescheduled_to_id=dto.rescheduled_to_id,
        )

        persisted = self.schedule_repo.create(new_schedule)
        event_bus.emit("schedules_changed", persisted.id)
        return self._to_response_dto(persisted)

    def update_schedule(self, dto: ScheduleUpdateDTO) -> ScheduleResponseDTO:
        existing = self.schedule_repo.get_by_id(dto.id)
        if not existing:
            raise NotFoundError(f"Không tìm thấy buổi lịch ID '{dto.id}'.")

        # Check conflict excluding current schedule
        self.check_conflicts(
            target_date=dto.date,
            start_time=dto.start_time,
            end_time=dto.end_time,
            student_id=dto.student_id,
            class_id=dto.class_id,
            ignore_schedule_id=dto.id,
        )

        existing.class_id = dto.class_id
        existing.student_id = dto.student_id
        existing.date = dto.date
        existing.start_time = dto.start_time
        existing.end_time = dto.end_time
        existing.location = dto.location
        existing.online_url = dto.online_url
        existing.lesson_title = dto.lesson_title
        existing.status = dto.status
        existing.color = dto.color
        if dto.original_schedule_id is not None:
            existing.original_schedule_id = dto.original_schedule_id
        if dto.rescheduled_to_id is not None:
            existing.rescheduled_to_id = dto.rescheduled_to_id

        updated = self.schedule_repo.update(existing)
        event_bus.emit("schedules_changed", updated.id)
        return self._to_response_dto(updated)

    def delete_schedule(self, schedule_id: str) -> bool:
        sch = self.schedule_repo.get_by_id(schedule_id)
        if not sch:
            return False

        # If this schedule was a rescheduled session, restore the original schedule!
        orig_id = getattr(sch, "original_schedule_id", None)
        if not orig_id:
            for s in self.schedule_repo.get_all():
                if getattr(s, "rescheduled_to_id", None) == schedule_id:
                    orig_id = s.id
                    break

        if orig_id:
            orig = self.schedule_repo.get_by_id(orig_id)
            if orig:
                orig.status = ScheduleStatus.SCHEDULED
                orig.rescheduled_to_id = None
                self.schedule_repo.update(orig)

                # Clean up any RESCHEDULED attendance on original session so it is active again
                if self.attendance_repo:
                    orig_atts = self.attendance_repo.get_by_schedule_id(orig.id)
                    for att in orig_atts:
                        if att.status == AttendanceStatus.RESCHEDULED:
                            self.attendance_repo.delete(att.id)
                    event_bus.emit("attendance_changed", orig.id)

        result = self.schedule_repo.delete(schedule_id)
        event_bus.emit("schedules_changed", schedule_id)
        return result

    def cleanup_orphan_schedules(self) -> int:
        """Purge schedules belonging to deleted classes or deleted students."""
        valid_class_ids = {c.id for c in self.class_repo.get_all()}
        valid_student_ids = {s.id for s in self.student_repo.get_all()}

        all_schedules = self.schedule_repo.get_all()
        to_delete = []

        for s in all_schedules:
            is_orphan = False
            if s.class_id and s.class_id not in valid_class_ids:
                is_orphan = True
            elif s.student_id and s.student_id not in valid_student_ids:
                is_orphan = True
            elif not s.class_id and not s.student_id:
                is_orphan = True

            if is_orphan:
                to_delete.append(s.id)

        for sid in to_delete:
            self.schedule_repo.delete(sid)

        return len(to_delete)

    def ensure_recurring_class_schedules(self, horizon_weeks: int = 12) -> int:
        """Ensure all fixed classes and recurring slots are scheduled for subsequent weeks starting from creation/start date."""
        all_schedules = self.schedule_repo.get_all()
        if not all_schedules:
            return 0

        # Existing set of (class_id, student_id, date, start_time)
        existing_keys = {
            (s.class_id, s.student_id, s.date, s.start_time)
            for s in all_schedules
        }

        # Pattern: (class_id, student_id, weekday_int, start_time, end_time)
        patterns = {}
        for s in all_schedules:
            # CHỈ tự động gia hạn tuần cho các lớp học chung cố định (có class_id và không phải ca riêng của học sinh)
            if not s.class_id or s.student_id:
                continue
            # Tuyệt đối không lặp lại các ca đã hủy, ca đã đổi lịch, ca học bù / đổi lịch
            if s.status in (ScheduleStatus.CANCELLED, ScheduleStatus.RESCHEDULED):
                continue
            if getattr(s, "original_schedule_id", None):
                continue
            if "[Học bù]" in s.lesson_title or "[Đổi lịch]" in s.lesson_title:
                continue
            try:
                s_date = parse_date(s.date)
            except Exception:
                continue

            weekday = s_date.weekday()
            key = (s.class_id, s.student_id, weekday, s.start_time, s.end_time)

            if key not in patterns or s_date < patterns[key]["earliest_date"]:
                patterns[key] = {
                    "earliest_date": s_date,
                    "class_id": s.class_id,
                    "student_id": s.student_id,
                    "weekday": weekday,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "location": s.location,
                    "online_url": s.online_url,
                    "color": s.color,
                    "lesson_title": s.lesson_title,
                }

        from backend.core.dates import today_date
        today = today_date()
        max_future_date = today + timedelta(weeks=horizon_weeks)
        new_count = 0

        for key, p in patterns.items():
            base_date = p["earliest_date"]
            curr_date = base_date + timedelta(days=7)
            while curr_date <= max_future_date:
                curr_date_str = format_date_iso(curr_date)
                slot_key = (p["class_id"], p["student_id"], curr_date_str, p["start_time"])

                if slot_key not in existing_keys:
                    new_sch = Schedule(
                        class_id=p["class_id"],
                        student_id=p["student_id"],
                        date=curr_date_str,
                        start_time=p["start_time"],
                        end_time=p["end_time"],
                        location=p["location"],
                        online_url=p["online_url"],
                        color=p["color"],
                        lesson_title=p["lesson_title"],
                        status=ScheduleStatus.SCHEDULED,
                    )
                    self.schedule_repo.create(new_sch)
                    existing_keys.add(slot_key)
                    new_count += 1

                curr_date += timedelta(days=7)

        return new_count

    def get_week_schedules(self, target_date: date | str) -> List[ScheduleResponseDTO]:
        d = parse_date(target_date) if isinstance(target_date, str) else target_date
        start_d, end_d = get_week_bounds(d)

        # Purge any orphan schedules for non-existent classes/students
        self.cleanup_orphan_schedules()

        from backend.core.dates import today_date
        weeks_ahead = max(12, int((end_d - today_date()).days / 7) + 2)
        self.ensure_recurring_class_schedules(horizon_weeks=weeks_ahead)

        schedules = self.schedule_repo.get_by_date_range(
            format_date_iso(start_d), format_date_iso(end_d)
        )

        # Batch load references for fast rendering
        students = {s.id: s for s in self.student_repo.get_all()}
        classes = {c.id: c for c in self.class_repo.get_all()}

        valid_schedules = []
        for s in schedules:
            if s.class_id and s.class_id not in classes:
                continue
            if s.student_id and s.student_id not in students:
                continue
            if not s.class_id and not s.student_id:
                continue
            # Ca đã hủy hoặc ca cũ đã đổi lịch thì ẩn khỏi bảng lịch tuần
            if s.status in (ScheduleStatus.CANCELLED, ScheduleStatus.RESCHEDULED):
                continue
            valid_schedules.append(s)

        return [self._to_response_dto(s, students, classes) for s in valid_schedules]

    def get_today_schedules(self, today_iso_str: str) -> List[ScheduleResponseDTO]:
        schedules = self.schedule_repo.get_by_date_range(today_iso_str, today_iso_str)
        students = {s.id: s for s in self.student_repo.get_all()}
        classes = {c.id: c for c in self.class_repo.get_all()}
        valid_schedules = [
            s for s in schedules
            if (s.class_id in classes if s.class_id else (s.student_id in students if s.student_id else False))
            and s.status not in (ScheduleStatus.CANCELLED, ScheduleStatus.RESCHEDULED)
        ]
        return [self._to_response_dto(s, students, classes) for s in valid_schedules]
        return [self._to_response_dto(s, students, classes) for s in valid_schedules]

    def get_class_recurring_slots(self, class_id: str) -> List[dict]:
        """Extract unique recurring weekly slots (day_idx, day_name, start_time, end_time, location) for a class."""
        if not class_id:
            return []
        schedules = self.schedule_repo.get_by_class_id(class_id)
        weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        seen = set()
        slots = []
        for s in schedules:
            if s.status == ScheduleStatus.CANCELLED:
                continue
            try:
                d = parse_date(s.date)
                w_idx = d.weekday()
                day_name = weekday_names[w_idx]
                key = (w_idx, s.start_time, s.end_time)
                if key not in seen:
                    seen.add(key)
                    slots.append({
                        "day_idx": w_idx,
                        "day_name": day_name,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "location": s.location or "Phòng học 1",
                    })
            except Exception:
                continue
        slots.sort(key=lambda x: (x["day_idx"], x["start_time"]))
        return slots

    def create_class_recurring_schedules(
        self, class_id: str, slots: List[dict], num_weeks: int = 8
    ) -> int:
        """Generate recurring schedules for an entire class for upcoming weeks."""
        cl = self.class_repo.get_by_id(class_id)
        if not cl:
            return 0
        from backend.core.dates import today_date, get_week_days, format_date_iso
        today = today_date()
        count = 0
        for w in range(num_weeks):
            week_days = get_week_days(today + timedelta(weeks=w))
            for slot in slots:
                day_idx = slot["day_idx"] if isinstance(slot, dict) else slot[0]
                st = slot["start_time"] if isinstance(slot, dict) else slot[1]
                et = slot["end_time"] if isinstance(slot, dict) else slot[2]
                loc = (slot.get("location") if isinstance(slot, dict) else (slot[3] if len(slot) > 3 else None)) or "Phòng học 1"
                slot_date = week_days[day_idx]
                if slot_date >= today:
                    try:
                        self.create_schedule(
                            ScheduleCreateDTO(
                                class_id=class_id,
                                student_id=None,
                                date=format_date_iso(slot_date),
                                start_time=st,
                                end_time=et,
                                location=loc,
                                lesson_title=f"{cl.name}",
                            )
                        )
                        count += 1
                    except Exception:
                        pass
        return count

    def create_student_recurring_schedules(
        self, student_id: str, slots: List[dict], class_type: ClassType, num_weeks: int = 8, class_id: Optional[str] = None
    ) -> int:
        """Generate recurring schedules for a 1-on-1 or online student starting from current week."""
        st_obj = self.student_repo.get_by_id(student_id)
        if not st_obj:
            return 0
        from backend.core.dates import today_date, get_week_days, format_date_iso
        today = today_date()
        count = 0
        for w in range(num_weeks):
            week_days = get_week_days(today + timedelta(weeks=w))
            for slot in slots:
                day_idx = slot["day_idx"] if isinstance(slot, dict) else slot[0]
                st = slot["start_time"] if isinstance(slot, dict) else slot[1]
                et = slot["end_time"] if isinstance(slot, dict) else slot[2]
                loc = (slot.get("location") if isinstance(slot, dict) else (slot[3] if len(slot) > 3 else None)) or (
                    "Phòng Grand Piano 1" if class_type == ClassType.ONE_ON_ONE else "Phòng học 1"
                )
                slot_date = week_days[day_idx]
                # In current week (w=0) allow all selected weekdays so schedule appears immediately on calendar
                try:
                    self.create_schedule(
                        ScheduleCreateDTO(
                            class_id=class_id,
                            student_id=student_id,
                            date=format_date_iso(slot_date),
                            start_time=st,
                            end_time=et,
                            lesson_title=f"{class_type.display_name} - {st_obj.name}",
                            location=loc,
                            online_url="https://meet.google.com/dao-piano" if class_type == ClassType.ONLINE else None,
                        )
                    )
                    count += 1
                except Exception:
                    pass
        return count
