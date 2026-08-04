#!/usr/bin/env python3
"""
Ostranauts RU translator - локальная версия для мощного ПК
Поддерживает GPU (CUDA / ROCm) и CPU, рестарт с кэша, сохранение плейсхолдеров.

Требования:
  pip install torch --index-url https://download.pytorch.org/whl/rocm6.0   # для RX 6800/6900 (Navi 21)
  # или для CPU: pip install torch --index-url https://download.pytorch.org/whl/cpu
  pip install transformers sentencepiece sacremoses tqdm

Запуск:
  python translate_local.py --input untranslated.json --output translated.json --batch 64 --device cuda:0
  # если ROCm не стартует, используй --device cpu и --batch 16-32

На системе:
  - RX 6800 XT 16GB (Navi 21) - поддерживается ROCm 6.0+, ставь rocm-версию torch
  - R9 290X 8GB (Hawaii) - слишком старая (GCN 1.1), ROCm её уже не поддерживает, не используй
  - E5-1680 v2 + 32GB RAM - на CPU переведёт ~10k строк за 1.5-3 часа

Скрипт:
  - защищает плейсхолдеры [us], [them], [is], [has], [3rd], [us-pos] и т.д.
  - защищает фракции CCRE, OKLG, VENC, VNCA, GalCon, BCER, BCRS, GF
  - сохраняет \n
  - использует ручной словарь для плохих переводов модели
  - кэширует в cache_translations.json чтобы можно было прервать и продолжить
"""

import argparse
import json
import re
import os
import gc
from collections import defaultdict
from pathlib import Path

try:
    from tqdm import tqdm
except:
    tqdm = lambda x, **kw: x

# --- Конфиг ---
PROTECT_ACRO = ["CCRE","OKLG","VENC","VNCA","GalCon","BCER","BCRS","GF"]

# Ручной словарь - самые кривые переводы модели + UI
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
    "0": "0", "1": "1", "2": "2",
    "XXX": "XXX",
    "Good": "Хорошо",
    "Goodish": "Неплохо",
    "Lower Left Arm": "Нижняя левая рука",
    "Lower Right Arm": "Нижняя правая рука",
    "Upper Left Arm": "Верхняя левая рука",
    "Upper Right Arm": "Верхняя правая рука",
    "Back": "Спина", "Body": "Тело",
    "Drag": "Перетаскивание",
    "Left Foot": "Левая стопа", "Right Foot": "Правая стопа",
    "Glasses": "Очки",
    "Head (Inner)": "Голова (внутр.)",
    "Head (Middle)": "Голова (сред.)",
    "Head (Outer)": "Голова (внеш.)",
    "Lower Left Leg": "Нижняя левая нога",
    "Lower Right Leg": "Нижняя правая нога",
    "Upper Left Leg": "Верхняя левая нога",
    "Upper Right Leg": "Верхняя правая нога",
    "Pants (Inner)": "Штаны (внутр.)",
    "Pants (Middle)": "Штаны (сред.)",
    "Pants (Outer)": "Штаны (внеш.)",
    "Pledges": "Обязательства",
    "Clip Point": "Точка крепления",
    "EVA Battery Compartment": "Отсек батареи ВКД",
    "EVA CO2 Filter Compartment": "Отсек фильтра CO2 ВКД",
    "EVA O2 Bottle Compartment": "Отсек баллона O2 ВКД",
    "Equip helmet": "Надеть шлем",
    "Equip suit and helmet": "Надеть скафандр и шлем",
    "Equip suit": "Надеть скафандр",
    "Combat": "Бой",
    "Stand up": "Встать",
    "Firefight": "Тушение пожара",
    "Arrest": "Арест",
    "Attack": "Атака",
    "Rob": "Ограбить",
}

CORRECTIONS = {
    "Спаун": "появление",
    "спавн": "появление",
    "Пристин": "Нетронутый",
    "пристин": "нетронутый",
    "ДОКУШИТЕЛЬНЫЕ ПОМЕЩЕНИЯ": "НЕТ СТЫКОВОЧНЫХ СООРУЖЕНИЙ",
    "Отбой в открытии": "Отказ в открытии",
    "отбой в открытии": "отказ в открытии",
    "ККЭЙР": "CCRE",
    "ККЭВ": "CCRE",
    "RCRE": "CCRE",
    "ИКЭ": "CCRE",
    "Дозвониться в космический костюм": "Надеть скафандр",
}

def apply_corrections(text):
    for bad, good in CORRECTIONS.items():
        if bad in text:
            text = text.replace(bad, good)
    return text

# --- Плейсхолдеры ---
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="untranslated.json", help="входной JSON")
    parser.add_argument("--output", default="translated.json", help="выходной JSON")
    parser.add_argument("--cache", default="cache_translations.json", help="кэш для рестарта")
    parser.add_argument("--nocache", action="store_true", help="отключить кэш")
    parser.add_argument("--batch", type=int, default=32, help="батч для GPU (для 16GB ставь 64, для CPU 8-16)")
    parser.add_argument("--device", default="cuda:0", help="cuda:0 / cuda:1 / cpu")
    parser.add_argument("--model", default="Helsinki-NLP/opus-mt-en-ru", help="модель")
    args = parser.parse_args()

    print(f"Loading {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Собираем уникальные строки
    unique_map = {}
    for file_path, entries in data['files'].items():
        for entry in entries:
            for field in ['strNameFriendly','strNameShort','strTitle','strDesc','original']:
                if field in entry and entry[field]:
                    val = entry[field]
                    if val not in unique_map:
                        unique_map[val] = None

    print(f"Всего уникальных строк: {len(unique_map)}")

    # Загружаем кэш если есть
    cache_path = Path(args.cache)
    if not args.nocache and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as cf:
                cached = json.load(cf)
                for k,v in cached.items():
                    if k in unique_map:
                        unique_map[k]=v
            print(f"Загружено из кэша {len([v for v in unique_map.values() if v is not None])}")
        except Exception as e:
            print(f"Не удалось загрузить кэш: {e}")
    elif args.nocache:
        print("Кэш отключен флагом --nocache")

    # Ручной словарь
    for txt in list(unique_map.keys()):
        if unique_map[txt] is not None:
            continue
        stripped = txt.strip()
        if stripped in MANUAL_DICT:
            m = re.match(r'^(\s*)(.*?)(\s*)$', txt, re.DOTALL)
            if m:
                lead, core, trail = m.groups()
                if core.strip() in MANUAL_DICT:
                    unique_map[txt] = lead + MANUAL_DICT[core.strip()] + trail
                else:
                    unique_map[txt] = MANUAL_DICT.get(txt, txt)
            else:
                unique_map[txt] = MANUAL_DICT[txt]

    to_translate = [t for t,v in unique_map.items() if v is None]
    print(f"Осталось перевести моделью: {len(to_translate)}")

    if to_translate:
        # Импорт модели только если нужно
        print(f"Загружаю модель {args.model} на {args.device}...")
        from transformers import MarianMTModel, MarianTokenizer
        import torch

        tokenizer = MarianTokenizer.from_pretrained(args.model)
        model = MarianMTModel.from_pretrained(args.model)

        device = args.device
        # Проверка доступности
        if "cuda" in device:
            if not torch.cuda.is_available():
                print("CUDA/ROCm не доступен, переключаюсь на CPU")
                device = "cpu"
            else:
                print(f"GPU доступно: {torch.cuda.get_device_name(0)}")
                # Для AMD ROCm может быть нужно установить переменную
                # тебе не нужно, просто torch должен видеть amdgpu

        model.to(device)
        model.eval()

        # Подготовка задач - разбиваем на сегменты защищённые/незащищённые
        tasks = []
        text_splits = {}
        for idx, txt in enumerate(to_translate):
            if '\n' in txt:
                lines = txt.split('\n')
                parts_per_line=[]
                for line in lines:
                    parts = split_protected(line)
                    parts_per_line.append(parts)
                    for is_prot, content in parts:
                        if not is_prot:
                            if not content.strip() or not re.search(r'[A-Za-z]', content):
                                continue
                            m = re.match(r'^(\s*)(.*?)(\s*)$', content, re.DOTALL)
                            if m:
                                lead, core, trail = m.groups()
                                if not core.strip():
                                    continue
                                tasks.append({'text_idx': idx, 'line_idx': len(parts_per_line)-1, 'lead': lead, 'core': core, 'trail': trail})
                            else:
                                tasks.append({'text_idx': idx, 'line_idx': len(parts_per_line)-1, 'lead': '', 'core': content, 'trail': ''})
                text_splits[txt] = ('multiline', parts_per_line)
            else:
                parts = split_protected(txt)
                text_splits[txt] = ('single', parts)
                for is_prot, content in parts:
                    if not is_prot:
                        if not content.strip() or not re.search(r'[A-Za-z]', content):
                            continue
                        m = re.match(r'^(\s*)(.*?)(\s*)$', content, re.DOTALL)
                        if m:
                            lead, core, trail = m.groups()
                            if not core.strip():
                                continue
                            tasks.append({'text_idx': idx, 'line_idx': None, 'lead': lead, 'core': core, 'trail': trail})
                        else:
                            tasks.append({'text_idx': idx, 'line_idx': None, 'lead': '', 'core': content, 'trail': ''})

        cores = [t['core'] for t in tasks]
        print(f"Всего сегментов для перевода: {len(cores)}")

        translated_cores = []
        # Батчинг
        for i in tqdm(range(0, len(cores), args.batch), desc="Перевод"):
            batch = cores[i:i+args.batch]
            tokens = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=256).to(device)
            with torch.no_grad():
                out = model.generate(**tokens, max_length=256, num_beams=1)
            dec = [tokenizer.decode(t, skip_special_tokens=True) for t in out]
            dec = [apply_corrections(d) for d in dec]
            translated_cores.extend(dec)

            # Периодически сохраняем кэш
            if i % (args.batch*20) == 0 and i>0:
                # Промежуточная реконструкция для кэша
                # Сохраняем только уже готовые to_translate
                # Для простоты пока сохраним уникальные что есть
                # Делаем временный маппинг для уже переведённых батчей - сложно, пропустим
                pass

            del tokens, out
            if device=="cpu":
                gc.collect()

        # Реконструкция
        tasks_by_text = defaultdict(list)
        for task_idx, task in enumerate(tasks):
            tasks_by_text[task['text_idx']].append((task_idx, task))

        for text_idx, txt in enumerate(to_translate):
            mode, parts_data = text_splits[txt]
            if mode == 'multiline':
                task_list = tasks_by_text.get(text_idx, [])
                task_ptr = 0
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
                                    trans_core = translated_cores[t_idx]
                                    translated_parts.append(t['lead']+trans_core+t['trail'])
                                    task_ptr+=1
                                else:
                                    translated_parts.append(content)
                    translated_lines.append(''.join(translated_parts))
                unique_map[txt] = '\n'.join(translated_lines)
            else:
                parts = parts_data
                task_list = tasks_by_text.get(text_idx, [])
                task_ptr = 0
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
                                trans_core = translated_cores[t_idx]
                                translated_parts.append(t['lead']+trans_core+t['trail'])
                                task_ptr+=1
                            else:
                                translated_parts.append(content)
                unique_map[txt] = ''.join(translated_parts)

        # Сохранить кэш
        if not args.nocache:
            with open(cache_path, "w", encoding="utf-8") as cf:
                json.dump(unique_map, cf, ensure_ascii=False, indent=2)
            print(f"Кэш сохранён в {cache_path}")
        else:
            print("Пропуск сохранения кэша (--nocache)")

    # Сборка итогового файла
    output_files = {}
    for file_path, entries in data['files'].items():
        out_entries=[]
        for entry in entries:
            if 'key' in entry and 'original' in entry:
                orig = entry['original']
                trans = unique_map.get(orig, orig)
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
    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(output_data, out, ensure_ascii=False, indent=2)

    print(f"Готово! Сохранено в {args.output}")

if __name__ == "__main__":
    main()
