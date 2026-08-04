#!/usr/bin/env python3
"""Apply only unambiguous second-pass polish fixes reported during testing."""
from pathlib import Path
import json, shutil
ROOT=Path('/home/user/wspace'); C=ROOT/'complete'; BACK=ROOT/'work/easy_polish_backup'; BACK.mkdir(parents=True,exist_ok=True)
# Exact, context-safe replacements.
REPL={
 'conditions/conditions.json': {
  'У [us] временно усилена иммунная система.':'У [us-obj] временно усилена иммунная система.',
  'Температура воздуха вокруг [us]':'Температура воздуха вокруг [us-obj]',
  '[us] спит.':'[us] [спит].',
  '[us] спит в удобной кровати.':'[us] [спит] в удобной кровати.',
  '[us] тепло.':'У [us-obj] комфортная температура тела.',
 },
 'conditions_simple/conditions_simple.json': {
  '[us] [is] герметичен.':'[us] герметичен.',
 },
 'interactions/interactions.json': {
  '[us] [shows] [us-pos] доступные товары для [them].':'[us] [shows] [them-obj] доступные товары.',
  '[us] [shows] [us-pos] товары черного рынка [them].':'[us] [shows] [them-obj] товары чёрного рынка.',
  '[us] [shows] [us-pos] товары черного рынка для [them].':'[us] [shows] [them-obj] товары чёрного рынка.',
  '[us] [shows] [us-pos] товары чёрного рынка [them].':'[us] [shows] [them-obj] товары чёрного рынка.',
 },
 'interactions/interactions_modeswitch.json': {
  '[us] ОТКРЫВАЕТ.':'[us] ОТКРЫТ.',
 },
}
changes={}
for rel,repls in REPL.items():
 p=C/rel;s=p.read_text('utf8');shutil.copy2(p,BACK/rel.replace('/','__'));n=0
 for old,new in repls.items():
  k=s.count(old)
  if k:n+=k;s=s.replace(old,new)
 if n:p.write_text(s,encoding='utf8')
 changes[rel]=n
# Add the missing present-tense verb [спит] to the external DLL table.
forms=['сплю','спишь','спит','спим','спите','спят']
for p in [ROOT/'work/BepInExPlugin/verb_conjugations.json',ROOT/'work/verb_conjugations.json']:
 d=json.loads(p.read_text('utf8')); keys={x['infinitive'].casefold() for x in d['verbs']}
 if 'спит' not in keys:d['verbs'].append({'infinitive':'спит','forms':forms})
 d['_comment']='Russian 6-form conjugations; English and Russian verb aliases are retained. Forms: [1sg, 2sg, 3sg, 1pl, 2pl, 3pl].'
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(changes)
