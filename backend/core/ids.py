"""Identifier generator producing collision-resistant, prefix-tagged unique IDs."""

import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a clean unique identifier, optionally prepended with an entity prefix.

    Examples:
        generate_id("stu") -> "stu_4a2c9f..."
        generate_id() -> "4a2c9f..."
    """
    token = uuid.uuid4().hex[:12]
    if prefix:
        return f"{prefix}_{token}"
    return token
