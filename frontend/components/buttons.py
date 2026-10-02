"""Reusable CustomTkinter button components following design system tokens."""

from __future__ import annotations
from typing import Optional, Callable
import customtkinter as ctk
from frontend.theme import Theme


class PrimaryButton(ctk.CTkButton):
    """Primary emerald action button."""

    def __init__(self, master, text: str, command: Optional[Callable] = None, icon: Optional[ctk.CTkImage] = None, width: int = 140, height: int = 38, **kwargs):
        super().__init__(
            master=master,
            text=text,
            image=icon,
            command=command,
            width=width,
            height=height,
            fg_color=Theme.colors.EMERALD,
            hover_color=Theme.colors.EMERALD_HOVER,
            text_color=Theme.colors.TEXT_WHITE,
            font=Theme.fonts.BODY_BOLD,
            corner_radius=Theme.radius.BUTTON,
            compound="left",
            **kwargs,
        )


class OceanButton(ctk.CTkButton):
    """Ocean blue button for secondary primary actions."""

    def __init__(self, master, text: str, command: Optional[Callable] = None, icon: Optional[ctk.CTkImage] = None, width: int = 140, height: int = 38, **kwargs):
        super().__init__(
            master=master,
            text=text,
            image=icon,
            command=command,
            width=width,
            height=height,
            fg_color=Theme.colors.OCEAN,
            hover_color=Theme.colors.OCEAN_HOVER,
            text_color=Theme.colors.TEXT_WHITE,
            font=Theme.fonts.BODY_BOLD,
            corner_radius=Theme.radius.BUTTON,
            compound="left",
            **kwargs,
        )


class OutlineButton(ctk.CTkButton):
    """Subtle bordered white surface button."""

    def __init__(self, master, text: str, command: Optional[Callable] = None, icon: Optional[ctk.CTkImage] = None, width: int = 120, height: int = 38, **kwargs):
        super().__init__(
            master=master,
            text=text,
            image=icon,
            command=command,
            width=width,
            height=height,
            fg_color=Theme.colors.BG_CARD,
            hover_color=Theme.colors.BG_CARD_HOVER,
            text_color=Theme.colors.TEXT_PRIMARY,
            border_width=1,
            border_color=Theme.colors.BORDER_SUBTLE,
            font=Theme.fonts.BODY_BOLD,
            corner_radius=Theme.radius.BUTTON,
            compound="left",
            **kwargs,
        )


class DangerButton(ctk.CTkButton):
    """Red destructive action button."""

    def __init__(self, master, text: str, command: Optional[Callable] = None, icon: Optional[ctk.CTkImage] = None, width: int = 120, height: int = 38, **kwargs):
        super().__init__(
            master=master,
            text=text,
            image=icon,
            command=command,
            width=width,
            height=height,
            fg_color=Theme.colors.DANGER,
            hover_color=Theme.colors.DANGER_HOVER,
            text_color=Theme.colors.TEXT_WHITE,
            font=Theme.fonts.BODY_BOLD,
            corner_radius=Theme.radius.BUTTON,
            compound="left",
            **kwargs,
        )


class IconButton(ctk.CTkButton):
    """Compact square icon-only button."""

    def __init__(self, master, icon: ctk.CTkImage, command: Optional[Callable] = None, size: int = 34, **kwargs):
        super().__init__(
            master=master,
            text="",
            image=icon,
            command=command,
            width=size,
            height=size,
            fg_color=Theme.colors.BG_CARD,
            hover_color=Theme.colors.BG_CARD_HOVER,
            border_width=1,
            border_color=Theme.colors.BORDER_SUBTLE,
            corner_radius=Theme.radius.BUTTON,
            **kwargs,
        )
