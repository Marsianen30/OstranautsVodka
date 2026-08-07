# Ostranauts Localization: Technical Guide and FAQ

[Russian version](LOCALIZATION_RU.md) · [Project README](README.md) · [Russian glossary and style guide](script/stage3_glossary.md)

This document is for authors of Ostranauts localizations. It covers more than string translation: a changed JSON behavior field can break a plot chain, block a tutorial, or send a character to the wrong region.

## Project map

The localization has two independent layers:

| Layer | Location | Purpose |
|---|---|---|
| Mod data | `OstranautsVodkaEdition/data/**` | Dialogues, conditions, descriptions, encyclopedia entries, and most UI strings |
| BepInEx/Harmony plugin | `BepInExPlugin/**` | Dynamic grammar, tutorials, Unity-prefab text, and other strings not exposed through data |

Before starting, obtain source data from the same game version. For a local project install this is normally:

```text
Ostranauts_Data/StreamingAssets/data/
```

Russian style, forms of address, names, and token conventions are documented in the [glossary](script/stage3_glossary.md). For another locale, create a locale-specific glossary, but never change internal IDs or tokens.

## Safe workflow

1. Find the corresponding record in the original game data.
2. Match it with the mod record by `strName`.
3. Translate only player-visible fields, such as `strTitle`, `strDesc`, `strTooltip`, `strNameFriendly`, and `strNameShort`.
4. Preserve every token, tag, line break, and the record structure.
5. Compare the mod structurally with the original, review the diff, and test the result in-game.

Do not replace a record wholesale with a prepared “translated” version unless its structure has been verified against the original data for the same game version. This project previously had to restore **437 non-text fields** after such damage: JSON loaded and Russian text appeared, but plot screens, conditions, and achievements were broken.

### Fields that must not be translated or changed without understanding the game code

The following fields drive game behavior. Their values should normally match the original:

- `strName` — internal record ID;
- `aInverse` — links between actions and plot screens;
- `CTTestUs`, `CTTestThem`, `ShipTestUs`, `ShipTestThem`, `LootCondsUs`, `LootCondsThem` — conditions, checks, and condition grants;
- `strRaiseUI`, `strSubUI`, `bPause`, `strImage`, `strMusic` — dedicated plot UI, artwork, pause state, and music;
- `strTutorialKey`, `strSetPlotObjective` — tutorial and objective keys;
- `strAchievementUnlock` — achievement ID;
- `strTeleportRegID`, `strTargetPoint`, `strThemType` — destination, target type, and interaction point;
- resource paths, prefab names, region codes, enum-like values, and reference arrays.

For example, translating `strTutorialKey` breaks lookup of the relevant tutorial step, and a damaged `aInverse` can redirect a plot screen to `ENCFinish`. Do not translate IDs, codes, or paths just because they look like English words.

## Data formats and JSON

### Normal records

Most files are JSON arrays of objects. Use `strName` to match an original record to a mod record. Do not remove records that are absent from the original: they may be intentional localization additions.

### Flat `aValues` tables

`strings.json` and some condition files use a flat `aValues` array, where one logical rule is stored in several adjacent entries. Do not reorder, remove, or manually insert entries in these tables: preserve order, count, and every behavior-bearing cell. Change only the known text-value position of a record.

### Token and grammar tables

Files such as `data/tokens/grammar.json` are not ordinary text dictionaries. Their keys, variant order, and syntax matter. Do not replace an English token key with a localized word unless plugin support has been verified.

### Why a strict JSON parser can be the wrong tool

Original game files are not always strict JSON for Python's standard library. They can contain UTF-8 BOMs, full-line `//` comments, raw control characters inside strings, and non-standard escape sequences.

Use the functions in `script/ostranauts_tools/json_utils.py` and the project tools for reading and bulk processing, rather than blindly using `json.load()` or `json.dump()`. Run every rewriting tool on a copy or branch first, then inspect `git diff`.

## Tokens, grammar, and markup

Preserve exactly:

- square-bracket tokens: `[us]`, `[them]`, `[us-obj]`, `[them-pos]`;
- verb tokens such as `[watches]`, `[asks]`, `[hacks]`;
- HTML/TMP markup: `<b>`, `<color=...>`, `<size=...>`;
- `\n` line breaks;
- tutorial markers `{glyph:...}`;
- gender-condition constructs and the count/order of `|` variants.

For Russian, keeping English verb tokens is preferred because they are the most reliable keys for grammar processing. The plugin supplies Russian forms through:

- `OstranautsVodkaEdition/data/tokens/grammar.json` — pronouns, cases, and helper grammar;
- `BepInExPlugin/verb_conjugations.json` — six verb forms: 1st/2nd/3rd person, singular/plural;
- `BepInExPlugin/Main.cs` — Harmony patches selecting forms, handling gendered past forms, and removing the English `the` article.

Do not change a global token merely because it reads badly in one sentence. For example, `[learns]` can mean “studies” in one context but “learns about” in a news item. Fix the specific sentence instead of breaking other uses.

## Tutorials and behavior-coupled text

Tutorial objective text is stored in `BepInExPlugin/tutorial_translations.json` and injected by the plugin. `{glyph:...}` markers are required: the plugin replaces them with the player's current bindings.

Never use a translated visible label as a completion condition. In this project, the `RestoreNavStation` objective is checked by the stable internal field `strDuty == "Restore"`, not by a localized button title. Apply this rule to objectives, conditions, triggers, and plot transitions in every locale.

## When the text is not in JSON

A correct data translation might not appear in-game because strings fall into four categories:

| String type | What to do |
|---|---|
| Mod data | Find the record under `OstranautsVodkaEdition/data/**` and translate its visible field |
| Game code | Find a safe interception point and add a Harmony patch |
| Unity-prefab-baked text | After `Awake`/initialization, find `TMP_Text` through a stable `transform.Find(...)` path and replace `.text` |
| Text overwritten at runtime | Patch the specific refresh/save/update method, not only `Awake` |

Existing examples in `BepInExPlugin/Main.cs` include:

- tutorials and dynamic objectives;
- the Escape menu and last-save indicator;
- Sink Mirror (`GUIChargenBody.Awake`);
- Career Kiosk (`GUIChargenCareer.Awake`);
- dialogue window and radial context menu;
- translated manual-image priority and override-table loading.

`transform.Find(...)` paths, component names, and method signatures depend on the game version. Recheck them in-game and in BepInEx logs after each Ostranauts update.

## TextMeshPro fonts

If a locale needs glyphs absent from the game's font, create a runtime `TMP_FontAsset` and apply it only to the required components. This project loads `Montserrat-Bold.ttf` beside the plugin DLL for dialogue and context-menu text, while retaining the original font as a fallback.

Do not distribute commercial fonts without permission. For fonts packaged with a mod, use a license that permits redistribution and include the license text next to the asset.

## Validation tools

Use explicit paths rather than relying on outdated defaults:

```bash
# Translation coverage and remaining English strings
python script/ostranauts_tools/translation_stats.py \
  --game-path "D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data" \
  --mod-path "OstranautsVodkaEdition/data" \
  --sort-by remaining --top 20

# Token, placeholder, and suspicious original-text matches
python script/audit_translation.py

# Structural validation; report only first
python script/ostranauts_tools/validate_mod.py \
  --game-path "D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data" \
  --mod-path "OstranautsVodkaEdition/data" --norus
```

`translation_stats.py` measures Cyrillic coverage, not translation quality. `audit_translation.py` helps detect token omissions but cannot replace reading the text and launching the game. Before using modes that mutate data (`--apply`, bulk injection, or synchronization), create a backup/branch and review the diff. Do not use aggressive cleanup modes until you have confirmed that they will not remove intentional localization additions.

## Final pre-release checklist

- [ ] Every changed JSON file loads through the same tolerant parser used by the project tools.
- [ ] Structural comparison contains no differences outside approved text fields.
- [ ] All tokens, tags, `\n`, `{glyph:...}`, and `|` variants are preserved.
- [ ] `git diff` contains no accidental changes to IDs, conditions, paths, `aInverse`, or UI fields.
- [ ] The mod launches without data-loading errors.
- [ ] `BepInEx/LogOutput.log` shows conjugation/tutorial loading and Harmony patching.
- [ ] Dynamic pronouns and verbs, one tutorial step, one dedicated plot screen, and one prefab-baked UI screen were tested.
- [ ] For a new game version, prefab paths and Harmony patch points were revalidated.

## What to include with a contribution

For review, state the game version, changed files and `strName` records, validation commands run, in-game smoke-test results, and known untested scenarios. Small, focused diffs are safer to review than mass reformatting.
