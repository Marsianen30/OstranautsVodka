import json, re, os, gc
print("Loading model...", flush=True)
from transformers import MarianMTModel, MarianTokenizer
import torch

model_name = "Helsinki-NLP/opus-mt-en-ru"
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)
print("Model loaded", flush=True)

PROTECT_ACRO = ["CCRE","OKLG","VENC","VNCA","GalCon","BCER","BCRS","GF"]

MANUAL_DICT = {
    "???": "???",
    "Enemy Spawn Blocked": "Блокировка появления врагов",
    "Due Pirate Spawn": "Ожидается пират",
    "Due Faction Spawn": "Ожидается корабль фракции",
    "Pristine": "Нетронутый",
    "Attempting to fight fire": "Пытается потушить пожар",
    "CCRE Arrest Warning Count": "Предупреждений об аресте CCRE",
    "CCRE Arrest Warrant": "Ордер на арест CCRE",
    "CCRE Public Enemy": "Враг общества CCRE",
    "CCRE Trespass Warrant": "Ордер за вторжение CCRE",
    "CCRE Arrest Warrant for Stolen Ship": "Ордер CCRE за угон корабля",
    "CCRE Arrest Warrant for Failure to Undock": "Ордер CCRE за отказ от расстыковки",
    "Used AntiHypo-V": "Применён АнтиГипо-В",
    "AntiHypo-V Course Complete": "Курс АнтиГипо-В завершён",
    "AntiHypo-V Dose Count": "Доз АнтиГипо-В",
    "G-LOC": "G-LOC",
    "Greeted by a Friend": "Приветствие от друга",
    "Greeted a friend recently": "Недавно поприветствовал друга",
    "Greeted by a Crewmate": "Приветствие от члена экипажа",
    "Greeted Captain Recently": "Недавно поприветствовал капитана",
    "Greeted by an Enemy": "Приветствие от врага",
    "Told off an Enemy": "Отшил врага",
    "Kissed a lover recently": "Недавно поцеловал возлюбленного",
    "Kissed": "Поцелован",
    "Installed Recently": "Недавно установлено",
    "Uninstalled Recently": "Недавно демонтировано",
    "Repaired Recently": "Недавно отремонтировано",
    "Restored Recently": "Недавно восстановлено",
    "Dismantled Recently": "Недавно разобрано",
    "Patched Recently": "Недавно залатано",
    "Bashed Recently": "Недавно разбито",
    "Attacked Recently": "Недавно атаковано",
    "Admired Recently": "Недавно любовался",
    "Studied Recently": "Недавно изучал",
    "Watched News Recently": "Недавно смотрел новости",
    "Watched Drama Recently": "Недавно смотрел драму",
    "Slept Recently": "Недавно спал",
    "Ate Recently": "Недавно ел",
    "Ate Well Recently": "Недавно хорошо поел",
    "Drank Recently": "Недавно пил",
    "Drank Caffeine Recently": "Недавно пил кофеин",
    "Drank Alcohol Recently": "Недавно пил алкоголь",
    "Exercised Recently": "Недавно тренировался",
    "Played Game Recently": "Недавно играл",
    "Anti-HypoV Dose: 1": "Доза АнтиГипо-В: 1",
    "Malaise": "Недомогание",
    "Mild Hypercapnia": "Лёгкая гиперкапния",
    "Moderate Hypercapnia": "Умеренная гиперкапния",
    "Advanced Hypercapnia": "Прогрессирующая гиперкапния",
    "Severe Hypercapnia": "Тяжёлая гиперкапния",
    "Critical Hypercapnia": "Критическая гиперкапния",
    "Lethal Hypercapnia": "Смертельная гиперкапния",
    "Asphyxiated by Hypercapnia": "Удушье от гиперкапнии",
    "Stinging Throat and Eyes": "Жжение в горле и глазах",
    "Burning Throat and Eyes": "Жжение в горле и глазах",
    "Lethal Smoke Inhalation": "Смертельное отравление дымом",
    "Fire Chem: Empty": "Огнетушитель: пуст",
    "Fire Chem: Low": "Огнетушитель: мало",
    "Fire Chem: Medium": "Огнетушитель: половина",
    "Fire Chem: Full": "Огнетушитель: полон",
    "Norm CO": "Норма CO",
    "Norm Smoke": "Норма дыма",
    "NO DOCKING FACILITIES": "НЕТ СТЫКОВОЧНЫХ СООРУЖЕНИЙ",
    "Piracy": "Пиратство",
    "Multiple accounts of murder": "Множественные убийства",
    "Fraud": "Мошенничество",
    "Black market trading": "Торговля на чёрном рынке",
    "Extortion": "Вымогательство",
    "Armed robbery": "Вооружённое ограбление",
    "Weapons trafficking": "Торговля оружием",
    "Hacking secure networks": "Взлом защищённых сетей",
    "Spaceship theft": "Угон космического корабля",
    "Station bombings": "Взрывы на станциях",
    "Destruction of public property": "Уничтожение общественного имущества",
    "Tampering with signal beacons": "Повреждение сигнальных маяков",
    "Smuggling restricted tech": "Контрабанда запрещённых технологий",
    "Assaulting security forces": "Нападение на силы безопасности",
    "Raiding cargo freighters": "Налёты на грузовые суда",
    "Raiding civilian ships": "Налёты на гражданские суда",
    "Attacking patrols": "Нападение на патрули",
    "Sabotage of corporate infrastructure": "Саботаж корпоративной инфраструктуры",
    "Espionage": "Шпионаж",
    "Murder": "Убийство",
    "Cannot reach that location.": "Невозможно добраться до этого места.",
    "Done": "Готово",
    "OK": "ОК",
    ".": ".",
    "false": "ложь",
    "Neutral": "Нейтрально",
    "0": "0",
    "1": "1",
    "2": "2",
    "XXX": "XXX",
}

CORRECTIONS = {
    "Спаун": "появление",
    "спавн": "появление",
    "Пристин": "Нетронутый",
    "ДОКУШИТЕЛЬНЫЕ ПОМЕЩЕНИЯ": "НЕТ СТЫКОВОЧНЫХ СООРУЖЕНИЙ",
    "Отбой в открытии": "Отказ в открытии",
    "ККЭЙР": "CCRE",
    "ККЭВ": "CCRE",
    "RCRE": "CCRE",
    "ИКЭ": "CCRE",
}

def apply_corrections(text):
    for bad, good in CORRECTIONS.items():
        if bad in text:
            text = text.replace(bad, good)
    return text

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
            res.append((True, p))
        else:
            res.append((False, p))
    return res

print("Loading input", flush=True)
with open("/home/user/uploads/untranslated.json","r",encoding="utf-8") as f:
    data=json.load(f)

unique_map={}
for file_path, entries in data['files'].items():
    for entry in entries:
        for field in ['strNameFriendly','strNameShort','strTitle','strDesc','original']:
            if field in entry and entry[field]:
                val=entry[field]
                if val not in unique_map:
                    unique_map[val]=None

print(f"Unique {len(unique_map)}", flush=True)

for txt in list(unique_map.keys()):
    stripped=txt.strip()
    if stripped in MANUAL_DICT:
        m=re.match(r'^(\s*)(.*?)(\s*)$', txt, re.DOTALL)
        if m:
            lead, core, trail=m.groups()
            if core.strip() in MANUAL_DICT:
                unique_map[txt]=lead+MANUAL_DICT[core.strip()]+trail
            else:
                unique_map[txt]=MANUAL_DICT.get(txt, txt)
        else:
            unique_map[txt]=MANUAL_DICT[txt]

to_translate=[t for t,v in unique_map.items() if v is None]
print(f"To translate {len(to_translate)}", flush=True)

# Prepare tasks
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
                if not is_prot:
                    if not content.strip() or not re.search(r'[A-Za-z]', content):
                        continue
                    m=re.match(r'^(\s*)(.*?)(\s*)$', content, re.DOTALL)
                    if m:
                        lead, core, trail=m.groups()
                        if not core.strip():
                            continue
                        tasks.append({'text_idx': idx, 'line_idx': len(parts_per_line)-1, 'lead': lead, 'core': core, 'trail': trail})
                    else:
                        tasks.append({'text_idx': idx, 'line_idx': len(parts_per_line)-1, 'lead': '', 'core': content, 'trail': ''})
        text_splits[txt]=('multiline', parts_per_line)
    else:
        parts=split_protected(txt)
        text_splits[txt]=('single', parts)
        for is_prot, content in parts:
            if not is_prot:
                if not content.strip() or not re.search(r'[A-Za-z]', content):
                    continue
                m=re.match(r'^(\s*)(.*?)(\s*)$', content, re.DOTALL)
                if m:
                    lead, core, trail=m.groups()
                    if not core.strip():
                        continue
                    tasks.append({'text_idx': idx, 'line_idx': None, 'lead': lead, 'core': core, 'trail': trail})
                else:
                    tasks.append({'text_idx': idx, 'line_idx': None, 'lead': '', 'core': content, 'trail': ''})

print(f"Tasks {len(tasks)}", flush=True)

# Batch translate with small batch and num_beams=1
cores=[t['core'] for t in tasks]
translated_cores=[]
batch_size=8
for i in range(0, len(cores), batch_size):
    batch=cores[i:i+batch_size]
    tokens=tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=256)
    with torch.no_grad():
        out=model.generate(**tokens, max_length=256, num_beams=1, early_stopping=True)
    dec=[tokenizer.decode(t, skip_special_tokens=True) for t in out]
    dec=[apply_corrections(d) for d in dec]
    translated_cores.extend(dec)
    # free
    del tokens, out
    gc.collect()
    if i % (batch_size*20)==0:
        print(f"Batch {i}/{len(cores)}", flush=True)

# Reconstruct
from collections import defaultdict
tasks_by_text=defaultdict(list)
for task_idx, task in enumerate(tasks):
    tasks_by_text[task['text_idx']].append((task_idx, task))

for text_idx, txt in enumerate(to_translate):
    mode, parts_data = text_splits[txt]
    if mode=='multiline':
        task_list=tasks_by_text.get(text_idx, [])
        task_ptr=0
        translated_lines=[]
        for line_parts in parts_data:
            translated_parts=[]
            for is_prot, content in line_parts:
                if is_prot:
                    translated_parts.append(content)
                else:
                    if not content.strip() or not re.search(r'[A-Za-z]', content):
                        translated_parts.append(content)
                    else:
                        if task_ptr < len(task_list):
                            t_idx, t = task_list[task_ptr]
                            trans_core=translated_cores[t_idx]
                            translated_parts.append(t['lead']+trans_core+t['trail'])
                            task_ptr+=1
                        else:
                            translated_parts.append(content)
            translated_lines.append(''.join(translated_parts))
        reconstructed='\n'.join(translated_lines)
        unique_map[txt]=reconstructed
    else:
        parts=parts_data
        task_list=tasks_by_text.get(text_idx, [])
        task_ptr=0
        translated_parts=[]
        for is_prot, content in parts:
            if is_prot:
                translated_parts.append(content)
            else:
                if not content.strip() or not re.search(r'[A-Za-z]', content):
                    translated_parts.append(content)
                else:
                    if task_ptr < len(task_list):
                        t_idx, t = task_list[task_ptr]
                        trans_core=translated_cores[t_idx]
                        translated_parts.append(t['lead']+trans_core+t['trail'])
                        task_ptr+=1
                    else:
                        translated_parts.append(content)
        reconstructed=''.join(translated_parts)
        unique_map[txt]=reconstructed

print("Reconstruction done", flush=True)

# Build output
output_files={}
for file_path, entries in data['files'].items():
    out_entries=[]
    for entry in entries:
        if 'key' in entry and 'original' in entry:
            orig=entry['original']
            trans=unique_map.get(orig, orig)
            out_entries.append({"key": entry['key'], "original": orig, "translation": trans})
        else:
            out_entry={}
            if 'strName' in entry:
                out_entry['strName']=entry['strName']
            existing=entry.get('_existing',{})
            for field in ['strNameFriendly','strNameShort','strTitle','strDesc']:
                if field in entry and entry[field]:
                    orig_val=entry[field]
                    trans_val=unique_map.get(orig_val, orig_val)
                    if field in existing and re.search(r'[А-Яа-я]', existing[field]):
                        trans_val=existing[field]
                    out_entry[field]=trans_val
                elif field in existing:
                    out_entry[field]=existing[field]
            for k,v in entry.items():
                if k not in out_entry and k!='_existing' and k not in ['strNameFriendly','strNameShort','strTitle','strDesc']:
                    out_entry[k]=v
            out_entries.append(out_entry)
    output_files[file_path]=out_entries

output_data={"files": output_files}
with open("/home/user/translated.json","w",encoding="utf-8") as out:
    json.dump(output_data, out, ensure_ascii=False, indent=2)

print("Saved translated.json", flush=True)
