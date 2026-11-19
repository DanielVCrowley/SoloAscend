"""Общие константы и форматирование для экранов."""
import time
from datetime import date

import flet as ft

from game import Equipment

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

TABS = [
    ("Статус", ft.Icons.PERSON_OUTLINE, ft.Icons.PERSON_ROUNDED),
    ("Квест", ft.Icons.PLAY_ARROW_OUTLINED, ft.Icons.PLAY_ARROW_ROUNDED),
    ("Программы", ft.Icons.SCHOOL_OUTLINED, ft.Icons.SCHOOL),
    ("Навыки", ft.Icons.ACCOUNT_TREE_OUTLINED, ft.Icons.ACCOUNT_TREE),
    ("История", ft.Icons.HISTORY, ft.Icons.HISTORY_ROUNDED),
]

EQUIPMENT_ICONS = {
    Equipment.PULL_BAR: ft.Icons.SPORTS_GYMNASTICS,
    Equipment.DIP_BARS: ft.Icons.ACCESSIBILITY_NEW,
    Equipment.DUMBBELLS: ft.Icons.FITNESS_CENTER,
    Equipment.KETTLEBELL: ft.Icons.SPORTS_MMA,
    Equipment.BANDS: ft.Icons.LINEAR_SCALE,
}

INTRO = "Система активирована.\nОбнаружен кандидат на пробуждение.\n\nНачать регистрацию?"
ONBOARDING_STEPS = 4


def fmt_seconds(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def fmt_day(day: int) -> str:
    d = date.fromordinal(day)
    return f"{d.day} {MONTHS[d.month - 1]}", WEEKDAYS[d.weekday()]


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def seconds_left(end: float) -> int:
    return max(0, int(end - time.monotonic() + 0.999))
