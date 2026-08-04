#!/usr/bin/env python3
r"""
Inject translated strings back into Ostranauts mod JSON files.

Takes a JSON file with translations and writes them into the
corresponding mod data files.

Usage:
    python inject_translations.py --translated translated.json
    python inject_translations.py -t translated.json -m ".\src\ostranautsRu\data" -c
"""

import argparse
import json
import os
import re
import sys
from copy import deepcopy
from typing import Any

from json_utils import load_json_file, save_json_file


TRANSLATABLE_FIELDS = frozenset({"strNameFriendly", "strNameShort", "strDesc", "strTitle"})
SPECIAL_FILES = {"strings.json", "conditions_simple.json"}



def inject_standard(filepath: str, translations: list) -> int:
    """
    Вставляет переводы в стандартный JSON-файл (массив объектов).
    Сопоставление по strName.
    Возвращает количество вставленных переводов.
    """
    if not os.path.exists(filepath):
        print(f"  [WARN] Mod file not found, skipping: {filepath}")
        return 0

    data = load_json_file(filepath)
    if not isinstance(data, list):
        print(f"  [WARN] Not a list: {filepath}")
        return 0

    # Строим индекс по strName
    index = {}
    for i, item in enumerate(data):
        if isinstance(item, dict) and "strName" in item:
            index[item["strName"]] = i

    injected = 0
    for entry in translations:
        name = entry.get("strName")
        if not name:
            continue
        if name not in index:
            print(f"  [WARN] strName '{name}' not found in {filepath}")
            continue

        idx = index[name]
        item = data[idx]

        for field in TRANSLATABLE_FIELDS:
            translation = entry.get(field)
            if translation and isinstance(translation, str) and translation.strip():
                # Записываем перевод (создаём поле если его не было)
                item[field] = translation
                injected += 1

    save_json_file(filepath, data)
    return injected


def inject_strings_format(filepath: str, translations: list) -> int:
    """
    Вставляет переводы в strings.json (формат aValues).
    Каждый элемент translations имеет: key, original, translation.
    """
    if not os.path.exists(filepath):
        print(f"  [WARN] Mod file not found, skipping: {filepath}")
        return 0

    data = load_json_file(filepath)
    if not isinstance(data, list) or len(data) == 0:
        print(f"  [WARN] Bad structure: {filepath}")
        return 0

    obj = data[0]
    if not isinstance(obj, dict) or "aValues" not in obj:
        print(f"  [WARN] No aValues in: {filepath}")
        return 0

    values = obj["aValues"]

    # Строим индекс ключ -> позиция в массиве
    key_index = {}
    i = 0
    while i + 1 < len(values):
        key = str(values[i]).strip()
        key_index[key] = i
        i += 2

    injected = 0
    for entry in translations:
        key = entry.get("key")
        translation = entry.get("translation")
        if not key or not translation or not translation.strip():
            continue
        if key not in key_index:
            print(f"  [WARN] Key '{key}' not found in {filepath}")
            continue
        pos = key_index[key] + 1  # значение идёт сразу после ключа
        values[pos] = translation
        injected += 1

    obj["aValues"] = values
    data[0] = obj
    save_json_file(filepath, data)
    return injected


def main():
    parser = argparse.ArgumentParser(
        description="Inject translated strings back into Ostranauts mod files",
    )
    parser.add_argument("--translated", "-t", required=True,
                        help="JSON file with translations (output from translator agent)")
    parser.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data",
                        help="Path to mod data folder")
    parser.add_argument("--game-path", "-g", default=None,
                        help="Optional: game data path to copy original file structure for new files")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview changes without writing files")
    parser.add_argument("--create-missing", "-c", action="store_true",
                        help="Create mod files from game originals if they don't exist yet")

    args = parser.parse_args()

    if not os.path.exists(args.translated):
        print(f"ERROR: translated file not found: {args.translated}", file=sys.stderr)
        sys.exit(1)

    with open(args.translated, "r", encoding="utf-8") as f:
        translated_data = json.load(f)

    files = translated_data.get("files", {})
    if not files:
        print("No 'files' key found in translated JSON. Trying direct format...")
        # Может быть просто { "file/path.json": [...] }
        files = {k: v for k, v in translated_data.items() if not k.startswith("_")}

    print(f"Mod path: {args.mod_path}")
    print(f"Files to process: {len(files)}")
    if args.dry_run:
        print("[DRY RUN MODE - no files will be written]")
    print()

    total_injected = 0
    total_entries = 0

    for file_rel, translations in sorted(files.items()):
        if not translations:
            continue

        mod_file = os.path.join(args.mod_path, file_rel)
        filename = os.path.basename(file_rel)
        total_entries += len(translations)

        # Если мод-файла нет, но есть game-path, можем создать его из оригинала
        if not os.path.exists(mod_file) and args.create_missing and args.game_path:
            game_file = os.path.join(args.game_path, file_rel)
            if os.path.exists(game_file):
                print(f"  [NEW] Creating mod file from game: {file_rel}")
                game_data = load_json_file(game_file)
                os.makedirs(os.path.dirname(mod_file), exist_ok=True)
                save_json_file(mod_file, game_data)
            else:
                print(f"  [SKIP] No source to create: {file_rel}")
                continue

        if not os.path.exists(mod_file):
            print(f"  [SKIP] Mod file not found: {file_rel}")
            continue

        print(f"  {file_rel}: {len(translations)} entries...", end=" ")

        if args.dry_run:
            print("(dry run)")
            continue

        if filename in SPECIAL_FILES:
            injected = inject_strings_format(mod_file, translations)
        else:
            injected = inject_standard(mod_file, translations)

        total_injected += injected
        print(f"{injected} fields injected")

    print()
    print("=" * 60)
    print(f"  Files processed:  {len(files)}")
    print(f"  Entries in input: {total_entries}")
    print(f"  Fields injected:  {total_injected}")
    if args.dry_run:
        print("  [DRY RUN] No files were modified")
    print("=" * 60)


if __name__ == "__main__":
    main()
