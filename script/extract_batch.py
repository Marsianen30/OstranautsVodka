"""Extract untranslated strings from a list of files.

For each file in FILE_LIST, walks the JSON and collects string values
where original (English) is ascii and translate (existing Russian)
differs/is missing.

Saves to /home/user/wspace/work/extract/<relpath>.txt with one entry per line:
  KEY | FIELD | "value"

For apply, see apply_batch.py.
"""
import re
import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ORIG_DIR = '/home/user/wspace/original'
TRANS_DIR = '/home/user/wspace/translate'
OUT_DIR = '/home/user/wspace/work/extract'

# Fields to extract per file. None = all string fields whose value is ascii
# and differs in source vs target.
# Mapping: relpath -> {record_key: [(field_name, ...)]}
# If record_key == '*' means "any record"
# If field list empty, extract all string fields

# All entries are (field, mode) where mode in {'always', 'if_diff'}
# 'always' = extract from original even if no translate file (translate == original)
# 'if_diff' = extract only where original != translate (means missing in translate)

# We just collect: for each record (matched by strName), for each listed field,
# if the value in original differs from translate OR translate is missing,
# emit it. Single source of truth: original.

# How to match records between orig and trans: by strName.

# If file is missing in translate, treat as all-untranslated.
# If file is missing in original, skip.

# Special: if a record has no strName (e.g. flat aValues in conditions_simple),
# we match by position.

# For cooverlays_datafiles.json, we keep strNameFriendly untranslated.

EXTRACTION_CONFIG = {
    # relpath -> {mode, fields, special}
    'conditions/conditions_crime_BCER.json': {'fields': ['strNameFriendly', 'strDesc']},
    'conditions/conditions_plots.json': {'fields': ['strNameFriendly', 'strDesc']},
    'conditions/conditions_stakes.json': {'fields': ['strNameFriendly', 'strDesc']},
    'conditions/conditions_stakes_follow.json': {'fields': ['strNameFriendly', 'strDesc']},
    'condowners/condowners_meat.json': {'fields': ['strNameShort', 'strNameFriendly', 'strDesc']},
    'condowners/condowners_mining.json': {'fields': ['strNameShort', 'strNameFriendly', 'strDesc']},
    'condowners/condowners_navmods.json': {'fields': ['strNameShort', 'strNameFriendly', 'strDesc']},
    'condowners/condowners_plots.json': {'fields': ['strNameShort', 'strNameFriendly', 'strDesc']},
    'condowners/condowners_reactor.json': {'fields': ['strNameShort', 'strNameFriendly', 'strDesc']},
    'condowners/condowners_wounds.json': {'fields': ['strNameShort', 'strNameFriendly', 'strDesc']},
    'context/context.json': {'fields': ['strTitle', 'strMainText']},
    'cooverlays/cooverlays_body.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_clothes.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_containers.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_datafiles.json': {'fields': ['strDesc'], 'skip_strNameFriendly': True},
    'cooverlays/cooverlays_decor.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_floors.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_markets.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_navmods.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_plots.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_traders.json': {'fields': ['strNameFriendly', 'strDesc']},
    'cooverlays/cooverlays_walls.json': {'fields': ['strNameFriendly', 'strDesc']},
    'headlines/headlines.json': {'fields': ['strDesc']},
    'installables/installables.json': {'fields': ['strTooltip']},
    'installables/installables_dismantle.json': {'fields': ['strTooltip']},
    'installables/installables_repair.json': {'fields': ['strTooltip']},
    'installables/installables_undamage.json': {'fields': ['strTooltip']},
    'jobitems/jobitems.json': {'fields': ['strFriendlyName']},
    'market/CoCollections/cocollections.json': {'fields': ['strFriendlyName']},
    'market/Production/production_maps.json': {'fields': ['strFriendlyDescription']},
    'pledges/pledges.json': {'fields': ['strNameFriendly']},
    'pledges/pledges_crime_BCER.json': {'fields': ['strNameFriendly']},
    'racing/leagues/leagues.json': {'fields': ['strNameFriendly', 'strDescription', 'strRequirementDescription']},
    'racing/tracks/racetracks.json': {'fields': ['strNameFriendly', 'strDescription']},
    'slots/slots.json': {'fields': ['strNameFriendly']},
    'slots/slots_wounds.json': {'fields': ['strNameFriendly']},
    # interactions - complex
    'interactions/interactions_autofactions.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_debug.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_honeypot.json': {'fields': ['strTitle', 'strDesc', 'strTooltip']},
    'interactions/interactions_qol.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_relationships.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_ship_to_ship.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_slots.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_slots_wield.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_social_relationships.json': {'fields': ['strTitle', 'strDesc']},
    'interactions/interactions_stk_follow.json': {'fields': ['strTitle', 'strDesc']},
}


def load_json(path):
    """Load JSON, strip // comments. Lenient about escapes."""
    with open(path, encoding='utf-8-sig') as f:
        text = f.read()
    text = re.sub(r'//[^\n]*', '', text)
    # fix \' -> ' (game uses non-standard escaping)
    text = text.replace("\\'", "'")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        # last resort: skip bad escapes via aggressive replace
        text2 = re.sub(r'\\(?![\"\\/bfnrtu])', '', text)
        return json.loads(text2, strict=False)


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def extract_one(rel, cfg):
    """Extract untranslated strings from a single file."""
    op = os.path.join(ORIG_DIR, rel)
    tp = os.path.join(TRANS_DIR, rel)
    if not os.path.exists(op):
        return []
    orig = load_json(op)
    trans = load_json(tp) if os.path.exists(tp) else None

    # Build translate lookup by strName
    if isinstance(orig, list):
        orig_list = orig
    else:
        orig_list = [orig]
    if trans is not None and isinstance(trans, list):
        trans_list = trans
    elif trans is not None:
        trans_list = [trans]
    else:
        trans_list = [None] * len(orig_list)

    trans_by_name = {}
    for r in trans_list:
        if isinstance(r, dict) and 'strName' in r:
            trans_by_name[r['strName']] = r

    fields = cfg.get('fields', [])
    skip_friendly = cfg.get('skip_strNameFriendly', False)
    out_lines = []
    for rec in orig_list:
        if not isinstance(rec, dict):
            continue
        key = rec.get('strName', '?')
        t_rec = trans_by_name.get(key)
        for fld in fields:
            if skip_friendly and fld == 'strNameFriendly':
                continue
            v = rec.get(fld)
            if not v or not isinstance(v, str):
                continue
            # only extract if ascii (English) and not yet translated
            if not is_ascii(v):
                continue
            t_v = t_rec.get(fld) if t_rec else None
            if t_v and not is_ascii(t_v):
                # already translated
                continue
            out_lines.append(f'{key} | {fld} | {v}')
    return out_lines


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    for rel, cfg in EXTRACTION_CONFIG.items():
        lines = extract_one(rel, cfg)
        out_path = os.path.join(OUT_DIR, rel.replace('/', '__') + '.txt')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n' if lines else '')
        print(f'  {rel}: {len(lines)} entries -> {out_path}')

    # Also handle plotIAs (same as interactions)
    plotIAs_dir = os.path.join(ORIG_DIR, 'interactions/plotIAs')
    for name in os.listdir(plotIAs_dir):
        rel = f'interactions/plotIAs/{name}'
        cfg = {'fields': ['strTitle', 'strDesc']}
        lines = extract_one(rel, cfg)
        out_path = os.path.join(OUT_DIR, rel.replace('/', '__') + '.txt')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n' if lines else '')
        print(f'  {rel}: {len(lines)} entries')

    # tsv
    for sd in os.listdir(os.path.join(ORIG_DIR, 'tsv/output/stakes/')):
        sub = f'tsv/output/stakes/{sd}'
        for name in os.listdir(os.path.join(ORIG_DIR, sub)):
            rel = f'{sub}/{name}'
            # try to detect fields
            op = os.path.join(ORIG_DIR, rel)
            with open(op, encoding='utf-8-sig') as f:
                text = re.sub(r'//[^\n]*', '', f.read())
            text = text.replace("\\'", "'")
            try:
                rec = json.loads(text)[0] if isinstance(json.loads(text), list) else json.loads(text)
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue
            # guess fields: pick text-y ones
            guess = []
            for k in ('strTitle', 'strDesc', 'strNameFriendly', 'strFriendlyName', 'strTooltip', 'strDescription', 'strMainText', 'strRequirementDescription', 'strFriendlyDescription'):
                if k in rec and isinstance(rec[k], str):
                    guess.append(k)
            if not guess:
                continue
            cfg = {'fields': guess}
            lines = extract_one(rel, cfg)
            out_path = os.path.join(OUT_DIR, rel.replace('/', '__') + '.txt')
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n' if lines else '')
            print(f'  {rel}: {len(lines)} entries')


if __name__ == '__main__':
    main()
