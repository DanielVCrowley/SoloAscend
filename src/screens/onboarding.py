"""Вступление Системы и анкета нового игрока."""
import asyncio

import flet as ft

from common import EQUIPMENT_ICONS, INTRO, ONBOARDING_STEPS
import game
from game import Equipment, Sex
from ui import (
    ACCENT, ACCENT_2, CARD, DANGER, FAINT, GOLD, LINE, MUTED, SUCCESS, TEXT, alpha, field, icon, icon_badge,
    kicker, primary_button, segments, select_tile, text,
)

GOAL_ICONS = {
    game.Goal.LOSE: ft.Icons.LOCAL_FIRE_DEPARTMENT,
    game.Goal.MASS: ft.Icons.FITNESS_CENTER,
    game.Goal.DEFINE: ft.Icons.FLARE,
    game.Goal.ENDURANCE: ft.Icons.DIRECTIONS_RUN,
    game.Goal.FLEX: ft.Icons.SELF_IMPROVEMENT,
}
GOAL_COLORS = {
    game.Goal.LOSE: DANGER,
    game.Goal.MASS: ACCENT_2,
    game.Goal.DEFINE: GOLD,
    game.Goal.ENDURANCE: SUCCESS,
    game.Goal.FLEX: ACCENT,
}


class OnboardingScreen:
    def go(self, step):
        self.step = step
        self.error = ""
        self.render(animate=True)

    def onboarding(self, animate):
        if self.step == 0:
            return self.onboarding_intro(animate)
        f = self.form
        r = lambda c: self.reveal(c, animate)

        def set_field(key):
            def handler(e):
                f[key] = e.control.value
            return handler

        def next_step(_=None):
            self.error = self.validate(self.step)
            if self.error:
                self.render()
                return
            if self.step < ONBOARDING_STEPS:
                self.go(self.step + 1)
            else:
                self.finish_onboarding()

        top = ft.Row([
            ft.Container(
                content=icon(ft.Icons.ARROW_BACK, MUTED, 20),
                width=40, height=40, alignment=ft.Alignment.CENTER,
                border_radius=ft.BorderRadius.all(20), ink=True,
                on_click=lambda _: self.go(self.step - 1),
            ),
            ft.Container(content=segments(self.step, ONBOARDING_STEPS), expand=True),
            text(f"{self.step}/{ONBOARDING_STEPS}", MUTED, 12, mono=True),
        ], spacing=12)

        controls = [top]
        if self.step == 1:
            controls += [
                r(ft.Column([kicker("Шаг 1 · Идентификация"), text("Как тебя зовут?", TEXT, 30, ft.FontWeight.W_800),
                             text("Так Система будет обращаться к тебе.", MUTED)], spacing=6)),
                r(field(f["name"], "Имя игрока", set_field("name"), leading=ft.Icons.PERSON_OUTLINE, autofocus=True, on_submit=next_step)),
            ]
        elif self.step == 2:
            def pick(value):
                def handler(_):
                    f["sex"] = value
                    self.error = ""
                    self.render()
                return handler

            controls += [
                r(ft.Column([kicker("Шаг 2 · Пол"), text("Кто ты?", TEXT, 30, ft.FontWeight.W_800),
                             text("Система подстроит нормы: для девушек упражнения немного легче, "
                                  "особенно на верх тела.", MUTED)], spacing=6)),
                r(select_tile("Мужской", "Стандартные нормы", ft.Icons.MALE,
                              f["sex"] is Sex.MALE, pick(Sex.MALE))),
                r(select_tile("Женский", "Облегчённые нормы: отжимания и подтягивания ~на треть легче",
                              ft.Icons.FEMALE, f["sex"] is Sex.FEMALE, pick(Sex.FEMALE), ACCENT_2)),
            ]
        elif self.step == 3:
            controls += [
                r(ft.Column([kicker("Шаг 3 · Параметры"), text("Твоё тело", TEXT, 30, ft.FontWeight.W_800),
                             text("По ИМТ Система подберёт нагрузку: при лишнем весе нормы будут легче, чтобы беречь суставы.", MUTED)], spacing=6)),
                r(field(f["weight"], "Вес", set_field("weight"), ft.KeyboardType.NUMBER, ft.Icons.MONITOR_WEIGHT, autofocus=True, suffix="кг")),
                r(field(f["height"], "Рост", set_field("height"), ft.KeyboardType.NUMBER, ft.Icons.HEIGHT, on_submit=next_step, suffix="см")),
            ]
        elif self.step == 4:
            def toggle_goal(goal):
                def handler(_):
                    f["goals"] ^= {goal}
                    self.error = ""
                    self.render()
                return handler

            plan = game.goal_plan(f["goals"])
            controls += [
                r(ft.Column([kicker("Шаг 4 · Цель"), text("Чего хочешь добиться?", TEXT, 30, ft.FontWeight.W_800),
                             text("Можно выбрать несколько — Система подстроит квесты.", MUTED)], spacing=6)),
                *[r(self.goal_tile(g, g in f["goals"], toggle_goal(g))) for g in game.Goal],
            ]
            if f["goals"]:
                controls.append(self.plan_summary(plan))
        elif self.step == 5:
            def choose(value):
                def handler(_):
                    f["experienced"] = value
                    self.error = ""
                    self.render()
                return handler

            controls += [
                r(ft.Column([kicker("Шаг 5 · Опыт"), text("Тренировался раньше?", TEXT, 30, ft.FontWeight.W_800),
                             text("Речь о тренировках со своим весом.", MUTED)], spacing=6)),
                r(select_tile("Я новичок", "Начну с самых лёгких ступеней", ft.Icons.SPA, f["experienced"] is False, choose(False))),
                r(select_tile("Есть опыт", "Пропущу лёгкие ступени", ft.Icons.BOLT, f["experienced"] is True, choose(True), ACCENT_2)),
            ]
        elif self.step == 6:
            def toggle(item):
                def handler(_):
                    f["equipment"] ^= {item}
                    self.render()
                return handler

            tiles = [
                ft.Container(
                    col=6,
                    content=self.equipment_tile(item, item in f["equipment"], toggle(item)),
                )
                for item in Equipment
            ]
            controls += [
                r(ft.Column([kicker("Шаг 6 · Инвентарь"), text("Что есть дома?", TEXT, 30, ft.FontWeight.W_800),
                             text("Можно ничего не выбирать — упражнения подберутся без инвентаря.", MUTED)], spacing=6)),
                r(ft.ResponsiveRow(tiles, spacing=10, run_spacing=10)),
            ]

        if self.error:
            controls.append(ft.Row([icon(ft.Icons.WARNING_AMBER, DANGER, 18), text(self.error, DANGER)], spacing=8))
        controls.append(r(ft.Container(
            padding=ft.Padding.only(top=8),
            content=primary_button(
                "ЗАВЕРШИТЬ" if self.step == ONBOARDING_STEPS else "ДАЛЕЕ",
                next_step,
                ft.Icons.CHECK if self.step == ONBOARDING_STEPS else ft.Icons.ARROW_FORWARD,
            ),
        )))
        return controls

    def onboarding_intro(self, animate):
        label = text(INTRO if self.intro_done else "", TEXT, 22, ft.FontWeight.W_600, align=ft.TextAlign.CENTER)
        self.live["intro"] = label
        actions = ft.Container(
            opacity=1 if self.intro_done else 0,
            offset=ft.Offset(0, 0) if self.intro_done else ft.Offset(0, 0.3),
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(500, ft.AnimationCurve.EASE_OUT_CUBIC),
            content=primary_button("ПРИНЯТЬ", lambda _: self.go(1), ft.Icons.AUTO_AWESOME),
        )
        self.live["intro_actions"] = actions
        orb = ft.Container(
            content=icon(ft.Icons.AUTO_AWESOME, ACCENT, 44),
            width=110,
            height=110,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(55),
            gradient=ft.RadialGradient(colors=[alpha(ACCENT, 0.35), alpha(ACCENT_2, 0.08)]),
            border=ft.Border.all(1, alpha(ACCENT, 0.6)),
            shadow=ft.BoxShadow(blur_radius=60, spread_radius=4, color=alpha(ACCENT, 0.35)),
        )
        panel = ft.Container(
            padding=26,
            border_radius=ft.BorderRadius.all(24),
            bgcolor=alpha(CARD, 0.85),
            border=ft.Border.all(1, alpha(ACCENT, 0.4)),
            shadow=ft.BoxShadow(blur_radius=40, spread_radius=-10, color=alpha(ACCENT, 0.3)),
            content=ft.Column([
                kicker("[ Уведомление ]"),
                ft.Container(content=label, height=150, alignment=ft.Alignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14),
        )
        return [
            ft.Container(height=40),
            self.reveal(ft.Row([orb], alignment=ft.MainAxisAlignment.CENTER), animate),
            ft.Container(height=10),
            self.reveal(panel, animate),
            ft.Container(height=6),
            actions,
        ]

    async def type_intro(self, generation):
        label = self.live.get("intro")
        if not label:
            return
        await asyncio.sleep(0.5)
        for i in range(1, len(INTRO) + 1):
            if generation != self.generation:
                return
            label.value = INTRO[:i]
            self.page.update()
            await asyncio.sleep(0.012 if INTRO[i - 1] == " " else 0.03)
        self.intro_done = True
        actions = self.live.get("intro_actions")
        if actions and generation == self.generation:
            actions.opacity = 1
            actions.offset = ft.Offset(0, 0)
            self.page.update()

    @staticmethod
    def goal_tile(goal, selected, on_click):
        """Плитка цели с галочкой — для анкеты и окна смены целей."""
        color = GOAL_COLORS[goal]
        return ft.Container(
            padding=14,
            border_radius=ft.BorderRadius.all(16),
            bgcolor=alpha(color, 0.12) if selected else alpha(CARD, 0.8),
            border=ft.Border.all(1.5 if selected else 1, color if selected else LINE),
            animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            ink=True,
            on_click=on_click,
            content=ft.Row([
                icon_badge(GOAL_ICONS[goal], color if selected else MUTED, 40),
                ft.Column([
                    text(goal.title, TEXT, 16, ft.FontWeight.W_700),
                    text(goal.hint, MUTED, 12),
                ], spacing=2, expand=True),
                icon(ft.Icons.CHECK_BOX if selected else ft.Icons.CHECK_BOX_OUTLINE_BLANK, color if selected else FAINT, 22),
            ], spacing=12),
        )

    @staticmethod
    def plan_summary(plan):
        """Что изменится в тренировке при выбранных целях."""
        return ft.Container(
            padding=12,
            border_radius=ft.BorderRadius.all(14),
            bgcolor=alpha(ACCENT, 0.06),
            border=ft.Border.all(1, alpha(ACCENT, 0.25)),
            content=ft.Column([
                kicker("Что изменится", ACCENT),
                *[ft.Row([icon(ft.Icons.CHECK_ROUNDED, ACCENT, 16), ft.Container(content=text(line, TEXT, 12), expand=True)],
                         spacing=8) for line in plan.summary],
            ], spacing=6),
        )

    @staticmethod
    def equipment_tile(item, selected, on_click):
        color = ACCENT if selected else MUTED
        return ft.Container(
            height=104,
            padding=14,
            border_radius=ft.BorderRadius.all(16),
            bgcolor=alpha(ACCENT, 0.1) if selected else alpha(CARD, 0.8),
            border=ft.Border.all(1.5 if selected else 1, ACCENT if selected else LINE),
            animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            ink=True,
            on_click=on_click,
            content=ft.Column([
                ft.Row([
                    icon(EQUIPMENT_ICONS[item], color, 26),
                    icon(ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED, ACCENT if selected else FAINT, 20),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                text(item.value, TEXT if selected else MUTED, 14, ft.FontWeight.W_600),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        )

    def validate(self, step) -> str:
        f = self.form
        if step == 1 and not f["name"].strip():
            return "Введи имя."
        if step == 2 and f["sex"] is None:
            return "Выбери один из вариантов."
        if step == 3:
            try:
                weight = float(f["weight"].replace(",", "."))
                height = int(f["height"])
            except ValueError:
                return "Укажи вес и рост числами."
            if not 30 <= weight <= 250:
                return "Вес должен быть от 30 до 250 кг."
            if not 120 <= height <= 230:
                return "Рост должен быть от 120 до 230 см."
        if step == 4 and not f["goals"]:
            return "Выбери хотя бы одну цель."
        if step == 5 and f["experienced"] is None:
            return "Выбери один из вариантов."
        return ""

    def finish_onboarding(self):
        f = self.form
        events = self.engine.create_profile(
            f["name"].strip(),
            float(f["weight"].replace(",", ".")),
            int(f["height"]),
            f["experienced"],
            set(f["equipment"]),
            f["sex"] or Sex.MALE,
            sorted(f["goals"], key=list(game.Goal).index),
        )
        self.engine.ensure_daily_quest()
        self.tab = 1
        self.render(animate=True)
        self.push(events)
