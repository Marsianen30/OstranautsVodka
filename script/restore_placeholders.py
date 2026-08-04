#!/usr/bin/env python3
"""Restore Russian bracket placeholders in complete/ to their original English names.

The source/translation trees are aligned by strName where possible. Placeholder
replacement is per string occurrence, not a global replace: this is important for
Russian synonyms such as [говорит], which correspond to [says], [speaks], or
[tells] depending on the original string.
"""
from __future__ import annotations

import collections
import json
import re
import shutil
from pathlib import Path

ROOT = Path("/home/user/wspace")
COMPLETE = ROOT / "complete"
ORIGINAL = ROOT / "original"
TRANSLATE = ROOT / "translate"
REPORT = ROOT / "work/placeholder_restore_report.tsv"

TOKEN_RE = re.compile(r"\[[^\[\]\r\n]{1,120}\]")
RUS_RE = re.compile(r"[А-Яа-яЁё]")
VALID_ESCAPES = set('"\\/bfnrtu')


def clean_json(text: str) -> str:
    """Make the game's JSON/JSONC readable by Python's json parser."""
    out: list[str] = []
    in_string = False
    escaped = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_string:
            if escaped:
                if c not in VALID_ESCAPES:
                    out.append("\\")
                out.append(c)
                escaped = False
                i += 1
                continue
            if c == "\\":
                out.append(c)
                escaped = True
                i += 1
                continue
            if ord(c) < 32:
                out.append({"\n": "\\n", "\r": "\\r", "\t": "\\t", "\b": "\\b", "\f": "\\f"}.get(c, f"\\u{ord(c):04x}"))
                i += 1
                continue
            out.append(c)
            if c == '"':
                in_string = False
            i += 1
        else:
            if c == '"':
                in_string = True
                out.append(c)
                i += 1
            elif c == "/" and i + 1 < len(text) and text[i + 1] == "/":
                i += 2
                while i < len(text) and text[i] not in "\r\n":
                    i += 1
            else:
                out.append(c)
                i += 1
    return "".join(out)


def load_json(path: Path):
    return json.loads(clean_json(path.read_text(encoding="utf-8-sig")))


def is_russian_token(token: str) -> bool:
    return bool(RUS_RE.search(token))


def token_inner(token: str) -> str:
    return token[1:-1]


def named_list(values) -> bool:
    return isinstance(values, list) and all(isinstance(x, dict) and isinstance(x.get("strName"), str) for x in values)


def aligned_leaves(c, o, t, cp=(), op=(), tp=()):
    """Yield (complete_path, complete_string, original_string, translate_string).

    Arrays of objects are paired by strName, otherwise by position. This avoids
    the one extra TEST_VERBS entry shifting every later interaction.
    """
    if isinstance(c, dict) and isinstance(o, dict):
        for key, value in c.items():
            if key in o:
                tv = t.get(key) if isinstance(t, dict) else None
                yield from aligned_leaves(value, o[key], tv, cp + (key,), op + (key,), tp + (key,))
        return
    if isinstance(c, list) and isinstance(o, list):
        if named_list(c) and named_list(o):
            om = collections.defaultdict(list)
            tm = collections.defaultdict(list)
            for j, item in enumerate(o):
                om[item["strName"]].append((j, item))
            if isinstance(t, list):
                for j, item in enumerate(t):
                    if isinstance(item, dict) and isinstance(item.get("strName"), str):
                        tm[item["strName"]].append((j, item))
            for i, item in enumerate(c):
                name = item["strName"]
                # Match duplicate names in original order.
                same_c = [k for k, x in enumerate(c[:i]) if x["strName"] == name]
                occurrence = len(same_c)
                if occurrence >= len(om.get(name, [])):
                    continue
                j, oval = om[name][occurrence]
                if occurrence < len(tm.get(name, [])):
                    tj, tval = tm[name][occurrence]
                else:
                    tj, tval = -1, None
                yield from aligned_leaves(item, oval, tval, cp + (i,), op + (j,), tp + ((tj,) if tj >= 0 else ()))
        else:
            for i, (cv, ov) in enumerate(zip(c, o)):
                tv = t[i] if isinstance(t, list) and i < len(t) else None
                yield from aligned_leaves(cv, ov, tv, cp + (i,), op + (i,), tp + (i,))
        return
    if isinstance(c, str) and isinstance(o, str):
        yield cp, c, o, t if isinstance(t, str) else ""


def raw_string_spans(text: str):
    """Return (path, start, end, decoded_value) for JSON value strings."""
    decoder = json.JSONDecoder()
    result = []

    def ws(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    def quoted(pos, path, record=True):
        start = pos
        pos += 1
        escaped = False
        while pos < len(text):
            c = text[pos]
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                pos += 1
                if record:
                    result.append((path, start, pos, json.loads(text[start:pos])))
                return pos
            pos += 1
        raise ValueError("unterminated JSON string")

    def value(pos, path):
        pos = ws(pos)
        if pos >= len(text):
            raise ValueError("unexpected end")
        if text[pos] == '"':
            return quoted(pos, path, True)
        if text[pos] == '{':
            pos = ws(pos + 1)
            if pos < len(text) and text[pos] == '}':
                return pos + 1
            while True:
                pos = ws(pos)
                if text[pos] != '"':
                    raise ValueError("object key expected")
                pos = quoted(pos, (), False)
                pos = ws(pos)
                if text[pos] != ':':
                    raise ValueError("colon expected")
                pos = value(pos + 1, path + ("__last_key__",))
                # Replace the marker with the actual key is done by a small
                # second pass below; this branch is not used for transformations.
                pos = ws(pos)
                if text[pos] == '}':
                    return pos + 1
                if text[pos] != ',':
                    raise ValueError("comma expected")
                pos += 1
        if text[pos] == '[':
            pos = ws(pos + 1)
            idx = 0
            if pos < len(text) and text[pos] == ']':
                return pos + 1
            while True:
                pos = value(pos, path + (idx,))
                idx += 1
                pos = ws(pos)
                if text[pos] == ']':
                    return pos + 1
                if text[pos] != ',':
                    raise ValueError("comma expected")
                pos += 1
        _, end = decoder.raw_decode(text, pos)
        return end

    # The generic parser above cannot retain object keys in paths. Use a second
    # path-aware parser; keeping it separate makes the string scanner easier to
    # audit.
    result.clear()

    def parse(pos, path):
        pos = ws(pos)
        if text[pos] == '"':
            return quoted(pos, path, True)
        if text[pos] == '{':
            pos = ws(pos + 1)
            if text[pos] == '}':
                return pos + 1
            while True:
                pos = ws(pos)
                key_start = pos
                pos = quoted(pos, (), False)
                key = json.loads(text[key_start:pos])
                pos = ws(pos)
                if text[pos] != ':':
                    raise ValueError("colon expected")
                pos = parse(pos + 1, path + (key,))
                pos = ws(pos)
                if text[pos] == '}':
                    return pos + 1
                if text[pos] != ',':
                    raise ValueError("comma expected")
                pos += 1
        if text[pos] == '[':
            pos = ws(pos + 1)
            idx = 0
            if text[pos] == ']':
                return pos + 1
            while True:
                pos = parse(pos, path + (idx,))
                idx += 1
                pos = ws(pos)
                if text[pos] == ']':
                    return pos + 1
                if text[pos] != ',':
                    raise ValueError("comma expected")
                pos += 1
        _, end = decoder.raw_decode(text, pos)
        return end

    parse(0, ())
    return result


# Only used when a translated Russian form is an extra or its source placeholder
# was reordered/removed. Values are original placeholder names, without brackets.
MANUAL = {
    "просит": "asks",
    "спрашивает": "asks",
    "настаивает": "insists",
    "желает": "wishes",
    "знает": "knows",
    "помнит": "remembers",
    "ест": "eats",
    "кричит": "shouts",
    "впрыскивает": "injects",
    "собрал": "has",
    "вскрывает": "pries",
    "покидает": "abandons",
    "просыпается": "wakes",
    "активирует": "activates",
    "выдыхает": "exhales",
    "герметизирует": "spaces",
    "зажигает/тушит": "snuffs",
    "контролирует": "monitors",
    "курит": "smokes",
    "чинит": "repairs",
    "не мог": "us-subj",
    "понимает": "realizes",
    "согласен": "doesn't",
    "начинать": "starts",
    "начинает": "starts",  # TEST_VERBS only; absent from original source text
    "заканчивает": "ends",  # TEST_VERBS only; absent from original source text
    "пытается": "tries",  # TEST_VERBS/title-only extra; source title is "Relax"
}


def make_token_map():
    original = load_json(ORIGINAL / "tokens/verbs.json")[0]["tokens2"]
    translated = load_json(TRANSLATE / "tokens/verbs.json")[0]["tokens2"]
    result = collections.defaultdict(set)
    for oval, tval in zip(original, translated):
        if oval and tval and oval[0] and tval[0]:
            result[tval[0]].add(oval[0])
    return result


def align_tokens(ct, ot, tt, token_map, original_verb_set):
    """Return complete-token-index -> original-token-inner mapping."""
    n, m = len(ct), len(ot)
    local = collections.defaultdict(set)
    # An intermediate translation token that is already English is strong local
    # evidence, but only use it if it is a known original placeholder.
    for i, ctoken in enumerate(ct):
        if is_russian_token(ctoken) and i < len(tt) and not is_russian_token(tt[i]):
            if token_inner(tt[i]) in original_verb_set:
                local[token_inner(ctoken)].add(token_inner(tt[i]))

    def score(c, o):
        if c == o:
            return 100
        if not is_russian_token(c):
            return -10**8
        ci, oi = token_inner(c), token_inner(o)
        candidates = set(token_map.get(ci, ())) | set(local.get(ci, ()))
        if ci in MANUAL and MANUAL[ci] in oi:
            return 95
        if ci.startswith("us-") and oi.startswith("us-"):
            return 45
        if ci.startswith("them-") and oi.startswith("them-"):
            return 45
        if oi in candidates:
            return 80
        # A Russian synonym may not be present in translate/tokens/verbs.json.
        # Permit a weak match to a source verb; known candidates still win.
        if oi in original_verb_set:
            return 2 if candidates else 12
        return -10**8

    dp = [[(-10**9, None) for _ in range(m + 1)] for _ in range(n + 1)]
    dp[0][0] = (0, None)

    def update(i, j, value, action):
        if value > dp[i][j][0]:
            dp[i][j] = (value, action)

    for i in range(n + 1):
        for j in range(m + 1):
            current = dp[i][j][0]
            if current < -10**8:
                continue
            if i < n:
                update(i + 1, j, current - 6, ("skip_c",))
            if j < m:
                update(i, j + 1, current - 6, ("skip_o",))
            if i < n and j < m:
                value = score(ct[i], ot[j])
                if value > -10**7:
                    update(i + 1, j + 1, current + value, ("match", i, j))

    i, j = n, m
    pairs = []
    while i or j:
        action = dp[i][j][1]
        if action is None:
            break
        if action[0] == "skip_c":
            i -= 1
        elif action[0] == "skip_o":
            j -= 1
        else:
            _, ci, oi = action
            pairs.append((ci, oi))
            i -= 1
            j -= 1
    pairs.reverse()
    return {ci: ot[oi] for ci, oi in pairs}


def resolve_string(text, original_text, translation_text, token_map, original_verb_set, file_rel, path, unresolved):
    ct = TOKEN_RE.findall(text)
    ot = TOKEN_RE.findall(original_text or "")
    tt = TOKEN_RE.findall(translation_text or "")
    aligned = align_tokens(ct, ot, tt, token_map, original_verb_set)
    result_by_index = {}
    for i, token in enumerate(ct):
        if not is_russian_token(token):
            continue
        inner = token_inner(token)
        candidates = set(token_map.get(inner, ()))
        source_tokens = [token_inner(x) for x in ot]
        # If exactly one known candidate occurs in the original string, it is
        # stronger than sequence position (Russian often reordered the phrase).
        candidate_in_source = [x for x in source_tokens if x in candidates]
        if len(set(candidate_in_source)) == 1:
            result_by_index[i] = candidate_in_source[0]
            continue
        if i in aligned:
            result_by_index[i] = token_inner(aligned[i])
            continue
        # Handle [us-asks] and similar composite placeholders explicitly.
        if inner == "спрашивает" and "us-asks" in source_tokens:
            result_by_index[i] = "us-asks"
            continue
        # A manual mapping that exists in the current source wins.
        manual = MANUAL.get(inner)
        if manual and manual in source_tokens:
            result_by_index[i] = manual
            continue
        if manual:
            result_by_index[i] = manual
            continue
        if len(candidates) == 1:
            result_by_index[i] = next(iter(candidates))
            continue
        # If there is one obvious original verb left in this string, use it.
        source_verbs = [x for x in source_tokens if x in original_verb_set]
        if len(set(source_verbs)) == 1:
            result_by_index[i] = source_verbs[0]
            continue
        unresolved.append((file_rel, path, token, text, original_text))

    counter = 0

    def repl(match):
        nonlocal counter
        i = counter
        counter += 1
        if i in result_by_index:
            return "[" + result_by_index[i] + "]"
        return match.group(0)

    return TOKEN_RE.sub(repl, text)


def counts(root: Path):
    """Count placeholders in JSON string values, not in JSONC comments."""
    counter = collections.Counter()
    for path in root.rglob("*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue
        def visit(value):
            if isinstance(value, str):
                counter.update(TOKEN_RE.findall(value))
            elif isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                for item in value.values():
                    visit(item)
        visit(data)
    return counter


def main():
    before = counts(COMPLETE)
    token_map = make_token_map()
    original_verb_set = {x[0] for x in load_json(ORIGINAL / "tokens/verbs.json")[0]["tokens2"] if x and x[0]}
    original_verb_set.update({"is", "has", "was", "had", "will", "isn't", "doesn't", "Pin", "Unpin"})

    transformed = 0
    changed_files = 0
    unresolved = []
    audit_rows = []

    for cp in sorted(COMPLETE.rglob("*.json")):
        rel = cp.relative_to(COMPLETE)
        if rel.as_posix() == "tokens/verbs.json":
            # The declarations themselves must be the original English token
            # dictionary, not the reduced Russian helper list.
            shutil.copyfile(ORIGINAL / "tokens/verbs.json", cp)
            changed_files += 1
            continue
        op = ORIGINAL / rel
        tp = TRANSLATE / rel
        try:
            complete_data = load_json(cp)
        except Exception as exc:
            audit_rows.append((str(rel), "", "", "", f"COMPLETE_PARSE_ERROR:{exc}"))
            continue
        original_data = load_json(op) if op.exists() else None
        translate_data = load_json(tp) if tp.exists() else None
        aligned = {}
        if original_data is not None:
            trans_iter = aligned_leaves(complete_data, original_data, translate_data)
            for cpath, ctext, otext, ttext in trans_iter:
                aligned[cpath] = (otext, ttext)

        raw = cp.read_text(encoding="utf-8")
        try:
            spans = raw_string_spans(raw)
        except Exception as exc:
            audit_rows.append((str(rel), "", "", "", f"RAW_SCAN_ERROR:{exc}"))
            continue
        replacements = []
        file_changed = False
        for cpath, start, end, value in spans:
            if not isinstance(value, str) or not TOKEN_RE.search(value):
                continue
            otext, ttext = aligned.get(cpath, ("", ""))
            unresolved_before = len(unresolved)
            new_value = resolve_string(value, otext, ttext, token_map, original_verb_set, str(rel), cpath, unresolved)
            if new_value != value:
                replacements.append((start, end, json.dumps(new_value, ensure_ascii=False)))
                file_changed = True
                transformed += sum(1 for a, b in zip(TOKEN_RE.findall(value), TOKEN_RE.findall(new_value)) if a != b)
            if len(unresolved) > unresolved_before:
                pass
        if replacements:
            for start, end, replacement in reversed(replacements):
                raw = raw[:start] + replacement + raw[end:]
            cp.write_text(raw, encoding="utf-8")
            changed_files += 1

    # One already-English translation variant was hyphenated although the
    # original token is `reenacts`; normalize it to the exact source key.
    variant_file = COMPLETE / "interactions/interactions2.json"
    if variant_file.exists():
        variant_raw = variant_file.read_text(encoding="utf-8")
        variant_new = variant_raw.replace("[re-enacts]", "[reenacts]")
        if variant_new != variant_raw:
            variant_file.write_text(variant_new, encoding="utf-8")

    after = counts(COMPLETE)
    with REPORT.open("w", encoding="utf-8") as fh:
        fh.write("file\tpath\trussian_placeholder\toriginal_context\tstatus\n")
        for rel, path, token, text, original_text in unresolved:
            fh.write(f"{rel}\t{path}\t{token}\t{original_text.replace(chr(9), ' ')}\tUNRESOLVED\n")
        fh.write(f"# changed_files\t{changed_files}\n")
        fh.write(f"# changed_placeholder_occurrences\t{transformed}\n")
        fh.write(f"# before_occurrences\t{sum(before.values())}\n")
        fh.write(f"# before_unique\t{len(before)}\n")
        fh.write(f"# after_occurrences\t{sum(after.values())}\n")
        fh.write(f"# after_unique\t{len(after)}\n")
        fh.write(f"# unresolved_occurrences\t{len(unresolved)}\n")
        fh.write(f"# unresolved_unique\t{len({x[2] for x in unresolved})}\n")

    print(json.dumps({
        "before_occurrences": sum(before.values()),
        "before_unique": len(before),
        "russian_before_occurrences": sum(n for t, n in before.items() if is_russian_token(t)),
        "russian_before_unique": len([t for t in before if is_russian_token(t)]),
        "changed_files": changed_files,
        "changed_placeholder_occurrences": transformed,
        "after_occurrences": sum(after.values()),
        "after_unique": len(after),
        "russian_after_occurrences": sum(n for t, n in after.items() if is_russian_token(t)),
        "russian_after_unique": len([t for t in after if is_russian_token(t)]),
        "unresolved_occurrences": len(unresolved),
        "unresolved_unique": len({x[2] for x in unresolved}),
        "report": str(REPORT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
