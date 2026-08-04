# -*- coding: utf-8 -*-
import sys, json, io
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/archived_content/archived_content.json'
OUT = 'ostranautsRuNss/data/archived_content/archived_content.json'

TR = {
    'SOCPoliceShakedownNameDrop': (
        'Упомянуть контакт-менеджера OKLG',
        '[us] говорит [them], что было бы жаль, если бы об этом узнал [3rd].',
    ),
    'SOCPoliceShakedownNameDropAllow': (
        'Реакция на упоминание менеджера OKLG',
        '[us] явно теряется при упоминании [3rd] и бормочет извинения.',
    ),
    'ENCPoliceBoardAllow': (
        'Согласиться',
        '[us] соглашается встретиться с [them].',
    ),
    'ENCPoliceBoardIgnore': (
        'Игнорировать',
        '[us] игнорирует [them].',
    ),
    'ENCPoliceBoardGetAttention': (
        'Привлечь внимание',
        '[us] требует внимания [them].',
    ),
    'ENCPoliceBoardForceResponse': (
        'Подтвердить',
        '[us] оборачивается к [them].',
    ),
    'ENCPoliceBoardThinking': (
        'Раздумье',
        '[us] обдумывает, что делать с [them].',
    ),
    'ENCPoliceBoardQuestioning': (
        'Рутинный допрос',
        '[us] расспрашивает [them] по некоторым обычным вопросам.',
    ),
    'ENCPoliceBoardQuestioningAnswerTruthfully': (
        'Ответить честно',
        '[us] отвечает [them] по мере своих воспоминаний.',
    ),
    'ENCPoliceBoardQuestioningAnswerEvasively': (
        'Ответить уклончиво',
        '[us] не лжёт напрямую, но и правду особо не выпячивает.',
    ),
    'ENCPoliceBoardQuestioningLie': (
        'Лгать',
        '[us] врёт, глядя [them] прямо в глаза.',
    ),
    'ENCPoliceBoardLieBelieves': (
        'Принять',
        '[us], похоже, верит лжи [them].',
    ),
    'ENCPoliceBoardSuspiciousQuestioning': (
        'Подозрительный допрос',
        '[us] думает, что [them] что-то скрывает, и допрос становится жёстче.',
    ),
    'ENCPoliceBoardFishForBribe': (
        'Допрос',
        '[us] невзначай намекает, что [them] стоило бы дать взятку.',
    ),
}

d = load_json_file(G)
count = 0
for e in d:
    name = e.get('strName')
    if name in TR:
        title, desc = TR[name]
        e['strTitle'] = title
        e['strDesc'] = desc
        count += 1

json.dump(d, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('replaced', count, 'total', len(d))
