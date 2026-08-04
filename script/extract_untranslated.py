#!/usr/bin/env python3
"""
Скрипт для извлечения непереведённых строк из "переведённых" файлов.
Используется для доделывания перевода.
"""
import json, re, os, sys
from collections import defaultdict

# Поля для перевода (согласно правилам пользователя)
TRANSLATABLE = {'strTitle', 'strDesc', 'strNameFriendly', 'strTooltip'}

def is_english(s):
    """Считаем строку непереведённой, если в ней только ASCII и нет кириллицы"""
    if not s or not isinstance(s, str): return False
    s = s.strip()
    if len(s) < 2: return False
    if any('А' <= c <= 'я' or 'Ё' <= c <= 'ё' for c in s): return False
    if not re.search(r'[a-zA-Z]', s): return False
    return True

def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else 'translated'
    out_file = sys.argv[2] if len(sys.argv) > 2 else 'untranslated_to_translate.txt'
    target_files = sys.argv[3:] if len(sys.argv) > 3 else None

    rows = []  # (file, strName, field, text, idx)
    for root, dirs, files in os.walk(src_dir):
        for fn in files:
            if not fn.endswith('.json'): continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, src_dir)
            if target_files and rel not in target_files: continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                continue

            def walk(obj, file_path):
                if isinstance(obj, list):
                    for i, x in enumerate(obj):
                        if isinstance(x, dict):
                            name = x.get('strName', f'idx{i}')
                            for fld in TRANSLATABLE:
                                v = x.get(fld)
                                if is_english(v):
                                    rows.append((file_path, name, fld, v, i))
                elif isinstance(obj, dict):
                    name = obj.get('strName', '?')
                    for fld in TRANSLATABLE:
                        v = obj.get(fld)
                        if is_english(v):
                            rows.append((file_path, name, fld, v, 0))
            walk(data, rel)

    # Запишем в файл
    with open(out_file, 'w', encoding='utf-8') as f:
        for file_path, name, fld, text, idx in rows:
            f.write(f'### {file_path} | {name} | {fld}\n')
            f.write(f'{text}\n')
            f.write('---\n')
    print(f'Wrote {len(rows)} rows to {out_file}')

if __name__ == '__main__':
    main()
