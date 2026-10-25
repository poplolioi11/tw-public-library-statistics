#!/usr/bin/env python3
"""Create a single queryable bundle and portable reader from verified component datasets."""
import csv,datetime,hashlib,html,json,sqlite3,zipfile
from pathlib import Path
import record_io
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip() if (ROOT/'VERSION').exists() else '0.1.0'
def sha(b):return hashlib.sha256(b).hexdigest()
def write_json(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def main():
 rows=[json.loads(x) for x in (ROOT/'data/observations.jsonl').read_text().splitlines() if x]
 # Additional verified historical components are explicitly adapted; no guessed field mappings.
 adapters=record_io.path_for(ROOT,'data/component_records.jsonl')
 if adapters.exists():rows += list(record_io.rows(ROOT,'data/component_records.jsonl'))
 for r in rows:
  if not r.get('source_family'):r['source_family']='國資圖公開全國圖表' if r['source_id'].startswith('public-chart-') else '國資圖2023開放資料（含縣市）'
 rows.sort(key=lambda r:(r['data_year'],r['source_id'],r['geography'],r['series_id']))
 ids=[x['observation_id'] for x in rows]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate IDs across components')
 target=ROOT/'data/combined';target.mkdir(parents=True,exist_ok=True)
 columns=list(dict.fromkeys(k for r in rows for k in r))
 for r in rows:
  for c in columns:r.setdefault(c,None)
 jsonl_path=record_io.write(ROOT,'data/combined/observations.jsonl',rows)
 jsonl_relative=str(jsonl_path.relative_to(ROOT))
 with (target/'observations.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
 dbpath=target/'library_statistics.sqlite'
 if dbpath.exists():dbpath.unlink()
 con=sqlite3.connect(dbpath)
 con.execute('CREATE TABLE observations ('+', '.join('"'+c+'" '+('INTEGER' if c=='data_year' else 'TEXT') for c in columns)+')')
 con.executemany('INSERT INTO observations VALUES ('+','.join('?' for c in columns)+')',[[r.get(c) for c in columns] for r in rows])
 con.execute('CREATE UNIQUE INDEX observation_key ON observations(observation_id)');con.execute('CREATE INDEX year_geo_series ON observations(data_year,geography,series_id)')
 con.execute('CREATE VIEW national_public_trends AS SELECT * FROM observations WHERE source_id LIKE "public-chart-%"')
 con.execute('CREATE VIEW counties_ogdl_2023 AS SELECT * FROM observations WHERE source_id="ogdl-api-2023" AND geographic_scope="county_default_includes_national_where_applicable"')
 con.commit();con.close()
 bysource={}
 for r in rows:
  key=r['source_id'];b=bysource.setdefault(key,{'source_id':key,'year':r['data_year'],'data_years':set(),'periods':set(),'records':0,'geographies':set(),'source_url':r['source_url'],'rights':r['license_status']});b['records']+=1;b['geographies'].add(r['geography']);b['data_years'].add(r['data_year']);b['periods'].add(r.get('period_effective') or str(r['data_year']))
 coverage=[{**b,'year':next(iter(b['data_years'])) if len(b['data_years'])==1 else None,'data_years':sorted(b['data_years']),'periods':sorted(b['periods']),'geographies':sorted(b['geographies'])} for b in bysource.values()]
 write_json(target/'coverage.json',coverage)
 registry={}
 for r in rows:
  key=r['source_id']+'@'+r['source_sha256']
  registry.setdefault(key,{k:r.get(k) for k in ['source_id','source_family','source_url','source_page_url','source_method','source_request','source_sha256','source_snapshot_path','retrieved_at','license_status','license_url','snapshot_distribution','public_evidence_path','public_evidence_sha256','public_projection_policy']})
 write_json(target/'sources.json',list(registry.values()))
 indicators=json.loads((ROOT/'data/indicators.json').read_text());seen={r['series_id'] for r in indicators}
 for r in rows:
  if r['series_id'] not in seen:
   indicators.append({k:r.get(k) for k in ['series_id','definition_id','indicator','indicator_group','unit','temporal_kind','definition_status','source_id','source_url','notes']});seen.add(r['series_id'])
 for item in indicators:item['observed_years']=sorted({r['data_year'] for r in rows if r['series_id']==item['series_id']})
 write_json(target/'indicators.json',indicators)
 summary={'version':VERSION,'canonical_jsonl_path':jsonl_relative,'jsonl_compression':'gzip' if jsonl_path.suffix=='.gz' else None,'canonical_uncompressed_sha256':record_io.logical_sha(ROOT),'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':len(rows),'missing_cells':sum(r['value'] is None for r in rows),'null_value_status_counts':{status:sum(r['value'] is None and r['value_status']==status for r in rows) for status in sorted({r['value_status'] for r in rows if r['value'] is None})},'reference_years':sorted({r['data_year'] for r in rows}),'source_series':len({r['series_id'] for r in rows}),'source_groups':len(coverage),'source_families':{},'scope_statement':'已驗證可得來源的全量整理；不是宣稱臺灣所有年代、所有縣市與每一圖書館都已完整。','all_history_complete':False}
 for r in rows:
  fam='國資圖公開全國圖表' if r['source_id'].startswith('public-chart-') else ('國資圖2023開放資料（含縣市）' if r['source_id']=='ogdl-api-2023' else r.get('source_family','其他官方歷史表'))
  summary['source_families'][fam]=summary['source_families'].get(fam,0)+1
 write_json(target/'summary.json',summary)
 schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:tw-public-library-statistics:observation:1.0.0','title':'Taiwan public library source observation','type':'object','required':['observation_id','data_year','geography','geographic_scope','series_id','indicator','value','raw_value','value_status','source_id','source_url','source_locator','source_sha256','license_status'],'properties':{c:{'description':c} for c in columns}}
 schema['properties'].update({'data_year':{'type':'integer'},'value':{'type':['integer','number','string','null'],'description':'Decimal values may be canonical decimal strings. Zero is as reported, not certified true zero.'},'source_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},'source_locator':{'type':'string','description':'JSON Pointer for API data; original page/table/row/column for published tables.'}})
 schema['properties']['value_status']={'type':'string','description':'Source state: reported/reported_decimal, source_blank (original empty cell, reason unconfirmed), not_available_in_source (explicit missing marker), source_marker (original literal無/未新增; meaning unresolved, never automatically zero or not applicable). Always preserve raw_value.'}
 for field in ('period_start_candidate','period_end_candidate','source_period_interpretation_status'):
  schema['properties'][field]={'type':['string','null'],'description':'Unresolved date interpretation, separated from confirmed period dates. Read the exact source_subrow_label_raw and period_basis.'}
 schema['properties']['value_qualifier']={'type':['string','null'],'description':'scoped_source_component limits a reported number to the original named component; never treat it as the full county total.'}
 schema['properties']['unit_basis']={'type':['string','null'],'description':'Original or contextual basis of normalized unit. Read unit_raw and unit_status; inferred units are not printed labels.'}
 write_json(target/'observation.schema.json',schema)
 write_json(ROOT/'datapackage.json',{'name':'tw-public-library-statistics','title':'臺灣公共圖書館跨年度統計','version':VERSION,'description':summary['scope_statement'],'licenses':[{'name':'source-specific','title':'按每筆來源標記；明確6425/2023為OGDL-1.0，其餘公開統計事實或各來源授權，詳LICENSE.md'}],'resources':[{'name':'observations','path':'data/combined/observations.csv','format':'csv','encoding':'utf-8-sig','hash':'sha256:'+sha((target/'observations.csv').read_bytes())},{'name':'observations-jsonl','path':jsonl_relative,'format':'jsonl','compression':'gzip' if jsonl_path.suffix=='.gz' else None},{'name':'query-database','path':'data/combined/library_statistics.sqlite','format':'sqlite'}]})
 fields=['data_year','source_id','series_id','indicator','indicator_group','geography','geographic_scope','value','unit','notes','source_field','source_page_url','source_url','source_method','source_request','source_snapshot_path','source_locator','source_sha256','retrieved_at','license_status','source_family','snapshot_distribution','period_effective','facility','public_evidence_path','raw_value','value_status','quality_flags','aggregation_role','institutional_level','source_version_id','unit_raw','unit_basis','unit_status','source_edition','source_edition_roc','source_footnotes_raw','source_original_access_date_raw','source_cell_annotation','value_qualifier','source_location_kind','book_class_raw','age_group_raw','sex_raw','source_time_reference','observation_identity_suffix','source_unit_interpretation_basis','unit_interpretation_candidate']
 dictionaries=[[] for _ in fields];indexes=[{} for _ in fields];vectors=[]
 for row in rows:
  vector=[]
  for i,key in enumerate(fields):
   value=row.get(key);token=json.dumps(value,ensure_ascii=False,sort_keys=True)
   if token not in indexes[i]:indexes[i][token]=len(dictionaries[i]);dictionaries[i].append(value)
   vector.append(indexes[i][token])
  vectors.append(vector)
 payload=json.dumps({'fields':fields,'dictionaries':dictionaries,'vectors':vectors},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
 summary_payload=json.dumps(summary,ensure_ascii=False).replace('</','<\\/')
 template=(ROOT/'site/template.html').read_text()
 (ROOT/'site/index.html').write_text(template.replace('__ROWS__',payload).replace('__SUMMARY__',summary_payload).replace('__JSONL_HREF__','../'+jsonl_relative).replace('__JSONL_LABEL__','下載 JSONL（gzip）' if jsonl_path.suffix=='.gz' else '下載 JSONL'))
 # The portable reader is self contained; no remote libraries, fonts, telemetry or network calls.
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
