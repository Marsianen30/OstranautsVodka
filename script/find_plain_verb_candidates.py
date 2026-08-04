#!/usr/bin/env python3
"""Find Russian verb forms left as ordinary text near entity placeholders.

This is a read-only audit. It does not modify complete/. The output is useful
for preparing the next reorganization chunks.
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

ROOT = Path('/home/user/wspace')
COMPLETE = ROOT / 'complete'
ORIGINAL = ROOT / 'original'
OUT = ROOT / 'work/plain_verb_candidates.tsv'
TOKEN = re.compile(r'\[[^\[\]\r\n]{1,120}\]')
WORD = re.compile(r'[А-Яа-яЁё-]+')
CYR = re.compile(r'[А-Яа-яЁё]')
VALID = set('"\\/bfnrtu')


def clean(text: str) -> str:
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


def load(path: Path):
    return json.loads(clean(path.read_text(encoding='utf-8-sig')))


def leaves(complete, original, path=()):
    if isinstance(complete, dict) and isinstance(original, dict):
        for key, value in complete.items():
            if key in original:
                yield from leaves(value, original[key], path+(key,))
    elif isinstance(complete, list) and isinstance(original, list):
        named=lambda a: all(isinstance(x,dict) and isinstance(x.get('strName'),str) for x in a)
        if named(complete) and named(original):
            om=collections.defaultdict(list)
            for j, item in enumerate(original): om[item['strName']].append(item)
            seen=collections.Counter()
            for i, item in enumerate(complete):
                name=item['strName']; occurrence=seen[name]; seen[name]+=1
                if occurrence < len(om[name]):
                    yield from leaves(item, om[name][occurrence], path+(i,))
        else:
            for i, (a, b) in enumerate(zip(complete, original)):
                yield from leaves(a, b, path+(i,))
    elif isinstance(complete, str) and isinstance(original, str):
        yield path, complete, original


def main():
    verb_forms={}
    vc=load(ROOT/'work/BepInExPlugin/verb_conjugations.json')['verbs']
    for entry in vc:
        for form in entry.get('forms',[]):
            if form and CYR.search(form) and len(form)>=3:
                verb_forms[form.casefold()] = form

    rows=[]
    for complete_path in sorted(COMPLETE.rglob('*.json')):
        rel=complete_path.relative_to(COMPLETE)
        original_path=ORIGINAL/rel
        if not original_path.exists() or rel.as_posix() in {'tokens/verbs.json','tokens/grammar.json'}:
            continue
        try:
            complete=load(complete_path); original=load(original_path)
        except Exception:
            continue
        for path, text, source in leaves(complete, original):
            entity=bool(re.search(r'\[(?:us|them|3rd)(?:-[^\]]+)?\]', text))
            if not entity or not TOKEN.search(source):
                continue
            masked=[]; last=0
            for match in TOKEN.finditer(text):
                masked.append(text[last:match.start()])
                masked.append(' '*(match.end()-match.start()))
                last=match.end()
            masked.append(text[last:])
            plain=''.join(masked)
            found=[]
            for word in WORD.findall(plain):
                if word.casefold() in verb_forms:
                    found.append(word)
            if not found:
                continue
            name=''; field=''
            # Walk the path back to a simple record is intentionally avoided;
            # the text plus relative path is enough for a later audit chunk.
            for word in found:
                rows.append((str(rel), '/'.join(map(str,path)), word, text, source))

    # Deduplicate exact candidates while preserving deterministic order.
    unique=[]; seen=set()
    for row in rows:
        if row not in seen:
            seen.add(row); unique.append(row)
    with OUT.open('w',encoding='utf-8') as fh:
        fh.write('file\tpath\tplain_form\tcomplete_text\toriginal_text\n')
        for row in unique:
            fh.write('\t'.join(x.replace('\t',' ').replace('\n','\\n') for x in row)+'\n')
        fh.write(f'# occurrences\t{len(unique)}\n')
        fh.write(f'# unique_plain_forms\t{len({x[2].casefold() for x in unique})}\n')
        fh.write(f'# unique_strings\t{len({x[3] for x in unique})}\n')
    counts=collections.Counter(x[2].casefold() for x in unique)
    print('candidate occurrences:',len(unique))
    print('unique forms:',len(counts))
    print('unique strings:',len({x[3] for x in unique}))
    print('top:',counts.most_common(40))
    print('report:',OUT)


if __name__=='__main__': main()
