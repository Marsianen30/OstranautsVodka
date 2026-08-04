# -*- coding: utf-8 -*-
import sys, json, io
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/manpages/manpages.json'
OUT = 'ostranautsRuNss/data/manpages/manpages.json'

TR = {
    'Manual Pages': 'Страницы руководств',
    'Basics': 'Основы',
    'Basic Controls': 'Основное управление',
    'Work Safety': 'Охрана труда',
    "Ogiso's Register Work Safety Poster": 'Плакат по охране труда «Реестр Огисо»',
    'Hull Patch': 'Заплата корпуса',
    'Holden Patch by Halvorson': 'Заплата «Холден» от Halvorson',
    'Nav Console': 'Навигационная консоль',
    'Polaris Standard Navigation Console User Manual and Pilot Handbook': 'Руководство пользователя навигационной консоли Polaris Standard и справочник пилота',
    'Environmental': 'Экология',
    'Environmental Control Systems Certification Guide': 'Руководство по сертификации систем жизнеобеспечения',
    'Fusion': 'Термоядерный реактор',
    'Fusion Reactor Manual': 'Руководство по термоядерному реактору',
    "Cont'd": 'Продолжение',
    'Left Blank': 'Оставлено пустым',
}

d = load_json_file(G)
count = 0
for e in d:
    if e.get('strName') in TR:
        e['strName'] = TR[e['strName']]
        count += 1
    vals = e.get('aValues', [])
    for i, v in enumerate(vals):
        if v in TR:
            vals[i] = TR[v]
            count += 1

json.dump(d, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('replaced', count)
