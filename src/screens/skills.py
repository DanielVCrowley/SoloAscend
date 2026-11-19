"""Вкладка «Навыки»: лестницы прогрессий по веткам."""
import flet as ft

import game
from game import Branch
from ui import (
    ACCENT, BG, BRANCH_ICONS, FAINT, LINE, MUTED, STAT_COLORS, SUCCESS, TEXT, alpha, bar, card,
    icon, icon_badge, page_header, pill, text,
)


class SkillsScreen:
    def skills(self, animate):
        r = lambda c: self.reveal(c, animate)
        e = self.engine
        equipment = e.equipment()
        result = [r(page_header("Навыки", "Ветки развития", self.level_pill()))]
        for branch in Branch:
            pr = e.progress.get(branch.name)
            if not pr:
                continue
            current = game.STEP_BY_ID[pr["step"]]
            current_tier = game.tier(current)
            color = STAT_COLORS[branch.stat]
            ladder = game.full_ladder(branch)
            unlocked = sum(1 for s in ladder if game.tier(s) <= current_tier and s.available_with(equipment))
            available = sum(1 for s in ladder if s.available_with(equipment))

            in_quest = branch in game.quest_branches(e.rank(), e.goals())
            rows = [ft.Row([
                icon_badge(BRANCH_ICONS[branch], color, 44),
                ft.Column([
                    text(branch.title, TEXT, 18, ft.FontWeight.W_800),
                    text(f"{branch.stat.value} · {pr['xp']} XP", MUTED, 12, mono=True),
                ], spacing=2, expand=True),
                pill(f"{unlocked}/{available}", color) if in_quest
                else pill("не в целях" if branch is Branch.CARDIO else f"с ранга {game.QUEST_UNLOCK[branch].value}",
                          FAINT, ft.Icons.LOCK_OUTLINE),
            ], spacing=12)]

            for i, step in enumerate(ladder):
                is_current = step is current
                locked_eq = not step.available_with(equipment)
                passed = not locked_eq and game.tier(step) < current_tier
                if is_current:
                    node_color, glyph = ACCENT, ft.Icons.PLAY_ARROW_ROUNDED
                elif locked_eq:
                    node_color, glyph = FAINT, ft.Icons.BLOCK
                elif passed:
                    node_color, glyph = SUCCESS, ft.Icons.CHECK
                else:
                    node_color, glyph = FAINT, ft.Icons.LOCK_OUTLINE

                node = ft.Container(
                    content=icon(glyph, BG if is_current or passed else node_color, 14),
                    width=26,
                    height=26,
                    alignment=ft.Alignment.CENTER,
                    border_radius=ft.BorderRadius.all(13),
                    bgcolor=node_color if is_current or passed else None,
                    border=ft.Border.all(1.5, node_color),
                    shadow=ft.BoxShadow(blur_radius=14, color=alpha(ACCENT, 0.7)) if is_current else None,
                )
                details = [text(
                    step.name,
                    TEXT if is_current else (MUTED if passed else FAINT),
                    15 if is_current else 14,
                    ft.FontWeight.W_700 if is_current else None,
                )]
                if is_current:
                    details += [
                        text(f"Минимум {step.fmt(pr['target'])} · цель {step.fmt(game.goal_for(step, e.load()))} в каждом подходе{step.side_note}", MUTED, 12),
                        bar(pr["target"] / game.goal_for(step, e.load()), ACCENT, 6),
                    ]
                    if step.tip:
                        details.append(text(step.tip, FAINT, 12))
                elif locked_eq:
                    details.append(text(f"Нужно: {step.requirement_text}", FAINT, 12))

                line = ft.Container(width=2, height=12, bgcolor=SUCCESS if passed else LINE, margin=ft.Margin.only(left=12))
                if i > 0:
                    rows.append(line)
                rows.append(self.tappable(step, ft.Row(
                    [node, ft.Column(details, spacing=4, expand=True),
                     icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, FAINT, 18)],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )))
            result.append(r(card(rows, color, spacing=4, glow=0.08)))
        return result
