# -*- coding: utf-8 -*-
"""Stage 2: append missing 1.0 entries to conditions_plots.json (translated)."""
import json, re, io

GAME = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/'
MOD = 'D:/Wello/OstranautsVodka/ostranautsRuNss/data/conditions/conditions_plots.json'
GFILE = GAME + 'conditions/conditions_plots.json'

g = json.load(open(GFILE, encoding='utf-8-sig'))
m = json.load(open(MOD, encoding='utf-8'))
mset = {e['strName'] for e in m}
missing = [e for e in g if e['strName'] not in mset]

# Hand-translated prose fields, keyed by strName -> {field: value}
PROSE = {
    'Plot_Ceres_FactionRatings_Complete': {
        'strDesc': 'Репутация у фракций поднята достаточно, чтобы продвинуться дальше тайных вмешательств.'},
    'Plot_Ceres_Dead_Drop_Black_Hat_Is_Active_Xinhua': {
        'strDesc': 'Игрок готов выполнить задание «чёрной шляпы» для Xinhua.'},
    'Plot_Ceres_Dead_Drop_Black_Hat_Is_Active_Titan': {
        'strDesc': 'Игрок готов выполнить задание «чёрной шляпы» для Titan.'},
    'PLOT_Ceres_Brain_Case': {
        'strDesc': 'Предмет — мозговой контейнер для сюжета Ceres.'},
    'Plot_PLOT_Ceres_The_Scholar_Establish_Contact_Completed': {
        'strDesc': 'Установлен контакт с посредником в Прокси-войне на Ceres.'},
    'ValkyrieReqA': {'strDesc': 'Выполнено одно из требований для Валькирии.'},
    'ValkyrieReqB': {'strDesc': 'Выполнено одно из требований для Валькирии.'},
    'PlayerLearnedOrtega': {'strDesc': 'Игрок нашёл имя Ортеги в квартире Чунга.'},
    'PlayerLearnedPanTao': {'strDesc': 'Игрок нашёл имя Пана в квартире Чунга.'},
    'TriggerCeresP4XinhuaIntro': {'strDesc': 'CeresP4Intro готов к запуску.'},
    'TriggerCeresP4TitanIntro': {'strDesc': 'CeresP4Intro готов к запуску.'},
    'ChoongTimer': {'strNameFriendly': 'Растёт по мере приближения Чунга'},
    'DeadUniverse': {
        'strNameFriendly': 'Мёртвая вселенная',
        'strDesc': 'Ты бродишь по кладбищу старого мира в поисках места упокоения для себя.'},
}

COMPLETED_RE = re.compile(r'^Completed (.+)$')

def translate_field(name, field, value):
    if name in PROSE and field in PROSE[name]:
        return PROSE[name][field]
    if not value:
        return value
    if value == name:  # friendly repeats internal ID -> leave as-is (matches original)
        return value
    mobj = COMPLETED_RE.match(value)
    if mobj:
        return 'Успешно завершен сюжет: ' + mobj.group(1)
    return value  # leave untouched (should not happen after prose map)

added = []
for e in missing:
    ne = dict(e)  # preserve all keys/structure verbatim
    for f in ('strNameFriendly', 'strDesc'):
        if f in ne:
            ne[f] = translate_field(e['strName'], f, e.get(f, ''))
    added.append(ne)

# Report any residual untranslated prose (latin desc that's not Completed/ID)
cyr = re.compile('[а-яА-ЯёЁ]')
resid = []
for e in added:
    d = e.get('strDesc', '')
    if d and not cyr.search(d) and not d.startswith('Успешно завершен'):
        resid.append((e['strName'], d))
print('residual untranslated desc:', len(resid))
for n, d in resid:
    print('  ', n, '||', repr(d))

m2 = m + added
json.dump(m2, io.open(MOD, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('added', len(added), 'entries; new total', len(m2))
