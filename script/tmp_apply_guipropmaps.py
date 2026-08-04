# -*- coding: utf-8 -*-
import sys, json, io
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/guipropmaps/guipropmaps.json'
OUT = 'ostranautsRuNss/data/guipropmaps/guipropmaps.json'

FN_TR = {
    "'Heavy Lift Rotor'": "«Кран большой грузоподъёмности»",
    'Air Pump': 'Воздушный насос',
    'Alarm': 'Сигнализация',
    'AtmoScrubber': 'Скруббер атмосферы',
    'Ayotimiwa Salvage Notice': 'Уведомление о спасательных работах «Айотимива»',
    'Ayotimiwa Salvage Permit': 'Разрешение на спасательные работы «Айотимива»',
    'Battery': 'Батарея',
    'Bounty Board': 'Доска наград',
    'Breaker Box': 'Щиток автоматов',
    'Bulk Trading Interface': 'Интерфейс оптовой торговли',
    'CO2 AtmoScrubber User Guide': 'Руководство пользователя скруббера CO2',
    'CO2 Pressure Alarm': 'Сигнализация давления CO2',
    'Career Kiosk': 'Киоск карьеры',
    'Cargo Trader': 'Торговец грузами',
    'CargoPod': 'Грузовой модуль',
    'Comms Controls': 'Пульт связи',
    'Contaminants AtmoScrubber': 'Скруббер загрязнений',
    'Contaminants Pressure Alarm': 'Сигнализация давления загрязнений',
    'Cooler': 'Охладитель',
    'Crate Lock': 'Замок ящика',
    'Crew Duties': 'Обязанности экипажа',
    'Crew Roster': 'Список экипажа',
    'Door Lock': 'Замок двери',
    'Encounter': 'Встреча',
    'Environmental Cert': 'Сертификат экологии',
    'Faction Trading Interface': 'Интерфейс фракционной торговли',
    'Feature Voting': 'Голосование за функции',
    'Ferry Kiosk': 'Киоск паромов',
    'Finances': 'Финансы',
    'Fusion Cert': 'Сертификат термоядерного реактора',
    'Gig Nexus': 'Биржа заказов',
    'Heater': 'Обогреватель',
    'Hire': 'Найм',
    'Homeworld Kiosk': 'Киоск родного мира',
    'Hull Patch': 'Заплата корпуса',
    'Inventory': 'Инвентарь',
    'Launch Area': 'Зона запуска',
    'Loot Spawner': 'Генератор лута',
    'N2 Pressure Alarm': 'Сигнализация давления N2',
    'Nav Controls': 'Навигационный пульт',
    'Nav Manual': 'Навигационное руководство',
    'O2 Pressure Alarm': 'Сигнализация давления O2',
    'O2 Pressure Vent': 'Клапан сброса давления O2',
    'OKLG Transit': 'Транзит OKLG',
    "Ogiso's Register Work Safety": 'Реестр охраны труда «Огисо»',
    'PDA': 'КПК',
    'PDA Home': 'КПК: главная',
    'PDA NAV': 'КПК: навигация',
    'PDA NavLink': 'КПК: навигационная связь',
    'Poster: Bismertnaya Classic': 'Плакат: «Бисмертная Классика»',
    'Poster: Bismertnaya Psyche': 'Плакат: «Бисмертная Психея»',
    'Poster: Black Bull Kape': 'Плакат: «Чёрный Бык Кейп»',
    'Poster: Damask Rose': 'Плакат: «Дамасская роза»',
    'Poster: Grande Prêmio do Encantado': 'Плакат: «Гран-при Энкантаду»',
    'Poster: Lucky says PANIC': 'Плакат: «Лаки говорит: ПАНИКА»',
    'Poster: Lucky says YIELD': 'Плакат: «Лаки говорит: УСТУПИ»',
    'Poster: New Earth Ostracon': 'Плакат: «Остракон Новой Земли»',
    'Poster: Travel Atlantis': 'Плакат: «Путешествуйте в Атлантис»',
    'Poster: Travel Tharsis Landing': 'Плакат: «Путешествуйте в Тарсис-Лэндинг»',
    "Poster: Viceroy's Advertisement": 'Плакат: реклама наместника',
    'Racing Kiosk': 'Киоск гонок',
    'Reactor Controls': 'Пульт реактора',
    'Real Estate Broker': 'Брокер недвижимости',
    'Refuel Kiosk': 'Киоск заправки',
    'Sensor': 'Датчик',
    'Ship Broker': 'Брокер кораблей',
    'Ship Rating': 'Рейтинг корабля',
    'Sink Mirror': 'Зеркало над раковиной',
    'Smoke Alarm': 'Датчик дыма',
    'Social': 'Общение',
    'Social Combat': 'Социальный конфликт',
    'Stabilizer': 'Стабилизатор',
    'Super Fast-Forward': 'Суперускоренная перемотка',
    'Task List': 'Список задач',
    'Thermostat': 'Термостат',
    'Toggles': 'Переключатели',
    'Trading Interface': 'Торговый интерфейс',
    'Traits Kiosk': 'Киоск черт характера',
    'Transit Kiosk': 'Транзитный киоск',
    'Transponder Broker': 'Брокер транспондеров',
    'XPDR Transponder': 'Транспондер XPDR',
}

TT_TR = {
    'Alarm Override': 'Отключение сигнализации',
    'Heavy Lift Rotor': 'Кран большой грузоподъёмности',
    'INPUT 1': 'ВХОД 1',
    'INPUT 2': 'ВХОД 2',
    'INPUT 3': 'ВХОД 3',
    'INPUT 4': 'ВХОД 4',
    'Sensor': 'Датчик',
    'Stabilizer': 'Стабилизатор',
    'Unscrew for CO2 Sensor Input Signal': 'Открутите для сигнала датчика CO2',
    'Unscrew for Contaminants Sensor Input Signal': 'Открутите для сигнала датчика загрязнений',
    'Unscrew for Pressure Sensor Input Signal': 'Открутите для сигнала датчика давления',
    'Unscrew for Thermostat Sensor Input Signal': 'Открутите для сигнала датчика термостата',
}

d = load_json_file(G)
fn_count = 0
tt_count = 0
for e in d:
    m = e.get('dictGUIPropMap', [])
    for i in range(0, len(m) - 1, 2):
        k, v = m[i], m[i + 1]
        if k == 'strFriendlyName' and v in FN_TR:
            m[i + 1] = FN_TR[v]
            fn_count += 1
        elif k and k.startswith('strTitle') and v in TT_TR:
            m[i + 1] = TT_TR[v]
            tt_count += 1

json.dump(d, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('fn_replaced', fn_count, 'tt_replaced', tt_count)
