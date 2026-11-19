from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Equipment(Enum):
    PULL_BAR = "Турник"
    DIP_BARS = "Брусья"
    DUMBBELLS = "Гантели"
    KETTLEBELL = "Гиря"
    BANDS = "Резиновые петли"


class Measure(Enum):
    REPS = "reps"
    SECONDS = "seconds"


class Stat(Enum):
    STRENGTH = "Сила"
    AGILITY = "Ловкость"
    VITALITY = "Выносливость"


class Branch(Enum):
    PUSH = ("Толкающие", Stat.STRENGTH)
    PULL = ("Тяга", Stat.STRENGTH)
    LEGS = ("Ноги", Stat.AGILITY)
    CORE = ("Кор", Stat.VITALITY)
    CARDIO = ("Кардио", Stat.VITALITY)

    @property
    def title(self) -> str:
        return self.value[0]

    @property
    def stat(self) -> Stat:
        return self.value[1]


class Sex(Enum):
    MALE = "male"
    FEMALE = "female"

    @property
    def title(self) -> str:
        return "Мужской" if self is Sex.MALE else "Женский"


# Насколько облегчены нормы для девушек по веткам. Разница в силе верха тела
# заметнее, чем ног и кора, поэтому толкающие и тяга облегчены сильнее.
SEX_FACTORS = {
    Sex.MALE: {Branch.PUSH: 1.0, Branch.PULL: 1.0, Branch.LEGS: 1.0, Branch.CORE: 1.0, Branch.CARDIO: 1.0},
    Sex.FEMALE: {Branch.PUSH: 0.7, Branch.PULL: 0.65, Branch.LEGS: 0.9, Branch.CORE: 0.85, Branch.CARDIO: 0.9},
}

# С какой ступени начинают девушки с опытом (если отличается от общей).
FEMALE_EXPERIENCED_START = {Branch.PUSH: "push_knee"}


# Нагрузка по весу: чем выше ИМТ, тем легче нормы — меньше нагрузка на суставы и сердце.
# (ИМТ от, множитель, название) — по классификации ВОЗ.
BMI_TIERS = [(35, 0.7, "Ожирение II+"), (30, 0.8, "Ожирение I"), (25, 0.9, "Избыточный вес")]


def bmi(weight_kg: float, height_cm: float) -> float:
    meters = height_cm / 100
    return weight_kg / (meters * meters)


def bmi_tier(value: float):
    """(множитель, название) для ИМТ."""
    return next(((f, label) for low, f, label in BMI_TIERS if value >= low), (1.0, "Норма"))


@dataclass(frozen=True)
class Load:
    """Индивидуальная нагрузка: пол и поправка на вес. Эталон — мужчина с нормальным ИМТ."""
    sex: Sex = Sex.MALE
    weight_factor: float = 1.0

    def factor(self, branch: "Branch") -> float:
        return SEX_FACTORS[self.sex][branch] * self.weight_factor


BASE_LOAD = Load()


def as_load(value) -> Load:
    """Функции норм принимают и Load, и просто пол (для совместимости)."""
    if isinstance(value, Load):
        return value
    if isinstance(value, Sex):
        return Load(value)
    return BASE_LOAD


def sex_factor(branch: "Branch", load) -> float:
    """Итоговый множитель нормы для ветки (пол × вес)."""
    return as_load(load).factor(branch)


class Rank(Enum):
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    S = "S"


RANKS = list(Rank)


@dataclass(frozen=True)
class Step:
    id: str
    branch: Branch
    name: str
    measure: Measure
    goal: int
    requires_all: frozenset = field(default_factory=frozenset)
    requires_any: frozenset = field(default_factory=frozenset)
    experienced_start: bool = False
    tip: str = ""
    per_side: bool = False

    def available_with(self, equipment: set) -> bool:
        return all(e in equipment for e in self.requires_all) and (
            not self.requires_any or any(e in equipment for e in self.requires_any)
        )

    @property
    def requirement_text(self) -> str:
        if self.requires_all:
            return " + ".join(e.value for e in self.requires_all)
        return " или ".join(e.value for e in self.requires_any)

    @property
    def is_reps(self) -> bool:
        return self.measure is Measure.REPS

    @property
    def unit(self) -> str:
        return "повторов" if self.is_reps else "секунд"

    @property
    def side_note(self) -> str:
        return " на каждую сторону" if self.per_side else ""

    def fmt(self, value: int) -> str:
        return str(value) if self.is_reps else f"{value} с"


R = Measure.REPS
S = Measure.SECONDS
EQ = Equipment


def _s(id, branch, name, measure, goal, all_=(), any_=(), exp=False, tip="", side=False):
    return Step(id, branch, name, measure, goal, frozenset(all_), frozenset(any_), exp, tip, side)


# Лестницы прогрессий собраны по Recommended Routine (r/bodyweightfitness)
# и Convict Conditioning: от самых лёгких вариантов к навыкам.
STEPS = [
    _s("push_wall", Branch.PUSH, "Отжимания от стены", R, 20,
       tip="Стопы в шаге от стены, тело прямое, грудь касается стены."),
    _s("push_incline", Branch.PUSH, "Отжимания от стола", R, 15,
       tip="Руки на краю устойчивого стола, корпус одной линией, локти под 45°."),
    _s("push_knee", Branch.PUSH, "Отжимания с колен", R, 15,
       tip="Линия колени–плечи прямая, опускайся грудью почти до пола."),
    _s("push_classic", Branch.PUSH, "Классические отжимания", R, 15, exp=True,
       tip="Пресс и ягодицы напряжены, грудь до пола, руки выпрямляй полностью."),
    _s("push_diamond", Branch.PUSH, "Алмазные отжимания", R, 12,
       tip="Ладони вместе под грудью, пальцы образуют ромб, локти вдоль корпуса."),
    _s("push_decline", Branch.PUSH, "Отжимания с ногами на возвышении", R, 12,
       tip="Стопы на стуле или диване, корпус не провисает."),
    _s("push_dips", Branch.PUSH, "Отжимания на брусьях", R, 12, all_=[EQ.DIP_BARS],
       tip="Опускайся, пока плечо не станет параллельно полу, плечи держи внизу."),
    _s("push_pseudo", Branch.PUSH, "Псевдопланш-отжимания", R, 10,
       tip="Ладони у пояса пальцами в стороны или назад, корпус подан вперёд за кисти."),
    _s("push_archer", Branch.PUSH, "Отжимания лучника", R, 8, side=True,
       tip="Широкая постановка рук, вес уходит на одну руку, вторая остаётся прямой."),
    _s("push_one_arm", Branch.PUSH, "Отжимания на одной руке", R, 5, side=True,
       tip="Ноги шире плеч, свободная рука за спиной, корпус не разворачивай."),

    _s("pull_db_row", Branch.PULL, "Тяга гантели или гири в наклоне", R, 15,
       any_=[EQ.DUMBBELLS, EQ.KETTLEBELL], side=True,
       tip="Спина прямая, тяни локоть к поясу, корпус не разворачивай."),
    _s("pull_australian", Branch.PULL, "Австралийские подтягивания", R, 15, exp=True,
       tip="Низкая перекладина или край прочного стола, тело прямое, грудь к опоре."),
    _s("pull_hang", Branch.PULL, "Вис на турнике", S, 45, all_=[EQ.PULL_BAR],
       tip="Хват на ширине плеч, плечи слегка опущены, дыши ровно."),
    _s("pull_scap", Branch.PULL, "Подтягивания лопатками", R, 12, all_=[EQ.PULL_BAR],
       tip="В висе на прямых руках опускай плечи вниз, поднимая тело на пару сантиметров."),
    _s("pull_band", Branch.PULL, "Подтягивания с резиной", R, 10, all_=[EQ.PULL_BAR, EQ.BANDS],
       tip="Резина под коленом или стопой, подбородок выше перекладины."),
    _s("pull_negative", Branch.PULL, "Негативные подтягивания", R, 8, all_=[EQ.PULL_BAR],
       tip="Запрыгни в верхнюю точку и опускайся 4–5 секунд."),
    _s("pull_chin", Branch.PULL, "Подтягивания обратным хватом", R, 10, all_=[EQ.PULL_BAR],
       tip="Ладони к себе на ширине плеч, без раскачки, внизу полностью выпрямляй руки."),
    _s("pull_classic", Branch.PULL, "Подтягивания", R, 12, all_=[EQ.PULL_BAR],
       tip="Прямой хват, подбородок выше перекладины, без рывков ногами."),
    _s("pull_wide", Branch.PULL, "Подтягивания широким хватом", R, 10, all_=[EQ.PULL_BAR],
       tip="Хват в полтора раза шире плеч, тянись грудью к перекладине."),
    _s("pull_archer", Branch.PULL, "Подтягивания лучника", R, 6, all_=[EQ.PULL_BAR], side=True,
       tip="Широкий хват, тянись к одной руке, вторая выпрямляется вдоль перекладины."),

    _s("legs_chair", Branch.LEGS, "Приседания на стул", R, 20,
       tip="Садись на край стула, едва касаясь, и вставай без помощи рук."),
    _s("legs_squat", Branch.LEGS, "Приседания", R, 25,
       tip="Пятки на полу, колени смотрят туда же, куда носки, бедро до параллели."),
    _s("legs_lunge", Branch.LEGS, "Выпады назад", R, 15, exp=True, side=True,
       tip="Шаг назад, заднее колено почти касается пола, корпус вертикально."),
    _s("legs_goblet", Branch.LEGS, "Гоблет-присед", R, 15, any_=[EQ.DUMBBELLS, EQ.KETTLEBELL],
       tip="Вес у груди, внизу локти между коленями, спина прямая."),
    _s("legs_bulgarian", Branch.LEGS, "Болгарские сплит-приседания", R, 12, side=True,
       tip="Задняя стопа на стуле, опускайся вертикально, колено не заваливай внутрь."),
    _s("legs_shrimp", Branch.LEGS, "Присед-креветка", R, 8, side=True,
       tip="Стоя на одной ноге, держи вторую сзади за стопу и касайся коленом пола."),
    _s("legs_box_pistol", Branch.LEGS, "Пистолет на опору", R, 8, side=True,
       tip="Садись на одной ноге до стула, вторая нога вытянута вперёд."),
    _s("legs_pistol", Branch.LEGS, "Пистолет", R, 6, side=True,
       tip="Полный присед на одной ноге, руки вперёд для баланса, пятка на полу."),

    _s("core_plank", Branch.CORE, "Планка", S, 60,
       tip="Локти под плечами, таз не провисает и не задирается, ягодицы напряжены."),
    _s("core_knee_raise", Branch.CORE, "Подъёмы коленей лёжа", R, 20,
       tip="Поясница прижата к полу, подтягивай колени к груди и медленно опускай."),
    _s("core_side_plank", Branch.CORE, "Боковая планка", S, 45, side=True,
       tip="Локоть под плечом, тело одной линией от головы до стоп."),
    _s("core_leg_raise", Branch.CORE, "Подъёмы прямых ног лёжа", R, 15, exp=True,
       tip="Поясница не отрывается от пола, опускай ноги медленно."),
    _s("core_hollow", Branch.CORE, "Лодочка", S, 45,
       tip="Поясница прижата к полу, лопатки и ноги приподняты, руки за головой."),
    _s("core_hang_knee", Branch.CORE, "Подъёмы коленей в висе", R, 15, all_=[EQ.PULL_BAR],
       tip="Без раскачки, пауза секунду вверху и внизу."),
    _s("core_tuck_lsit", Branch.CORE, "Уголок с поджатыми ногами", S, 20,
       tip="Упор на кулаках или двух стульях, колени у груди, плечи опущены."),
    _s("core_hang_leg", Branch.CORE, "Подъёмы ног в висе", R, 12, all_=[EQ.PULL_BAR],
       tip="Прямые ноги до параллели с полом и выше, без рывка."),
    _s("core_lsit", Branch.CORE, "Уголок", S, 20,
       tip="Прямые ноги параллельно полу, руки прямые, плечи опущены."),
    _s("core_dragon_neg", Branch.CORE, "Негативы флага дракона", R, 6,
       tip="Лёжа на скамье, держись за опору за головой и медленно опускай прямое тело."),

    _s("cardio_march", Branch.CARDIO, "Марш на месте", S, 90,
       tip="Высоко поднимай колени и активно работай руками. Дыши ровно."),
    _s("cardio_jacks", Branch.CARDIO, "Прыжки «звёздочка»", S, 60,
       tip="Прыжком разведи ноги и подними руки над головой, следующим прыжком верни. Приземляйся мягко."),
    _s("cardio_high_knees", Branch.CARDIO, "Бег на месте с высоким подниманием колен", S, 60, exp=True,
       tip="Колени до уровня пояса, на носках, корпус прямой, темп высокий."),
    _s("cardio_climbers", Branch.CARDIO, "Скалолаз", S, 45,
       tip="Упор лёжа, быстро подтягивай колени к груди по очереди. Таз не задирай."),
    _s("cardio_skaters", Branch.CARDIO, "Конькобежец", S, 45,
       tip="Прыжки из стороны в сторону с ноги на ногу, свободная нога уходит за опорную."),
    _s("cardio_burpee_step", Branch.CARDIO, "Бёрпи без прыжка", R, 12,
       tip="Присед → шагами в упор лёжа → шагами обратно → встань. Без прыжков, но в темпе."),
    _s("cardio_burpee", Branch.CARDIO, "Бёрпи", R, 15,
       tip="Присед → прыжком в упор лёжа → отжимание → прыжком к рукам → выпрыгни вверх."),
    _s("cardio_burpee_tuck", Branch.CARDIO, "Бёрпи с прыжком «колени к груди»", R, 10,
       tip="Классический бёрпи, но в прыжке подтягивай колени к груди."),
]

STEP_BY_ID = {s.id: s for s in STEPS}


@dataclass(frozen=True)
class Move:
    """Упражнение разминки или заминки — выполняется по таймеру."""
    name: str
    seconds: int
    kind: str  # "mobility" | "stretch" | "core"
    tip: str


# Разминка: суставная подвижность → динамическая растяжка → активация кора.
# Основа — разминка Recommended Routine (r/bodyweightfitness), адаптирована без инвентаря.
WARMUP = [
    Move("Круги руками", 30, "mobility", "Большие круги прямыми руками: 15 секунд вперёд, 15 назад."),
    Move("Разминка запястий", 30, "mobility", "Встань на четвереньки, покачайся вперёд-назад и по кругу на ладонях."),
    Move("Кошка-корова", 30, "stretch", "На четвереньках поочерёдно округляй и прогибай спину на вдохе и выдохе."),
    Move("Присед с вытяжением вверх", 30, "stretch", "Глубокий присед, затем встань и потянись руками к потолку."),
    Move("Выпад с поворотом корпуса", 40, "stretch", "Шаг вперёд в выпад, повернись к передней ноге. Чередуй стороны."),
    Move("Мёртвый жук", 30, "core", "Лёжа на спине, поясница прижата. Опускай противоположные руку и ногу."),
    Move("Ягодичный мостик", 30, "core", "Подними таз до прямой линии колени–плечи, сожми ягодицы наверху."),
    Move("Планка", 20, "core", "Локти под плечами, пресс напряжён, тело одной линией."),
]

# Дополнительная растяжка для цели «Гибкость» — добавляется в конец заминки.
COOLDOWN_FLEX = [
    Move("Бабочка", 40, "stretch", "Сидя, стопы вместе, колени в стороны. Мягко дави локтями на бёдра, спина прямая."),
    Move("Голубь", 40, "stretch", "Одна нога согнута перед собой, другая вытянута назад. По 20 с на сторону."),
    Move("Глубокий присед с удержанием", 40, "mobility", "Пятки на полу, локти распирают колени, грудь вверх."),
    Move("Скрутка лёжа", 40, "stretch", "Лёжа на спине, опусти согнутые колени в сторону, плечи на полу. По 20 с."),
]

# Заминка: статическая растяжка мышц, которые работали в квесте, и спокойное дыхание.
COOLDOWN = [
    Move("Растяжка груди у стены", 40, "stretch", "Предплечье на стене, мягко поворачивай корпус в сторону. По 20 с на руку."),
    Move("Поза ребёнка с вытяжением", 40, "stretch", "Таз к пяткам, руки вытянуты вперёд, тянись спиной и подмышками."),
    Move("Растяжка трицепса", 40, "stretch", "Локоть за голову, второй рукой мягко дави на него. По 20 с на руку."),
    Move("Растяжка бедра стоя", 40, "stretch", "Держи стопу у ягодицы, колени вместе, таз подай вперёд. По 20 с."),
    Move("Наклон к ногам сидя", 40, "stretch", "Ноги прямые, тянись грудью к коленям, спина длинная."),
    Move("Поза кобры", 30, "core", "Лёжа на животе, выпрями руки, раскрой грудь, плечи вниз."),
    Move("Дыхание лёжа", 30, "core", "Ладонь на животе, медленный вдох носом на 4 счёта, выдох на 6."),
]

COOLDOWN_BONUS = 15

# Бонус к опыту за серию дней с выполненным квестом: (от скольких дней, процент).
STREAK_TIERS = [(3, 5), (7, 7), (30, 10), (60, 12)]


def streak_bonus(streak: int) -> int:
    """Процент бонуса к опыту для текущей серии."""
    return max((pct for days, pct in STREAK_TIERS if streak >= days), default=0)


def next_streak_tier(streak: int):
    """Следующая ступень бонуса (дней, процент) или None, если достигнут максимум."""
    return next(((days, pct) for days, pct in STREAK_TIERS if streak < days), None)


def with_streak(xp: int, streak: int) -> int:
    return round(xp * (100 + streak_bonus(streak)) / 100)


QUEST_BONUS = 50
PENALTY_PER_DAY = 30
MAX_PENALTY_DAYS = 3
REST_SECONDS = 60


# С какого ранга ветка входит в ежедневный квест. На ранге E — только отжимания и подтягивания.
QUEST_UNLOCK = {
    Branch.PUSH: Rank.E,
    Branch.PULL: Rank.E,
    Branch.LEGS: Rank.D,
    Branch.CORE: Rank.D,
    Branch.CARDIO: Rank.E,   # но только если в целях есть кардио — см. GoalPlan
}


class Goal(Enum):
    LOSE = ("lose", "Похудение", "Больше кардио, короче отдых")
    MASS = ("mass", "Набор массы", "Больше силовых подходов, длиннее отдых")
    DEFINE = ("define", "Рельеф", "Кардио и больше работы на кор")
    ENDURANCE = ("endurance", "Выносливость", "Кардио и короткий отдых")
    FLEX = ("flex", "Гибкость", "Расширенная растяжка в заминке")

    @property
    def key(self) -> str:
        return self.value[0]

    @property
    def title(self) -> str:
        return self.value[1]

    @property
    def hint(self) -> str:
        return self.value[2]

    @staticmethod
    def from_key(key: str):
        return next((g for g in Goal if g.key == key), None)


@dataclass(frozen=True)
class GoalPlan:
    """Как цели меняют тренировку."""
    cardio: bool
    extra_sets: dict
    rest: int
    flex: bool

    @property
    def summary(self) -> list:
        lines = []
        if self.cardio:
            lines.append("Кардио в каждом ежедневном квесте")
        strength = [b for b in (Branch.PUSH, Branch.PULL, Branch.LEGS) if self.extra_sets.get(b)]
        if strength:
            lines.append("+1 подход в силовых: " + ", ".join(b.title.lower() for b in strength))
        if self.extra_sets.get(Branch.CORE):
            lines.append("+1 подход в коре")
        if self.extra_sets.get(Branch.CARDIO):
            lines.append("+1 подход в кардио")
        lines.append(f"Отдых между подходами — {self.rest} с")
        if self.flex:
            lines.append(f"Расширенная заминка (+{len(COOLDOWN_FLEX)} упражнения на растяжку)")
        return lines


def goal_plan(goals) -> GoalPlan:
    goals = set(goals or [])
    fast = goals & {Goal.LOSE, Goal.DEFINE, Goal.ENDURANCE}
    extra = {}
    if Goal.MASS in goals:
        for b in (Branch.PUSH, Branch.PULL, Branch.LEGS):
            extra[b] = 1
    if Goal.DEFINE in goals:
        extra[Branch.CORE] = 1
    if goals & {Goal.LOSE, Goal.ENDURANCE}:
        extra[Branch.CARDIO] = 1
    if Goal.MASS in goals and fast:
        rest = 60
    elif Goal.MASS in goals:
        rest = 90
    elif fast:
        rest = 45
    else:
        rest = REST_SECONDS
    return GoalPlan(cardio=bool(fast), extra_sets=extra, rest=rest, flex=Goal.FLEX in goals)


def quest_branches(rank: Rank, goals=None) -> list:
    plan = goal_plan(goals)
    return [
        b for b in Branch
        if RANKS.index(rank) >= RANKS.index(QUEST_UNLOCK[b]) and (b is not Branch.CARDIO or plan.cardio)
    ]


def quest_sets(rank: Rank, branch: Branch, goals=None) -> int:
    return sets_for(rank) + goal_plan(goals).extra_sets.get(branch, 0)


def today() -> int:
    return date.today().toordinal()


def full_ladder(branch: Branch) -> list:
    return [s for s in STEPS if s.branch is branch]


def ladder(branch: Branch, equipment: set) -> list:
    return [s for s in full_ladder(branch) if s.available_with(equipment)]


def tier(step: Step) -> int:
    return full_ladder(step.branch).index(step)


def start_step(branch: Branch, equipment: set, experienced: bool, sex: Sex = Sex.MALE) -> Step:
    steps = ladder(branch, equipment)
    if experienced:
        override = FEMALE_EXPERIENCED_START.get(branch) if as_load(sex).sex is Sex.FEMALE else None
        if override and STEP_BY_ID[override] in steps:
            return STEP_BY_ID[override]
        return next((s for s in steps if s.experienced_start), steps[0])
    return steps[0]


def goal_for(step: Step, sex: Sex = Sex.MALE) -> int:
    """Цель ступени с учётом пола: для девушек — облегчённая."""
    f = sex_factor(step.branch, sex)
    if f == 1.0:
        return step.goal
    if step.is_reps:
        return max(3, round(step.goal * f))
    return max(10, 5 * round(step.goal * f / 5))


def next_step(step: Step, equipment: set):
    steps = ladder(step.branch, equipment)
    if step not in steps:
        return None
    i = steps.index(step)
    return steps[i + 1] if i + 1 < len(steps) else None


def start_target(step: Step, sex: Sex = Sex.MALE) -> int:
    """Минимальная норма на новой ступени — около 40% от цели (15 отжиманий → 6)."""
    goal = goal_for(step, sex)
    if step.is_reps:
        return max(3, round(goal * 0.4))
    return max(10, 5 * round(goal * 0.4 / 5))


def target_increment(step: Step) -> int:
    return 1 if step.is_reps else 5


def stage_count(step: Step) -> int:
    """Сколько успешных дней нужно, чтобы дойти от стартовой нормы до цели. Одинаково для всех полов:
    так темп прохождения ступеней и опыт равны, у девушек просто норма растёт меньшими шагами."""
    unit = target_increment(step)
    return max(0, (goal_for(step, Sex.MALE) - start_target(step, Sex.MALE)) // unit)


def target_at(step: Step, stage: int, sex: Sex = Sex.MALE) -> int:
    """Норма на этапе stage (0 — старт, stage_count — цель)."""
    start, goal = start_target(step, sex), goal_for(step, sex)
    n = stage_count(step)
    if n <= 0:
        return goal
    unit = target_increment(step)
    stage = min(max(stage, 0), n)
    return min(goal, start + unit * round((goal - start) / unit * stage / n))


def stage_of(step: Step, target: int, sex: Sex = Sex.MALE) -> int:
    """Этап по норме — для старых сохранений, где этап ещё не хранился."""
    start, goal = start_target(step, sex), goal_for(step, sex)
    n = stage_count(step)
    if goal <= start or n <= 0:
        return n
    return min(n, max(0, round((target - start) / (goal - start) * n)))


def regulator_step(step: Step) -> int:
    return 1 if step.is_reps else 5


def regulator_max(step: Step, target: int, sex: Sex = Sex.MALE) -> int:
    """Верхняя граница регулятора — с запасом выше цели ступени."""
    goal = goal_for(step, sex)
    top = max(goal + goal // 2, target * 2)
    unit = regulator_step(step)
    return -(-top // unit) * unit


def xp_to_next(level: int) -> int:
    return 100 + (level - 1) * 25


@dataclass
class LevelInfo:
    level: int
    current: int
    needed: int

    @property
    def fraction(self) -> float:
        return self.current / self.needed


def level_info(total_xp: int) -> LevelInfo:
    level, rest = 1, total_xp
    while rest >= xp_to_next(level):
        rest -= xp_to_next(level)
        level += 1
    return LevelInfo(level, rest, xp_to_next(level))


def level_start_xp(level: int) -> int:
    return sum(xp_to_next(i) for i in range(1, level))


def rank_for(level: int) -> Rank:
    return RANKS[min((level - 1) // 10, len(RANKS) - 1)]


def sets_for(rank: Rank) -> int:
    return {Rank.E: 3, Rank.D: 3, Rank.C: 4, Rank.B: 4, Rank.A: 5, Rank.S: 5}[rank]


def male_equivalent(step: Step, value: float, sex: Sex, stage: int = None) -> float:
    """Переводит результат девушки в «мужской эквивалент». Если известен этап, норма этапа девушки
    приравнивается к норме того же этапа у мужчины — так за дневную норму XP одинаковый каждый день.
    Без этапа шкала строится от стартовой нормы до цели."""
    if sex_factor(step.branch, sex) == 1.0:
        return value
    start_m, goal_m = start_target(step, Sex.MALE), goal_for(step, Sex.MALE)
    start_f, goal_f = start_target(step, sex), goal_for(step, sex)
    slope = goal_m / goal_f if goal_f == start_f else (goal_m - start_m) / (goal_f - start_f)
    if stage is not None:
        base_m, base_f = target_at(step, stage, Sex.MALE), target_at(step, stage, sex)
    else:
        base_m, base_f = (0, 0) if goal_f == start_f else (start_m, start_f)
    return max(0.0, base_m + (value - base_f) * slope)


def xp_for_set(step: Step, value: int, sex: Sex = Sex.MALE, stage: int = None) -> int:
    """XP за подход. Для девушек считается от мужского эквивалента — награда за свою норму одинаковая."""
    value = male_equivalent(step, value, sex, stage)
    base = value if step.is_reps else value / 4
    return max(1, round(base * (1 + tier(step) * 0.25)))


def stat_value(branch_xp: int) -> int:
    return 10 + branch_xp // 40


def kcal(weight_kg: float, sets: int) -> int:
    return round(3.8 * weight_kg * sets * 1.5 / 60)
