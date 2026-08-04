#!/usr/bin/env python3
"""
translate_llm.py — финальная полировка через LLM (Qwen/Llama) с глоссарием.

Фикс: теперь работает и без accelerate, и с ним.

Установка Arch:
  sudo pacman -S python-pytorch python-transformers python-accelerate python-bitsandbytes
  # или в venv:
  python -m venv ~/ostranslator
  source ~/ostranslator/bin/activate
  pip install torch --index-url https://download.pytorch.org/whl/rocm6.0
  pip install transformers accelerate bitsandbytes sentencepiece tqdm

Если ошибка:
  ValueError: Using a `device_map` ... requires `accelerate`
  -> pip install accelerate  или pacman -S python-accelerate

Запуск:
  python translate_llm.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-14B-Instruct --bits 4 --device cuda:0 --nocache
  python translate_llm.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-7B-Instruct --bits 0 --device cuda:0 --nocache
"""

import argparse, json, re, gc
from pathlib import Path
from collections import defaultdict

GLOSSARY = """
Игровая терминология (используй строго):
condition -> состояние
vessel / ship -> корабль
airlock -> шлюз
berth / dock -> стыковочный узел
transponder -> транспондер
RCS -> РСУ (реактивная система управления)
thruster -> двигатель
nav station -> навигационная станция
roster -> реестр (экипажа)
port (electrical) -> порт
signal -> сигнал
warrant -> ордер
pledge -> обязательство
faction -> фракция
CCRE, OKLG, VENC, VNCA, GalCon — оставлять как есть
EVA -> ВКД

Правила:
- НЕ переводить плейсхолдеры: [us], [them], [is], [has], [was], [were], [bashes], [sits], [3rd], [us-pos], [them-pos] и т.д.
- \\n сохраняй
- Тон: мрачное sci-fi, сухой/технический с чёрным юмором
- Русский — литературный, не калька
- UI — коротко 2-4 слова
"""

SYSTEM_PROMPT = f"Ты — переводчик игры Ostranauts с английского на русский.\n{GLOSSARY}\nПереведи ТОЛЬКО текст, сохраняя плейсхолдеры. Отвечай ТОЛЬКО переводом."

def build_user_prompt(text):
    return f"Переведи на русский, сохрани плейсхолдеры:\n\n{text}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="translated_big.json")
    parser.add_argument("--output", default="translated_final.json")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--batch", type=int, default=1, help="для LLM лучше 1, иначе ломает плейсхолдеры")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--bits", type=int, default=4, help="4/8 квантизация, 0=fp16")
    parser.add_argument("--nocache", action="store_true", help="отключить кэш полировки")
    parser.add_argument("--cache", default="cache_llm.json")
    parser.add_argument("--limit", type=int, default=0, help="для теста — сколько строк полировать, 0=все")
    args = parser.parse_args()

    with open(args.input,"r",encoding="utf-8") as f:
        data=json.load(f)

    # собираем строки
    all_texts=[]
    mapping=[]
    for file_path, entries in data['files'].items():
        for ei, e in enumerate(entries):
            if 'translation' in e:
                all_texts.append(e['translation'])
                mapping.append((file_path, ei, 'translation'))
            else:
                for field in ['strNameFriendly','strTitle','strDesc']:
                    if field in e:
                        all_texts.append(e[field])
                        mapping.append((file_path, ei, field))

    if args.limit>0:
        all_texts=all_texts[:args.limit]
        mapping=mapping[:args.limit]

    print(f"Всего строк для полировки: {len(all_texts)}")

    # кэш
    cache_path=Path(args.cache)
    cache={}
    if not args.nocache and cache_path.exists():
        try:
            with open(cache_path,"r",encoding="utf-8") as cf:
                cache=json.load(cf)
            print(f"Кэш загружен: {len(cache)}")
        except Exception as ex:
            print(f"cache fail {ex}")

    # фильтруем что уже в кэше
    to_polish_idx=[]
    to_polish_texts=[]
    for i, txt in enumerate(all_texts):
        if not args.nocache and txt in cache and cache[txt]:
            continue
        # пропускаем совсем короткие/технические
        if txt.strip() in ["???",".","0","1","2","XXX","ложь","Нейтрально"]:
            continue
        to_polish_idx.append(i)
        to_polish_texts.append(txt)

    print(f"Осталось полировать: {len(to_polish_texts)} (остальные из кэша/пропуск)")

    if to_polish_texts:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        print(f"Loading {args.model} (bits={args.bits})")
        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)

        # пробуем с accelerate, если нет — без device_map
        load_kwargs={}
        if args.bits==4:
            load_kwargs['load_in_4bit']=True
            load_kwargs['bnb_4bit_compute_dtype']=torch.float16
        elif args.bits==8:
            load_kwargs['load_in_8bit']=True

        # device_map требует accelerate — пробуем
        try:
            # если accelerate установлен
            import accelerate
            has_accelerate=True
        except ImportError:
            has_accelerate=False
            print("accelerate не установлен — ставлю без device_map, будет медленнее. Установи: pip install accelerate или pacman -S python-accelerate")

        model_kwargs={
            "trust_remote_code": True,
            "dtype": torch.float16,
            **load_kwargs
        }
        if has_accelerate:
            model_kwargs["device_map"] = args.device if "cuda" in args.device else "auto"
        else:
            # без accelerate device_map нельзя, загружаем на cpu потом to(device)
            pass

        try:
            model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
        except Exception as ex:
            print(f"Не удалось загрузить с bits={args.bits}, пробую без квантизации: {ex}")
            # fallback без bits
            model_kwargs.pop('load_in_4bit', None)
            model_kwargs.pop('load_in_8bit', None)
            model_kwargs.pop('bnb_4bit_compute_dtype', None)
            model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True, dtype=torch.float16, device_map=model_kwargs.get("device_map","auto") if has_accelerate else None)

        if not has_accelerate:
            # ручной перенос
            if "cuda" in args.device:
                try:
                    model.to(args.device)
                except Exception as e:
                    print(f"to({args.device}) fail {e}, остаюсь на cpu")
            # else cpu уже

        model.eval()

        # полировка поштучно — надёжнее для плейсхолдеров
        from tqdm import tqdm
        ph_pat=re.compile(r'\[[^\]]+\]')

        for idx, txt in zip(tqdm(to_polish_idx, desc="Полировка LLM"), to_polish_texts):
            # если в кэше — уже пропустили
            messages=[
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user","content":build_user_prompt(txt)}
            ]
            try:
                prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            except Exception:
                prompt = f"{SYSTEM_PROMPT}\n\n{build_user_prompt(txt)}\n\nПеревод:"

            tokens=tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
            # перенос на устройство модели
            try:
                device = next(model.parameters()).device
                tokens = {k: v.to(device) for k,v in tokens.items()}
            except:
                pass

            with torch.no_grad():
                out=model.generate(**tokens, max_new_tokens=256, do_sample=False, temperature=0.0, top_p=1.0)

            input_len=tokens['input_ids'].shape[1]
            out_text=tokenizer.decode(out[0][input_len:], skip_special_tokens=True).strip()
            out_text=out_text.strip().strip('"').strip("'").strip()

            # защита плейсхолдеров
            orig_ph=set(ph_pat.findall(txt))
            new_ph=set(ph_pat.findall(out_text))
            if orig_ph and orig_ph!=new_ph:
                # модель потеряла плейсхолдер — оставляем исходный перевод
                # print(f"placeholder lost: {orig_ph} vs {new_ph} | {txt[:60]} -> {out_text[:60]}")
                cache[txt]=txt
            else:
                cache[txt]=out_text if out_text else txt

            # периодическое сохранение кэша
            if len(cache)%200==0 and not args.nocache:
                with open(cache_path,"w",encoding="utf-8") as cf:
                    json.dump(cache, cf, ensure_ascii=False, indent=2)

            # очистка для CPU
            del tokens, out
            if args.device=="cpu":
                gc.collect()

        if not args.nocache:
            with open(cache_path,"w",encoding="utf-8") as cf:
                json.dump(cache, cf, ensure_ascii=False, indent=2)
            print(f"Кэш LLM сохранён в {cache_path}")

    # применяем кэш к all_texts
    final_texts=[]
    for txt in all_texts:
        if txt in cache:
            final_texts.append(cache[txt])
        else:
            final_texts.append(txt)

    # сборка обратно
    for (file_path, ei, field), new_txt in zip(mapping, final_texts):
        data['files'][file_path][ei][field]=new_txt

    with open(args.output,"w",encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
    print(f"Готово -> {args.output}")

if __name__=="__main__":
    main()
