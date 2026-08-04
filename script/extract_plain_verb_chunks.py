#!/usr/bin/env python3
"""Prepare agent chunks for plain Russian verbs that are not in brackets."""
from __future__ import annotations
import collections, json, re
from pathlib import Path
ROOT=Path('/home/user/wspace'); COMPLETE=ROOT/'complete'; OUT=ROOT/'work/plain_verb_chunks'
TOKEN=re.compile(r'\[[^\[\]\r\n]{1,120}\]'); WORD=re.compile(r'[А-Яа-яЁё-]+'); CYR=re.compile('[А-Яа-яЁё]')
FIELDS={'strTitle','strDesc','strNameFriendly','strTooltip','strDescription','strRequirementDescription','strFriendlyDescription','strMainText'}
CHUNK=607
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
def main():
 vc=load(ROOT/'work/BepInExPlugin/verb_conjugations.json')['verbs']
 forms={x.casefold() for e in vc for x in e.get('forms',[]) if x and CYR.search(x) and len(x)>=3}
 rows=[]
 for p in sorted(COMPLETE.rglob('*.json')):
  if p.name in {'verbs.json','grammar.json'}:continue
  try:d=load(p)
  except:continue
  rel=str(p.relative_to(COMPLETE))
  def rec(x, inherited_name=''):
   if isinstance(x,dict):
    name=x.get('strName',inherited_name)
    for k,v in x.items():
     if k in FIELDS and isinstance(v,str):
      matches=[];parts=[];last=0
      for m in TOKEN.finditer(v):parts.extend([v[last:m.start()],' '*(m.end()-m.start())]);last=m.end()
      parts.append(v[last:]);plain=''.join(parts)
      for word in WORD.findall(plain):
       if word.casefold() in forms:matches.append(word)
      if matches and name and re.search(r'\[(?:us|them|3rd)(?:-[^\]]+)?\]',v):
       rows.append((rel,name,k,v,sorted(set(matches))))
     elif isinstance(v,(dict,list)):rec(v,name)
   elif isinstance(x,list):
    for y in x:rec(y,inherited_name)
  rec(d)
 # dedup by file/name/field; report all matching words once
 uniq=[];seen=set()
 for r in rows:
  key=r[:3]
  if key not in seen:seen.add(key);uniq.append(r)
 uniq.sort(key=lambda r:(r[0],r[1],r[2]))
 OUT.mkdir(parents=True,exist_ok=True)
 for p in OUT.glob('*'):p.unlink()
 chunks=[uniq[i:i+CHUNK] for i in range(0,len(uniq),CHUNK)]
 for idx,chunk in enumerate(chunks,1):
  txt=OUT/f'plain_verb_chunk_{idx:03d}.txt'; ctx=OUT/f'plain_verb_chunk_{idx:03d}.context.tsv'
  with txt.open('w',encoding='utf8') as f,ctx.open('w',encoding='utf8') as c:
   c.write('file\tstrName\tfield\tplain_forms\ttext\n')
   for rel,name,field,text,words in chunk:
    f.write(f'### {rel} | {name} | {field}\n{text}\n---\n')
    c.write('\t'.join([rel,name,field,', '.join(words),text.replace('\t',' ').replace('\n','\\n')])+'\n')
  print(txt.name,len(chunk))
 print('total',len(uniq),'chunks',len(chunks),'chunk_size',CHUNK)
if __name__=='__main__':main()
