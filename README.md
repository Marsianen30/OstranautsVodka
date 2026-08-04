# Ostranauts Russian Translation

Русская локализация [Ostranauts](https://bluebottlegames.com/games/ostranauts) в двух частях:

1. **`ostranautsRuNss/`** — мод в нативном формате загрузчика модов Ostranauts: переведённые JSON-файлы игровых данных (условия, взаимодействия, диалоги, описания кораблей, справочники, интерфейс и т.д.).
2. **`BepInExPlugin/`** — плагин BepInEx/Harmony, который на лету обрабатывает то, что нельзя перевести статичным JSON: спряжение русских глаголов, склонение местоимений/токенов (`[them-subj]`, `[us-obj]` и т.п.) и перевод встроенных обучающих целей `TutorialBeat`.

Обе части independent, но рассчитаны на совместную установку: JSON-мод даёт переведённый текст, плагин — грамматически верно его склоняет и подставляет в динамические фразы.

За основу взят https://github.com/SerJo2/OstranautsRu

## Текущая версия

- Мод данных: **ostranautsRuNss 3.2.0**, под игру **Ostranauts 0.15.1.20**
- Плагин: **OstranautsRuTranslationNss 3.0.0**
- Загрузчик плагина: **BepInEx 5.4.23.5 + Harmony**, `netstandard2.1`, x64

## Что переведено

- Условия и состояния персонажей (`conditions`, `conditions_simple`, `conditions_plots`, `conditions_pda`, `conditions_stakes*`).
- Взаимодействия и диалоги, включая полный набор локационных файлов преступлений (`interactions_crime_*`, `conditions_crime_*` — BCER, EJDR, HQCH, JATL, JFTS, MHNG, MSUZ, MTRS, MVOL, SVIR).
- Описания кораблей (`ships/`, 102 файла).
- Сюжетные ветки (плоты) Ceres P4, 79 Au, Ceres BC.
- Справочные материалы: `manpages` (руководства), `archived_content` (архивные диалоги), `guipropmaps` (подписи интерфейса), `transit` (метки транзитных зон), `condtrigs` (читаемые названия условий-триггеров).
- Общие строки интерфейса (`strings.json`) и токены грамматики (`tokens/grammar.json`).

Не переводились (сознательно): собственные имена, коды/enum-идентификаторы, внутренние ID условий и путей спрайтов — они не показываются игроку как текст.

## Установка

### 1. Мод данных (обязательно)

1. Скопируйте папку `ostranautsRuNss/` в `Ostranauts_Data/Mods/` (путь показывает экран игры **Options → Files**, либо **Главное меню → MODS → Open Mod Folder**).
2. Откройте `Ostranauts_Data/Mods/loading_order.json` и добавьте `"ostranautsRuNss"` в список `aLoadOrder` **после** `"core"`:

```json
[
  {
    "strName": "Mod Loading Order",
    "aLoadOrder": [
      "core",
      "ostranautsRuNss"
    ],
    "CORE_MOD_NAME": "core"
  }
]
```

3. Запустите игру — переведённые файлы данных подхватятся автоматически.

### 2. Плагин BepInEx (для грамматики и обучения)

Если BepInEx ещё не установлен в игре, сначала поставьте BepInEx 5.4.x (64-bit Mono) в корень игры — появятся папки `BepInEx/core`, `BepInEx/plugins` и т.д.

Скопируйте в `Ostranauts/BepInEx/plugins/`:

```text
Ostranauts/BepInEx/plugins/
├── OstranautsRuTranslationNss.dll
├── verb_conjugations.json
└── tutorial_translations.json
```

DLL собирается из `BepInExPlugin/` (см. раздел «Сборка» ниже); `verb_conjugations.json` и `tutorial_translations.json` лежат там же готовыми.

После запуска в `BepInEx/LogOutput.log` должны появиться строки:

```text
[RU] Plugin starting...
[RU] Loaded ... verb conjugations
[RU] Loaded ... TutorialBeat translations
[RU] Grammar replaced
[RU] Harmony patches applied
```

Если видно `0 plugins to load` — DLL лежит не в `BepInEx/plugins`, либо используется другая установка BepInEx.

## Как работает плагин

Плагин не заменяет `Assembly-CSharp.dll`, а устанавливает Harmony-патчи во время запуска игры.

### Загрузка внешних таблиц

При запуске загружаются:

- `verb_conjugations.json` — русские формы глаголов;
- `tutorial_translations.json` — перевод целей `TutorialBeat`.

JSON загружается через встроенный `LitJson`.

### Спряжение глаголов

Оригинальная `GrammarUtils` различает только базовую форму и форму 3-го лица — для русского этого недостаточно.

Плагин перехватывает `GrammarUtils.Verb`, выбирает форму по субъекту и записывает её в буфер игрового текста.

Порядок форм:

```text
[1sg, 2sg, 3sg, 1pl, 2pl, 3pl]
```

Пример:

```json
{
  "infinitive": "starts",
  "forms": ["начинаю", "начинаешь", "начинает", "начинаем", "начинаете", "начинают"]
}
```

### Надёжная регистрация плейсхолдеров

Игра вызывает обработчик глагола только для ключей, зарегистрированных в `dictVerbs`. Плагин:

1. загружает ключи из `verb_conjugations.json`;
2. регистрирует английские ключи оригинала и русские alias-ключи;
3. перехватывает `DataHandler.PrepareToken` и дополнительно распознаёт известные глаголы после повторной загрузки игровых token-таблиц;
4. перехватывает `GrammarUtils.Verb`;
5. выбирает форму по `SentenceEntity.InflectionIndex`.

Это предотвращает появление необработанных токенов вроде `[сидит]`.

### Русская грамматика

`ostranautsRuNss/data/tokens/grammar.json` содержит категории:

- `subj` — субъектная форма;
- `pos` — притяжательная форма;
- `obj` — объектная форма;
- `reflexive` — возвратная форма;
- `contractIs`, `contractHas`, `contractWill`, `contractWould`.

Примеры:

```text
[them-subj] → он / она / они / оно
[them-obj]  → его / её / их
[us-obj]    → меня / тебя / его / её / их
```

Местоименные плейсхолдеры не являются глаголами и обрабатываются через `grammar.json`, а не плагин напрямую.

### Названия предметов

Оригинальный движок добавляет `the ` перед некоторыми неодушевлёнными объектами. Плагин перехватывает `GrammarUtils.AttemptProperName` и удаляет английский артикль для русской локализации: `the door` → `дверь`.

### TutorialBeat

Тексты встроенных обучающих целей вынесены в `tutorial_translations.json`. Плагин переводит название цели, описание и текст завершения при создании цели и при обновлении панели Objectives. Маркеры `{glyph:...}` заменяются текущими клавишами игры через `InputManager`.

Для `RestoreNavStation` проверяется стабильное внутреннее поле `strDuty == "Restore"`, а не локализованный заголовок взаимодействия — это предотвращает поломку завершения цели после перевода названия кнопки.

## Сборка плагина

```bash
dotnet build BepInExPlugin/OstranautsRuTranslation.csproj -c Release
```

DLL собирается под `netstandard2.1`, `x64`, с использованием reference-версий сборок из `BepInExPlugin/lib/` (взяты из установленной копии игры).

## Ограничения

- Полное согласование прилагательных по роду и числу пока не реализовано.
- Прошедшее время требует отдельной грамматической системы.
- Часть жёстко зашитых игровых строк находится внутри `Assembly-CSharp.dll` и требует отдельных Harmony-патчей.

## Лицензия и благодарности

Проект является фанатской локализацией и не связан официально с Blue Bottle Games. Названия игры, бренды и игровые материалы принадлежат их правообладателям.

Если есть желание помочь с доведением до ума — сделайте форк.
