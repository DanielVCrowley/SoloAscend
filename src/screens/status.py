"""Вкладка «Статус»: профиль, ранг, характеристики."""
import flet as ft
import flet.canvas as cv

import game
from common import EQUIPMENT_ICONS, fmt_day, plural
from programs import PROGRAM_BY_ID, TOTAL_SESSIONS
from screens.onboarding import GOAL_COLORS, GOAL_ICONS
from ui import (
    ACCENT, CARD, DANGER, FAINT, GOLD, LINE, MUTED, RANK_COLORS, STAT_COLORS, STAT_ICONS, SUCCESS, TEXT,
    alpha, bar, card, ghost_button, icon, icon_badge, kicker, page_header, pill, ring, stat_row, text,
)


class StatusScreen:
    def goals_card(self):
        e = self.engine
        goals = e.goals()
        chips = [pill(g.title, GOAL_COLORS[g], GOAL_ICONS[g]) for g in goals] or [text("Цели не выбраны", MUTED)]
        return card([
            ft.Row([
                kicker("Цели", ACCENT),
                ghost_button("Изменить", lambda _: self.show_goals_dialog(), ACCENT, ft.Icons.EDIT_OUTLINED),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(chips, wrap=True, spacing=6, run_spacing=6),
            *([self.plan_summary(e.plan())] if goals else []),
        ], ACCENT, glow=0.08, spacing=10)

    def streak_ladder(self):
        """Бонус к опыту за серию: ступени, текущий бонус и сколько дней до следующего."""
        streak = self.engine.active_streak()
        pct = game.streak_bonus(streak)
        nxt = game.next_streak_tier(streak)
        chips = []
        for days, tier_pct in game.STREAK_TIERS:
            reached = streak >= days
            current = reached and tier_pct == pct
            chip = ft.Container(
                expand=True,
                padding=ft.Padding.symmetric(vertical=8),
                border_radius=ft.BorderRadius.all(12),
                bgcolor=alpha(GOLD, 0.22 if current else (0.1 if reached else 0.0)),
                border=ft.Border.all(1.5 if current else 1, GOLD if reached else LINE),
                content=ft.Column([
                    text(f"+{tier_pct}%", GOLD if reached else MUTED, 15, ft.FontWeight.W_800, mono=True),
                    text(f"{days} дн.", TEXT if reached else FAINT, 11),
                ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            )
            chips.append(self.pulse(chip, 1.05) if current else chip)

        if nxt:
            days, tier_pct = nxt
            prev = max((d for d, _ in game.STREAK_TIERS if d <= streak), default=0)
            left = days - streak
            status = f"До +{tier_pct}%: ещё {left} {plural(left, 'день', 'дня', 'дней')}"
            progress = bar((streak - prev) / (days - prev), GOLD, 6)
        else:
            status, progress = "Максимальный бонус серии", bar(1, GOLD, 6)

        return [
            ft.Row([
                text("Бонус к опыту", TEXT, 14, ft.FontWeight.W_700),
                pill(f"+{pct}% XP" if pct else "нет", GOLD if pct else MUTED, ft.Icons.LOCAL_FIRE_DEPARTMENT),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(chips, spacing=6),
            progress,
            text(status, MUTED, 12),
            text("Действует на весь опыт: подходы, награду за квест, заминку и программы. "
                 "Пропуск дня обнуляет серию.", FAINT, 11),
        ]

    def weight_card(self):
        """Вес: крупное текущее значение, изменение за неделю, линия замеров и таблица последних."""
        e = self.engine
        history = e.weights()[-30:]
        today = game.today()
        day, current = history[-1]
        recorded_today = day == today

        week_base = next((kg for d, kg in reversed(history) if d <= today - 7), history[0][1])
        diff = round(current - week_base, 1)
        trend = ft.Icons.TRENDING_FLAT if diff == 0 else (ft.Icons.TRENDING_UP if diff > 0 else ft.Icons.TRENDING_DOWN)
        span = min(7, today - history[0][0]) or 0
        diff_text = (f"{'+' if diff > 0 else '−' if diff < 0 else '±'}{abs(diff):.1f} кг за {span} дн."
                     if len(history) > 1 and span else "Первый замер")

        rows = [
            ft.Row([
                kicker("Вес", ACCENT),
                ghost_button("Изменить сегодня" if recorded_today else "Записать вес",
                             lambda _: self.show_weigh_in(), ACCENT, ft.Icons.EDIT_OUTLINED),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                text(f"{current:.1f}", TEXT, 36, ft.FontWeight.W_900, mono=True),
                text("кг", MUTED, 16, ft.FontWeight.W_700),
                ft.Container(expand=True),
                ft.Row([icon(trend, MUTED, 18), text(diff_text, MUTED, 12, mono=True)], spacing=4),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.END),
        ]

        if len(history) >= 2:
            low = min(kg for _, kg in history)
            high = max(kg for _, kg in history)
            rows.append(ft.Row([
                ft.Container(content=self.weight_line(history), expand=True, height=76),
                ft.Column([
                    text(f"{high:.1f}", MUTED, 10, mono=True),
                    text(f"{low:.1f}", MUTED, 10, mono=True),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, height=76),
            ], spacing=8))
            first_day, _ = fmt_day(history[0][0])
            rows.append(ft.Row([
                text(first_day, FAINT, 10, mono=True),
                text("сегодня" if recorded_today else fmt_day(day)[0], FAINT, 10, mono=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
        else:
            rows.append(text("График появится после второго замера.", FAINT, 12))

        recent = list(reversed(history))[:5]
        table = []
        for i, (d, kg) in enumerate(recent):
            before = recent[i + 1][1] if i + 1 < len(recent) else None
            change = "" if before is None else f"{'+' if kg > before else '−' if kg < before else '±'}{abs(kg - before):.1f}"
            table.append(ft.Row([
                text("Сегодня" if d == today else fmt_day(d)[0], MUTED, 12),
                ft.Container(expand=True),
                text(change, FAINT, 11, mono=True),
                ft.Container(content=text(f"{kg:.1f} кг", TEXT, 13, ft.FontWeight.W_600, mono=True),
                             width=70, alignment=ft.Alignment.CENTER_RIGHT),
            ], spacing=8))
        rows += [ft.Divider(color=LINE, height=1), kicker("Последние замеры", MUTED), *table]
        return card(rows, ACCENT, glow=0.1, spacing=10)

    @staticmethod
    def weight_line(history):
        """Линия замеров на холсте: ось X — дни, Y — вес. Перерисовывается под ширину экрана."""
        height = 76.0
        first, last = history[0][0], history[-1][0]
        low = min(kg for _, kg in history)
        high = max(kg for _, kg in history)
        pad = 8.0

        def shapes(width):
            width = max(width, 40.0)
            span_x = max(1, last - first)
            span_y = high - low

            def point(d, kg):
                x = pad + (d - first) / span_x * (width - 2 * pad)
                y = height / 2 if span_y == 0 else pad + (high - kg) / span_y * (height - 2 * pad)
                return x, y

            pts = [point(d, kg) for d, kg in history]
            grid = ft.Paint(color=alpha(LINE, 0.9), stroke_width=1, style=ft.PaintingStyle.STROKE)
            line = ft.Paint(color=ACCENT, stroke_width=2, style=ft.PaintingStyle.STROKE,
                            stroke_cap=ft.StrokeCap.ROUND, stroke_join=ft.StrokeJoin.ROUND)
            path = [cv.Path.MoveTo(*pts[0])] + [cv.Path.LineTo(x, y) for x, y in pts[1:]]
            lx, ly = pts[-1]
            return [
                cv.Line(0, pad, width, pad, paint=grid),
                cv.Line(0, height - pad, width, height - pad, paint=grid),
                cv.Path(path, paint=line),
                cv.Circle(lx, ly, 6, paint=ft.Paint(color=CARD, style=ft.PaintingStyle.FILL)),
                cv.Circle(lx, ly, 4, paint=ft.Paint(color=ACCENT, style=ft.PaintingStyle.FILL)),
            ]

        canvas = cv.Canvas(shapes=shapes(280), height=height, expand=True)

        def resize(e):
            canvas.shapes = shapes(e.width)
            canvas.update()

        canvas.on_resize = resize
        return canvas

    def status(self, animate):
        r = lambda c: self.reveal(c, animate)
        e = self.engine
        p = e.profile
        lvl = e.level()
        rank = e.rank()
        rank_color = RANK_COLORS[rank]
        meters = p["height_cm"] / 100
        equipment = e.equipment()
        done = e.today_done()

        badge, _ = ring(lvl.fraction, 104, rank_color, ft.Column([
            text(rank.value, rank_color, 40, ft.FontWeight.W_900),
            text("РАНГ", MUTED, 10, ft.FontWeight.W_700, mono=True, spacing=2),
        ], spacing=0, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER), stroke=7)

        hero = card([
            ft.Row([
                ft.Container(content=badge, shadow=ft.BoxShadow(blur_radius=40, spread_radius=-12, color=alpha(rank_color, 0.6)), border_radius=52),
                ft.Column([
                    text(p["name"], TEXT, 24, ft.FontWeight.W_800),
                    text(f"Уровень {lvl.level}", rank_color, 16, ft.FontWeight.W_600),
                    text(f"{lvl.current} / {lvl.needed} XP до следующего", MUTED, 12, mono=True),
                    ft.Row([
                        pill(f"{e.active_streak()} дн." + (f" · +{e.streak_bonus()}%" if e.streak_bonus() else ""),
                             GOLD, ft.Icons.LOCAL_FIRE_DEPARTMENT),
                        pill("Квест ✓" if done else "Квест ✗", SUCCESS if done else DANGER),
                    ], spacing=6, wrap=True),
                ], spacing=4, expand=True),
            ], spacing=18),
            bar(lvl.fraction, rank_color, 6),
        ], rank_color, glow=0.2)

        tiles = []
        for stat, value in e.stats().items():
            color = STAT_COLORS[stat]
            tiles.append(ft.Container(col=4, content=ft.Container(
                padding=14,
                border_radius=ft.BorderRadius.all(16),
                bgcolor=alpha(CARD, 0.9),
                border=ft.Border.all(1, alpha(color, 0.25)),
                content=ft.Column([
                    icon_badge(STAT_ICONS[stat], color, 34),
                    text(value, TEXT, 26, ft.FontWeight.W_800, mono=True),
                    text(stat.value, MUTED, 12),
                ], spacing=6),
            )))

        skills_card = []
        done_programs = [PROGRAM_BY_ID[i] for i in e.programs_done() if i in PROGRAM_BY_ID]
        active = e.program()
        if done_programs or active:
            rows = [kicker("Освоенные навыки", GOLD)]
            if done_programs:
                rows.append(ft.Row([pill(p.name, GOLD, ft.Icons.MILITARY_TECH) for p in done_programs],
                                   wrap=True, spacing=6, run_spacing=6))
            else:
                rows.append(text("Пока ни одного — заверши первую программу.", MUTED, 12))
            if active:
                done = e.program_state()["session"]
                rows += [
                    ft.Divider(color=LINE, height=1),
                    stat_row("Сейчас осваиваю", active.name, leading=ft.Icons.SCHOOL),
                    bar(done / TOTAL_SESSIONS, ACCENT, 6),
                    text(f"{done} из {TOTAL_SESSIONS} тренировок", MUTED, 12, mono=True),
                ]
            skills_card = [r(card(rows, GOLD, glow=0.1))]

        return [
            r(page_header("Статус", "Профиль игрока")),
            r(hero),
            r(self.goals_card()),
            r(self.weight_card()),
            *skills_card,
            r(ft.Column([kicker("Характеристики", MUTED), ft.ResponsiveRow(tiles, spacing=10)], spacing=10)),
            r(card([
                kicker("Серия", GOLD),
                ft.Row([
                    self.metric(str(e.active_streak()), "подряд", GOLD),
                    self.metric(str(p["best_streak"]), "рекорд", TEXT),
                    self.metric(str(len(e.history())), "дней всего", ACCENT),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                ft.Divider(color=LINE, height=1),
                *self.streak_ladder(),
            ], GOLD, glow=0.08)),
            r(card([
                kicker("Тело", MUTED),
                stat_row("Вес", f"{p['weight_kg']:.1f} кг", leading=ft.Icons.MONITOR_WEIGHT),
                stat_row("Рост", f"{p['height_cm']} см", leading=ft.Icons.HEIGHT),
                stat_row("ИМТ", f"{e.bmi():.1f} · {game.bmi_tier(e.bmi())[1].lower()}", leading=ft.Icons.FAVORITE_BORDER),
                stat_row(
                    "Нагрузка",
                    "стандартная" if e.load().weight_factor == 1 else f"−{round((1 - e.load().weight_factor) * 100)}% из-за веса",
                    GOLD if e.load().weight_factor < 1 else TEXT,
                    leading=ft.Icons.SPEED,
                ),
                ft.Row([
                    ft.Container(content=stat_row(
                        "Пол", e.sex().title if e.sex_known() else "не указан",
                        leading=ft.Icons.MALE if e.sex() is game.Sex.MALE else ft.Icons.FEMALE,
                    ), expand=True),
                    ghost_button("Изменить", lambda _: self.show_sex_dialog(), ACCENT),
                ], spacing=4),
                ft.Divider(color=LINE, height=1),
                kicker("Инвентарь", MUTED),
                ft.Row(
                    [pill(x.value, ACCENT, EQUIPMENT_ICONS[x]) for x in equipment] or [text("Без инвентаря", MUTED)],
                    wrap=True, spacing=6, run_spacing=6,
                ),
            ], glow=0.06)),
        ]
