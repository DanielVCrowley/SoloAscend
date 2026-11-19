"""Разминка и заминка: таймер упражнений и смена карточек."""
import time

import flet as ft

import game
from common import fmt_seconds, seconds_left
from engine import Event
from ui import (
    ACCENT_2, DANGER, FAINT, GOLD, LINE, MUTED, SUCCESS, TEXT, alpha, card, ghost_button, icon,
    kicker, pill, ring, segments, text,
)


class RoutineScreen:
    def routine_moves(self):
        return game.WARMUP if self.routine and self.routine["kind"] == "warmup" else self.engine.cooldown_moves()

    def start_routine(self, kind):
        moves = game.WARMUP if kind == "warmup" else self.engine.cooldown_moves()
        self.rest_end = None
        self.routine = {"kind": kind, "index": 0, "end": time.monotonic() + moves[0].seconds, "paused": None, "skipped": 0}
        self.render(animate=True)

    def toggle_pause(self):
        r = self.routine
        if not r:
            return
        if r["end"]:
            r["paused"], r["end"] = seconds_left(r["end"]), None
        else:
            r["end"], r["paused"] = time.monotonic() + (r["paused"] or 1), None
        self.render()

    def routine_next(self, skipped=False):
        r = self.routine
        if not r:
            return
        r["skipped"] += int(skipped)
        moves = self.routine_moves()
        if r["index"] + 1 >= len(moves):
            self.finish_routine(completed=r["skipped"] == 0)
            return
        r["index"] += 1
        r["end"], r["paused"] = time.monotonic() + moves[r["index"]].seconds, None
        if not self.update_routine_view():
            self.render()

    def abort_routine(self):
        self.routine = None
        self.render(animate=True)

    def finish_routine(self, completed=True):
        kind = self.routine["kind"] if self.routine else None
        self.routine = None
        events = []
        if kind == "warmup":
            self.engine.finish_warmup()
            events.append(Event("warmup", {}))
        elif kind == "cooldown":
            events = self.engine.finish_cooldown(completed)
        self.render(animate=True)
        self.push(events)

    def skip_cooldown(self):
        self.routine = None
        self.engine.finish_cooldown(False)
        self.render(animate=True)

    def move_view(self, move, left, paused):
        """Карточка одного упражнения: «дышащее» кольцо таймера, название и подсказка."""
        kinds = {
            "mobility": ("Подвижность", ft.Icons.SYNC, GOLD),
            "stretch": ("Растяжка", ft.Icons.ACCESSIBILITY, ACCENT_2),
            "core": ("Кор", ft.Icons.BOLT, SUCCESS),
        }
        label, glyph, color = kinds[move.kind]
        timer = text(fmt_seconds(left), TEXT, 30, ft.FontWeight.W_900, mono=True)
        timer_ring, progress = ring(left / move.seconds, 150, color, ft.Column([
            icon(ft.Icons.PAUSE_ROUNDED if paused else glyph, color, 22),
            timer,
        ], spacing=2, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER), stroke=10)
        self.live.update(routine_text=timer, routine_ring=progress)
        glow = ft.Container(
            content=timer_ring,
            border_radius=75,
            shadow=ft.BoxShadow(blur_radius=50, spread_radius=-14, color=alpha(color, 0.7)),
        )
        ring_box = ft.Container(content=glow, animate_scale=ft.Animation(700, ft.AnimationCurve.EASE_IN_OUT))
        pulses = [p for p in self.live.get("pulses", []) if p[0] is not self.live.get("routine_pulse")]
        if not paused:
            pulses.append((ring_box, 1.04))
        self.live["pulses"] = pulses
        self.live["routine_pulse"] = ring_box
        return ft.Container(
            key=f"{self.routine['kind']}-{self.routine['index']}",
            content=ft.Column([
                ft.Row([ring_box], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([pill(label, color, glyph)], alignment=ft.MainAxisAlignment.CENTER),
                text(move.name, TEXT, 22, ft.FontWeight.W_800, align=ft.TextAlign.CENTER),
                text(move.tip, MUTED, 13, align=ft.TextAlign.CENTER),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def routine_panel(self):
        r = self.routine
        moves = self.routine_moves()
        warm = r["kind"] == "warmup"
        color = GOLD if warm else ACCENT_2
        move = moves[r["index"]]
        paused = r["end"] is None
        left = r["paused"] if paused else seconds_left(r["end"])

        title = kicker(f"[ {'Разминка' if warm else 'Заминка'} · {r['index'] + 1}/{len(moves)} ]", color)
        bars = segments(r["index"] + 1, len(moves), color)
        switcher = ft.AnimatedSwitcher(
            content=self.move_view(move, left, paused),
            transition=ft.AnimatedSwitcherTransition.SCALE,
            duration=500,
            reverse_duration=250,
            switch_in_curve=ft.AnimationCurve.EASE_OUT_BACK,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
        )
        upcoming = text(self.upcoming_text(moves, r["index"]), FAINT, 12, align=ft.TextAlign.CENTER)
        self.live["routine_view"] = (title, bars, switcher, upcoming, color)

        pause = ghost_button("Продолжить" if paused else "Пауза", lambda _: self.toggle_pause(), color,
                             ft.Icons.PLAY_ARROW_ROUNDED if paused else ft.Icons.PAUSE_ROUNDED)
        if warm:
            buttons = ft.Row([
                ghost_button("Прервать", lambda _: self.abort_routine(), DANGER, ft.Icons.STOP_ROUNDED),
                pause,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            note = text("Разминку нельзя пропустить — без неё квест не принять.", FAINT, 11, align=ft.TextAlign.CENTER)
        else:
            buttons = ft.Row([
                ghost_button("Пропустить заминку", lambda _: self.skip_cooldown(), MUTED),
                pause,
                ghost_button("Дальше", lambda _: self.routine_next(skipped=True), color, ft.Icons.SKIP_NEXT_ROUNDED),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)
            note = text(f"Пройди все упражнения без пропусков — получишь +{game.COOLDOWN_BONUS} XP.", FAINT, 11,
                        align=ft.TextAlign.CENTER)

        return card([
            ft.Row([title, text(f"~{round(sum(m.seconds for m in moves) / 60)} мин", MUTED, 12, mono=True)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bars,
            switcher,
            upcoming,
            ft.Divider(color=LINE, height=1),
            buttons,
            note,
        ], color, glow=0.22, spacing=14)

    @staticmethod
    def upcoming_text(moves, index):
        return f"Далее: {moves[index + 1].name}" if index + 1 < len(moves) else "Последнее упражнение"

    def update_routine_view(self) -> bool:
        """Смена упражнения без перерисовки экрана — так AnimatedSwitcher проигрывает переход."""
        view = self.live.get("routine_view")
        if not view:
            return False
        title, bars, switcher, upcoming, color = view
        r = self.routine
        moves = self.routine_moves()
        title.value = f"[ {'Разминка' if r['kind'] == 'warmup' else 'Заминка'} · {r['index'] + 1}/{len(moves)} ]"
        for i, segment in enumerate(bars.controls):
            segment.bgcolor = color if i <= r["index"] else LINE
        switcher.content = self.move_view(moves[r["index"]], moves[r["index"]].seconds, False)
        upcoming.value = self.upcoming_text(moves, r["index"])
        self.page.update()
        return True
