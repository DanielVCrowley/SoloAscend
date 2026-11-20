"""Диалоги: события Системы и окно «Как выполнять»."""
import asyncio

import flet as ft

try:  # встроенный плеер — расширение flet-webview (на телефоне)
    from flet_webview import WebView
except ImportError:  # без расширения остаются превью с переходом в YouTube
    WebView = None

import game
import programs
import videos
from common import plural
from engine import Event
from guides import GUIDES
from ui import (
    ACCENT, ACCENT_2, BG, BG_SOFT, BRANCH_ICONS, CARD, DANGER, FAINT, GOLD, MUTED, RANK_COLORS, STAT_COLORS,
    STAT_ICONS, SUCCESS, TEXT, alpha, ghost_button, icon, icon_badge, kicker, pill, primary_button, text,
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
        if event.kind in ("level", "stat_points"):
            self.events.pop(0)
            self.show_level_dialog(event if event.kind == "level" else None)
            return
        if event.kind == "focus":
            self.events.pop(0)
            if self.engine.focus_pending():
                self.show_focus_dialog(event)
            else:
                self.show_next_event()
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
        if event.kind == "focus_set":
            lines = "\n".join("• " + line for line in d["lines"])
            until = f"до ранга {d['until']}" if d["until"] else "на высшем ранге"
            when = "Сегодняшний квест уже пересобран." if d["today"] else "План сместится с завтрашнего квеста."
            return ("НАПРАВЛЕНИЕ ВЫБРАНО", d["stat"].value, f"Действует {until}.\n{lines}\n\n{when}",
                    STAT_COLORS[d["stat"]], STAT_ICONS[d["stat"]])
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

        video = videos.for_step(step.id)
        blocks = [
            ft.Row([
                icon_badge(BRANCH_ICONS[step.branch], color, 46),
                ft.Column([kicker(step.branch.title, color), text(step.name, TEXT, 19, ft.FontWeight.W_800)],
                          spacing=2, expand=True),
            ], spacing=12),
            *([self.video_card(video, color)] if video else []),
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

    # ---------- повышение уровня и ранга ----------

    def choice_dialog(self, color, badge_content, heading, headline, body, tiles, extra=None):
        """Окно-выбор без кнопки закрытия: значок «выпрыгивает», строки выезжают по очереди."""
        badge = ft.Container(
            content=badge_content,
            width=84, height=84,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(42),
            bgcolor=alpha(color, 0.14),
            border=ft.Border.all(1.5, alpha(color, 0.6)),
            shadow=ft.BoxShadow(blur_radius=34, color=alpha(color, 0.5)),
            scale=0.2, opacity=0, rotate=ft.Rotate(-0.8),
            animate_scale=ft.Animation(900, ft.AnimationCurve.ELASTIC_OUT),
            animate_rotation=ft.Animation(700, ft.AnimationCurve.EASE_OUT_BACK),
            animate_opacity=ft.Animation(200),
        )

        def rise(control):
            return ft.Container(
                content=control, opacity=0, offset=ft.Offset(0, 0.35),
                animate_opacity=ft.Animation(380, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(520, ft.AnimationCurve.EASE_OUT_CUBIC),
            )

        lines = [rise(kicker(f"[ {heading} ]", color)),
                 rise(text(headline, TEXT, 24, ft.FontWeight.W_900, align=ft.TextAlign.CENTER)),
                 rise(text(body, MUTED, 13, align=ft.TextAlign.CENTER))]
        if extra:
            lines.append(rise(extra))
        rows = [rise(t) for t in tiles]
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(color, 0.55))),
            content=ft.Container(width=330, content=ft.Column(
                [badge, *lines, ft.Container(height=2), *rows],
                spacing=10, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )),
        ))
        steps = [(0.1, badge, {"scale": 1, "opacity": 1, "rotate": ft.Rotate(0)})]
        steps += [(0.28 + i * 0.07, w, {"opacity": 1, "offset": ft.Offset(0, 0)}) for i, w in enumerate(lines + rows)]
        self.page.run_task(self.play_anims, steps)

    def choice_tile(self, glyph, color, title, subtitle, on_pick, trailing=None):
        tile = ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=ft.BorderRadius.all(16),
            bgcolor=alpha(color, 0.07),
            border=ft.Border.all(1, alpha(color, 0.4)),
            ink=True,
            animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(260, ft.AnimationCurve.EASE_OUT_BACK),
            content=ft.Row([
                icon_badge(glyph, color, 40),
                ft.Column([text(title, TEXT, 15, ft.FontWeight.W_700), text(subtitle, MUTED, 12)],
                          spacing=1, expand=True),
                trailing or icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color, 22),
            ], spacing=12),
        )

        def pick(_):
            if getattr(tile, "_picked", False):
                return
            tile._picked = True
            tile.bgcolor = alpha(color, 0.3)
            tile.border = ft.Border.all(2, color)
            tile.scale = 1.05
            self.page.update()
            on_pick()

        tile.on_click = pick
        return tile

    def close_choice(self, then=None):
        """Закрывает окно выбора чуть позже — чтобы успела проиграть подсветка выбранного варианта."""
        async def later():
            await asyncio.sleep(0.45)
            self.page.pop_dialog()
            self.dialog_open = False
            self.render()
            if then:
                then()
            self.show_next_event()
        self.page.run_task(later)

    def show_level_dialog(self, event=None):
        """Новый уровень: игрок выбирает, какую характеристику поднять на 1."""
        e = self.engine
        rank_up = bool(event and event.data.get("rank_up"))
        if self.dialog_open:
            return
        if e.unspent_points() <= 0:
            if rank_up and e.focus_pending():
                self.show_focus_dialog(event)
            else:
                self.show_next_event()
            return
        self.dialog_open = True
        level = e.level().level
        points = e.unspent_points()
        stats = e.stats()

        def picked(stat):
            def handler():
                e.spend_point(stat)

                def after():
                    if e.unspent_points() > 0:
                        self.events.insert(0, event or Event("stat_points", {}))
                    elif rank_up:
                        self.events.insert(0, Event("focus", dict(event.data)))
                self.close_choice(after)
            return handler

        tiles = []
        for stat in game.Stat:
            color = STAT_COLORS[stat]
            value = stats[stat]
            tiles.append(self.choice_tile(
                STAT_ICONS[stat], color, stat.value, f"{value} → {value + 1}", picked(stat),
                trailing=pill("+1", color),
            ))
        body = "Выбери, какую характеристику улучшить на 1."
        if points > 1:
            body += f"\nОчков к распределению: {points}"
        self.choice_dialog(
            GOLD, text(str(level), GOLD, 34, ft.FontWeight.W_900, mono=True),
            "Уровень повышен" if event else "Очки характеристик",
            f"Уровень {level}", body, tiles,
        )

    def show_focus_dialog(self, event=None):
        """Новый ранг: игрок выбирает направление тренировок до следующего ранга."""
        e = self.engine
        if self.dialog_open or not e.focus_pending():
            return
        self.dialog_open = True
        rank = e.rank()
        color = RANK_COLORS[rank]
        nxt = game.next_rank(rank)
        unlocked = (event.data.get("unlocked") if event else None) or []

        def picked(stat):
            def handler():
                today = e.choose_focus(stat)
                plan = e.plan()
                self.close_choice(lambda: self.events.insert(0, Event("focus_set", {
                    "stat": stat, "today": today, "lines": plan.summary,
                    "until": nxt.value if nxt else None,
                })))
            return handler

        tiles = [
            self.choice_tile(STAT_ICONS[stat], STAT_COLORS[stat], stat.value, game.FOCUS[stat]["hint"], picked(stat))
            for stat in game.Stat
        ]
        until = f"до ранга {nxt.value}" if nxt else "на высшем ранге"
        extra = None
        if unlocked:
            extra = pill("В квест добавлены: " + ", ".join(b.title.lower() for b in unlocked), SUCCESS, ft.Icons.LOCK_OPEN)
        self.choice_dialog(
            color, text(rank.value, color, 40, ft.FontWeight.W_900),
            "Новый ранг", f"Ранг {rank.value}",
            f"Выбери направление тренировок {until}. План немного сместится в его пользу.",
            tiles, extra,
        )

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

    # ---------- видео ----------

    def video_card(self, video, color=ACCENT, width=316):
        """Превью ролика с кнопкой ▶, названием и каналом. По нажатию открывается YouTube."""
        height = round(width * 9 / 16)
        placeholder = ft.Container(
            width=width, height=height, alignment=ft.Alignment.CENTER, bgcolor=CARD,
            content=ft.Column([
                icon(ft.Icons.VIDEOCAM_OFF_OUTLINED, FAINT, 28),
                text("Превью не загрузилось — нужен интернет", FAINT, 11, align=ft.TextAlign.CENTER),
            ], spacing=6, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )
        play = ft.Container(
            width=58, height=58, alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius.all(29),
            bgcolor=alpha(BG, 0.72),
            border=ft.Border.all(1.5, color),
            shadow=ft.BoxShadow(blur_radius=24, color=alpha(color, 0.6)),
            content=icon(ft.Icons.PLAY_ARROW_ROUNDED, color, 34),
        )
        layers = [
            ft.Image(src=video.thumb, width=width, height=height, fit=ft.BoxFit.COVER,
                     gapless_playback=True, error_content=placeholder),
            ft.Container(width=width, height=height, gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
                colors=[alpha(BG, 0.0), alpha(BG, 0.55)],
            )),
            ft.Container(width=width, height=height, alignment=ft.Alignment.CENTER, content=self.pulse(play, 1.08)),
        ]
        if video.length:
            layers.append(ft.Container(
                right=8, bottom=8, padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border_radius=ft.BorderRadius.all(6), bgcolor=alpha(BG, 0.8),
                content=text(video.length, TEXT, 11, ft.FontWeight.W_700, mono=True),
            ))
        return ft.Container(
            ink=True,
            on_click=lambda _: self.open_video(video),
            border_radius=ft.BorderRadius.all(16),
            bgcolor=alpha(CARD, 0.9),
            border=ft.Border.all(1, alpha(color, 0.35)),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column([
                ft.Stack(layers, width=width, height=height),
                ft.Container(padding=ft.Padding.only(left=12, right=12, top=8, bottom=10), content=ft.Column([
                    ft.Text(video.title, color=TEXT, size=13, weight=ft.FontWeight.W_600,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row([
                        icon(ft.Icons.SMART_DISPLAY, DANGER, 16),
                        ft.Container(content=text(f"YouTube · {video.channel}", MUTED, 11), expand=True),
                        icon(ft.Icons.OPEN_IN_NEW, FAINT, 14),
                    ], spacing=6),
                ], spacing=4)),
            ], spacing=0),
        )

    def can_embed_video(self) -> bool:
        """Встроенный плеер работает только на телефоне (WebView на Windows не поддерживается)."""
        return WebView is not None and \
            getattr(self.page, "platform", None) in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)

    def autoplay_video(self) -> bool:
        return self.can_embed_video() and self.engine.autoplay_video()

    def video_player(self, video, color=ACCENT, height=196):
        """Встроенный плеер YouTube: сам стартует без звука и крутится по кругу.
        Где встраивание недоступно — карточка-превью с переходом в YouTube."""
        if not self.can_embed_video():
            return self.video_card(video, color)
        view = WebView(url="about:blank", expand=True, bgcolor=BG, prevent_links=videos.BLOCKED_LINKS)
        player = {"view": view, "html": video.player_html(), "loaded": False}

        async def on_ended(e):
            # about:blank загрузился — теперь кладём свою страницу (иначе её перезапишет пустая)
            await self.load_player(player)

        view.on_page_ended = on_ended
        self.pending_players.append(player)
        box = ft.Container(
            expand=True,
            border_radius=ft.BorderRadius.all(16),
            bgcolor=alpha(CARD, 0.9),
            border=ft.Border.all(1, alpha(color, 0.35)),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column([
                ft.Container(height=height, bgcolor="#000000", content=view),
                ft.Container(padding=ft.Padding.only(left=12, right=4, top=6, bottom=6), content=ft.Row([
                    icon(ft.Icons.SMART_DISPLAY, DANGER, 16),
                    ft.Column([
                        ft.Text(video.title, color=TEXT, size=12, weight=ft.FontWeight.W_600,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        text(f"{video.channel} · звук — коснись видео", MUTED, 10),
                    ], spacing=0, expand=True),
                    ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, icon_color=MUTED, icon_size=18,
                                  tooltip="Открыть в YouTube", on_click=lambda _: self.open_video(video)),
                ], spacing=8)),
            ], spacing=0),
        )
        return ft.Row([box])  # строка растягивает плеер на всю ширину карточки

    async def load_player(self, player):
        if player["loaded"]:
            return
        player["loaded"] = True
        try:
            await player["view"].load_html(player["html"], base_url=videos.PLAYER_ORIGIN + "/")
        except Exception:
            player["loaded"] = False

    async def flush_players(self, players, generation=None):
        """Подстраховка: если событие загрузки about:blank не пришло — грузим плеер сами."""
        await asyncio.sleep(1.2)
        for player in players:
            if generation is not None and generation != self.generation:
                return
            await self.load_player(player)

    def video_button(self, video, color=ACCENT, label="Видео"):
        return ghost_button(label, lambda _: self.open_video(video), color, ft.Icons.SMART_DISPLAY_OUTLINED)

    def open_video(self, video):
        """Открывает ролик в YouTube. Таймер разминки/заминки ставится на паузу, чтобы не убежал."""
        if self.routine and self.routine.get("end"):
            self.toggle_pause()
        self.page.run_task(self.launch_url, video.url)

    async def launch_url(self, url):
        launcher = getattr(self, "launcher", None) or ft.UrlLauncher()
        self.launcher = launcher
        try:
            await launcher.launch_url(url, mode=ft.LaunchMode.EXTERNAL_APPLICATION)
        except Exception:
            try:
                await launcher.launch_url(url)
            except Exception:
                pass

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
