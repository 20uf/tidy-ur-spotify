"""Shared workflow header for the 3 main application stages."""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.ui.theme import ACCENT, BG, BG_CARD, BG_INPUT, BORDER, FG, FG_DIM

DEFAULT_WORKFLOW_STEPS = ["Configuration", "Pre-analysis", "Qualification"]


def _is_compact(page: ft.Page) -> bool:
    width = int(getattr(page.window, "width", 0) or 0)
    return width > 0 and width < 980


def build_workflow_header(
    page: ft.Page,
    current_step: int,
    subtitle: str,
    width: int | None = None,
    mode_label: str | None = None,
    progress_text: str | None = None,
    on_back_to_step2: Callable[[ft.ControlEvent], None] | None = None,
    step_labels: list[str] | None = None,
) -> ft.Container:
    """Build a unified workflow header used by setup, pre-analysis and qualification views."""
    _ = subtitle
    labels = step_labels or DEFAULT_WORKFLOW_STEPS
    compact = _is_compact(page)

    circle_size = 26 if compact else 30
    connector_width = 26 if compact else 48

    step_controls: list[ft.Control] = []
    for idx, label in enumerate(labels, start=1):
        is_done = idx < current_step
        is_current = idx == current_step
        circle_bg = ACCENT if (is_done or is_current) else BG_INPUT
        circle_fg = BG if (is_done or is_current) else FG_DIM
        step_label_color = FG if is_current else FG_DIM
        marker = "\u2713" if is_done else str(idx)

        step_controls.append(
            ft.Column(
                [
                    ft.Container(
                        width=circle_size,
                        height=circle_size,
                        border_radius=circle_size / 2,
                        alignment=ft.Alignment(0, 0),
                        bgcolor=circle_bg,
                        content=ft.Text(marker, size=11, weight=ft.FontWeight.BOLD, color=circle_fg),
                    ),
                    ft.Text(f"{idx} {label}", size=10, color=step_label_color, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            )
        )

        if idx < len(labels):
            step_controls.append(
                ft.Container(
                    width=connector_width,
                    height=2,
                    bgcolor=ACCENT if is_done else BORDER,
                    margin=ft.margin.only(top=12),
                )
            )

    right_meta_controls: list[ft.Control] = []
    if mode_label:
        right_meta_controls.append(
            ft.Container(
                bgcolor=BG_INPUT,
                border=ft.border.all(1, BORDER),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                content=ft.Text(f"Mode: {mode_label}", size=10, color=FG),
            )
        )
    if progress_text:
        right_meta_controls.append(ft.Text(progress_text, size=10, color=FG_DIM))
    if on_back_to_step2:
        right_meta_controls.append(
            ft.TextButton(
                "Back to pre-analysis",
                on_click=on_back_to_step2,
                style=ft.ButtonStyle(color=FG_DIM),
            )
        )

    content_controls: list[ft.Control] = []
    if right_meta_controls:
        content_controls.append(
            ft.Row(
                right_meta_controls,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                wrap=True,
            )
        )

    return ft.Container(
        width=width,
        bgcolor=BG_CARD,
        border=ft.border.all(1, BORDER),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        content=ft.Column(
            content_controls
            + [
                ft.Row(
                    step_controls,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                    wrap=compact,
                )
            ],
            spacing=8,
        ),
    )
