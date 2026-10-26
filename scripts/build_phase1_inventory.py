#!/usr/bin/env python3
"""Build auditable source availability outputs without harmonising values.

The 22-county grid is a navigation/discovery grid. Its cells count source
observations, never library quantities or complete/comparable indicator panels.
Every original observation remains in a source/period/population-specific group.
"""
from __future__ import annotations
import argparse,csv,datetime,hashlib,html,json,re,sqlite3,urllib.parse
from collections import Counter,defaultdict
from pathlib import Path
import record_io
ROOT=Path(__file__).resolve().parents[1]
PUBLICATION_FIELDS={'snapshot_distribution','public_evidence_path','public_evidence_sha256','public_projection_policy'}
PROFILE_FIELDS=['source_id','source_family','series_id','data_year','geography','geographic_scope','geography_vintage','indicator','indicator_group','source_field','unit','unit_raw','unit_status','population_scope','national_libraries_scope','temporal_kind','period_basis','source_edition','source_edition_roc','aggregation_role','institutional_level']
BAD_GEO=('uncertain','ambiguous','unresolved')
def sha(body):return hashlib.sha256(body).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def load(path,default=None):return json.loads(path.read_text()) if path.exists() else default
def write_json(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def csv_value(value):return canonical(value) if isinstance(value,(list,dict,bool)) else value
def write_table(root,name,rows):
 target=root/'derived';target.mkdir(parents=True,exist_ok=True)
 (target/(name+'.jsonl')).write_text(''.join(canonical(r)+'\n' for r in rows))
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (target/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:csv_value(v) for k,v in r.items()} for r in rows])
def original_text(row):return ' '.join(str(row.get(k) or '') for k in ('indicator','indicator_group','source_field'))
def topics_for(row):
 """Lexical discovery tags only, not a definition crosswalk or compatibility rule."""
 s=original_text(row);i=str(row.get('indicator') or '');result=set()
 if any(x in s for x in ('圖書館數','圖書館個數','館數','館所統計','館舍間數')) or re.search(r'(?:^|／)(?:總館|分館|區館|館外服務站|巡迴車)(?:[（(／]|$)',i):result.add('library_count')
 monetary=any(x in s for x in ('經費','資料費','購書','預算','決算','採購'))
 circulation=any(x in s for x in ('借閱','外借','續借','還書','預約'))
 if not monetary and not circulation and (any(x in s for x in ('館藏','藏書','收藏','圖書資料','非書資料')) or re.search(r'^(圖書|期刊|報紙|地圖|錄影資料|錄音資料|微縮|靜畫|視聽)',i)):result.add('holdings')
 if not monetary and any(x in s for x in ('電子','資料庫')):result.add('electronic_resources')
 if any(x in s for x in ('借閱','外借','續借')):
  if any(x in s for x in ('冊','件','量')) and not any(x in i for x in ('每人','人均','率')):result.add('loan_volumes')
  if any(x in s for x in ('人次','人數','人）','人)')):result.add('loan_visits')
 if any(x in s for x in ('進館','入館','到館')):result.add('visits')
 if any(x in s for x in ('人力','館員','人員','工讀','志工','聘僱','臨時','專業人','行政人','技術人')):result.add('staff')
 purchase=any(x in s for x in ('購書','購買圖書','圖書資料購置','圖書購置','購置圖書','資料費')) or any(x in i for x in ('預算','決算')) and any(x in i for x in ('圖書','電子書','期刊','報紙','視聽','電子資料'))
 if monetary and purchase:result.add('purchase_expenditure')
 if any(x in s for x in ('館舍面積','館舍總面積','館舍樓地板','樓地板面積')):result.add('floor_area')
 if any(x in s for x in ('活動','推廣','說故事','影片欣賞')):result.add('activities')
 # One original field may have multiple search tags. Counts are not additive.
 return sorted(result)
def quantity_role(row):
 s=original_text(row);unit=str(row.get('unit') or '')
 if 'ratio' in str(row.get('temporal_kind') or '') or any(x in s for x in ('每人','人均','每位','每10萬','每十萬','每千','成長率','利用率','借閱率','比率','比例','百分比','D/A','B/A','C/A')) or unit in ('%','百分比'):return 'ratio_or_per_capita_not_original_quantity'
 if any(x in s for x in ('人口數','人口(人)','人口（人）')):return 'population_context'
 if any(x in s for x in ('預約','還書','辦證','閱覽席','電腦','平板','參考諮詢','社群網站')) and not topics_for(row):return 'other_original_statistic_outside_ten_topics'
 return 'source_quantity_or_unresolved_original_measure'
def temporal_resolution(row):
 kind=str(row.get('temporal_kind') or '');periodicity=str(row.get('periodicity_raw') or '')
 basis=str(row.get('period_basis') or '');state=str(row.get('source_period_interpretation_status') or '')
 if 'unresolved' in basis or 'unresolved' in state:return 'time_basis_unconfirmed'
 if 'subperiod' in basis:return 'partial_or_programme_period'
 if 'month' in kind or '月' in periodicity or kind=='source_period_月':return 'monthly_source_not_annual_total'
 if any(x in kind for x in ('programme','campaign','partial','subperiod')):return 'partial_or_programme_period'
 if 'stock' in kind:return 'stock_or_year_end_reference'
 if 'year' in kind or 'annual' in kind or '年' in periodicity:return 'annual_reference_read_original_time_basis'
 return 'time_basis_unconfirmed'
def geography_uncertain(row):
 fields=' '.join(str(row.get(k) or '') for k in ('geographic_scope','entity_label_status'))
 flags=str(row.get('quality_flags') or '')
 return any(x in fields for x in BAD_GEO) or bool(re.search(r'(?:geograph\w*|county_label|entity_label)[^\s,;]{0,100}(?:uncertain|ambiguous|unresolved)',flags))
def profile_rows(rows):
 groups=defaultdict(list)
 for r in rows:groups[canonical({k:r.get(k) for k in PROFILE_FIELDS})].append(r)
 result=[]
 for key,items in sorted(groups.items()):
  p=json.loads(key);p['profile_id']='profile-'+sha(key.encode())[:24];p['topic_ids']=topics_for(items[0]);p['quantity_role']=quantity_role(items[0]);p['topic_assignment_basis']='literal_field_search_tags_only_not_definition_equivalence'
  p['temporal_resolution']=temporal_resolution(items[0]);p['observation_count']=len(items);p['nonmissing_value_records']=sum(r['value'] is not None for r in items);p['null_status_counts']=dict(sorted(Counter(r['value_status'] for r in items if r['value'] is None).items()))
  p['reported_zero_records']=sum(r['value'] in (0,'0','0.0','0.00') and r['value'] is not None for r in items)
  p['unconfirmed_geography_records']=sum(geography_uncertain(r) for r in items)
  p['unconfirmed_unit_records']=sum(r.get('unit') is None or any(x in str(r.get('unit_status') or '') for x in ('unresolved','unconfirmed','conflict')) for r in items)
  p['periods_present']=sorted({str(r.get('period_effective') or r.get('period_raw') or r.get('source_time_reference') or '') for r in items})
  p['facility_labels']=sorted({str(r.get('facility')) for r in items if r.get('facility')})
  p['source_urls']=sorted({r['source_url'] for r in items});p['source_sha256s']=sorted({r['source_sha256'] for r in items});p['observation_ids']=sorted(r['observation_id'] for r in items)
  p['compatibility_status']='not_certified_by_phase1_inventory';result.append(p)
 return result
def county_documents(root):
 docs=[]
 for path in (root/'raw/phase1-inventory').glob('county-*.json'):
  d=load(path,{});docs.append((path,d))
 return docs
def authority_and_candidate_rows(root,scope):
 by_key={};candidates=[];inputs=[]
 for path,d in county_documents(root):
  inputs.append({'path':path.relative_to(root).as_posix(),'sha256':sha(path.read_bytes())})
  counties=d.get('counties',[])
  if isinstance(counties,dict):counties=[{'county':name,**v} for name,v in counties.items()]
  for entry in counties:
   county=entry.get('county') or entry.get('name');slots=entry.get('authority_slots',[])
   for slot in slots:
    role=slot.get('role');key=(county,role)
    if key in by_key:raise ValueError('Duplicate authority role '+str(key))
    r=dict(slot);checks=r.get('checks') or [];latest=checks[-1] if checks else {};r.setdefault('check_status',r.get('status') or latest.get('status') or 'not_checked')
    relevant=[c for c in checks if c.get('status')==r['check_status']];primary=relevant[-1] if relevant else latest
    explicit=r.get('checked_url');matching=[c for c in checks if explicit and explicit in (c.get('url'),c.get('final_url'),c.get('checked_url'))]
    selected=matching[-1] if matching and matching[-1].get('status')==r['check_status'] else primary
    if explicit and explicit not in (selected.get('url'),selected.get('final_url')):r['original_preferred_entry_url']=explicit
    r['checked_url']=selected.get('url') or selected.get('checked_url') or explicit;r['checked_at']=selected.get('checked_at') or r.get('checked_at');r.setdefault('agency_name',r.get('agency'));r['county']=county;r['role']=role;r['inventory_record_id']='authority-'+sha((str(county)+'|'+str(role)).encode())[:20];r['evidence_inventory']=path.relative_to(root).as_posix();r['evidence_inventory_sha256']=sha(path.read_bytes());by_key[key]=r
   for s in entry.get('source_candidates',[]):
    item=dict(s);item['county']=county;item.setdefault('candidate_id',item.get('source_key') or 'candidate-'+sha(canonical(item).encode())[:24]);item['evidence_inventory']=path.relative_to(root).as_posix();item.setdefault('ingestion_status','not_ingested_unless_separate_verified_batch_evidence');candidates.append(item)
  for s in d.get('source_candidates',[]):
   item=dict(s);item.setdefault('candidate_id',item.get('source_key') or 'candidate-'+sha(canonical(item).encode())[:24]);item['evidence_inventory']=path.relative_to(root).as_posix();item.setdefault('ingestion_status','not_ingested_unless_separate_verified_batch_evidence');candidates.append(item)
 rows=[]
 for county in scope['current_county_navigation']:
  for role in scope['authority_roles']:
   rows.append(by_key.get((county,role),{'inventory_record_id':'authority-'+sha((county+'|'+role).encode())[:20],'county':county,'role':role,'check_status':'not_checked','checked_url':None,'checked_at':None,'check_scope':'Not yet checked; never interpret as no data.'}))
 if set(by_key)-{(c,r) for c in scope['current_county_navigation'] for r in scope['authority_roles']}:raise ValueError('Authority role outside the frozen scope')
 return rows,sorted(candidates,key=lambda x:(x.get('county',''),x['candidate_id'])),inputs
def discovery_matrix(rows,profiles,scope,authorities):
 index=defaultdict(list);id_to_profile={oid:p['profile_id'] for p in profiles for oid in p['observation_ids']}
 for r in rows:
  if not scope['years']['first']<=r['data_year']<=scope['years']['last']:continue
  # Ratio/prose evidence cannot silently fill a missing original-quantity slot.
  if quantity_role(r) in ('ratio_or_per_capita_not_original_quantity','population_context'):continue
  region=r.get('geography')
  if region not in set(scope['current_county_navigation'])|{'全國'}:continue
  for topic in topics_for(r):index[(r['data_year'],region,topic)].append(r)
 checks=Counter(r['county'] for r in authorities if r.get('check_status') not in (None,'not_checked'))
 output=[]
 for year in range(scope['years']['first'],scope['years']['last']+1):
  for county in ['全國',*scope['current_county_navigation']]:
   for topic in scope['topics']:
    items=index[(year,county,topic['id'])];confirmed=[r for r in items if not geography_uncertain(r)];valid=[r for r in confirmed if r['value'] is not None]
    status=('source_values_present_not_full_indicator_or_comparability_certification' if valid else 'source_nulls_or_markers_only' if confirmed else 'unconfirmed_geography_only' if items else 'no_ingested_match_not_evidence_of_no_official_data')
    output.append({'data_year':year,'navigation_region_current_name':county,'topic_id':topic['id'],'topic_label':topic['label'],'availability_status':status,'matched_source_observations':len(items),'confirmed_label_value_records':len(valid),'unconfirmed_geography_records':len(items)-len(confirmed),'temporal_resolution_counts':dict(sorted(Counter(temporal_resolution(r) for r in items).items())),'null_status_counts':dict(sorted(Counter(r['value_status'] for r in items if r['value'] is None).items())),'source_ids':sorted({r['source_id'] for r in items}),'profile_ids':sorted({id_to_profile[r['observation_id']] for r in items}),'checked_authority_slots':checks[county] if county!='全國' else None,'geography_rule':'Exact original label matches this navigation name only; historical county/city boundaries are not transformed. Read raw profiles for old labels.','interpretation':'This cell is source-field presence. Ratios are excluded. Monthly records are not annual totals. It is not a complete indicator value, an additive statistic, a comparable panel or proof that all relevant sources were searched.'})
 return output
def batch_inventory(root):
 d=load(root/'docs/historical-batches.json',{})
 if isinstance(d,list):return d
 for k in ('batches','cohorts','historical_batches'):
  if isinstance(d.get(k),list):return d[k]
 groups=load(root/'data/reviewed_historical_cohorts.json',{}).get('cohorts',[]);result=[]
 for group in groups:
  csv_path=root/group['derived_csv']
  if group.get('review_status')=='source_reviewed' and csv_path.exists():
   with csv_path.open(encoding='utf-8-sig',newline='') as f:count=sum(1 for _ in csv.DictReader(f))
   result.append({'cohort_id':group['id'],'status':'reviewed_bounded_scope','source_cells':count,'derived_csv':group['derived_csv'],'review_metadata':group.get('metadata_paths',[]),'completeness_scope':'Only the named table/subset batch; not entire yearbook or all counties/years.'})
 return result
def supplement_availability(root):
 path=root/'derived/phase1_local_sources_long.jsonl';sources=load(root/'raw/phase1_local_sources/sources.json',{}).get('sources',[])
 if not path.exists():return {},[],[]
 rows=[json.loads(x) for x in path.read_text().splitlines()];source_rows=defaultdict(list)
 for r in rows:source_rows[r['source_id']].append(r)
 index=defaultdict(lambda:{'source_cell_records':0,'nonmissing_source_cell_records':0,'source_ids':set(),'temporal_basis':set()})
 # Formal year slots require evidence from the sheet, not a filename/catalogue hint.
 for r in rows:
  if r.get('period_status') not in ('matching_sheet_name_and_header_month','explicit_sheet_year'):continue
  year=r.get('period_year');county=r.get('county')
  if not isinstance(year,int):continue
  probe={'indicator':r.get('metric_raw'),'source_field':r.get('metric_raw'),'unit':r.get('unit'),'indicator_group':''}
  for topic in topics_for(probe):
   x=index[(year,county,topic)];x['source_cell_records']+=1;x['nonmissing_source_cell_records']+=r.get('value') is not None;x['source_ids'].add(r['source_id']);x['temporal_basis'].add(r.get('period_status'))
 summaries=[]
 for s in sources:
  items=source_rows[s['source_id']];verified=sorted({r['period_year'] for r in items if isinstance(r.get('period_year'),int) and r.get('period_status') in ('matching_sheet_name_and_header_month','explicit_sheet_year')})
  summaries.append({'source_id':s['source_id'],'county':s['county'],'title':s['source_title'],'catalog_url':s['source_url'],'download_url':s['source_download_url'],'final_url':s.get('source_final_url'),'source_sha256':s['source_sha256'],'statistical_cells':len(items),'verified_sheet_years':verified,'period_status_counts':dict(sorted(Counter(r['period_status'] for r in items).items())),'value_status_counts':dict(sorted(Counter(r['value_status'] for r in items).items())),'scope':'Complete relevant source-cell batch only; do not append to canonical observations or interpret county navigation as complete county coverage.'})
 inputs=[{'path':path.relative_to(root).as_posix(),'sha256':sha(path.read_bytes())}]
 for name in ('raw/phase1_local_sources/sources.json','raw/phase1_local_sources/summary.json','research/phase1-local-independent-review.json'):
  p=root/name
  if p.exists():inputs.append({'path':name,'sha256':sha(p.read_bytes())})
 return index,summaries,inputs
def link_supplement_batches(candidates,supplements,root):
 review=load(root/'research/phase1-local-independent-review.json',{});comparison=review.get('comparison',{})
 accepted=(review.get('result')=='PASS' and comparison.get('matched_all_expected_source_cells') is True and not comparison.get('mismatches') and bool(comparison.get('final_file_sha256')))
 if accepted:
  accepted=all((root/path).is_file() and hashlib.sha256((root/path).read_bytes()).hexdigest()==digest for path,digest in comparison['final_file_sha256'].items())
 def key(url):return urllib.parse.unquote(urllib.parse.urldefrag(str(url or ''))[0])
 by_url={key(s[k]):s for s in supplements for k in ('download_url','final_url') if s.get(k)}
 for c in candidates:
  urls=[c.get('source_download_url'),c.get('download_url')]+[r.get('url') for r in c.get('resources',[]) if r.get('in_operational_library_scope')is not False]
  matches={by_url[key(u)]['source_id']:by_url[key(u)] for u in urls if key(u) in by_url}
  if not matches:continue
  c['discovery_ingestion_status']=c.get('ingestion_status');c['verified_source_cell_batches']=sorted(matches);c['source_cell_batch_records']=sum(s['statistical_cells'] for s in matches.values());c['verified_sheet_years']=sorted({y for s in matches.values() for y in s['verified_sheet_years']})
  c['ingestion_status']='source_cell_batch_verified_not_harmonised' if accepted else 'source_cell_extraction_complete_independent_review_pending';c['canonical_union_permitted']=False
def write_database(root,tables):
 p=root/'derived/phase1_inventory.sqlite';tmp=p.with_suffix('.sqlite.tmp');tmp.unlink(missing_ok=True);con=sqlite3.connect(tmp)
 for name,rows in tables.items():
  fields=list(dict.fromkeys(k for row in rows for k in row))
  if not fields:con.execute('CREATE TABLE "'+name+'" (empty_table TEXT)');continue
  con.execute('CREATE TABLE "'+name+'" ('+','.join('"'+x+'" TEXT' for x in fields)+')')
  con.executemany('INSERT INTO "'+name+'" VALUES ('+','.join('?' for _ in fields)+')',[[csv_value(r.get(k)) for k in fields] for r in rows])
 con.commit();con.close();tmp.replace(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--require-survey-complete',action='store_true');a=p.parse_args();root=a.root.resolve();scope=load(root/'scripts/phase1_scope.json');rows=list(record_io.rows(root,'data/combined/observations.jsonl'));summary=load(root/'data/combined/summary.json')
 authorities,candidates,inputs=authority_and_candidate_rows(root,scope);profiles=profile_rows(rows);matrix=discovery_matrix(rows,profiles,scope,authorities);batches=batch_inventory(root);central=load(root/'raw/phase1-inventory/central.json',{'sources':[]});supp_index,supplements,supp_inputs=supplement_availability(root);inputs+=supp_inputs;link_supplement_batches(candidates,supplements,root)
 for cell in matrix:
  ext=supp_index.get((cell['data_year'],cell['navigation_region_current_name'],cell['topic_id']),{});cell['supplementary_source_cells']=ext.get('source_cell_records',0);cell['supplementary_nonmissing_cells']=ext.get('nonmissing_source_cell_records',0);cell['supplementary_source_ids']=sorted(ext.get('source_ids',[]));cell['supplementary_period_basis']=sorted(ext.get('temporal_basis',[]));cell['supplementary_scope_note']='Additional independent source-cell layer; period/header conflicts and catalogue-only years excluded; not a harmonised county/annual quantity.'
 all_ids=[i for p in profiles for i in p['observation_ids']];assert len(all_ids)==len(set(all_ids))==len(rows)
 pending=[r for r in authorities if r.get('check_status') in (None,'not_checked')]
 if a.require_survey_complete and pending:raise ValueError('Authority roles still unchecked: '+str([(r['county'],r['role']) for r in pending]))
 stat=sha(canonical([{k:v for k,v in r.items() if k not in PUBLICATION_FIELDS} for r in rows]).encode())
 inputs+=[{'path':'scripts/phase1_scope.json','sha256':sha((root/'scripts/phase1_scope.json').read_bytes())},{'path':'scripts/build_phase1_inventory.py','sha256':sha(Path(__file__).read_bytes())},{'path':'canonical_statistical_content','sha256':stat}]
 if (root/'raw/phase1-inventory/central.json').exists():inputs.append({'path':'raw/phase1-inventory/central.json','sha256':sha((root/'raw/phase1-inventory/central.json').read_bytes())})
 report={'schema_version':'1.0.0','scope_id':scope['scope_id'],'scope_version':scope['version'],'dataset_version':summary['version'],'canonical_records':len(rows),'canonical_statistical_content_sha256':stat,'authority_slots_expected':len(authorities),'authority_slots_with_recorded_attempt':len(authorities)-len(pending),'authority_check_status_counts':dict(sorted(Counter(r.get('check_status','not_checked') for r in authorities).items())),'counties_expected':len(scope['current_county_navigation']),'central_entry_status_counts':dict(sorted(Counter(r.get('check_status') for r in central['sources']).items())),'source_candidates_listed':len(candidates),'reviewed_batch_inventory_entries':len(batches),'raw_source_profiles':len(profiles),'discovery_matrix_cells':len(matrix),'matched_value_navigation_cells':sum(r['confirmed_label_value_records']>0 for r in matrix),'unclassified_observations':sum(p['observation_count'] for p in profiles if not p['topic_ids']),'historical_or_other_raw_region_profiles':sum(p['geography'] not in scope['current_county_navigation']+['全國'] for p in profiles),'all_original_observation_ids_accounted_for':True,'all_history_complete':False,'cross_year_comparability_certified':False,'source_survey_scope':'Four specified role checks per current county; evidence bounds and failed checks are visible. Not exhaustive crawling of every agency archive.','core_coverage_scope':'Exact label/topic discovery slots only, not detailed indicator completeness. Use raw profiles and original statuses.','known_2012_gap':'County core original-quantity tables not obtained in checked sources; original prose ratios remain separate; no imputation.','inputs':inputs}
 report['supplemental_source_batches']=supplements;report['additional_source_cell_period_policy']='Only explicit sheet years or matching sheet/header month years enter the navigation index. Unresolved and catalogue-only periods remain in original source-cell files, not verified year slots.'
 tables={'phase1_authority_checks':authorities,'phase1_source_candidates':candidates,'phase1_raw_source_profiles':profiles,'phase1_discovery_matrix':matrix}
 for name,items in tables.items():write_table(root,name,items)
 # SQLite is derived/ so publication explicitly allowlists this one additional DB.
 write_database(root,tables);write_json(root/'docs/phase1-summary.json',report);write_json(root/'docs/phase1-source-inventory.json',{'schema_version':'1.0.0','scope':scope,'authority_checks':authorities,'central_checks':central['sources'],'source_candidates':candidates,'reviewed_batches':batches})
 text=['# 第一階段：來源與缺口矩陣','',f"資料版本v{summary['version']}；盤點範圍2005–2025。全臺所有歷年仍未齊全，這份矩陣不認證跨年可比。",'',f"22縣市×4角色，共{len(authorities)}個指定入口查核槽位；有記錄的查核嘗試{len(authorities)-len(pending)}個。HTTP失敗、只查入口及已見相關表分列，不把連線成功當整機關查核完整。",'',f"目前正式{len(rows):,}筆全部分入{len(profiles):,}個原來源／原指標／母體／期間／版次組，沒有合併數值或重編行政區。{len(matrix):,}個年×導航地區×主題格只是資料出現索引，不是完整指標或可比面板。",'', '## 下載與重現','', '- [來源清單JSON](phase1-source-inventory.json)與[進度摘要](phase1-summary.json)。','- [角色查核CSV](../derived/phase1_authority_checks.csv)、[候選來源CSV](../derived/phase1_source_candidates.csv)。','- [年／地區／主題索引CSV](../derived/phase1_discovery_matrix.csv)、[逐來源口徑CSV](../derived/phase1_raw_source_profiles.csv)。','- 同名JSONL為同一批資料；[SQLite](../derived/phase1_inventory.sqlite)有四個同名表。','- 以`python scripts/build_phase1_inventory.py --require-survey-complete`重建；輸入與規則雜湊在摘要中。','', '## 如何讀完整度','', '來源查核、表格批次完成、原格有值是三個不同分母。原刊留白／未統計／明示缺值不算有值，也不改0；未取得、權利待確認與尚未查不能混成無資料。候選來源僅表示已定位，未有完整來源批次驗收前不算已入庫。','', '原標籤與每組來源網址、SHA、觀測ID仍保留。現行22縣市導航不會將臺北縣改成新北市，也不會將舊臺南縣市加總；舊名稱在逐來源口徑清單獨立呈現。未確認的2015/2024縣市標籤不計為已確認縣市值。','', '十個主題只作搜尋分類，不能把同一主題的冊／件／種、預算／決算、場次／人次相加。所有原指標保留；未能依原欄標確定主題的觀測列在逐來源清單，不猜分類。','', '2012縣市核心原量仍未取得，不由比率反算。2026月值／暫計與1991–2004既有資料保留在正式資料和逐來源清單，不冒稱本期核心範圍完整。','', '原始HTML可能含聯絡資訊，保持私人研究來源；公開清單只保留必要事實、短定位、URL與原件SHA。取得公開頁不等於已確認其所有附件可再散布。','', '## 各縣市角色查核','', '|縣市|圖書館|文化|主計／統計|開放資料|','|---|---|---|---|---|']
 lookup={(r['county'],r['role']):r for r in authorities}
 for county in scope['current_county_navigation']:
  cells=[]
  for role in scope['authority_roles']:
   r=lookup[(county,role)];url=r.get('checked_url') or r.get('official_home_url');label=r.get('check_status','not_checked');cells.append(f'[{label}]({url})' if url else label)
  text.append('|'+county+'|'+'|'.join(cells)+'|')
 (root/'docs/PHASE1.md').write_text('\n'.join(text)+'\n');print(json.dumps({k:v for k,v in report.items() if k in ('authority_slots_expected','authority_slots_with_recorded_attempt','source_candidates_listed','raw_source_profiles','discovery_matrix_cells','unclassified_observations')},ensure_ascii=False))
if __name__=='__main__':main()
