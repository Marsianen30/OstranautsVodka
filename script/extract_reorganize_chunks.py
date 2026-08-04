#!/usr/bin/env python3
"""Extract context-dependent Russian reorganization chunks from complete/.

Output format is compatible with apply_translation.py:
  ### relpath | strName | field
  current text
  ---

Only text fields containing Russian plus one of the English grammatical
placeholders are selected. The script is conservative and does not touch files.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path('/home/user/wspace')
COMPLETE = ROOT / 'complete'
OUT = ROOT / 'work/reorganize_chunks'
CHUNK_SIZE = 522
FIELDS = {
    'strTitle', 'strDesc', 'strNameFriendly', 'strTooltip',
    'strDescription', 'strRequirementDescription',
    'strFriendlyDescription', 'strMainText',
}
GRAMMAR_PLACEHOLDER = re.compile(r"\[(?:is|has|does|doesn't|isn't|was|had)\]")
CYRILLIC = re.compile(r'[А-Яа-яЁё]')


def load(path: Path):
    text = path.read_text(encoding='utf-8-sig')
    # complete JSON is valid; this also tolerates JSONC files if one is added.
    text = re.sub(r'//[^\n]*', '', text)
    return json.loads(text)


def walk(value):
    if isinstance(value, dict):
        name = value.get('strName', '')
        for field, item in value.items():
            if field in FIELDS and isinstance(item, str):
                yield name, field, item
            if isinstance(item, (dict, list)):
                yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def main():
    rows = []
    for path in sorted(COMPLETE.rglob('*.json')):
        if path.name in {'verbs.json', 'grammar.json'}:
            continue
        try:
            data = load(path)
        except Exception as exc:
            print(f'SKIP {path}: {exc}')
            continue
        rel = str(path.relative_to(COMPLETE))
        for name, field, text in walk(data):
            if name and CYRILLIC.search(text) and GRAMMAR_PLACEHOLDER.search(text):
                rows.append((rel, name, field, text))

    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob('reorganize_chunk_*.txt'):
        old.unlink()

    chunks = [rows[i:i + CHUNK_SIZE] for i in range(0, len(rows), CHUNK_SIZE)]
    for index, chunk in enumerate(chunks, 1):
        output = OUT / f'reorganize_chunk_{index:03d}.txt'
        with output.open('w', encoding='utf-8') as fh:
            for rel, name, field, text in chunk:
                fh.write(f'### {rel} | {name} | {field}\n')
                fh.write(text.replace('\r\n', '\n') + '\n')
                fh.write('---\n')
        print(f'{output}: {len(chunk)} entries')

    print(f'Total: {len(rows)} entries, {len(chunks)} chunks, size={CHUNK_SIZE}')


if __name__ == '__main__':
    main()
