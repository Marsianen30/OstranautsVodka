#!/usr/bin/env python3
"""
translate_llm_fixed.py — полировка с Qwen, фикс для bitsandbytes + batch

Фиксы под твои ошибки:
  - Qwen2ForCausalLM got unexpected keyword argument 'load_in_4bit' -> теперь через BitsAndBytesConfig
  - CUDA OOM на 14B -> 4-бит + offload, батч 1-2
  - Медленная поштучная генерация — добавлен нормальный батчинг

Установка Arch:
  sudo pacman -S python-transformers python-accelerate python-bitsandbytes python-sentencepiece
  # или venv:
  python -m venv ~/ostranslator
  source ~/ostranslator/bin/activate
  pip install transformers accelerate bitsandbytes sentencepiece tqdm torch --index-url https://download.pytorch.org/whl/rocm6.0

Запуск:
  # 7B — влезает в 16GB даже без квантизации (15.7GB)
  python translate_llm_fixed.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-7B-Instruct --bits 0 --batch 4 --device cuda:0 --nocache

  # 7B с 4-бит — быстрее и экономнее, ~5GB
  python translate_llm_fixed.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-7B-Instruct --bits 4 --batch 8 --device cuda:0 --nocache

  # 14B — только 4-бит, иначе OOM (28GB в fp16 не влезет в 16GB)
  python translate_llm_fixed.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-14B-Instruct --bits 4 --batch 2 --device cuda:0 --nocache

  # тест на 100 строках
  python translate_llm_fixed.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-7B-Instruct --bits 4 --batch 4 --limit 100 --nocache
"""

import argparse, json, re, gc
from pathlib import Path
from collections import defaultdict

GLOSSARY = """
Глоссарий Ostranauts (строго соблюдай):
condition → состояние
vessel / ship → корабль
airlock → шлюз
berth / dock → стыковочный узел
transponder → транспондер
RCS → РСУ
thruster → двигатель
nav station → навигационная станция
roster → реестр
port → порт
signal → сигнал
warrant → ордер
pledge → обязательство
faction → фракция
EVA → ВКД
CCRE, OKLG, VENC, VNCA, GalCon, BCER, BCRS, GF — НЕ переводить
"""

SYSTEM_PROMPT = f"""Ты — переводчик игры Ostranauts с английского на русский. Мрачное sci-fi, сухой технический с чёрным юмором.

{GLOSSARY}

Правила:
- НЕ трогай плейсхолдеры: [us], [them], [is], [has], [was], [were], [bashes], [sits], [attempts], [3rd], [us-pos], [them-pos], [us-subj] и любые [глагол]
- Сохраняй \\n
- UI короткие: 2-4 слова
- Отвечай ТОЛЬКО переводом, без кавычек и пояснений
"""

def build_prompt(txt):
    return f"Переведи на русский, сохрани плейсхолдеры:\n{txt}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="translated.json")
    parser.add_argument("--output", default="translated_final.json")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--batch", type=int, default=4, help="батч для LLM, 1-8")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--bits", type=int, default=4, help="0=fp16, 4=4bit, 8=8bit")
    parser.add_argument("--nocache", action="store_true")
    parser.add_argument("--cache", default="cache_llm.json")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

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

    print(f"Всего строк: {len(all_texts)}")

    cache_path=Path(args.cache)
    cache={}
    if not args.nocache and cache_path.exists():
        try:
            cache=json.load(open(cache_path,"r",encoding="utf-8"))
            print(f"Кэш загружен: {len(cache)}")
        except Exception as ex:
            print(f"cache fail {ex}")

    to_polish_idx=[]
    to_polish=[]
    for i, txt in enumerate(all_texts):
        if not args.nocache and txt in cache:
            continue
        if txt.strip() in ["???",".","0","1","2","XXX","ложь","Нейтрально"]:
            continue
        to_polish_idx.append(i)
        to_polish.append(txt)

    print(f"Полировать осталось: {len(to_polish)}")

    if to_polish:
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        import torch

        print(f"Loading {args.model} bits={args.bits}")
        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)

        # Квантизация через новый API
        bnb_config=None
        if args.bits==4:
            bnb_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
        elif args.bits==8:
            bnb_config=BitsAndBytesConfig(load_in_8bit=True)

        # device_map
        try:
            import accelerate
            has_acc=True
        except ImportError:
            has_acc=False
            print("accelerate не стоит — будет без device_map. pip install accelerate")

        model_kwargs={
            "trust_remote_code": True,
            "dtype": torch.float16 if args.bits!=0 else torch.float16,
        }
        if bnb_config is not None:
            model_kwargs["quantization_config"]=bnb_config
        if has_acc:
            model_kwargs["device_map"]=args.device if "cuda" in args.device else "auto"
        else:
            model_kwargs["device_map"]=None

        try:
            model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
        except Exception as ex:
            print(f"Первая попытка загрузки упала {ex}, пробую fallback без квантизации")
            model_kwargs.pop("quantization_config", None)
            model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True, dtype=torch.float16, device_map=model_kwargs.get("device_map"))

        if not has_acc:
            try:
                model.to(args.device)
            except Exception as e:
                print(f"to({args.device}) fail {e}")

        model.eval()

        from tqdm import tqdm
        ph_pat=re.compile(r'\[[^\]]+\]')

        # Батчевая генерация
        for start in tqdm(range(0, len(to_polish), args.batch), desc="LLM полировка"):
            batch_texts = to_polish[start:start+args.batch]
            batch_indices = to_polish_idx[start:start+args.batch]

            prompts=[]
            for txt in batch_texts:
                messages=[
                    {"role":"system","content":SYSTEM_PROMPT},
                    {"role":"user","content":build_prompt(txt)}
                ]
                try:
                    p = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                except:
                    p = f"{SYSTEM_PROMPT}\n\n{build_prompt(txt)}\n\nПеревод:"
                prompts.append(p)

            tokens = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=1024)
            # на устройство модели
            try:
                device = next(model.parameters()).device
                tokens = {k: v.to(device) for k,v in tokens.items()}
            except:
                pass

            with torch.no_grad():
                out = model.generate(**tokens, max_new_tokens=256, do_sample=False, temperature=None, top_p=None, repetition_penalty=1.05)

            # декод
            for j, seq in enumerate(out):
                input_len = tokens['input_ids'][j].shape[0]
                new = seq[input_len:]
                txt_out = tokenizer.decode(new, skip_special_tokens=True).strip()
                txt_out = txt_out.strip().strip('"').strip("'").strip()

                orig = batch_texts[j]
                # защита плейсхолдеров
                if set(ph_pat.findall(orig)) != set(ph_pat.findall(txt_out)) and ph_pat.search(orig):
                    # потеряли — оставляем оригинал
                    cache[orig]=orig
                else:
                    # если пусто — тоже оригинал
                    cache[orig]=txt_out if txt_out else orig

            if not args.nocache and len(cache)%200==0:
                with open(cache_path,"w",encoding="utf-8") as cf:
                    json.dump(cache, cf, ensure_ascii=False, indent=2)

            del tokens, out
            gc.collect()
            if "cuda" in args.device:
                try:
                    torch.cuda.empty_cache()
                except:
                    pass

        if not args.nocache:
            with open(cache_path,"w",encoding="utf-8") as cf:
                json.dump(cache, cf, ensure_ascii=False, indent=2)

    # применяем
    final=[]
    for txt in all_texts:
        final.append(cache.get(txt, txt))

    for (fp, ei, field), new in zip(mapping, final):
        data['files'][fp][ei][field]=new

    with open(args.output,"w",encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
    print(f"Готово -> {args.output}")

if __name__=="__main__":
    main()
