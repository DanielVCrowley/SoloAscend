"""Точка входа: flet run src/main.py"""
import os

import flet as ft

from engine import Engine
from ui import ACCENT, ACCENT_2, BG, BG_SOFT, DANGER, LINE, MUTED, TEXT

from app import AscendApp


def data_path() -> str:
    base = os.getenv("FLET_APP_STORAGE_DATA") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")
    return os.path.join(base, "ascend.json")


def main(page: ft.Page):
    page.title = "Ascend"
    page.bgcolor = BG
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = page.dark_theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            on_primary=BG,
            secondary=ACCENT_2,
            surface=BG_SOFT,
            on_surface=TEXT,
            on_surface_variant=MUTED,
            outline=LINE,
            error=DANGER,
        ),
    )
    app = AscendApp(page, Engine(data_path()))
    page.on_app_lifecycle_state_change = app.on_lifecycle
    app.start()


if __name__ == "__main__":
    ft.run(main)
