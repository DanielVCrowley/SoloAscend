import flet as ft

from game import Branch, Rank, Stat

BG = "#05070E"
BG_SOFT = "#0A0F1C"
CARD = "#0E1527"
CARD_HIGH = "#141E36"
LINE = "#1F2C48"
ACCENT = "#3DD6FF"
ACCENT_2 = "#7B6CFF"
TEXT = "#EAF3FF"
MUTED = "#8494B2"
FAINT = "#4A5878"
GOLD = "#FFC857"
DANGER = "#FF5A76"
SUCCESS = "#4FE3A0"
MONO = "monospace"

RANK_COLORS = {Rank.E: "#9AA8C2", Rank.D: SUCCESS, Rank.C: ACCENT, Rank.B: ACCENT_2, Rank.A: GOLD, Rank.S: DANGER}

BRANCH_ICONS = {
    Branch.PUSH: ft.Icons.FITNESS_CENTER,
    Branch.PULL: ft.Icons.SPORTS_GYMNASTICS,
    Branch.LEGS: ft.Icons.DIRECTIONS_RUN,
    Branch.CORE: ft.Icons.SELF_IMPROVEMENT,
}

STAT_ICONS = {
    Stat.STRENGTH: ft.Icons.BOLT,
    Stat.AGILITY: ft.Icons.TRENDING_UP,
    Stat.VITALITY: ft.Icons.SHIELD,
}

STAT_COLORS = {Stat.STRENGTH: DANGER, Stat.AGILITY: SUCCESS, Stat.VITALITY: ACCENT}


def alpha(color, value):
    return ft.Colors.with_opacity(value, color)


def text(value, color=TEXT, size=14, weight=None, mono=False, spacing=None, align=None):
    return ft.Text(
        str(value),
        color=color,
        size=size,
        weight=weight,
        font_family=MONO if mono else None,
        text_align=align or ft.TextAlign.START,
        style=ft.TextStyle(letter_spacing=spacing) if spacing else None,
    )


def kicker(value, color=ACCENT):
    return text(value.upper(), color, 11, ft.FontWeight.W_700, mono=True, spacing=2.5)


def icon(name, color=ACCENT, size=20):
    return ft.Icon(name, color=color, size=size)


def card(controls, accent=ACCENT, padding=18, spacing=12, glow=0.14):
    return ft.Container(
        content=ft.Column(controls, spacing=spacing),
        padding=padding,
        border_radius=ft.BorderRadius.all(18),
        border=ft.Border.all(1, alpha(accent, 0.28)),
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[CARD_HIGH, CARD],
        ),
        shadow=ft.BoxShadow(blur_radius=28, spread_radius=-6, color=alpha(accent, glow), offset=ft.Offset(0, 8)),
    )


def pill(value, color=ACCENT, leading=None):
    controls = []
    if leading:
        controls.append(icon(leading, color, 14))
    controls.append(text(value, color, 12, ft.FontWeight.W_600))
    return ft.Container(
        content=ft.Row(controls, spacing=4, tight=True),
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        border_radius=ft.BorderRadius.all(20),
        bgcolor=alpha(color, 0.12),
        border=ft.Border.all(1, alpha(color, 0.3)),
    )


def icon_badge(name, color=ACCENT, size=40):
    return ft.Container(
        content=icon(name, color, size * 0.5),
        width=size,
        height=size,
        alignment=ft.Alignment.CENTER,
        border_radius=ft.BorderRadius.all(size * 0.32),
        bgcolor=alpha(color, 0.14),
        border=ft.Border.all(1, alpha(color, 0.3)),
    )


def bar(fraction, color=ACCENT, height=8):
    return ft.ProgressBar(
        value=max(0.0, min(1.0, fraction)),
        bar_height=height,
        color=color,
        bgcolor=alpha(LINE, 0.9),
        border_radius=ft.BorderRadius.all(height),
    )


def ring(fraction, size, color, center, stroke=8):
    progress = ft.ProgressRing(
        value=max(0.0, min(1.0, fraction)),
        stroke_width=stroke,
        color=color,
        bgcolor=alpha(LINE, 0.9),
        stroke_cap=ft.StrokeCap.ROUND,
        width=size,
        height=size,
    )
    stack = ft.Stack(
        [
            ft.Container(width=size, height=size, content=progress),
            ft.Container(width=size, height=size, alignment=ft.Alignment.CENTER, content=center),
        ],
        width=size,
        height=size,
    )
    return stack, progress


def primary_button(label, on_click, leading=None, disabled=False, height=54, expand=False, colors=None):
    colors = colors or [ACCENT, ACCENT_2]
    row = [text(label, BG if not disabled else MUTED, 15, ft.FontWeight.W_700, spacing=1)]
    if leading:
        row.insert(0, icon(leading, BG if not disabled else MUTED, 20))
    return ft.Container(
        content=ft.Row(row, alignment=ft.MainAxisAlignment.CENTER, spacing=8),
        height=height,
        expand=expand,
        border_radius=ft.BorderRadius.all(14),
        gradient=None if disabled else ft.LinearGradient(
            begin=ft.Alignment.CENTER_LEFT, end=ft.Alignment.CENTER_RIGHT, colors=colors
        ),
        bgcolor=CARD_HIGH if disabled else None,
        shadow=None if disabled else ft.BoxShadow(blur_radius=22, spread_radius=-8, color=alpha(colors[0], 0.6), offset=ft.Offset(0, 6)),
        ink=True,
        disabled=disabled,
        on_click=on_click,
        padding=ft.Padding.symmetric(horizontal=18),
    )


def ghost_button(label, on_click, color=MUTED, leading=None):
    row = [text(label, color, 14, ft.FontWeight.W_600)]
    if leading:
        row.insert(0, icon(leading, color, 18))
    return ft.Container(
        content=ft.Row(row, spacing=6, tight=True),
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        border_radius=ft.BorderRadius.all(12),
        ink=True,
        on_click=on_click,
    )


def round_button(name, on_click, disabled=False, color=ACCENT):
    return ft.Container(
        content=icon(name, FAINT if disabled else color, 20),
        width=42,
        height=42,
        alignment=ft.Alignment.CENTER,
        border_radius=ft.BorderRadius.all(21),
        bgcolor=alpha(color, 0.06 if disabled else 0.12),
        border=ft.Border.all(1, alpha(color, 0.15 if disabled else 0.35)),
        ink=True,
        disabled=disabled,
        on_click=on_click,
    )


def select_tile(title, subtitle, leading, selected, on_click, color=ACCENT):
    return ft.Container(
        content=ft.Row([
            icon_badge(leading, color if selected else MUTED, 44),
            ft.Column([
                text(title, TEXT, 16, ft.FontWeight.W_600),
                text(subtitle, MUTED, 12),
            ], spacing=2, expand=True),
            icon(ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED, color if selected else FAINT, 22),
        ], spacing=14),
        padding=16,
        border_radius=ft.BorderRadius.all(16),
        bgcolor=alpha(color, 0.1) if selected else alpha(CARD, 0.8),
        border=ft.Border.all(1.5 if selected else 1, color if selected else LINE),
        animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
        ink=True,
        on_click=on_click,
    )


def stat_row(label, value, color=TEXT, leading=None):
    left = [text(label, MUTED)]
    if leading:
        left.insert(0, icon(leading, MUTED, 16))
    return ft.Row(
        [ft.Row(left, spacing=8, tight=True), text(value, color, 14, ft.FontWeight.W_600, mono=True)],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def field(value, label, on_change, keyboard=ft.KeyboardType.TEXT, leading=None, expand=None, autofocus=False, on_submit=None, suffix=None):
    return ft.TextField(
        value=value,
        label=label,
        keyboard_type=keyboard,
        on_change=on_change,
        on_submit=on_submit,
        autofocus=autofocus,
        expand=expand,
        color=TEXT,
        text_size=18,
        filled=True,
        fill_color=alpha(CARD, 0.9),
        border_radius=ft.BorderRadius.all(14),
        border_color=LINE,
        focused_border_color=ACCENT,
        focused_border_width=1.5,
        cursor_color=ACCENT,
        label_style=ft.TextStyle(color=MUTED),
        prefix_icon=leading,
        suffix=text(suffix, MUTED) if suffix else None,
        content_padding=ft.Padding.symmetric(horizontal=16, vertical=18),
    )


def segments(current, total, color=ACCENT):
    return ft.Row(
        [
            ft.Container(
                height=4,
                expand=True,
                border_radius=ft.BorderRadius.all(4),
                bgcolor=color if i < current else LINE,
                animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            )
            for i in range(total)
        ],
        spacing=6,
    )


def page_header(section, title, trailing=None):
    left = ft.Column([kicker(f"SYSTEM // {section}"), text(title, TEXT, 28, ft.FontWeight.W_800)], spacing=2, expand=True)
    return ft.Row([left] + ([trailing] if trailing else []), vertical_alignment=ft.CrossAxisAlignment.END)
