# -*- coding: utf-8 -*-
import sys, json, io
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

DATA = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/conditions/conditions_crime_{}.json'
OUT = 'ostranautsRuNss/data/conditions/conditions_crime_{}.json'

# code -> (loc_name_nominative, loc_name_genitive_or_locative_for_"in X", loc_name_instr_for_"with X")
# We'll build phrase-based translations directly per code, following the BCER pattern.
LOC = {
    'EJDR': 'Джейд Рэббит',
    'HQCH': 'Цинчэне',
    'JATL': 'Атлантисе',
    'JFTS': 'Форт-Симпсоне',
    'MHNG': 'Ханчжоу',
    'MSUZ': 'Сучжоу',
    'MTRS': 'Тарсис-Лэндинге',
    'MVOL': 'Вольтере, Деймос',
    'SVIR': 'Вирджинии, Титан',
}
# "with X" (instrumental-ish, used as "с X" or same locative depending on style; BCER used "в Галилейской Конфедерации" for both in/with)
LOC_WITH = {
    'EJDR': 'Джейд Рэббит',
    'HQCH': 'Цинчэнем',
    'JATL': 'Атлантисом',
    'JFTS': 'Форт-Симпсоном',
    'MHNG': 'Ханчжоу',
    'MSUZ': 'Сучжоу',
    'MTRS': 'Тарсис-Лэндингом',
    'MVOL': 'Вольтером',
    'SVIR': 'Вирджинией, Титан',
}
LOC_BY = {
    'EJDR': 'Джейд Рэббит',
    'HQCH': 'Цинчэня',
    'JATL': 'Атлантиса',
    'JFTS': 'Форт-Симпсона',
    'MHNG': 'Ханчжоу',
    'MSUZ': 'Сучжоу',
    'MTRS': 'Тарсис-Лэндинга',
    'MVOL': 'Вольтера',
    'SVIR': 'Вирджинии, Титан',
}
FRIENDLY_PREFIX = {
    'EJDR': 'EJDR',
    'HQCH': 'HQCH',
    'JATL': 'JATL',
    'JFTS': 'JFTS',
    'MHNG': 'MHNG',
    'MSUZ': 'MSUZ',
    'MTRS': 'MTRS',
    'MVOL': 'MVOL',
    'SVIR': 'SVIR',
}

def build(code):
    loc_in = LOC[code]       # "в X"
    loc_with = LOC_WITH[code]  # "с X" / "действующий ордер ... в X" for with-cases (BCER uses "в X" even for with)
    loc_by = LOC_BY[code]     # "местными властями X"
    fp = FRIENDLY_PREFIX[code]
    entries = [
        {
            'strName': f'StatCrime{code}ArrestWarning',
            'strNameFriendly': f'Количество предупреждений об аресте от {fp}',
            'strColor': 'Bad',
            'strDesc': '[us] [has] столько предупреждений об аресте от ' + fp + '.',
            'nDisplaySelf': 0, 'nDisplayOther': 0, 'fDuration': 0.0, 'bRemoveAll': True,
        },
        {
            'strName': f'Crime{code}Arrest',
            'strNameFriendly': f'Ордер {fp} на арест',
            'strColor': 'Bad',
            'strDesc': f'[us] [has] действующий ордер на арест в {loc_in}.',
            'nDisplaySelf': 2, 'nDisplayOther': 2, 'fDuration': 0.0, 'bRemoveAll': True, 'bInvert': True,
        },
        {
            'strName': f'Crime{code}Threat',
            'strNameFriendly': f'Враг общества по версии {fp}',
            'strColor': 'Bad',
            'strDesc': f'[us] разыскивается живым или мёртвым местными властями {loc_by} и считается врагом общества.',
            'nDisplaySelf': 2, 'nDisplayOther': 2, 'fDuration': 0.0, 'bRemoveAll': True, 'bInvert': True,
        },
        {
            'strName': f'Crime{code}Trespass',
            'strNameFriendly': f'Ордер {fp} за нарушение границ',
            'strColor': 'Bad',
            'strDesc': f'[us] [has] действующий ордер за проникновение на частную территорию в {loc_in}.',
            'nDisplaySelf': 0, 'nDisplayOther': 0, 'fDuration': 1e-05, 'bRemoveAll': True,
            'aNext': [f'TUpCrime{code}TrespassNext'],
        },
        {
            'strName': f'Crime{code}StolenShip',
            'strNameFriendly': f'Ордер {fp} за угон корабля',
            'strColor': 'Bad',
            'strDesc': f'[us] [has] действующий ордер на арест в {loc_in} за угон корабля.',
            'nDisplaySelf': 2, 'nDisplayOther': 2, 'fDuration': 0.0, 'bRemoveAll': True,
        },
        {
            'strName': f'Crime{code}NoUndock',
            'strNameFriendly': f'Ордер {fp} за отказ отстыковаться',
            'strColor': 'Bad',
            'strDesc': f'[us] [has] действующий ордер на арест в {loc_in} за отказ отстыковаться во время инспекции офицера.',
            'nDisplaySelf': 2, 'nDisplayOther': 2, 'fDuration': 0.0, 'bRemoveAll': True,
        },
    ]
    return entries

TOK_RE = None
import re
TOK = re.compile(r'\[[^\]\r\n]+\]|\{[^}\r\n]+\}|<[^>\r\n]+>')
def tokens(s):
    return sorted(TOK.findall(s or ''))

for code in LOC:
    g = load_json_file(DATA.format(code))
    tr = build(code)
    trd = {e['strName']: e for e in tr}
    # validate all g entries covered and tokens match
    assert len(g) == len(tr), (code, len(g), len(tr))
    for e in g:
        name = e['strName']
        te = trd.get(name)
        assert te is not None, (code, name, 'missing in translation')
        if tokens(e.get('strDesc')) != tokens(te.get('strDesc')):
            print('TOKEN_MISMATCH', code, name, tokens(e.get('strDesc')), tokens(te.get('strDesc')))
    json.dump(tr, io.open(OUT.format(code), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('WROTE', code, len(tr))
