#!/usr/bin/env python3
"""
translate_html_protected.py — твоя идея с HTML + notranslate, но правильно

Идея:
  1. Парсим untranslated.json -> HTML где каждый [us], [gains] обёрнут в <span translate="no">[us]</span>
  2. Этот HTML скармливаем Яндекс.Документам / Google Документам (они уважают translate="no" и notranslate)
  3. Получаем переведённый HTML, парсим обратно, плейсхолдеры на месте

Почему PDF плохо — PDF теряет структуру. HTML с translate="no" — стандарт.

Плейсхолдеры в Ostranauts (501 штука):
  - местоимения: [us] (6305 раз), [them] (2107), [3rd] (304), [us-pos], [them-pos], [us-subj]...
  - вспомогательные: [is] (1782), [has] (752), [was], [were], [doesn't]...
  - глагольные: [gains] (67), [bashes], [says] (226), [asks] (210), [switches] (146) и ещё 485 штук типа [tells], [decides], [starts]...

Они нужны для склонения — движок подставляет "is/are", "has/have" в зависимости от [us]/[them].

Запуск:
  python translate_html_protected.py --input untranslated.json --html for_yandex.html

  # Этот for_yandex.html загружаешь на https://translate.yandex.ru/documents
  # или https://translate.google.com/intl/ru/about/ -> Документы
  # Выбираешь перевод EN->RU, скачиваешь переведённый HTML

  python translate_html_protected.py --parse translated_from_yandex.html --output fixed_from_yandex.json

Если Яндекс всё равно переведёт [us] -> [мы], значит он проигнорил translate="no" — тогда второй вариант:
  Заменяем [us] на __US__ , [gains] на __GAINS__ перед загрузкой, а после возвращаем.
  Флаг --use-underscores
"""

import argparse, json, re, html
from pathlib import Path
from html.parser import HTMLParser

placeholder_pat = re.compile(r'\[[^\]]+\]')

def protect_html(text, use_underscores=False):
    """Оборачиваем каждый [xxx] в <span translate=no>"""
    def repl(m):
        ph = m.group(0)
        if use_underscores:
            # [us] -> __US__ , [gains] -> __GAINS__ (что Яндекс не тронет)
            key = ph.strip('[]').upper().replace('-','_').replace("'",'').replace('"','')
            # делаем уникальным чтобы не конфликтовало с текстом
            return f"__PH_{key}__"
        else:
            # HTML5 way
            return f'<span translate="no">{html.escape(ph)}</span>'
    return placeholder_pat.sub(repl, html.escape(text))

def unprotect_html(text, use_underscores=False):
    # если использовали __PH_US__, возвращаем [us]
    if use_underscores:
        def repl2(m):
            inner = m.group(1)
            # __PH_US__ -> [us] , __PH_US_POS__ -> [us-pos]
            orig = inner.replace('_', '-').lower()
            # костыль для -pos, -subj и т.д.
            orig = orig.replace('-pos','-pos').replace('-subj','-subj').replace('-obj','-obj').replace('-reg-id','-regID')
            # восстанавливаем исходный регистр? упрощённо lower, потом маппим частые
            # Лучше хранить маппинг, но для примера lower
            return f"[{orig}]"
        text = re.sub(r'__PH_([A-Z0-9_]+?)__', repl2, text)
        return text
    else:
        # убираем <span> обёртку, оставляем [us]
        text = re.sub(r'<span[^>]*translate=["\']no["\'][^>]*>(.*?)</span>', r'\1', text, flags=re.IGNORECASE)
        text = re.sub(r'<span[^>]*class=["\']notranslate["\'][^>]*>(.*?)</span>', r'\1', text, flags=re.IGNORECASE)
        return html.unescape(text)

def json_to_html(json_path, html_path, use_underscores=False):
    with open(json_path,'r',encoding='utf-8') as f:
        data=json.load(f)

    html_lines=['<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>']
    html_lines.append('<style>.notranslate { background: #eee; }</style>')
    # Для каждого файла делаем секцию
    for file_path, entries in data['files'].items():
        html_lines.append(f'<h2 data-file="{html.escape(file_path)}">{html.escape(file_path)}</h2>')
        html_lines.append('<table border=1>')
        for idx, e in enumerate(entries):
            if 'key' in e:
                # strings.json
                orig=e['original']
                protected=protect_html(orig, use_underscores)
                html_lines.append(f'<tr data-key="{html.escape(e["key"])}" data-idx="{idx}"><td>{html.escape(e["key"])}</td><td class="orig" data-field="original">{protected}</td></tr>')
            else:
                strName=e.get('strName','')
                html_lines.append(f'<tr data-strname="{html.escape(strName)}" data-idx="{idx}"><td>{html.escape(strName)}</td>')
                for field in ['strNameFriendly','strTitle','strDesc']:
                    if field in e:
                        protected=protect_html(e[field], use_underscores)
                        html_lines.append(f'<td class="orig" data-field="{field}">{protected}</td>')
                html_lines.append('</tr>')
        html_lines.append('</table>')

    html_lines.append('</body></html>')
    Path(html_path).write_text('\n'.join(html_lines), encoding='utf-8')
    print(f"HTML для Яндекса сохранён: {html_path} — загружай на translate.yandex.ru/documents")

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.files={}
        self.current_file=None
        self.current_key=None
        self.current_strname=None
        self.current_field=None
        self.in_td=False
        self.buffer=""

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='h2' and 'data-file' in attrs:
            self.current_file=attrs['data-file']
            self.files.setdefault(self.current_file, [])
        if tag=='tr':
            self.current_key=attrs.get('data-key')
            self.current_strname=attrs.get('data-strname')
            self.current_idx=attrs.get('data-idx')
        if tag=='td' and 'data-field' in attrs:
            self.in_td=True
            self.current_field=attrs['data-field']
            self.buffer=""

    def handle_endtag(self, tag):
        if tag=='td' and self.in_td:
            # сохраняем
            text=self.buffer.strip()
            # разэкранируем плейсхолдеры если были в span
            text=unprotect_html(text, use_underscores=False)
            # также пробуем underscored вариант
            text=unprotect_html(text, use_underscores=True)

            # найдём куда
            if self.current_file not in self.files:
                self.files[self.current_file]=[]
            # расширяем список если нужно
            while len(self.files[self.current_file]) <= int(self.current_idx or 0):
                self.files[self.current_file].append({})

            entry=self.files[self.current_file][int(self.current_idx or 0)]
            if self.current_key:
                entry['key']=self.current_key
                entry[self.current_field]=text
            else:
                if self.current_strname:
                    entry['strName']=self.current_strname
                entry[self.current_field]=text

            self.in_td=False
            self.buffer=""

    def handle_data(self, data):
        if self.in_td:
            self.buffer+=data

def html_to_json(html_path, json_path, original_json_path, use_underscores=False):
    parser=MyHTMLParser()
    parser.current_file=None
    content=Path(html_path).read_text(encoding='utf-8')
    parser.feed(content)

    # теперь надо собрать итоговый JSON в формате как untranslated -> translated
    with open(original_json_path,'r',encoding='utf-8') as f:
        orig=json.load(f)

    output_files={}
    for file_path, orig_entries in orig['files'].items():
        translated_entries=parser.files.get(file_path, [])
        # маппим по strName/key
        orig_map={}
        for e in orig_entries:
            k=e.get('strName') or e.get('key')
            orig_map[k]=e

        out_list=[]
        for trans_e in translated_entries:
            k=trans_e.get('strName') or trans_e.get('key')
            o=orig_map.get(k, {})
            # проверяем плейсхолдеры на месте
            for field in ['strDesc','strTitle','strNameFriendly','original']:
                if field in trans_e:
                    # проверка
                    orig_ph=set(placeholder_pat.findall(o.get(field,'') or ''))
                    trans_ph=set(placeholder_pat.findall(trans_e[field]))
                    if orig_ph!=trans_ph:
                        print(f"ВНИМАНИЕ: плейсхолдеры не совпали в {file_path} {k} {field}: {orig_ph} vs {trans_ph}")

            # формируем как в формате translated.json
            if 'key' in trans_e:
                out_list.append({
                    "key": trans_e['key'],
                    "original": orig_map.get(trans_e['key'],{}).get('original',''),
                    "translation": trans_e.get('original','') or trans_e.get('translation','')
                })
            else:
                out_e={"strName": trans_e.get('strName','')}
                for fld in ['strNameFriendly','strTitle','strDesc']:
                    if fld in trans_e:
                        out_e[fld]=trans_e[fld]
                out_list.append(out_e)
        output_files[file_path]=out_list

    with open(json_path,'w',encoding='utf-8') as out:
        json.dump({"files":output_files}, out, ensure_ascii=False, indent=2)
    print(f"Сконверчено обратно: {json_path}")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input", default="untranslated.json", help="входной untranslated.json")
    parser.add_argument("--html", default="for_yandex.html", help="куда сохранить HTML для Яндекса")
    parser.add_argument("--parse", help="переведённый HTML от Яндекса чтобы распарсить обратно")
    parser.add_argument("--output", default="from_yandex.json")
    parser.add_argument("--use-underscores", action="store_true", help="использовать __PH_US__ вместо <span translate=no>")
    args=parser.parse_args()

    if args.parse:
        html_to_json(args.parse, args.output, args.input, use_underscores=args.use_underscores)
    else:
        json_to_html(args.input, args.html, use_underscores=args.use_underscores)

if __name__=="__main__":
    main()
