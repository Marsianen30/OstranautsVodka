import json, re, os, sys
from collections import defaultdict

# Load model
print("Loading model...", flush=True)
from transformers import MarianMTModel, MarianTokenizer
model_name = "Helsinki-NLP/opus-mt-en-ru"
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)
print("Model loaded", flush=True)

# Config
PROTECT_ACRO = ["CCRE","OKLG","VENC","VNCA","GalCon","BCER","BCRS","GF","LA","LEO","AyoSec"]

# Manual dictionary for worst translations
MANUAL_DICT = {
    "???": "???",
    "Enemy Spawn Blocked": "Блокировка появления врагов",
    "Due Pirate Spawn": "Ожидается пират",
    "Due Faction Spawn": "Ожидается корабль фракции",
    "Pristine": "Нетронутый",
    "Attempting to fight fire": "Пытается потушить пожар",
    "CCRE Arrest Warning Count": "Предупреждений об аресте CCRE",
    "CCRE Arrest Warrant": "Ордер на арест CCRE",
    "CCRE Public Enemy": "Враг общества CCRE",
    "CCRE Trespass Warrant": "Ордер за вторжение CCRE",
    "CCRE Arrest Warrant for Stolen Ship": "Ордер CCRE за угон корабля",
    "CCRE Arrest Warrant for Failure to Undock": "Ордер CCRE за отказ от расстыковки",
    "Used AntiHypo-V": "Применён АнтиГипо-В",
    "AntiHypo-V Course Complete": "Курс АнтиГипо-В завершён",
    "AntiHypo-V Dose Count": "Доз АнтиГипо-В",
    "G-LOC": "G-LOC",
    "Greeted by a Friend": "Приветствие от друга",
    "Greeted a friend recently": "Недавно поприветствовал друга",
    "Greeted by a Crewmate": "Приветствие от члена экипажа",
    "Greeted Captain Recently": "Недавно поприветствовал капитана",
    "Greeted by an Enemy": "Приветствие от врага",
    "Told off an Enemy": "Отшил врага",
    "Kissed a lover recently": "Недавно поцеловал возлюбленного",
    "Kissed": "Поцелован",
    "Installed Recently": "Недавно установлено",
    "Uninstalled Recently": "Недавно демонтировано",
    "Repaired Recently": "Недавно отремонтировано",
    "Restored Recently": "Недавно восстановлено",
    "Dismantled Recently": "Недавно разобрано",
    "Patched Recently": "Недавно залатано",
    "Bashed Recently": "Недавно разбито",
    "Attacked Recently": "Недавно атаковано",
    "Admired Recently": "Недавно любовался",
    "Studied Recently": "Недавно изучал",
    "Watched News Recently": "Недавно смотрел новости",
    "Watched Drama Recently": "Недавно смотрел драму",
    "Slept Recently": "Недавно спал",
    "Ate Recently": "Недавно ел",
    "Ate Well Recently": "Недавно хорошо поел",
    "Drank Recently": "Недавно пил",
    "Drank Caffeine Recently": "Недавно пил кофеин",
    "Drank Alcohol Recently": "Недавно пил алкоголь",
    "Exercised Recently": "Недавно тренировался",
    "Played Game Recently": "Недавно играл",
    "Anti-HypoV Dose: 1": "Доза АнтиГипо-В: 1",
    "Anti-HypoV Doses: 2": "Доз АнтиГипо-В: 2",
    "Anti-HypoV Doses: 3": "Доз АнтиГипо-В: 3",
    "Anti-HypoV Doses: 4": "Доз АнтиГипо-В: 4",
    "Anti-HypoV Doses: 5": "Доз АнтиГипо-В: 5",
    "Anti-HypoV Doses: 6": "Доз АнтиГипо-В: 6",
    "Malaise": "Недомогание",
    "Mild Hypercapnia": "Лёгкая гиперкапния",
    "Moderate Hypercapnia": "Умеренная гиперкапния",
    "Advanced Hypercapnia": "Прогрессирующая гиперкапния",
    "Severe Hypercapnia": "Тяжёлая гиперкапния",
    "Critical Hypercapnia": "Критическая гиперкапния",
    "Lethal Hypercapnia": "Смертельная гиперкапния",
    "Asphyxiated by Hypercapnia": "Удушье от гиперкапнии",
    "Stinging Throat and Eyes": "Жжение в горле и глазах",
    "Burning Throat and Eyes": "Жжение в горле и глазах",
    "Lethal Smoke Inhalation": "Смертельное отравление дымом",
    "Fire Chem: Empty": "Огнетушитель: пуст",
    "Fire Chem: Low": "Огнетушитель: мало",
    "Fire Chem: Medium": "Огнетушитель: половина",
    "Fire Chem: Full": "Огнетушитель: полон",
    "Norm CO": "Норма CO",
    "Norm Smoke": "Норма дыма",
    "NO DOCKING FACILITIES": "НЕТ СТЫКОВОЧНЫХ СООРУЖЕНИЙ",
    "Piracy": "Пиратство",
    "Multiple accounts of murder": "Множественные убийства",
    "Fraud": "Мошенничество",
    "Black market trading": "Торговля на чёрном рынке",
    "Extortion": "Вымогательство",
    "Armed robbery": "Вооружённое ограбление",
    "Weapons trafficking": "Торговля оружием",
    "Hacking secure networks": "Взлом защищённых сетей",
    "Spaceship theft": "Угон космического корабля",
    "Station bombings": "Взрывы на станциях",
    "Destruction of public property": "Уничтожение общественного имущества",
    "Tampering with signal beacons": "Повреждение сигнальных маяков",
    "Smuggling restricted tech": "Контрабанда запрещённых технологий",
    "Assaulting security forces": "Нападение на силы безопасности",
    "Raiding cargo freighters": "Налёты на грузовые суда",
    "Raiding civilian ships": "Налёты на гражданские суда",
    "Attacking patrols": "Нападение на патрули",
    "Sabotage of corporate infrastructure": "Саботаж корпоративной инфраструктуры",
    "Espionage": "Шпионаж",
    "Murder": "Убийство",
    "Cannot reach that location.": "Невозможно добраться до этого места.",
    "cannot open airlock without space suit.": "невозможно открыть шлюз без скафандра.",
    "cannot open airlock without space helmet.": "невозможно открыть шлюз без шлема.",
    "airlock opening denied, per ROSTER permissions.": "отказ в открытии шлюза согласно правам реестра.",
    "shore leave denied, per ROSTER permissions.": "увольнение на берег запрещено согласно правам реестра.",
    "cannot EVA to this point while accelerating/in gravity.": "невозможно выполнить ВКД до этой точки во время ускорения/в гравитации.",
    "getting a space suit and helmet before using airlock.": "надевает скафандр и шлем перед использованием шлюза.",
    "could not find a path. Forbidden Zone might be in the way.": "не удалось найти путь. Возможно, мешает запретная зона.",
    "Switching attention to": "Переключает внимание на",
    ".": ".",
    "Done": "Готово",
    "OK": "ОК",
    "Set Dial": "Установить диск",
    "AUTOPAUSE": "АВТОПАУЗА",
    "AUTOTASK": "АВТОЗАДАЧА",
    "Status is not available": "Статус недоступен",
    "Unknown": "Неизвестно",
    "SHIFT": "СМЕНА",
    "CREW": "ЭКИПАЖ",
    "STATS": "СТАТЫ",
    "Pay Selected Payees": "Оплатить выбранных получателей",
    "Amount": "Сумма",
    "Date": "Дата",
    "Paid": "Оплачено",
    "Payee": "Получатель",
    "Payor": "Плательщик",
    "Description": "Описание",
    "Reported in $USD": "Указано в $USD",
    "Shift": "Смена",
    "End-of-Shift Cash Reserves": "Денежный резерв на конец смены",
    "Gross Income": "Валовый доход",
    "Net Profit": "Чистая прибыль",
    "Selected Payee Balance": "Баланс выбранного получателя",
    "Total Expenses": "Общие расходы",
    "Income": "Доход",
    "Operating Expenses": "Операционные расходы",
    "Game Speed Speed": "Скорость игры",
    "Undo Trash...": "Отменить удаление...",
    "Take Gig": "Взять халтуру",
    "My Gigs": "Мои халтуры",
    "Turn-In": "Сдать",
    "Collateral for Gig:": "Залог за халтуру:",
    "Gig Nexus, LLC": "Gig Nexus, LLC",
    "CH4": "CH4",
    "CO": "CO",
    "CO2": "CO2",
    "H2SO4": "H2SO4",
    "Gas": "Газ",
    "N2": "N2",
    "NH3": "NH3",
    "O2": "O2",
    "Smoke": "Дым",
    "Thust Type": "Тип тяги",
    "ACCESSIBILITY SETTINGS": "НАСТРОЙКИ ДОСТУПНОСТИ",
    "Assets": "Ресурсы",
    "AUDIO": "ЗВУК",
    "AUDIO SETTINGS": "НАСТРОЙКИ ЗВУКА",
    "EFFECTS": "ЭФФЕКТЫ",
    "MASTER": "ОБЩИЙ",
    "MUSIC": "МУЗЫКА",
    "AUTOSAVE INTERVAL": "ИНТЕРВАЛ АВТОСОХРАНЕНИЯ",
    "MAX AUTOSAVES COUNT": "МАКС. КОЛ-ВО АВТОСОХРАНЕНИЙ",
    "AUTOSAVE SETTINGS": "НАСТРОЙКИ АВТОСОХРАНЕНИЯ",
    "BACKGROUND ROTATION": "ВРАЩЕНИЕ ФОНА",
    "Control Settings": "Настройки управления",
    "CONTROLS": "УПРАВЛЕНИЕ",
    "DATE AND TIME FORMAT SETTINGS": "ФОРМАТ ДАТЫ И ВРЕМЕНИ",
    "FILES": "ФАЙЛЫ",
    "FLICKER AMOUNT": "МЕРЦАНИЕ",
    "GENERAL": "ОБЩИЕ",
    "GENERAL SETTINGS": "ОБЩИЕ НАСТРОЙКИ",
    "INTERFACE SETTINGS": "НАСТРОЙКИ ИНТЕРФЕЙСА",
    "Manuals": "Руководства",
    "Mods": "Моды",
    "OPEN FOLDERS": "ОТКРЫТЬ ПАПКИ",
    "Reset Settings": "Сбросить настройки",
    "Save": "Сохранить",
    "SAVE ON CLOSE": "СОХРАНЕНИЕ ПРИ ВЫХОДЕ",
    "Saves": "Сохранения",
    "Screenshots": "Скриншоты",
    "Settings": "Настройки",
    "TEMPERATURE UNITS": "ЕДИНИЦЫ ТЕМПЕРАТУРЫ",
    "VIDEO": "ВИДЕО",
    "Ambient Occlusion": "Фоновое затенение",
    "Custom Parameters": "Пользовательские параметры",
    "FPS LIMIT": "ЛИМИТ FPS",
    "VIDEO SETTINGS": "НАСТРОЙКИ ВИДЕО",
    "Key": "Ключ",
    "Line of Sight": "Прямая видимость",
    "Parallax": "Параллакс",
    "RESOLUTION": "РАЗРЕШЕНИЕ",
    "Screen Shake": "Тряска экрана",
    "Turbo": "Турбо",
    "FULLSCREEN": "ПОЛНЫЙ ЭКРАН",
    "WINDOW STYLE": "РЕЖИМ ОКНА",
    "WINDOWED": "ОКНО",
    "In": "Вход",
    "Out": "Выход",
    "Install App": "Установить приложение",
    "DamageViz Toggle": "Перекл. Повреждений",
    "Hide PDA": "Скрыть КПК",
    "PASS Ferry App": "Паром PASS",
    "Datafiles App": "Файлы данных",
    "View your current accepted gig details": "Посмотреть детали текущих халтур",
    "Gigs App": "Халтуры",
    "Goals App": "Цели",
    "Inventory": "Инвентарь",
    "Nav Link App": "Навигационная связь",
    "Nav Map App": "Карта",
    "Notes App": "Заметки",
    "Orders App": "Приказы",
    "PowerViz Toggle": "Перекл. Энергии",
    "Roster App": "Реестр",
    "Socials App": "Соцсеть",
    "Tasks App": "Задачи",
    "Timer App": "Таймер",
    "Vizor App": "Визор",
    "Zones App": "Зоны",
    "n/a": "н/д",
    "January": "Январь",
    "February": "Февраль",
    "Lower Left Arm": "Нижняя левая рука",
    "Lower Right Arm": "Нижняя правая рука",
    "Upper Left Arm": "Верхняя левая рука",
    "Upper Right Arm": "Верхняя правая рука",
    "Back": "Спина",
    "Body": "Тело",
    "Drag": "Перетаскивание",
    "Left Foot": "Левая стопа",
    "Right Foot": "Правая стопа",
    "Left Hand (Worn)": "Левая рука (надето)",
    "Right Hand (Worn)": "Правая рука (надето)",
    "Left Hand (Hold)": "Левая рука (держать)",
    "Right Hand (Hold)": "Правая рука (держать)",
    "Glasses": "Очки",
    "Head (Inner)": "Голова (внутр.)",
    "Head (Middle)": "Голова (сред.)",
    "Head (Outer)": "Голова (внеш.)",
    "Lower Left Leg": "Нижняя левая нога",
    "Lower Right Leg": "Нижняя правая нога",
    "Upper Left Leg": "Верхняя левая нога",
    "Upper Right Leg": "Верхняя правая нога",
    "Pants (Inner)": "Штаны (внутр.)",
    "Pants (Middle)": "Штаны (сред.)",
    "Pants (Outer)": "Штаны (внеш.)",
    "Pledges": "Обязательства",
    "Left Breast Pocket": "Левый нагрудный карман",
    "Right Breast Pocket": "Правый нагрудный карман",
    "Clip Point": "Точка крепления",
    "Left Coat Pocket": "Левый карман пальто",
    "Right Coat Pocket": "Правый карман пальто",
    "EVA Battery Compartment": "Отсек батареи ВКД",
    "EVA CO2 Filter Compartment": "Отсек фильтра CO2 ВКД",
    "EVA O2 Bottle Compartment": "Отсек баллона O2 ВКД",
    "Left Hip Pocket": "Левый бедренный карман",
    "Right Hip Pocket": "Правый бедренный карман",
    "Hoodie Pocket": "Карман толстовки",
    "Small Pouch": "Маленький подсумок",
    "Cargo Pocket": "Грузовой карман",
    "Movement Unit": "Ходовой модуль",
    "Shirt (Inner)": "Рубашка (внутр.)",
    "Shirt (Middle)": "Рубашка (сред.)",
    "Shirt (Outer)": "Рубашка (внеш.)",
    "Left Shoe": "Левый ботинок",
    "Right Shoe": "Правый ботинок",
    "Data": "Данные",
    "PDA Carts": "Картриджи КПК",
    "Social": "Социальное",
    "Trash": "Мусор",
    "Wrist": "Запястье",
    "Trials": "Испытания",
    "Venus Bronze League": "Бронзовая лига Венеры",
    "Venus Silver League": "Серебряная лига Венеры",
    "Venus Gold League": "Золотая лига Венеры",
    "Grande Prêmio do Encantado": "Гран-при Энкантадо",
    "Track Type: Circuit": "Тип трассы: Круг",
    "Track Type: Orientation": "Тип трассы: Ориентация",
    "Track Type: Point to Point": "Тип трассы: Из точки в точку",
    "Fluid": "Поток",
    "Ladder": "Лестница",
    "Cue": "Сигнал",
    "The Rising Star": "Восходящая звезда",
    "O-Ring": "О-Кольцо",
    # conditions
    "false": "ложь",
    "Neutral": "Нейтрально",
    "0": "0",
    "1": "1",
    "2": "2",
    "XXX": "XXX",
    "Good": "Хорошо",
    "Goodish": "Неплохо",
    # more
    "Equip helmet": "Надеть шлем",
    "Equip suit and helmet": "Надеть скафандр и шлем",
    "Equip suit": "Надеть скафандр",
    "Survive CO2": "Выжить при CO2",
    "Survive O2": "Выжить при O2",
    "Combat": "Бой",
    "Stand up": "Встать",
    "Combat join": "Вступить в бой",
    "Firefight": "Тушение пожара",
    "MaintenanceTech extinguish": "Техник: тушение",
    "Drone decoy": "Дрон-приманка",
    "Combat Boarding": "Абордаж",
    "Arrest": "Арест",
    "Attack": "Атака",
    "Rob": "Ограбить",
    "MaintenanceTech patch": "Техник: заплатка",
    "Greet Captain": "Приветствовать капитана",
    "Greet Enemy": "Приветствовать врага",
    "Greet Friend": "Приветствовать друга",
    "Greet Lover": "Приветствовать возлюбленного",
    "Free up space": "Освободить место",
    "Eat": "Есть",
    "Drink": "Пить",
    "Crime arrest": "Арест за преступление",
    "MaintenanceTech retrieve": "Техник: извлечение",
    "MaintenanceTech deliver": "Техник: доставка",
    "Report crime": "Сообщить о преступлении",
    "Faction fight": "Бой фракций",
    "Reply": "Ответить",
    "Disembark": "Высадиться",
    "Disembark and undock": "Высадиться и отстыковаться",
    "Undock": "Отстыковаться",
    "MaintenanceTech repair": "Техник: ремонт",
    "MaintenanceTech replace": "Техник: замена",
    "MaintenanceTech rest": "Техник: отдых",
    "MaintenanceTech restore": "Техник: восстановление",
    "Close": "Закрыть",
    "Embark": "Сесть на борт",
    "Follow": "Следовать",
    "Shakedown": "Вымогательство",
    "Stand": "Стоять",
    "Remove Suit": "Снять скафандр",
    "Hygiene": "Гигиена",
    "Patrol": "Патруль",
}

# Correction mapping after model translation
CORRECTIONS = {
    "Спаун": "появление",
    "спавн": "появление",
    "Пристин": "Нетронутый",
    "пристин": "нетронутый",
    "ДОКУШИТЕЛЬНЫЕ ПОМЕЩЕНИЯ": "НЕТ СТЫКОВОЧНЫХ СООРУЖЕНИЙ",
    "Отбой в открытии": "Отказ в открытии",
    "отбой в открытии": "отказ в открытии",
    "Враг Спаун": "Появление врагов",
    "Пиратский спаун": "Появление пирата",
    "Дозвониться в космический костюм": "Надеть скафандр",
    "ККЭЙР": "CCRE",
    "ККЭВ": "CCRE",
    "RCRE": "CCRE",
    "ИКЭ": "CCRE",
    "скафандр и шлем, прежде чем использовать шлюз.": "скафандр и шлем перед использованием шлюза.",
    "Я рад, что тебя недавно поприветствовали": "чувствует себя хорошо после недавнего приветствия",
    "Я рада, что тебя недавно поприветствовали": "чувствует себя хорошо после недавнего приветствия",
}

def apply_corrections(text):
    for bad, good in CORRECTIONS.items():
        if bad in text:
            text = text.replace(bad, good)
    return text

# Helper functions
placeholder_pat = r'\[[^\]]+\]'
acr_pat = r'\b(?:' + '|'.join(map(re.escape, PROTECT_ACRO)) + r')\b'
combined_pat = f'({placeholder_pat}|{acr_pat})'
combined_regex = re.compile(combined_pat)
ph_regex = re.compile(placeholder_pat)
acr_regex = re.compile(acr_pat)

def split_protected(text):
    parts = combined_regex.split(text)
    result=[]
    for p in parts:
        if p is None or p=='':
            continue
        if ph_regex.fullmatch(p) or acr_regex.fullmatch(p):
            result.append((True, p))
        else:
            result.append((False, p))
    return result

def translate_segments_list(segs):
    # segs: list of non-protected contents
    cores = []
    metas = []
    for s in segs:
        if not s.strip() or not re.search(r'[A-Za-z]', s):
            metas.append((s, False))
            cores.append(None)
        else:
            m = re.match(r'^(\s*)(.*?)(\s*)$', s, re.DOTALL)
            if m:
                lead, core, trail = m.groups()
                # skip if core empty
                if not core.strip():
                    metas.append((s, False))
                    cores.append(None)
                else:
                    metas.append((lead, core, trail, True))
                    cores.append(core)
            else:
                metas.append(('', s, '', True))
                cores.append(s)
    to_trans = [c for c in cores if c is not None]
    if not to_trans:
        return segs
    # batch translate
    batch_size = 16
    translated_cores=[]
    for i in range(0, len(to_trans), batch_size):
        batch = to_trans[i:i+batch_size]
        tokens = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512)
        out = model.generate(**tokens, max_length=512)
        dec = [tokenizer.decode(t, skip_special_tokens=True) for t in out]
        translated_cores.extend(dec)
    result=[]
    idx=0
    for meta in metas:
        if len(meta)==2:
            result.append(meta[0])
        else:
            lead, orig_core, trail, _ = meta
            trans_core = translated_cores[idx]
            idx+=1
            # apply corrections after?
            trans_core = apply_corrections(trans_core)
            result.append(lead + trans_core + trail)
    return result

def translate_full(text):
    if not text or not text.strip():
        return text
    # check manual dict exact match
    stripped = text.strip()
    if stripped in MANUAL_DICT:
        # preserve leading/trailing spaces
        m = re.match(r'^(\s*)(.*?)(\s*)$', text, re.DOTALL)
        if m:
            lead, core, trail = m.groups()
            if core in MANUAL_DICT:
                return lead + MANUAL_DICT[core] + trail
        return MANUAL_DICT.get(text, text)
    # handle newlines separately
    if '\n' in text:
        lines = text.split('\n')
        translated_lines = [translate_full(line) if line.strip() else line for line in lines]
        return '\n'.join(translated_lines)
    parts = split_protected(text)
    non_prot = [c for is_prot, c in parts if not is_prot]
    trans_non_prot = translate_segments_list(non_prot)
    out=[]
    j=0
    for is_prot, c in parts:
        if is_prot:
            out.append(c)
        else:
            out.append(trans_non_prot[j])
            j+=1
    joined = ''.join(out)
    joined = apply_corrections(joined)
    return joined

# Load input
print("Loading input json", flush=True)
with open("/home/user/uploads/untranslated.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Collect unique texts
unique_map = {}
all_fields = []

for file_path, entries in data['files'].items():
    for entry in entries:
        for field in ['strNameFriendly','strNameShort','strTitle','strDesc','original']:
            if field in entry and entry[field]:
                val = entry[field]
                # skip if only placeholders? but still need translation
                if val not in unique_map:
                    unique_map[val] = None
                all_fields.append((file_path, entry, field, val))

print(f"Unique texts: {len(unique_map)} total fields: {len(all_fields)}", flush=True)

# Translate unique texts
unique_list = list(unique_map.keys())
# Pre-fill manual
for txt in unique_list:
    if txt.strip() in MANUAL_DICT:
        unique_map[txt] = MANUAL_DICT[txt.strip()]
        # preserve spaces? we already handle exact, but for simplicity
        # Actually use translate_full logic for manual
        # We'll just set and skip model
    # also handle _existing for some? not here

# Filter those needing model translation
to_translate = [t for t in unique_list if unique_map[t] is None]

print(f"Need model translation for {len(to_translate)} unique texts", flush=True)

# Translate in batches
batch_size = 16
for i in range(0, len(to_translate), batch_size):
    batch = to_translate[i:i+batch_size]
    # translate each via translate_full which itself batches internally, but we can call directly for better perf
    # We'll call translate_full one by one but it will batch inside? Let's call individually for now using translate_full
    # To improve speed, we can directly use translate_segments approach, but placeholder protection needed
    # For simplicity, use translate_full per text (which itself will batch segments if needed)
    # However translate_full for single text does model call for its segments only, okay
    for txt in batch:
        try:
            trans = translate_full(txt)
            unique_map[txt] = trans
        except Exception as e:
            print(f"Error translating {txt[:100]}: {e}", flush=True)
            unique_map[txt] = txt  # fallback
    if i % (batch_size*10) == 0:
        print(f"Progress {i}/{len(to_translate)}", flush=True)

print("Translation of unique done", flush=True)

# Build output files
output_files = {}

for file_path, entries in data['files'].items():
    out_entries = []
    for entry in entries:
        if 'key' in entry and 'original' in entry:
            # Format2
            orig = entry['original']
            trans = unique_map.get(orig, orig)
            # Ensure translation field exists
            out_entry = {
                "key": entry['key'],
                "original": orig,
                "translation": trans
            }
            out_entries.append(out_entry)
        else:
            # Format1
            out_entry = {}
            if 'strName' in entry:
                out_entry['strName'] = entry['strName']
            # handle _existing as fallback
            existing = entry.get('_existing', {})
            for field in ['strNameFriendly','strNameShort','strTitle','strDesc']:
                if field in entry and entry[field]:
                    orig_val = entry[field]
                    trans_val = unique_map.get(orig_val, orig_val)
                    # If existing has translation for same field, prefer existing if it looks Russian (contains cyrillic)
                    if field in existing:
                        # existing may be translation
                        ex_val = existing[field]
                        # check if cyrillic
                        if re.search(r'[А-Яа-я]', ex_val):
                            trans_val = ex_val
                    out_entry[field] = trans_val
                elif field in existing:
                    # field not in original but in existing -> include as translation
                    out_entry[field] = existing[field]
            # also copy any other fields? spec says preserve all fields
            # For safety include strNameFriendly etc that may have been in original but we already
            # If original had other fields, keep them
            # Actually we should copy any field not handled that is not _existing
            for k,v in entry.items():
                if k not in out_entry and k != '_existing':
                    # if it's translatable we already handled, otherwise keep
                    if k not in ['strNameFriendly','strNameShort','strTitle','strDesc']:
                        out_entry[k] = v
            out_entries.append(out_entry)
    output_files[file_path] = out_entries

output_data = {"files": output_files}

# Save
with open("/home/user/translated.json", "w", encoding="utf-8") as out:
    json.dump(output_data, out, ensure_ascii=False, indent=2)

print("Saved translated.json", flush=True)
