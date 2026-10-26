#!/usr/bin/env python3
"""Materialize complete source routes and registered default decisions, no acquisition."""
import argparse,collections,gzip,json,sqlite3,tempfile
from pathlib import Path
import phase2_engine as p2
import phase3_engine as engine
from build_phase2 import table_buffers,replace_if_changed,sql_ident,cell,fields,file_hash
ROOT=Path(__file__).resolve().parents[1]
INPUTS=['derived/phase2/annotations.jsonl.gz','derived/phase2/evidence_cards.jsonl','docs/phase3-contract.json','docs/phase3-profiles.json','scripts/phase3_engine.py','scripts/build_phase3.py']
def compact_table(con,name,rows,dictionary):
 columns=fields(rows);coded=[]
 for row in rows:
  values=[]
  for column in columns:
   value=cell(row.get(column));value=None if value is None else str(value)
   if value is not None and value not in dictionary:dictionary[value]=len(dictionary)+1
   values.append(None if value is None else dictionary[value])
  coded.append(values)
 con.execute('CREATE TABLE '+sql_ident(name+'_codes')+' ('+','.join(sql_ident(c)+' INTEGER' for c in columns)+')')
 con.executemany('INSERT INTO '+sql_ident(name+'_codes')+' VALUES ('+','.join('?' for c in columns)+')',coded)
 joins=[];select=[]
 for i,column in enumerate(columns):
  alias='v'+str(i);select.append(alias+'.value AS '+sql_ident(column));joins.append(' LEFT JOIN value_dictionary '+alias+' ON '+alias+'.value_id=r.'+sql_ident(column))
 con.execute('CREATE VIEW '+sql_ident(name)+' AS SELECT '+','.join(select)+' FROM '+sql_ident(name+'_codes')+' r'+''.join(joins))
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=ROOT);args=ap.parse_args();root=args.root.resolve();version=(root/'VERSION').read_text().strip();before={name:file_hash(root/name) for name in INPUTS}
 annotations=engine.load_annotations(root);policy=engine.load_policy(root);contract=json.loads((root/'docs/phase3-contract.json').read_text());profiles=policy['profiles']
 if {p['id'] for p in profiles}!=set(contract['profiles']):raise ValueError('Question registry differs from reviewed contract')
 source_groups=collections.defaultdict(list)
 for a in annotations:source_groups[(a['layer'],a['source_id'],a['source_sha256'])].append(a)
 routes=[];runtime=[]
 for key,items in sorted(source_groups.items()):
  evidence={a['evidence_id']:policy['_current_evidence_digests'].get(a['evidence_id']) for a in items}
  sig=engine.hashed({'source':key,'records':items,'policy':before['docs/phase3-profiles.json'],'evidence':evidence,'engine':before['scripts/phase3_engine.py']});cache=root/'data/cache/phase3-routes'/sig;bodyfile=cache.with_suffix('.jsonl');hashfile=cache.with_suffix('.sha256')
  reuse=bodyfile.exists() and hashfile.exists() and file_hash(bodyfile)==hashfile.read_text().strip()
  if reuse:batch=[json.loads(x) for x in bodyfile.read_text().splitlines()]
  else:
   batch=engine.route_records(items,policy);body=''.join(engine.stable(r)+'\n' for r in batch).encode();replace_if_changed(bodyfile,body)
   replace_if_changed(hashfile,(file_hash(bodyfile)+'\n').encode())
  if {r['record_key'] for r in batch}!={a['record_key'] for a in items}:raise ValueError('Source route cache identities differ')
  routes+=batch;runtime.append({'layer':key[0],'source_id':key[1],'source_sha256':key[2],'records':len(batch),'reused':reuse})
 routes.sort(key=lambda r:r['record_key']);decisions=[];queries=[];edges=[]
 for p in profiles:
  answer=engine.select(policy,annotations,p['id']);decisions+=answer['decisions'];queries.append(answer['query']);edges+=answer['edges']
 decisions.sort(key=lambda r:(r['profile_id'],r['record_key']));queries.sort(key=lambda r:r['profile_id']);edges.sort(key=lambda r:(r['profile_id'],r['edge_id']))
 tables={'record_routes':routes,'candidate_decisions':decisions,'queries':queries,'series_edges':edges};payloads={};definitions=[];dictionary_schema={}
 for name,rows in tables.items():
  if not rows:raise ValueError('Expected complete nonempty source table: '+name)
  compressed=name in ('record_routes','candidate_decisions');csvpath='derived/phase3/'+name+'.csv'+('.gz' if compressed else '');jsonpath='derived/phase3/'+name+'.jsonl'+('.gz' if compressed else '')
  buffers=table_buffers(name,rows,compressed=compressed)
  # table_buffers exposes names rooted under derived/phase2; only transport bytes are reused.
  csvbody=next(v for k,v in buffers.items() if '.csv' in k);jsonbody=next(v for k,v in buffers.items() if '.jsonl' in k);payloads[csvpath]=csvbody;payloads[jsonpath]=jsonbody
  definitions.append({'table':name,'records':len(rows),'csv':csvpath,'jsonl':jsonpath})
  dictionary_schema[name]={k:{'json_types':sorted({type(r[k]).__name__ for r in rows if k in r}),'present_in_all_records':all(k in r for r in rows)} for k in fields(rows)}
 partitions=[];parts=collections.defaultdict(list)
 for d in decisions:parts[(d['profile_id'],d['period_year'])].append(d)
 for (pid,year),rows in sorted(parts.items(),key=lambda x:(x[0][0],str(x[0][1]))):
  name='derived/phase3/by_profile_year/'+pid+'/'+(str(year) if year is not None else 'unresolved_period')+'.jsonl';body=''.join(engine.stable(r)+'\n' for r in rows).encode();payloads[name]=body;partitions.append({'profile_id':pid,'period_year':year,'path':name,'records':len(rows),'selected_records':sum(r['selected'] for r in rows),'sha256':p2.sha(body),'bytes':len(body)})
 with tempfile.TemporaryDirectory(prefix='phase3-sqlite-') as temporary:
  db=Path(temporary)/'selection.sqlite';con=sqlite3.connect(db);con.execute('CREATE TABLE value_dictionary(value_id INTEGER PRIMARY KEY,value TEXT NOT NULL)');dictionary={}
  for name,rows in tables.items():compact_table(con,name,rows,dictionary)
  con.executemany('INSERT INTO value_dictionary VALUES (?,?)',[(i,v) for v,i in dictionary.items()]);con.commit();con.execute('VACUUM');con.close();payloads['derived/phase3/selection.sqlite']=db.read_bytes()
 if len(payloads['derived/phase3/selection.sqlite'])>=100*1024*1024:raise ValueError('Selection database exceeds GitHub file limit; retain previous release and review storage layout')
 if {name:file_hash(root/name) for name in INPUTS}!=before:raise ValueError('Phase3 input changed during build; previous outputs retained')
 for name,body in payloads.items():replace_if_changed(root/name,body)
 p2summary=json.loads((root/'docs/phase2-summary.json').read_text())
 counts={name:len(rows) for name,rows in tables.items()};summary={'schema_version':'1.0.0','dataset_version':version,'policy_version':policy['policy_version'],'scope':'Registered source selection over the complete existing quantitative inventory; not additional operational statistics.','counts':counts,'registered_profiles':len(profiles),'route_status_counts':dict(collections.Counter(r['route_status'] for r in routes)),'selection_status_counts':dict(collections.Counter(d['selection_status'] for d in decisions)),'selected_decisions':sum(d['selected'] for d in decisions),'drawable_edges':sum(e['drawable'] for e in edges),'partitions':len(partitions),'tables':definitions,'layer_raw_fingerprints':p2summary['layer_raw_fingerprints'],'canonical_values_modified':False,'all_history_complete':False,'all_historical_definitions_certified':False,'automatic_defaults_are_bounded_registered_questions_only':True,'no_imputation':True,'no_aggregation':True,'no_geographic_recoding':True,'inputs':before,'outputs':{name:{'sha256':p2.sha(body),'bytes':len(body)} for name,body in sorted(payloads.items())}}
 for name,obj in [('docs/phase3-summary.json',summary),('docs/phase3-partitions.json',{'schema_version':'1.0.0','dataset_version':version,'union_equals_candidate_decisions':True,'partitions':partitions}),('docs/phase3-data-dictionary.json',{'schema_version':'1.0.0','dataset_version':version,'tables':dictionary_schema,'sqlite_scalar_policy':'Wide views expose TEXT; JSON structures are encoded JSON and NULL stays SQL NULL. Never infer numeric zero from failed parsing.'}),('docs/phase3-question-index.json',{'schema_version':'1.0.0','dataset_version':version,'policy_version':policy['policy_version'],'profiles':profiles})]:replace_if_changed(root/name,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())
 replace_if_changed(root/'data/phase3-build-runtime.private.json',(json.dumps({'source_groups':runtime,'reused':sum(x['reused'] for x in runtime),'rebuilt':sum(not x['reused'] for x in runtime)},ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({k:summary[k] for k in ('dataset_version','counts','registered_profiles','selection_status_counts','selected_decisions','drawable_edges','partitions')},ensure_ascii=False))
if __name__=='__main__':main()
