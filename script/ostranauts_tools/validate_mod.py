#!/usr/bin/env python3
r"""
Validate and apply game updates to mod JSON files.

Algorithm:
1. Looks into the mod directory, finds all JSON files, and checks only those files that exist in the mod.
2. Inside each JSON file, matches objects by `strName`.
3. Compares all keys and values between original game and mod:
   - Missing keys are reported / automatically added if `--apply` is passed.
   - Extra keys are reported; if `--apply` is passed, extra keys are removed UNLESS --all is omitted AND they are in IGNORE_FIELDS.
     (With `--all`, even IGNORE_FIELDS extra keys and [NEW OBJ] extra objects are cleaned up).
   - Value mismatches are updated with game values (unless IGNORE_FIELDS or --norus applies).

Options:
    --norus: Ignore/suppress reporting value mismatches for values containing Russian letters.
    --noignore: Do not apply the IGNORE_FIELDS filter for value mismatches.
    --apply, -a: Automatically sync mod with game (add missing keys, update values, remove extra technical keys).
    --all: Disables field protection for IGNORE_FIELDS when cleaning extra keys/objects with --apply.
    --dry-run, -n: Preview changes without writing files when using --apply.

Usage:
    python validate_mod.py -g "C:\...\StreamingAssets\data" -m ".\src\ostranautsRu\data" --apply --all
"""

import argparse
import os
import re
import sys
from copy import deepcopy
from typing import Any

from json_utils import load_json_file, save_json_file, resolve_data_path

IGNORE_FIELDS = {
    "strNameFriendly",
    "strDesc",
    "strTitle",
    "strName",
    "strMainText",
    "strBody",
    "strRequirementDescription",
    "aPhaseTitles",
    "strFriendlyDescription",
    "strDescription",
    "strFriendlyName",
    "tokens2",
    "aValues",
    "strTooltip",
    "strArticleTitle",
    "strLookup",
    "strNodeLabel",
    "strTutorialKey",
    "strArticleBody",
    "strNameShort",
    "strNameDesc",
    "aOverrideValues",
}

SPECIAL_FILES = {"strings.json", "conditions_simple.json"}
SKIP_DIRS = {"schemas"}
SKIP_FILES_PATTERNS = {"verbs.json"}


def contains_russian(obj: Any) -> bool:
    """Recursively checks if a string, list, or dict contains Russian letters."""
    if isinstance(obj, str):
        return bool(re.search(r"[а-яА-ЯёЁ]", obj))
    elif isinstance(obj, list):
        return any(contains_russian(item) for item in obj)
    elif isinstance(obj, dict):
        return any(contains_russian(v) for v in obj.values())
    return False


def walk_mod_data(mod_path: str) -> list:
    files = []
    if not os.path.isdir(mod_path):
        return files
    for root, dirs, filenames in os.walk(mod_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, mod_path)
        if rel == ".":
            rel = ""
        for f in filenames:
            if not f.lower().endswith(".json"):
                continue
            if any(pattern in f for pattern in SKIP_FILES_PATTERNS):
                continue
            files.append((rel, f))
    return files


def process_file(game_file: str, mod_file: str, file_rel: str, norus: bool, noignore: bool, apply: bool, clean_all: bool, dry_run: bool) -> int:
    """
    Validates and optionally applies game updates to a single mod file.
    Returns the number of discrepancies found.
    """
    if not os.path.exists(game_file):
        print(f"[{file_rel}] [INFO] File exists in mod, but not found in game originals.")
        return 0

    try:
        game_data = load_json_file(game_file)
    except Exception as e:
        print(f"[{file_rel}] [ERROR] Failed to load game original: {e}")
        return 1

    try:
        mod_data = load_json_file(mod_file)
    except Exception as e:
        print(f"[{file_rel}] [ERROR] Failed to load mod file: {e}")
        return 1

    if not isinstance(game_data, list) or not isinstance(mod_data, list):
        # Skip non-standard structure files (like strings.json)
        return 0

    # Index game items by strName
    game_index = {}
    for item in game_data:
        if isinstance(item, dict) and "strName" in item:
            game_index[item["strName"]] = item

    discrepancies = 0
    file_modified = False

    # If --apply and --all are active, remove entire objects in mod that do not exist in game original
    if apply and clean_all:
        filtered_mod_data = []
        for item in mod_data:
            if isinstance(item, dict) and "strName" in item:
                name = item["strName"]
                if name not in game_index:
                    print(f"[{file_rel}] [APPLIED] Removed extra object strName '{name}' not found in game original.")
                    file_modified = True
                    continue
            filtered_mod_data.append(item)
        mod_data = filtered_mod_data

    # Re-index mod items by strName after filtering
    mod_index = {}
    for item in mod_data:
        if isinstance(item, dict) and "strName" in item:
            mod_index[item["strName"]] = item

    # Check mod items against game items
    for name, mod_item in mod_index.items():
        if name not in game_index:
            print(f"[{file_rel}] [NEW OBJ] strName '{name}' exists in mod, but not in game original.")
            discrepancies += 1
            continue

        game_item = game_index[name]

        # 1. Compare ALL keys
        game_keys_all = set(game_item.keys())
        mod_keys_all = set(mod_item.keys())

        missing_keys_all = game_keys_all - mod_keys_all
        extra_keys_all = mod_keys_all - game_keys_all
        common_keys_all = game_keys_all & mod_keys_all

        # If --apply is requested, automatically add missing keys from game to mod item
        if missing_keys_all and apply:
            for k in missing_keys_all:
                mod_item[k] = deepcopy(game_item[k])
                file_modified = True
            print(f"[{file_rel}] strName '{name}': [APPLIED] Added missing keys from game: {sorted(missing_keys_all)}")
            missing_keys_all = set()

        # If --apply is requested, remove extra keys
        if extra_keys_all and apply:
            if clean_all:
                keys_to_remove = list(extra_keys_all)
            else:
                # With standard --apply, respect IGNORE_FIELDS protection (do not remove extra keys in IGNORE_FIELDS)
                keys_to_remove = [k for k in extra_keys_all if k not in IGNORE_FIELDS]

            if keys_to_remove:
                for k in keys_to_remove:
                    del mod_item[k]
                    file_modified = True
                print(f"[{file_rel}] strName '{name}': [APPLIED] Removed extra keys: {sorted(keys_to_remove)}")
                mod_keys_all = set(mod_item.keys())
                extra_keys_all = mod_keys_all - game_keys_all

        missing_keys = sorted(list(missing_keys_all))
        extra_keys = sorted(list(extra_keys_all))

        # 2. Value mismatches check
        mismatched_keys = []
        for key in common_keys_all:
            if game_item[key] != mod_item[key]:
                # If --norus is enabled and Russian text is present in game or mod value
                if norus and (contains_russian(game_item[key]) or contains_russian(mod_item[key])):
                    continue
                # If field is in IGNORE_FIELDS and --noignore is not set, suppress value mismatch report
                if not noignore and key in IGNORE_FIELDS:
                    continue
                
                # If --apply is set for non-ignored keys (technical values), update mod with game's value
                if apply:
                    mod_item[key] = deepcopy(game_item[key])
                    file_modified = True
                    print(f"[{file_rel}] strName '{name}': [APPLIED] Updated key '{key}' with game value.")
                else:
                    mismatched_keys.append(key)

        mismatched_keys = sorted(mismatched_keys)

        # 3. Report remaining discrepancies
        if missing_keys:
            print(f"[{file_rel}] strName '{name}': Missing keys in mod (present in game): {missing_keys}")
            discrepancies += 1

        if extra_keys:
            print(f"[{file_rel}] strName '{name}': Extra keys in mod (not in game): {extra_keys}")
            discrepancies += 1

        if mismatched_keys:
            print(f"[{file_rel}] strName '{name}': Value mismatch for keys: {mismatched_keys}")
            for k in mismatched_keys:
                print(f"    - {k}: game={repr(game_item[k])} != mod={repr(mod_item[k])}")
            discrepancies += 1

    # Save modified mod file if --apply is active
    if apply and file_modified:
        if dry_run:
            print(f"[{file_rel}] [DRY RUN] Would save updated mod file.")
        else:
            save_json_file(mod_file, mod_data)
            print(f"[{file_rel}] [SAVED] Updated mod file written.")

    return discrepancies


def main():
    parser = argparse.ArgumentParser(
        description="Validate and apply game updates to mod JSON files",
    )
    parser.add_argument("--game-path", "-g", required=True,
                        help="Path to game StreamingAssets/data")
    parser.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data",
                        help="Path to mod data folder")
    parser.add_argument("--norus", action="store_true",
                        help="Ignore/suppress reporting value mismatches for values containing Russian letters")
    parser.add_argument("--noignore", action="store_true",
                        help="Do not apply IGNORE_FIELDS filter for value mismatches")
    parser.add_argument("--apply", "-a", action="store_true",
                        help="Automatically apply game updates and clean technical extra keys (keeping IGNORE_FIELDS protection)")
    parser.add_argument("--all", action="store_true",
                        help="When used with --apply, disables IGNORE_FIELDS field protection and removes extra objects/keys")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview changes without writing files when using --apply")

    args = parser.parse_args()

    if not os.path.isdir(args.mod_path):
        print(f"ERROR: mod path not found: {args.mod_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.game_path):
        print(f"ERROR: game path not found: {args.game_path}", file=sys.stderr)
        sys.exit(1)

    resolved = resolve_data_path(args.game_path)
    if resolved != os.path.normpath(args.game_path):
        print(f"[INFO] Auto-detected data path: {resolved}")
    args.game_path = resolved

    print(f"Game: {args.game_path}")
    print(f"Mod:  {args.mod_path}")
    if args.norus:
        print("[OPTION] --norus enabled")
    if args.noignore:
        print("[OPTION] --noignore enabled")
    if args.apply:
        print("[OPTION] --apply enabled")
    if args.all:
        print("[OPTION] --all enabled (field protection disabled during --apply)")
    if args.dry_run:
        print("[OPTION] --dry-run enabled")
    print()

    mod_files = walk_mod_data(args.mod_path)
    print(f"Found {len(mod_files)} files in mod directory to validate/apply.\n")

    total_discrepancies = 0
    checked_files = 0

    for rel_dir, filename in sorted(mod_files):
        file_rel = os.path.join(rel_dir, filename) if rel_dir else filename
        mod_file = os.path.join(args.mod_path, rel_dir, filename)
        game_file = os.path.join(args.game_path, rel_dir, filename)

        disc = process_file(
            game_file, mod_file, file_rel,
            norus=args.norus, noignore=args.noignore,
            apply=args.apply, clean_all=args.all, dry_run=args.dry_run
        )
        total_discrepancies += disc
        checked_files += 1

    print()
    print("=" * 60)
    print(f"  Checked mod files:    {checked_files}")
    print(f"  Total discrepancies:  {total_discrepancies}")
    print("=" * 60)


if __name__ == "__main__":
    main()
