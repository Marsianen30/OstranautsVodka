#!/usr/bin/env python3
"""
translate_big.py — перевод Ostranauts с более тяжёлыми моделями
Поддерживает:
  - Helsinki-NLP/opus-mt-en-ru (базовая, 300M, 3GB VRAM)
  - Helsinki-NLP/opus-mt-tc-big-en-ru (большая, ~1GB модель, лучше качество)
  - facebook/nllb-200-distilled-600M (2.5GB)
  - facebook/nllb-200-1.3B (5-6GB)
  - facebook/nllb-200-3.3B (12-14GB) — влезает в RX 6800 16GB

Для LLM режима (Qwen, Llama) смотри translate_llm.py

Установка (в venv!):
  python -m venv ~/ostranslator
  source ~/ostranslator/bin/activate
  pip install torch --index-url https://download.pytorch.org/whl/rocm6.0
  pip install transformers sentencepiece sacremoses tqdm bitsandbytes accelerate

Запуск:
  python translate_big.py --input untranslated.json --output translated_big.json --model facebook/nllb-200-3.3B --batch 16 --device cuda:0
  python translate_big.py --model Helsinki-NLP/opus-mt-tc-big-en-ru --batch 64 --device cuda:0

Кэш: cache_big.json
"""

import argparse, json, re, gc, signal
from collections import defaultdict
from pathlib import Path

PROTECT_ACRO = ["CCRE","OKLG","VENC","VNCA","GalCon","BCER","BCRS","GF"]
MANUAL_DICT = {
    "???": "???",
    "Enemy Spawn Blocked": "Блокировка появления врагов",
    "Due Pirate Spawn": "Ожидается пират",
    "Due Faction Spawn": "Ожидается корабль фракции",
    "Pristine": "Нетронутый",
    "NO DOCKING FACILITIES": "НЕТ СТЫКОВОЧНЫХ СООРУЖЕНИЙ",
    "Piracy": "Пиратство",
    "false": "ложь", "Neutral": "Нейтрально", ".": ".",
}

CORRECTIONS = {
    "Спаун": "появление", "спавн": "появление",
    "Пристин": "Нетронутый",
    "ДОКУШИТЕЛЬНЫЕ ПОМЕЩЕНИЯ": "НЕТ СТЫКОВОЧНЫХ СООРУЖЕНИЙ",
    "Отбой в открытии": "Отказ в открытии",
    "ККЭЙР": "CCRE", "ККЭВ": "CCRE", "RCRE": "CCRE", "ИКЭ": "CCRE",
    "космодрома": "скафандра", "Космодрома": "Скафандра",
    "космодром": "скафандр", "ЭВА": "ВКД",
    "скафандр и шлем, прежде чем использовать шлюз.": "скафандр и шлем перед использованием шлюза.",
}

def apply_corrections(t):
    for k,v in CORRECTIONS.items():
        if k in t:
            t=t.replace(k,v)
    return t

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
        if p is None or p=='':
            continue
        if ph_regex.fullmatch(p) or acr_regex.fullmatch(p):
            res.append((True,p))
        else:
            res.append((False,p))
    return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="untranslated.json")
    parser.add_argument("--output", default="translated_big.json")
    parser.add_argument("--cache", default="cache_big.json")
    parser.add_argument("--nocache", action="store_true", help="отключить чтение/запись кэша для макс. скорости")
    parser.add_argument("--model", default="Helsinki-NLP/opus-mt-tc-big-en-ru", help="model name")
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    interrupted=False
    def handle_sigint(signum, frame):
        nonlocal interrupted
        print("\n\nCtrl-C, сохраняю кэш и выхожу...")
        interrupted=True
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    with open(args.input,"r",encoding="utf-8") as f:
        data=json.load(f)

    unique_map={}
    for entries in data['files'].values():
        for e in entries:
            for field in ['strNameFriendly','strNameShort','strTitle','strDesc','original']:
                if field in e and e[field] and e[field] not in unique_map:
                    unique_map[e[field]]=None

    cache_path=Path(args.cache)
    if not args.nocache and cache_path.exists():
        try:
            with open(cache_path,"r",encoding="utf-8") as cf:
                cached=json.load(cf)
                for k,v in cached.items():
                    if k in unique_map:
                        unique_map[k]=v
            print(f"Кэш загружен, уже переведено: {len([v for v in unique_map.values() if v is not None])}")
        except Exception as ex:
            print(f"cache load fail {ex}")
    elif args.nocache:
        print("Кэш отключен флагом --nocache")

    for txt in list(unique_map.keys()):
        if unique_map[txt] is None and txt.strip() in MANUAL_DICT:
            unique_map[txt]=MANUAL_DICT[txt.strip()]

    to_translate=[t for t,v in unique_map.items() if v is None]
    print(f"Уникальных: {len(unique_map)}, осталось: {len(to_translate)}")

    if to_translate:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch

        print(f"Loading {args.model} on {args.device}")
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        model = AutoModelForSeq2SeqLM.from_pretrained(args.model, torch_dtype=torch.float16 if "cuda" in args.device else torch.float32)
        
        if "cuda" in args.device and not torch.cuda.is_available():
            print("CUDA/ROCm not available -> cpu")
            args.device="cpu"
        
        model.to(args.device)
        model.eval()

        # Для NLLB нужно указать языки
        is_nllb = "nllb" in args.model.lower()
        src_lang = "eng_Latn"
        tgt_lang = "rus_Cyrl"
        if is_nllb:
            tokenizer.src_lang = src_lang
            # форсируем русский
            forced_bos = tokenizer.convert_tokens_to_ids(tgt_lang)

        tasks=[]
        text_splits={}
        for idx, txt in enumerate(to_translate):
            if '\n' in txt:
                lines=txt.split('\n')
                parts_per_line=[]
                for line in lines:
                    parts=split_protected(line)
                    parts_per_line.append(parts)
                    for is_prot, content in parts:
                        if not is_prot and content.strip() and re.search(r'[A-Za-z]', content):
                            m=re.match(r'^(\s*)(.*?)(\s*)$', content, re.DOTALL)
                            if m:
                                lead,core,trail=m.groups()
                                if core.strip():
                                    tasks.append({'text_idx':idx,'line_idx':len(parts_per_line)-1,'lead':lead,'core':core,'trail':trail})
                            else:
                                tasks.append({'text_idx':idx,'line_idx':len(parts_per_line)-1,'lead':'','core':content,'trail':''})
                text_splits[txt]=('multiline',parts_per_line)
            else:
                parts=split_protected(txt)
                text_splits[txt]=('single',parts)
                for is_prot, content in parts:
                    if not is_prot and content.strip() and re.search(r'[A-Za-z]', content):
                        m=re.match(r'^(\s*)(.*?)(\s*)$', content, re.DOTALL)
                        if m:
                            lead,core,trail=m.groups()
                            if core.strip():
                                tasks.append({'text_idx':idx,'line_idx':None,'lead':lead,'core':core,'trail':trail})
                        else:
                            tasks.append({'text_idx':idx,'line_idx':None,'lead':'','core':content,'trail':''})

        cores=[t['core'] for t in tasks]
        print(f"Сегментов: {len(cores)}")

        translated_cores=[]
        from tqdm import tqdm
        try:
            for i in tqdm(range(0,len(cores),args.batch), desc="Перевод"):
                if interrupted:
                    print("\nПрервано флагом, сохраняю...")
                    break
                batch=cores[i:i+args.batch]
                tokens=tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=256).to(args.device)
                try:
                    with torch.no_grad():
                        if is_nllb:
                            out=model.generate(**tokens, max_length=256, num_beams=1, forced_bos_token_id=forced_bos)
                        else:
                            out=model.generate(**tokens, max_length=256, num_beams=1)
                except KeyboardInterrupt:
                    print("\nCtrl-C внутри generate, сохраняю...")
                    interrupted=True
                    break
                except RuntimeError as e:
                    print(f"\nRuntimeError OOM в батче {i}: {e}, пропускаю")
                    # заполняем заглушками
                    dec=[c for c in batch] # fallback оригинал
                    translated_cores.extend(dec)
                    continue
                dec=[tokenizer.decode(t, skip_special_tokens=True) for t in out]
                dec=[apply_corrections(d) for d in dec]
                translated_cores.extend(dec)
                del tokens,out
                gc.collect()
                if "cuda" in args.device:
                    try:
                        import torch
                        torch.cuda.empty_cache()
                    except:
                        pass
        except KeyboardInterrupt:
            print("\nПрервано по Ctrl-C")
            interrupted=True

        # если прервали, дополняем недошедшие оригиналами чтобы сборка не упала
        if len(translated_cores) < len(cores):
            print(f"Досрочный выход: переведено {len(translated_cores)}/{len(cores)}, добиваю оригиналами")
            translated_cores.extend(cores[len(translated_cores):])

        tasks_by_text=defaultdict(list)
        for task_idx, task in enumerate(tasks):
            tasks_by_text[task['text_idx']].append((task_idx,task))

        for text_idx, txt in enumerate(to_translate):
            mode,parts_data=text_splits[txt]
            if mode=='multiline':
                task_list=tasks_by_text.get(text_idx,[])
                ptr=0
                lines=[]
                for line_parts in parts_data:
                    tparts=[]
                    for is_prot,content in line_parts:
                        if is_prot:
                            tparts.append(content)
                        else:
                            if not content.strip() or not re.search(r'[A-Za-z]',content):
                                tparts.append(content)
                            else:
                                if ptr < len(task_list):
                                    ti,t=task_list[ptr]
                                    tparts.append(t['lead']+translated_cores[ti]+t['trail'])
                                    ptr+=1
                                else:
                                    tparts.append(content)
                    lines.append(''.join(tparts))
                unique_map[txt]='\n'.join(lines)
            else:
                parts=parts_data
                task_list=tasks_by_text.get(text_idx,[])
                ptr=0
                tparts=[]
                for is_prot,content in parts:
                    if is_prot:
                        tparts.append(content)
                    else:
                        if not content.strip() or not re.search(r'[A-Za-z]',content):
                            tparts.append(content)
                        else:
                            if ptr < len(task_list):
                                ti,t=task_list[ptr]
                                tparts.append(t['lead']+translated_cores[ti]+t['trail'])
                                ptr+=1
                            else:
                                tparts.append(content)
                unique_map[txt]=''.join(tparts)

        if not args.nocache:
            with open(cache_path,"w",encoding="utf-8") as cf:
                json.dump(unique_map,cf,ensure_ascii=False, indent=2)
            print(f"Кэш сохранён в {cache_path}")
        else:
            print("Пропуск сохранения кэша (--nocache)")

    # сборка
    output_files={}
    for file_path, entries in data['files'].items():
        out=[]
        for e in entries:
            if 'key' in e and 'original' in e:
                orig=e['original']
                out.append({"key":e['key'],"original":orig,"translation":unique_map.get(orig,orig)})
            else:
                oe={}
                if 'strName' in e:
                    oe['strName']=e['strName']
                existing=e.get('_existing',{})
                for field in ['strNameFriendly','strNameShort','strTitle','strDesc']:
                    if field in e and e[field]:
                        tv=unique_map.get(e[field], e[field])
                        if field in existing and re.search(r'[А-Яа-я]', existing[field]):
                            tv=existing[field]
                        oe[field]=tv
                    elif field in existing:
                        oe[field]=existing[field]
                for k,v in e.items():
                    if k not in oe and k!='_existing' and k not in ['strNameFriendly','strNameShort','strTitle','strDesc']:
                        oe[k]=v
                out.append(oe)
        output_files[file_path]=out

    with open(args.output,"w",encoding="utf-8") as out:
        json.dump({"files":output_files}, out, ensure_ascii=False, indent=2)
    print(f"Готово -> {args.output}")

if __name__=="__main__":
    main()
