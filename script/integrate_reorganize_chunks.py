#!/usr/bin/env python3
"""Validate, normalize, apply, and register the two reorganized chunks.

Rules agreed for this pass:
- present-tense Russian verbs stay in brackets and receive six forms;
- adjectives/participles/past/future/non-verb Russian bracket tokens lose brackets;
- entity pronoun tokens stay in brackets for grammar.json;
- [есть] is ordinary text, not a verb token.
"""
from __future__ import annotations

import collections
import json
import re
import shutil
from pathlib import Path

ROOT = Path('/home/user/wspace')
COMPLETE = ROOT / 'complete'
UPLOADS = Path('/home/user/uploads')
CHUNK_DIR = ROOT / 'work/reorganize_chunks'
PLUGIN_JSON = ROOT / 'work/BepInExPlugin/verb_conjugations.json'
DEPLOY_JSON = ROOT / 'work/verb_conjugations.json'
BACKUP_DIR = ROOT / 'work/reorganize_backup'

HEADER = re.compile(r'^### (.+?) \| (.+?) \| (\S+)$')
TOKEN = re.compile(r'\[[^\[\]\r\n]{1,120}\]')
RUSSIAN = re.compile(r'[А-Яа-яЁё]')

# These are present-tense verbs in the submitted chunks. Existing entries are
# preserved if already present in the authoritative JSON.
TRUE_PRESENT_VERBS = {
    'держит', 'стоит', 'ищет', 'нуждается', 'ставит', 'хочет',
    'собирается', 'заканчивает', 'имеет', 'продолжает', 'знает', 'может',
    'говорит', 'разбирается', 'покидает', 'возвращается', 'патрулирует',
    'использует', 'разговаривает', 'считает', 'выглядит', 'описывает',
    'работает', 'слышит', 'понимает', 'намекает', 'обвиняет', 'делится',
    'проявляет', 'смотрит', 'отдаёт', 'принимает', 'отвечает', 'ведётся',
    'уходит', 'идёт', 'спешит',
}

# Entity/grammar placeholders are not verbs. Preserve any Russian token in
# these namespaces; the submitted chunks only add the listed forms.
PRONOUN_PREFIXES = ('us-', 'them-', '3rd-', 'racing_icon-', 'they-')
PRONOUN_EXACT = {'us', 'them', '3rd', 'racing_icon'}

# Hand-curated six-form present-tense sets for the new verbs. Existing entries
# in verb_conjugations.json remain authoritative and are not overwritten.
NEW_FORMS = {
    'держит': ['держу', 'держишь', 'держит', 'держим', 'держите', 'держат'],
    'стоит': ['стою', 'стоишь', 'стоит', 'стоим', 'стоите', 'стоят'],
    'нуждается': ['нуждаюсь', 'нуждаешься', 'нуждается', 'нуждаемся', 'нуждаетесь', 'нуждаются'],
    'ставит': ['ставлю', 'ставишь', 'ставит', 'ставим', 'ставите', 'ставят'],
    'собирается': ['собираюсь', 'собираешься', 'собирается', 'собираемся', 'собираетесь', 'собираются'],
    'заканчивает': ['заканчиваю', 'заканчиваешь', 'заканчивает', 'заканчиваем', 'заканчиваете', 'заканчивают'],
    'имеет': ['имею', 'имеешь', 'имеет', 'имеем', 'имеете', 'имеют'],
    'продолжает': ['продолжаю', 'продолжаешь', 'продолжает', 'продолжаем', 'продолжаете', 'продолжают'],
    'может': ['могу', 'можешь', 'может', 'можем', 'можете', 'могут'],
    'разбирается': ['разбираюсь', 'разбираешься', 'разбирается', 'разбираемся', 'разбираетесь', 'разбираются'],
    'покидает': ['покидаю', 'покидаешь', 'покидает', 'покидаем', 'покидаете', 'покидают'],
    'возвращается': ['возвращаюсь', 'возвращаешься', 'возвращается', 'возвращаемся', 'возвращаетесь', 'возвращаются'],
    'патрулирует': ['патрулирую', 'патрулируешь', 'патрулирует', 'патрулируем', 'патрулируете', 'патрулируют'],
    'использует': ['использую', 'используешь', 'использует', 'используем', 'используете', 'используют'],
    'разговаривает': ['разговариваю', 'разговариваешь', 'разговаривает', 'разговариваем', 'разговариваете', 'разговаривают'],
    'считает': ['считаю', 'считаешь', 'считает', 'считаем', 'считаете', 'считают'],
    'выглядит': ['выгляжу', 'выглядишь', 'выглядит', 'выглядим', 'выглядите', 'выглядят'],
    'описывает': ['описываю', 'описываешь', 'описывает', 'описываем', 'описываете', 'описывают'],
    'работает': ['работаю', 'работаешь', 'работает', 'работаем', 'работаете', 'работают'],
    'слышит': ['слышу', 'слышишь', 'слышит', 'слышим', 'слышите', 'слышат'],
    'понимает': ['понимаю', 'понимаешь', 'понимает', 'понимаем', 'понимаете', 'понимают'],
    'намекает': ['намекаю', 'намекаешь', 'намекает', 'намекаем', 'намекаете', 'намекают'],
    'обвиняет': ['обвиняю', 'обвиняешь', 'обвиняет', 'обвиняем', 'обвиняете', 'обвиняют'],
    'делится': ['делюсь', 'делишься', 'делится', 'делимся', 'делитесь', 'делятся'],
    'проявляет': ['проявляю', 'проявляешь', 'проявляет', 'проявляем', 'проявляете', 'проявляют'],
    'смотрит': ['смотрю', 'смотришь', 'смотрит', 'смотрим', 'смотрите', 'смотрят'],
    'отдаёт': ['отдаю', 'отдаёшь', 'отдаёт', 'отдаём', 'отдаёте', 'отдают'],
    'принимает': ['принимаю', 'принимаешь', 'принимает', 'принимаем', 'принимаете', 'принимают'],
    'отвечает': ['отвечаю', 'отвечаешь', 'отвечает', 'отвечаем', 'отвечаете', 'отвечают'],
    'ведётся': ['ведусь', 'ведёшься', 'ведётся', 'ведёмся', 'ведётесь', 'ведутся'],
    'уходит': ['ухожу', 'уходишь', 'уходит', 'уходим', 'уходите', 'уходят'],
    'идёт': ['иду', 'идёшь', 'идёт', 'идём', 'идёте', 'идут'],
    'спешит': ['спешу', 'спешишь', 'спешит', 'спешим', 'спешите', 'спешат'],
}


def parse_chunk(path: Path):
    lines = path.read_text(encoding='utf-8').splitlines()
    rows = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        match = HEADER.match(lines[i])
        if not match:
            raise RuntimeError(f'{path}: invalid header line {i + 1}: {lines[i]}')
        rel, name, field = match.groups()
        i += 1
        body = []
        while i < len(lines) and lines[i] != '---':
            body.append(lines[i])
            i += 1
        if i >= len(lines):
            raise RuntimeError(f'{path}: missing separator after {name}')
        i += 1
        rows.append((rel, name, field, '\n'.join(body).strip()))
    return rows


def is_pronoun(inner):
    return inner in PRONOUN_EXACT or inner.startswith(PRONOUN_PREFIXES) or any(
        inner.startswith(x) for x in ('us-', 'them-', '3rd-')
    )


def normalize_text(text):
    """Remove brackets from non-verb Russian additions; preserve true verbs."""
    def classify(match):
        token = match.group(0)
        inner = token[1:-1]
        if not RUSSIAN.search(inner):
            return token
        if is_pronoun(inner) or inner in TRUE_PRESENT_VERBS:
            return token
        return inner

    # Only remove [is] when it directly precedes a Russian placeholder that is
    # being converted to ordinary adjective/participle/past text. Do not remove
    # [is] before ordinary Cyrillic text such as `[is] тем` or `[is] частью`;
    # those need the conjugated copula `являешься`.
    pair = re.compile(r'\[is\]\s+(\[[^\[\]\r\n]{1,120}\])')
    def replace_pair(match):
        token = match.group(1)
        inner = token[1:-1]
        if RUSSIAN.search(inner) and not (is_pronoun(inner) or inner in TRUE_PRESENT_VERBS):
            return inner
        return match.group(0)

    result = pair.sub(replace_pair, text)
    return TOKEN.sub(classify, result)


def walk_records(value):
    if isinstance(value, dict):
        name = value.get('strName')
        for field, item in value.items():
            if isinstance(item, str):
                yield value, name, field, item
            elif isinstance(item, (dict, list)):
                yield from walk_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_records(item)


def apply_rows(rows):
    grouped = collections.defaultdict(list)
    for rel, name, field, text in rows:
        grouped[rel].append((name, field, text))

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    applied = 0
    for rel, changes in grouped.items():
        path = COMPLETE / rel
        if not path.exists():
            raise RuntimeError(f'missing complete file: {rel}')
        data = json.loads(path.read_text(encoding='utf-8'))
        shutil.copy2(path, BACKUP_DIR / rel.replace('/', '__'))
        for name, field, text in changes:
            matches = []
            for obj, obj_name, obj_field, old in walk_records(data):
                if obj_name == name and obj_field == field:
                    matches.append((obj, old))
            if len(matches) != 1:
                raise RuntimeError(f'{rel} | {name} | {field}: matches={len(matches)}')
            matches[0][0][field] = text
            applied += 1
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return applied


def add_verbs():
    data = json.loads(PLUGIN_JSON.read_text(encoding='utf-8'))
    entries = data['verbs']
    existing = {str(x['infinitive']).casefold() for x in entries}
    added = []
    for key in sorted(TRUE_PRESENT_VERBS):
        if key in existing:
            continue
        forms = NEW_FORMS.get(key)
        if not forms or len(forms) != 6:
            raise RuntimeError(f'no six-form set for {key}')
        entries.append({'infinitive': key, 'forms': forms})
        existing.add(key)
        added.append(key)
    data['_comment'] = (
        'Russian 6-form conjugations. Existing Russian keys and English aliases '
        'are retained. New present-tense Russian verb aliases from the '
        'reorganization chunks are also registered. Forms order: '
        '[1sg, 2sg, 3sg, 1pl, 2pl, 3pl].'
    )
    encoded = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    PLUGIN_JSON.write_text(encoded, encoding='utf-8')
    DEPLOY_JSON.write_text(encoded, encoding='utf-8')
    return added, len(entries)


def main():
    rows = []
    for path in sorted(UPLOADS.glob('reorganize_chunk_*_ru.txt')):
        rows.extend(parse_chunk(path))
    if len(rows) != 1044:
        raise RuntimeError(f'expected 1044 rows, got {len(rows)}')

    normalized = []
    changed = 0
    for rel, name, field, text in rows:
        new_text = normalize_text(text)
        if new_text != text:
            changed += 1
        normalized.append((rel, name, field, new_text))

    # Save normalized chunks for audit/reproducibility.
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    for index in (1, 2):
        part = normalized[(index - 1) * 522:index * 522]
        output = CHUNK_DIR / f'reorganize_chunk_{index:03d}_corrected.txt'
        with output.open('w', encoding='utf-8') as fh:
            for rel, name, field, text in part:
                fh.write(f'### {rel} | {name} | {field}\n{text}\n---\n')

    applied = apply_rows(normalized)
    added, total_verbs = add_verbs()
    print(json.dumps({
        'rows': len(rows),
        'normalized_rows': changed,
        'applied_to_complete': applied,
        'new_present_verbs_added': added,
        'verb_conjugation_entries': total_verbs,
        'backup_dir': str(BACKUP_DIR),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
