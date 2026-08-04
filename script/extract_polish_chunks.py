#!/usr/bin/env python3
from pathlib import Path
import json,re
ROOT=Path('/home/user/wspace'); C=ROOT/'complete'; OUT=ROOT/'work/polish_chunks'; CHUNK=600
PAT=re.compile(r'(?:(?:У|у|вокруг|для) \[(?:us|them|3rd)\](?!-)|\[us\] \[starts\]|\[is\]|ОТКРЫВАЕТ|\[us-pos\]|\[them-pos\])')
FIELDS={'strTitle','strDesc','strTooltip','strNameFriendly','strDescription','strRequirementDescription','strFriendlyDescription','strMainText'}
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
   if ord(c)<32:out.append({'\n':'\\n','\r':'\\r','\t':'\\t'}.get(c,f'\\u{ord(c):04x}'));i+=1;continue
   out.append(c)
   if c=='"':ins=False
   i+=1
  else:
   if c=='"':ins=True;out.append(c);i+=1
   elif c=='/' and i+1<len(s) and s[i+1]=='/':
    i+=2
    while i<len(s) and s[i] not in '\r\n':i+=1
   else:out.append(c);i+=1
 return ''.join(out)
def load(p):return json.loads(clean(p.read_text('utf-8-sig')))
def parse_keys(path):
 keys=set()
 try: lines=path.read_text(encoding='utf8').splitlines()
 except: return keys
 for line in lines:
  m=re.match(r'^### (.+?) \| (.+?) \| (\S+)$',line)
  if m: keys.add(m.groups())
 return keys
def main():
 rows=[]
 for p in sorted(C.rglob('*.json')):
  if p.name in {'verbs.json','grammar.json'}:continue
  try:d=load(p)
  except:continue
  def rec(x):
   if isinstance(x,dict):
    name=x.get('strName','')
    for k,v in x.items():
     if k in FIELDS and isinstance(v,str) and name and PAT.search(v):rows.append((str(p.relative_to(C)),name,k,v))
     elif isinstance(v,(dict,list)):rec(v)
   elif isinstance(x,list):
    for y in x:rec(y)
  rec(d)
 uniq=[];seen=set()
 for r in rows:
  if r[:3] not in seen:seen.add(r[:3]);uniq.append(r)
 uniq.sort(key=lambda r:(r[0],r[1],r[2]));OUT.mkdir(exist_ok=True)
 processed=set()
 for old in OUT.glob('polish_chunk_*.txt'):
  processed |= parse_keys(old)
 for old in Path('/home/user/uploads').glob('polish_chunk_*_ru.txt'):
  processed |= parse_keys(old)
 allkeys={r[:3] for r in uniq}
 # A previously processed record can reappear when the old agent left a
 # remaining case (for example a still-unresolved -pos form). Such records
 # are intentionally exported again under the next chunk number.
 remaining=[r for r in uniq if r[:3] not in processed or PAT.search(r[3])]
 numbers=[]
 for old in OUT.glob('polish_chunk_*.txt'):
  m=re.match(r'polish_chunk_(\d+)\.txt$',old.name)
  if m:numbers.append(int(m.group(1)))
 next_index=max(numbers,default=0)+1
 chunks=[remaining[i:i+CHUNK] for i in range(0,len(remaining),CHUNK)]
 for offset,ch in enumerate(chunks):
  p=OUT/f'polish_chunk_{next_index+offset:03d}.txt'
  with p.open('w',encoding='utf8') as f:
   for rel,n,field,text in ch:f.write(f'### {rel} | {n} | {field}\n{text}\n---\n')
  print(p.name,len(ch))
 print('all_candidates',len(uniq),'already_processed',len(processed & allkeys),'remaining_exported',len(remaining),'new_chunks',len(chunks),'start_index',next_index)
if __name__=='__main__':main()
