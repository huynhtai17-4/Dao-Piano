"""Tabular data representation component."""

from __future__ import annotations
from typing import List, Tuple, Callable, Any
import customtkinter as ctk
from frontend.theme import Theme


class DataTable(ctk.CTkFrame):
    """Clean data table with styled header and scrollable body rows."""

    def __init__(self, master, columns: List[Tuple], **kwargs):
        """
        Args:
            columns: List of (Column Title, minsize_or_weight) or (Column Title, minsize, weight)
        """
        super().__init__(
            master=master,
            fg_color=Theme.colors.BG_CARD,
            border_color=Theme.colors.BORDER_SUBTLE,
            border_width=1,
            corner_radius=Theme.radius.CARD,
            **kwargs,
        )
        self.columns = columns
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header Frame (padx=(8, 24) compensates for vertical scrollbar)
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=Theme.colors.BG_MUTED,
            corner_radius=Theme.radius.CARD,
            height=42,
        )
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=(8, 24), pady=(8, 4))
        for col_idx, col_spec in enumerate(self.columns):
            title = col_spec[0]
            minsize = col_spec[1] if len(col_spec) > 1 else 100
            weight = col_spec[2] if len(col_spec) > 2 else 0
            self.header_frame.grid_columnconfigure(col_idx, minsize=minsize, weight=weight)
            lbl = ctk.CTkLabel(
                self.header_frame,
                text=title,
                font=Theme.fonts.CAPTION_BOLD,
                text_color=Theme.colors.TEXT_SECONDARY,
                anchor="w",
            )
            lbl.grid(row=0, column=col_idx, sticky="w", padx=10, pady=10)

        # Scrollable Body Frame
        self.body_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.body_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))

        self._row_count = 0

    def clear(self) -> None:
        """Clear all table rows."""
        for widget in self.body_scroll.winfo_children():
            widget.destroy()
        self._row_count = 0

    def add_row(self, cells: List[Any], on_click: Callable | None = None) -> ctk.CTkFrame:
        """Add a row of widgets or text cells."""
        row_frame = ctk.CTkFrame(
            self.body_scroll,
            fg_color=Theme.colors.BG_CARD if self._row_count % 2 == 0 else "#FAFAFA",
            corner_radius=8,
            height=46,
        )
        row_frame.pack(fill="x", padx=4, pady=2)
        for col_idx, col_spec in enumerate(self.columns):
            minsize = col_spec[1] if len(col_spec) > 1 else 100
            weight = col_spec[2] if len(col_spec) > 2 else 0
            row_frame.grid_columnconfigure(col_idx, minsize=minsize, weight=weight)

        for col_idx, cell in enumerate(cells):
            if isinstance(cell, ctk.CTkBaseClass):
                cell.master = row_frame
                cell.grid(row=0, column=col_idx, sticky="w", padx=10, pady=6)
            else:
                lbl = ctk.CTkLabel(
                    row_frame,
                    text=str(cell),
                    font=Theme.fonts.BODY,
                    text_color=Theme.colors.TEXT_PRIMARY,
                    anchor="w",
                )
                lbl.grid(row=0, column=col_idx, sticky="w", padx=10, pady=10)

        self._row_count += 1
        return row_frame
