#!/usr/bin/env python3
"""
translate_ollama.py — полировка через Ollama (работает на Vulkan)

Почему это самый простой выход для твоего железа:
  - E5-1680 v2 = Ivy Bridge, без AVX2. vLLM требует AVX2 -> падает с "Недопустимая инструкция" при сборке
  - Ollama на Vulkan, не нужен ROCm билд
  - Использует твою RX 6800 через Vulkan, GPU 303W остаётся в 100%, CPU не жрёт 2 ядра как bitsandbytes

Установка:
  # Ollama у тебя уже стоит
  ollama pull qwen2.5:7b-instruct
  ollama pull qwen2.5:14b-instruct  # если влезет в 16GB, ~9GB в Q4_K_M

  pip install ollama tqdm requests
  # или в venv
  # python -m venv ~/ollama_translator && source ~/ollama_translator/bin/activate
  # pip install ollama tqdm

Запуск:
  # убедись что ollama запущена: ollama serve &  (обычно уже запущена)
  python translate_ollama.py --input translated.json --output translated_final.json --model qwen2.5:7b-instruct --batch 8 --nocache --only-bad

  # 14B через Ollama (лучше чем 7B, но медленнее)
  python translate_ollama.py --input translated.json --output translated_final_14b.json --model qwen2.5:14b-instruct --batch 4 --nocache --only-bad

  # тест 100 строк
  python translate_ollama.py --input translated.json --output test.json --model qwen2.5:7b-instruct --limit 100 --nocache

Скорость: на Vulkan + RX 6800 ожидай ~5-10 токенов/сек на 7B, ~2-4 токенов/сек на 14B.
21137 строк в only-bad (~2-3к реально плохих) = 2-3 часа на 7B, 5-6 часов на 14B.
"""

import argparse, json, re, signal
from pathlib import Path

GLOSSARY = "condition->состояние, vessel/ship->корабль, airlock->шлюз, berth/dock->стыковочный узел, transponder->транспондер, RCS->РСУ, EVA->ВКД, CCRE/OKLG/VENC/VNCA/GalCon не переводить. НЕ трогай [us] [them] [is] [has] [3rd] [us-pos] и т.д."

SYSTEM_PROMPT = f"Ты переводчик Ostranauts EN->RU. {GLOSSARY} Переведи ТОЛЬКО текст, сохраняя плейсхолдеры. Отвечай ТОЛЬКО переводом. Тон мрачное sci-fi."

def build_prompt(txt):
    return f"Переведи на русский, сохрани плейсхолдеры:\n{txt}"

def is_bad(txt):
    if not txt or len(txt.strip())<3:
        return False
    if txt.strip() in ["???",".","0","1","2","XXX"]:
        return False
    tmp=re.sub(r'\b(?:CCRE|OKLG|VENC|VNCA|GalCon|BCER|BCRS|GF|RCS|EVA|PDA|USD)\b','',txt)
    if re.search(r'[A-Za-z]{4,}', tmp):
        return True
    for bm in ["космодрома","Спаун","Пристин","ДОКУШИТЕЛЬНЫЕ","ККЭЙР"]:
        if bm in txt:
            return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="translated.json")
    parser.add_argument("--output", default="translated_final.json")
    parser.add_argument("--model", default="qwen2.5:7b-instruct", help="ollama model tag")
    parser.add_argument("--batch", type=int, default=8, help="батч запросов к ollama, 4-8 оптимально")
    parser.add_argument("--nocache", action="store_true")
    parser.add_argument("--cache", default="cache_ollama.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only-bad", action="store_true")
    parser.add_argument("--host", default="http://localhost:11434", help="ollama host")
    args = parser.parse_args()

    interrupted=False
    def handle_sigint(signum, frame):
        nonlocal interrupted
        print("\nCtrl-C, сохраняю кэш...")
        interrupted=True
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    with open(args.input,"r",encoding="utf-8") as f:
        data=json.load(f)

    all_texts=[]
    mapping=[]
    for fp, entries in data['files'].items():
        for ei, e in enumerate(entries):
            if 'translation' in e:
                all_texts.append(e['translation'])
                mapping.append((fp, ei, 'translation'))
            else:
                for field in ['strNameFriendly','strTitle','strDesc']:
                    if field in e:
                        all_texts.append(e[field])
                        mapping.append((fp, ei, field))

    if args.limit>0:
        all_texts=all_texts[:args.limit]
        mapping=mapping[:args.limit]

    print(f"Всего: {len(all_texts)}")

    cache_path=Path(args.cache)
    cache={}
    if not args.nocache and cache_path.exists():
        try:
            cache=json.load(open(cache_path,"r",encoding="utf-8"))
            print(f"Кэш: {len(cache)}")
        except:
            pass

    to_polish_idx=[]
    to_polish=[]
    for i, txt in enumerate(all_texts):
        if not args.nocache and txt in cache:
            continue
        if args.only_bad and not is_bad(txt):
            continue
        to_polish_idx.append(i)
        to_polish.append(txt)

    print(f"Полировать: {len(to_polish)} only-bad={args.only_bad}")

    if to_polish:
        try:
            import ollama
            has_ollama_lib=True
        except ImportError:
            has_ollama_lib=False
            print("pip install ollama не стоит, использую requests")
            import requests

        from tqdm import tqdm
        import concurrent.futures

        # Ollama через библиотеку умеет батчить? Делаем через ThreadPool для скорости
        # Но Vulkan бэкенд в ollama не любит большой параллелизм, поэтому batch=4-8 и 1 воркер
        ph_pat=re.compile(r'\[[^\]]+\]')

        def polish_one(txt):
            prompt = build_prompt(txt)
            try:
                if has_ollama_lib:
                    # используем chat API
                    resp = ollama.chat(
                        model=args.model,
                        messages=[
                            {"role":"system","content":SYSTEM_PROMPT},
                            {"role":"user","content":prompt}
                        ],
                        options={"temperature":0, "num_predict": 256}
                    )
                    out = resp['message']['content'].strip()
                else:
                    import requests
                    r = requests.post(f"{args.host}/api/chat", json={
                        "model": args.model,
                        "messages": [
                            {"role":"system","content":SYSTEM_PROMPT},
                            {"role":"user","content":prompt}
                        ],
                        "stream": False,
                        "options": {"temperature":0, "num_predict":256}
                    }, timeout=120)
                    r.raise_for_status()
                    out = r.json()['message']['content'].strip()
                out = out.strip().strip('"').strip("'")
                # защита плейсхолдеров
                if ph_pat.search(txt) and set(ph_pat.findall(txt)) != set(ph_pat.findall(out)):
                    return txt
                return out if out else txt
            except Exception as e:
                print(f"\nОшибка на '{txt[:40]}': {e}")
                return txt

        # последовательный батч с прогрессом (параллельный на Vulkan медленнее из-за блокировок)
        try:
            for start in tqdm(range(0, len(to_polish), args.batch), desc="Ollama"):
                if interrupted:
                    break
                batch = to_polish[start:start+args.batch]
                batch_idx = to_polish_idx[start:start+args.batch]
                # для ollama лучше по одному, но с батч-отображением прогресса
                for txt, global_idx in zip(batch, batch_idx):
                    if interrupted:
                        break
                    result = polish_one(txt)
                    cache[txt]=result

                if not args.nocache and len(cache)%200==0:
                    with open(cache_path,"w",encoding="utf-8") as cf:
                        json.dump(cache, cf, ensure_ascii=False, indent=2)
        except KeyboardInterrupt:
            print("\nПрервано")
            interrupted=True
        finally:
            if not args.nocache:
                with open(cache_path,"w",encoding="utf-8") as cf:
                    json.dump(cache, cf, ensure_ascii=False, indent=2)
                print(f"Кэш сохранён {len(cache)}")

    final=[cache.get(txt, txt) for txt in all_texts]
    for (fp, ei, field), new in zip(mapping, final):
        data['files'][fp][ei][field]=new

    with open(args.output,"w",encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
    print(f"Готово -> {args.output} interrupted={interrupted}")

if __name__=="__main__":
    main()
