"""Главный класс приложения."""
import asyncio

import flet as ft

import game
from common import TABS, fmt_seconds, seconds_left
from engine import Engine, Event
from ui import ACCENT, ACCENT_2, BG, BG_SOFT, MUTED, RANK_COLORS, alpha, pill, text
from anim import AnimMixin
from dialogs import DialogsMixin
from screens.onboarding import OnboardingScreen
from screens.status import StatusScreen
from screens.quest import QuestScreen
from screens.routine import RoutineScreen
from screens.programs import ProgramsScreen
from screens.skills import SkillsScreen
from screens.history import HistoryScreen


class AscendApp(
    AnimMixin,
    DialogsMixin,
    OnboardingScreen,
    StatusScreen,
    QuestScreen,
    RoutineScreen,
    ProgramsScreen,
    SkillsScreen,
    HistoryScreen,
):
    """Каркас приложения: состояние, рендер вкладок, тикер таймеров, очередь событий.

    Экраны, диалоги и анимации подмешиваются из отдельных модулей.
    """

    def __init__(self, page: ft.Page, engine: Engine):
        self.page = page
        self.engine = engine
        self.tab = 1
        self.events: list = []
        self.dialog_open = False
        self.form = {"name": "", "weight": "", "height": "", "experienced": None, "equipment": set()}
        self.step = 0
        self.error = ""
        self.intro_done = False
        self.values: dict = {}
        self.rest_end = None
        self.hold = None
        self.live: dict = {}
        self.pending: list = []
        self.generation = 0
        self.haptics = None
        self.anims: list = []
        self.flash = None
        self.prev_fraction = None
        self.routine = None
        self.pulse_on = False
        self.pulse_clock = 0.0
        self.rest_total = game.REST_SECONDS
        self.ptimer = None  # таймер удержания в тренировке программы: (упражнение, секунды, конец)
        self.pflash = None  # только что отмеченный подход программы: (упражнение, номер подхода)
        self.weigh_open = False

    def start(self):
        try:
            self.haptics = ft.HapticFeedback()
        except Exception:
            self.haptics = None
        self.refresh_day(animate=True)
        self.page.run_task(self.ticker)

    def refresh_day(self, animate=False):
        self.events += self.engine.apply_penalty()
        self.engine.ensure_daily_quest()
        if self.engine.weight_due() and not self.weigh_open \
                and not any(ev.kind == "weigh_in" for ev in self.events):
            self.events.append(Event("weigh_in", {}))
        self.render(animate)
        self.show_next_event()

    def on_lifecycle(self, e):
        if e.state == ft.AppLifecycleState.RESUME:
            self.refresh_day()

    async def ticker(self):
        while True:
            await asyncio.sleep(0.25)
            dirty = self.tick_pulses()
            if self.routine and self.routine["end"]:
                left = seconds_left(self.routine["end"])
                if left <= 0:
                    await self.vibrate(1)
                    self.routine_next()
                    continue
                if "routine_text" in self.live:
                    move = self.routine_moves()[self.routine["index"]]
                    self.live["routine_text"].value = fmt_seconds(left)
                    self.live["routine_ring"].value = left / move.seconds
                    dirty = True
            if self.ptimer:
                index, seconds, end = self.ptimer
                left = seconds_left(end)
                if left <= 0:
                    self.ptimer = None
                    await self.vibrate()
                    self.program_mark(index)
                    continue
                if "ptimer_text" in self.live:
                    self.live["ptimer_text"].value = fmt_seconds(left)
                    self.live["ptimer_ring"].value = left / seconds
                    dirty = True
            if self.hold:
                branch, seconds, end = self.hold
                left = seconds_left(end)
                if left <= 0:
                    self.hold = None
                    await self.vibrate()
                    self.log_set(branch, seconds)
                elif "hold_text" in self.live:
                    self.live["hold_text"].value = fmt_seconds(left)
                    self.live["hold_ring"].value = left / seconds
                    self.page.update()
            elif self.rest_end:
                left = seconds_left(self.rest_end)
                if left <= 0:
                    self.rest_end = None
                    self.render()
                    await self.vibrate()
                elif "rest_text" in self.live:
                    self.live["rest_text"].value = fmt_seconds(left)
                    self.live["rest_ring"].value = left / self.rest_total
                    self.page.update()
                    dirty = False
            if dirty:
                self.page.update()

    def push(self, events: list):
        self.events += events
        self.show_next_event()

    def set_tab(self, e):
        self.tab = e.control.selected_index
        self.render(animate=True)

    def render(self, animate=False):
        self.generation += 1
        self.live = {}
        self.pending = []
        self.anims = []
        if not self.engine.profile:
            self.page.navigation_bar = None
            body = self.onboarding(animate)
        else:
            self.page.navigation_bar = ft.NavigationBar(
                selected_index=self.tab,
                bgcolor=BG_SOFT,
                indicator_color=alpha(ACCENT, 0.16),
                height=70,
                on_change=self.set_tab,
                destinations=[
                    ft.NavigationBarDestination(icon=outline, selected_icon=filled, label=name)
                    for name, outline, filled in TABS
                ],
            )
            body = [self.status, self.quest, self.programs, self.skills, self.history][self.tab](animate)
        self.page.controls.clear()
        self.page.controls.append(ft.Container(
            expand=True,
            gradient=ft.RadialGradient(
                center=ft.Alignment(0.8, -1.1),
                radius=1.4,
                colors=[alpha(ACCENT_2, 0.16), alpha(ACCENT, 0.04), BG],
                stops=[0.0, 0.45, 1.0],
            ),
            content=ft.SafeArea(
                content=ft.ListView(controls=body, spacing=16, padding=ft.Padding.only(left=18, right=18, top=12, bottom=24), expand=True),
                expand=True,
            ),
        ))
        self.page.update()
        if self.pending:
            self.page.run_task(self.play_reveal, list(self.pending), self.generation)
        if self.anims:
            self.page.run_task(self.play_anims, list(self.anims), self.generation)
        if "ring_tween" in self.live:
            self.page.run_task(self.tween_ring, *self.live["ring_tween"], self.generation)
        self.pflash = None
        self.flash = None
        self.prev_fraction = None
        if "intro" in self.live and not self.intro_done:
            self.page.run_task(self.type_intro, self.generation)

    def level_pill(self):
        lvl = self.engine.level()
        rank = self.engine.rank()
        return pill(f"LV {lvl.level} · {rank.value}", RANK_COLORS[rank])

    @staticmethod
    def metric(value, caption, color):
        return ft.Column([
            text(value, color, 28, ft.FontWeight.W_800, mono=True),
            text(caption, MUTED, 12),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
