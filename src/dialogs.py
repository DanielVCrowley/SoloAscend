"""Диалоги: события Системы и окно «Как выполнять»."""
import flet as ft

import game
import programs
from common import plural
from engine import Event
from guides import GUIDES
from ui import (
    ACCENT, ACCENT_2, BG, BG_SOFT, BRANCH_ICONS, DANGER, FAINT, GOLD, MUTED, RANK_COLORS, STAT_COLORS,
    SUCCESS, TEXT, alpha, ghost_button, icon, icon_badge, kicker, pill, primary_button, text,
)


class DialogsMixin:
    def show_next_event(self):
        if self.dialog_open or not self.events:
            return
        event = self.events[0]
        if event.kind == "weigh_in":
            self.events.pop(0)
            self.show_weigh_in(daily=True)
            return
        if event.kind == "ask_goals":
            self.events.pop(0)
            if self.engine.goals_known():
                self.show_next_event()
            else:
                self.show_goals_dialog(first_time=True)
            return
        if event.kind == "ask_sex":
            self.events.pop(0)
            if self.engine.sex_known():
                self.show_next_event()
            else:
                self.show_sex_dialog(first_time=True)
            return
        self.dialog_open = True
        heading, headline, body, color, glyph = self.describe(event)

        def accept(_):
            self.page.pop_dialog()
            self.dialog_open = False
            self.events.pop(0)
            self.show_next_event()

        badge = ft.Container(
            content=icon(glyph, color, 34),
            width=72,
            height=72,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(36),
            bgcolor=alpha(color, 0.14),
            border=ft.Border.all(1, alpha(color, 0.45)),
            shadow=ft.BoxShadow(blur_radius=30, spread_radius=0, color=alpha(color, 0.45)),
            scale=0.2,
            rotate=ft.Rotate(-0.6),
            opacity=0,
            animate_scale=ft.Animation(900, ft.AnimationCurve.ELASTIC_OUT),
            animate_rotation=ft.Animation(700, ft.AnimationCurve.EASE_OUT_BACK),
            animate_opacity=ft.Animation(200),
        )

        def rise(control):
            return ft.Container(
                content=control,
                opacity=0,
                offset=ft.Offset(0, 0.4),
                animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(500, ft.AnimationCurve.EASE_OUT_CUBIC),
            )

        lines = [
            rise(kicker(f"[ {heading} ]", color)),
            rise(text(headline, TEXT, 22, ft.FontWeight.W_800, align=ft.TextAlign.CENTER)),
            rise(text(body, MUTED, 14, align=ft.TextAlign.CENTER)),
            rise(primary_button("ПРИНЯТЬ", accept, colors=[color, alpha(color, 0.7)])),
        ]
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(color, 0.5))),
            content=ft.Container(
                width=320,
                content=ft.Column(
                    [badge, *lines[:3], ft.Container(height=4), lines[3]],
                    spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        ))
        steps = [(0.12, badge, {"scale": 1, "rotate": ft.Rotate(0), "opacity": 1})]
        steps += [(0.3 + i * 0.09, line, {"opacity": 1, "offset": ft.Offset(0, 0)}) for i, line in enumerate(lines)]
        self.page.run_task(self.play_anims, steps)

    @staticmethod
    def describe(event: Event):
        d = event.data
        if event.kind == "welcome":
            return "СИСТЕМА", f"Добро пожаловать, {d['name']}", "Регистрация завершена. Ранг: E.\nЕжедневный квест уже ждёт.", ACCENT, ft.Icons.AUTO_AWESOME
        if event.kind == "level":
            if d["rank_up"]:
                body = f"Уровень {d['level']}. Ты стал сильнее."
                if d.get("unlocked"):
                    body += "\nВ квест добавлены: " + ", ".join(b.title.lower() for b in d["unlocked"]) + " — с завтрашнего дня."
                return "НОВЫЙ РАНГ", f"Ранг {d['rank'].value}", body, RANK_COLORS[d["rank"]], ft.Icons.EMOJI_EVENTS
            return "УРОВЕНЬ ПОВЫШЕН", f"Уровень {d['level']}", "Характеристики растут вместе с тобой.", GOLD, ft.Icons.TRENDING_UP
        if event.kind == "skill":
            step = d["step"]
            return "НОВЫЙ НАВЫК", step.name, f"Ветка «{step.branch.title}» усилена.", ACCENT_2, BRANCH_ICONS[step.branch]
        if event.kind == "quest":
            body = f"Серия: {d['streak']} дн. подряд."
            if d.get("new_tier"):
                body += f"\nНовый бонус серии: +{d['pct']}% к опыту!"
            elif d.get("pct"):
                body += f"\nБонус серии: +{d['pct']}% к опыту."
            else:
                nxt = game.next_streak_tier(d["streak"])
                if nxt:
                    left = nxt[0] - d["streak"]
                    body += f"\nЕщё {left} {plural(left, 'день', 'дня', 'дней')} — и бонус +{nxt[1]}% к опыту."
            body += "\nНе забудь заминку — она снимет напряжение."
            return "КВЕСТ ВЫПОЛНЕН", f"+{d['bonus']} XP", body, GOLD if d.get("new_tier") else SUCCESS, ft.Icons.DONE_ALL
        if event.kind == "load":
            if d["up"]:
                body = (f"ИМТ {d['bmi']} — теперь «{d['label']}». Отличная работа!\n"
                        "Нормы стали чуть выше: тело готово к большей нагрузке.")
                return "ВЕС СНИЖЕН", "Нагрузка повышена", body, SUCCESS, ft.Icons.TRENDING_UP
            body = (f"ИМТ {d['bmi']} — «{d['label']}». Нормы стали чуть легче, "
                    "чтобы беречь суставы. Опыт за выполненную норму не уменьшается.")
            return "НАГРУЗКА ОБНОВЛЕНА", f"−{round((1 - d['factor']) * 100)}% к нормам", body, GOLD, ft.Icons.MONITOR_WEIGHT
        if event.kind == "goals":
            lines = "\n".join("• " + line for line in d["lines"])
            when = "Сегодняшний квест уже пересобран." if d["today"] else "Изменения вступят в силу с завтрашнего квеста."
            return "ЦЕЛИ ОБНОВЛЕНЫ", d["titles"], f"{lines}\n\n{when}", ACCENT, ft.Icons.FLAG
        if event.kind == "warmup":
            return "РАЗМИНКА ЗАВЕРШЕНА", "Тело готово", "Мышцы разогреты, суставы подвижны.\nТеперь можно принять квест или начать тренировку программы.", SUCCESS, ft.Icons.SELF_IMPROVEMENT
        if event.kind == "program_session":
            left = programs.TOTAL_SESSIONS - d["number"]
            body = f"«{d['program'].name}»: тренировка {d['number']} из {programs.TOTAL_SESSIONS}.\n"
            body += "Следующая — испытание!" if left == 1 else f"Осталось тренировок: {left}. Следующая — завтра или позже."
            return "ТРЕНИРОВКА ЗАВЕРШЕНА", f"+{d['xp']} XP", body, ACCENT_2, ft.Icons.SCHOOL
        if event.kind == "program_done":
            return ("НАВЫК ОСВОЕН", d["program"].name,
                    f"Программа пройдена за {programs.WEEKS} недели. +{d['xp']} XP.\n"
                    "Навык добавлен в профиль — продолжай закреплять его.", GOLD, ft.Icons.MILITARY_TECH)
        if event.kind == "cooldown":
            return "ЗАМИНКА ЗАВЕРШЕНА", f"+{d['bonus']} XP", "Мышцы восстановятся быстрее.\nДо завтра, игрок.", ACCENT_2, ft.Icons.SPA
        return (
            "ШТРАФ",
            f"−{d['lost']} XP",
            f"Квест не выполнен (дней: {d['missed']}).\nСерия обнулена.",
            DANGER,
            ft.Icons.WARNING_AMBER,
        )

    def show_guide(self, step):
        """Окно с подробной техникой упражнения: мышцы, шаги, ошибки, как облегчить и усложнить."""
        guide = GUIDES.get(step.id)
        if not guide or self.dialog_open:
            return
        self.dialog_open = True
        color = STAT_COLORS[step.branch.stat]

        def close(_):
            self.page.pop_dialog()
            self.dialog_open = False
            self.show_next_event()

        def section(title, glyph, tint, body):
            return ft.Column([
                ft.Row([icon(glyph, tint, 16), kicker(title, tint)], spacing=6),
                *body,
            ], spacing=8)

        def numbered(i, line):
            return ft.Row([
                ft.Container(
                    content=text(str(i), BG, 11, ft.FontWeight.W_800, mono=True),
                    width=22, height=22, alignment=ft.Alignment.CENTER,
                    border_radius=ft.BorderRadius.all(11), bgcolor=color,
                ),
                ft.Container(content=text(line, TEXT, 13), expand=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

        def bullet(glyph, tint, line):
            return ft.Row([
                icon(glyph, tint, 16),
                ft.Container(content=text(line, MUTED, 13), expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START)

        def option(title, glyph, tint, line):
            return ft.Container(
                expand=True,
                padding=10,
                border_radius=ft.BorderRadius.all(12),
                bgcolor=alpha(tint, 0.08),
                border=ft.Border.all(1, alpha(tint, 0.3)),
                content=ft.Column([
                    ft.Row([icon(glyph, tint, 14), text(title, tint, 11, ft.FontWeight.W_700, mono=True)], spacing=4),
                    text(line, TEXT, 12),
                ], spacing=4),
            )

        chips = [pill(f"Цель {step.fmt(game.goal_for(step, self.engine.load()))}{step.side_note}", color, ft.Icons.FLAG_OUTLINED)]
        if step.requires_all or step.requires_any:
            chips.append(pill(step.requirement_text, MUTED, ft.Icons.FITNESS_CENTER))

        blocks = [
            ft.Row([
                icon_badge(BRANCH_ICONS[step.branch], color, 46),
                ft.Column([kicker(step.branch.title, color), text(step.name, TEXT, 19, ft.FontWeight.W_800)],
                          spacing=2, expand=True),
            ], spacing=12),
            ft.Row(chips, wrap=True, spacing=6, run_spacing=6),
            section("Работают мышцы", ft.Icons.ACCESSIBILITY_NEW, MUTED, [text(guide.muscles, TEXT, 13)]),
            section("Техника", ft.Icons.FORMAT_LIST_NUMBERED, color,
                    [numbered(i, line) for i, line in enumerate(guide.steps, 1)]),
            section("Частые ошибки", ft.Icons.ERROR_OUTLINE, DANGER,
                    [bullet(ft.Icons.CLOSE_ROUNDED, DANGER, line) for line in guide.mistakes]),
            ft.Row([
                option("ЛЕГЧЕ", ft.Icons.SOUTH_ROUNDED, SUCCESS, guide.easier),
                option("СЛОЖНЕЕ", ft.Icons.NORTH_ROUNDED, GOLD, guide.harder),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
        ]
        wrapped = [
            ft.Container(
                content=b,
                opacity=0,
                offset=ft.Offset(0, 0.25),
                animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(450, ft.AnimationCurve.EASE_OUT_CUBIC),
            )
            for b in blocks
        ]
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(color, 0.5))),
            content=ft.Container(
                width=340,
                height=520,
                content=ft.Column(wrapped, spacing=16, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[primary_button("ПОНЯТНО", close, ft.Icons.CHECK, height=46,
                                    colors=[color, alpha(color, 0.7)])],
        ))
        self.page.run_task(self.play_anims, [
            (0.08 + i * 0.07, w, {"opacity": 1, "offset": ft.Offset(0, 0)}) for i, w in enumerate(wrapped)
        ])

    def show_weigh_in(self, daily=False):
        """Ежедневный замер веса: крупное число, кнопки ±0.1/±1 кг и ползунок вокруг прошлого значения."""
        if self.dialog_open or not self.engine.profile:
            return
        self.dialog_open = True
        self.weigh_open = True
        history = self.engine.weights()
        last = history[-1][1] if history else self.engine.profile["weight_kg"]
        previous = next((kg for day, kg in reversed(history) if day != game.today()), None)
        state = {"kg": last}
        low, high = max(30.0, round(last - 5, 1)), min(250.0, round(last + 5, 1))

        number = text(f"{last:.1f}", TEXT, 46, ft.FontWeight.W_900, mono=True)
        box = ft.Container(content=number, animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT_BACK))
        delta = text("", MUTED, 13, ft.FontWeight.W_600)
        slider = ft.Slider(
            min=low, max=high, divisions=int(round((high - low) * 10)), value=last,
            active_color=ACCENT, inactive_color=alpha(ACCENT, 0.18), thumb_color=ACCENT,
            on_change=lambda e: set_kg(e.control.value, bump=False),
        )

        def describe_delta(kg):
            if previous is None:
                return "Первый замер — дальше будет видна динамика."
            diff = round(kg - previous, 1)
            if diff == 0:
                return "Как в прошлый раз"
            return f"{'+' if diff > 0 else '−'}{abs(diff):.1f} кг с прошлого замера"

        def set_kg(value, bump=True):
            kg = round(min(high, max(low, value)), 1)
            changed = kg != state["kg"]
            state["kg"] = kg
            number.value = f"{kg:.1f}"
            delta.value = describe_delta(kg)
            slider.value = kg
            if changed and bump:
                box.scale = 1.12
                self.page.run_task(self.play_anims, [(0.12, box, {"scale": 1})])
            self.page.update()

        delta.value = describe_delta(last)

        def close():
            self.page.pop_dialog()
            self.dialog_open = False
            self.weigh_open = False
            self.render()
            self.show_next_event()

        def save(_):
            events = self.engine.record_weight(state["kg"])
            close()
            self.push(events)

        def skip(_):
            self.engine.skip_weight()
            close()

        def step(amount, label):
            return ft.Container(
                content=text(label, ACCENT, 14, ft.FontWeight.W_700, mono=True),
                width=58, height=40, alignment=ft.Alignment.CENTER,
                border_radius=ft.BorderRadius.all(12),
                bgcolor=alpha(ACCENT, 0.1), border=ft.Border.all(1, alpha(ACCENT, 0.3)),
                ink=True, on_click=lambda _: set_kg(state["kg"] + amount),
            )

        badge = ft.Container(
            content=icon(ft.Icons.MONITOR_WEIGHT, ACCENT, 32),
            width=68, height=68, alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(34),
            bgcolor=alpha(ACCENT, 0.14), border=ft.Border.all(1, alpha(ACCENT, 0.45)),
            shadow=ft.BoxShadow(blur_radius=30, color=alpha(ACCENT, 0.45)),
            scale=0.3, opacity=0,
            animate_scale=ft.Animation(900, ft.AnimationCurve.ELASTIC_OUT),
            animate_opacity=ft.Animation(200),
        )
        actions = [ft.Row([
            ghost_button("Пропустить" if daily else "Отмена", skip if daily else (lambda _: close()), MUTED),
            primary_button("СОХРАНИТЬ", save, ft.Icons.CHECK, height=46, expand=True),
        ], spacing=8)]

        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(ACCENT, 0.5))),
            content=ft.Container(width=320, content=ft.Column([
                badge,
                kicker("[ Ежедневный замер ]"),
                text("Сколько ты весишь сегодня?", TEXT, 20, ft.FontWeight.W_800, align=ft.TextAlign.CENTER),
                text("Взвешивайся утром натощак — так замеры сравнимы между собой.", MUTED, 12,
                     align=ft.TextAlign.CENTER),
                ft.Row([box, text("кг", MUTED, 18, ft.FontWeight.W_700)], spacing=6,
                       alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.END),
                delta,
                ft.Row([step(-1, "−1"), step(-0.1, "−0.1"), step(0.1, "+0.1"), step(1, "+1")],
                       alignment=ft.MainAxisAlignment.CENTER, spacing=6),
                slider,
            ], spacing=10, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)),
            actions=actions,
        ))
        self.page.run_task(self.play_anims, [(0.1, badge, {"scale": 1, "opacity": 1})])

    def show_goals_dialog(self, first_time=False):
        """Выбор целей (несколько). Сразу показывает, что изменится в тренировке."""
        if self.dialog_open or not self.engine.profile:
            return
        self.dialog_open = True
        chosen = set(self.engine.goals())
        tiles = ft.Column(spacing=8)
        summary = ft.Container()
        error = text("", DANGER, 12)

        def refresh():
            tiles.controls = [self.goal_tile(g, g in chosen, toggle(g)) for g in game.Goal]
            summary.content = self.plan_summary(game.goal_plan(chosen)) if chosen else None
            error.value = ""

        def toggle(goal):
            def handler(_):
                chosen.symmetric_difference_update({goal})
                refresh()
                self.page.update()
            return handler

        def close():
            self.page.pop_dialog()
            self.dialog_open = False
            self.render()
            self.show_next_event()

        def save(_):
            if not chosen:
                error.value = "Выбери хотя бы одну цель."
                self.page.update()
                return
            applied_today = self.engine.set_goals(sorted(chosen, key=list(game.Goal).index))
            self.values.clear()
            close()
            if not first_time:
                self.push([Event("goals", {
                    "today": applied_today,
                    "titles": ", ".join(g.title for g in self.engine.goals()),
                    "lines": self.engine.plan().summary,
                })])

        refresh()
        actions = [ft.Row(
            ([] if first_time else [ghost_button("Отмена", lambda _: close(), MUTED)])
            + [primary_button("СОХРАНИТЬ", save, ft.Icons.CHECK, height=46, expand=True)],
            spacing=8,
        )]
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(ACCENT, 0.5))),
            content=ft.Container(width=340, height=520, content=ft.Column([
                kicker("[ Система ]" if first_time else "[ Цели ]"),
                text("Чего хочешь добиться?", TEXT, 20, ft.FontWeight.W_800),
                text("Теперь квесты подстраиваются под цель. Можно выбрать несколько." if first_time else
                     "Можно выбрать несколько. Квест подстроится под новый выбор.", MUTED, 13),
                tiles,
                summary,
                error,
            ], spacing=12, scroll=ft.ScrollMode.AUTO)),
            actions=actions,
        ))

    def show_sex_dialog(self, first_time=False):
        """Выбор пола. Для старых профилей спрашивается один раз, потом меняется из «Статуса»."""
        if self.dialog_open or not self.engine.profile:
            return
        self.dialog_open = True
        current = self.engine.sex() if self.engine.sex_known() else None

        def close():
            self.page.pop_dialog()
            self.dialog_open = False
            self.render()
            self.show_next_event()

        def choose(sex):
            def handler(_):
                self.engine.set_sex(sex)
                self.values.clear()
                close()
            return handler

        def tile(sex, subtitle, glyph, color):
            selected = sex is current
            return ft.Container(
                padding=14,
                border_radius=ft.BorderRadius.all(16),
                bgcolor=alpha(color, 0.12 if selected else 0.05),
                border=ft.Border.all(1.5 if selected else 1, color if selected else alpha(color, 0.35)),
                ink=True,
                on_click=choose(sex),
                content=ft.Row([
                    icon_badge(glyph, color, 40),
                    ft.Column([text(sex.title, TEXT, 16, ft.FontWeight.W_700), text(subtitle, MUTED, 12)],
                              spacing=2, expand=True),
                    icon(ft.Icons.CHECK_CIRCLE if selected else ft.Icons.CHEVRON_RIGHT_ROUNDED,
                         color if selected else FAINT, 20),
                ], spacing=12),
            )

        body = ("Теперь Система учитывает пол: для девушек нормы немного легче. "
                "Выбери, чтобы подстроить квесты." if first_time else
                "Текущие нормы пересчитаются под выбранный вариант. Прогресс по ступеням сохранится.")
        actions = [] if first_time else [ghost_button("Отмена", lambda _: close(), MUTED)]
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(ACCENT, 0.5))),
            content=ft.Container(width=320, content=ft.Column([
                kicker("[ Система ]" if first_time else "[ Пол ]"),
                text("Укажи пол", TEXT, 20, ft.FontWeight.W_800),
                text(body, MUTED, 13),
                tile(game.Sex.MALE, "Стандартные нормы", ft.Icons.MALE, ACCENT),
                tile(game.Sex.FEMALE, "Отжимания и подтягивания ~на треть легче, ноги и кор — чуть легче",
                     ft.Icons.FEMALE, ACCENT_2),
            ], spacing=12, tight=True)),
            actions=actions,
        ))

    def confirm(self, title, body, yes_label, on_yes, color=DANGER):
        """Окно подтверждения для необратимых действий."""
        if self.dialog_open:
            return
        self.dialog_open = True

        def close(_=None):
            self.page.pop_dialog()
            self.dialog_open = False
            self.show_next_event()

        def yes(_):
            close()
            on_yes()

        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(color, 0.5))),
            content=ft.Container(width=320, content=ft.Column([
                ft.Row([icon(ft.Icons.WARNING_AMBER, color, 22), kicker(f"[ {title} ]", color)], spacing=8),
                text(body, MUTED, 14),
            ], spacing=12, tight=True)),
            actions=[ft.Row([
                ghost_button("Отмена", close, MUTED),
                primary_button(yes_label, yes, height=44, expand=True, colors=[color, alpha(color, 0.7)]),
            ], spacing=8)],
        ))

    def tappable(self, step, control):
        return ft.Container(
            content=control,
            ink=True,
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.symmetric(vertical=4),
            on_click=lambda _: self.show_guide(step),
        )

    def guide_link(self, step, color=ACCENT):
        return ghost_button("Как выполнять", lambda _: self.show_guide(step), color, ft.Icons.MENU_BOOK_OUTLINED)
