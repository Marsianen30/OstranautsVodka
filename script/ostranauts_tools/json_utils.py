#!/usr/bin/env python3
r"""
Robust JSON loader for Ostranauts game files.

Handles:
- utf-8-sig BOM
- // comments
- Raw control characters inside strings (unescaped \n, \r, etc.)
- Invalid JSON escape sequences (the game uses backslash-underscore etc.)
- Windows paths with backslashes inside strings
"""

import json
import os
import re
from typing import Any


# Valid JSON escape sequences: \" \\ \/ \b \f \n \r \t \uXXXX
# Any other backslash-char combo is invalid in strict JSON
_INVALID_ESCAPE_RE = re.compile(r'\\(?!["\\/bfnrtu])')


def _fix_invalid_escapes(text: str) -> str:
    """Double-escape backslashes in invalid escape sequences."""
    return _INVALID_ESCAPE_RE.sub(r'\\\\', text)


def _escape_control_chars(text: str) -> str:
    """
    Escape raw control characters (U+0000..U+001F) that appear inside
    JSON string literals.  Walks the text keeping track of whether we are
    inside a string, and of backslash-escaping.
    """
    result = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            # Previous char was backslash – this char is part of an escape
            # sequence, pass it through as-is.
            result.append(ch)
            escape_next = False
            continue

        if ch == '\\':
            # Start of an escape sequence.
            result.append(ch)
            escape_next = True
            continue

        if ch == '"':
            # Entering or leaving a string.
            in_string = not in_string
            result.append(ch)
            continue

        if in_string and ord(ch) < 0x20:
            # Raw control character inside a string – escape it.
            result.append('\\u{:04x}'.format(ord(ch)))
            continue

        result.append(ch)

    return ''.join(result)


def load_json_file(filepath: str) -> Any:
    """
    Load a JSON file with maximum tolerance:
    utf-8-sig BOM, // comments, raw control chars, invalid escape sequences.
    """
    with open(filepath, "r", encoding="utf-8-sig") as f:
        raw = f.read()

    # Strip // comments (only whole-line comments)
    cleaned = re.sub(r"^\s*//.*$", "", raw, flags=re.MULTILINE)

    # Attempts from most conservative to most aggressive
    attempts = [
        # 1. Cleaned text, strict parse
        cleaned,
        # 2. Cleaned + control chars escaped
        _escape_control_chars(cleaned),
        # 3. Cleaned + control chars escaped + invalid escapes fixed
        _fix_invalid_escapes(_escape_control_chars(cleaned)),
        # 4. Raw text, strict parse
        raw,
        # 5. Raw + control chars escaped
        _escape_control_chars(raw),
        # 6. Raw + control chars escaped + invalid escapes fixed
        _fix_invalid_escapes(_escape_control_chars(raw)),
    ]

    last_error = None
    for text in attempts:
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            last_error = e
            continue

    # All attempts failed
    raise RuntimeError(
        f"Failed to parse JSON file: {filepath}\n"
        f"Last error: {last_error}"
    ) from last_error


def save_json_file(filepath: str, data: Any):
    """Save JSON with consistent formatting (utf-8, 2-space indent)."""
    dirname = os.path.dirname(filepath)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


__all__ = ["load_json_file", "save_json_file", "resolve_data_path"]


def resolve_data_path(path: str) -> str:
    """
    Auto-detect Ostranauts_Data/StreamingAssets/data if the user
    passed the game root directory instead of the data folder.
    """
    p = os.path.normpath(path)

    # Already looks right?
    if os.path.isdir(p):
        entries = os.listdir(p)
        subdirs = {e for e in entries if os.path.isdir(os.path.join(p, e))}
        if {"conditions", "strings"} & subdirs:
            return p

    # Try common sub-paths
    for suffix in [
        "Ostranauts_Data/StreamingAssets/data",
        "Ostranauts_Data/StreamingAssets",
    ]:
        candidate = os.path.normpath(os.path.join(path, suffix))
        if os.path.isdir(candidate):
            return candidate

    # Give up, return as-is
    return p
