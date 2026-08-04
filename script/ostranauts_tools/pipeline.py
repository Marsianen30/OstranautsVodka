#!/usr/bin/env python3
r"""
Full pipeline for Ostranauts translation.

Steps:
  1. sync     - sync mod files with game version (keep existing translations)
  2. extract  - extract untranslated strings
  3. stats    - show translation statistics
  4. inject   - insert translated strings back into mod

Usage:
  python pipeline.py sync --game-path "D:\...\data"
  python pipeline.py extract --game-path "D:\...\data"
  python pipeline.py stats --game-path "D:\...\data"
  python pipeline.py inject --translated translated.json
"""

import argparse
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(name: str, args: list):
    script = os.path.join(SCRIPTS_DIR, f"{name}.py")
    cmd = [sys.executable, script] + args
    print(f">>> Running: {' '.join(cmd)}")
    print()
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Ostranauts translation pipeline")
    sub = parser.add_subparsers(dest="command", help="Command")

    # sync
    p_sync = sub.add_parser("sync", help="Sync mod files with game version")
    p_sync.add_argument("--game-path", "-g", required=True)
    p_sync.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data")
    p_sync.add_argument("--dry-run", "-n", action="store_true")
    p_sync.add_argument("--verbose", "-v", action="store_true")

    # extract
    p_extract = sub.add_parser("extract", help="Extract untranslated strings")
    p_extract.add_argument("--game-path", "-g", required=True)
    p_extract.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data")
    p_extract.add_argument("--output", "-o", default="untranslated.json")
    p_extract.add_argument("--verbose", "-v", action="store_true")

    # stats
    p_stats = sub.add_parser("stats", help="Show translation statistics")
    p_stats.add_argument("--game-path", "-g", default=None)
    p_stats.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data")
    p_stats.add_argument("--sort-by", choices=["file", "pct", "remaining"], default="remaining")
    p_stats.add_argument("--top", "-t", type=int, default=30)

    # inject
    p_inject = sub.add_parser("inject", help="Inject translations into mod")
    p_inject.add_argument("--translated", "-t", required=True)
    p_inject.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data")
    p_inject.add_argument("--game-path", "-g", default=None)
    p_inject.add_argument("--create-missing", "-c", action="store_true")
    p_inject.add_argument("--dry-run", "-n", action="store_true")

    # validate
    p_validate = sub.add_parser("validate", help="Validate mod JSON files against game original")
    p_validate.add_argument("--game-path", "-g", required=True)
    p_validate.add_argument("--mod-path", "-m", default="./src/ostranautsRu/data")
    p_validate.add_argument("--norus", action="store_true")
    p_validate.add_argument("--noignore", action="store_true")
    p_validate.add_argument("--apply", "-a", action="store_true")
    p_validate.add_argument("--dry-run", "-n", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_args = []
    for key, value in vars(args).items():
        if key == "command":
            continue
        if isinstance(value, bool):
            if value:
                # Convert underscores to dashes for CLI
                flag = "--" + key.replace("_", "-")
                cmd_args.append(flag)
        elif value is not None:
            flag = "--" + key.replace("_", "-")
            cmd_args.append(flag)
            cmd_args.append(str(value))

    # Map command name to script name
    script_map = {
        "sync": "sync_mod",
        "extract": "extract_untranslated",
        "stats": "translation_stats",
        "inject": "inject_translations",
        "validate": "validate_mod",
    }

    script = script_map[args.command]
    rc = run_script(script, cmd_args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
