#!/usr/bin/env python3
r"""
Extract untranslated strings from Ostranauts game JSON files.

Compares original game files with already-translated mod files,
finds strings not yet translated, and saves them to a JSON file
for subsequent translation.

Usage:
    python extract_untranslated.py --game-path "C:\...\StreamingAssets\data"
    python extract_untranslated.py -g "C:\...\data" -m ".\src\ostranautsRu\data" -o out.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from json_utils import load_json_file, resolve_data_path

TRANSLATABLE_FIELDS = frozenset({"strNameFriendly", "strNameShort", "strDesc", "strTitle"})
SPECIAL_FILES = {"strings.json", "conditions_simple.json"}
SKIP_DIRS = {"schemas"}
SKIP_FILES_PATTERNS = {"verbs.json"}


def contains_russian(text: str) -> bool:
    return bool(re.search(r"[а-яА-ЯёЁ]", text))


def is_translatable_value(value: str) -> bool:
    if not value or not value.strip():
        return False
    stripped = value.strip()
    if all(c in "=-_" for c in stripped):
        return False
    if re.match(r"^(GUI_|AI_|ATC_|ERROR_|COMBAT_|CREW_|COMMS_|DAMAGE_|COLOR_|AUTOPAUSE_|BUG_)", stripped):
        return False
    return True



def extract_standard_translations(data: list) -> dict:
    result = {}
    if not isinstance(data, list):
        return result
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("strName")
        if not name:
            continue
        translations = {}
        for field in TRANSLATABLE_FIELDS:
            if field in item:
                val = item[field]
                if isinstance(val, str) and is_translatable_value(val) and contains_russian(val):
                    translations[field] = val
        if translations:
            result[name] = translations
    return result


def extract_strings_translations(data: list) -> dict:
    result = {}
    if not isinstance(data, list) or len(data) == 0:
        return result
    obj = data[0]
    if not isinstance(obj, dict) or "aValues" not in obj:
        return result
    values = obj["aValues"]
    i = 0
    while i + 1 < len(values):
        key = str(values[i]).strip()
        value = str(values[i + 1]).strip() if values[i + 1] is not None else ""
        if contains_russian(value) and is_translatable_value(value):
            result[key] = value
        i += 2
    return result


def extract_standard_untranslated(game_data: list, mod_translations: dict) -> list:
    untranslated = []
    if not isinstance(game_data, list):
        return untranslated
    for item in game_data:
        if not isinstance(item, dict):
            continue
        name = item.get("strName")
        if not name:
            continue
        missing_fields = {}
        for field in TRANSLATABLE_FIELDS:
            if field in item:
                val = item[field]
                if isinstance(val, str) and is_translatable_value(val):
                    if name not in mod_translations or field not in mod_translations[name]:
                        missing_fields[field] = val
        if missing_fields:
            entry = {"strName": name}
            entry.update(missing_fields)
            if name in mod_translations:
                entry["_existing"] = mod_translations[name]
            untranslated.append(entry)
    return untranslated


def extract_strings_untranslated(game_data: list, mod_translations: dict) -> list:
    untranslated = []
    if not isinstance(game_data, list) or len(game_data) == 0:
        return untranslated
    obj = game_data[0]
    if not isinstance(obj, dict) or "aValues" not in obj:
        return untranslated
    values = obj["aValues"]
    i = 0
    while i + 1 < len(values):
        key = str(values[i]).strip()
        value = str(values[i + 1]).strip() if values[i + 1] is not None else ""
        if is_translatable_value(value) and key not in mod_translations:
            untranslated.append({"key": key, "original": value})
        i += 2
    return untranslated


def count_standard_strings(game_data: list, mod_translations: dict) -> tuple:
    total = 0
    translated = 0
    if not isinstance(game_data, list):
        return 0, 0
    for item in game_data:
        if not isinstance(item, dict):
            continue
        name = item.get("strName")
        if not name:
            continue
        for field in TRANSLATABLE_FIELDS:
            if field in item:
                val = item[field]
                if isinstance(val, str) and is_translatable_value(val):
                    total += 1
                    if name in mod_translations and field in mod_translations[name]:
                        translated += 1
    return total, translated


def count_strings_strings(game_data: list, mod_translations: dict) -> tuple:
    total = 0
    translated = 0
    if not isinstance(game_data, list) or len(game_data) == 0:
        return 0, 0
    obj = game_data[0]
    if not isinstance(obj, dict) or "aValues" not in obj:
        return 0, 0
    values = obj["aValues"]
    i = 0
    while i + 1 < len(values):
        key = str(values[i]).strip()
        value = str(values[i + 1]).strip() if values[i + 1] is not None else ""
        if is_translatable_value(value):
            total += 1
            if key in mod_translations:
                translated += 1
        i += 2
    return total, translated


def process_file(game_path: str, mod_path: str, rel_path: str, filename: str) -> dict:
    game_file = os.path.join(game_path, rel_path, filename)
    mod_file = os.path.join(mod_path, rel_path, filename)

    result = {
        "file": os.path.join(rel_path, filename) if rel_path else filename,
        "type": "standard",
        "total": 0,
        "translated": 0,
        "untranslated": [],
    }

    try:
        game_data = load_json_file(game_file)
    except Exception as e:
        result["error"] = f"read error: {e}"
        return result

    is_special = filename in SPECIAL_FILES
    mod_std = {}
    mod_str = {}

    if os.path.exists(mod_file):
        try:
            mod_data = load_json_file(mod_file)
            if is_special:
                mod_str = extract_strings_translations(mod_data)
            else:
                mod_std = extract_standard_translations(mod_data)
        except Exception:
            pass

    if is_special:
        result["type"] = "strings_format"
        total, translated = count_strings_strings(game_data, mod_str)
        result["total"] = total
        result["translated"] = translated
        result["untranslated"] = extract_strings_untranslated(game_data, mod_str)
    else:
        total, translated = count_standard_strings(game_data, mod_std)
        result["total"] = total
        result["translated"] = translated
        result["untranslated"] = extract_standard_untranslated(game_data, mod_std)

    return result


def walk_game_data(game_path: str) -> list:
    files = []
    for root, dirs, filenames in os.walk(game_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, game_path)
        if rel == ".":
            rel = ""
        for f in filenames:
            if not f.lower().endswith(".json"):
                continue
            if any(pattern in f for pattern in SKIP_FILES_PATTERNS):
                continue
            files.append((rel, f))
    return files


def progress_bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct / 100)
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}]"


def main():
    parser = argparse.ArgumentParser(
        description="Extract untranslated strings from Ostranauts game files",
    )
    parser.add_argument("--game-path", "-g", required=True,
                        help="Path to StreamingAssets/data of Ostranauts")
    parser.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data",
                        help="Path to mod data folder")
    parser.add_argument("--output", "-o", default="untranslated.json",
                        help="Output file for untranslated strings")
    parser.add_argument("--stats-only", "-s", action="store_true",
                        help="Show stats only, no output file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose per-file output")

    args = parser.parse_args()

    if not os.path.isdir(args.game_path):
        print(f"ERROR: game path not found: {args.game_path}", file=sys.stderr)
        sys.exit(1)

    resolved = resolve_data_path(args.game_path)
    if resolved != os.path.normpath(args.game_path):
        print(f"[INFO] Auto-detected data path: {resolved}")
    args.game_path = resolved

    print(f"Game: {args.game_path}")
    print(f"Mod:  {args.mod_path}")
    print()

    all_files = walk_game_data(args.game_path)
    print(f"Found {len(all_files)} JSON files in game\n")

    grand_total = 0
    grand_translated = 0
    all_untranslated = {}
    file_stats = []

    for rel_dir, filename in sorted(all_files):
        result = process_file(args.game_path, args.mod_path, rel_dir, filename)
        grand_total += result.get("total", 0)
        grand_translated += result.get("translated", 0)

        file_key = result["file"]
        pct = round(result["translated"] / result["total"] * 100, 1) if result["total"] > 0 else 0
        file_stats.append({
            "file": file_key,
            "total": result["total"],
            "translated": result["translated"],
            "pct": pct,
        })

        if result["untranslated"]:
            all_untranslated[file_key] = result["untranslated"]

        if args.verbose:
            bar = progress_bar(pct)
            print(f"  {file_key:<55} {result['total']:>5} str | {result['translated']:>5} tr | {bar} {pct:>5.1f}%")

    overall_pct = round(grand_translated / grand_total * 100, 2) if grand_total > 0 else 0

    print()
    print("=" * 70)
    print(f"  TOTAL TRANSLATABLE STRINGS: {grand_total}")
    print(f"  ALREADY TRANSLATED:         {grand_translated}")
    print(f"  REMAINING:                  {grand_total - grand_translated}")
    print(f"  PROGRESS:                   {progress_bar(overall_pct)} {overall_pct}%")
    print("=" * 70)

    if not args.stats_only and all_untranslated:
        untranslated_count = sum(len(v) for v in all_untranslated.values())
        print(f"\nSaving {untranslated_count} untranslated strings to {args.output} ...")

        output_data = {
            "_meta": {
                "game_path": os.path.abspath(args.game_path),
                "mod_path": os.path.abspath(args.mod_path),
                "total_strings": grand_total,
                "translated_strings": grand_translated,
                "untranslated_strings": untranslated_count,
                "progress_pct": overall_pct,
                "files_with_untranslated": len(all_untranslated),
            },
            "files": all_untranslated,
        }

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Done: {os.path.abspath(args.output)}")

        stats_file = args.output.replace(".json", "_stats.json")
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump({"files": file_stats, "summary": output_data["_meta"]}, f, ensure_ascii=False, indent=2)

    elif args.stats_only:
        print("\nStats-only mode: no file saved.")


if __name__ == "__main__":
    main()
