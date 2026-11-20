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

    def create_profile(self, name: str, weight_kg: float, height_cm: int, experienced: bool, equipment: set,
                       sex: game.Sex = game.Sex.MALE, goals=()):
        day = game.today()
        load = game.Load(sex, game.bmi_tier(game.bmi(weight_kg, height_cm))[0])
        self.state["profile"] = {
            "name": name,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "experienced": experienced,
            "sex": sex.value,
            "weight_factor": load.weight_factor,
            "goals": [g.key for g in goals],
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
            step = game.start_step(branch, equipment, experienced, load)
            target = game.start_target(step, load)
            progress[branch.name] = {
                "step": step.id,
                "target": target,
                "xp": 0,
                "quest_day": day,
                "quest_step": step.id,
                "quest_target": target,
                "quest_sets": game.quest_sets(game.Rank.E, branch, goals),
                "stage": 0,
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
        for branch in Branch:
            if branch.name not in self.progress:
                step = game.start_step(branch, equipment, self.profile["experienced"], self.load())
                target = game.start_target(step, self.load())
                self.progress[branch.name] = {
                    "step": step.id, "target": target, "xp": 0, "stage": 0,
                    "quest_day": None, "quest_step": step.id, "quest_target": target,
                    "quest_sets": game.sets_for(self.rank()),
                }
                changed = True
        for name, item in self.progress.items():
            if item["step"] not in game.STEP_BY_ID:
                step = game.start_step(Branch[name], equipment, self.profile["experienced"], self.load())
                item.update(step=step.id, target=game.start_target(step, self.load()), stage=0)
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
        events = []
        if completed:
            bonus = game.with_streak(game.COOLDOWN_BONUS, self.active_streak())
            events = [Event("cooldown", {"bonus": bonus})] + self._add_xp(bonus)
        self._save()
        return events

    # ---------- пол ----------

    def sex(self) -> game.Sex:
        """Пол игрока. В старых профилях поля нет — считаем мужским, пока игрок не выберет."""
        value = self.profile.get("sex") if self.profile else None
        return game.Sex(value) if value in ("male", "female") else game.Sex.MALE

    def sex_known(self) -> bool:
        return bool(self.profile) and self.profile.get("sex") in ("male", "female")

    def program_factor(self, program) -> float:
        return game.sex_factor(program.branch, self.load())

    def set_sex(self, sex: game.Sex):
        """Смена пола пересчитывает нормы по этапу ступени — этап (пройденные дни) сохраняется."""
        p = self.profile
        if not p:
            return
        old = self.applied_load()
        p["sex"] = sex.value
        self._rescale(old)
        self._save()

    # ---------- нагрузка по весу ----------

    def bmi(self) -> float:
        return game.bmi(self.profile["weight_kg"], self.profile["height_cm"])

    def load(self) -> game.Load:
        """Нагрузка игрока: пол и поправка на ИМТ."""
        if not self.profile:
            return game.BASE_LOAD
        return game.Load(self.sex(), game.bmi_tier(self.bmi())[0])

    def applied_load(self) -> game.Load:
        """Нагрузка, под которую сейчас рассчитаны нормы в сохранении."""
        return game.Load(self.sex(), self.profile.get("weight_factor", 1.0))

    def _rescale(self, old: game.Load):
        """Пересчитывает текущие нормы под новую нагрузку. Этап ступени (пройденные дни) сохраняется."""
        new = self.load()
        self.profile["weight_factor"] = new.weight_factor
        if new == old:
            return
        for pr in self.progress.values():
            step = game.STEP_BY_ID[pr["step"]]
            stage = pr.get("stage", game.stage_of(step, pr["target"], old))
            # норма сегодняшнего квеста: по текущей ступени — тот же этап, иначе — этап по её значению
            quest_step = game.STEP_BY_ID[pr["quest_step"]]
            if quest_step is step and pr["quest_target"] == pr["target"]:
                quest_stage = stage
            else:
                quest_stage = game.stage_of(quest_step, pr["quest_target"], old)
            pr.update(
                stage=stage,
                target=game.target_at(step, stage, new),
                quest_target=game.target_at(quest_step, quest_stage, new),
                quest_stage=quest_stage,
            )

    # ---------- настройки ----------

    def autoplay_video(self) -> bool:
        """Автовоспроизведение видео в тренировке (по умолчанию включено)."""
        return bool(self.profile.get("autoplay_video", True)) if self.profile else True

    def set_autoplay_video(self, on: bool):
        if self.profile:
            self.profile["autoplay_video"] = bool(on)
            self._save()

    # ---------- цели ----------

    def goals(self) -> list:
        keys = self.profile.get("goals") if self.profile else None
        return [g for g in (game.Goal.from_key(k) for k in keys or []) if g]

    def goals_known(self) -> bool:
        return bool(self.profile) and "goals" in self.profile

    def plan(self) -> game.GoalPlan:
        return game.goal_plan(self.goals(), self.focus())

    def rest_seconds(self) -> int:
        return self.plan().rest

    def cooldown_moves(self) -> list:
        return game.COOLDOWN + (game.COOLDOWN_FLEX if self.plan().flex else [])

    def set_goals(self, goals) -> bool:
        """Сохраняет цели. Если сегодняшний квест ещё не начат — он сразу пересобирается под них.
        Возвращает True, если изменения применились уже сегодня."""
        p = self.profile
        if not p:
            return False
        p["goals"] = [g.key for g in goals]
        return self._rebuild_today()

    def _rebuild_today(self) -> bool:
        """Если сегодняшний квест ещё не начат — пересобирает его под новый план. True — применилось сегодня."""
        p = self.profile
        today_now = not self.quest_accepted() and not self.day_sets(game.today())
        if today_now:
            p["quest_branches_day"] = None
            for item in self.progress.values():
                item["quest_day"] = None
        self._save()
        if today_now:
            self.ensure_daily_quest()
        return today_now

    # ---------- характеристики и направление ----------

    def unspent_points(self) -> int:
        return int(self.profile.get("unspent_points", 0)) if self.profile else 0

    def stat_points(self) -> dict:
        """Очки, вложенные игроком в характеристики при повышениях уровня."""
        raw = self.profile.get("stat_points", {}) if self.profile else {}
        return {stat: int(raw.get(stat.name, 0)) for stat in game.Stat}

    def spend_point(self, stat: game.Stat) -> bool:
        p = self.profile
        if not p or self.unspent_points() <= 0:
            return False
        points = p.setdefault("stat_points", {})
        points[stat.name] = points.get(stat.name, 0) + 1
        p["unspent_points"] = self.unspent_points() - 1
        self._save()
        return True

    def focus(self):
        """Направление тренировок до следующего ранга (Stat) или None."""
        name = self.profile.get("focus") if self.profile else None
        return game.Stat[name] if name in game.Stat.__members__ else None

    def focus_pending(self) -> bool:
        return bool(self.profile and self.profile.get("focus_pending"))

    def choose_focus(self, stat: game.Stat) -> bool:
        """Выбор направления на новом ранге. True — сегодняшний квест уже пересобран."""
        p = self.profile
        if not p:
            return False
        p.update(focus=stat.name, focus_rank=self.rank().value, focus_pending=False)
        return self._rebuild_today()

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

    def record_weight(self, kg: float) -> list:
        """Сохраняет замер. Если вес перешёл в другую категорию ИМТ — нормы пересчитываются."""
        p = self.profile
        kg = round(min(250.0, max(30.0, kg)), 1)
        day = game.today()
        old_load, old_label = self.applied_load(), game.bmi_tier(self.bmi())[1]
        entries = [w for w in (p.get("weights") or [{"day": p["created_day"], "kg": p["weight_kg"]}]) if w["day"] != day]
        entries.append({"day": day, "kg": kg})
        p.update(weights=entries, weight_kg=kg, weight_asked_day=day)
        events = []
        if self.load() != old_load:
            self._rescale(old_load)
            factor, label = game.bmi_tier(self.bmi())
            events.append(Event("load", {
                "up": factor > old_load.weight_factor, "factor": factor, "label": label,
                "old_label": old_label, "bmi": round(self.bmi(), 1),
            }))
        self._save()
        return events

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
        return program.session(self.program_state()["session"], self.program_factor(program)) if program else ()

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
        streak = self.active_streak()
        gained = game.with_streak(programs.SESSION_XP, streak)
        events = [Event("program_session", {"program": program, "number": number, "xp": gained})]
        if number >= programs.TOTAL_SESSIONS:
            gained = game.with_streak(programs.SESSION_XP + programs.PROGRAM_XP, streak)
            done = self.profile.setdefault("programs_done", [])
            if program.id not in done:
                done.append(program.id)
            self.profile["program"] = None
            events = [Event("program_done", {"program": program, "xp": gained})]
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
        rank_up = game.rank_for(after) != game.rank_for(before)
        unlocked = [
            b for b in game.quest_branches(game.rank_for(after), self.goals(), self.focus())
            if b not in game.quest_branches(game.rank_for(before), self.goals(), self.focus())
        ]
        p["unspent_points"] = p.get("unspent_points", 0) + (after - before)
        if rank_up:
            # направление действует до следующего ранга — теперь его нужно выбрать заново
            p.update(focus=None, focus_pending=True)
        return [Event("level", {
            "level": after,
            "points": after - before,
            "rank": game.rank_for(after),
            "rank_up": rank_up,
            "unlocked": unlocked,
        })]

    def ensure_daily_quest(self):
        if not self.profile:
            return
        day = game.today()
        rank, goals, focus = self.rank(), self.goals(), self.focus()
        changed = self._migrate_steps()
        if self.applied_load() != self.load():
            # профиль создан до учёта веса или вес меняли вне замера — подгоняем нормы
            self._rescale(self.applied_load())
            changed = True
        if self.profile.get("quest_branches_day") != day:
            self.profile.update(
                quest_branches=[b.name for b in game.quest_branches(rank, goals, focus)],
                quest_branches_day=day,
            )
            changed = True
        for name, item in self.progress.items():
            if item["quest_day"] != day:
                item.update(quest_day=day, quest_step=item["step"], quest_target=item["target"],
                            quest_sets=game.quest_sets(rank, Branch[name], goals, focus), quest_stage=item.get("stage"))
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
        return game.quest_branches(self.rank(), self.goals(), self.focus()) if p else []

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
                sets=pr["quest_sets"] if fresh else game.quest_sets(self.rank(), branch, self.goals(), self.focus()),
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

    def active_streak(self) -> int:
        """Серия, которая сейчас даёт бонус: если вчера и сегодня квест не закрыт — серия прервана."""
        p = self.profile
        if not p or p["last_completed_day"] < game.today() - 1:
            return 0
        return p["streak"]

    def streak_bonus(self) -> int:
        return game.streak_bonus(self.active_streak())

    def today_done(self) -> bool:
        return bool(self.profile) and self.profile["last_completed_day"] == game.today()

    def _quest_stage(self, pr: dict, step) -> int:
        """Этап сегодняшней нормы — если он известен и совпадает с нормой (иначе XP по общей шкале)."""
        stage = pr.get("quest_stage")
        if stage is None or game.target_at(step, stage, self.load()) != pr["quest_target"]:
            return None
        return stage

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
        xp = game.with_streak(game.xp_for_set(step, value, self.load(), self._quest_stage(pr, step)),
                              self.active_streak())
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
            sex = self.load()
            stage = pr.get("stage", game.stage_of(step, pr["target"], sex))
            # ступень пройдена, когда пройдены все этапы — одинаково для всех, даже если
            # из-за округления норма девушки дошла до цели раньше последнего этапа
            if stage >= game.stage_count(step) and pr["target"] >= game.goal_for(step, sex):
                nxt = game.next_step(step, self.equipment())
                if nxt:
                    pr.update(step=nxt.id, target=game.start_target(nxt, sex), stage=0)
                    events.append(Event("skill", {"step": nxt}))
            else:
                # этап растёт на 1 у всех; норма считается из этапа — у девушек шаги меньше
                stage += 1
                pr.update(stage=stage, target=max(pr["target"], game.target_at(step, stage, sex)))

        gained = xp
        if self.quest_done() and p["last_completed_day"] != day:
            streak = p["streak"] + 1 if p["last_completed_day"] == day - 1 else 1
            before_pct = game.streak_bonus(streak - 1)
            p.update(streak=streak, best_streak=max(p["best_streak"], streak), last_completed_day=day)
            bonus = game.with_streak(game.QUEST_BONUS, streak)
            gained += bonus
            events.append(Event("quest", {
                "bonus": bonus, "streak": streak, "pct": game.streak_bonus(streak),
                "new_tier": game.streak_bonus(streak) > before_pct,
            }))
        events += self._add_xp(gained)
        self._save()
        return events

    def stats(self) -> dict:
        result = {}
        for stat in game.Stat:
            xp = sum(pr["xp"] for name, pr in self.progress.items() if Branch[name].stat is stat)
            result[stat] = game.stat_value(xp) + self.stat_points()[stat]
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
