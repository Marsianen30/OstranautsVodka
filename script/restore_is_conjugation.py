#!/usr/bin/env python3
"""Restore [is] before the Russian word `является`.

The previous conservative cleanup was too aggressive: `[is] является` must
remain because the DLL conjugates [is] by person (я являюсь, ты являешься,
...). The translate tree still contains the pre-cleanup strings and is used as
an occurrence map; no translation source is changed by this script.
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

ROOT = Path('/home/user/wspace')
COMPLETE = ROOT / 'complete'
TRANSLATE = ROOT / 'translate'
MARKER = '[is] является'
VALID = set('"\\/bfnrtu')


def clean(text):
    out=[]; ins=False; esc=False; i=0
    while i < len(text):
        c=text[i]
        if ins:
            if esc:
                if c not in VALID: out.append('\\')
                out.append(c); esc=False; i+=1; continue
            if c=='\\': out.append(c); esc=True; i+=1; continue
            if ord(c)<32:
                out.append({'\n':'\\n','\r':'\\r','\t':'\\t'}.get(c, f'\\u{ord(c):04x}')); i+=1; continue
            out.append(c)
            if c=='"': ins=False
            i+=1
        else:
            if c=='"': ins=True; out.append(c); i+=1
            elif c=='/' and i+1<len(text) and text[i+1]=='/':
                i+=2
                while i<len(text) and text[i] not in '\r\n': i+=1
            else: out.append(c); i+=1
    return ''.join(out)


def load(path):
    return json.loads(clean(path.read_text(encoding='utf-8-sig')))


def leaves(c, t, cp=(), tp=()):
    if isinstance(c, dict) and isinstance(t, dict):
        for k, v in c.items():
            if k in t:
                yield from leaves(v, t[k], cp+(k,), tp+(k,))
    elif isinstance(c, list) and isinstance(t, list):
        named=lambda x: all(isinstance(y,dict) and isinstance(y.get('strName'),str) for y in x)
        if named(c) and named(t):
            tm=collections.defaultdict(list)
            for j, x in enumerate(t): tm[x['strName']].append((j,x))
            seen=collections.Counter()
            for i, x in enumerate(c):
                name=x['strName']; occ=seen[name]; seen[name]+=1
                if occ < len(tm[name]):
                    j,y=tm[name][occ]
                    yield from leaves(x,y,cp+(i,),tp+(j,))
        else:
            for i,(a,b) in enumerate(zip(c,t)):
                yield from leaves(a,b,cp+(i,),tp+(i,))
    elif isinstance(c,str) and isinstance(t,str):
        yield cp,c,t


def put_before_n(value, n):
    result=value
    pos=0
    for _ in range(n):
        idx=result.find('является', pos)
        if idx < 0:
            raise RuntimeError(f'not enough `является` in {value!r}')
        result=result[:idx]+'[is] '+result[idx:]
        pos=idx+len('[is] является')
    return result


def main():
    replacements={}
    expected=0
    for cp in sorted(COMPLETE.rglob('*.json')):
        rel=cp.relative_to(COMPLETE); tp=TRANSLATE/rel
        if not tp.exists() or rel.as_posix() in {'tokens/verbs.json','tokens/grammar.json'}: continue
        try: c=load(cp); t=load(tp)
        except Exception: continue
        for _, cs, ts in leaves(c,t):
            n=ts.count(MARKER)
            if n:
                if cs.count('является') < n:
                    raise RuntimeError(f'Cannot restore {rel}: {cs!r}')
                if cs in replacements and replacements[cs] != n:
                    raise RuntimeError(f'ambiguous identical string with different counts: {cs!r}')
                replacements[cs]=n
                expected += n

    changed_files=0; changed_strings=0; changed_occurrences=0
    for path in sorted(COMPLETE.rglob('*.json')):
        text=path.read_text(encoding='utf-8')
        new=text
        for old,n in replacements.items():
            serialized_old=json.dumps(old,ensure_ascii=False)
            if serialized_old not in new: continue
            restored=put_before_n(old,n)
            new=new.replace(serialized_old,json.dumps(restored,ensure_ascii=False))
            changed_strings += 1
            changed_occurrences += n
        if new != text:
            path.write_text(new,encoding='utf-8')
            changed_files += 1
    print({'expected_occurrences':expected,'changed_files':changed_files,'changed_strings':changed_strings,'restored_occurrences':changed_occurrences})

if __name__=='__main__': main()
