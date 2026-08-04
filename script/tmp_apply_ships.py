import sys, glob, os, io, json
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file
sys.path.insert(0, 'script')
from tmp_ships_translations import TR

files = sorted(glob.glob('D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/ships/*.json'))
OUTDIR = 'ostranautsRuNss/data/ships'
os.makedirs(OUTDIR, exist_ok=True)

# rebuild same unique-text order as tmp_ships_unique.py to map index->text
seen = {}
order = []
for f in files:
    g = load_json_file(f)
    d = g[0].get('description') if isinstance(g, list) else g.get('description')
    if d and len(d.split()) > 3:
        if d not in seen:
            seen[d] = []
            order.append(d)
        seen[d].append(os.path.basename(f))

assert len(order) == len(TR), (len(order), len(TR))
text_to_ru = {order[i]: TR[i] for i in range(len(order))}

written = 0
skipped_notext = 0
for f in files:
    g = load_json_file(f)
    base = os.path.basename(f)
    d = g[0].get('description') if isinstance(g, list) else g.get('description')
    if d and len(d.split()) > 3:
        ru = text_to_ru[d]
        if isinstance(g, list):
            g[0]['description'] = ru
        else:
            g['description'] = ru
        out_path = os.path.join(OUTDIR, base)
        json.dump(g, io.open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        written += 1
    else:
        skipped_notext += 1

print('written_with_translation', written, 'skipped_no_text', skipped_notext, 'total', len(files))
