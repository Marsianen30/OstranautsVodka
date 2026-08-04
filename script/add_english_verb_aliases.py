#!/usr/bin/env python3
"""Add English token aliases to the Russian conjugation table.

complete/ now uses the original English placeholder names. GrammarUtils therefore
passes English tokenData.verbForms to the plugin. The forms remain Russian; only
lookup keys are added. Existing human-curated Russian entries are retained.
"""
from __future__ import annotations

import ast
import copy
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/user/wspace")
PLUGIN_JSON = ROOT / "work/BepInExPlugin/verb_conjugations.json"
DEPLOY_JSON = ROOT / "work/verb_conjugations.json"
ORIGINAL_TOKENS = ROOT / "original/tokens/verbs.json"
TRANSLATED_TOKENS = ROOT / "translate/tokens/verbs.json"
TRANSLATE_SCRIPT = ROOT / "work/translate_verbs.py"
REPORT = ROOT / "work/english_verb_aliases.tsv"

VALID_ESCAPES = set('"\\/bfnrtu')


def clean_json(text: str) -> str:
    out = []
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


def read_translation_table():
    tree = ast.parse(TRANSLATE_SCRIPT.read_text(encoding="utf-8"), filename=str(TRANSLATE_SCRIPT))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "T" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("T dictionary not found in translate_verbs.py")


def add_suffix(forms, suffix):
    # Russian reflexive suffix attaches to the conjugated non-reflexive form.
    if suffix == "ся":
        return [forms[0] + "сь", forms[1] + "ся", forms[2] + "ся", forms[3] + "ся", forms[4] + "ся", forms[5] + "ся"]
    return forms


def generate_forms(three_sg: str, infinitive: str):
    """Regular present-tense fallback; 3sg is always kept exactly as supplied."""
    if not infinitive:
        infinitive = three_sg
    reflexive = infinitive.endswith("ся") or infinitive.endswith("сь")
    suffix = "ся" if infinitive.endswith("ся") else ("сь" if infinitive.endswith("сь") else "")
    base_inf = infinitive[:-2] if suffix else infinitive
    base_sg = three_sg[:-2] if suffix and three_sg.endswith(("ся", "сь")) else three_sg

    # Determine conjugation from the 3sg form first; this handles many -еть
    # verbs whose infinitive ending alone is ambiguous.
    second = base_sg.endswith("ит") or base_inf.endswith("ить")
    if second:
        stem = base_sg[:-2] if base_sg.endswith("ит") else base_inf[:-2]
        forms = [stem + "ю", stem + "ишь", stem + "ит", stem + "им", stem + "ите", stem + "ят"]
    else:
        if base_sg.endswith(("ает", "яет", "ует", "юет", "ёет")):
            stem = base_sg[:-2]
        elif base_sg.endswith(("ет", "ёт")):
            stem = base_sg[:-2]
        elif base_inf.endswith(("ать", "ять", "еть")):
            stem = base_inf[:-2]
        elif base_inf.endswith("овать"):
            stem = base_inf[:-5] + "у"
        else:
            stem = base_sg
        # For -овать verbs the stem already ends in у (рису-), while ordinary
        # first-conjugation stems use ю/ешь/ет/ем/ете/ют.
        if base_inf.endswith("овать") and not stem.endswith("у"):
            stem += "у"
        forms = [stem + "ю", stem + "ешь", stem + "ет", stem + "ем", stem + "ете", stem + "ют"]
    if reflexive:
        forms = add_suffix(forms, suffix)
    forms[2] = three_sg
    return forms


def main():
    source = load_json(PLUGIN_JSON)
    existing_entries = source["verbs"]
    existing_keys = {str(e["infinitive"]).casefold() for e in existing_entries}
    existing_by_key = {str(e["infinitive"]).casefold(): e["forms"] for e in existing_entries}

    original = load_json(ORIGINAL_TOKENS)[0]["tokens2"]
    translated = load_json(TRANSLATED_TOKENS)[0]["tokens2"]
    table = read_translation_table()

    aliases = {}
    report = []
    missing_translation = []
    generated = 0
    exact = 0

    for index, (english_pair, russian_pair) in enumerate(zip(original, translated)):
        if not english_pair or not english_pair[0]:
            continue
        english_keys = [x for x in english_pair if x]
        russian_values = [x for x in russian_pair if x] if russian_pair else []
        english_singular = english_pair[0]
        t = table.get(english_singular)
        ru_sg = russian_values[0] if russian_values else (t[0] if t else "")
        ru_inf = russian_values[1] if len(russian_values) > 1 else (t[1] if t else ru_sg)
        if not ru_sg and t:
            ru_sg, ru_inf = t
        if not ru_sg:
            missing_translation.append((index, english_pair, russian_pair))
            continue

        forms = None
        # Prefer the existing human-curated 6-form set whenever one of the
        # translated keys is present in the current authoritative table.
        for ru_key in [ru_sg, ru_inf]:
            if ru_key and ru_key.casefold() in existing_by_key:
                forms = list(existing_by_key[ru_key.casefold()])
                exact += 1
                break
        if forms is None:
            forms = generate_forms(ru_sg, ru_inf)
            generated += 1

        for english_key in english_keys:
            key_norm = english_key.casefold()
            if key_norm in existing_keys:
                continue
            aliases[key_norm] = {"infinitive": english_key, "forms": forms}
            report.append((english_key, ru_sg, ru_inf, "curated" if forms[2] == ru_sg and ru_key in existing_by_key else "generated"))

    # Deterministic append order follows the original English token list.
    output_entries = copy.deepcopy(existing_entries)
    for key, entry in aliases.items():
        output_entries.append(entry)

    output = {
        "_comment": (
            "Russian 6-form conjugations. Existing Russian keys are retained. "
            "English aliases are added for the original tokens/verbs.json keys, "
            "so the DLL can conjugate [starts], [says], etc. after placeholders "
            "are restored to their original English names. Forms order: "
            "[1sg, 2sg, 3sg, 1pl, 2pl, 3pl]."
        ),
        "verbs": output_entries,
    }
    encoded = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    PLUGIN_JSON.write_text(encoded, encoding="utf-8")
    DEPLOY_JSON.write_text(encoded, encoding="utf-8")

    with REPORT.open("w", encoding="utf-8") as fh:
        fh.write("english_key\tru_3sg\tru_inf\tsource\n")
        for row in report:
            fh.write("\t".join(row) + "\n")
        fh.write(f"# existing_entries\t{len(existing_entries)}\n")
        fh.write(f"# english_alias_entries\t{len(aliases)}\n")
        fh.write(f"# exact_curated_source_rows\t{exact}\n")
        fh.write(f"# generated_source_rows\t{generated}\n")
        fh.write(f"# missing_translation_rows\t{len(missing_translation)}\n")
        for row in missing_translation:
            fh.write(f"# missing\t{row}\n")

    print(json.dumps({
        "old_entries": len(existing_entries),
        "english_alias_entries_added": len(aliases),
        "new_entries": len(output_entries),
        "curated_source_rows": exact,
        "generated_source_rows": generated,
        "missing_translation_rows": len(missing_translation),
        "plugin_json": str(PLUGIN_JSON),
        "deployment_copy": str(DEPLOY_JSON),
        "report": str(REPORT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
