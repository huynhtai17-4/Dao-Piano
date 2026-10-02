"""Time utilities for schedule representation and conflict calculation."""

from __future__ import annotations
import re


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def validate_time_format(t_str: str) -> bool:
    """Validate that time string is formatted as HH:MM in 24-hour clock."""
    return bool(TIME_PATTERN.match(t_str.strip()))


def time_to_minutes(time_str: str) -> int:
    """Convert HH:MM string to total minutes since midnight.

    Example: "07:30" -> 450
    """
    time_str = time_str.strip()
    if not validate_time_format(time_str):
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM (24-hour).")
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight back to HH:MM string.

    Example: 450 -> "07:30"
    """
    minutes = minutes % (24 * 60)
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def is_time_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """Determine whether two time intervals [start_a, end_a) and [start_b, end_b) overlap.

    Adjacent intervals (e.g. 18:00-19:00 and 19:00-20:00) do NOT overlap.
    """
    s_a = time_to_minutes(start_a)
    e_a = time_to_minutes(end_a)
    s_b = time_to_minutes(start_b)
    e_b = time_to_minutes(end_b)

    if e_a <= s_a:
        raise ValueError(f"Invalid interval A: end_time {end_a} must be after start_time {start_a}")
    if e_b <= s_b:
        raise ValueError(f"Invalid interval B: end_time {end_b} must be after start_time {start_b}")

    return max(s_a, s_b) < min(e_a, e_b)


def format_currency_vnd(amount: int | float) -> str:
    """Format an integer amount into Vietnamese Dong currency string.

    Example: 1500000 -> "1.500.000 ₫"
    """
    return f"{int(amount):,}".replace(",", ".") + " ₫"
