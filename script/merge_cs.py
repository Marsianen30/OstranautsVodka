"""Merge original conditions_simple.json with existing translate, translate 13 new keys."""
import re
import json
import sys
import io

# Force utf-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_orig(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'//[^\n]*', '', text)
    return json.loads(text)

orig = load_orig('/home/user/wspace/original/conditions_simple/conditions_simple.json')
trans_old = load_orig('/home/user/wspace/translate/conditions_simple/conditions_simple.json')

orig_av = orig[0]['aValues']
old_av = trans_old[0]['aValues']
old_recs = [old_av[i*7:(i+1)*7] for i in range(len(old_av)//7)]
old_map = {r[0]: r for r in old_recs}

# Translations to apply for the 13 new keys
# desc only — names are brand/ID, kept as-is
NEW_TRANSLATIONS = {
    'IsDebug15-0-38Fixed': 'Это сохранение получило исправление проблем с картой станции, действующее до версии 0.15.0.38.',
    'IsJOBMVPCourierTestClient': '[us] [is] клиентом, предлагающим задание курьера.',
    'IsJOBMVPCourierTarget': '[us] [is] целью в задании курьера.',
    'IsJOBMVPCourierLockerTarget': '[us] [is] целью в задании курьера-локера.',
    'IsJOBMVPTestClient': '[us] [is] клиентом, предлагающим разведывательное задание.',
    'IsJOBMVPTest01Agent': '[us] [is] агентом, выполняющим разведывательное задание.',
    'IsJOBMVPTest01Client': '[us] [is] клиентом, предлагающим разведывательное задание.',
    'IsJOBMVPTest01Target': '[us] [is] целью разведывательного задания.',
    'IsJOBHeavy1Client': '[us] [is] клиентом, предлагающим тяжёлое задание.',
    'IsJOBDeadBody1Client': '[us] [is] клиентом, предлагающим задание с телом.',
    'IsJOBMVPHoneypotClient': '[us] [is] клиентом, предлагающим задание-приманку.',
    'IsJOBMVPPowerItemClient': '[us] [is] клиентом, предлагающим задание с энергоблоком.',
    'StationHasGrav': '[us] [is] станцией, всегда использующей гравитацию ближайших планет.',
}

# Walk orig in order, building new aValues
n = len(orig_av) // 7
new_av = []
for i in range(n):
    rec = orig_av[i*7:(i+1)*7]
    key = rec[0]
    if key in old_map:
        # use existing translation (desc is already in russian)
        new_av.extend(old_map[key])
    elif key in NEW_TRANSLATIONS:
        # translate desc, keep name from orig
        r = list(rec)
        r[2] = NEW_TRANSLATIONS[key]
        new_av.extend(r)
    else:
        # missing translation? keep original
        print(f'WARN: key {key} not in old_map and not in NEW_TRANSLATIONS — keeping orig')
        new_av.extend(rec)

# Build output preserving the "Simple Conditions" wrapper
# We need to be careful about trailing 6-element record mentioned in summary
# Let's verify lengths
print(f'orig recs: {n}, new_av len: {len(new_av)}, expected: {n*7}')

out = [{
    'strName': 'Simple Conditions',
    'aValues': new_av
}]

# Write with same formatting as original: tab indent, no indent for aValues strings
# We'll write pretty JSON
out_path = '/home/user/wspace/translate/conditions_simple/conditions_simple.json'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('[\n')
    f.write('  {\n')
    f.write('    "strName" : "Simple Conditions",\n')
    f.write('    "aValues" : [\n')
    for idx, item in enumerate(new_av):
        # strings get quoted
        s = json.dumps(item, ensure_ascii=False)
        comma = ',' if idx < len(new_av) - 1 else ''
        f.write('      ' + s + comma + '\n')
    f.write('    ]\n')
    f.write('  }\n')
    f.write(']\n')

print('Wrote:', out_path)
print('File size:', __import__('os').path.getsize(out_path), 'bytes')
