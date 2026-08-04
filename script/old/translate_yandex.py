#!/usr/bin/env python3
"""
translate_yandex.py — фикс длинных текстов через Yandex/Google/DeepL без API-ключа
Подходит чтобы починить 1-2 галлюцинации NLLB типа AVClub_FirstWatch

Почему Yandex лучше на длинных:
  - NLLB/Marian лимит 512 токенов, на 3200 символов с Cut: уходит в луп
  - Yandex/Google берут до 10к символов, не лупит

Почему NLLB лучше на коротких:
  - Yandex переведёт [us] -> [нас], [them] -> [их] — сломает игру
  - NLLB с нашей защитой плейсхолдеров оставляет [us] как есть

Поэтому этот скрипт:
  - берёт твой NLLB перевод
  - ищет только плохие (повторы, латиница осталась, >1000 символов)
  - переводит их через deep_translator (Yandex/Google) с защитой плейсхолдеров

Установка:
  pip install deep-translator
  # или
  sudo pacman -S python-deep-translator

Запуск:
  python translate_yandex.py --input translated_nllb-200-3.3B.json --output fixed.json --provider yandex --only-bad
  python translate_yandex.py --input translated_nllb-200-3.3B.json --output fixed.json --provider google --only-bad

Провайдеры: yandex, google, deepl, libre, lingvanex

Если лимиты — ставь --limit 10 для теста
"""

import argparse, json, re, time
from pathlib import Path

PROTECT_ACRO = ["CCRE","OKLG","VENC","VNCA","GalCon","BCER","BCRS","GF"]
placeholder_pat = r'\[[^\]]+\]'
acr_pat = r'\b(?:' + '|'.join(map(re.escape, PROTECT_ACRO)) + r')\b'
combined_pat = f'({placeholder_pat}|{acr_pat})'
combined_regex = re.compile(combined_pat)
ph_regex = re.compile(placeholder_pat)
acr_regex = re.compile(acr_pat)

def split_protected(text):
    parts = combined_regex.split(text)
    res=[]
    for p in parts:
        if not p or p is None:
            continue
        if ph_regex.fullmatch(p) or acr_regex.fullmatch(p):
            res.append((True,p))
        else:
            res.append((False,p))
    return res

def has_repetition(text):
    if "Получается, что в этом случае" in text:
        return True
    if len(text)>800:
        # проверяем 3+ одинаковых предложения
        sentences = re.split(r'[.!?]\s+', text)
        from collections import Counter
        c=Counter([s.strip() for s in sentences if len(s.strip())>30])
        for cnt in c.values():
            if cnt>=3:
                return True
    return False

def is_bad(text):
    if not text or len(text.strip())<10:
        return False
    if has_repetition(text):
        return True
    # если осталась латиница длинная
    tmp=re.sub(r'\b(?:CCRE|OKLG|VENC|VNCA|GalCon|BCER|BCRS|GF|RCS|EVA|PDA|USD|BNW|Voltaire)\b','',text)
    if re.search(r'[A-Za-z]{5,}', tmp) and re.search(r'[А-Яа-я]', text):
        # смешанный — возможно не до конца переведено
        if len(tmp)>20:
            return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="translated_nllb-200-3.3B.json")
    parser.add_argument("--output", default="fixed.json")
    parser.add_argument("--provider", default="yandex", choices=["yandex","google","deepl","libre","lingvanex"])
    parser.add_argument("--only-bad", action="store_true", help="чинить только плохие с повторами/латиницей")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.5, help="задержка между запросами чтобы не забанили")
    args = parser.parse_args()

    try:
        from deep_translator import GoogleTranslator, YandexTranslator, DeeplTranslator, LibreTranslator, LingvanexTranslator
    except ImportError:
        print("pip install deep-translator")
        return

    provider_map={
        "yandex": lambda: YandexTranslator(source='en', target='ru'),
        "google": lambda: GoogleTranslator(source='en', target='ru'),
        "deepl": lambda: DeeplTranslator(source='en', target='ru'),
        "libre": lambda: LibreTranslator(source='en', target='ru'),
        "lingvanex": lambda: LingvanexTranslator(source='en', target='ru'),
    }

    translator = provider_map[args.provider]()

    with open(args.input,"r",encoding="utf-8") as f:
        data=json.load(f)
        # нам нужен ещё оригинал английский чтобы переводить с него, а не с битого русского
        # поэтому грузим untranslated если есть рядом
        orig_path=Path(args.input).parent / "untranslated.json"
        if not orig_path.exists():
            orig_path=Path("untranslated.json")
        orig_data=None
        if orig_path.exists():
            with open(orig_path,"r",encoding="utf-8") as of:
                orig_data=json.load(of)
            print(f"Оригинал найден {orig_path}, буду переводить с английского, а не чинить русский")

    to_fix=[]
    for fp, entries in data['files'].items():
        for ei, e in enumerate(entries):
            field=None
            txt=None
            if 'translation' in e:
                field='translation'
                txt=e[field]
            elif 'strDesc' in e and len(e['strDesc'])>500:
                field='strDesc'
                txt=e[field]

            if not txt:
                continue
            if args.only_bad and not is_bad(txt):
                continue

            # находим английский оригинал если есть
            orig_en=None
            if orig_data and fp in orig_data['files']:
                for oe in orig_data['files'][fp]:
                    if 'key' in e and oe.get('key')==e.get('key'):
                        orig_en=oe.get('original') or oe.get('strDesc')
                        break
                    if 'strName' in e and oe.get('strName')==e.get('strName'):
                        orig_en=oe.get('strDesc') or oe.get('original')
                        break

            # если нашли оригинал английский — переводим его, а не русский
            source_text = orig_en if orig_en else txt

            if args.limit and len(to_fix)>=args.limit:
                break

            to_fix.append((fp, ei, field, txt, source_text))

    print(f"Буду чинить: {len(to_fix)} строк через {args.provider}")

    from tqdm import tqdm
    for fp, ei, field, old_ru, source_en in tqdm(to_fix, desc=f"{args.provider} фикс"):
        # защита плейсхолдеров
        parts = split_protected(source_en)
        cores=[]
        metas=[]
        for is_prot, content in parts:
            if is_prot:
                metas.append((True, content))
            else:
                if not content.strip() or not re.search(r'[A-Za-z]', content):
                    metas.append((True, content))  # не переводим
                else:
                    m=re.match(r'^(\s*)(.*?)(\s*)$', content, re.DOTALL)
                    if m:
                        lead,core,trail=m.groups()
                        if core.strip():
                            cores.append(core)
                            metas.append((False, lead, core, trail, len(cores)-1))
                        else:
                            metas.append((True, content))
                    else:
                        cores.append(content)
                        metas.append((False, '', content, '', len(cores)-1))

        # переводим ядра через провайдер
        translated_cores=[]
        for core in cores:
            try:
                tr = translator.translate(core)
                time.sleep(args.delay)
            except Exception as ex:
                print(f"\nОшибка {args.provider}: {ex}, оставляю оригинал")
                tr=core
            translated_cores.append(tr)

        # сборка
        rebuilt=[]
        for meta in metas:
            if meta[0]==True:
                rebuilt.append(meta[1])
            else:
                _, lead, core, trail, idx = meta
                rebuilt.append(lead + translated_cores[idx] + trail)

        new_ru=''.join(rebuilt)
        data['files'][fp][ei][field]=new_ru

    with open(args.output,"w",encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
    print(f"Готово -> {args.output}")

if __name__=="__main__":
    main()
