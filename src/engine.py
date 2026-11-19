import json
import os
import time
from dataclasses import dataclass

import game
import programs
from game import Branch, Equipment


@dataclass
class Event:
    kind: str
    data: dict


@dataclass
class QuestItem:
    branch: Branch
    step: game.Step
    sets: int
    target: int
    done: list

    @property
    def completed(self) -> bool:
        return len(self.done) >= self.sets


class Engine:
    def __init__(self, path: str):
        self.path = path
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return {"profile": None, "progress": {}, "log": []}

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    @property
    def profile(self):
        return self.state["profile"]

    @property
    def progress(self) -> dict:
        return self.state["progress"]

    @property
    def log(self) -> list:
        return self.state["log"]

    def equipment(self) -> set:
        if not self.profile:
            return set()
        return {Equipment[name] for name in self.profile["equipment"] if name in Equipment.__members__}

    def level(self) -> game.LevelInfo:
        return game.level_info(self.profile["total_xp"])

    def rank(self) -> game.Rank:
        return game.rank_for(self.level().level)

    def create_profile(self, name: str, weight_kg: float, height_cm: int, experienced: bool, equipment: set):
        day = game.today()
        self.state["profile"] = {
            "name": name,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "experienced": experienced,
            "equipment": [e.name for e in equipment],
            "total_xp": 0,
            "streak": 0,
            "best_streak": 0,
            "last_completed_day": day - 1,
            "penalty_checked_day": day,
            "created_day": day,
            "weights": [{"day": day, "kg": weight_kg}],
            "weight_asked_day": day,
        }
        progress = {}
        for branch in Branch:
            step = game.start_step(branch, equipment, experienced)
            target = game.start_target(step)
            progress[branch.name] = {
                "step": step.id,
                "target": target,
                "xp": 0,
                "quest_day": day,
                "quest_step": step.id,
                "quest_target": target,
                "quest_sets": game.sets_for(game.Rank.E),
            }
        self.state["progress"] = progress
        self.state["log"] = []
        self._save()
        return [Event("welcome", {"name": name})]

    def apply_penalty(self) -> list:
        p = self.profile
        if not p:
            return []
        day = game.today()
        start = max(p["last_completed_day"], p["penalty_checked_day"]) + 1
        missed = day - start
        if missed <= 0:
            return []
        floor = game.level_start_xp(self.level().level)
        loss = min(missed, game.MAX_PENALTY_DAYS) * game.PENALTY_PER_DAY
        new_xp = max(floor, p["total_xp"] - loss)
        lost = p["total_xp"] - new_xp
        p.update(total_xp=new_xp, streak=0, penalty_checked_day=day - 1)
        self._save()
        return [Event("penalty", {"missed": missed, "lost": lost})]

    def _migrate_steps(self) -> bool:
        """Если упражнение из сохранения убрали из каталога — ставим стартовую ступень ветки."""
        changed = False
        equipment = self.equipment()
        for name, item in self.progress.items():
            if item["step"] not in game.STEP_BY_ID:
                step = game.start_step(Branch[name], equipment, self.profile["experienced"])
                item.update(step=step.id, target=game.start_target(step))
                changed = True
            if item.get("quest_step") not in game.STEP_BY_ID:
                item.update(quest_step=item["step"], quest_target=item["target"])
                changed = True
        return changed

    def quest_accepted(self) -> bool:
        day = game.today()
        return bool(self.profile) and (self.profile.get("accepted_day") == day or bool(self.day_sets(day)))

    def warmup_done(self) -> bool:
        day = game.today()
        return bool(self.profile) and (self.profile.get("warmup_day") == day or bool(self.day_sets(day)))

    def finish_warmup(self):
        if self.profile:
            self.profile["warmup_day"] = game.today()
            self._save()

    def accept_quest(self) -> bool:
        """Квест нельзя принять без разминки."""
        if not self.profile or not self.warmup_done():
            return False
        self.ensure_daily_quest()
        self.profile["accepted_day"] = game.today()
        self._save()
        return True

    def cooldown_result(self):
        """None — заминка ещё не пройдена сегодня, иначе "done" или "skipped"."""
        p = self.profile
        if p and p.get("cooldown_day") == game.today():
            return p.get("cooldown_result")
        return None

    def finish_cooldown(self, completed: bool) -> list:
        p = self.profile
        if not p or not self.today_done() or self.cooldown_result():
            return []
        p.update(cooldown_day=game.today(), cooldown_result="done" if completed else "skipped")
        events = self._add_xp(game.COOLDOWN_BONUS) if completed else []
        self._save()
        return events

    # ---------- ежедневный замер веса ----------

    def weights(self) -> list:
        """История замеров [(день, кг)] по возрастанию дня. Старые профили — один замер из анкеты."""
        p = self.profile
        if not p:
            return []
        entries = p.get("weights") or [{"day": p["created_day"], "kg": p["weight_kg"]}]
        return [(w["day"], w["kg"]) for w in sorted(entries, key=lambda w: w["day"])]

    def weight_due(self) -> bool:
        """Сегодня вес ещё не вводили и не пропускали."""
        return bool(self.profile) and self.profile.get("weight_asked_day") != game.today()

    def record_weight(self, kg: float) -> float:
        p = self.profile
        kg = round(min(250.0, max(30.0, kg)), 1)
        day = game.today()
        entries = [w for w in (p.get("weights") or [{"day": p["created_day"], "kg": p["weight_kg"]}]) if w["day"] != day]
        entries.append({"day": day, "kg": kg})
        p.update(weights=entries, weight_kg=kg, weight_asked_day=day)
        self._save()
        return kg

    def skip_weight(self):
        if self.profile:
            self.profile["weight_asked_day"] = game.today()
            self._save()

    # ---------- программы навыков ----------

    def program(self):
        """Активная программа или None."""
        p = self.profile
        state = p.get("program") if p else None
        if not state or state["id"] not in programs.PROGRAM_BY_ID:
            return None
        return programs.PROGRAM_BY_ID[state["id"]]

    def program_state(self) -> dict:
        return self.profile.get("program") or {}

    def programs_done(self) -> list:
        return list(self.profile.get("programs_done", [])) if self.profile else []

    def can_start_program(self, program) -> str:
        """Пустая строка — можно начать, иначе причина отказа."""
        if self.program():
            return "Сначала заверши или брось текущую программу."
        if not program.available_with(self.equipment()):
            return "Нужен инвентарь: " + ", ".join(e.value for e in program.equipment) + "."
        return ""

    def start_program(self, program_id: str) -> bool:
        program = programs.PROGRAM_BY_ID.get(program_id)
        if not self.profile or not program or self.can_start_program(program):
            return False
        self.profile["program"] = {
            "id": program_id, "started_day": game.today(), "session": 0,
            "last_day": None, "marks": [], "marks_day": None,
        }
        self._save()
        return True

    def abandon_program(self):
        if self.profile and self.profile.get("program"):
            self.profile["program"] = None
            self._save()

    def session_drills(self) -> tuple:
        program = self.program()
        return program.session(self.program_state()["session"]) if program else ()

    def session_started(self) -> bool:
        return bool(self.program()) and self.program_state().get("marks_day") == game.today()

    def session_available(self) -> bool:
        """Тренировка программы — не чаще одной в день."""
        state = self.program_state()
        return bool(self.program()) and state.get("last_day") != game.today() \
            and state["session"] < programs.TOTAL_SESSIONS

    def start_session(self) -> bool:
        if not self.session_available() or not self.warmup_done():
            return False
        state = self.program_state()
        if state.get("marks_day") != game.today():
            state.update(marks=[0] * len(self.session_drills()), marks_day=game.today())
            self._save()
        return True

    def session_marks(self) -> list:
        state = self.program_state()
        if state.get("marks_day") != game.today():
            return [0] * len(self.session_drills())
        return list(state["marks"])

    def mark_set(self, drill_index: int) -> bool:
        if not self.session_started():
            return False
        state = self.program_state()
        drills = self.session_drills()
        if not 0 <= drill_index < len(drills) or state["marks"][drill_index] >= drills[drill_index].sets:
            return False
        state["marks"][drill_index] += 1
        self._save()
        return True

    def session_complete(self) -> bool:
        drills = self.session_drills()
        return self.session_started() and all(m >= d.sets for m, d in zip(self.session_marks(), drills))

    def finish_session(self) -> list:
        if not self.session_complete():
            return []
        program = self.program()
        state = self.program_state()
        number = state["session"] + 1
        state.update(session=number, last_day=game.today(), marks=[], marks_day=None)
        gained = programs.SESSION_XP
        events = [Event("program_session", {"program": program, "number": number, "xp": programs.SESSION_XP})]
        if number >= programs.TOTAL_SESSIONS:
            gained += programs.PROGRAM_XP
            done = self.profile.setdefault("programs_done", [])
            if program.id not in done:
                done.append(program.id)
            self.profile["program"] = None
            events = [Event("program_done", {"program": program, "xp": programs.SESSION_XP + programs.PROGRAM_XP})]
        pr = self.progress.get(program.branch.name)
        if pr:
            pr["xp"] += gained
        events += self._add_xp(gained)
        self._save()
        return events

    def _add_xp(self, amount: int) -> list:
        p = self.profile
        before = game.level_info(p["total_xp"]).level
        p["total_xp"] += amount
        after = game.level_info(p["total_xp"]).level
        if after <= before:
            return []
        return [Event("level", {
            "level": after,
            "rank": game.rank_for(after),
            "rank_up": game.rank_for(after) != game.rank_for(before),
            "unlocked": [
                b for b in game.quest_branches(game.rank_for(after))
                if b not in game.quest_branches(game.rank_for(before))
            ],
        })]

    def ensure_daily_quest(self):
        if not self.profile:
            return
        day = game.today()
        sets = game.sets_for(self.rank())
        changed = self._migrate_steps()
        if self.profile.get("quest_branches_day") != day:
            self.profile.update(
                quest_branches=[b.name for b in game.quest_branches(self.rank())],
                quest_branches_day=day,
            )
            changed = True
        for item in self.progress.values():
            if item["quest_day"] != day:
                item.update(quest_day=day, quest_step=item["step"], quest_target=item["target"], quest_sets=sets)
                changed = True
        if changed:
            self._save()

    def day_sets(self, day: int, branch: Branch = None) -> list:
        return [s for s in self.log if s["day"] == day and (branch is None or s["branch"] == branch.name)]

    def quest_branches(self) -> list:
        """Ветки сегодняшнего квеста. Фиксируются на день, чтобы новый ранг не менял квест посреди дня."""
        p = self.profile
        if p and p.get("quest_branches_day") == game.today():
            return [Branch[name] for name in p["quest_branches"]]
        return game.quest_branches(self.rank()) if p else []

    def quest(self) -> list:
        day = game.today()
        items = []
        for branch in self.quest_branches():
            pr = self.progress.get(branch.name)
            if not pr:
                continue
            fresh = pr["quest_day"] == day
            done = [s["value"] for s in sorted(self.day_sets(day, branch), key=lambda s: s["time"])]
            items.append(QuestItem(
                branch=branch,
                step=game.STEP_BY_ID[pr["quest_step"] if fresh else pr["step"]],
                sets=pr["quest_sets"] if fresh else game.sets_for(self.rank()),
                target=pr["quest_target"] if fresh else pr["target"],
                done=done,
            ))
        return items

    def quest_done(self) -> bool:
        day = game.today()
        branches = [b for b in self.quest_branches() if b.name in self.progress]
        return bool(branches) and all(
            self.progress[b.name]["quest_day"] == day
            and len(self.day_sets(day, b)) >= self.progress[b.name]["quest_sets"]
            for b in branches
        )

    def today_done(self) -> bool:
        return bool(self.profile) and self.profile["last_completed_day"] == game.today()

    def log_set(self, branch: Branch, value: int) -> list:
        p = self.profile
        pr = self.progress.get(branch.name)
        if not p or not pr or branch not in self.quest_branches():
            return []
        day = game.today()
        branch_sets = self.day_sets(day, branch)
        if pr["quest_day"] != day or len(branch_sets) >= pr["quest_sets"]:
            return []

        step = game.STEP_BY_ID[pr["quest_step"]]
        xp = game.xp_for_set(step, value)
        self.log.append({
            "day": day,
            "time": time.time(),
            "branch": branch.name,
            "step": step.id,
            "value": value,
            "xp": xp,
        })
        pr["xp"] += xp

        events = []
        values = [s["value"] for s in branch_sets] + [value]
        cleared = len(values) >= pr["quest_sets"] and all(v >= pr["quest_target"] for v in values)
        if cleared and pr["step"] == step.id:
            if pr["target"] >= step.goal:
                nxt = game.next_step(step, self.equipment())
                if nxt:
                    pr.update(step=nxt.id, target=game.start_target(nxt))
                    events.append(Event("skill", {"step": nxt}))
            else:
                pr["target"] = min(step.goal, pr["target"] + game.target_increment(step))

        gained = xp
        if self.quest_done() and p["last_completed_day"] != day:
            streak = p["streak"] + 1 if p["last_completed_day"] == day - 1 else 1
            gained += game.QUEST_BONUS
            p.update(streak=streak, best_streak=max(p["best_streak"], streak), last_completed_day=day)
            events.append(Event("quest", {"bonus": game.QUEST_BONUS, "streak": streak}))
        events += self._add_xp(gained)
        self._save()
        return events

    def stats(self) -> dict:
        result = {}
        for stat in game.Stat:
            xp = sum(pr["xp"] for name, pr in self.progress.items() if Branch[name].stat is stat)
            result[stat] = game.stat_value(xp)
        return result

    def history(self) -> list:
        days = {}
        for s in self.log:
            days.setdefault(s["day"], []).append(s)
        result = []
        for day in sorted(days, reverse=True):
            logs = sorted(days[day], key=lambda s: s["time"])
            entries = {}
            for s in logs:
                if s["step"] in game.STEP_BY_ID:
                    entries.setdefault(s["step"], []).append(s["value"])
            result.append({
                "day": day,
                "entries": [(game.STEP_BY_ID[k], v) for k, v in entries.items()],
                "xp": sum(s["xp"] for s in logs),
                "sets": len(logs),
                "kcal": game.kcal(self.profile["weight_kg"], len(logs)),
            })
        return result
