# -*- coding: utf-8 -*-
"""Stage 2: translate untranslated + missing strings in strings/strings.json.

Mod file is a single object with aValues = flat [KEY, VALUE, KEY, VALUE, ...].
We translate values of existing keys in-place, and append missing pairs.
"""
import json, io

GAME = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/'
MODFILE = 'D:/Wello/OstranautsVodka/ostranautsRuNss/data/strings/strings.json'
GFILE = GAME + 'strings/strings.json'

# key -> Russian value. English source kept verbatim for placeholders/tags.
TR = {
    # --- AI pathfind (leading space preserved: text is appended after NPC name) ---
    'AI_PATHFIND_FORBIDDENZONE_BLOCK': ' не может найти путь. Возможно, мешает запретная зона.',
    'AI_PATHFIND_GET_SUIT': ' берёт скафандр и шлем перед использованием шлюза.',
    'AI_PATHFIND_NO_AIRLOCK_PERM': ' открытие шлюза запрещено настройками РОСТЕРА.',
    'AI_PATHFIND_NO_DISEMBARK': ' увольнение на берег запрещено настройками РОСТЕРА.',
    'AI_PATHFIND_NO_EVA_GRAV': ' не может выйти в открытый космос при ускорении или в гравитации.',
    'AI_PATHFIND_NO_GENERAL': 'Не удаётся добраться до этого места.',
    'AI_PATHFIND_NO_HELMET': ' не может открыть шлюз без космического шлема.',
    'AI_PATHFIND_NO_SUIT': ' не может открыть шлюз без скафандра.',
    'AI_REL_SWITCH': 'Переключение внимания на ',
    # --- Bounty / wanted list labels ---
    'Bounty_TXT_2': 'Контрабанда запрещённых технологий',
    'Bounty_TXT_3': 'Нападение на силы безопасности',
    'Bounty_TXT_4': 'Разбой на грузовых судах',
    'Bounty_TXT_5': 'Разбой на гражданских кораблях',
    'Bounty_TXT_6': 'Нападение на патрули',
    'Bounty_TXT_7': 'Саботаж корпоративной инфраструктуры',
    'Bounty_TXT_10': 'Множественные обвинения в убийстве',
    'Bounty_TXT_12': 'Торговля на чёрном рынке',
    'Bounty_TXT_14': 'Вооружённое ограбление',
    'Bounty_TXT_15': 'Торговля оружием',
    'Bounty_TXT_16': 'Взлом защищённых сетей',
    'Bounty_TXT_17': 'Угон космического корабля',
    'Bounty_TXT_18': 'Подрывы на станциях',
    'Bounty_TXT_19': 'Уничтожение общественного имущества',
    'Bounty_TXT_20': 'Порча сигнальных маяков',
    # --- GUI jobs / gigs ---
    'GUI_CREW_BAR_PHYSIO_STATUSUNAVAILABLE': 'Статус недоступен',
    'GUI_JOBS_LEDGER_COLLATERAL_PREFIX': 'Залог за подработку: ',
    'GUI_JOBS_MAIN_ERROR_INSUFFICIENTFUNDS': 'Недостаточно средств для оплаты контракта',
    'GUI_JOBS_MAIN_ERROR_INV_FULL': 'Чтобы взять эту подработку, шкафчик должен быть пуст.',
    'GUI_JOBS_MAIN_ERROR_INV_MISSING': 'В шкафчике не хватает следующих предметов:\n',
    'GUI_JOBS_MAIN_ERROR_WRONG_DEST': 'Неверный киоск выдачи.',
    'GUI_JOBS_MAIN_ERROR_WRONG_ORIGIN': 'Неверный киоск получения.',
    'GUI_JOBSPDA_ROW_EMPTY1': '<b>Нет взятых подработок.</b>\n\nНайдите подработки в ближайшем Gig Nexus уже сегодня!\n\n',
    'GUI_JOBSPDA_ROW_EMPTY2': ('<b>Вы — Gig Pro?</b>\n\nГотовы брать и сдавать подработки на ходу? Оформите подписку* на статус ProGig, '
        'чтобы получить инструменты управления подработками прямо у себя на ладони!\n\n'
        '<size=60%>*Предложение действительно в отдельных локациях. Предложения и их составляющие, включая, но не ограничиваясь, '
        'участвующие локации и подходящие подработки, зависят от доступности, пропускной способности сети, закрытия станций и '
        'дополнительных ограничений и исключений, могут быть изменены или отменены без уведомления и не гарантируются. Для полного '
        'доступа к специальным функциям необходимо приобрести действующую подписку Gig Nexus Pro. Профессиональные функции управления '
        'могут быть недоступны для некоторых подработок и в некоторых локациях, включая киоски, не принадлежащие Gig Nexus или не '
        'управляемые им. Не суммируется с другими предложениями, скидками, акциями или с любой предыдущей покупкой. Может потребоваться '
        'минимальный срок подписки и/или отдельные улучшения. Предложения предназначены только для личного использования и не подлежат '
        'передаче или перепродаже.'),
    'GUI_OPTIONS_CONTROL_SETTINGS_NOTE': 'Щёлкните по клавише левой кнопкой, чтобы начать добавление новой комбинации, и правой кнопкой, чтобы удалить последнюю комбинацию.',
    'GUI_OPTIONS_VIDEO_KEY_NOTE': 'Чтобы это работало, пользовательские параметры должны быть правильно оформлены как пары «Ключ Значение», разделённые двоеточием. Например:\n\nKey:Value\nKey2:Value2',
    'GUI_PDA_BUTTON_GIGS': 'Просмотр деталей текущих принятых подработок',
    'GUI_PDA_FERRY_NOTE': 'ПРИМЕЧАНИЕ: политика Pacific Airlines Space Service запрещает подниматься на борт судов PASS пассажирам, недавно участвовавшим в бою.',
    'GUI_PDA_FILES_ERROR': 'ОШИБКА: КПК не найден. Невозможно открыть приложение FILES.',
    # --- Reactor tooltips ---
    'GUI_REACTOR_ALERT_CORELINER': 'Абляционная облицовка ядра между полевыми катушками и кораблём истощается, когда температура реакции слишком высока. Истощённая ОБЛИЦОВКА ЯДРА повышает риск повреждения ядра и близлежащих деталей, возможного расплавления и рентгеновского облучения экипажа.',
    'GUI_REACTOR_ALERT_LASCAP': 'Лазерный конденсатор полностью заряжен и готов к зажиганию',
    'GUI_REACTOR_ALERT_XRAY': 'Обнаружено опасное рентгеновское излучение за пределами ядра реактора (возможно, из-за повреждения абляционной облицовки ядра или самого ядра реактора)',
    'GUI_REACTOR_CAPCHARGE': 'Перед зажиганием конденсатор(ы) должны достичь полного заряда, чтобы успешно активировать лазеры для зажигания топливных гранул',
    'GUI_REACTOR_COREPRESSURE': 'Давление в ядре: перед зажиганием ядро должно быть в вакууме. Предыдущее зажигание или полёт в атмосфере могут заполнить ядро, что потребует ОЧИСТКИ ЯДРА (для которой нужен исправный насос ядра, подключённый к ядру)',
    'GUI_REACTOR_COREPRESSURE_TITLE': 'Давление в ядре: перед зажиганием ядро должно быть в вакууме. Предыдущее зажигание или полёт в атмосфере могут заполнить ядро, что потребует ОЧИСТКИ ЯДРА (для которой нужен исправный насос ядра, подключённый к ядру)',
    'GUI_REACTOR_CORETEMP': 'Высокая температура опасна; низкая температура может остановить реактор',
    'GUI_REACTOR_CRYO': 'Включает/выключает охлаждение, чтобы ядро не перегревалось (требуется исправный криогенный насос, подключённый к ядру, и криогенный резервуар, установленный где-либо на корабле. Износ криогенных насосов снижает эффективность охлаждения)',
    'GUI_REACTOR_CYCLE': 'Увеличьте Цикл, чтобы открыть заднее отверстие двигателя и выпустить реакционную плазму через заднюю полевую катушку в качестве тяги. Более открытый ЦИКЛ увеличивает ускорение тяги (в G) и снижает температуру ядра. (Тяга должна быть переключена в положение «Активно», иначе Цикл ничего не делает.)',
    'GUI_REACTOR_FIELDCOIL_FWD': 'Активирует переднюю полевую катушку: магнитные поля, отделяющие корабль от реакционной плазмы',
    'GUI_REACTOR_FIELDCOIL_REAR': 'Активирует заднюю полевую катушку: магнитные поля, отводящие тепло реакционной плазмы от корабля в виде тяги факельного двигателя (когда ЦИКЛ открыт)',
    'GUI_REACTOR_LASALIGN': 'Включает/выключает юстировку лазера для правильного наведения на топливные гранулы. Необходимо перед зажиганием',
    'GUI_REACTOR_PELLFEED': 'Включает/выключает подачу топливных гранул в ядро. Необходимо перед зажиганием.',
    'GUI_REACTOR_PWRBUS': 'Задаёт отношения реактора с подключёнными аккумуляторами: OFF: реактор не взаимодействует с подключёнными аккумуляторами/nBATT: реактор разряжает подключённые аккумуляторы как стартовую энергию во время зажигания/nCHRG: реактор заряжает подключённые аккумуляторы, пока он работает с исправным подключённым MHD и включённым переключателем MHD',
    'GUI_REACTOR_THRUST': 'Включает/выключает функцию факельного двигателя реактора (позволяя открытому циклу выпускать плазму для создания тяги). Активная тяга запрещена в зонах без кильватерного следа рядом со станцией',
    'GUI_REACTOR_THRUST_ALERT_PROX': 'Корабль слишком близко к станции для активации факельной тяги (в зоне без кильватерного следа)',
    # --- GUI save / trade ---
    'GUI_SAVE_NOT_DOWNLOADED_TITLE': 'ZIP отсутствует локально',
    'GUI_SAVE_NOT_DOWNLOADED_BODY': 'При загрузке игра попытается скачать его из облака',
    'GUI_TRADE_WINDOW_COLUMN_ITEM': 'Предмет (* означает, что предмет экипирован)',
    'GUI_TRADE_ZONELABEL': 'Отправить предметы в зону обмена',
    # --- Misc ---
    'JOB_RECON_TXT1_09': 'по слухам, состоит в романтических отношениях с ведущим игроком в «Брейкаут» команды The Tharsis Timberwolves, Анной «Заморозкой» Гостава.',
    'NAV_BOARDING_LEO': 'Абордаж местных властей!',
    'NAV_LOG_CREW_TRANSFER_IN': ' переведён с ',
    'OBJV_LOW_PRESSURE_DESC': 'Внимание: датчик обнаружил давление ниже безопасного уровня.',
    'OBJV_LOW_PRESSURE_TITLE': 'Предупреждение о низком давлении',
    'TOOLTIP_SOCIAL_TOGGLE': 'Показывает/скрывает подгруппу дополнительных действий.',
    # --- Missing (appended) ---
    'GUI_CONTROLS_LOCK_GLYPHS': 'Принудительно показывать в интерфейсе ввод для:',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcAchievement05': '\n\n<size=85%><color=yellow>Улучшается за счёт успешного выполнения работы и продуктивных задач</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcAltruism05': '\n\n<size=85%><color=yellow>Улучшается, когда ты добр к другим или когда другие недобры к тебе</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcAutonomy05': '\n\n<size=85%><color=yellow>Улучшается, когда ты отстаиваешь свою независимость и находишься в режиме АВТОЗАДАЧИ</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcContact05': '\n\n<size=85%><color=yellow>Улучшается за счёт общения с другими</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcEsteem05': '\n\n<size=85%><color=yellow>Улучшается за счёт впечатляющей или достойной уважения деятельности</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcFamily05': '\n\n<size=85%><color=yellow>Улучшается через ощущение принадлежности рядом с другими</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcIntimacy05': '\n\n<size=85%><color=yellow>Улучшается, когда ты проводишь время наедине с NPC</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcMeaning05': '\n\n<size=85%><color=yellow>Улучшается через переживание красоты и моментов радости и осмысленности</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcPrivacy05': '\n\n<size=85%><color=yellow>Улучшается, когда ты проводишь время вдали от социальных взаимодействий</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcSecurity05': '\n\n<size=85%><color=yellow>Улучшается за счёт избегания опасности, отдыха и сна, владения оружием и успеха в агрессивных действиях</color></size>',
    'GUI_CREW_BAR_PHYSIO_BONUS_DcSelfRespect05': '\n\n<size=85%><color=yellow>Улучшается за счёт заботы о себе и умения постоять за себя</color></size>',
    'GUI_PDA_PASS_REQUEST_DEAD_ETA': 'НЕТ СВЯЗИ',
    'GUI_PDA_SOCIAL_MISSING': 'Отсутствует',
    'TOOLTIP_EMERGENCY_REASON_CO2': 'Аварийное переопределение: высокий уровень CO2',
    'TOOLTIP_EMERGENCY_REASON_FIRE': 'Аварийное переопределение: пожаротушение',
    'TOOLTIP_EMERGENCY_REASON_FIRE_FLEE': 'Аварийное переопределение: бегство от пожара',
    'TOOLTIP_EMERGENCY_REASON_O2': 'Аварийное переопределение: низкий уровень кислорода',
    'TOOLTIP_EMERGENCY_REASON_UNKNOWN': 'Аварийное переопределение: неизвестная чрезвычайная ситуация',
}

g = json.load(open(GFILE, encoding='utf-8-sig'))
mobj = json.load(open(MODFILE, encoding='utf-8'))
gav = g[0]['aValues']
av = mobj[0]['aValues']
gkeys = set(gav[0::2])

# 1) translate existing keys in-place (all occurrences)
existing_keys = set(av[0::2])
applied = 0
for i in range(0, len(av), 2):
    k = av[i]
    if k in TR:
        av[i + 1] = TR[k]
        applied += 1

# 2) append missing pairs (present in game, absent in mod), in game order
appended = 0
for i in range(0, len(gav), 2):
    k = gav[i]
    if k not in existing_keys:
        if k not in TR:
            print('WARNING: missing key with no translation:', k)
            continue
        av.append(k)
        av.append(TR[k])
        appended += 1

json.dump(mobj, io.open(MODFILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('translated existing occurrences:', applied, '| appended missing pairs:', appended)
print('new total pairs:', len(av)//2)
