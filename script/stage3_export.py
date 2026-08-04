# -*- coding: utf-8 -*-
"""Export missing/untranslated stage-3 entries per file for translation.

Writes script/stage3_src/<file>.json = list of {name, title, desc} to translate.
"""
import sys, json, io, os, re
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/interactions/plotIAs/'
M = 'ostranautsRuNss/data/interactions/plotIAs/'
OUT = 'script/stage3_src'
os.makedirs(OUT, exist_ok=True)

FILES = ['79au', 'ceres_bc', 'ceres_p1', 'ceres_p2', 'ceres_p3', 'ceres_p4', 'ceres_p5']
cyr = re.compile('[а-яА-ЯёЁ]')
lat = re.compile('[a-z]{3,}')

summary = []
for f in FILES:
    g = load_json_file(G + f'interactions_plots_{f}.json')
    mp = M + f'interactions_plots_{f}.json'
    m = load_json_file(mp) if os.path.exists(mp) else []
    mset = {e.get('strName') for e in m}
    todo = []
    # missing entries
    for e in g:
        if e.get('strName') not in mset:
            t = e.get('strTitle') or ''
            d = e.get('strDesc') or ''
            if t or d:
                todo.append({'name': e['strName'], 'title': t, 'desc': d})
    # untranslated existing entries
    for e in m:
        t = e.get('strTitle') or ''
        d = e.get('strDesc') or ''
        untr = (t and lat.search(t) and not cyr.search(t)) or (d and lat.search(d) and not cyr.search(d))
        if untr:
            todo.append({'name': e['strName'], 'title': t, 'desc': d, 'existing': True})
    json.dump(todo, io.open(f'{OUT}/{f}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    chars = sum(len(x['title']) + len(x['desc']) for x in todo)
    summary.append((f, len(todo), chars))

for f, n, c in summary:
    print(f'{f:12} entries={n:4} chars={c:6}')
print('TOTAL entries:', sum(n for _, n, _ in summary), 'chars:', sum(c for _, _, c in summary))
