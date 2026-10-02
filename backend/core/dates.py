"""Date manipulation and formatting utilities for calendar and scheduling."""

from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import List, Tuple

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DISPLAY_DATE_FORMAT = "%d/%m/%Y"

WEEKDAY_VN = [
    "Thứ 2",
    "Thứ 3",
    "Thứ 4",
    "Thứ 5",
    "Thứ 6",
    "Thứ 7",
    "Chủ Nhật",
]

WEEKDAY_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def today_date() -> date:
    """Return today's date object."""
    return date.today()


def today_str() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return today_date().strftime(DATE_FORMAT)


def now_iso() -> str:
    """Return current timestamp in ISO 8601 string format."""
    return datetime.now().strftime(DATETIME_FORMAT)


def parse_date(date_str: str) -> date:
    """Parse date from YYYY-MM-DD or DD/MM/YYYY string."""
    try:
        if "/" in date_str:
            return datetime.strptime(date_str, DISPLAY_DATE_FORMAT).date()
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except Exception as e:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or DD/MM/YYYY") from e


def format_date_display(d: date | str) -> str:
    """Format date to DD/MM/YYYY for user interface."""
    if isinstance(d, str):
        d = parse_date(d)
    return d.strftime(DISPLAY_DATE_FORMAT)


def format_date_iso(d: date) -> str:
    """Format date to standard YYYY-MM-DD string."""
    return d.strftime(DATE_FORMAT)


def get_week_bounds(target_date: date) -> Tuple[date, date]:
    """Return the (Monday, Sunday) date range for the week containing target_date."""
    # target_date.weekday(): Monday is 0, Sunday is 6
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week


def get_week_days(target_date: date) -> List[date]:
    """Return list of 7 consecutive dates (Monday through Sunday) for the given week."""
    start_of_week, _ = get_week_bounds(target_date)
    return [start_of_week + timedelta(days=i) for i in range(7)]


def get_day_of_week_label(d: date, lang: str = "vi") -> str:
    """Return weekday label (e.g. 'Thứ 2' or 'MON')."""
    idx = d.weekday()
    if lang == "en":
        return WEEKDAY_EN[idx]
    return WEEKDAY_VN[idx]
