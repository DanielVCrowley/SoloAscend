"""Главный класс приложения."""
import asyncio

import flet as ft

import game
from common import TABS, fmt_seconds, seconds_left
from engine import Engine, Event
from ui import ACCENT, ACCENT_2, BG, BG_SOFT, MUTED, RANK_COLORS, TEXT, alpha, pill, text
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
        self.form = {"name": "", "weight": "", "height": "", "experienced": None, "equipment": set(), "sex": None, "goals": set()}
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
        self.pending_players: list = []  # встроенные плееры, ждущие загрузки
        self.counters: list = []         # числа и полосы, которые «досчитываются» после отрисовки
        self.shell = None                # постоянная оболочка: список экрана + нижняя панель
        self.screen_key = None
        self.body_list = None
        self.nav_selected = None
        self.focus_branch = None         # упражнение квеста, развёрнутое вручную
        self.focus_drill = None          # упражнение программы, развёрнутое вручную
        self.focus_flash = None          # только что развёрнутая карточка — для анимации
        self.show_weight_log = False
        self.program_filter = None       # фильтр каталога навыков по типу
        self.filter_flash = False

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
        if self.engine.profile and not self.engine.goals_known() \
                and not any(ev.kind == "ask_goals" for ev in self.events):
            self.events.append(Event("ask_goals", {}))
        if self.engine.profile and not self.engine.sex_known() \
                and not any(ev.kind == "ask_sex" for ev in self.events):
            self.events.append(Event("ask_sex", {}))
        if self.engine.weight_due() and not self.weigh_open \
                and not any(ev.kind == "weigh_in" for ev in self.events):
            self.events.append(Event("weigh_in", {}))
        # нераспределённые очки и невыбранное направление — напомнить (например, если закрыли приложение)
        if self.engine.unspent_points() > 0 and not any(ev.kind in ("level", "stat_points") for ev in self.events):
            self.events.append(Event("stat_points", {}))
        if self.engine.focus_pending() and not any(ev.kind == "focus" for ev in self.events):
            self.events.append(Event("focus", {}))
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

    def set_tab(self, e):  # совместимость со старым обработчиком
        self.select_tab(e.control.selected_index)

    def select_tab(self, index):
        if index == self.tab and self.screen_key == ("tab", index):
            return
        self.tab = index
        self.render(animate=True)

    # ---------- оболочка и нижняя панель ----------

    def build_shell(self):
        """Оболочка создаётся один раз: смена вкладок идёт через AnimatedSwitcher (плавное
        перетекание), а внутри вкладки обновляется тот же список — прокрутка не сбрасывается."""
        self.switcher = ft.AnimatedSwitcher(
            content=ft.Container(),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=340,
            reverse_duration=180,
            switch_in_curve=ft.AnimationCurve.EASE_OUT_CUBIC,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )
        self.nav_holder = self.build_nav()
        self.page.navigation_bar = None
        self.page.controls.clear()
        self.page.controls.append(ft.Container(
            expand=True,
            gradient=ft.RadialGradient(
                center=ft.Alignment(0.8, -1.1),
                radius=1.4,
                colors=[alpha(ACCENT_2, 0.16), alpha(ACCENT, 0.04), BG],
                stops=[0.0, 0.45, 1.0],
            ),
            content=ft.SafeArea(expand=True, content=ft.Column([
                ft.Container(content=self.switcher, expand=True),
                self.nav_holder,
            ], spacing=0, expand=True)),
        ))
        self.shell = True

    def build_nav(self):
        """Плавающая нижняя панель: поднята над краем экрана, выделение «переезжает» с пружинкой."""
        self.nav_parts = []
        items = []
        for i, (name, outline, filled) in enumerate(TABS):
            glyph = ft.Icon(outline, color=MUTED, size=24)
            box = ft.Container(content=glyph, animate_scale=ft.Animation(550, ft.AnimationCurve.ELASTIC_OUT))
            label = ft.Text(name, size=10, color=MUTED, weight=ft.FontWeight.W_500, no_wrap=True)
            items.append(ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                on_click=lambda _, i=i: self.select_tab(i),
                content=ft.Column([box, label], spacing=4, tight=True,
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ))
            self.nav_parts.append((glyph, box, label, outline, filled))
        self.nav_indicator = ft.Container(
            expand=1,
            offset=ft.Offset(self.tab, 0),
            animate_offset=ft.Animation(520, ft.AnimationCurve.EASE_OUT_BACK),
            alignment=ft.Alignment.CENTER,
            content=ft.Container(
                width=64, height=56,
                border_radius=ft.BorderRadius.all(20),
                bgcolor=alpha(ACCENT, 0.13),
                border=ft.Border.all(1, alpha(ACCENT, 0.35)),
                shadow=ft.BoxShadow(blur_radius=18, spread_radius=-4, color=alpha(ACCENT, 0.35)),
            ),
        )
        bar = ft.Container(
            height=76,
            margin=ft.Margin.only(left=14, right=14, top=6, bottom=16),
            border_radius=ft.BorderRadius.all(28),
            bgcolor=alpha(BG_SOFT, 0.97),
            border=ft.Border.all(1, alpha(ACCENT, 0.18)),
            shadow=ft.BoxShadow(blur_radius=32, spread_radius=-8, color=alpha(ACCENT, 0.3), offset=ft.Offset(0, 8)),
            content=ft.Stack([
                ft.Row([self.nav_indicator, ft.Container(expand=len(TABS) - 1)], spacing=0),
                ft.Row(items, spacing=0),
            ], expand=True),
        )
        return ft.Container(
            content=bar,
            visible=False,
            offset=ft.Offset(0, 1.4),
            opacity=0,
            animate_offset=ft.Animation(650, ft.AnimationCurve.EASE_OUT_BACK),
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        )

    def update_nav(self, visible: bool):
        holder = self.nav_holder
        if not visible:
            holder.visible = False
            holder.offset, holder.opacity = ft.Offset(0, 1.4), 0
            self.nav_selected = None
            return
        # анимации панели не привязаны к номеру отрисовки: быстрая перерисовка не должна
        # оставить панель спрятанной или значок увеличенным
        if not holder.visible:  # первое появление — панель «выезжает» снизу
            holder.visible = True
            self.page.run_task(self.play_anims, [(0.15, holder, {"offset": ft.Offset(0, 0), "opacity": 1})])
        sel = self.tab
        self.nav_indicator.offset = ft.Offset(sel, 0)
        for i, (glyph, box, label, outline, filled) in enumerate(self.nav_parts):
            on = i == sel
            glyph.icon = filled if on else outline
            glyph.color = ACCENT if on else MUTED
            label.color = TEXT if on else MUTED
            label.weight = ft.FontWeight.W_700 if on else ft.FontWeight.W_500
            box.scale = 1
        if self.nav_selected is not None and self.nav_selected != sel:
            box = self.nav_parts[sel][1]
            box.scale = 1.32
            self.page.run_task(self.play_anims, [(0.1, box, {"scale": 1})])
        self.nav_selected = sel

    def render(self, animate=False):
        self.generation += 1
        self.live = {}
        self.pending = []
        self.anims = []
        self.pending_players = []
        self.counters = []
        if self.shell is None:
            self.build_shell()
        if not self.engine.profile:
            key = ("onboarding", self.step)
            body = self.onboarding(animate)
        else:
            key = ("tab", self.tab)
            body = [self.status, self.quest, self.programs, self.skills, self.history][self.tab](animate)
        self.update_nav(bool(self.engine.profile))
        if key != self.screen_key or self.body_list is None:
            # новый экран — новый список: AnimatedSwitcher плавно сменит его, прокрутка с начала
            self.body_list = ft.ListView(
                controls=body, spacing=16, expand=True,
                padding=ft.Padding.only(left=18, right=18, top=12, bottom=12),
            )
            self.switcher.content = self.body_list
            self.screen_key = key
        else:
            # тот же экран — меняем только содержимое: прокрутка остаётся на месте
            self.body_list.controls = body
        self.page.update()
        if self.pending:
            self.page.run_task(self.play_reveal, list(self.pending), self.generation)
        if self.anims:
            self.page.run_task(self.play_anims, list(self.anims), self.generation)
        if self.counters:
            self.page.run_task(self.play_counters, list(self.counters), self.generation)
        if self.pending_players:
            self.page.run_task(self.flush_players, list(self.pending_players), self.generation)
        if "ring_tween" in self.live:
            self.page.run_task(self.tween_ring, *self.live["ring_tween"], self.generation)
        self.pflash = None
        self.flash = None
        self.prev_fraction = None
        self.focus_flash = None
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
