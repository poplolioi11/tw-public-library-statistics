#!/usr/bin/env python3
"""Replay NLPI statistical snapshot fields, preserving current-definition limits."""
import hashlib,json
from collections import defaultdict
from pathlib import Path
import record_io
ROOT=Path(__file__).resolve().parents[1]
def sha(x):return hashlib.sha256(x).hexdigest()
def stable(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def write(path,obj):
 body=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
 if not path.exists() or path.read_bytes()!=body:path.write_bytes(body)
def pointer(obj,path):
 for part in path.split('/')[1:]:
  part=part.replace('~1','/').replace('~0','~');obj=obj[int(part)] if isinstance(obj,list) else obj[part]
 return obj
def main():
 groups=defaultdict(list)
 for r in record_io.rows(ROOT,'data/combined/observations.jsonl'):
  if r['source_family'] in ('國資圖公開全國圖表','國資圖2023開放資料（含縣市）'):groups[(r['source_id'],r['source_sha256'])].append(r)
 cards=[];checks=0
 for (sid,digest),rows in sorted(groups.items()):
  first=rows[0];path=ROOT/first['source_snapshot_path'];body=path.read_bytes()
  if sha(body)!=digest:raise ValueError('Reviewed official statistical source changed: '+sid)
  original=json.loads(body)
  for r in rows:
   if pointer(original,r['source_locator'])!=r['raw_value']:raise ValueError('Original statistical JSON field differs: '+r['observation_id'])
   checks+=1
  cards.append({'evidence_id':'phase2-nlpi-'+sid,'layer':'canonical','source_id':sid,'source_sha256':digest,'source_url':first['source_url'],'source_locator':{'kind':'original_JSON_pointer','pointers':sorted({r['source_locator'] for r in rows})},'source_table':None,'source_table_title':first['indicator_group'],'source_fields':sorted({r['source_field'] for r in rows}),'data_years_present':sorted({r['data_year'] for r in rows}),'observation_ids':sorted(r['observation_id'] for r in rows),'reviewed_original':True,'semantic_facts':{'statistics':'Every assigned original JSON field/raw value replayed against the recorded official snapshot SHA.','source_series':'A displayed year series is not independent proof of invariant historical definitions.','current_reference':'raw/phase2-definitions/current-reference-sources.json','current_definition_sha256':first.get('definition_sha256'),'effective_dates':'No retrospective adoption date inferred.','national_library_scope':'Default/alternative county rows and national total remain original scopes; no cross-family splice.','measures':'Printed fields, indicator group and unit retained; current definitions only a separate reference.'},'original_notes_short':sorted({r['notes'] for r in rows if r.get('notes')}),'supported_comparison_scope':{'status':'source_series_only','scope':'Original labelled source series only; no certified historical-method or cross-source equivalence.','historical_effective_dates_confirmed':False},'unresolved':['Historical definition effect dates and reporting completeness not documented for every year.','Source-returned zero is not proof of measured zero.','Current electronic-resource and staff terms do not automatically replace older labels.'],'review_method':'Local Python replay of every original statistical JSON pointer and raw value; current-reference definition audit remains distinct from historical applicability.'})
 payload={'schema_version':'1.0.0','scope':'All existing NLPI chart and licensed2023 statistical observations; no new annual API requested.','status':'pass','original_field_checks':checks,'source_cards':cards,'script_sha256':sha(Path(__file__).read_bytes()),'current_reference_manifest_sha256':sha((ROOT/'raw/phase2-definitions/current-reference-sources.json').read_bytes())}
 write(ROOT/'research/phase2-nlpi-evidence.json',payload)
 print(json.dumps({'status':'pass','cards':len(cards),'original_fields_checked':checks,'historical_comparability_certified':False}))
if __name__=='__main__':main()
