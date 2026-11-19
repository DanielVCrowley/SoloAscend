"""Вкладка «История»: журнал тренировок по дням."""
import flet as ft

from common import fmt_day
from ui import (
    ACCENT, BRANCH_ICONS, GOLD, LINE, MUTED, STAT_COLORS, TEXT, card, icon, icon_badge,
    page_header, pill, text,
)


class HistoryScreen:
    def history(self, animate):
        r = lambda c: self.reveal(c, animate)
        days = self.engine.history()
        result = [r(page_header("История", "Журнал тренировок", self.level_pill()))]
        if not days:
            result.append(r(card([
                ft.Row([icon_badge(ft.Icons.HISTORY, MUTED, 56)], alignment=ft.MainAxisAlignment.CENTER),
                text("Пока пусто", TEXT, 18, ft.FontWeight.W_700, align=ft.TextAlign.CENTER),
                text("Выполни первый подход — он появится здесь.", MUTED, align=ft.TextAlign.CENTER),
            ], MUTED, padding=30, glow=0.04)))
            return result

        result.append(r(card([ft.Row([
            self.metric(str(len(days)), "дней", ACCENT),
            self.metric(str(sum(d["sets"] for d in days)), "подходов", TEXT),
            self.metric(str(sum(d["xp"] for d in days)), "XP", GOLD),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND)], glow=0.1)))

        for d in days:
            day, weekday = fmt_day(d["day"])
            rows = [
                ft.Row([
                    ft.Column([text(day, TEXT, 18, ft.FontWeight.W_800), text(weekday, MUTED, 12)], spacing=0, expand=True),
                    pill(f"+{d['xp']} XP", ACCENT),
                ]),
                ft.Row([
                    pill(f"{d['sets']} подх.", MUTED, ft.Icons.DONE_ALL),
                    pill(f"≈{d['kcal']} ккал", GOLD, ft.Icons.LOCAL_FIRE_DEPARTMENT),
                ], spacing=6),
                ft.Divider(color=LINE, height=1),
            ]
            for step, values in d["entries"]:
                rows.append(ft.Row([
                    icon(BRANCH_ICONS[step.branch], STAT_COLORS[step.branch.stat], 18),
                    ft.Column([
                        text(step.name, TEXT, 14, ft.FontWeight.W_600),
                        text(" · ".join(step.fmt(v) for v in values), MUTED, 12, mono=True),
                    ], spacing=2, expand=True),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START))
            result.append(r(card(rows, glow=0.06, spacing=10)))
        return result
