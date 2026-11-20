"""Вкладка «Программы»: месячные программы освоения навыков (выход силой, горизонт и др.)."""
import math
import time

import flet as ft

import game
import programs as prog_data
import videos
from common import fmt_seconds, seconds_left
from guides import GUIDES
from ui import (
    ACCENT, ACCENT_2, BG, BG_SOFT, CARD, DANGER, FAINT, GOLD, LINE, MUTED, SUCCESS, TEXT,
    alpha, card, ghost_button, icon, icon_badge, kicker, page_header, pill, primary_button, ring, text,
)

PROGRAM_ICONS = {
    "muscle_up": ft.Icons.KEYBOARD_DOUBLE_ARROW_UP,
    "planche": ft.Icons.AIRPLANEMODE_ACTIVE,
    "front_lever": ft.Icons.SPORTS_GYMNASTICS,
    "handstand": ft.Icons.ACCESSIBILITY_NEW,
    "back_lever": ft.Icons.SWAP_VERT,
    "first_pullup": ft.Icons.KEYBOARD_ARROW_UP,
    "pistol": ft.Icons.ACCESSIBILITY,
    "headstand": ft.Icons.PERSON,
    "bridge": ft.Icons.SPA,
    "splits": ft.Icons.OPEN_IN_FULL,
    "pullover": ft.Icons.SYNC,
    "hspu": ft.Icons.EMOJI_PEOPLE,
    "dragon_flag": ft.Icons.FLAG,
}
UPSIDE_DOWN = {"handstand", "headstand", "hspu"}  # иконки этих навыков переворачиваются
PROGRAM_COLORS = {
    "muscle_up": ACCENT_2,
    "planche": GOLD,
    "front_lever": ACCENT,
    "handstand": SUCCESS,
    "back_lever": DANGER,
    "first_pullup": ACCENT,
    "pistol": SUCCESS,
    "headstand": GOLD,
    "bridge": ACCENT_2,
    "splits": DANGER,
    "pullover": ACCENT_2,
    "hspu": GOLD,
    "dragon_flag": DANGER,
}
DIFFICULTY_COLORS = {"Лёгкая": SUCCESS, "Средняя": ACCENT, "Сложная": DANGER}
CATEGORIES = ["Сила", "Баланс", "Гибкость", "Пресс"]


class ProgramsScreen:
    # ---------- экран ----------

    def programs(self, animate):
        r = lambda c: self.reveal(c, animate)
        e = self.engine
        controls = [r(page_header("Программы", "Освоение навыков", self.level_pill()))]

        if self.routine and self.routine["kind"] == "warmup":
            controls.append(r(self.routine_panel()))
            return controls

        active = e.program()
        if active and e.session_started():
            return controls + self.session_view(active, r)

        if active:
            controls.append(r(self.active_program_card(active)))
        else:
            controls.append(r(card([ft.Row([
                self.pulse(icon_badge(ft.Icons.SCHOOL, ACCENT_2, 44), 1.08),
                ft.Column([
                    text("Выбери навык", TEXT, 18, ft.FontWeight.W_800),
                    text(f"Программа на {prog_data.WEEKS} недели: {prog_data.SESSIONS_PER_WEEK} тренировки в неделю, "
                         "в конце — испытание. Идёт параллельно с ежедневным квестом.", MUTED, 12),
                ], spacing=2, expand=True),
            ], spacing=12)], ACCENT_2, glow=0.14)))

        controls.append(r(kicker(f"Каталог навыков · {len(prog_data.PROGRAMS)}", MUTED)))
        controls.append(r(self.category_filter()))
        shown = [p for p in prog_data.PROGRAMS if not self.program_filter or p.category == self.program_filter]
        recommended = self.recommended_categories()
        shown.sort(key=lambda p: (p.category not in recommended, prog_data.PROGRAMS.index(p)))
        changed, self.filter_flash = self.filter_flash, False
        for i, p in enumerate(shown):
            tile = self.program_tile(p, p.category in recommended)
            controls.append(self.slide_in(tile, 0.04 + i * 0.05, dy=0.18) if changed else r(tile))
        return controls

    def recommended_categories(self) -> set:
        """Навыки под цель «Гибкость» и под выбранное направление тренировок."""
        e = self.engine
        found = set()
        if game.Goal.FLEX in e.goals():
            found.add("Гибкость")
        focus = e.focus()
        if focus is game.Stat.STRENGTH:
            found.add("Сила")
        elif focus is game.Stat.AGILITY:
            found |= {"Баланс", "Пресс"}
        return found

    def category_filter(self):
        """Фильтр каталога по типу навыка. Выбранный чип подсвечен."""
        counts = {c: sum(1 for p in prog_data.PROGRAMS if p.category == c) for c in CATEGORIES}

        def pick(value):
            def handler(_):
                if self.program_filter == value:
                    return
                self.program_filter = value
                self.filter_flash = True
                self.render()
            return handler

        chips = []
        for value, label in [(None, f"Все {len(prog_data.PROGRAMS)}")] + [(c, f"{c} {counts[c]}") for c in CATEGORIES]:
            on = self.program_filter == value
            chips.append(ft.Container(
                padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                border_radius=ft.BorderRadius.all(20),
                bgcolor=alpha(ACCENT, 0.18) if on else alpha(CARD, 0.85),
                border=ft.Border.all(1, ACCENT if on else LINE),
                ink=True,
                on_click=pick(value),
                content=text(label, TEXT if on else MUTED, 12, ft.FontWeight.W_700 if on else ft.FontWeight.W_500),
            ))
        return ft.Row(chips, wrap=True, spacing=6, run_spacing=6)

    def program_icon(self, program, size=44):
        color = PROGRAM_COLORS[program.id]
        badge = icon_badge(PROGRAM_ICONS[program.icon], color, size)
        if program.id in UPSIDE_DOWN:
            return ft.Container(content=badge, rotate=ft.Rotate(math.pi))
        return badge

    def program_tile(self, program, recommended=False):
        e = self.engine
        color = PROGRAM_COLORS[program.id]
        active = e.program()
        status = []
        if recommended:
            status.append(pill("★ Рекомендуем", GOLD))
        if program.id in e.programs_done():
            status.append(pill("Освоено", GOLD, ft.Icons.MILITARY_TECH))
        if active and active.id == program.id:
            status.append(pill("Активна", ACCENT, ft.Icons.PLAY_ARROW_ROUNDED))
        if not program.available_with(e.equipment()):
            status.append(pill("Нет инвентаря", FAINT, ft.Icons.LOCK_OUTLINE))

        equipment = " + ".join(x.value for x in program.equipment) or "Без инвентаря"
        return ft.Container(
            ink=True,
            border_radius=ft.BorderRadius.all(20),
            on_click=lambda _: self.show_program(program),
            content=card([
                ft.Row([
                    self.program_icon(program),
                    ft.Column([
                        text(program.name, TEXT, 18, ft.FontWeight.W_800),
                        text(program.goal, MUTED, 12),
                    ], spacing=2, expand=True),
                    icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, FAINT, 22),
                ], spacing=12),
                ft.Row([
                    pill(program.difficulty, DIFFICULTY_COLORS.get(program.difficulty, MUTED)),
                    pill(equipment, MUTED, ft.Icons.FITNESS_CENTER),
                    *status,
                ], wrap=True, spacing=6, run_spacing=6),
            ], color, glow=0.08, spacing=10),
        )

    # ---------- активная программа ----------

    def calendar(self, program, done):
        """12 тренировок, сгруппированных по неделям. Следующая «дышит», испытание — звезда."""
        color = PROGRAM_COLORS[program.id]
        weeks = []
        for w in range(prog_data.WEEKS):
            dots = []
            for s in range(prog_data.SESSIONS_PER_WEEK):
                n = w * prog_data.SESSIONS_PER_WEEK + s
                test = n == prog_data.TOTAL_SESSIONS - 1
                passed, current = n < done, n == done
                tint = SUCCESS if passed else (color if current else FAINT)
                glyph = ft.Icons.CHECK_ROUNDED if passed else (ft.Icons.STAR_ROUNDED if test else None)
                dot = ft.Container(
                    width=26, height=26, alignment=ft.Alignment.CENTER,
                    border_radius=ft.BorderRadius.all(13),
                    bgcolor=tint if passed or current else None,
                    border=ft.Border.all(1.5, tint),
                    content=icon(glyph, BG if passed or current else tint, 14) if glyph else
                    text(str(n + 1), BG if current else FAINT, 10, ft.FontWeight.W_700, mono=True),
                )
                dots.append(self.pulse(dot, 1.15) if current else dot)
            weeks.append(ft.Column([
                text(f"Н{w + 1}", MUTED, 10, ft.FontWeight.W_700, mono=True),
                ft.Row(dots, spacing=4),
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        return ft.Row(weeks, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def active_program_card(self, program):
        e = self.engine
        color = PROGRAM_COLORS[program.id]
        done = e.program_state()["session"]
        index = min(done, prog_data.TOTAL_SESSIONS - 1)
        test = index == prog_data.TOTAL_SESSIONS - 1
        week = program.week_of(index)
        drills = program.session(index, e.program_factor(program))

        progress, _ = ring(done / prog_data.TOTAL_SESSIONS, 86, color, ft.Column([
            text(f"{done}/{prog_data.TOTAL_SESSIONS}", TEXT, 18, ft.FontWeight.W_800, mono=True),
            text("ТРЕН.", MUTED, 9, ft.FontWeight.W_700, mono=True),
        ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER), stroke=7)

        plan = [
            self.slide_in(ft.Row([
                icon(ft.Icons.TIMER if d.seconds else ft.Icons.REPEAT, color, 16),
                ft.Container(content=text(d.name, TEXT, 13), expand=True),
                text(d.scheme, MUTED, 12, mono=True),
            ], spacing=8), 0.3 + i * 0.08, dx=0.12, dy=0)
            for i, d in enumerate(drills)
        ]

        if not e.session_available():
            action = primary_button("Следующая тренировка — завтра", None, ft.Icons.HOURGLASS_BOTTOM, disabled=True)
            hint = "Связкам нужен отдых: не больше одной тренировки программы в день."
        elif not e.warmup_done():
            action = primary_button("СНАЧАЛА РАЗМИНКА", lambda _: self.start_routine("warmup"),
                                    ft.Icons.SELF_IMPROVEMENT, colors=[GOLD, alpha(GOLD, 0.7)])
            hint = "Разминка общая с квестом: если уже делал её сегодня — повторять не нужно."
        else:
            action = self.pulse(self.pop_in(primary_button(
                "НАЧАТЬ ИСПЫТАНИЕ" if test else "НАЧАТЬ ТРЕНИРОВКУ", lambda _: self.begin_session(),
                ft.Icons.PLAY_ARROW_ROUNDED, colors=[color, alpha(color, 0.7)],
            ), 0.5, start=0.6), 1.03)
            hint = ""

        return card([
            ft.Row([
                self.program_icon(program, 46),
                ft.Column([
                    kicker("[ Активная программа ]", color),
                    text(program.name, TEXT, 20, ft.FontWeight.W_800),
                    text(f"Неделя {week} из {prog_data.WEEKS}", MUTED, 12),
                ], spacing=2, expand=True),
                progress,
            ], spacing=12),
            self.calendar(program, done),
            ft.Divider(color=LINE, height=1),
            ft.Row([
                kicker(f"Испытание" if test else f"Тренировка {index + 1}", color),
                text("Итог месяца" if test else program.weeks[week - 1].focus, MUTED, 12),
            ], spacing=8, wrap=True),
            *plan,
            action,
            *([text(hint, FAINT, 11, align=ft.TextAlign.CENTER)] if hint else []),
            ft.Row([
                ghost_button("План программы", lambda _: self.show_program(program), MUTED, ft.Icons.CALENDAR_MONTH),
                ghost_button("Бросить", lambda _: self.ask_abandon(program), DANGER, ft.Icons.CLOSE_ROUNDED),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], color, glow=0.2, spacing=12)

    # ---------- тренировка ----------

    def session_view(self, program, r):
        e = self.engine
        color = PROGRAM_COLORS[program.id]
        index = e.program_state()["session"]
        test = index == prog_data.TOTAL_SESSIONS - 1
        drills = e.session_drills()
        marks = e.session_marks()
        total = sum(d.sets for d in drills)
        done = sum(min(m, d.sets) for m, d in zip(marks, drills))
        complete = e.session_complete()

        header = card([
            ft.Row([
                self.program_icon(program, 42),
                ft.Column([
                    kicker(f"Неделя {program.week_of(index)} · " + ("Испытание" if test else
                           f"Тренировка {index + 1}/{prog_data.TOTAL_SESSIONS}"), color),
                    text(program.name, TEXT, 19, ft.FontWeight.W_800),
                ], spacing=2, expand=True),
                pill(f"+{prog_data.SESSION_XP + (prog_data.PROGRAM_XP if test else 0)} XP", GOLD),
            ], spacing=12),
            ft.ProgressBar(value=done / total if total else 0, bar_height=6, color=color,
                           bgcolor=alpha(LINE, 0.9), border_radius=ft.BorderRadius.all(6)),
            text(f"Подходов: {done} из {total}. Отдых между подходами — {prog_data.SKILL_REST_SECONDS} с.", MUTED, 12),
        ], color, glow=0.18)

        controls = [r(header)]
        if self.rest_end and not self.ptimer:
            controls.append(self.rest_card(slide=bool(self.pflash)))
        # текущее упражнение — первое незавершённое: у него видео запускается само
        pending = [i for i, d in enumerate(drills) if marks[i] < d.sets]
        if self.ptimer and self.ptimer[0] in pending:
            current = self.ptimer[0]
        elif self.focus_drill in pending:
            current = self.focus_drill
        else:
            current = pending[0] if pending else None
        controls += [r(self.drill_card(i, d, marks[i], color, i == current)) for i, d in enumerate(drills)]

        if complete:
            controls.append(self.pulse(self.pop_in(primary_button(
                "ЗАВЕРШИТЬ ИСПЫТАНИЕ" if test else "ЗАВЕРШИТЬ ТРЕНИРОВКУ", lambda _: self.finish_program_session(),
                ft.Icons.TASK_ALT, colors=[SUCCESS, alpha(SUCCESS, 0.7)],
            ), 0.2, start=0.5), 1.03))
        else:
            controls.append(primary_button("Выполни все подходы", None, ft.Icons.CHECKLIST, disabled=True))
        return controls

    def focus_program_drill(self, index):
        if self.ptimer:
            return
        self.focus_drill = index
        self.focus_flash = ("drill", index)
        self.render()

    def drill_row(self, index, drill, marked, color, complete):
        """Свёрнутое упражнение программы: выполненное — с галочкой, ожидающее — нажатие разворачивает."""
        flash = self.pflash if self.pflash and self.pflash[0] == index else None
        tint = SUCCESS if complete else MUTED
        dots = ft.Row([
            ft.Container(width=10, height=10, border_radius=5,
                         bgcolor=SUCCESS if k < marked else None,
                         border=ft.Border.all(1.5, SUCCESS if k < marked else LINE))
            for k in range(drill.sets)
        ], spacing=5)
        row = ft.Row([
            icon_badge(ft.Icons.TIMER if drill.seconds else ft.Icons.REPEAT, tint, 34),
            ft.Column([
                text(drill.name, TEXT, 14, ft.FontWeight.W_600),
                text(drill.scheme, MUTED, 11, mono=True),
            ], spacing=1, expand=True),
            icon(ft.Icons.CHECK_CIRCLE, SUCCESS, 22) if complete else dots,
            *([] if complete else [icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, FAINT, 20)]),
        ], spacing=10)
        body = ft.Container(
            ink=not complete,
            on_click=None if complete else (lambda _: self.focus_program_drill(index)),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=ft.BorderRadius.all(16),
            bgcolor=alpha(SUCCESS, 0.06) if complete else alpha(CARD, 0.85),
            border=ft.Border.all(1, alpha(SUCCESS, 0.25) if complete else LINE),
            content=row,
        )
        return self.pop_in(body, 0.05, start=0.9, ms=650) if flash else body

    def drill_card(self, index, drill, marked, color, current_drill=False):
        complete = marked >= drill.sets
        if complete or not current_drill:
            return self.drill_row(index, drill, marked, color, complete)
        flash = self.pflash if self.pflash and self.pflash[0] == index else None
        timing = self.ptimer is not None and self.ptimer[0] == index
        busy = self.ptimer is not None

        cells = []
        for k in range(drill.sets):
            done, current = k < marked, k == marked and not complete
            tint = SUCCESS if done else (color if current else LINE)
            cell = ft.Container(
                expand=True, height=30, alignment=ft.Alignment.CENTER,
                border_radius=ft.BorderRadius.all(9),
                bgcolor=alpha(tint, 0.18 if done else (0.08 if current else 0)),
                border=ft.Border.all(1.5 if current else 1, tint),
                content=icon(ft.Icons.CHECK_ROUNDED, SUCCESS, 16) if done else
                text(drill.fmt(), MUTED if not current else tint, 11, ft.FontWeight.W_700, mono=True),
            )
            if flash and k == flash[1]:
                cell = self.pop_in(cell, 0.06, start=0.3, expand=True)
            elif current and not busy:
                cell = ft.Container(content=self.pulse(cell, 1.05), expand=True)
            cells.append(cell)

        tint = SUCCESS if complete else color
        controls = [
            ft.Row([
                icon_badge(ft.Icons.TIMER if drill.seconds else ft.Icons.REPEAT, tint, 38),
                ft.Column([
                    text(drill.name, TEXT, 16, ft.FontWeight.W_700),
                    text(drill.scheme, tint, 12, ft.FontWeight.W_700, mono=True),
                ], spacing=2, expand=True),
            ], spacing=12),
            ft.Row(cells, spacing=6),
        ]
        video = videos.for_drill(drill)
        autoplay = current_drill and not complete and video is not None and self.autoplay_video()
        if autoplay:
            controls.insert(1, self.video_player(video, color))

        if complete:
            done_row = ft.Row([icon(ft.Icons.CHECK_CIRCLE, SUCCESS, 18), text("Выполнено", SUCCESS, 14, ft.FontWeight.W_700)], spacing=6)
            controls.append(self.pop_in(done_row, 0.3, start=0.5) if flash else done_row)
        else:
            controls.append(ft.Row([
                icon(ft.Icons.LIGHTBULB_OUTLINE, FAINT, 16),
                ft.Container(content=text(drill.tip, MUTED, 12), expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START))
            links = []
            if video and not autoplay:
                links.append(self.video_button(video, color))
            if drill.guide in GUIDES:
                links.append(self.guide_link(game.STEP_BY_ID[drill.guide], color))
            if links:
                controls.append(ft.Row(links, alignment=ft.MainAxisAlignment.END, spacing=0))
            if timing:
                _, seconds, end = self.ptimer
                left = seconds_left(end)
                label = text(fmt_seconds(left), GOLD, 20, ft.FontWeight.W_800, mono=True)
                timer_ring, progress = ring(left / seconds, 84, GOLD, label, stroke=7)
                self.live.update(ptimer_text=label, ptimer_ring=progress)
                controls.append(ft.Row([
                    self.pulse(timer_ring, 1.05),
                    ft.Column([
                        text("Держи позицию", TEXT, 16, ft.FontWeight.W_700),
                        text("Подход засчитается сам. «Готово» — засчитать досрочно.", MUTED, 12),
                    ], spacing=2, expand=True),
                ], spacing=14))
                controls.append(ft.Row([
                    ghost_button("Отмена", lambda _: self.cancel_ptimer(), DANGER),
                    ghost_button("Готово", lambda _: self.stop_ptimer(), GOLD, ft.Icons.CHECK),
                ], alignment=ft.MainAxisAlignment.END))
            else:
                n = marked + 1
                if drill.seconds:
                    action = primary_button(f"Старт · подход {n}", lambda _: self.start_ptimer(index, drill.value),
                                            ft.Icons.TIMER, disabled=busy, height=46, colors=[color, alpha(color, 0.7)])
                else:
                    action = primary_button(f"Подход {n} выполнен", lambda _: self.program_mark(index),
                                            ft.Icons.CHECK, disabled=busy, height=46, colors=[color, alpha(color, 0.7)])
                controls.append(action)

        body = ft.Container(content=card(controls, tint, glow=0.1))
        if self.focus_flash == ("drill", index):
            return self.pop_in(body, 0.03, start=0.95, ms=600)
        return body

    # ---------- действия ----------

    def begin_session(self):
        if self.engine.start_session():
            self.rest_end = None
            self.render(animate=True)

    def program_mark(self, index):
        marked = self.engine.session_marks()[index]
        if not self.engine.mark_set(index):
            return
        self.pflash = (index, marked)
        if self.engine.session_complete():
            self.rest_end = None
        else:
            self.start_rest(prog_data.SKILL_REST_SECONDS)
        self.render()

    def start_ptimer(self, index, seconds):
        if self.ptimer:
            return
        self.rest_end = None
        self.ptimer = (index, seconds, time.monotonic() + seconds)
        self.render()

    def stop_ptimer(self):
        if self.ptimer:
            index = self.ptimer[0]
            self.ptimer = None
            self.program_mark(index)

    def cancel_ptimer(self):
        self.ptimer = None
        self.render()

    def finish_program_session(self):
        events = self.engine.finish_session()
        if events:
            self.rest_end = None
            self.ptimer = None
            self.render(animate=True)
            self.push(events)

    def ask_abandon(self, program):
        def abandon():
            self.engine.abandon_program()
            self.ptimer = None
            self.rest_end = None
            self.render(animate=True)

        done = self.engine.program_state().get("session", 0)
        self.confirm(
            "Бросить программу",
            f"Прогресс «{program.name}» ({done} из {prog_data.TOTAL_SESSIONS} тренировок) будет сброшен. "
            "Начать её можно будет заново в любой момент.",
            "БРОСИТЬ", abandon,
        )

    # ---------- окно программы ----------

    def show_program(self, program):
        """Описание программы: требования, план по неделям, награды и кнопка старта."""
        if self.dialog_open:
            return
        self.dialog_open = True
        e = self.engine
        color = PROGRAM_COLORS[program.id]
        active = e.program()
        is_active = bool(active and active.id == program.id)
        reason = "" if is_active else e.can_start_program(program)
        factor = e.program_factor(program)

        def close(_=None):
            self.page.pop_dialog()
            self.dialog_open = False
            self.show_next_event()

        def start(_):
            close()
            if e.start_program(program.id):
                self.tab = 2
                self.render(animate=True)

        def drill_row(d):
            return ft.Row([
                icon(ft.Icons.TIMER if d.seconds else ft.Icons.REPEAT, FAINT, 14),
                ft.Container(content=text(d.name, TEXT, 12), expand=True),
                text(d.scheme, MUTED, 11, mono=True),
            ], spacing=6)

        weeks = []
        for w, week in enumerate(program.weeks, 1):
            weeks.append(ft.Container(
                padding=10,
                border_radius=ft.BorderRadius.all(12),
                bgcolor=alpha(CARD, 0.9),
                border=ft.Border.all(1, LINE),
                content=ft.Column([
                    ft.Row([kicker(f"Неделя {w}", color), text(week.focus, MUTED, 11)], spacing=8, wrap=True),
                    *[drill_row(d.scaled(factor)) for d in week.drills],
                ], spacing=6),
            ))
        weeks.append(ft.Container(
            padding=10,
            border_radius=ft.BorderRadius.all(12),
            bgcolor=alpha(GOLD, 0.08),
            border=ft.Border.all(1, alpha(GOLD, 0.4)),
            content=ft.Column([
                ft.Row([icon(ft.Icons.STAR_ROUNDED, GOLD, 16), kicker("Испытание · тренировка 12", GOLD)], spacing=6),
                *[drill_row(d.scaled(factor)) for d in program.test],
            ], spacing=6),
        ))

        blocks = [
            ft.Row([
                self.program_icon(program, 48),
                ft.Column([kicker(program.difficulty, DIFFICULTY_COLORS.get(program.difficulty, MUTED)),
                           text(program.name, TEXT, 20, ft.FontWeight.W_800)], spacing=2, expand=True),
            ], spacing=12),
            text(program.description, MUTED, 13),
            ft.Row([
                pill(f"{prog_data.WEEKS} нед · {prog_data.SESSIONS_PER_WEEK}×/нед", MUTED, ft.Icons.CALENDAR_MONTH),
                pill(" + ".join(x.value for x in program.equipment) or "Без инвентаря", MUTED, ft.Icons.FITNESS_CENTER),
                pill(f"+{prog_data.SESSION_XP} XP / трен.", ACCENT_2),
                pill(f"+{prog_data.PROGRAM_XP} XP за навык", GOLD, ft.Icons.MILITARY_TECH),
            ], wrap=True, spacing=6, run_spacing=6),
            ft.Container(
                padding=10,
                border_radius=ft.BorderRadius.all(12),
                bgcolor=alpha(DANGER, 0.06),
                border=ft.Border.all(1, alpha(DANGER, 0.3)),
                content=ft.Row([
                    icon(ft.Icons.INFO_OUTLINE, DANGER, 18),
                    ft.Container(content=ft.Column([
                        text("ТРЕБОВАНИЯ", DANGER, 11, ft.FontWeight.W_700, mono=True),
                        text(program.prereq, TEXT, 12),
                    ], spacing=2), expand=True),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
            ),
            kicker("План по неделям", MUTED),
            *weeks,
        ]
        wrapped = [
            ft.Container(
                content=b, opacity=0, offset=ft.Offset(0, 0.25),
                animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(450, ft.AnimationCurve.EASE_OUT_CUBIC),
            )
            for b in blocks
        ]

        if is_active:
            actions = [ghost_button("Закрыть", close, MUTED)]
        elif reason:
            actions = [ft.Column([
                text(reason, FAINT, 12, align=ft.TextAlign.CENTER),
                ghost_button("Закрыть", close, MUTED),
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.END)]
        else:
            actions = [ft.Row([
                ghost_button("Закрыть", close, MUTED),
                primary_button("НАЧАТЬ ПРОГРАММУ", start, ft.Icons.PLAY_ARROW_ROUNDED, height=46, expand=True,
                               colors=[color, alpha(color, 0.7)]),
            ], spacing=8)]

        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            bgcolor=BG_SOFT,
            shape=ft.RoundedRectangleBorder(radius=24, side=ft.BorderSide(width=1, color=alpha(color, 0.5))),
            content=ft.Container(width=350, height=540,
                                 content=ft.Column(wrapped, spacing=14, scroll=ft.ScrollMode.AUTO)),
            actions=actions,
        ))
        self.page.run_task(self.play_anims, [
            (0.08 + i * 0.06, w, {"opacity": 1, "offset": ft.Offset(0, 0)}) for i, w in enumerate(wrapped)
        ])
