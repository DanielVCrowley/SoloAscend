"""Вкладка «Квест»: этапы дня, окно принятия, подходы, регулятор, удержания."""
import time

import flet as ft

import game
from common import fmt_seconds, plural, seconds_left
from game import Branch
from ui import (
    ACCENT, ACCENT_2, BG, BRANCH_ICONS, CARD, DANGER, FAINT, GOLD, LINE, MUTED, STAT_COLORS,
    SUCCESS, TEXT, alpha, card, ghost_button, icon, icon_badge, kicker, page_header, pill,
    primary_button, ring, round_button, text,
)


class QuestScreen:
    def quest(self, animate):
        r = lambda c: self.reveal(c, animate)
        e = self.engine
        items = e.quest()
        done = e.today_done()
        accepted = e.quest_accepted()
        routine = self.routine["kind"] if self.routine else None
        cooldown = e.cooldown_result()

        if not accepted and not done:
            stage = 0
        elif not done:
            stage = 1
        else:
            stage = 3 if cooldown else 2

        controls = [
            r(page_header("Квест", "Тренировка дня", self.level_pill())),
            r(self.stage_bar(stage)),
        ]

        if routine == "warmup":
            controls.append(r(self.routine_panel()))
            return controls
        if stage == 0:
            controls.append(r(self.quest_offer(items)))
            return controls

        controls.append(r(self.summary_card(items, done)))

        if done:
            if routine == "cooldown":
                controls.append(r(self.routine_panel()))
            elif not cooldown:
                controls.append(r(self.cooldown_offer()))
            else:
                controls.append(r(self.cooldown_summary(cooldown)))

        if self.rest_end and not self.hold:
            controls.append(self.rest_card(slide=bool(self.flash)))

        controls += [r(self.quest_card(q)) for q in items]
        return controls

    def start_rest(self, seconds: int):
        self.rest_total = seconds
        self.rest_end = time.monotonic() + seconds

    def rest_card(self, slide=False):
        """Карточка отдыха между подходами — общая для квеста и программ."""
        left = seconds_left(self.rest_end)
        label = text(fmt_seconds(left), GOLD, 18, ft.FontWeight.W_800, mono=True)
        rest_ring, rest_progress = ring(left / self.rest_total, 72, GOLD, label, stroke=6)
        self.live.update(rest_text=label, rest_ring=rest_progress)

        def skip(_):
            self.rest_end = None
            self.render()

        rest = card([ft.Row([
            self.pulse(rest_ring, 1.04),
            ft.Column([text("Отдых", TEXT, 18, ft.FontWeight.W_700), text("Восстанови дыхание перед следующим подходом.", MUTED, 12)], spacing=2, expand=True),
            ghost_button("Пропустить", skip, GOLD),
        ], spacing=14)], GOLD, padding=14, glow=0.18)
        return self.slide_in(rest, 0.05, dy=-0.3) if slide else rest

    def stage_bar(self, stage):
        """Этапы дня: Разминка → Квест → Заминка. Текущий этап «дышит»."""
        names = [("Разминка", ft.Icons.SELF_IMPROVEMENT), ("Квест", ft.Icons.BOLT), ("Заминка", ft.Icons.SPA)]
        row = []
        for i, (name, glyph) in enumerate(names):
            passed, current = i < stage, i == stage
            color = SUCCESS if passed else (ACCENT if current else FAINT)
            dot = ft.Container(
                content=icon(ft.Icons.CHECK_ROUNDED if passed else glyph, BG if passed or current else FAINT, 16),
                width=32,
                height=32,
                alignment=ft.Alignment.CENTER,
                border_radius=ft.BorderRadius.all(16),
                bgcolor=color if passed or current else None,
                border=ft.Border.all(1.5, color),
                shadow=ft.BoxShadow(blur_radius=16, color=alpha(ACCENT, 0.7)) if current else None,
            )
            row.append(ft.Column([
                self.pulse(dot, 1.12) if current else dot,
                text(name, TEXT if current else (MUTED if passed else FAINT), 11, ft.FontWeight.W_700 if current else None),
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
            if i < len(names) - 1:
                line = ft.Container(
                    height=2,
                    expand=True,
                    margin=ft.Margin.only(bottom=18),
                    border_radius=ft.BorderRadius.all(2),
                    bgcolor=SUCCESS if i < stage else LINE,
                )
                row.append(line)
        return ft.Container(
            content=ft.Row(row, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=ft.BorderRadius.all(16),
            bgcolor=alpha(CARD, 0.7),
            border=ft.Border.all(1, LINE),
        )

    def summary_card(self, items, done):
        total = sum(q.sets for q in items)
        finished = sum(min(len(q.done), q.sets) for q in items)
        fraction = finished / total if total else 0
        color = SUCCESS if done else ACCENT
        start = self.prev_fraction if self.prev_fraction is not None else fraction

        percent = text(f"{round(start * 100)}%", TEXT, 26, ft.FontWeight.W_800, mono=True)
        counter = text(f"{finished}/{total}", MUTED, 11, mono=True)
        progress, ring_control = ring(start, 112, color, ft.Column(
            [percent, counter], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ), stroke=9)
        if start != fraction:
            self.live["ring_tween"] = (ring_control, percent, counter, start, fraction, finished, total)

        info = [
            text("Квест выполнен" if done else "Квест принят", TEXT, 20, ft.FontWeight.W_800),
            text("Награда получена. Осталась заминка." if done else "Выполни минимум в каждом подходе до конца дня.", MUTED, 13),
            ft.Row([pill(f"+{game.QUEST_BONUS} XP", SUCCESS, ft.Icons.EMOJI_EVENTS)], wrap=True),
        ]
        if not done:
            info[2].controls.append(pill(f"−{game.PENALTY_PER_DAY} XP за пропуск", DANGER))
        return card([ft.Row([progress, ft.Column(info, spacing=6, expand=True)], spacing=18)], color, glow=0.2)

    def quest_offer(self, items):
        """Окно Системы: задания на день. Принять квест можно только после разминки."""
        warmed = self.engine.warmup_done()

        def accept(_):
            if self.engine.accept_quest():
                self.render(animate=True)

        rows = []
        for i, q in enumerate(items):
            color = STAT_COLORS[q.branch.stat]
            rows.append(self.slide_in(self.tappable(q.step, ft.Row([
                icon_badge(BRANCH_ICONS[q.branch], color, 40),
                ft.Column([
                    kicker(q.branch.title, color),
                    text(q.step.name, TEXT, 15, ft.FontWeight.W_700),
                    text(f"{q.sets} {plural(q.sets, 'подход', 'подхода', 'подходов')} · минимум "
                         f"{q.step.fmt(q.target)}{q.step.side_note}", MUTED, 12),
                ], spacing=2, expand=True),
                self.pop_in(ft.Container(
                    content=ft.Column([
                        text("МИН.", MUTED, 9, ft.FontWeight.W_700, mono=True, spacing=1),
                        text(q.step.fmt(q.target), color, 20, ft.FontWeight.W_800, mono=True),
                    ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    width=62,
                    padding=ft.Padding.symmetric(vertical=6),
                    border_radius=ft.BorderRadius.all(12),
                    bgcolor=alpha(color, 0.12),
                    border=ft.Border.all(1, alpha(color, 0.35)),
                ), 0.45 + i * 0.12),
            ], spacing=12)), 0.25 + i * 0.12, dx=0.15, dy=0))
        rows.append(ft.Row([
            icon(ft.Icons.TOUCH_APP_OUTLINED, FAINT, 14),
            text("Нажми на упражнение, чтобы посмотреть технику", FAINT, 11),
        ], spacing=6))

        minutes = round(sum(m.seconds for m in game.WARMUP) / 60)
        warm_color = SUCCESS if warmed else GOLD
        warm_block = ft.Container(
            padding=12,
            border_radius=ft.BorderRadius.all(14),
            bgcolor=alpha(warm_color, 0.08),
            border=ft.Border.all(1, alpha(warm_color, 0.35)),
            content=ft.Row([
                icon(ft.Icons.CHECK_CIRCLE if warmed else ft.Icons.SELF_IMPROVEMENT, warm_color, 26),
                ft.Column([
                    text("Разминка выполнена" if warmed else "Сначала разминка", TEXT, 14, ft.FontWeight.W_700),
                    text("Можно принимать квест." if warmed else
                         f"{len(game.WARMUP)} упражнений · ~{minutes} мин · растяжка и кор. Пропустить нельзя.", MUTED, 12),
                ], spacing=2, expand=True),
            ], spacing=12),
        )

        if warmed:
            action = self.pulse(self.pop_in(primary_button("ПРИНЯТЬ КВЕСТ", accept, ft.Icons.CHECK), 0.6, start=0.6), 1.03)
            lock = []
        else:
            action = primary_button("НАЧАТЬ РАЗМИНКУ", lambda _: self.start_routine("warmup"), ft.Icons.PLAY_ARROW_ROUNDED,
                                    colors=[GOLD, alpha(GOLD, 0.7)])
            lock = [ft.Row([
                icon(ft.Icons.LOCK_OUTLINE, FAINT, 16),
                text("Кнопка «Принять квест» откроется после разминки", FAINT, 12),
            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER)]

        return card([
            ft.Row([
                self.pulse(icon_badge(ft.Icons.AUTO_AWESOME, ACCENT, 44), 1.08),
                ft.Column([
                    kicker("[ Ежедневный квест ]"),
                    text("Подготовка к росту", TEXT, 20, ft.FontWeight.W_800),
                ], spacing=2, expand=True),
            ], spacing=12),
            text("Система назначила задания на сегодня. В каждом подходе сделай не меньше нормы — "
                 "после подхода впишешь, сколько получилось на самом деле.", MUTED, 13),
            ft.Divider(color=LINE, height=1),
            *rows,
            ft.Divider(color=LINE, height=1),
            ft.Row([
                pill(f"+{game.QUEST_BONUS} XP", SUCCESS, ft.Icons.EMOJI_EVENTS),
                pill(f"−{game.PENALTY_PER_DAY} XP за пропуск", DANGER, ft.Icons.WARNING_AMBER),
            ], wrap=True, spacing=6),
            warm_block,
            action,
            *lock,
        ], ACCENT, glow=0.22, spacing=14)

    def cooldown_offer(self):
        minutes = round(sum(m.seconds for m in game.COOLDOWN) / 60)
        chips = ft.Row(
            [pill(m.name, ACCENT_2) for m in game.COOLDOWN],
            wrap=True, spacing=6, run_spacing=6,
        )
        return self.slide_in(card([
            ft.Row([
                self.pulse(icon_badge(ft.Icons.SPA, ACCENT_2, 44), 1.08),
                ft.Column([
                    kicker("[ Заминка ]", ACCENT_2),
                    text("Растяжка после квеста", TEXT, 20, ft.FontWeight.W_800),
                ], spacing=2, expand=True),
                pill(f"+{game.COOLDOWN_BONUS} XP", ACCENT_2),
            ], spacing=12),
            text(f"{len(game.COOLDOWN)} упражнений · ~{minutes} мин. Снимает напряжение и ускоряет восстановление. "
                 "Можно пропустить.", MUTED, 13),
            chips,
            ft.Row([
                ghost_button("Пропустить", lambda _: self.skip_cooldown(), MUTED, ft.Icons.SKIP_NEXT_ROUNDED),
                primary_button("НАЧАТЬ ЗАМИНКУ", lambda _: self.start_routine("cooldown"), ft.Icons.PLAY_ARROW_ROUNDED,
                               height=48, expand=True, colors=[ACCENT_2, alpha(ACCENT_2, 0.7)]),
            ], spacing=8),
        ], ACCENT_2, glow=0.18), 0.3)

    def cooldown_summary(self, result):
        ok = result == "done"
        color = ACCENT_2 if ok else FAINT
        return card([ft.Row([
            icon(ft.Icons.SPA if ok else ft.Icons.SKIP_NEXT_ROUNDED, color, 22),
            text("Заминка выполнена" if ok else "Заминка пропущена", TEXT if ok else MUTED, 15, ft.FontWeight.W_700),
            ft.Container(expand=True),
            pill(f"+{game.COOLDOWN_BONUS} XP", ACCENT_2) if ok else ft.Container(),
        ], spacing=10)], color, padding=14, glow=0.06)

    def regulator_value(self, q) -> int:
        key = q.branch.name
        state = (q.step.id, q.target, len(q.done))
        stored = self.values.get(key)
        if not stored or stored[0] != state:
            self.values[key] = (state, q.target)
        return self.values[key][1]

    def set_regulator(self, q, value: int):
        unit = game.regulator_step(q.step)
        top = game.regulator_max(q.step, q.target)
        value = min(top, max(unit, int(round(value / unit)) * unit))
        key = q.branch.name
        changed = value != self.values[key][1]
        self.values[key] = (self.values[key][0], value)
        live = self.live.get(f"reg_{key}")
        if not live:
            return
        number, box, status, slider = live
        ok = value >= q.target
        number.value = q.step.fmt(value)
        number.color = SUCCESS if ok else GOLD
        status.value = "норма выполнена" if ok else f"ниже нормы на {q.step.fmt(q.target - value)}"
        status.color = SUCCESS if ok else GOLD
        slider.value = value
        if changed:
            box.scale = 1.18
            self.page.run_task(self.play_anims, [(0.12, box, {"scale": 1})])
        self.page.update()

    def regulator(self, q, value):
        """Регулятор: −/+, крупное число и ползунок. Число «подпрыгивает» при изменении."""
        unit = game.regulator_step(q.step)
        top = game.regulator_max(q.step, q.target)
        ok = value >= q.target
        number = text(q.step.fmt(value), SUCCESS if ok else GOLD, 34, ft.FontWeight.W_900, mono=True)
        box = ft.Container(content=number, animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT_BACK))
        status = text(
            "норма выполнена" if ok else f"ниже нормы на {q.step.fmt(q.target - value)}",
            SUCCESS if ok else GOLD, 12, ft.FontWeight.W_600,
        )
        slider = ft.Slider(
            min=unit,
            max=top,
            divisions=max(1, (top - unit) // unit),
            value=value,
            active_color=ACCENT,
            inactive_color=alpha(ACCENT, 0.18),
            thumb_color=ACCENT,
            secondary_track_value=min(q.target, top),
            secondary_active_color=alpha(ACCENT, 0.4),
            on_change=lambda e: self.set_regulator(q, e.control.value),
        )
        self.live[f"reg_{q.branch.name}"] = (number, box, status, slider)

        def change(delta):
            return lambda _: self.set_regulator(q, self.values[q.branch.name][1] + delta)

        return ft.Column([
            ft.Row([
                round_button(ft.Icons.REMOVE, change(-unit)),
                ft.Column([box, status], spacing=0, tight=True, expand=True,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                round_button(ft.Icons.ADD, change(unit)),
            ], spacing=8),
            slider,
            ft.Row([
                text(q.step.fmt(unit), FAINT, 11, mono=True),
                text(f"мин. {q.step.fmt(q.target)}", MUTED, 11, mono=True),
                text(q.step.fmt(top), FAINT, 11, mono=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=2)

    def quest_card(self, q):
        is_reps = q.step.is_reps
        busy = self.hold is not None
        holding = busy and self.hold[0] is q.branch
        color = SUCCESS if q.completed else ACCENT
        flash = self.flash if self.flash and self.flash["branch"] is q.branch else None

        cells = []
        for i in range(q.sets):
            v = q.done[i] if i < len(q.done) else None
            current = v is None and i == len(q.done) and not q.completed
            cell_color = (ACCENT if current else LINE) if v is None else (SUCCESS if v >= q.target else GOLD)
            cell = ft.Container(
                expand=True,
                height=34,
                alignment=ft.Alignment.CENTER,
                border_radius=ft.BorderRadius.all(10),
                bgcolor=alpha(cell_color, 0.18 if v is not None else (0.08 if current else 0.0)),
                border=ft.Border.all(1.5 if current else 1, alpha(cell_color, 0.9 if v is not None or current else 1)),
                content=text("·" if v is None else q.step.fmt(v), MUTED if v is None else cell_color, 13, ft.FontWeight.W_700, mono=True),
            )
            if flash and i == flash["index"]:
                cell = self.pop_in(cell, 0.08, start=0.3, expand=True)
            elif current and not busy:
                cell = ft.Container(content=self.pulse(cell, 1.05), expand=True)
            cells.append(cell)

        badge = ft.Container(
            content=ft.Column([
                text("МИН.", MUTED, 9, ft.FontWeight.W_700, mono=True, spacing=1),
                text(q.step.fmt(q.target), color, 16, ft.FontWeight.W_800, mono=True),
            ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            border_radius=ft.BorderRadius.all(10),
            bgcolor=alpha(color, 0.12),
        )
        trailing = [badge]
        if flash:
            xp = ft.Container(
                content=text(f"+{flash['xp']} XP", GOLD, 14, ft.FontWeight.W_800, mono=True),
                opacity=0,
                offset=ft.Offset(0, 0.8),
                animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(900, ft.AnimationCurve.EASE_OUT_CUBIC),
            )
            self.anim(xp, 0.1, opacity=1, offset=ft.Offset(0, 0))
            self.anim(xp, 1.4, opacity=0, offset=ft.Offset(0, -1.2))
            trailing.insert(0, xp)

        header = ft.Row([
            icon_badge(BRANCH_ICONS[q.branch], color, 42),
            ft.Column([
                kicker(q.branch.title, color),
                text(q.step.name, TEXT, 17, ft.FontWeight.W_700),
            ], spacing=2, expand=True),
            *trailing,
        ], spacing=10)

        controls = [header, ft.Row(cells, spacing=8)]
        if q.completed:
            done_row = ft.Row([icon(ft.Icons.CHECK_CIRCLE, SUCCESS, 18), text("Выполнено", SUCCESS, 14, ft.FontWeight.W_700)], spacing=6)
            controls.append(self.pop_in(done_row, 0.35, start=0.5) if flash else done_row)
        elif holding:
            branch, seconds, end = self.hold
            left = seconds_left(end)
            label = text(fmt_seconds(left), GOLD, 20, ft.FontWeight.W_800, mono=True)
            hold_ring, hold_progress = ring(left / seconds, 84, GOLD, label, stroke=7)
            self.live.update(hold_text=label, hold_ring=hold_progress)
            controls.append(ft.Row([
                self.pulse(hold_ring, 1.05),
                ft.Column([
                    text("Держи позицию", TEXT, 16, ft.FontWeight.W_700),
                    text("Подход запишется сам. Не выдержал — нажми «Сдался», запишем сколько продержался.", MUTED, 12),
                ], spacing=2, expand=True),
            ], spacing=14))
            controls.append(ft.Row([
                ghost_button("Сдался", lambda _: self.stop_hold(), GOLD),
                ghost_button("Отмена", lambda _: self.cancel_hold(), DANGER),
            ], alignment=ft.MainAxisAlignment.END, spacing=6))
        else:
            value = self.regulator_value(q)
            n = len(q.done) + 1
            if q.step.tip:
                controls.append(ft.Row([
                    icon(ft.Icons.LIGHTBULB_OUTLINE, FAINT, 16),
                    ft.Container(content=text(q.step.tip, MUTED, 12), expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START))
            controls.append(ft.Row([self.guide_link(q.step)], alignment=ft.MainAxisAlignment.END))
            panel = ft.Container(
                padding=12,
                border_radius=ft.BorderRadius.all(14),
                bgcolor=alpha(ACCENT, 0.06),
                border=ft.Border.all(1, alpha(ACCENT, 0.2)),
                content=ft.Column([
                    ft.Row([
                        kicker(f"Подход {n} из {q.sets}", ACCENT),
                        text(f"минимум {q.step.fmt(q.target)}{q.step.side_note}", MUTED, 12),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    text("Сколько сделал?" if is_reps else "Сколько держать?", TEXT, 14, ft.FontWeight.W_700),
                    self.regulator(q, value),
                ], spacing=8),
            )
            controls.append(self.slide_in(panel, 0.2, dy=0.15) if flash else panel)

            def act(_):
                current = self.values[q.branch.name][1]
                if is_reps:
                    self.log_set(q.branch, current)
                else:
                    self.start_hold(q.branch, current)

            controls.append(primary_button(
                f"Записать подход {n}" if is_reps else "Старт таймера",
                act,
                ft.Icons.CHECK if is_reps else ft.Icons.TIMER,
                disabled=busy,
                height=50,
            ))

        body = ft.Container(
            content=card(controls, color, glow=0.1 if not q.completed else 0.04),
            opacity=0.75 if q.completed else 1,
        )
        if flash and flash["completed"]:
            return self.pop_in(body, 0.05, start=0.94, ms=700)
        return body

    def quest_fraction(self):
        items = self.engine.quest()
        total = sum(q.sets for q in items)
        return sum(min(len(q.done), q.sets) for q in items) / total if total else 0

    def log_set(self, branch: Branch, value: int):
        before = self.quest_fraction()
        index = len(self.engine.day_sets(game.today(), branch))
        events = self.engine.log_set(branch, value)
        if len(self.engine.day_sets(game.today(), branch)) > index:
            item = next(q for q in self.engine.quest() if q.branch is branch)
            self.flash = {"branch": branch, "index": index, "xp": self.engine.log[-1]["xp"], "completed": item.completed}
            self.prev_fraction = before
        if self.engine.quest_done():
            self.rest_end = None
        else:
            self.start_rest(game.REST_SECONDS)
        self.render()
        self.push(events)

    def start_hold(self, branch: Branch, seconds: int):
        if self.hold:
            return
        self.rest_end = None
        self.hold = (branch, seconds, time.monotonic() + seconds)
        self.render()

    def cancel_hold(self):
        self.hold = None
        self.render()

    def stop_hold(self):
        """Досрочная остановка удержания: записываем, сколько реально продержался."""
        if not self.hold:
            return
        branch, seconds, end = self.hold
        self.hold = None
        held = seconds - seconds_left(end)
        if held >= 1:
            self.log_set(branch, held)
        else:
            self.render()
