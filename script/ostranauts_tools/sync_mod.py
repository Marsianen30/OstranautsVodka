#!/usr/bin/env python3
r"""
Sync mod files with game version.

Copies game structure into mod while preserving existing translations.
Improved version_upgrade.py: no translation loss, adds new game objects,
updates changed strings.

Usage:
    python sync_mod.py --game-path "C:\...\StreamingAssets\data"
    python sync_mod.py -g "C:\...\data" -m ".\src\ostranautsRu\data" -v
"""

import argparse
import os
import re
import sys
from copy import deepcopy
from typing import Any

from json_utils import load_json_file, save_json_file, resolve_data_path


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



def sync_standard(game_file: str, mod_file: str, dry_run: bool = False) -> dict:
    game_data = load_json_file(game_file)
    if not isinstance(game_data, list):
        return {"status": "skip", "reason": "game data is not a list"}

    mod_translations = {}
    if os.path.exists(mod_file):
        try:
            mod_data = load_json_file(mod_file)
            if isinstance(mod_data, list):
                for item in mod_data:
                    if isinstance(item, dict) and "strName" in item:
                        name = item["strName"]
                        trans = {}
                        for field in TRANSLATABLE_FIELDS:
                            val = item.get(field)
                            if isinstance(val, str) and contains_russian(val):
                                trans[field] = val
                        if trans:
                            mod_translations[name] = trans
        except Exception:
            pass

    result = []
    stats = {"total": 0, "kept": 0, "new": 0}

    for game_item in game_data:
        if not isinstance(game_item, dict):
            result.append(game_item)
            continue

        new_item = deepcopy(game_item)
        name = new_item.get("strName")

        if name and name in mod_translations:
            trans = mod_translations[name]
            for field, value in trans.items():
                if field in new_item:
                    new_item[field] = value
                    stats["kept"] += 1
                else:
                    new_item[field] = value
                    stats["kept"] += 1

        for field in TRANSLATABLE_FIELDS:
            if field in new_item and isinstance(new_item[field], str) and is_translatable_value(new_item[field]):
                stats["total"] += 1
                if not (name and name in mod_translations and field in mod_translations[name]):
                    stats["new"] += 1

        result.append(new_item)

    if not dry_run:
        save_json_file(mod_file, result)

    return {"status": "ok", "stats": stats}


def sync_strings_format(game_file: str, mod_file: str, dry_run: bool = False) -> dict:
    game_data = load_json_file(game_file)
    if not isinstance(game_data, list) or len(game_data) == 0:
        return {"status": "skip", "reason": "bad game data structure"}

    game_obj = game_data[0]
    if not isinstance(game_obj, dict) or "aValues" not in game_obj:
        return {"status": "skip", "reason": "no aValues in game"}

    game_values = game_obj["aValues"]

    mod_translations = {}
    if os.path.exists(mod_file):
        try:
            mod_data = load_json_file(mod_file)
            if isinstance(mod_data, list) and len(mod_data) > 0:
                mod_obj = mod_data[0]
                if isinstance(mod_obj, dict) and "aValues" in mod_obj:
                    mv = mod_obj["aValues"]
                    i = 0
                    while i + 1 < len(mv):
                        key = str(mv[i]).strip()
                        val = str(mv[i + 1]) if mv[i + 1] is not None else ""
                        if contains_russian(val):
                            mod_translations[key] = val
                        i += 2
        except Exception:
            pass

    result_values = []
    stats = {"total": 0, "kept": 0, "new": 0}

    i = 0
    while i + 1 < len(game_values):
        key = str(game_values[i]).strip()
        original = str(game_values[i + 1]) if game_values[i + 1] is not None else ""

        result_values.append(game_values[i])
        if key in mod_translations and is_translatable_value(original):
            result_values.append(mod_translations[key])
            stats["kept"] += 1
        else:
            result_values.append(game_values[i + 1])

        if is_translatable_value(original):
            stats["total"] += 1
            if key not in mod_translations:
                stats["new"] += 1

        i += 2

    new_obj = deepcopy(game_obj)
    new_obj["aValues"] = result_values
    output = [new_obj]

    if not dry_run:
        save_json_file(mod_file, output)

    return {"status": "ok", "stats": stats}


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


def main():
    parser = argparse.ArgumentParser(description="Sync mod files with game data")
    parser.add_argument("--game-path", "-g", required=True,
                        help="Path to game root or StreamingAssets/data")
    parser.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data",
                        help="Path to mod data folder")
    parser.add_argument("--dry-run", "-n", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if not os.path.isdir(args.game_path):
        print(f"ERROR: game path not found: {args.game_path}", file=sys.stderr)
        sys.exit(1)

    # Auto-detect the data subfolder
    resolved = resolve_data_path(args.game_path)
    if resolved != os.path.normpath(args.game_path):
        print(f"[INFO] Auto-detected data path: {resolved}")
    args.game_path = resolved

    print(f"Game: {args.game_path}")
    print(f"Mod:  {args.mod_path}")
    if args.dry_run:
        print("[DRY RUN]")
    print()

    all_files = walk_game_data(args.game_path)
    print(f"Found {len(all_files)} JSON files in game\n")

    total_created = 0
    total_updated = 0
    total_skipped = 0
    grand_translated_kept = 0
    grand_total = 0
    grand_new = 0

    for rel_dir, filename in sorted(all_files):
        game_file = os.path.join(args.game_path, rel_dir, filename)
        mod_file = os.path.join(args.mod_path, rel_dir, filename)

        is_new = not os.path.exists(mod_file)
        filename_short = os.path.join(rel_dir, filename) if rel_dir else filename

        if filename in SPECIAL_FILES:
            result = sync_strings_format(game_file, mod_file, dry_run=args.dry_run)
        else:
            result = sync_standard(game_file, mod_file, dry_run=args.dry_run)

        if result["status"] == "skip":
            if args.verbose:
                print(f"  [SKIP] {filename_short}: {result.get('reason')}")
            total_skipped += 1
            continue

        stats = result.get("stats", {})
        grand_translated_kept += stats.get("kept", 0)
        grand_total += stats.get("total", 0)
        grand_new += stats.get("new", 0)

        if is_new:
            total_created += 1
            tag = "[NEW]"
        else:
            total_updated += 1
            tag = "[UPD]"

        if args.verbose:
            print(f"  {tag} {filename_short:<55} total={stats.get('total',0):>5}  kept={stats.get('kept',0):>5}  new={stats.get('new',0):>5}")

    print()
    print("=" * 65)
    print(f"  Files created:  {total_created}")
    print(f"  Files updated:  {total_updated}")
    print(f"  Files skipped:  {total_skipped}")
    print(f"  Total strings:  {grand_total}")
    print(f"  Kept translated:{grand_translated_kept}")
    print(f"  New (untranslated): {grand_new}")
    if args.dry_run:
        print("  [DRY RUN] No files were modified")
    print("=" * 65)


if __name__ == "__main__":
    main()
