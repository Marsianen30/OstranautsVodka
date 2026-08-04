#!/usr/bin/env python3
r"""
Quick Ostranauts translation statistics.

Shows overall progress and per-file breakdown without extracting strings.
Can work with mod-only or compare against game version.

Usage:
    python translation_stats.py -g "C:\...\StreamingAssets\data" -m ".\src\ostranautsRu\data"
    python translation_stats.py -m ".\src\ostranautsRu\data"
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
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



def count_translatable_in_file(filepath: str) -> int:
    """Считает количество переводимых строк в одном файле."""
    try:
        data = load_json_file(filepath)
    except Exception:
        return 0

    count = 0
    filename = os.path.basename(filepath)

    if filename in SPECIAL_FILES:
        if isinstance(data, list) and len(data) > 0:
            obj = data[0]
            if isinstance(obj, dict) and "aValues" in obj:
                values = obj["aValues"]
                i = 0
                while i + 1 < len(values):
                    val = str(values[i + 1]).strip() if values[i + 1] is not None else ""
                    if is_translatable_value(val):
                        count += 1
                    i += 2
    else:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field in TRANSLATABLE_FIELDS:
                        if field in item:
                            val = item[field]
                            if isinstance(val, str) and is_translatable_value(val):
                                count += 1
    return count


def count_translated_in_file(filepath: str) -> int:
    """Считает количество уже переведённых (с кириллицей) строк в одном файле."""
    try:
        data = load_json_file(filepath)
    except Exception:
        return 0

    count = 0
    filename = os.path.basename(filepath)

    if filename in SPECIAL_FILES:
        if isinstance(data, list) and len(data) > 0:
            obj = data[0]
            if isinstance(obj, dict) and "aValues" in obj:
                values = obj["aValues"]
                i = 0
                while i + 1 < len(values):
                    val = str(values[i + 1]).strip() if values[i + 1] is not None else ""
                    if is_translatable_value(val) and contains_russian(val):
                        count += 1
                    i += 2
    else:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field in TRANSLATABLE_FIELDS:
                        if field in item:
                            val = item[field]
                            if isinstance(val, str) and is_translatable_value(val) and contains_russian(val):
                                count += 1
    return count


def walk_data(path: str) -> list:
    files = []
    if not os.path.isdir(path):
        return files
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, path)
        if rel == ".":
            rel = ""
        for f in filenames:
            if not f.lower().endswith(".json"):
                continue
            if any(pattern in f for pattern in SKIP_FILES_PATTERNS):
                continue
            files.append((rel, f))
    return files


def progress_bar(pct: float, width: int = 25) -> str:
    filled = int(width * pct / 100)
    empty = width - filled
    bar_filled = "#" * filled
    bar_empty = "." * empty
    return f"[{bar_filled}{bar_empty}]"


def main():
    parser = argparse.ArgumentParser(description="Ostranauts translation statistics")
    parser.add_argument("--game-path", "-g", default=None,
                        help="Path to game StreamingAssets/data (for comparison)")
    parser.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data",
                        help="Path to mod data folder")
    parser.add_argument("--sort-by", choices=["file", "pct", "remaining"], default="remaining",
                        help="Sort order for file list")
    parser.add_argument("--top", "-t", type=int, default=20,
                        help="Show top N files with most remaining work")

    args = parser.parse_args()

    if not os.path.isdir(args.mod_path):
        print(f"ERROR: mod path not found: {args.mod_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Mod path: {args.mod_path}")
    if args.game_path:
        # Auto-detect data path
        resolved = resolve_data_path(args.game_path)
        if resolved != os.path.normpath(args.game_path):
            print(f"[INFO] Auto-detected data path: {resolved}")
        args.game_path = resolved
        print(f"Game path: {args.game_path}")
    print()

    # Если указан game-path, сравниваем с игрой (как extract_untranslated)
    if args.game_path and os.path.isdir(args.game_path):
        game_files = set()
        for rel_dir, filename in walk_data(args.game_path):
            game_files.add(os.path.join(rel_dir, filename))

        mod_files_map = {}
        for rel_dir, filename in walk_data(args.mod_path):
            mod_files_map[os.path.join(rel_dir, filename)] = (rel_dir, filename)

        all_file_keys = sorted(game_files | set(mod_files_map.keys()))

        grand_total = 0
        grand_translated = 0
        file_stats = []

        for file_key in all_file_keys:
            game_file = os.path.join(args.game_path, file_key)
            mod_file = os.path.join(args.mod_path, file_key)

            if os.path.exists(game_file):
                total = count_translatable_in_file(game_file)
            else:
                total = 0

            if os.path.exists(mod_file):
                translated = count_translated_in_file(mod_file)
            else:
                translated = 0

            grand_total += total
            grand_translated += translated

            pct = round(translated / total * 100, 1) if total > 0 else (100 if total == 0 else 0)
            remaining = total - translated

            file_stats.append({
                "file": file_key,
                "total": total,
                "translated": translated,
                "remaining": remaining,
                "pct": pct,
            })

        # Сортировка
        if args.sort_by == "file":
            file_stats.sort(key=lambda x: x["file"])
        elif args.sort_by == "pct":
            file_stats.sort(key=lambda x: x["pct"])
        else:  # remaining
            file_stats.sort(key=lambda x: x["remaining"], reverse=True)

        overall_pct = round(grand_translated / grand_total * 100, 2) if grand_total > 0 else 0

        print(f"{'File':<55} {'Total':>6} {'Tr':>6} {'Rem':>6}  {'Progress'}")
        print("-" * 95)

        for stat in file_stats[:args.top]:
            bar = progress_bar(stat["pct"], 15)
            print(f"  {stat['file']:<53} {stat['total']:>6} {stat['translated']:>6} {stat['remaining']:>6}  {bar} {stat['pct']:>5.1f}%")

        if len(file_stats) > args.top:
            print(f"  ... and {len(file_stats) - args.top} more files")

        print()
        print("=" * 70)
        print(f"  TOTAL:    {grand_total}")
        print(f"  DONE:     {grand_translated}")
        print(f"  REMAIN:   {grand_total - grand_translated}")
        print(f"  PROGRESS: {progress_bar(overall_pct)} {overall_pct}%")
        print("=" * 70)

    else:
        # Только статистика по моду
        mod_files = walk_data(args.mod_path)
        grand_total = 0
        grand_translated = 0
        file_stats = []

        for rel_dir, filename in sorted(mod_files):
            filepath = os.path.join(args.mod_path, rel_dir, filename)
            total = count_translatable_in_file(filepath)
            translated = count_translated_in_file(filepath)

            grand_total += total
            grand_translated += translated

            pct = round(translated / total * 100, 1) if total > 0 else 0
            remaining = total - translated
            file_key = os.path.join(rel_dir, filename) if rel_dir else filename

            file_stats.append({
                "file": file_key,
                "total": total,
                "translated": translated,
                "remaining": remaining,
                "pct": pct,
            })

        if args.sort_by == "file":
            file_stats.sort(key=lambda x: x["file"])
        elif args.sort_by == "pct":
            file_stats.sort(key=lambda x: x["pct"])
        else:
            file_stats.sort(key=lambda x: x["remaining"], reverse=True)

        overall_pct = round(grand_translated / grand_total * 100, 2) if grand_total > 0 else 0

        print(f"{'File':<55} {'Total':>6} {'Tr':>6} {'Rem':>6}  {'Progress'}")
        print("-" * 95)

        for stat in file_stats[:args.top]:
            bar = progress_bar(stat["pct"], 15)
            print(f"  {stat['file']:<53} {stat['total']:>6} {stat['translated']:>6} {stat['remaining']:>6}  {bar} {stat['pct']:>5.1f}%")

        if len(file_stats) > args.top:
            print(f"  ... and {len(file_stats) - args.top} more files")

        print()
        print("=" * 70)
        print(f"  TOTAL STRINGS IN MOD:  {grand_total}")
        print(f"  TRANSLATED (CYRILLIC): {grand_translated}")
        print(f"  NOT TRANSLATED:        {grand_total - grand_translated}")
        print(f"  PROGRESS:              {progress_bar(overall_pct)} {overall_pct}%")
        print("=" * 70)
        print()
        print("Note: run with --game-path for comparison with the actual game version.")


if __name__ == "__main__":
    main()
