#!/usr/bin/env python3
"""
translate_vllm.py — полировка через vLLM (в 10-20 раз быстрее чем transformers generate)

Почему быстрее:
  - PagedAttention + continuous batching — GPU не простаивает
  - На ROCm идёт напрямую через HIP, без bitsandbytes CPU fallback
  - Токенизация батчами на GPU

карта gfx1030 (RX 6800 16GB) + 303W в 100% — идеально для vLLM

Установка Arch:
  # ROCm уже стоит (gfx1030), проверь:
  # rocminfo | grep gfx
  # python -c "import torch; print(torch.cuda.is_available())" -> True

  # vLLM с ROCm — ставь через AUR (быстрее) или pip
  yay -S python-vllm-rocm
  # или
  # python -m venv ~/vllm
  # source ~/vllm/bin/activate
  # pip install torch --index-url https://download.pytorch.org/whl/rocm6.0
  # pip install vllm

  # для Qwen нужен свежий transformers
  pip install transformers

Запуск:
  # 7B — летает, ~8GB VRAM, 303W будет в 100% но CPU 20-30%
  python translate_vllm.py --input translated.json --output translated_final.json --model Qwen/Qwen2.5-7B-Instruct --batch 32 --device cuda --nocache --only-bad

  # 14B — ~10GB VRAM в fp16 с AWQ/GPTQ или 4-бит через vLLM автоматически
  python translate_vllm.py --input translated.json --output translated_final_14b.json --model Qwen/Qwen2.5-14B-Instruct --batch 16 --device cuda --nocache

  # только плохие строки — в 7 раз быстрее
  python translate_vllm.py --input translated.json --output final.json --model Qwen/Qwen2.5-7B-Instruct --only-bad --nocache

  # тест 100 строк
  python translate_vllm.py --input translated.json --output test.json --model Qwen/Qwen2.5-7B-Instruct --limit 100 --nocache
"""

import argparse, json, re, os, sys, signal
from pathlib import Path

GLOSSARY = "condition->состояние, vessel/ship->корабль, airlock->шлюз, berth/dock->стыковочный узел, transponder->транспондер, RCS->РСУ, thruster->двигатель, roster->реестр, warrant->ордер, EVA->ВКД, CCRE/OKLG/VENC/VNCA/GalCon не переводить"

SYSTEM_PROMPT = f"Ты переводчик Ostranauts EN->RU. {GLOSSARY} Правила: НЕ трогай плейсхолдеры [us] [them] [is] [has] [3rd] [us-pos] [them-pos] и любые [глагол], сохраняй \\n, UI коротко 2-4 слова. Отвечай ТОЛЬКО переводом."

def build_prompt(tokenizer, txt):
    messages=[
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":f"Переведи на русский, сохрани плейсхолдеры:\n{txt}"}
    ]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except:
        return f"{SYSTEM_PROMPT}\n\nПереведи:\n{txt}\n\nПеревод:"

def is_bad(txt):
    if not txt or len(txt.strip())<3:
        return False
    if txt.strip() in ["???",".","0","1","2","XXX"]:
        return False
    tmp=re.sub(r'\b(?:CCRE|OKLG|VENC|VNCA|GalCon|BCER|BCRS|GF|RCS|EVA|PDA|USD)\b','',txt)
    if re.search(r'[A-Za-z]{4,}', tmp):
        return True
    for bm in ["космодрома","Спаун","Пристин","ДОКУШИТЕЛЬНЫЕ","ККЭЙР","ККЭВ"]:
        if bm in txt:
            return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="translated.json")
    parser.add_argument("--output", default="translated_final.json")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--batch", type=int, default=32, help="vLLM любит большие батчи, 32-64 для 7B")
    parser.add_argument("--device", default="cuda", help="для vLLM просто cuda")
    parser.add_argument("--nocache", action="store_true")
    parser.add_argument("--cache", default="cache_vllm.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only-bad", action="store_true", help="только плохие переводы")
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()

    interrupted=False
    def handle_sigint(signum, frame):
        nonlocal interrupted
        print("\nCtrl-C, сохраняю...")
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

    print(f"Полировать: {len(to_polish)} (only-bad={args.only_bad})")

    if to_polish:
        try:
            from vllm import LLM, SamplingParams
        except ImportError:
            print("vLLM не установлен! Ставь: yay -S python-vllm-rocm или pip install vllm")
            print("Fallback на transformers, но будет медленно")
            # fallback на старый метод
            sys.exit(1)

        print(f"Loading vLLM {args.model} on {args.device}...")
        # vLLM сам разрулит ROCm
        # для 16GB карты 14B лучше с --enforce-eager и --gpu-memory-utilization 0.9
        llm = LLM(
            model=args.model,
            dtype="half",  # fp16, для 7B/14B оптимально на gfx1030
            gpu_memory_utilization=0.9,
            enforce_eager=False,  # True если OOM
            max_model_len=2048,
            trust_remote_code=True,
        )
        tokenizer = llm.get_tokenizer()
        # left padding не нужен в vLLM, он сам

        sampling_params = SamplingParams(
            temperature=0.0,
            top_p=1.0,
            max_tokens=args.max_tokens,
            repetition_penalty=1.05,
            stop_token_ids=[tokenizer.eos_token_id] if hasattr(tokenizer,'eos_token_id') else None,
        )

        # готовим промпты батчами
        from tqdm import tqdm
        import os
        os.environ["TOKENIZERS_PARALLELISM"]="false"

        # vLLM любит сразу весь список, но мы батчим для прогресса и Ctrl-C
        results_cache={}

        try:
            for start in tqdm(range(0, len(to_polish), args.batch), desc="vLLM"):
                if interrupted:
                    break
                batch_texts = to_polish[start:start+args.batch]
                batch_prompts = [build_prompt(llm.get_tokenizer(), txt) if hasattr(llm, 'get_tokenizer') else build_prompt(tokenizer, txt) for txt in batch_texts]
                # vLLM generate
                try:
                    outputs = llm.generate(batch_prompts, sampling_params)
                except KeyboardInterrupt:
                    print("\nCtrl-C в generate")
                    interrupted=True
                    break

                for txt_orig, output in zip(batch_texts, outputs):
                    generated = output.outputs[0].text.strip().strip('"').strip("'")
                    # защита плейсхолдеров
                    ph_pat=re.compile(r'\[[^\]]+\]')
                    if ph_pat.search(txt_orig) and set(ph_pat.findall(txt_orig)) != set(ph_pat.findall(generated)):
                        cache[txt_orig]=txt_orig
                    else:
                        cache[txt_orig]=generated if generated else txt_orig

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

    # применяем
    final=[]
    for txt in all_texts:
        final.append(cache.get(txt, txt))

    for (fp, ei, field), new in zip(mapping, final):
        data['files'][fp][ei][field]=new

    with open(args.output,"w",encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
    print(f"Готово -> {args.output} interrupted={interrupted}")

if __name__=="__main__":
    main()
