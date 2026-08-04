"""Apply translated strings from a chunk file back to translate/ JSON files.

Format expected (one line per entry):
  KEY | FIELD | <russian text>

If the line has only "KEY | FIELD" (no third column), it's skipped.
The script maps each entry to the source file by reverse-engineering the
KEY prefix (uses a lookup table).

It walks the translate/<file>.json, finds each record by strName, and
overwrites the listed field. If the record/field doesn't exist in the
translate file (i.e. was not yet created), it creates the field in place.

For files where the translate JSON does not exist, it copies the original
and applies translations on top.
"""
import os
import re
import json
import sys
import io
import shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ORIG_DIR = '/home/user/wspace/original'
TRANS_DIR = '/home/user/wspace/translate'

# Map file (chunk1 name -> source relpath) for chunk1
# chunk1 contains entries from these files:
CHUNK1_FILES = [
    'context/context.json',
    'jobitems/jobitems.json',
    'market/CoCollections/cocollections.json',
    'pledges/pledges.json',
    'pledges/pledges_crime_BCER.json',
    'racing/leagues/leagues.json',
    'racing/tracks/racetracks.json',
    'condowners/condowners_meat.json',
    'slots/slots.json',
    'slots/slots_wounds.json',
    'headlines/headlines.json',
    'cooverlays/cooverlays_datafiles.json',
    'installables/installables_dismantle.json',
]

CHUNK2_FILES = [
    'cooverlays/cooverlays_body.json',
    'cooverlays/cooverlays_clothes.json',
    'cooverlays/cooverlays_containers.json',
    'cooverlays/cooverlays_decor.json',
    'cooverlays/cooverlays_markets.json',
    'cooverlays/cooverlays_navmods.json',
    'cooverlays/cooverlays_plots.json',
    'cooverlays/cooverlays_traders.json',
    'cooverlays/cooverlays_walls.json',
    'condowners/condowners_mining.json',
    'condowners/condowners_navmods.json',
    'condowners/condowners_plots.json',
    'condowners/condowners_reactor.json',
    'condowners/condowners_wounds.json',
    'conditions/conditions_crime_BCER.json',
    'conditions/conditions_stakes.json',
    'conditions/conditions_stakes_follow.json',
    'market/Production/production_maps.json',
]


def load_json(path):
    with open(path, encoding='utf-8-sig') as f:
        text = f.read()
    text = re.sub(r'//[^\n]*', '', text)
    text = text.replace("\\'", "'")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        text2 = re.sub(r'\\(?![\"\\/bfnrtu])', '', text)
        return json.loads(text2, strict=False)


def save_json(path, data):
    """Save with same compact/pretty format: indent=2, ensure_ascii=False."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_chunk(path):
    """Parse chunk file -> list of (key, field, translation)."""
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip() or line.startswith('=') or line.startswith('---') or line.startswith('#') or line.startswith('Файл') or line.startswith('Правил') or line.startswith('-') or line.startswith('Применя') or line.startswith('Перед'):
                continue
            parts = line.split(' | ', 2)
            if len(parts) < 2:
                continue
            key, field = parts[0].strip(), parts[1].strip()
            trans = parts[2].strip() if len(parts) >= 3 else ''
            if not trans:
                continue
            out.append((key, field, trans))
    return out


def apply_to_file(rel, entries):
    """Apply entries to translate/<rel>.json. Returns (count_applied, count_missing)."""
    op = os.path.join(ORIG_DIR, rel)
    tp = os.path.join(TRANS_DIR, rel)
    if not os.path.exists(op):
        return 0, 0
    orig = load_json(op)
    if not os.path.exists(tp):
        # copy original to translate
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        trans = orig
    else:
        trans = load_json(tp)
    # normalize to list
    if isinstance(orig, dict):
        orig = [orig]
    if isinstance(trans, dict):
        trans = [trans]
    # build lookup by strName
    trans_by_name = {}
    for r in trans:
        if isinstance(r, dict) and 'strName' in r:
            trans_by_name[r['strName']] = r
    orig_by_name = {}
    for r in orig:
        if isinstance(r, dict) and 'strName' in r:
            orig_by_name[r['strName']] = r

    applied = 0
    missing = 0
    for key, field, trans_text in entries:
        if key not in orig_by_name:
            missing += 1
            continue
        if key not in trans_by_name:
            # create new record from orig
            new_rec = json.loads(json.dumps(orig_by_name[key]))  # deep copy
            trans_by_name[key] = new_rec
            trans.append(new_rec)
        rec = trans_by_name[key]
        if field in rec:
            rec[field] = trans_text
            applied += 1
        else:
            # add new field
            rec[field] = trans_text
            applied += 1

    save_json(tp, trans)
    return applied, missing


CHUNK3_FILES = [
    'cooverlays/cooverlays_floors.json',
    'conditions/conditions_plots.json',
    'headlines/headlines.json',
]

CHUNK4_FILES = [
    'installables/installables.json',
    'installables/installables_repair.json',
    'installables/installables_undamage.json',
    'headlines/headlines.json',
]


CHUNK5_FILES = [
    'interactions/interactions_autofactions.json',
    'interactions/interactions_debug.json',
    'interactions/interactions_honeypot.json',
    'interactions/interactions_qol.json',
    'interactions/interactions_relationships.json',
    'interactions/interactions_ship_to_ship.json',
    'interactions/interactions_slots.json',
    'interactions/interactions_slots_wield.json',
    'interactions/interactions_social_relationships.json',
    'interactions/interactions_stk_follow.json',
]


CHUNK6_FILES = [
    'interactions/plotIAs/interactions_plots.json',
]


CHUNK7_FILES = [
    'interactions/plotIAs/interactions_plots_3act.json',
    'interactions/plotIAs/interactions_plots_ceres_bc.json',
    'interactions/plotIAs/interactions_plots_ceres_p1.json',
    'interactions/plotIAs/interactions_plots_ceres_p2.json',
    'interactions/plotIAs/interactions_plots_ceres_p3.json',
    'interactions/plotIAs/interactions_plots_ceres_p4.json',
    'interactions/plotIAs/interactions_plots_ceres_p5.json',
    'interactions/plotIAs/interactions_plots_ceres_triggers.json',
]


CHUNK8_FILES = [
    'interactions/plotIAs/interactions_plots_meat.json',
    'interactions/plotIAs/interactions_plots_merga.json',
    'interactions/plotIAs/interactions_plots_whodunnit.json',
]


CHUNK9_FILES = [
    'tsv/output/stakes/conditions/conditions_STKMedHeistDissuade.json',
    'tsv/output/stakes/conditions/conditions_STKMedHeistPersuade.json',
    'tsv/output/stakes/conditions/conditions_STKShipSurrender_AIOffer.json',
    'tsv/output/stakes/conditions/conditions_STKShipSurrender_PlayerDemand.json',
    'tsv/output/stakes/conditions/conditions_STKShipSurrender_PlayerOffer.json',
    'tsv/output/stakes/conditions/conditions_STKStrangerMeet.json',
    'tsv/output/stakes/contexts/contexts_STKMedHeistDissuade.json',
    'tsv/output/stakes/contexts/contexts_STKMedHeistPersuade.json',
    'tsv/output/stakes/interactions/interactions_STKMedHeistDissuade.json',
    'tsv/output/stakes/interactions/interactions_STKMedHeistPersuade.json',
    'tsv/output/stakes/interactions/interactions_STKShipSurrender_AIDemand.json',
    'tsv/output/stakes/interactions/interactions_STKShipSurrender_AIOffer.json',
    'tsv/output/stakes/interactions/interactions_STKShipSurrender_PlayerDemand.json',
    'tsv/output/stakes/interactions/interactions_STKShipSurrender_PlayerOffer.json',
    'tsv/output/stakes/interactions/interactions_STKStrangerMeet.json',
]


CHUNK10_FILES = [
    'interactions/interactions_ship_to_ship.json',
    'interactions/interactions_relationships.json',
    'market/CoCollections/cocollections.json',
]


CHUNK11B_FILES = [
    'cooverlays/cooverlays_clothes.json',
    'cooverlays/cooverlays_decor.json',
    'cooverlays/cooverlays_navmods.json',
    'interactions/interactions_ship_to_ship.json',
    'interactions/plotIAs/interactions_plots.json',
    'interactions/plotIAs/interactions_plots_ceres_p2.json',
    'interactions/plotIAs/interactions_plots_meat.json',
    'market/CoCollections/cocollections.json',
    'tsv/output/stakes/conditions/conditions_STKMedHeistPersuade.json',
    'tsv/output/stakes/interactions/interactions_STKShipSurrender_PlayerDemand.json',
]


CHUNK12_FILES = [
    'interactions/plotIAs/interactions_plots.json',
    'interactions/plotIAs/interactions_plots_whodunnit.json',
    'interactions/plotIAs/interactions_plots_meat.json',
    'interactions/plotIAs/interactions_plots_ceres_p1.json',
    'interactions/plotIAs/interactions_plots_ceres_p2.json',
    'interactions/plotIAs/interactions_plots_merga.json',
    'interactions/interactions_relationships.json',
    'interactions/interactions_ship_to_ship.json',
    'cooverlays/cooverlays_floors.json',
    'cooverlays/cooverlays_traders.json',
    'cooverlays/cooverlays_markets.json',
    'cooverlays/cooverlays_plots.json',
    'cooverlays/cooverlays_navmods.json',
    'conditions/conditions_plots.json',
    'condowners/condowners_navmods.json',
    'tsv/output/stakes/interactions/interactions_STKShipSurrender_PlayerDemand.json',
    'market/CoCollections/cocollections.json',
]


def main():
    chunk_path = sys.argv[1] if len(sys.argv) > 1 else '/home/user/uploads/chunk1_ru.txt'
    files_arg = sys.argv[2] if len(sys.argv) > 2 else 'chunk1'
    if files_arg == 'chunk1':
        file_list = CHUNK1_FILES
    elif files_arg == 'chunk2':
        file_list = CHUNK2_FILES
    elif files_arg == 'chunk3':
        file_list = CHUNK3_FILES
    elif files_arg == 'chunk4':
        file_list = CHUNK4_FILES
    elif files_arg == 'chunk5':
        file_list = CHUNK5_FILES
    elif files_arg == 'chunk6':
        file_list = CHUNK6_FILES
    elif files_arg == 'chunk7':
        file_list = CHUNK7_FILES
    elif files_arg == 'chunk8':
        file_list = CHUNK8_FILES
    elif files_arg == 'chunk9':
        file_list = CHUNK9_FILES
    elif files_arg == 'chunk10':
        file_list = CHUNK10_FILES
    elif files_arg == 'chunk11a':
        file_list = CHUNK11A_FILES
    elif files_arg == 'chunk11b':
        file_list = CHUNK11B_FILES
    elif files_arg == 'chunk12':
        file_list = CHUNK12_FILES
    else:
        # interpret as comma-separated rel paths
        file_list = files_arg.split(',')

    entries = parse_chunk(chunk_path)
    print(f'Parsed {len(entries)} translated entries from {chunk_path}')

    # Group entries by source file. We don't know the source file from the
    # entry itself (just KEY + FIELD). So we need to look up: for each entry,
    # which file contains a record with strName=KEY and field=FIELD.
    # Build a global index.
    print('Building global index...')
    file_to_entries = {f: [] for f in file_list}
    file_unmatched = []
    for key, field, trans_text in entries:
        matched = False
        for f in file_list:
            op = os.path.join(ORIG_DIR, f)
            if not os.path.exists(op):
                continue
            data = load_json(op)
            if isinstance(data, dict):
                data = [data]
            for rec in data:
                if isinstance(rec, dict) and rec.get('strName') == key and field in rec:
                    file_to_entries[f].append((key, field, trans_text))
                    matched = True
                    break
            if matched:
                break
        if not matched:
            file_unmatched.append((key, field, trans_text))

    print(f'Unmatched entries (no source found): {len(file_unmatched)}')
    for k, f, t in file_unmatched[:5]:
        print(f'  {k} | {f} | {t}')

    total_applied = 0
    for f, e_list in file_to_entries.items():
        if not e_list:
            continue
        applied, missing = apply_to_file(f, e_list)
        total_applied += applied
        print(f'  {f}: {applied} applied, {missing} missing (orig)')

    print(f'Total applied: {total_applied}')


if __name__ == '__main__':
    main()
