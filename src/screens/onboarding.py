"""Вступление Системы и анкета нового игрока."""
import asyncio

import flet as ft

from common import EQUIPMENT_ICONS, INTRO, ONBOARDING_STEPS
from game import Equipment
from ui import (
    ACCENT, ACCENT_2, CARD, DANGER, FAINT, LINE, MUTED, TEXT, alpha, field, icon, kicker,
    primary_button, segments, select_tile, text,
)


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
            controls += [
                r(ft.Column([kicker("Шаг 2 · Параметры"), text("Твоё тело", TEXT, 30, ft.FontWeight.W_800),
                             text("Нужно для расчёта ИМТ и примерных калорий.", MUTED)], spacing=6)),
                r(field(f["weight"], "Вес", set_field("weight"), ft.KeyboardType.NUMBER, ft.Icons.MONITOR_WEIGHT, autofocus=True, suffix="кг")),
                r(field(f["height"], "Рост", set_field("height"), ft.KeyboardType.NUMBER, ft.Icons.HEIGHT, on_submit=next_step, suffix="см")),
            ]
        elif self.step == 3:
            def choose(value):
                def handler(_):
                    f["experienced"] = value
                    self.error = ""
                    self.render()
                return handler

            controls += [
                r(ft.Column([kicker("Шаг 3 · Опыт"), text("Тренировался раньше?", TEXT, 30, ft.FontWeight.W_800),
                             text("Речь о тренировках со своим весом.", MUTED)], spacing=6)),
                r(select_tile("Я новичок", "Начну с самых лёгких ступеней", ft.Icons.SPA, f["experienced"] is False, choose(False))),
                r(select_tile("Есть опыт", "Пропущу лёгкие ступени", ft.Icons.BOLT, f["experienced"] is True, choose(True), ACCENT_2)),
            ]
        elif self.step == 4:
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
                r(ft.Column([kicker("Шаг 4 · Инвентарь"), text("Что есть дома?", TEXT, 30, ft.FontWeight.W_800),
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
        if step == 2:
            try:
                weight = float(f["weight"].replace(",", "."))
                height = int(f["height"])
            except ValueError:
                return "Укажи вес и рост числами."
            if not 30 <= weight <= 250:
                return "Вес должен быть от 30 до 250 кг."
            if not 120 <= height <= 230:
                return "Рост должен быть от 120 до 230 см."
        if step == 3 and f["experienced"] is None:
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
        )
        self.engine.ensure_daily_quest()
        self.tab = 1
        self.render(animate=True)
        self.push(events)
