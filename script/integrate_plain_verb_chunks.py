#!/usr/bin/env python3
"""Validate/apply plain-verb chunks and register their new Russian verbs."""
from __future__ import annotations
import collections,json,re,shutil
from pathlib import Path
ROOT=Path('/home/user/wspace'); COMPLETE=ROOT/'complete'; UP=Path('/home/user/uploads')
CHUNK_DIR=ROOT/'work/plain_verb_chunks'; BACKUP=ROOT/'work/plain_verb_backup'
PLUGIN=ROOT/'work/BepInExPlugin/verb_conjugations.json'; DEPLOY=ROOT/'work/verb_conjugations.json'
HEADER=re.compile(r'^### (.+?) \| (.+?) \| (\S+)$'); TOKEN=re.compile(r'\[[^\[\]\r\n]{1,120}\]'); RUS=re.compile('[А-Яа-яЁё]')
# Six forms in [1sg, 2sg, 3sg, 1pl, 2pl, 3pl] order.
FORMS={
'агонизирует':['агонизирую','агонизируешь','агонизирует','агонизируем','агонизируете','агонизируют'],
'взрывается':['взрываюсь','взрываешься','взрывается','взрываемся','взрываетесь','взрываются'],
'восстанавливается':['восстанавливаюсь','восстанавливаешься','восстанавливается','восстанавливаемся','восстанавливаетесь','восстанавливаются'],
'восхваляет':['восхваляю','восхваляешь','восхваляет','восхваляем','восхваляете','восхваляют'],
'выражает':['выражаю','выражаешь','выражает','выражаем','выражаете','выражают'],
'держится':['держусь','держишься','держится','держимся','держитесь','держатся'],
'жалуется':['жалуюсь','жалуешься','жалуется','жалуемся','жалуетесь','жалуются'],
'живёт':['живу','живёшь','живёт','живём','живёте','живут'],
'забывает':['забываю','забываешь','забывает','забываем','забываете','забывают'],
'завершает':['завершаю','завершаешь','завершает','завершаем','завершаете','завершают'],
'заглядывает':['заглядываю','заглядываешь','заглядывает','заглядываем','заглядываете','заглядывают'],
'задыхается':['задыхаюсь','задыхаешься','задыхается','задыхаемся','задыхаетесь','задыхаются'],
'испытывает':['испытываю','испытываешь','испытывает','испытываем','испытываете','испытывают'],
'могут':['могу','можешь','может','можем','можете','могут'],
'наслаждается':['наслаждаюсь','наслаждаешься','наслаждается','наслаждаемся','наслаждаетесь','наслаждаются'],
'находит':['нахожу','находишь','находит','находим','находите','находят'],
'несёт':['несу','несёшь','несёт','несём','несёте','несут'],
'опознаёт':['опознаю','опознаёшь','опознаёт','опознаём','опознаёте','опознают'],
'определяет':['определяю','определяешь','определяет','определяем','определяете','определяют'],
'отключает':['отключаю','отключаешь','отключает','отключаем','отключаете','отключают'],
'отстаивает':['отстаиваю','отстаиваешь','отстаивает','отстаиваем','отстаиваете','отстаивают'],
'отшатывается':['отшатываюсь','отшатываешься','отшатывается','отшатываемся','отшатываетесь','отшатываются'],
'подключает':['подключаю','подключаешь','подключает','подключаем','подключаете','подключают'],
'приближается':['приближаюсь','приближаешься','приближается','приближаемся','приближаетесь','приближаются'],
'приходит':['прихожу','приходишь','приходит','приходим','приходите','приходят'],
'просыпается':['просыпаюсь','просыпаешься','просыпается','просыпаемся','просыпаетесь','просыпаются'],
'пытается':['пытаюсь','пытаешься','пытается','пытаемся','пытаетесь','пытаются'],
'расслабляется':['расслабляюсь','расслабляешься','расслабляется','расслабляемся','расслабляетесь','расслабляются'],
'скорбит':['скорблю','скорбишь','скорбит','скорбим','скорбите','скорбят'],
'скрывает':['скрываю','скрываешь','скрывает','скрываем','скрываете','скрывают'],
'соглашается':['соглашаюсь','соглашаешься','соглашается','соглашаемся','соглашаетесь','соглашаются'],
'сокрушается':['сокрушаюсь','сокрушаешься','сокрушается','сокрушаемся','сокрушаетесь','сокрушаются'],
'соображает':['соображаю','соображаешь','соображает','соображаем','соображаете','соображают'],
'сообщает':['сообщаю','сообщаешь','сообщает','сообщаем','сообщаете','сообщают'],
'сопротивляется':['сопротивляюсь','сопротивляешься','сопротивляется','сопротивляемся','сопротивляетесь','сопротивляются'],
'справляется':['справляюсь','справляешься','справляется','справляемся','справляетесь','справляются'],
'страдает':['страдаю','страдаешь','страдает','страдаем','страдаете','страдают'],
'съеживается':['съеживаюсь','съеживаешься','съеживается','съеживаемся','съеживаетесь','съеживаются'],
'умоляет':['умоляю','умоляешь','умоляет','умоляем','умоляете','умоляют'],
'учится':['учусь','учишься','учится','учимся','учитесь','учатся'],
'является':['являюсь','являешься','является','являемся','являетесь','являются'],
}

def parse(p):
 lines=p.read_text('utf8').splitlines(); rows=[];i=0
 while i<len(lines):
  if not lines[i].strip():i+=1;continue
  m=HEADER.match(lines[i])
  if not m:raise RuntimeError(f'bad header {p}:{i+1}')
  rel,name,field=m.groups();i+=1;buf=[]
  while i<len(lines) and lines[i]!='---':buf.append(lines[i]);i+=1
  if i>=len(lines):raise RuntimeError(f'missing separator {p}:{name}')
  i+=1;rows.append((rel,name,field,'\n'.join(buf).strip()))
 return rows

def walk(v):
 if isinstance(v,dict):
  name=v.get('strName')
  for k,x in v.items():
   if isinstance(x,str):yield v,name,k,x
   elif isinstance(x,(dict,list)):yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)

def main():
 base={}
 for p in sorted(CHUNK_DIR.glob('plain_verb_chunk_*.txt')):
  for r in parse(p):base[r[:3]]=r[3]
 rows=[]
 for p in sorted(UP.glob('plain_verb_chunk_*_ru.txt')):rows+=parse(p)
 keys={r[:3] for r in rows}
 if len(rows)!=1213 or len(keys)!=1213 or len(base)!=1213 or keys!=set(base):raise RuntimeError('chunk metadata mismatch')
 # Find newly introduced Russian bracket keys.
 added=collections.Counter()
 for r in rows:
  for t,n in (collections.Counter(TOKEN.findall(r[3]))-collections.Counter(TOKEN.findall(base[r[:3]]))).items():
   if RUS.search(t):added[t[1:-1]]+=n
 current=json.loads(PLUGIN.read_text('utf8'))
 current_keys={str(x['infinitive']).casefold() for x in current['verbs']}
 missing=sorted(k for k in added if k.casefold() not in current_keys)
 if set(missing)!=set(FORMS):raise RuntimeError(f'form map mismatch missing={missing} form_keys={sorted(FORMS)}')
 for k in missing:
  if len(FORMS[k])!=6:raise RuntimeError(k)
 # Backup target files and apply by exact strName+field.
 BACKUP.mkdir(parents=True,exist_ok=True); applied=0
 grouped=collections.defaultdict(list)
 for r in rows:grouped[r[0]].append(r)
 for rel,changes in grouped.items():
  path=COMPLETE/rel; data=json.loads(path.read_text('utf8'));shutil.copy2(path,BACKUP/rel.replace('/','__'))
  for _,name,field,text in changes:
   matches=[(o,old) for o,on,of,old in walk(data) if on==name and of==field]
   if len(matches)!=1:raise RuntimeError(f'{rel}|{name}|{field} matches={len(matches)}')
   matches[0][0][field]=text;applied+=1
  path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 # Append one alias entry for every missing Russian placeholder.
 for key in missing:
  current['verbs'].append({'infinitive':key,'forms':FORMS[key]})
 current['_comment']='Russian 6-form conjugations; includes English aliases and Russian verb aliases used by complete/. Forms: [1sg, 2sg, 3sg, 1pl, 2pl, 3pl].'
 encoded=json.dumps(current,ensure_ascii=False,indent=2)+'\n';PLUGIN.write_text(encoded,encoding='utf8');DEPLOY.write_text(encoded,encoding='utf8')
 # Save corrected chunks and report.
 for idx in (1,2):
  part=rows[(idx-1)*607:idx*607];out=CHUNK_DIR/f'plain_verb_chunk_{idx:03d}_corrected.txt'
  with out.open('w',encoding='utf8') as f:
   for rel,name,field,text in part:f.write(f'### {rel} | {name} | {field}\n{text}\n---\n')
 print(json.dumps({'rows':len(rows),'new_russian_verbs':len(missing),'new_keys':missing,'applied':applied,'verb_entries':len(current['verbs']),'backup':str(BACKUP)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
