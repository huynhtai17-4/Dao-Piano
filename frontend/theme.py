"""Design Tokens and Theme Configuration for Modern Glass-Neumorphism."""

from typing import Tuple


class Colors:
    """Design system color palette."""

    # Surfaces & Backgrounds
    BG_WINDOW = "#F8FAFC"          # Slate 50 (App canvas)
    BG_CARD = "#FFFFFF"            # Pure White (Floating surface)
    BG_CARD_HOVER = "#F1F5F9"      # Slate 100
    BG_SIDEBAR = "#FFFFFF"         # Floating sidebar
    BG_MUTED = "#F1F5F9"           # Slate 100 muted fills

    # Borders & Dividers
    BORDER_SUBTLE = "#E2E8F0"      # Slate 200
    BORDER_FOCUS = "#38BDF8"       # Sky 400
    BORDER_EMERALD = "#A7F3D0"     # Emerald 200

    # Typography
    TEXT_PRIMARY = "#0F172A"       # Slate 900
    TEXT_SECONDARY = "#475569"     # Slate 600
    TEXT_MUTED = "#94A3B8"         # Slate 400
    TEXT_WHITE = "#FFFFFF"

    # Accents - Mint Emerald (1-on-1 & Primary CTAs)
    EMERALD = "#10B981"            # Emerald 500
    EMERALD_HOVER = "#059669"      # Emerald 600
    EMERALD_LIGHT = "#ECFDF5"      # Emerald 50
    EMERALD_BORDER = "#6EE7B7"     # Emerald 300

    PRIMARY = "#10B981"
    PRIMARY_HOVER = "#059669"

    # Accents - Ocean Blue (Offline & Secondary Actions)
    OCEAN = "#0284C7"              # Sky 600
    OCEAN_HOVER = "#0369A1"        # Sky 700
    OCEAN_LIGHT = "#E0F2FE"        # Sky 100

    # Accents - Soft Purple (Online Classes)
    PURPLE = "#8B5CF6"             # Violet 500
    PURPLE_HOVER = "#7C3AED"       # Violet 600
    PURPLE_LIGHT = "#EDE9FE"       # Violet 100

    # Status & Alerts
    WARNING = "#F59E0B"            # Amber 500
    WARNING_LIGHT = "#FEF3C7"      # Amber 100
    WARNING_TEXT = "#B45309"       # Amber 700

    DANGER = "#EF4444"             # Red 500
    DANGER_HOVER = "#DC2626"       # Red 600
    DANGER_LIGHT = "#FEE2E2"       # Red 100
    DANGER_TEXT = "#B91C1C"        # Red 700

    INFO = "#3B82F6"               # Blue 500
    INFO_LIGHT = "#DBEAFE"         # Blue 100
    INFO_TEXT = "#1D4ED8"          # Blue 700


class Fonts:
    """Standardized typography scales using cross-platform font families."""

    FAMILY = "Segoe UI"
    FALLBACK_FAMILY = "Helvetica Neue"

    TITLE: Tuple[str, int, str] = (FAMILY, 20, "bold")
    H1: Tuple[str, int, str] = (FAMILY, 16, "bold")
    H2: Tuple[str, int, str] = (FAMILY, 14, "bold")
    BODY: Tuple[str, int] = (FAMILY, 13)
    BODY_BOLD: Tuple[str, int, str] = (FAMILY, 13, "bold")
    CAPTION: Tuple[str, int] = (FAMILY, 11)
    CAPTION_BOLD: Tuple[str, int, str] = (FAMILY, 11, "bold")
    CODE: Tuple[str, int] = ("Consolas", 12)


class Radius:
    """Standardized border radii for rounded elements."""

    CARD = 14
    MODAL = 16
    BUTTON = 8
    INPUT = 8
    BADGE = 6
    CIRCLE = 50


class Spacing:
    """Grid layout spacing dimensions."""

    XS = 4
    SM = 8
    MD = 14
    LG = 20
    XL = 28


class Theme:
    """Consolidated theme access token."""

    colors = Colors
    fonts = Fonts
    radius = Radius
    spacing = Spacing
