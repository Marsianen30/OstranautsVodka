# -*- coding: utf-8 -*-
import sys, json, io
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/condtrigs/contrigs_plots.json'
OUT = 'ostranautsRuNss/data/condtrigs/contrigs_plots.json'

TR = {
    'Venus Immunity': 'Иммунитет Венеры',
    'Is a San Diego Trader': 'Торговец Сан-Диего',
    'Is a San Diego Renbao Trader': 'Торговец Ренбао в Сан-Диего',
    'Is a San Diego Shoe Trader': 'Торговец обувью в Сан-Диего',
    'Is a San Diego Clothes Trader': 'Торговец одеждой в Сан-Диего',
    'Is a San Diego Curio Trader': 'Торговец редкостями в Сан-Диего',
    'Is a San Diego Sulaiman Trader': 'Торговец Сулейман в Сан-Диего',
}

d = load_json_file(G)
count = 0
for e in d:
    v = e.get('strCondName')
    if v in TR:
        e['strCondName'] = TR[v]
        count += 1

json.dump(d, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('replaced', count, 'total', len(d))
