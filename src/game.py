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

    @property
    def title(self) -> str:
        return self.value[0]

    @property
    def stat(self) -> Stat:
        return self.value[1]


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
}


def quest_branches(rank: Rank) -> list:
    return [b for b in Branch if RANKS.index(rank) >= RANKS.index(QUEST_UNLOCK[b])]


def today() -> int:
    return date.today().toordinal()


def full_ladder(branch: Branch) -> list:
    return [s for s in STEPS if s.branch is branch]


def ladder(branch: Branch, equipment: set) -> list:
    return [s for s in full_ladder(branch) if s.available_with(equipment)]


def tier(step: Step) -> int:
    return full_ladder(step.branch).index(step)


def start_step(branch: Branch, equipment: set, experienced: bool) -> Step:
    steps = ladder(branch, equipment)
    if experienced:
        return next((s for s in steps if s.experienced_start), steps[0])
    return steps[0]


def next_step(step: Step, equipment: set):
    steps = ladder(step.branch, equipment)
    if step not in steps:
        return None
    i = steps.index(step)
    return steps[i + 1] if i + 1 < len(steps) else None


def start_target(step: Step) -> int:
    """Минимальная норма на новой ступени — около 40% от цели (15 отжиманий → 6)."""
    if step.is_reps:
        return max(3, round(step.goal * 0.4))
    return max(10, 5 * round(step.goal * 0.4 / 5))


def target_increment(step: Step) -> int:
    return 1 if step.is_reps else 5


def regulator_step(step: Step) -> int:
    return 1 if step.is_reps else 5


def regulator_max(step: Step, target: int) -> int:
    """Верхняя граница регулятора — с запасом выше цели ступени."""
    top = max(step.goal + step.goal // 2, target * 2)
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


def xp_for_set(step: Step, value: int) -> int:
    base = value if step.is_reps else value / 4
    return max(1, round(base * (1 + tier(step) * 0.25)))


def stat_value(branch_xp: int) -> int:
    return 10 + branch_xp // 40


def kcal(weight_kg: float, sets: int) -> int:
    return round(3.8 * weight_kg * sets * 1.5 / 60)
