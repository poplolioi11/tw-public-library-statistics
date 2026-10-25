#!/usr/bin/env python3
"""Explicit adapters: preserve original periods/scopes; never fuzzy-merge sources."""
import csv,hashlib,json,re
from pathlib import Path
from library_pipeline import parse_number
ROOT=Path(__file__).resolve().parents[1]
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def read(p):
 if not p.exists():return []
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def base_record():return {'collection_year':None,'publication_year':None,'definition_source_id':None,'definition_sha256':None,'definition_retrieved_at':None,'source_method':'GET','source_request':None,'comparability':'not_certified_across_years_or_source_families'}
def period_year(text):
 s=text.strip()
 if re.match(r'^(19|20)\d{2}[-/]',s):return int(s[:4])
 if re.fullmatch(r'\d{5}',s):return int(s[:3])+1911
 if re.fullmatch(r'\d{2,3}',s):return int(s)+1911
 if re.fullmatch(r'(19|20)\d{2}',s):return int(s)
 m=re.match(r'^(?:民國)?(\d{2,3})[年/.-]',s)
 if m:return int(m.group(1))+1911
 raise ValueError('Unresolved reference year '+repr(s))
def parse_local_value(raw,unit):
 value,status=parse_number(raw)
 if status!='unparsed':return value,status,unit,'standard_numeric_or_marker'
 text=str(raw).strip().replace(',','')
 m=re.fullmatch(r'(\d+)冊',text)
 if m:return int(m.group(1)),'reported',unit or '冊','explicit_suffix_冊'
 m=re.fullmatch(r'(\d+)萬\s*(\d*)',text)
 if m and (not m.group(2) or int(m.group(2))<10000):return int(m.group(1))*10000+int(m.group(2) or '0'),'reported',unit,'explicit_萬_magnitude_no_currency_inference'
 return value,status,unit,'unparsed_preserved'

def main():
 records=[];issues=[]
 qp=ROOT/'derived/local_historical_quality.json';quality=json.loads(qp.read_text()) if qp.exists() else {}
 arithmetic_flags={(q['source_id'],q['period'],q['location'],q['total_field']):q for q in quality.get('hsinchu_arithmetic_errors',[])}
 for filename,family in [('ncl_historical_long.csv','國家圖書館年鑑統計事實'),('dgbas_historical_long.csv','主計總處歷史全國統計')]:
  for row in read(ROOT/'derived'/filename):
   yr=int(row['data_year']);source=row['source_id'];geo=row['entity_raw'];sid=source+'-'+row['metric_id'];v,status=parse_number(row['value']);unit=row['unit'];notes=[]
   if '混合' in unit:notes.append('原表標示：'+unit+'；不視為純圖書冊數。');unit=None
   if row.get('caveats'):notes.append(row['caveats'])
   if row.get('national_libraries_scope')=='excluded_from_county_metrics':notes.append('原縣市列不含另列三所國立／省設館；行政區依當年原表，不轉為現行22縣市。')
   if row.get('geography_vintage'):notes.append(row['geography_vintage'])
   if source.startswith('ncl') and yr==2010 and geo=='總計' and row['metric_id']=='acquisition_spending_per_capita':notes.append('來源內部差異：此表原印27.72，正文及總經費／人口計算約22.72；忠實保留原表，不自行改值。');issues.append({'source_id':source,'year':yr,'geography':geo,'indicator':row['metric_raw'],'issue':'official_internal_inconsistency','reported_value':v,'explanation':notes[-1]})
   pub=row.get('publication_date') or None
   if row.get('value_status')=='not_available_in_source':v=None;status='not_available_in_source'
   record={**base_record(),'observation_id':'obs-'+h(source+'|'+row['metric_id']+'|'+geo+'|'+str(yr))[:22],'data_year':yr,'geography':geo,'geography_contextual_name':row.get('entity_contextual_name',geo),'geographic_scope':row['entity_kind'],'geography_vintage':row.get('geography_vintage'),'national_libraries_scope':row.get('national_libraries_scope'),'population_scope':'公立公共圖書館，依各出版表母體與註腳','series_id':sid,'indicator':row['metric_raw'],'indicator_group':family,'source_field':row['metric_raw'],'value':v,'raw_value':row['value_raw'],'value_status':status,'zero_interpretation':'source_reported_zero_historical_context_required' if v==0 else None,'unit':unit,'unit_status':'source_table' if unit else 'mixed_not_uniform','temporal_kind':row['temporal_kind'],'period_start':f'{yr}-01-01' if row['temporal_kind']=='flow_calendar_year' else None,'period_end':f'{yr}-12-31','period_basis':'published_table_reference_year','definition_id':'def-'+sid,'definition_status':'original_table_heading_and_footnotes_preserved','source_id':source,'source_family':family,'source_url':row['source_download_url']+'#page='+row['source_pdf_page'],'source_page_url':row['source_url'],'source_locator':row['source_locator']+'; column '+row['source_column'],'source_sha256':row['source_sha256'],'source_snapshot_path':row['source_local_path'],'retrieved_at':row['source_retrieved_at'],'license_status':'OGDL-1.0_site_declaration' if source.startswith('dgbas') and row.get('license_status')=='verified_open' and row.get('license_code')=='OGDL-1.0_site_declaration' else 'published_statistical_facts_document_license_unconfirmed','license_url':'https://www.stat.gov.tw/cp.aspx?n=3164' if source.startswith('dgbas') else None,'snapshot_distribution':'not_in_public_bundle','extraction_status':row['extraction_status'],'notes':'；'.join(notes),'publication_year':int(pub[:4]) if pub else None,'source_pdf_page':int(row['source_pdf_page']),'source_printed_page':row['source_printed_page'],'source_table':row['source_table'],'source_row':row['source_row'],'source_column':row['source_column'],'source_edition':row.get('source_edition')}
   records.append(record)
 # Local public resources, exact duplicates preserved in component ledger but removed from canonical observations.
 raw_map={}
 for p in (ROOT/'raw/official-local').glob('catalog-*/resource-*.metadata.json'):
  meta=json.loads(p.read_text())
  if meta.get('source_sha256') and meta.get('raw_path'):raw_map[(meta.get('source_download_url'),meta['source_sha256'])]=meta['raw_path']
 local_input=read(ROOT/'derived/local_historical_long.csv');duplicates=0
 for row in local_input:
  if row.get('duplicate_of'):duplicates+=1;continue
  yr=period_year(row['period_effective']);source='local-'+h(row['source_download_url'])[:16];metric_key=row['metric_group_raw']+'|'+row['metric_raw']+'|'+row['unit_raw'];sid='local-series-'+h(row['county']+'|'+metric_key)[:18];v,status,local_unit,parse_rule=parse_local_value(row['value_raw'],row['unit_raw'] or None);periodicity=row['periodicity_raw'];period=row['period_effective'];scope='municipal_library_institution' if row['facility_raw'] else 'county_official_table'
  identity='|'.join(str(row.get(k,'')) for k in ['source_download_url','period_effective','county','geography_code_raw','district_code_raw','facility_raw','metric_group_raw','metric_raw','unit_raw'])
  path=raw_map.get((row['source_download_url'],row['source_sha256']))
  if not path:raise ValueError('Local snapshot mapping absent '+row['source_id'])
  notes=['原資料週期：'+(periodicity or '未標示')+'；原期間：'+period+'；期間依據：'+row['period_effective_basis'],'同年度月報與年報、縣市與分館資料不能直接加總。']
  if row['period_effective_basis']!='observation_field':notes.append('檔內未提供完整期間，以明列資源名稱辨識；未推定各數值的精確起訖日。')
  record={**base_record(),'observation_id':'obs-'+h(identity)[:22],'data_year':yr,'geography':row['county'],'geographic_scope':scope,'population_scope':row['source_title'],'facility':row['facility_raw'] or None,'geography_code_raw':row['geography_code_raw'],'district_code_raw':row['district_code_raw'],'series_id':sid,'indicator':row['metric_raw'],'indicator_group':row['metric_group_raw'],'source_field':row['metric_raw'],'value':v,'raw_value':row['value_raw'],'value_status':status,'zero_interpretation':'source_returned_zero_true_zero_or_uncollected_unconfirmed' if v==0 else None,'unit':local_unit,'value_parse_rule':parse_rule,'unit_status':'source_table_or_explicit_suffix' if local_unit else 'unconfirmed','temporal_kind':'source_period_'+periodicity,'period_start':None,'period_end':None,'period_raw':row['period_raw'],'period_effective':period,'periodicity_raw':periodicity,'period_basis':row['period_effective_basis'],'definition_id':'def-'+sid,'definition_status':'source_label_only','source_id':source,'source_family':'地方政府開放歷史表','source_url':row['source_download_url'],'source_page_url':row['source_url'],'source_locator':row['source_locator']+'; metric='+row['metric_raw'],'source_sha256':row['source_sha256'],'source_snapshot_path':path,'retrieved_at':row['source_retrieved_at'],'license_status':'OGDL-1.0_explicit_local_catalog','license_url':row['license_url'],'snapshot_distribution':'included','notes':'；'.join(notes),'component_source_id':row['source_id'],'source_record_id':row['record_id']}
  flag=arithmetic_flags.get((row['source_id'],period,row['facility_raw'],row['metric_raw']))
  record['quality_flags']='source_arithmetic_inconsistency' if flag else None
  if flag:record['notes']+='；來源合計欄與借閱、續借分項不一致，保留來源原值；詳derived/local_historical_quality.json。'
  if status=='unparsed':issues.append({'observation_id':record['observation_id'],'issue':'unparsed_local_value','raw_value':row['value_raw']})
  records.append(record)
 # Independent county-count system: official reorganized boundaries and a broader library population.
 for row in read(ROOT/'derived/dgbas_county_historical_long.csv'):
  yr=int(row['data_year']);source=row['source_id'];sid=source+'-'+row['metric_id'];v,status=parse_number(row['value'])
  if row['value_status']=='not_available_in_source':v=None;status='not_available_in_source'
  records.append({**base_record(),'observation_id':'obs-'+h(source+'|'+str(yr)+'|'+row['area_code_raw'])[:22],'data_year':yr,'geography':row['entity_raw'],'area_code_raw':row['area_code_raw'],'source_table_row':row['source_table_row'],'source_table_column':row['source_table_column'],'geographic_scope':'national_total' if row['entity_kind']=='national_total' else 'county_official_reorganized','geography_vintage':row['geography_vintage'],'national_libraries_scope':row['national_libraries_scope'],'population_scope':row['population_scope'],'series_id':sid,'indicator':row['metric_raw'],'indicator_group':'主計總處縣市公共館數','source_field':row['metric_raw'],'value':v,'raw_value':row['value_raw'],'value_status':status,'zero_interpretation':'source_reported_zero_context_unconfirmed' if v==0 else None,'unit':row['unit'],'unit_status':'source_label','temporal_kind':row['temporal_kind'],'period_raw':row['period_raw'],'period_start':None,'period_end':None,'periodicity_raw':'年','period_basis':'official_annual_selector_stock_date_unconfirmed','definition_id':'def-'+sid,'definition_status':'official_indicator_definition_current_historical_applicability_not_independently_certified','source_id':source,'source_family':'主計總處縣市公共館數','public_evidence_path':'raw/segis-history/dgbas_county_original_cells.json','source_url':row['source_download_url'],'source_page_url':row['source_url'],'source_method':row['source_method'],'source_request':row['source_request'],'source_locator':row['source_locator'],'source_sha256':row['source_sha256'],'source_snapshot_path':row['source_local_path'],'retrieved_at':row['source_retrieved_at'],'license_status':row['license_status'],'license_url':row['license_url'],'license_scope_inference':row['license_scope_inference']=='True','snapshot_distribution':'not_in_public_bundle','extraction_status':row['extraction_status'],'comparability':row['comparability'],'notes':row['population_scope']+'；'+row['geography_vintage']+'；'+row['license_scope_note']+'；1998–2005來源明示缺值，有數值範圍為2006–2025，不能與國資圖不同母體的館數直接互補。'})
 ids=[r['observation_id'] for r in records]
 if len(ids)!=len(set(ids)):raise ValueError('Component semantic key collision: review before exporting')
 checked_hashes={}
 for row in records:
  p=ROOT/row['source_snapshot_path']
  if str(p) not in checked_hashes:checked_hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
  if checked_hashes[str(p)]!=row['source_sha256']:raise ValueError('Component snapshot mismatch')
 with (ROOT/'data/component_records.jsonl').open('w') as f:
  for r in records:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
 (ROOT/'data/component_quality.json').write_text(json.dumps({'records':len(records),'local_duplicate_observations_excluded':duplicates,'issues':issues},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'records':len(records),'local_duplicate_observations_excluded':duplicates,'issues':len(issues)},ensure_ascii=False))
if __name__=='__main__':main()
