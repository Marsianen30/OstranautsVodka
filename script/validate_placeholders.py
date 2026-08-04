from pathlib import Path
import json,re,collections
ROOT=Path('/home/user/wspace'); C=ROOT/'complete'; O=ROOT/'original'
PAT=re.compile(r'\[[^\[\]\r\n]{1,120}\]'); RUS=re.compile('[А-Яа-яЁё]')
VALID=set('"\\/bfnrtu')
def clean(s):
 out=[];ins=False;esc=False;i=0
 while i<len(s):
  c=s[i]
  if ins:
   if esc:
    if c not in VALID:out.append('\\')
    out.append(c);esc=False;i+=1;continue
   if c=='\\':out.append(c);esc=True;i+=1;continue
   if ord(c)<32:out.append({'\n':'\\n','\r':'\\r','\t':'\\t','\b':'\\b','\f':'\\f'}.get(c,'\\u%04x'%ord(c)));i+=1;continue
   out.append(c)
   if c=='"':ins=False
   i+=1
  else:
   if c=='"':ins=True
   if c=='/' and i+1<len(s) and s[i+1]=='/':
    i+=2
    while i<len(s) and s[i] not in '\r\n':i+=1
    continue
   out.append(c);i+=1
 return ''.join(out)
def load(p):return json.loads(clean(p.read_text('utf-8-sig')))
def collect(root):
 c=collections.Counter(); by=collections.defaultdict(collections.Counter)
 for p in root.rglob('*.json'):
  try:d=load(p)
  except Exception:continue
  def rec(x):
   if isinstance(x,str):
    for t in PAT.findall(x):c[t]+=1;by[t][str(p.relative_to(root))]+=1
   elif isinstance(x,list):
    for y in x:rec(y)
   elif isinstance(x,dict):
    for y in x.values():rec(y)
  rec(d)
 return c,by
c,by=collect(C);o,_=collect(O)
with (ROOT/'work/placeholder_inventory_after.tsv').open('w',encoding='utf8') as f:
 f.write('count\tplaceholder\tfiles\n')
 for t,n in sorted(c.items(),key=lambda z:(-z[1],z[0])):
  f.write(f'{n}\t{t}\t{len(by[t])}\n')
with (ROOT/'work/placeholder_inventory_after.md').open('w',encoding='utf8') as f:
 f.write('# Финальный инвентарь плейсхолдеров complete\n\n')
 f.write(f'- Всего в JSON-значениях: **{sum(c.values())}** вхождений\n')
 f.write(f'- Уникальных: **{len(c)}**\n')
 f.write(f'- Русских осталось: **{sum(n for t,n in c.items() if RUS.search(t))}** вхождений, **{len([t for t in c if RUS.search(t)])}** уникальных\n')
 f.write(f'- Английских/прочих: **{sum(n for t,n in c.items() if not RUS.search(t))}** вхождений, **{len([t for t in c if not RUS.search(t)])}** уникальных\n\n')
 f.write('| Количество | Плейсхолдер | Файлов |\n|---:|---|---:|\n')
 for t,n in sorted(c.items(),key=lambda z:(-z[1],z[0])):f.write(f'| {n} | `{t}` | {len(by[t])} |\n')
 f.write('\n## Сопоставление с original\n')
 f.write(f'- Плейсхолдеров, встречающихся в original JSON-значениях: {len(o)} уникальных.\n')
 extra=sorted(set(c)-set(o)); missing=sorted(set(o)-set(c))
 f.write(f'- Есть только в complete: {len(extra)} уникальных.\n')
 if extra:f.write('  - '+', '.join(f'`{x}`' for x in extra)+'\n')
 f.write(f'- Есть только в original: {len(missing)} уникальных (это не ошибка: часть оригинальных строк отсутствует в предрелизном complete).\n')
 f.write(f'  - '+', '.join(f'`{x}`' for x in missing)+'\n')
print('actual complete JSON-value placeholders',sum(c.values()),len(c))
print('russian',sum(n for t,n in c.items() if RUS.search(t)),len([t for t in c if RUS.search(t)]))
print('extra vs original',len(set(c)-set(o)))
print('remaining russian',[(t,n) for t,n in c.items() if RUS.search(t)])
