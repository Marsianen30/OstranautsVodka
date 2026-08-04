#!/usr/bin/env python3
"""
Скрипт для применения перевода из small_untranslated_ru.txt обратно к JSON-файлам.
Формат входного файла:
  ### file_path | strName | field
  translated text
  ---

Применяет перевод к полю field в объекте strName в файле file_path.
"""
import json, re, os, sys

# Только эти поля (согласно правилам пользователя)
TRANSLATABLE = {'strTitle', 'strDesc', 'strNameFriendly', 'strTooltip'}

def parse_translation_file(path):
    """Парсит файл перевода в список (file, strName, field, text)"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Разделяем по '---'
    chunks = content.split('---')
    rows = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk: continue
        lines = chunk.split('\n')
        if not lines: continue
        # Первая строка — заголовок
        header = lines[0]
        if not header.startswith('### '): continue
        m = re.match(r'###\s+(\S+)\s+\|\s+(\S+)\s+\|\s+(\S+)\s*$', header)
        if not m:
            print(f'WARN: bad header: {header}')
            continue
        file_path, str_name, field = m.group(1), m.group(2), m.group(3)
        if field not in TRANSLATABLE:
            print(f'WARN: field {field} not translatable')
            continue
        text = '\n'.join(lines[1:]).strip()
        rows.append((file_path, str_name, field, text))
    return rows

def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else 'translated'
    trans_file = sys.argv[2] if len(sys.argv) > 2 else 'small_untranslated_ru.txt'

    rows = parse_translation_file(trans_file)
    print(f'Loaded {len(rows)} translation rows')

    # Группируем по файлу
    by_file = {}
    for file_path, str_name, field, text in rows:
        by_file.setdefault(file_path, []).append((str_name, field, text))

    # Применяем к каждому файлу
    for file_path, changes in by_file.items():
        full_path = os.path.join(src_dir, file_path)
        if not os.path.exists(full_path):
            print(f'WARN: file not found: {full_path}')
            continue
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        n_applied = 0
        n_missing = 0
        def apply_to_obj(obj, name, field, text):
            nonlocal n_applied, n_missing
            if not isinstance(obj, dict): return
            obj_name = obj.get('strName')
            if obj_name == name:
                if field in obj:
                    obj[field] = text
                    n_applied += 1
                else:
                    n_missing += 1

        def walk(obj, file_path):
            if isinstance(obj, list):
                for x in obj:
                    walk(x, file_path)
            elif isinstance(obj, dict):
                for n, fld, txt in changes:
                    apply_to_obj(obj, n, fld, txt)
                # Recurse
                for v in obj.values():
                    if isinstance(v, (list, dict)):
                        walk(v, file_path)
        walk(data, file_path)

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'  {file_path}: applied {n_applied}, missing {n_missing}')

if __name__ == '__main__':
    main()
