#!/usr/bin/env python3
"""
Фикс для interactions_encounters: убирает ложные плейсхолдеры
Причина: в dict.json были обычные слова "они", "его", "их" — они встречаются в любом русском тексте
и превращаются в [them-subj] даже если в оригинале плейсхолдеров не было.

Фикс: меняем словарь на уникальные токены которые не встречаются в естественном тексте:
  [us] -> ИванЮС, [them] -> ПётрЗЭМ, [them-subj] -> ПётрСАБЗЭМ и т.д.
И чистим уже переведённый файл: если в оригинале не было плейсхолдеров, а в переводе появились — возвращаем обратно русские слова.
"""

import json, re
from pathlib import Path

# Новый уникальный словарь — не встречается в естественном русском
NEW_DICT = {
    "[us]": "ИванЮС",
    "[them]": "ПётрЗЭМ",
    "[3rd]": "СидорТРТ",
    "[us-pos]": "ИванПОС",
    "[them-pos]": "ПётрПОС",
    "[us-subj]": "ИванСАБ",
    "[them-subj]": "ПётрСАБ",
    "[us-obj]": "ИванОБЖ",
    "[them-obj]": "ПётрОБЖ",
    "[3rd-pos]": "СидорПОС",
    "[3rd-subj]": "СидорСАБ",
    "[3rd-obj]": "СидорОБЖ",
    "[us-reflexive]": "ИванРЕФ",
    "[is]": "",
    "[has]": "",
    "[was]": "былБЫЛ",
    "[were]": "былиБЫЛИ",
    "[us-contractIs]": "ИванКОНТР",
    "[them-contractIs]": "ПётрКОНТР",
}

# Обратный для чистки: слово -> плейсхолдер
REV_NEW = {v:k for k,v in NEW_DICT.items() if v}

# Старый плохой словарь который дал ложные срабатывания
OLD_DICT = {
    "[us]": "Иван",
    "[them]": "Пётр",
    "[3rd]": "Сидор",
    "[us-pos]": "его",
    "[them-pos]": "их",
    "[us-subj]": "он",
    "[them-subj]": "они",
    "[us-obj]": "него",
    "[them-obj]": "них",
    "[3rd-pos]": "его",
    "[is]": "",
    "[has]": "",
}

# Для чистки: старые русские слова -> плейсхолдеры которые надо убрать если в оригинале их не было
OLD_REV = {v:k for k,v in OLD_DICT.items() if v}

placeholder_pat = re.compile(r'\[[^\]]+\]')

def clean_file(orig_path, trans_path, out_path):
    with open(orig_path,'r',encoding='utf-8') as f:
        orig=json.load(f)
    with open(trans_path,'r',encoding='utf-8') as f:
        trans=json.load(f)

    # orig and trans are lists
    orig_map={e.get('strName'): e for e in orig if isinstance(e, dict)}
    trans_map={e.get('strName'): e for e in trans if isinstance(e, dict)}

    fixed=0
    for name in orig_map:
        o=orig_map[name]
        t=trans_map.get(name)
        if not t:
            continue
        for field in ['strDesc','strTitle','strNameFriendly']:
            if field not in o or field not in t:
                continue
            o_text=o[field] or ''
            t_text=t[field] or ''
            o_ph=set(placeholder_pat.findall(o_text))
            t_ph=set(placeholder_pat.findall(t_text))

            # если в оригинале нет плейсхолдеров, а в переводе есть — это ложные из-за "они", "его"
            if not o_ph and t_ph:
                # убираем ложные плейсхолдеры, заменяя их обратно на русские слова из OLD_DICT
                # например [them-subj] -> "они"
                new_t=t_text
                for ph in t_ph:
                    # найти какое русское слово дало этот ph в старом словаре
                    # OLD_DICT: ph -> word, так что word -> ph, нам нужно word
                    # ищем word которое мапится в ph в OLD_DICT
                    for old_ph, old_word in OLD_DICT.items():
                        if old_ph==ph and old_word:
                            # заменяем placeholder обратно на слово
                            new_t=new_t.replace(ph, old_word)
                t[field]=new_t
                fixed+=1
            # если в оригинале были плейсхолдеры, но какие-то потерялись (например [inquires])
            # то это другая проблема — не трогаем

    print(f"Почистил {fixed} полей с ложными плейсхолдерами")

    with open(out_path,'w',encoding='utf-8') as out:
        json.dump(trans, out, ensure_ascii=False, indent=2)
    print(f"Сохранено -> {out_path}")

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--orig", required=True, help="оригинал interactions_encounters.json")
    parser.add_argument("--trans", required=True, help="переведённый с ложными плейсхолдерами")
    parser.add_argument("--out", required=True)
    args=parser.parse_args()
    clean_file(args.orig, args.trans, args.out)
