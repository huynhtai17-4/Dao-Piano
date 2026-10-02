"""Validation helpers for phone numbers, strings, and numeric constraints."""

import re

PHONE_REGEX = re.compile(r"^(0|\+84)[0-9]{8,10}$")


def validate_phone(phone: str) -> bool:
    """Validate standard Vietnamese phone number format (starts with 0 or +84 followed by 8-10 digits)."""
    cleaned = re.sub(r"[\s\-\.]", "", phone.strip())
    return bool(PHONE_REGEX.match(cleaned))


def sanitize_phone(phone: str) -> str:
    """Clean phone number of spaces, hyphens, and periods, standardizing to 0xxxxxxxxx."""
    cleaned = re.sub(r"[\s\-\.]", "", phone.strip())
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    return cleaned


def validate_non_empty_str(value: str, field_name: str = "Trường") -> str:
    """Validate that string is not blank."""
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} không được để trống.")
    return stripped


