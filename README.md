# OstranautsRu

Русификация [Ostranauts](https://bluebottlegames.com/games/ostranauts) — космического симулятора выживания с текстовым движком диалогов и процедурной грамматикой. Именно вторая часть — процедурная грамматика — главная сложность: игра не просто вставляет строки по ID, а склоняет глаголы и местоимения на лету, поэтому голого перевода JSON недостаточно.

Репозиторий держит две независимые, но взаимодополняющие части:

| Папка | Роль |
|---|---|
| `OstranautsRu/` | Мод в формате нативного загрузчика игры — переведённые данные: диалоги, состояния, описания кораблей, интерфейс. |
| `BepInExPlugin/` | Harmony-патч поверх `Assembly-CSharp.dll`, который на лету спрягает глаголы, склоняет токены-местоимения (`[them-subj]`, `[us-obj]`) и подставляет перевод во встроенное обучение (`TutorialBeat`). |

Первую часть можно поставить саму по себе — текст будет переведён. Вторая часть добавляет грамматическую связность там, где движок собирает фразы динамически.

За основу взят [SerJo2/OstranautsRu](https://github.com/SerJo2/OstranautsRu).

---

## Быстрый старт

```text
1. OstranautsRu/  →  Ostranauts_Data/Mods/
2. добавить "OstranautsRu" в aLoadOrder (loading_order.json)
3. запустить игру
```

Плагин — по желанию, но без него часть динамических фраз останется на английском (подробности ниже).

## Совместимость

| Компонент | Версия |
|---|---|
| Игра | Ostranauts 0.15.1.20 |
| Мод данных | OstranautsRu 3.2.0 |
| Плагин | OstranautsRuTranslationNss 3.0.0 |
| Загрузчик | BepInEx 5.4.23.5 + Harmony, netstandard2.1, x64 |

## Объём перевода

- Состояния и условия персонажей: `conditions`, `conditions_simple`, `conditions_plots`, `conditions_pda`, `conditions_stakes*`.
- Диалоги и взаимодействия — включая все 10 локационных наборов преступлений (`interactions_crime_*` / `conditions_crime_*`: BCER, EJDR, HQCH, JATL, JFTS, MHNG, MSUZ, MTRS, MVOL, SVIR).
- 102 описания кораблей (`ships/`).
- Сюжетные линии Ceres P4, 79 Au, Ceres BC.
- Справочники: руководства (`manpages`), архивные диалоги (`archived_content`), подписи интерфейса (`guipropmaps`), метки транзитных зон (`transit`), читаемые названия условий-триггеров (`condtrigs`).
- Общие строки интерфейса (`strings.json`) и таблица грамматических токенов (`tokens/grammar.json`).

Осознанно не переводились: собственные имена, коды/enum, внутренние ID и пути спрайтов — игрок их не видит как текст.

## Установка

### Часть 1 — данные (обязательно)

1. Найдите папку модов: **Главное меню → MODS → Open Mod Folder** (или **Options → Files**).
2. Скопируйте туда `OstranautsRu/` целиком.
3. В `Ostranauts_Data/Mods/loading_order.json` добавьте мод в `aLoadOrder` **после** `"core"`:

```json
[
  {
    "strName": "Mod Loading Order",
    "aLoadOrder": ["core", "OstranautsRu"],
    "CORE_MOD_NAME": "core"
  }
]
```

4. Запустите игру.

### Часть 2 — плагин (для живой грамматики)

Нужен BepInEx 5.4.x (64-bit Mono) в корне игры — если его ещё нет, распакуйте его первым, до плагина.

Положите в `Ostranauts/BepInEx/plugins/`:

```text
OstranautsRuTranslationNss.dll
verb_conjugations.json
tutorial_translations.json
```

Последние два файла и исходники DLL лежат в `BepInExPlugin/` — про сборку см. ниже.

Проверка: в `BepInEx/LogOutput.log` после запуска должны появиться

```text
[RU] Plugin starting...
[RU] Loaded ... verb conjugations
[RU] Loaded ... TutorialBeat translations
[RU] Grammar replaced
[RU] Harmony patches applied
```

`0 plugins to load` в логе значит, что DLL не в той папке или BepInEx стоит отдельно от `plugins/`.

## Сборка плагина

```bash
dotnet build BepInExPlugin/OstranautsRuTranslation.csproj -c Release
```

Собирается под `netstandard2.1`/x64 против референс-сборок в `BepInExPlugin/lib/` (сняты с установленной копии игры и BepInEx).

## Что делает плагин и почему это не просто DLL-замена

Плагин не трогает `Assembly-CSharp.dll` — все правки идут через Harmony-патчи в момент запуска.

**Спряжение глаголов.** Родная `GrammarUtils` знает только базовую форму и форму 3-го лица — этого мало для русского. Патч на `GrammarUtils.Verb` подбирает нужную форму из `verb_conjugations.json` по субъекту фразы:

```text
порядок форм: [1sg, 2sg, 3sg, 1pl, 2pl, 3pl]
```

```json
{ "infinitive": "starts", "forms": ["начинаю", "начинаешь", "начинает", "начинаем", "начинаете", "начинают"] }
```

**Регистрация плейсхолдеров.** Игра дёргает обработчик глагола только для ключей, уже известных `dictVerbs` — иначе получаются необработанные токены типа `[сидит]`. Плагин заранее регистрирует и английские, и русские alias-ключи, перехватывает `DataHandler.PrepareToken` при перезагрузке токен-таблиц и выбирает форму по `SentenceEntity.InflectionIndex`.

**Местоимения и падежи.** Не глаголы — обрабатываются отдельно через `OstranautsRu/data/tokens/grammar.json` (категории `subj`, `pos`, `obj`, `reflexive`, стяжения `contractIs/Has/Will/Would`):

```text
[them-subj] → он / она / они / оно
[them-obj]  → его / её / их
[us-obj]    → меня / тебя / его / её / их
```

**Артикли.** Движок иногда добавляет `the` перед предметами — патч на `GrammarUtils.AttemptProperName` вырезает его для русской версии (`the door` → `дверь`).

**TutorialBeat.** Название, описание и текст завершения обучающих целей берутся из `tutorial_translations.json` и подставляются при создании цели и обновлении панели Objectives; маркеры `{glyph:...}` заменяются на актуальные клавиши через `InputManager`. Для цели `RestoreNavStation` проверка идёт по внутреннему `strDuty == "Restore"`, а не по переведённому заголовку кнопки — иначе перевод сломал бы завершение цели.

## Известные ограничения

- Прилагательные пока не согласуются по роду/числу в полном объёме.
- Прошедшее время требует отдельной грамматической модели — сейчас не реализовано.
- Часть строк зашита прямо в `Assembly-CSharp.dll` и нуждается в собственных Harmony-патчах, которых пока нет.

## Лицензия

Фанатский перевод, не связан с Blue Bottle Games официально. Права на игру, бренды и материалы принадлежат правообладателям. Форки и правки — welcome.
