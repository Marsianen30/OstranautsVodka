#!/usr/bin/env python3
"""Validate/apply polish chunks and add their verb aliases."""
from __future__ import annotations
import collections,json,re,shutil
from pathlib import Path
ROOT=Path('/home/user/wspace'); COMPLETE=ROOT/'complete'; UP=Path('/home/user/uploads')
BASE=ROOT/'work/polish_chunks'; BACK=ROOT/'work/polish_backup'
PLUGIN=ROOT/'work/BepInExPlugin/verb_conjugations.json'; DEPLOY=ROOT/'work/verb_conjugations.json'
HEADER=re.compile(r'^### (.+?) \| (.+?) \| (\S+)$'); TOKEN=re.compile(r'\[[^\[\]\r\n]{1,120}\]'); RUS=re.compile('[А-Яа-яЁё]')
NEW_FORMS={
 'patches':['заделываю','заделываешь','заделывает','заделываем','заделываете','заделывают'],
 'toggles':['переключаю','переключаешь','переключает','переключаем','переключаете','переключают'],
 'reconfigures':['перенастраиваю','перенастраиваешь','перенастраивает','перенастраиваем','перенастраиваете','перенастраивают'],
}
FIX_FORMS={
 'extinguishes':['тушу','тушишь','тушит','тушим','тушите','тушат'],
 'scraps':['разбираю','разбираешь','разбирает','разбираем','разбираете','разбирают'],
}
NEW_RUS_FORMS={
 'готовится':['готовлюсь','готовишься','готовится','готовимся','готовитесь','готовятся'],
 'обсуждает':['обсуждаю','обсуждаешь','обсуждает','обсуждаем','обсуждаете','обсуждают'],
 # These are past/participle placeholders requested for this chunk. They are
 # fixed stubs until a dedicated past/adjective inflection layer exists.
 'выучил':['выучил','выучил','выучил','выучил','выучил','выучил'],
 'удалён':['удалён','удалён','удалён','удалён','удалён','удалён'],
}
def parse(p):
 lines=p.read_text('utf8').splitlines();rows=[];i=0
 while i<len(lines):
  if not lines[i].strip():i+=1;continue
  m=HEADER.match(lines[i])
  if not m:raise RuntimeError(f'bad header {p}:{i+1}')
  rel,name,field=m.groups();i+=1;buf=[]
  while i<len(lines) and lines[i]!='---':buf.append(lines[i]);i+=1
  if i>=len(lines):raise RuntimeError(f'missing sep {p}:{name}')
  i+=1;rows.append((rel,name,field,'\n'.join(buf).strip()))
 return rows
def walk(v):
 if isinstance(v,dict):
  n=v.get('strName')
  for k,x in v.items():
   if isinstance(x,str):yield v,n,k,x
   elif isinstance(x,(dict,list)):yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
def main():
 base={}
 source_chunk=BASE/'polish_chunk_003.txt'
 if not source_chunk.exists():raise RuntimeError('polish_chunk_003.txt is missing')
 for r in parse(source_chunk):base[r[:3]]=r[3]
 rows=parse(UP/'polish_chunk_003_ru.txt')
 keys={r[:3] for r in rows}
 if len(rows)!=len(base) or len(keys)!=len(base) or keys!=set(base):raise RuntimeError('polish chunk metadata mismatch')
 added=collections.Counter();removed=collections.Counter()
 for r in rows:
  for t,n in (collections.Counter(TOKEN.findall(r[3]))-collections.Counter(TOKEN.findall(base[r[:3]]))).items():added[t]+=n
  for t,n in (collections.Counter(TOKEN.findall(base[r[:3]]))-collections.Counter(TOKEN.findall(r[3]))).items():removed[t]+=n
 current=json.loads(PLUGIN.read_text('utf8')); entries=current['verbs']; by={str(x['infinitive']).casefold():x for x in entries}
 # All added English verbs must have an alias; all added Russian forms must be
 # existing/known aliases from the previous pass.
 new_eng={t[1:-1] for t in added if not RUS.search(t) and not (t[1:-1] in {'us','them','3rd'} or t[1:-1].startswith(('us-','them-','3rd-','racing_icon-','they-')))}
 new_rus={t[1:-1] for t in added if RUS.search(t)}
 missing_rus=[x for x in new_rus if x.casefold() not in by]
 unknown_rus=[x for x in missing_rus if x not in NEW_RUS_FORMS]
 if unknown_rus:raise RuntimeError(f'new Russian keys need forms: {sorted(unknown_rus)}')
 missing_eng=[x for x in new_eng if x.casefold() not in by]
 unknown=[x for x in missing_eng if x not in NEW_FORMS]
 if unknown:raise RuntimeError(f'new English verbs need forms: {sorted(unknown)}')
 for key,forms in {**NEW_FORMS,**FIX_FORMS,**NEW_RUS_FORMS}.items():
  if key.casefold() in by:
   by[key.casefold()]['forms']=forms
  else:
   entries.append({'infinitive':key,'forms':forms});by[key.casefold()]=entries[-1]
 # Backup/apply exact file+strName+field.
 BACK.mkdir(parents=True,exist_ok=True); grouped=collections.defaultdict(list)
 for r in rows:grouped[r[0]].append(r)
 applied=0
 for rel,changes in grouped.items():
  p=COMPLETE/rel;data=json.loads(p.read_text('utf8'));shutil.copy2(p,BACK/rel.replace('/','__'))
  for _,name,field,text in changes:
   matches=[(o,old) for o,on,of,old in walk(data) if on==name and of==field]
   if not matches: raise RuntimeError(f'{rel}|{name}|{field} matches=0')
   if len({old for _,old in matches}) > 1:
    raise RuntimeError(f'{rel}|{name}|{field} has conflicting duplicate records')
   for obj,_ in matches:
    obj[field]=text; applied+=1
  p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 current['_comment']='Russian 6-form conjugations; English and Russian verb aliases are retained. Forms: [1sg, 2sg, 3sg, 1pl, 2pl, 3pl].'
 encoded=json.dumps(current,ensure_ascii=False,indent=2)+'\n';PLUGIN.write_text(encoded,encoding='utf8');DEPLOY.write_text(encoded,encoding='utf8')
 print(json.dumps({'rows':len(rows),'added_placeholders':dict(added),'removed_placeholders':dict(removed),'new_english_keys':sorted(missing_eng),'fixed_forms':sorted(FIX_FORMS),'applied':applied,'verb_entries':len(entries),'backup':str(BACK)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
