"""Apply verbs.json translation: replace [en_singular] -> [ru_singular] in
all 35 complete/ JSON files via direct text replacement (preserves formatting
and comments). The token appears inside JSON strings like
  "strDesc" : "[us] [bashes] [them].",
and the regex [a-z][a-z\\-\\']* picks up the verb name only.

Preserves all non-verb tokens (pronouns/reflexives like us, them, us-pos,
us-subj, them-obj, them-subj, them-pos, them-shipfriendly, us-obj, us-shouts,
us-turns, us-reflexive, is-pos, itm, object, purple, x, etc.)
"""
import re
import os
import sys
import io
import shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

VERBS_ORIG = '/home/user/wspace/original/tokens/verbs.json'
VERBS_TRANS = '/home/user/wspace/translate/tokens/verbs.json'
COMPLETE_DIR = '/home/user/wspace/complete'
BACKUP_DIR = '/home/user/wspace/work/complete_backup_verbs'

PRESERVE = {
    'us', 'them',
    'is-pos', 'us-pos', 'us-reflexive',
    'them-obj', 'them-pos', 'them-shipfriendly', 'them-subj',
    'us-obj', 'us-shouts', 'us-subj', 'us-turns',
    'itm', 'object', 'purple', 'x',
    # "is" and "has" are themselves verbs in verbs.json. We replace them too.
}


def build_mapping():
    import json
    with open(VERBS_ORIG) as f:
        text = re.sub(r'//[^\n]*', '', f.read())
    orig = json.loads(text)
    with open(VERBS_TRANS) as f:
        text = re.sub(r'//[^\n]*', '', f.read())
    trans = json.loads(text)
    o_t = orig[0]['tokens2']
    t_t = trans[0]['tokens2']
    mapping = {}
    for i in range(len(o_t)):
        if not o_t[i] or not o_t[i][0]:
            continue
        if not t_t[i] or not t_t[i][0]:
            continue
        en = o_t[i][0]
        ru = t_t[i][0]
        if en and ru and en != ru:
            mapping[en] = ru
    return mapping


def process_text(text, mapping):
    """Replace [en] -> [ru] for en in mapping, leave preserve alone.
    Only replaces inside double-quoted string values: matches
    "..." that contains [...] verb tokens.
    """
    # Find all string values via simple state machine
    out = []
    i = 0
    n = len(text)
    changes = 0
    while i < n:
        c = text[i]
        if c == '"':
            # find matching close quote (no escapes for now; this is enough for game data)
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == '\\' and j + 1 < n:
                    j += 2
                else:
                    j += 1
            # text[i+1:j] is the string value
            inner = text[i+1:j]
            new_inner = inner
            for m in re.finditer(r'\[([a-z][a-z\-\']*)\]', inner):
                tok = m.group(1)
                if tok in PRESERVE:
                    continue
                if tok in mapping:
                    ru = mapping[tok]
                    # Replace just this match
                    new_inner = new_inner.replace(f'[{tok}]', f'[{ru}]', 1)
                    changes += 1
            out.append(text[i])
            out.append(new_inner)
            out.append('"')
            i = j + 1
        else:
            out.append(c)
            i += 1
    return ''.join(out), changes


def main():
    print('Backing up...')
    if os.path.isdir(BACKUP_DIR):
        shutil.rmtree(BACKUP_DIR)
    shutil.copytree(COMPLETE_DIR, BACKUP_DIR)
    print('  Backup at', BACKUP_DIR)

    print('Building mapping...')
    mapping = build_mapping()
    print(f'  {len(mapping)} verbs mapped')

    total_files = 0
    total_files_changed = 0
    total_changes = 0
    for root, dirs, files in os.walk(COMPLETE_DIR):
        for name in files:
            if not name.endswith('.json'):
                continue
            path = os.path.join(root, name)
            if path.endswith('/tokens/verbs.json'):
                continue
            total_files += 1
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read()
            new_txt, changes = process_text(txt, mapping)
            if changes:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_txt)
                total_files_changed += 1
                total_changes += changes
                print(f'  {os.path.relpath(path, COMPLETE_DIR)}: {changes}')

    print(f'\\nFiles: {total_files}, changed: {total_files_changed}, total replacements: {total_changes}')


if __name__ == '__main__':
    main()
