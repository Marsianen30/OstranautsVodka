#!/usr/bin/env python3
"""
translate_llm_v3.py — фикс padding_side + Ctrl-C + скорость

Фиксы под последние логи:
1) transformers: A decoder-only architecture is being used, but right-padding was detected!
   -> теперь tokenizer = ... padding_side='left' + pad_token = eos_token
2) 10GB VRAM на 14B 4bit — норма, но скорость 18-60 сек/батч -> медленный generate
   -> добавил use_cache=True, pad_token_id=eos, батч 4-8, и фильтр только плохих строк
3) Ctrl-C не ловился в model.generate() -> теперь try/except KeyboardInterrupt и сохранение кэша

Установка:
  pip install transformers accelerate bitsandbytes sentencepiece tqdm

Запуск быстрый (только плохие строки):
  python translate_llm_v3.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-7B-Instruct --bits 4 --batch 8 --device cuda:0 --nocache --only-bad

Запуск полный 14B:
  python translate_llm_v3.py --input translated.json --output translated_final_14b.json --model Qwen/Qwen2.5-14B-Instruct --bits 4 --batch 2 --device cuda:0 --nocache

Для остановки — Ctrl-C один раз, подожди 5-10 сек, сохранит кэш и выйдет.
"""

import argparse, json, re, gc, signal, sys
from pathlib import Path

GLOSSARY = """
Глоссарий: condition->состояние, vessel/ship->корабль, airlock->шлюз, berth/dock->стыковочный узел, transponder->транспондер, RCS->РСУ, thruster->двигатель, nav station->навигационная станция, roster->реестр, warrant->ордер, EVA->ВКД, CCRE/OKLG/VENC/VNCA/GalCon/BCER/BCRS/GF не переводить.
Правила: НЕ трогай [us] [them] [is] [has] [3rd] [us-pos] и т.д., сохраняй \\n, UI коротко.
"""

SYSTEM_PROMPT = f"Ты переводчик Ostranauts с EN на RU. {GLOSSARY} Переведи ТОЛЬКО текст, сохраняя плейсхолдеры. Отвечай ТОЛЬКО переводом."

def build_prompt(txt):
    return f"Переведи на русский, сохрани плейсхолдеры:\n{txt}"

def is_bad_translation(txt):
    """Эвристика плохих переводов от NLLB чтобы не полировать всё подряд"""
    if not txt or len(txt.strip())<3:
        return False
    # если остались латиница (кроме разрешённых акронимов)
    # убираем разрешённые
    tmp=re.sub(r'\b(?:CCRE|OKLG|VENC|VNCA|GalCon|BCER|BCRS|GF|RCS|EVA|PDA|USD|CH4|CO2|CO|O2|N2|NH3|H2SO4)\b','',txt)
    # если осталась латиница длиной >3 и есть кириллица — вероятно непереведено
    if re.search(r'[A-Za-z]{4,}', tmp):
        return True
    # специфичные косяки из твоих логов
    bad_markers=["космодрома","Спаун","Пристин","ДОКУШИТЕЛЬНЫЕ","ККЭЙР","ККЭВ"]
    for bm in bad_markers:
        if bm in txt:
            return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="translated.json")
    parser.add_argument("--output", default="translated_final.json")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument("--nocache", action="store_true")
    parser.add_argument("--cache", default="cache_llm.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only-bad", action="store_true", help="полировать только плохие переводы (в 5-10 раз быстрее)")
    args = parser.parse_args()

    # обработка Ctrl-C
    interrupted=False
    def handle_sigint(signum, frame):
        nonlocal interrupted
        print("\n\nПолучен Ctrl-C, сохраняю кэш и выхожу... (подожди генерацию текущего батча)")
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

    print(f"Всего строк: {len(all_texts)}")

    cache_path=Path(args.cache)
    cache={}
    if not args.nocache and cache_path.exists():
        try:
            cache=json.load(open(cache_path,"r",encoding="utf-8"))
            print(f"Кэш: {len(cache)}")
        except Exception as ex:
            print(f"cache fail {ex}")

    to_polish_idx=[]
    to_polish=[]
    for i, txt in enumerate(all_texts):
        if not args.nocache and txt in cache:
            continue
        if txt.strip() in ["???",".","0","1","2","XXX","ложь","Нейтрально"]:
            continue
        if args.only_bad and not is_bad_translation(txt):
            continue
        to_polish_idx.append(i)
        to_polish.append(txt)

    print(f"Полировать: {len(to_polish)} (only-bad={args.only_bad})")

    if to_polish:
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        import torch

        print(f"Loading {args.model} bits={args.bits}")
        # ВАЖНО: padding_side='left' для decoder-only!
        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True, padding_side="left")
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.pad_token_id = tokenizer.eos_token_id

        bnb_config=None
        if args.bits==4:
            bnb_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
        elif args.bits==8:
            bnb_config=BitsAndBytesConfig(load_in_8bit=True)

        try:
            import accelerate
            has_acc=True
        except ImportError:
            has_acc=False
            print("Нет accelerate, ставлю без device_map")

        model_kwargs={"trust_remote_code": True, "dtype": torch.float16}
        if bnb_config:
            model_kwargs["quantization_config"]=bnb_config
        if has_acc:
            model_kwargs["device_map"]=args.device if "cuda" in args.device else "auto"

        try:
            model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
        except Exception as ex:
            print(f"Fallback без квантизации: {ex}")
            model_kwargs.pop("quantization_config",None)
            model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True, dtype=torch.float16, device_map=model_kwargs.get("device_map"))

        if not has_acc:
            try:
                model.to(args.device)
            except:
                pass
        model.eval()

        from tqdm import tqdm
        ph_pat=re.compile(r'\[[^\]]+\]')

        try:
            for start in tqdm(range(0, len(to_polish), args.batch), desc="LLM полировка"):
                if interrupted:
                    print("Прерывание по флагу...")
                    break
                batch_texts = to_polish[start:start+args.batch]
                batch_global_idx = to_polish_idx[start:start+args.batch]

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

                # токенизация с left padding
                tokens = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=1024, padding_side="left")
                try:
                    device = next(model.parameters()).device
                    tokens = {k: v.to(device) for k,v in tokens.items()}
                except:
                    pass

                try:
                    with torch.no_grad():
                        out = model.generate(
                            **tokens,
                            max_new_tokens=256,
                            do_sample=False,
                            use_cache=True,
                            pad_token_id=tokenizer.eos_token_id,
                            eos_token_id=tokenizer.eos_token_id,
                            repetition_penalty=1.05,
                        )
                except KeyboardInterrupt:
                    print("\nKeyboardInterrupt внутри generate, сохраняю...")
                    interrupted=True
                    break
                except RuntimeError as e:
                    print(f"\nRuntimeError (возможно OOM): {e}, пропускаю батч")
                    for orig in batch_texts:
                        cache[orig]=orig
                    continue

                for j, seq in enumerate(out):
                    input_len = tokens['input_ids'][j].shape[0]
                    new = seq[input_len:]
                    txt_out = tokenizer.decode(new, skip_special_tokens=True).strip().strip('"').strip("'").strip()
                    orig = batch_texts[j]
                    # защита
                    if ph_pat.search(orig) and set(ph_pat.findall(orig)) != set(ph_pat.findall(txt_out)):
                        cache[orig]=orig
                    else:
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

        except KeyboardInterrupt:
            print("\n\nПрервано по Ctrl-C, сохраняю кэш...")
            interrupted=True

        finally:
            if not args.nocache:
                with open(cache_path,"w",encoding="utf-8") as cf:
                    json.dump(cache, cf, ensure_ascii=False, indent=2)
                print(f"Кэш сохранён {cache_path} ({len(cache)} записей)")

    # применяем
    final=[]
    for txt in all_texts:
        final.append(cache.get(txt, txt))

    for (fp, ei, field), new in zip(mapping, final):
        data['files'][fp][ei][field]=new

    with open(args.output,"w",encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
    print(f"Готово -> {args.output}, прервано={interrupted}")

if __name__=="__main__":
    main()
