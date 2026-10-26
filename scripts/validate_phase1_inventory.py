#!/usr/bin/env python3
"""Validate phase-one source availability products, never certify comparability."""
import argparse,csv,hashlib,json,sqlite3,re
from collections import Counter
from pathlib import Path
import record_io
ROOT=Path(__file__).resolve().parents[1]
PUBLICATION_FIELDS={'snapshot_distribution','public_evidence_path','public_evidence_sha256','public_projection_policy'}
PROFILE_FIELDS=('source_id','source_family','series_id','data_year','geography','geographic_scope','geography_vintage','indicator','indicator_group','source_field','unit','unit_raw','unit_status','population_scope','national_libraries_scope','temporal_kind','period_basis','source_edition','source_edition_roc','aggregation_role','institutional_level')
def stable(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sqlval(x):return stable(x) if isinstance(x,(dict,list,bool)) else None if x is None else str(x)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--allow-incomplete-survey',action='store_true');a=p.parse_args();root=a.root.resolve();report=json.loads((root/'docs/phase1-summary.json').read_text());scope=json.loads((root/'scripts/phase1_scope.json').read_text());rows=list(record_io.rows(root,'data/combined/observations.jsonl'));by_id={r['observation_id']:r for r in rows};checks=0
 def require(x,why):
  nonlocal checks;checks+=1
  if not x:raise ValueError(why)
 require(report['dataset_version']==(root/'VERSION').read_text().strip(),'Phase-one version differs')
 projections=json.loads((root/'docs/metadata-field-projections.json').read_text()).get('files',[]) if (root/'docs/metadata-field-projections.json').exists() else []
 projection_by_path={x['path']:x for x in projections}
 for entry in report['inputs']:
  if entry['path']=='canonical_statistical_content':continue
  f=root/entry['path'];require(f.is_file(),'Recorded input missing: '+entry['path']);actual=hashlib.sha256(f.read_bytes()).hexdigest();projection=projection_by_path.get(entry['path'],{})
  require(actual==entry['sha256'] or entry['sha256']==projection.get('private_metadata_sha256') and actual==projection.get('public_metadata_sha256'),'Recorded input changed; rebuild phase1: '+entry['path'])
 digest=hashlib.sha256(stable([{k:v for k,v in r.items() if k not in PUBLICATION_FIELDS} for r in rows]).encode()).hexdigest();require(report['canonical_statistical_content_sha256']==digest,'Canonical statistical input changed')
 require(not report['all_history_complete'] and not report['cross_year_comparability_certified'],'Inventory must not certify all history or compatibility')
 datasets={}
 db=sqlite3.connect('file:'+str(root/'derived/phase1_inventory.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 for name in ('phase1_authority_checks','phase1_source_candidates','phase1_raw_source_profiles','phase1_discovery_matrix'):
  path=root/'derived'/(name+'.jsonl');data=[json.loads(x) for x in path.read_text().splitlines()];datasets[name]=data
  with (root/'derived'/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:csvrows=list(csv.DictReader(f))
  require(len(csvrows)==len(data),name+' CSV count differs');sqlrows=[dict(r) for r in db.execute('SELECT * FROM '+name)]
  require(len(sqlrows)==len(data),name+' SQLite count differs')
  for expected,csvrow,sqlrow in zip(data,csvrows,sqlrows,strict=True):
   expected_sql={k:sqlval(v) for k,v in expected.items()};require(all(csvrow[k]==('' if v is None else v) for k,v in expected_sql.items()),name+' CSV differs');require(all(sqlrow[k]==v for k,v in expected_sql.items()),name+' SQLite differs')
 db.close();authorities=datasets['phase1_authority_checks'];profiles=datasets['phase1_raw_source_profiles'];matrix=datasets['phase1_discovery_matrix']
 keys=[(r['county'],r['role']) for r in authorities];required={(c,r) for c in scope['current_county_navigation'] for r in scope['authority_roles']};require(len(keys)==len(set(keys)) and set(keys)==required,'Authority-role scope differs')
 if not a.allow_incomplete_survey:require(all(r.get('check_status') not in (None,'not_checked') and r.get('checked_url') and r.get('checked_at') for r in authorities),'Some authority roles still lack actual check evidence')
 seen=[];profile_ids=set()
 for p in profiles:
  require(p['profile_id'] not in profile_ids,'Duplicate source profile');profile_ids.add(p['profile_id']);items=[]
  for oid in p['observation_ids']:
   require(oid in by_id,'Unknown observation ID');r=by_id[oid];items.append(r);seen.append(oid)
   for field in PROFILE_FIELDS:require(p[field]==r.get(field),'Source profile merged distinct '+field)
  require(p['observation_count']==len(items),'Profile count differs');require(p['nonmissing_value_records']==sum(r['value'] is not None for r in items),'Missing values became numbers');require(p['null_status_counts']==dict(sorted(Counter(r['value_status'] for r in items if r['value'] is None).items())),'Missing marker classes changed')
 require(len(seen)==len(set(seen))==len(rows) and set(seen)==set(by_id),'Profiles do not exactly partition canonical IDs')
 matrix_keys=[(r['data_year'],r['navigation_region_current_name'],r['topic_id']) for r in matrix];expected={(y,c,t['id']) for y in range(scope['years']['first'],scope['years']['last']+1) for c in ['全國',*scope['current_county_navigation']] for t in scope['topics']};require(len(matrix_keys)==len(set(matrix_keys)) and set(matrix_keys)==expected,'Discovery grid drops scope slots')
 by_profile={p['profile_id']:p for p in profiles}
 for cell in matrix:
  ps=[by_profile[x] for x in cell['profile_ids']];require(all(p['data_year']==cell['data_year'] and p['geography']==cell['navigation_region_current_name'] for p in ps),'Historical geography silently recoded')
  require(not any(p['quantity_role'] in ('ratio_or_per_capita_not_original_quantity','population_context') for p in ps),'Ratio or population filled an original-quantity slot')
  require(sum(p['observation_count'] for p in ps)==cell['matched_source_observations'],'Discovery cell count differs');require(all(p['compatibility_status']=='not_certified_by_phase1_inventory' for p in ps),'Discovery cell silently certified compatibility')
 require('不由比率反算' in (root/'docs/PHASE1.md').read_text(),'2012 gap safeguard missing')
 reader=root/'site/phase1.html'
 if reader.exists():
  match=re.search(r'<script type="application/json" id="payload">(.*?)</script>',reader.read_text(),re.S);require(bool(match),'Reader payload missing');payload=json.loads(match.group(1));require(payload['summary']==report,'Reader summary stale; rebuild reader');require(payload['scope']==scope,'Reader scope stale')
  require(len(payload['authorities'])==len(authorities) and len(payload['cells'])==len(matrix),'Reader drops scope slots')
  require(payload['authorities']==authorities,'Reader authority evidence differs')
  for expected,actual in zip(matrix,payload['cells'],strict=True):
   require(all(k in expected and expected[k]==v for k,v in actual.items()),'Reader source/availability field differs')
  expected_links={}
  for p in profiles:expected_links.setdefault(p['source_id'],set()).update(p['source_urls'])
  for s in report.get('supplemental_source_batches',[]):expected_links.setdefault(s['source_id'],set()).add(s['download_url'])
  require(payload.get('source_links')=={k:sorted(v) for k,v in sorted(expected_links.items())},'Reader official source links differ')
 print(json.dumps({'status':'pass','assertions':checks,'authority_slots':len(authorities),'source_profiles':len(profiles),'discovery_cells':len(matrix),'canonical_ids':len(seen),'formats':'CSV/JSONL/SQLite agree','not_a_comparability_certification':True},ensure_ascii=False))
if __name__=='__main__':main()
