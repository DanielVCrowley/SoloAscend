"""Видео с техникой упражнений — открытые ролики YouTube.

Сами видео в приложение не входят. На телефоне они проигрываются официальным встроенным
плеером YouTube (embed), на компьютере — открываются в YouTube по нажатию.
Каждая ссылка проверена: ролик существует и автор разрешил встраивание.
Файл сгенерирован скриптом подбора; правки — в словаре VIDEOS.
"""
from dataclasses import dataclass
from urllib.parse import urlencode

# Адрес-«источник» страницы плеера. YouTube требует Referer у встроенного плеера
# (без него — «Ошибка 153»), поэтому HTML грузится с базовым https-адресом.
# Домен .example зарезервирован стандартом и никуда не ведёт — запросы на него не уходят.
PLAYER_ORIGIN = "https://ascend.example"

# Переходы внутри плеера на сам сайт YouTube блокируются — для этого есть «Открыть в YouTube».
BLOCKED_LINKS = [
    "https://www.youtube.com/watch", "https://youtube.com/watch", "https://m.youtube.com",
    "https://www.youtube.com/@", "https://www.youtube.com/channel", "https://www.youtube.com/shorts",
    "https://youtu.be", "intent:", "vnd.youtube:",
]


@dataclass(frozen=True)
class Video:
    id: str
    title: str
    channel: str
    length: str = ""

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.id}"

    @property
    def thumb(self) -> str:
        return f"https://i.ytimg.com/vi/{self.id}/mqdefault.jpg"

    def player_html(self, autoplay=True, muted=True) -> str:
        """Страница со встроенным плеером YouTube: без звука сам стартует (так разрешает Android),
        крутится по кругу. Звук включается касанием плеера."""
        params = urlencode({
            "autoplay": int(autoplay), "mute": int(muted), "playsinline": 1,
            "loop": 1, "playlist": self.id, "rel": 0, "controls": 1,
            "origin": PLAYER_ORIGIN,
        })
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,maximum-scale=1'>"
            "<style>html,body{margin:0;padding:0;height:100%;background:#000;overflow:hidden}"
            "iframe{position:absolute;inset:0;width:100%;height:100%;border:0}</style></head><body>"
            f"<iframe src='https://www.youtube.com/embed/{self.id}?{params}' "
            "allow='autoplay; encrypted-media; picture-in-picture; fullscreen' allowfullscreen "
            "referrerpolicy='strict-origin-when-cross-origin'></iframe></body></html>"
        )


V = Video

# Ключи: "step:<id ступени>", "move:<упражнение разминки/заминки>", "drill:<упражнение программы>".
VIDEOS = {
    "step:cardio_burpee": V("egmD0-o9MME", "Берпи: техника выполнения [Спортивный Бро]", "Спортивный Бро", "0:57"),
    "step:cardio_burpee_step": V("Zeyqs8pXwXo", "Берпи без отжимания и прыжка", "Force Element", "0:24"),
    "step:cardio_burpee_tuck": V("WCHTrcsE6N4", "Берпи с прыжком (колени к груди)", "Евгений Владимирович", "0:20"),
    "step:cardio_climbers": V("Z46-PmWupF8", "Упражнение «скалолаз»: правила выполнения и основные ошибки", "Утро в Петербурге", "2:26"),
    "step:cardio_high_knees": V("FZPx2S-Kc94", "Упражнение бег на месте с высоким подъем колен. Кардио тренировка дома", "BodySportal.com", "1:20"),
    "step:cardio_jacks": V("zVJ8GZS22v4", "Джампинг Джек (Jumping Jack) - как делать упражнение", "iq-body.ru", "1:04"),
    "step:cardio_march": V("Y1khBnXE83Q", "Шаги на месте с высоким подъемом коленей: упражнение для разминки", "Viktoria Monchenko", "0:34"),
    "step:cardio_skaters": V("wtnGgvfDOzU", "Боковые прыжки с ноги на ногу/ «Конькобежец»| Skater jumps", "АЛЕКСАНДР ШУМСКИЙ", "0:19"),
    "step:core_dragon_neg": V("fo2tvqR4Gf8", "Упражнение \"Флаг Дракона\". Научись за 5 мин.", "KungFox", "4:29"),
    "step:core_hang_knee": V("fRGNHDuStr0", "Подъем коленей в висе | Александр Галдович | База упражнений", "AG Fit", "2:15"),
    "step:core_hang_leg": V("dVKJUa2gyww", "ПОДЪЕМЫ НОГ В ВИСЕ - разбор техники | Джефф Кавальер", "SMART TRAINING Channel", "4:19"),
    "step:core_hollow": V("0yPin8hSc8o", "Упражнение «Лодочка» | Техника выполнения для укрепления мышц кора", "FIT.nl", "0:18"),
    "step:core_knee_raise": V("Kv6VAc3CEjc", "05 Подъем коленей лежа", "Vasiliy Tyorkin", "0:17"),
    "step:core_leg_raise": V("bKXVFerLlUc", "Подъём ног лёжа: техника выполнения", "ТВОЙ ТРЕНЕР", "3:30"),
    "step:core_lsit": V("HxDP7SqggpI", "От НУЛЯ до L-SIT за 8 шагов | Упражнения и прогрессия для L-Sit дома", "Vitality", "8:04"),
    "step:core_plank": V("0JtBS11DGDk", "Как Правильно Держать Планку. Это Важно Знать!", "Юрий Харламов", "1:46"),
    "step:core_side_plank": V("q4hzrrvIFtk", "Боковая планка. Техника выполнения.", "Олександр Попенко", "0:50"),
    "step:core_tuck_lsit": V("pYjp3VdOn8Q", "L SIT Tutorial | Как научиться держать уголок", "DENYFLY", "3:15"),
    "step:legs_box_pistol": V("v-e05_n-sV0", "Pistol squat to bench", "ashleybordenfitness", "0:21"),
    "step:legs_bulgarian": V("6fOOCDSV04k", "Болгарские выпады. Техника выполнения", "Ilya Generalov", "0:58"),
    "step:legs_chair": V("APSedQvqhdA", "01-01-01 Приседание на стул", "Алексей Самойленко", "0:53"),
    "step:legs_goblet": V("5HlHpBGSvsU", "Приседания гоблет с гирей: техника выполнения [Спортивный Бро]", "Спортивный Бро", "1:07"),
    "step:legs_lunge": V("EZO6TbxsYTA", "Выпады назад. Техника.", "Make Fitness", "1:02"),
    "step:legs_pistol": V("NjJtrplzEJI", "Как делать пистолетик?", "SJBody", "1:06"),
    "step:legs_shrimp": V("z9Xi1CUj5fs", "Креветка и Пистолет. Учимся приседать на одной ноге", "FITFILIP", "6:44"),
    "step:legs_squat": V("51xwwaA5BnQ", "Приседания: техника выполнения [Спортивный Бро]", "Спортивный Бро", "1:27"),
    "step:pull_archer": V("cbP5aU201yQ", "Подтягивания «лучник» для начинающих", "The Red Delta Project", "3:54"),
    "step:pull_australian": V("LFoRoQVek4o", "АВСТРАЛИЙСКИЕ ПОДТЯГИВАНИЯ! ГЛАВНАЯ ОШИБКА НОВИЧКА!", "Школа Воркаута", "4:55"),
    "step:pull_band": V("VJWie8iidrQ", "Подтягивания с резинкой / как научиться подтягиваться | База упражнений | Кольцов Алексей", "Pain Buddy App", "2:07"),
    "step:pull_chin": V("bF4T6-Mh0MU", "Подтягивания обратным хватом: техника и нюансы", "ТВОЙ ТРЕНЕР", "3:34"),
    "step:pull_classic": V("K5UVjeNCKmY", "Техника Подтягиваний На Турнике. Делай Правильно!", "Юрий Харламов", "4:54"),
    "step:pull_db_row": V("kRK-mLcUBhw", "Тяга одной гантели в наклоне: техника выполнения", "ТВОЙ ТРЕНЕР", "3:48"),
    "step:pull_hang": V("zRJjCXxxoZk", "Техника строгих подтягиваний Активный вис на перекладине.", "Евгений Райский", "2:21"),
    "step:pull_negative": V("Uyjxz3qyBO4", "Негативные подтягивания", "Smarty Assistant", "0:24"),
    "step:pull_scap": V("XIkPI-_80r4", "Лопаточные подтягивания: правильная активация перед выполнением подтягиваний", "Perform 360", "0:54"),
    "step:pull_wide": V("-VaMVXrq8vw", "Подтягивания широким хватом к груди: техника и нюансы", "ТВОЙ ТРЕНЕР", "3:46"),
    "step:push_archer": V("QrLVew5Gg14", "Как делать отжимания «Лучника» правильно | Техника, ошибки и польза упражнения", "Воркаут заметки", "1:47"),
    "step:push_classic": V("c902b5g8w0A", "Техника Отжиманий От Пола. Делай Правильно!", "Юрий Харламов", "5:52"),
    "step:push_decline": V("jtcsx4ZsmNw", "Как правильно выполнять отжимания с ногами на стуле", "Стас Петренко", "0:30"),
    "step:push_diamond": V("jHUuwMOv5yw", "Как делать алмазные отжимания?", "Александр Крылов", "1:45"),
    "step:push_dips": V("XSmkKGKk-IA", "Техника Отжиманий На Брусьях. Делай Правильно!", "Юрий Харламов", "4:06"),
    "step:push_incline": V("YwrGYpEjFYA", "Отжимания от опоры. Отжимания от лавки. Техника выполнения", "Олександр Попенко", "1:01"),
    "step:push_knee": V("OEtAxzwjHiU", "Отжимания на коленях. Или как научиться отжиматься?", "Ivan Kiselev Coach", "0:43"),
    "step:push_one_arm": V("-0iiRc--5LU", "Научись Отжиматься на Одной Руке за 5 Простых Шагов", "Дикий Лось", "5:23"),
    "step:push_pseudo": V("VJd_q5w-VeY", "Отжимания С Уходом вперед Обучака (Все тонкости техники)", "Vitaly Pavlenko", "3:08"),
    "step:push_wall": V("92H7M1HErHE", "Отжимания от стены", "SOZONOV SERGEY", "2:03"),
    "drill:Баланс без стены": V("xwLdrsGCA4o", "Как научиться Ловить Баланс в Стойке на руках | Гимнастика", "Oleksiy Kononov", "5:22"),
    "drill:Взрывные подтягивания": V("le0sSAKYLc8", "Взрывные подтягивания | Туториал", "KRASKOVSKYFIT", "1:52"),
    "drill:Выкрут (скин зе кэт)": V("mqZDdpFh1gA", "Skin the Cat (bar)", "PowerMonkeyFitness", "0:23"),
    "drill:Выход силой с прыжка": V("bYjEpDf6Xak", "Jumping Bar Muscle-Up", "ZOAR Fitness", "0:22"),
    "drill:Горизонт в группировке": V("K1He1p3hdTI", "ИДЕАЛЬНЫЙ СТАРТ ДЛЯ ИЗУЧЕНИЯ ГОРИЗОНТА!", "Школа Воркаута", "2:35"),
    "drill:Задний вис в группировке": V("LfyGMZh-Bz4", "Tuck Back Lever Hold (Bar)", "PowerMonkeyFitness", "0:25"),
    "drill:Задний вис, ровная спина": V("yMbX8G6mliw", "Advanced Tuck Back Lever", "Granosthenics", "0:34"),
    "drill:Лягушка": V("zwfdymEUqcQ", "Как на самом деле научиться выполнять стойку «лягушка» | Университет калистеники, эпизод 9", "STRIQfit", "4:49"),
    "drill:Лягушка на прямых руках": V("5UnzutdwPBI", "Продвинутая стойка лягушкой за 21 день: тренировки и прогрессии", "9to5strength", "5:23"),
    "drill:Мах в стойку у стены": V("Ppoj0t8l0sk", "КАК ЛЕГКО ВЫЙТИ В СТОЙКУ НА РУКАХ?! Лучший заход в стойку на руках!", "Школа Воркаута", "2:39"),
    "drill:Наклон в упоре (планш-лин)": V("wKV5zVJTYBo", "Как правильно делать плаш-лин (Planche Lean) | Туториал по калистенике для начинающих", "Vitality", "5:30"),
    "drill:Негативный выход силой": V("zVlH3clfXKg", "How to Muscle Up Negative! (Tips) | Tutorial", "Califorged", "0:25"),
    "drill:Негативы из немецкого виса": V("8WFVvUpsqD8", "Bar back lever negatives", "Matt Hinds", "0:38"),
    "drill:Негативы переднего виса": V("atjSq7N_Ilc", "Front Lever - Negative", "Nicolas Sart", "0:16"),
    "drill:Немецкий вис": V("5KaDOUeMY98", "Урок по выполнению German Hang: развитие силы и мобильности плеч на гимнастических кольцах", "GMB Fitness (Praxis)", "2:38"),
    "drill:Отжимания на прямой перекладине": V("NBe4EOH_a1g", "Отжимания в упоре на перекладину или брусья | База упражнений | Кольцов Алексей", "Pain Buddy App", "1:33"),
    "drill:Отрыв ног от стены по очереди": V("GYR2vaQJOhk", "Отрывание ног лицом к стене | Стойка на Руках за 21 день", "Oleksiy Kononov", "1:40"),
    "drill:Пайк-отжимания": V("SCNI4TBFOnA", "Pike отжимания и отжимания уголком | База упражнений | Кольцов Алексей", "Pain Buddy App", "4:41"),
    "drill:Передний вис в группировке": V("BvDrLgH4O4g", "Front lever: 2. Tuck front lever (Передний вис в группировке)", "INSPIRE тренируйся с умом", "0:31"),
    "drill:Передний вис, ровная спина": V("D-dOt8Ey5Ig", "Как перейти от группировки к продвинутому вису в группировке | 5 ключевых упражнений (калистеника)", "Ashton Fitness", "5:35"),
    "drill:Переход на низкой перекладине": V("tlf5wHEPoLc", "ЛУЧШЕЕ упражнение на выход силой на перекладину: переход на нижнюю часть тумбы с перекладиной (бы...", "RXGYMNASTICS", "0:57"),
    "drill:Подтягивания к груди": V("1ZTTTTy4dfc", "Подтягивания строгие до груди | База упражнений | Кольцов Алексей", "Pain Buddy App", "2:11"),
    "drill:Подтягивания к поясу": V("V_PlOBbNotI", "Высокие подтягивания(обучалка)", "A.G.SPORTS", "0:58"),
    "drill:Подъём по стене": V("bOsE92qrxOA", "Wall Walk / Подъём (Ходьба) по стене 2 /", "Михаил Ю Поляков", "2:51"),
    "drill:Подъёмы в группировке": V("Nv5_gjD5VU4", "Как делать подъемы в группировке (Tuck Front Lever Raise) | Тренировка фронтального виса для начи...", "Kace Hollingsworth", "0:50"),
    "drill:Попытка выхода силой": V("iQwHZRXeF8s", "ВЫХОД СИЛОЙ НА 2 РУКИ. ОБУЧАЛКА. Краткий курс.", "Дикий Лось", "4:42"),
    "drill:Растяжка плеч в упоре сзади": V("6wed6WnpXTU", "Растяжка грудной и передней дельты", "IgoryanFit", "0:44"),
    "drill:Свободная стойка — попытки": V("qAtnDpKFtw0", "Как научиться стоять на руках / Обучалка по стойке на руках", "Альбертович Научит", "6:04"),
    "drill:Стойка грудью к стене": V("Gq_FMaOT6Ug", "Стойка на руках у стены 2 способа", "Gym Balance", "1:28"),
    "drill:Супермен": V("HorsNes1uDA", "bodymaster : Упражнение \"Супермен\"", "Bodymaster", "0:56"),
    "drill:Тяга в группировке": V("4DZPaCOfJOI", "Как научиться подтягиваниям в переднем висе с поджатыми ногами — 3 КРУТЫХ совета (калистеника)", "Ashton Fitness", "4:11"),
    "drill:Удержание в верхней точке подтягивания": V("dgg-US3DWFc", "Удержание в верхней точке (подтягивания)", "Евгениус Милявичус", "0:17"),
    "drill:Удержание в пайке": V("IDZQFrXR2X0", "How to do Pike Hold - Shoulder Drill - Handstand Pro", "Handstand Pro", "0:28"),
    "drill:Удержание упора на перекладине": V("NBe4EOH_a1g", "Отжимания в упоре на перекладину или брусья | База упражнений | Кольцов Алексей", "Pain Buddy App", "1:33"),
    "drill:Учебный выход из стойки": V("xfJCis8CFrM", "СТОЙКА НА РУКАХ. КАК НЕ БОЯТЬСЯ ПАДАТЬ!", "Школа Воркаута", "8:29"),
    "move:Бабочка": V("tR1T4N2lsoM", "КАК ОСВОИТЬ БАБОЧКУ В 5 РАЗ БЫСТРЕЕ", "Йога Без Купюр", "0:53"),
    "move:Выпад с поворотом корпуса": V("4jAv_3A2i48", "Выпады с поворотом корпуса", "YAFF", "1:39"),
    "move:Глубокий присед с удержанием": V("Uzbw1YGZRoA", "Приседание, мобильность голеностопа и сгибание позвоночника", "Ассоциация Профессионалов Фитнеса", "3:08"),
    "move:Голубь": V("zjkFoylLXP8", "Поза голубя для «деревянных»", "Йога,гвозди и стойка на руках с…", "1:43"),
    "move:Дыхание лёжа": V("pvsI37gXU64", "Диафрагмальное дыхание лёжа на спине восстанавливаем эмоциональный фон", "Svetlana Medvedeva", "1:17"),
    "move:Кошка-корова": V("g7BCihplOUo", "Как правильно делать упражнение кошка-корова", "DreamBodyClub", "3:22"),
    "move:Круги руками": V("fwOSb3HKfI0", "Круговые движения руками — разминка плеч и суставов", "ourbody.online", "0:44"),
    "move:Мёртвый жук": V("w3d8lKDXUVs", "ЛФК упражнение Мертвый жук. Техника выполнения, кому и зачем делать.", "Andre Power Life", "2:39"),
    "move:Наклон к ногам сидя": V("kKQEuZC3jTU", "Наклон сидят к прямым ногам", "Веселая наука", "3:18"),
    "move:Поза кобры": V("bmZqjobH6Xs", "Поза кобры, это важно знать!", "Nellyfit1", "1:00"),
    "move:Поза ребёнка с вытяжением": V("CpB8h4UkyaY", "Поза ребенка (Баласана) - базовое расслабляющее упражнение. Отлично подходит для отдыха между сетами", "AKOPYAN", "0:20"),
    "move:Присед с вытяжением вверх": V("460x3G_QsXA", "Приседания с подъемом рук", "Viktoria Monchenko", "0:32"),
    "move:Разминка запястий": V("knpBB0rzCSI", "Болят кисти? Делай это! Укрепляем запястья. Упражнения для правильной планки, стойки на руках", "Пётр Морозов тренер-кинезиолог…", "7:25"),
    "move:Растяжка бедра стоя": V("ePsipjoT2-8", "123.РАСТЯЖКА КВАДРИЦЕПСА СТОЯ (вторая). Упражнения На Растяжку Ног Квадрицепса Бедра Берцовой Дома.", "SportCasta", "0:39"),
    "move:Растяжка груди у стены": V("1rgU2ClCBvU", "Растяжка грудных мышц возле стены", "Тренировки для здоровья с…", "1:06"),
    "move:Растяжка трицепса": V("wcZ02c77538", "132. РАСТЯЖКА ТРИЦЕПСА. Упражнения Для Растяжки Трицепса Дельтовидной Большой Круглой Мышц Дома.", "SportCasta", "0:48"),
    "move:Скрутка лёжа": V("ocsvI_Utugs", "Здоровье позвоночника: Поза скручивания лежа (Супта Матсиендрасана) | Позы йоги | Наталья Орбу", "В гармонии с собой", "5:55"),
    "move:Ягодичный мостик": V("Xllwopeekb4", "Ягодичный мостик. Правильная техника выполнения и ошибки", "DreamBodyClub", "2:52"),
}

# Одно видео на несколько упражнений.
ALIASES = {
    "move:Планка": "step:core_plank",
    "drill:Свободная стойка — испытание": "drill:Свободная стойка — попытки",
    "drill:Выкрут с паузой": "drill:Выкрут (скин зе кэт)",
    "drill:Неполный выкрут": "drill:Выкрут (скин зе кэт)",
}


def get(key: str):
    return VIDEOS.get(ALIASES.get(key, key))


def for_step(step_id: str):
    return get(f"step:{step_id}")


def for_move(name: str):
    return get(f"move:{name}")


def for_drill(drill):
    """Упражнение программы: своё видео, иначе — видео ступени, на которую ссылается подсказка."""
    return get(f"drill:{drill.name}") or (for_step(drill.guide) if drill.guide else None)
