"""High-DPI Dynamic Pillow Icon Generation and Caching System."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple, Optional
from PIL import Image, ImageDraw
import customtkinter as ctk
from frontend.theme import Theme


class IconLoader:
    """Provides vector-like antialiased dynamic CTkImage icons with memory caching."""

    _cache: Dict[Tuple[str, int, str], ctk.CTkImage] = {}

    @classmethod
    def get_icon(cls, name: str, size: int = 20, color: Optional[str] = None) -> ctk.CTkImage:
        """Retrieve cached CTkImage or dynamically render a crisp icon using Pillow."""
        fill_color = color or Theme.colors.TEXT_PRIMARY
        cache_key = (name, size, fill_color)

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Check if asset exists on disk first
        icon_path = Path("assets") / "icons" / f"{name}.png"
        if icon_path.exists():
            try:
                pil_img = Image.open(icon_path).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
                cls._cache[cache_key] = ctk_img
                return ctk_img
            except Exception:
                pass

        # Dynamically generate crisp high-res 4x supersampled icon
        img = cls._draw_dynamic_icon(name, size * 4, fill_color)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        cls._cache[cache_key] = ctk_img
        return ctk_img

    @classmethod
    def _draw_dynamic_icon(cls, name: str, canvas_size: int, color_hex: str) -> Image.Image:
        """Render vector-like geometry into a supersampled transparent PIL Image."""
        img = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        s = canvas_size
        pad = s * 0.12
        stroke = max(2, int(s * 0.08))

        # Parse hex color
        hex_clean = color_hex.lstrip("#")
        if len(hex_clean) == 6:
            r, g, b = tuple(int(hex_clean[i : i + 2], 16) for i in (0, 2, 4))
            rgba = (r, g, b, 255)
        else:
            rgba = (70, 80, 95, 255)

        match name:
            case "calendar":
                # Calendar outline & top binder tabs
                draw.rounded_rectangle([pad, pad * 1.5, s - pad, s - pad], radius=s * 0.1, outline=rgba, width=stroke)
                draw.line([pad, pad * 3.2, s - pad, pad * 3.2], fill=rgba, width=stroke)
                # Binder pegs
                draw.line([pad * 2.2, pad * 0.6, pad * 2.2, pad * 1.8], fill=rgba, width=stroke)
                draw.line([s - pad * 2.2, pad * 0.6, s - pad * 2.2, pad * 1.8], fill=rgba, width=stroke)
                # Day dot grid
                dot_r = stroke * 0.6
                for gx in [pad * 2.2, s / 2, s - pad * 2.2]:
                    for gy in [pad * 4.6, pad * 6.2]:
                        draw.ellipse([gx - dot_r, gy - dot_r, gx + dot_r, gy + dot_r], fill=rgba)

            case "students":
                # User head & body
                cx = s / 2
                head_r = s * 0.16
                draw.ellipse([cx - head_r, pad * 1.2, cx + head_r, pad * 1.2 + head_r * 2], outline=rgba, width=stroke)
                draw.arc([pad * 1.2, pad * 3.6, s - pad * 1.2, s + pad * 1.8], start=190, end=350, fill=rgba, width=stroke)

            case "classes":
                # School graduation / classroom podium
                cx, cy = s / 2, s * 0.38
                draw.polygon([(pad, cy), (cx, pad * 1.2), (s - pad, cy), (cx, cy + (cy - pad * 1.2))], outline=rgba, width=stroke)
                draw.line([cx, cy + (cy - pad * 1.2), cx, s - pad * 1.2], fill=rgba, width=stroke)
                draw.arc([pad * 1.5, cy, s - pad * 1.5, s - pad * 0.5], start=0, end=180, fill=rgba, width=stroke)

            case "payment":
                # Credit card / banknote
                draw.rounded_rectangle([pad, pad * 2.0, s - pad, s - pad * 2.0], radius=s * 0.1, outline=rgba, width=stroke)
                draw.ellipse([s / 2 - stroke * 2, s / 2 - stroke * 2, s / 2 + stroke * 2, s / 2 + stroke * 2], outline=rgba, width=stroke)
                draw.line([pad, pad * 3.5, s - pad, pad * 3.5], fill=rgba, width=stroke)

            case "settings":
                # Minimalist gear / cog
                cx, cy = s / 2, s / 2
                draw.ellipse([cx - s * 0.18, cy - s * 0.18, cx + s * 0.18, cy + s * 0.18], outline=rgba, width=stroke)
                for deg in range(0, 360, 45):
                    draw.arc([cx - s * 0.35, cy - s * 0.35, cx + s * 0.35, cy + s * 0.35], start=deg - 10, end=deg + 10, fill=rgba, width=stroke * 2)

            case "plus":
                cx, cy = s / 2, s / 2
                draw.line([cx, pad, cx, s - pad], fill=rgba, width=stroke)
                draw.line([pad, cy, s - pad, cy], fill=rgba, width=stroke)

            case "edit":
                draw.line([pad * 1.5, s - pad * 1.5, s - pad * 1.5, pad * 1.5], fill=rgba, width=stroke)
                draw.polygon([(pad * 1.2, s - pad * 1.2), (pad * 1.2, s - pad * 2.4), (pad * 2.4, s - pad * 1.2)], fill=rgba)

            case "delete":
                # Trash can
                draw.line([pad, pad * 2.2, s - pad, pad * 2.2], fill=rgba, width=stroke)
                draw.line([pad * 2.2, pad * 1.2, s - pad * 2.2, pad * 1.2], fill=rgba, width=stroke)
                draw.rounded_rectangle([pad * 1.8, pad * 2.2, s - pad * 1.8, s - pad], radius=s * 0.08, outline=rgba, width=stroke)
                draw.line([s / 2, pad * 3.2, s / 2, s - pad * 1.8], fill=rgba, width=stroke)

            case "search":
                cr = s * 0.22
                draw.ellipse([pad * 1.2, pad * 1.2, pad * 1.2 + cr * 2, pad * 1.2 + cr * 2], outline=rgba, width=stroke)
                draw.line([pad * 1.2 + cr * 1.6, pad * 1.2 + cr * 1.6, s - pad, s - pad], fill=rgba, width=stroke)

            case "check":
                draw.line([pad, s * 0.55, s * 0.42, s - pad * 1.2], fill=rgba, width=stroke)
                draw.line([s * 0.42, s - pad * 1.2, s - pad, pad * 1.5], fill=rgba, width=stroke)

            case "close":
                draw.line([pad * 1.5, pad * 1.5, s - pad * 1.5, s - pad * 1.5], fill=rgba, width=stroke)
                draw.line([s - pad * 1.5, pad * 1.5, pad * 1.5, s - pad * 1.5], fill=rgba, width=stroke)

            case "arrow_left":
                draw.line([s - pad * 1.5, s / 2, pad * 1.5, s / 2], fill=rgba, width=stroke)
                draw.line([pad * 1.5, s / 2, s * 0.45, pad * 1.5], fill=rgba, width=stroke)
                draw.line([pad * 1.5, s / 2, s * 0.45, s - pad * 1.5], fill=rgba, width=stroke)

            case "arrow_right":
                draw.line([pad * 1.5, s / 2, s - pad * 1.5, s / 2], fill=rgba, width=stroke)
                draw.line([s - pad * 1.5, s / 2, s * 0.55, pad * 1.5], fill=rgba, width=stroke)
                draw.line([s - pad * 1.5, s / 2, s * 0.55, s - pad * 1.5], fill=rgba, width=stroke)

            case "warning":
                draw.polygon([(s / 2, pad), (s - pad, s - pad), (pad, s - pad)], outline=rgba, width=stroke)
                draw.line([s / 2, s * 0.4, s / 2, s * 0.65], fill=rgba, width=stroke)
                draw.ellipse([s / 2 - stroke / 2, s * 0.76 - stroke / 2, s / 2 + stroke / 2, s * 0.76 + stroke / 2], fill=rgba)

            case "piano":
                # Piano keys symbol
                draw.rounded_rectangle([pad, pad * 1.5, s - pad, s - pad * 1.5], radius=s * 0.08, outline=rgba, width=stroke)
                w_third = (s - pad * 2) / 3
                draw.line([pad + w_third, pad * 1.5, pad + w_third, s - pad * 1.5], fill=rgba, width=stroke)
                draw.line([pad + w_third * 2, pad * 1.5, pad + w_third * 2, s - pad * 1.5], fill=rgba, width=stroke)
                draw.rectangle([pad + w_third * 0.75, pad * 1.5, pad + w_third * 1.25, s * 0.58], fill=rgba)
                draw.rectangle([pad + w_third * 1.75, pad * 1.5, pad + w_third * 2.25, s * 0.58], fill=rgba)

            case _:
                # Generic fallback dot circle
                draw.ellipse([pad, pad, s - pad, s - pad], outline=rgba, width=stroke)
                draw.ellipse([s / 2 - stroke, s / 2 - stroke, s / 2 + stroke, s / 2 + stroke], fill=rgba)

        return img
