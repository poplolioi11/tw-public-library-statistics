#!/usr/bin/env python3
"""Read the maintainer-reviewed extraction inventory, never downloaded instructions."""
import json,re
from pathlib import PurePosixPath
NAME='reviewed_historical_cohorts.json'
def load(root):
 path=root/'data'/NAME
 if not path.exists():return None
 document=json.loads(path.read_text())
 if document['schema_version']!='1.0.0':raise ValueError('Unknown cohort inventory schema')
 result=[];keys=set();outputs=set()
 for group in document['cohorts']:
  if group['review_status']!='source_reviewed':continue
  if not re.fullmatch(r'[a-z0-9_]+',group['id']) or group['id'] in keys:raise ValueError('Invalid or duplicate cohort ID')
  if not re.fullmatch(r'[a-zA-Z0-9_]+\.py',group['script']):raise ValueError('Extractor must be a named local Python script')
  keys.add(group['id'])
  for field in ('inputs','outputs','raw_directories'):
   for name in group.get(field,[]):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] not in {'raw','derived'}:raise ValueError('Cohort paths must remain in raw/ or derived/')
  for name in group.get('dependencies',[]):
   p=PurePosixPath(name)
   if p.is_absolute() or '..' in p.parts or p.parts[0]!='scripts' or p.suffix not in {'.py','.json'}:raise ValueError('Dependencies must be local scripts or reviewed table specifications')
  if group['derived_csv'] not in group['outputs'] or not group['derived_csv'].endswith('.csv'):raise ValueError('Reviewed CSV must be an explicit output')
  if outputs.intersection(group['outputs']):raise ValueError('Cohorts may not overwrite each other')
  outputs.update(group['outputs']);result.append(group)
 return result
def csv_names(root,fallback):
 groups=load(root)
 return list(fallback) if groups is None else [g['derived_csv'].removeprefix('derived/') for g in groups]
