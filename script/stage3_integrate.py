# -*- coding: utf-8 -*-
"""Integrate stage-3 translations into mod plotIA files.

Reads script/stage3_out/<file>.json = list of {name, title_ru, desc_ru}.
For each source entry (from game original), builds the full entry preserving
ALL non-text fields verbatim, substitutes translated title/desc, then:
  - appends if strName absent in mod
  - replaces title/desc in-place if strName present (untranslated existing)
Validates placeholder parity vs original before writing.
"""
import sys, json, io, os, re
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/interactions/plotIAs/'
M = 'ostranautsRuNss/data/interactions/plotIAs/'
OUTDIR = 'script/stage3_out'

TOK = re.compile(r'\[[^\]\r\n]+\]|\{[^}\r\n]+\}|<[^>\r\n]+>')

def tokens(s):
    # count each token; gender-cond variants collapsed to the prefix only
    out = []
    for t in TOK.findall(s or ''):
        if t.startswith('[us-custom-characterGenderCond'):
            out.append('[GENDERCOND]')
        else:
            out.append(t)
    return sorted(out)

def process(f, apply=False):
    src = load_json_file(f'script/stage3_src/{f}.json')
    outp = f'{OUTDIR}/{f}.json'
    if not os.path.exists(outp):
        return None
    tr = {e['name']: e for e in load_json_file(outp)}
    g = load_json_file(G + f'interactions_plots_{f}.json')
    gd = {e['strName']: e for e in g}
    mp = M + f'interactions_plots_{f}.json'
    m = load_json_file(mp) if os.path.exists(mp) else []
    mindex = {e.get('strName'): i for i, e in enumerate(m)}

    issues = []
    appended = replaced = 0
    for s in src:
        name = s['name']
        t = tr.get(name)
        if not t:
            issues.append(('MISSING_TRANSLATION', name)); continue
        og = gd.get(name)
        # placeholder parity check
        for field, en, ru in [('title', s.get('title', ''), t.get('title_ru', '')),
                               ('desc', s.get('desc', ''), t.get('desc_ru', ''))]:
            if en and tokens(en) != tokens(ru):
                issues.append(('TOKEN_MISMATCH', name, field, tokens(en), tokens(ru)))
        if s.get('existing'):
            i = mindex.get(name)
            if i is None:
                issues.append(('EXPECTED_EXISTING_ABSENT', name)); continue
            if t.get('title_ru'): m[i]['strTitle'] = t['title_ru']
            if t.get('desc_ru'): m[i]['strDesc'] = t['desc_ru']
            replaced += 1
        else:
            ne = dict(og)  # preserve all fields verbatim
            if 'strTitle' in ne or t.get('title_ru'): ne['strTitle'] = t.get('title_ru', ne.get('strTitle', ''))
            ne['strDesc'] = t.get('desc_ru', ne.get('strDesc', ''))
            m.append(ne)
            appended += 1

    if apply and not [i for i in issues if i[0] in ('TOKEN_MISMATCH', 'MISSING_TRANSLATION')]:
        json.dump(m, io.open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        status = 'WROTE'
    else:
        status = 'DRY'
    return {'file': f, 'appended': appended, 'replaced': replaced,
            'issues': issues, 'status': status, 'total_mod': len(m)}

if __name__ == '__main__':
    apply = '--apply' in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    files = only or ['79au', 'ceres_bc', 'ceres_p1', 'ceres_p2', 'ceres_p3', 'ceres_p4', 'ceres_p5']
    for f in files:
        r = process(f, apply=apply)
        if r is None:
            print(f'{f:12} -- no output yet'); continue
        print(f"{r['file']:12} {r['status']:5} append={r['appended']:3} replace={r['replaced']:3} total={r['total_mod']:4} issues={len(r['issues'])}")
        for iss in r['issues'][:20]:
            print('   ', iss)
