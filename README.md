# Ostranauts Vodka Edition

Русификация [Ostranauts](https://bluebottlegames.com/games/ostranauts) — космического симулятора выживания с текстовым движком диалогов и процедурной грамматикой. Именно вторая часть — процедурная грамматика — главная сложность: игра не просто вставляет строки по ID, а склоняет глаголы и местоимения на лету, поэтому голого перевода JSON недостаточно.

Репозиторий держит две независимые, но взаимодополняющие части:

| Папка | Роль |
|---|---|
| `OstranautsVodkaEdition/` | Мод в формате нативного загрузчика игры — переведённые данные: диалоги, состояния, описания кораблей, интерфейс. |
| `BepInExPlugin/` | Harmony-патч поверх `Assembly-CSharp.dll`, который на лету спрягает глаголы, склоняет токены-местоимения (`[them-subj]`, `[us-obj]`) и подставляет перевод во встроенное обучение (`TutorialBeat`). |

Первую часть можно поставить саму по себе — текст будет переведён. Вторая часть добавляет грамматическую связность там, где движок собирает фразы динамически.

За основу взят [SerJo2/OstranautsRu](https://github.com/SerJo2/OstranautsRu).

Отдельная благодарность [NicRoss512/OstranautsRuNss](https://github.com/NicRoss512/OstranautsRuNss) за решение, которое помогло с переводом.

---

## Быстрый старт

```text
1. OstranautsVodkaEdition/  →  Ostranauts_Data/Mods/
2. добавить "OstranautsVodkaEdition" в aLoadOrder (loading_order.json)
3. запустить игру
```

Плагин — по желанию, но без него часть динамических фраз останется на английском (подробности ниже).

## Совместимость

| Компонент | Версия |
|---|---|
| Игра | Ostranauts 1.0 |
| Мод данных | Ostranauts Vodka Edition 3.2.0 |
| Плагин | OstranautsRuTranslation 3.0.0 |
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
2. Скопируйте туда `OstranautsVodkaEdition/` целиком.
3. В `Ostranauts_Data/Mods/loading_order.json` добавьте мод в `aLoadOrder` **после** `"core"`:

```json
[
  {
    "strName": "Mod Loading Order",
    "aLoadOrder": ["core", "OstranautsVodkaEdition"],
    "CORE_MOD_NAME": "core"
  }
]
```

4. Запустите игру.

### Часть 2 — плагин (для живой грамматики)

Нужен BepInEx 5.4.x (64-bit Mono) в корне игры — если его ещё нет, распакуйте его первым, до плагина.

Положите в `Ostranauts/BepInEx/plugins/`:

```text
OstranautsRuTranslation.dll
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

### Что нужно

- .NET SDK (6.0 или новее) — команда `dotnet` должна быть доступна в терминале.
- Установленная копия Ostranauts (нужна как источник референс-сборок).
- Установленный в игру BepInEx 5.4.x (нужен как источник `BepInEx.dll` и `0Harmony.dll`).

### 1. Собрать референс-сборки в `lib/`

Сборка идёт не против полного SDK игры, а против DLL-заглушек ("референс-сборок") — их компилятору достаточно, чтобы знать сигнатуры типов, а не полный код. Папка `BepInExPlugin/lib/` в репозитории уже содержит нужный набор, но если её нужно пересобрать с нуля (например, после обновления игры или BepInEx), скопируйте туда следующие файлы:

Из `Ostranauts_Data/Managed/` (папка с managed-сборками игры, лежит рядом с `Ostranauts.exe`):

```text
Assembly-CSharp.dll
UnityEngine.dll
UnityEngine.CoreModule.dll
UnityEngine.UI.dll
Unity.TextMeshPro.dll
```

Из корня игры, `BepInEx/core/` (появляется после установки BepInEx):

```text
BepInEx.dll
0Harmony.dll
```

Итого в `BepInExPlugin/lib/` должны лежать все 7 DLL. Ссылки на них уже прописаны в `OstranautsRuTranslation.csproj` (`<HintPath>lib\...</HintPath>`) — добавлять новые файлы в `.csproj` не нужно, пока набор не меняется.

### 2. Собрать сам плагин

```bash
dotnet build BepInExPlugin/OstranautsRuTranslation.csproj -c Release
```

Собирается под `netstandard2.1`/x64. Результат появится в `BepInExPlugin/bin/Release/netstandard2.1/OstranautsRuTranslation.dll`.

### 3. Установить собранный плагин в игру

Скопируйте в `Ostranauts/BepInEx/plugins/` (создайте папку `plugins`, если её нет) три файла:

```text
BepInExPlugin/bin/Release/netstandard2.1/OstranautsRuTranslation.dll  →  BepInEx/plugins/
BepInExPlugin/verb_conjugations.json                                     →  BepInEx/plugins/
BepInExPlugin/tutorial_translations.json                                 →  BepInEx/plugins/
```

Два `.json`-файла плагин читает по относительному пути рядом со своей DLL — если их не скопировать, спряжение глаголов и перевод обучения не заработают (лог покажет `0 conjugations`/`0 translations` вместо чисел, см. проверку в разделе выше).

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

**Местоимения и падежи.** Не глаголы — обрабатываются отдельно через `OstranautsVodkaEdition/data/tokens/grammar.json` (категории `subj`, `pos`, `obj`, `reflexive`, стяжения `contractIs/Has/Will/Would`):

```text
[them-subj] → он / она / они / оно
[them-obj]  → его / её / их
[us-obj]    → меня / тебя / его / её / их
```

**Артикли.** Движок иногда добавляет `the` перед предметами — патч на `GrammarUtils.AttemptProperName` вырезает его для русской версии (`the door` → `дверь`).

**TutorialBeat.** Название, описание и текст завершения обучающих целей берутся из `tutorial_translations.json` и подставляются при создании цели и обновлении панели Objectives; маркеры `{glyph:...}` заменяются на актуальные клавиши через `InputManager`. Для цели `RestoreNavStation` проверка идёт по внутреннему `strDuty == "Restore"`, а не по переведённому заголовку кнопки — иначе перевод сломал бы завершение цели.

**Escape-меню.** Кнопки паузы (`OPTIONS`/`SAVE`/`LOAD`/`MAIN MENU`/`SHIP EDITOR`/`QUIT APP` и ссылки STEAM GUIDE/PDF/FORUMS/DISCORD) — не строки из `strings.json` и не C#-литералы, а текст, запечённый прямо в `TextMeshProUGUI`-компонентах сцены (`resources.assets`), который `CrewSim.Awake` один раз находит по пути `transform.Find(...)` и не трогает после. Патч на `CrewSim.Awake` повторяет те же пути и переопределяет `.text`; индикатор последнего сохранения ("No Save"/"Last Save:...") патчится отдельно через `GUISaveIndicator.EstablishSave`/`Reset`, так как он перезаписывается заново при каждом сохранении.

**Редактор внешности персонажа (Sink Mirror / Rin-人).** По той же причине, что и Escape-меню, — текст запечён в `TextMeshProUGUI` на префабе, а не идёт через `DataHandler.GetString()`. Патч на `GUIChargenBody.Awake` переопределяет подписи разделов ("МЕСТОИМЕНИЕ", "ФЛИРТУЕТ С", "ИМЯ"), переключатели пола (ОН/ОНА/ОНИ в обеих секциях), кнопки ("ГОТОВО!", "СЛУЧАЙНО") и все 13 подписей атрибутов внешности (кожа, волосы, шрам, очки, борода, зрачки, глаза, нос, зубы, губы, шея, голова, тело). Название приложения "Rin-人" не переводится — это логотип-бренд.

**Киоск карьеры (Build-a-Resume Center).** Та же история: заголовок раздела, подписи шагов трекера (СТАРТ/ОФОРМЛЕНИЕ КАРЬЕРЫ/РЕГИСТРАЦИЯ СУДНА/ФИНИШ), заголовок боковой панели ("Сводка по карьере"), подписи ламп-индикаторов ("НЕ ГОТОВО"/"РЕЗЮМЕ ГОТОВО") и кнопка "ОТПРАВИТЬ" запечены на префабе `GUIChargenCareer` — патч на `GUIChargenCareer.Awake` переопределяет их так же, как для Sink Mirror.

## Известные ограничения

- Прилагательные пока не согласуются по роду/числу в полном объёме — движок не комбинирует прилагательное и существительное во время выполнения (только статичные готовые пары в генераторе имён кораблей), поэтому у этого ограничения нет реальной точки для патча.
- Прошедшее время связки "быть" (`[was]`/`[were]`, например `"[us] [was] poisoned to death."`) теперь согласуется по роду через `genderForms` в `verb_conjugations.json` и правку в `Patch_GrammarUtils_Verb` — «был»/«была»/«было»/«были» выбираются по `InflectionIndex` сущности. Остальные глаголы прошедшего времени в игре не встречаются.
- Часть строк зашита прямо в `Assembly-CSharp.dll` и нуждается в собственных Harmony-патчах, которых пока нет.

## Лицензия

Фанатский перевод, не связан с Blue Bottle Games официально. Права на игру, бренды и материалы принадлежат правообладателям. Форки и правки — welcome.
