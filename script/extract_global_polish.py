#!/usr/bin/env python3
"""Extract every human-facing text field from complete/ for global polishing.

The source JSON files are never modified. Output mirrors the complete tree and
uses the source filename plus .txt; oversized files are split into 700-entry
chunks. Each line is addressable by file and JSON path.
"""
from __future__ import annotations
import json,re,csv
from pathlib import Path

ROOT=Path('/home/user/wspace'); SOURCE=ROOT/'complete'; OUT=ROOT/'work/global_polish'; CHUNK=700
TOKEN=re.compile(r'\[[^\[\]\r\n]{1,160}\]'); CYR=re.compile('[А-Яа-яЁё]'); LETTER=re.compile('[A-Za-zА-Яа-яЁё]')
VALID=set('"\\/bfnrtu')
# Human-facing fields encountered in the game data. Technical str* fields are
# intentionally excluded (IDs, asset paths, animation names, condition keys).
TEXT_FIELDS={
 'strTitle','strDesc','strTooltip','strNameFriendly','strNameShort',
 'strFriendlyName','strFriendlyDescription','strDescription',
 'strRequirementDescription','strMainText','strArticleBody','strArticleTitle','strBody',
 'strSubtitle','strDisplayName','strDisplayDesc','strDisplayDescComplete',
 'strMessage','strMessageShort','strText','strLabel','strNameDisplay',
 'strNodeLabel','strShort','strNameDesc','strDisplayBonus',
 'FriendlyName',
}
LIST_TEXT_FIELDS={'aValues','aPhaseTitles','aDescriptions','aMessages'}
EXCLUDE_FILES={'tokens/verbs.json','tokens/grammar.json','tokens/aliases.json'}

def clean(s):
 out=[];ins=False;esc=False;i=0
 while i<len(s):
  c=s[i]
  if ins:
   if esc:
    if c not in VALID:out.append('\\')
    out.append(c);esc=False;i+=1;continue
   if c=='\\':out.append(c);esc=True;i+=1;continue
   if ord(c)<32:out.append({'\n':'\\n','\r':'\\r','\t':'\\t','\b':'\\b','\f':'\\f'}.get(c,f'\\u{ord(c):04x}'));i+=1;continue
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
def load(p):return json.loads(clean(p.read_text(encoding='utf-8-sig')))
def keep(v):
 return isinstance(v,str) and len(v.strip())>=2 and bool(LETTER.search(v))
def label(path,name,field):
 if name:return f'strName={name} | {field}'
 return f'path={".".join(map(str,path))} | {field}'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 for p in list(OUT.rglob('*')):
  if p.is_file():p.unlink()
 rows_by_file={}; manifest=[]
 for p in sorted(SOURCE.rglob('*.json')):
  rel=p.relative_to(SOURCE); rels=rel.as_posix()
  if rels in EXCLUDE_FILES:continue
  try:data=load(p)
  except Exception as e:
   print('SKIP',rels,e);continue
  rows=[]; occurrence=0
  def add(path,name,field,value):
   nonlocal occurrence
   if not keep(value):return
   rows.append((path,name,field,value));occurrence+=1
  def walk(x,path=(),in_name=''):
   if isinstance(x,dict):
    name=x.get('strName',in_name)
    for k,v in x.items():
     if k in TEXT_FIELDS and isinstance(v,str):add(path+(k,),name,k,v)
     elif k in LIST_TEXT_FIELDS and isinstance(v,list):
      for i,item in enumerate(v):
       if isinstance(item,str):add(path+(k,i),name,f'{k}[{i}]',item)
     elif isinstance(v,(dict,list)):walk(v,path+(k,),name)
   elif isinstance(x,list):
    for i,item in enumerate(x):walk(item,path+(i,),in_name)
  walk(data)
  rows_by_file[rels]=rows
  for path,name,field,value in rows:
   manifest.append((rels,'.'.join(map(str,path)),name or '',field,value))
 # Write mirrored text files; >700 records get numbered chunks.
 output_files=0;total=0
 for rel,rows in rows_by_file.items():
  if not rows:continue
  target_base=OUT/rel
  target_base.parent.mkdir(parents=True,exist_ok=True)
  parts=[rows[i:i+CHUNK] for i in range(0,len(rows),CHUNK)]
  for idx,part in enumerate(parts,1):
   if len(parts)==1: out=Path(str(target_base)+'.txt')
   else: out=Path(str(target_base)+f'.{idx:03d}.txt')
   with out.open('w',encoding='utf8') as f:
    for path,name,field,value in part:
     f.write(f'### {rel} | {label(path,name,field)}\n')
     f.write(value.replace('\r\n','\n')+'\n---\n')
   output_files+=1;total+=len(part)
 # Manifest for exact later application.
 with (OUT/'manifest.tsv').open('w',encoding='utf8',newline='') as f:
  w=csv.writer(f,delimiter='\t');w.writerow(['file','json_path','strName','field','text'])
  w.writerows(manifest)
 print('source_files',len(rows_by_file),'output_text_files',output_files,'text_entries',total,'chunk_size',CHUNK)
 print('manifest',OUT/'manifest.tsv')
if __name__=='__main__':main()
