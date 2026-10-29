#!/usr/bin/env python3
"""Explicit adapters: preserve original periods/scopes; never fuzzy-merge sources."""
import csv,hashlib,json,re
from pathlib import Path
import record_io
from library_pipeline import parse_number
from cohort_registry import csv_names,load as load_cohorts
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

def adapt_additional_ncl_rows(rows):
 result=[]
 for row in rows:
  year=int(row['data_year']);source=row['source_id'];series=source+'-'+row['metric_id'];geo=row['entity_raw'];raw=row['value_raw'];source_status=row.get('value_status','reported')
  if source_status in ('blank','source_blank','blank_in_source'):
   if str(raw).strip() or str(row.get('value','')).strip():raise ValueError('Blank cell carries a number')
   value,status=None,'source_blank'
  elif source_status=='source_marker' and raw in {'無','未新增','未統計'}:
   if row.get('value') not in (None,''):raise ValueError('Printed textual marker cannot discard a normalized number')
   value,status=None,'source_marker'
  elif source_status in ('not_available_in_source','missing','source_marker'):
   if row.get('value') not in (None,''):raise ValueError('Missing status would discard a normalized value: '+row['source_locator'])
   if str(raw).strip() not in {'-','—','–','…','...','N/A','NA'}:raise ValueError('Missing status would discard an unrecognized source value: '+row['source_locator'])
   value,status=None,'not_available_in_source'
  else:
   value,status=parse_number(row['value'])
   if value is None:raise ValueError('Unreviewed NCL numeric cell: '+row['source_locator'])
  unit=row.get('unit') or None;notes=[x for x in [row.get('scope_note'),row.get('source_note') or row.get('source_notes'),row.get('notes'),row.get('time_reference')] if x]
  if unit and ('混合' in unit or '件/種/冊' in unit or '原表未列' in unit):notes.append('原表單位狀態：'+unit+'；未有統一可計算單位，不視為純圖書冊數。');unit=None
  if row.get('unit_status')=='source_heading_conflict_unresolved':
   notes.append('原刊表題與正文單位衝突，正式unit留空；候選解讀另存，未當作定論。');unit=None
  unit_status=row.get('unit_status') or (('inferred_from_context' if row.get('unit_basis') and not row.get('unit_raw') else 'source_table') if unit else 'source_unit_unconfirmed_or_mixed')
  if status=='source_marker' and raw in {'無','未新增','未統計'}:notes.append('原刊此格印「'+raw+'」，保留原印文字狀態；不自行換算0或推定缺值原因。')
  if status=='source_blank':notes.append('原刊此格留白；保留為缺值，不推定為0或不適用。')
  if row.get('source_cell_note_raw'):notes.append('原格補述：'+row['source_cell_note_raw'])
  if row.get('aggregation_role') in ('total','subtotal','row_total','grand_total','published_total'):notes.append('原表合計／小計可能與分項重疊，不可把全部格相加。')
  period=row['temporal_kind'];pub=row.get('publication_date') or None
  explicit_subperiod=bool(row.get('source_subrow_label_raw') and row.get('period_start') and row.get('period_end'))
  ambiguous_subperiod=explicit_subperiod and row.get('source_period_interpretation_status')=='printed_extra_slash_unresolved_candidate_dates'
  extras={k:row[k] for k in ('ownership_scope','source_row_label_raw','source_parent_row_label_raw','source_row_hierarchy_raw','source_unit_context_locator','source_original_survey_date_raw','source_survey_population_libraries','source_original_table_row','source_subrow_sequence','source_subrow_label_status','source_response_notation_kind','source_parenthetical_raw','source_parent_row_label_english_raw','source_row_label_english_raw','source_original_physical_column','source_cell_note_raw','source_cell_note_status','source_subrow_label_raw','source_period_interpretation_status','copyright_publication_month','publication_entry_date','source_data_obtained_date_raw','entity_label_status') if row.get(k) not in (None,'')}
  if ambiguous_subperiod:extras.update(period_start_candidate=row['period_start'],period_end_candidate=row['period_end'])
  result.append({**base_record(),'observation_id':'obs-'+h(source+'|'+row['metric_id']+'|'+geo+'|'+str(year)+('|' + row['observation_identity_suffix'] if row.get('observation_identity_suffix') else ''))[:22],
   'data_year':year,'geography':geo,'geography_contextual_name':row.get('entity_contextual_name',geo),'geographic_scope':row['entity_kind'],
   'geography_vintage':row.get('geography_vintage'),'national_libraries_scope':row.get('national_libraries_scope'),
   'population_scope':row.get('population_scope') or row.get('scope_note') or '依原表列示的公共圖書館母體，未自行合併館類',
   'series_id':series,'indicator':row['metric_raw'],'indicator_group':row.get('source_family') or '國家圖書館年鑑統計事實','source_field':row.get('source_column_path') or row['metric_raw'],
   'value':value,'raw_value':raw,'value_status':status,'zero_interpretation':'source_reported_zero_historical_context_required' if value==0 else None,
   'unit':unit,'unit_raw':row.get('unit_raw'),'unit_basis':row.get('unit_basis'),'unit_status':unit_status,'temporal_kind':period,
   'period_start':None if ambiguous_subperiod else row['period_start'] if explicit_subperiod else f'{year}-01-01' if period in {'flow_calendar_year','annual_financial'} else None,'period_end':None if ambiguous_subperiod else row['period_end'] if explicit_subperiod else f'{year}-12-31' if period in {'flow_calendar_year','annual_financial','stock_year_end'} else None,
   'period_basis':'source_row_date_punctuation_unresolved_candidate_dates_only' if ambiguous_subperiod else 'source_row_subperiod_interpreted_dates_original_label_retained' if explicit_subperiod else 'source_calendar_year_flow' if period in {'flow_calendar_year','annual_financial'} else 'source_year_end_explicit_in_chapter' if period=='stock_year_end' else 'source_reference_year_exact_date_unconfirmed',
   'period_raw':row.get('period_raw') if explicit_subperiod else row.get('source_comparison_period_raw') or str(year),'source_time_reference':row.get('time_reference'),'definition_id':'def-'+series,'definition_status':'original_table_heading_and_footnotes_preserved',
   'institutional_level':row.get('institutional_level'),'aggregation_role':row.get('aggregation_role'),
   'source_id':source,'source_family':row.get('source_family') or '國家圖書館年鑑統計事實','source_url':row['source_download_url']+'#page='+row['source_pdf_page'],
   'source_page_url':row['source_url'],'source_locator':row['source_locator'],'source_sha256':row['source_sha256'],
   'source_version_id':source+'@sha256:'+row['source_sha256'],'source_snapshot_path':row['source_local_path'],'retrieved_at':row['source_retrieved_at'],
   'source_pdf_page':int(row['source_pdf_page']),'source_printed_page':row['source_printed_page'],'source_table':row['source_table'],
   'source_table_title':row.get('source_table_title'),'source_row':row['source_row'],'source_column':row['source_column'],
   'source_column_path':row.get('source_column_path'),'source_cell_bbox':row.get('source_cell_bbox'),'source_cell_bboxes':row.get('source_cell_bboxes'),'source_cell_annotation':row.get('cell_annotation'),'original_source_note':row.get('source_note') or row.get('source_notes'),'source_footnotes_raw':row.get('source_footnotes_raw'),'source_footnotes_status':row.get('source_footnotes_status'),'value_qualifier':row.get('value_qualifier'),'value_parse_rule':row.get('value_parse_rule'),'source_location_kind':row.get('source_location_kind'),'observation_identity_suffix':row.get('observation_identity_suffix'),'source_unit_interpretation_basis':row.get('source_unit_interpretation_basis'),'unit_interpretation_candidate':row.get('unit_interpretation_candidate'),'book_class_raw':row.get('book_class_raw'),'age_group_raw':row.get('age_group_raw'),'sex_raw':row.get('sex_raw'),'source_data_year_raw':row.get('source_data_year_raw'),'source_original_access_date_raw':row.get('source_original_access_date_raw'),'source_original_access_date':row.get('source_original_access_date'),
   'license_status':'published_statistical_facts_document_license_unconfirmed','license_url':None,'snapshot_distribution':'not_in_public_bundle',
   'extraction_status':row['extraction_status'],'quality_flags':row.get('quality_flags') or None,'notes':'；'.join(notes),'publication_year':int(pub[:4]) if pub else None,
   'publication_date':pub,'publication_date_basis':row.get('publication_date_basis'),'source_edition':row.get('source_edition'),'source_edition_roc':row.get('source_edition_roc'),**extras})
 return result

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
   record={**base_record(),'observation_id':'obs-'+h(source+'|'+row['metric_id']+'|'+geo+'|'+str(yr))[:22],'data_year':yr,'geography':geo,'geography_contextual_name':row.get('entity_contextual_name',geo),'geographic_scope':row['entity_kind'],'geography_vintage':row.get('geography_vintage'),'national_libraries_scope':row.get('national_libraries_scope'),'population_scope':'公立公共圖書館，依各出版表母體與註腳','series_id':sid,'indicator':row['metric_raw'],'indicator_group':family,'source_field':row['metric_raw'],'value':v,'raw_value':row['value_raw'],'value_status':status,'zero_interpretation':'source_reported_zero_historical_context_required' if v==0 else None,'unit':unit,'unit_status':'source_table' if unit else 'mixed_not_uniform','temporal_kind':row['temporal_kind'],'period_start':f'{yr}-01-01' if row['temporal_kind']=='flow_calendar_year' else None,'period_end':f'{yr}-12-31','period_basis':'published_table_reference_year','definition_id':'def-'+sid,'definition_status':'original_table_heading_and_footnotes_preserved','source_id':source,'source_family':family,'source_url':row['source_download_url']+'#page='+row['source_pdf_page'],'source_page_url':row['source_url'],'source_locator':row['source_locator']+'; column '+row['source_column'],'source_sha256':row['source_sha256'],'source_snapshot_path':row['source_local_path'],'retrieved_at':row['source_retrieved_at'],'license_status':'OGDL-1.0_site_declaration' if source.startswith('dgbas') and row.get('license_status')=='verified_open' and row.get('license_code')=='OGDL-1.0_site_declaration' else 'published_statistical_facts_document_license_unconfirmed','license_url':'https://www.stat.gov.tw/cp.aspx?n=3164' if source.startswith('dgbas') else None,'snapshot_distribution':'not_in_public_bundle','extraction_status':row['extraction_status'],'quality_flags':row.get('quality_flags') or None,'notes':'；'.join(notes),'publication_year':int(pub[:4]) if pub else None,'source_pdf_page':int(row['source_pdf_page']),'source_printed_page':row['source_printed_page'],'source_table':row['source_table'],'source_row':row['source_row'],'source_column':row['source_column'],'source_edition':row.get('source_edition')}
   records.append(record)
 direct_groups=[g for g in (load_cohorts(ROOT) or []) if g.get('adapter_kind')=='canonical_observations_jsonl']
 direct_csvs={g['derived_csv'].removeprefix('derived/') for g in direct_groups}
 for additional in csv_names(ROOT,['ncl_gap_tables_long.csv','ncl_additional_years_long.csv','ncl_earlier_years_long.csv']):
  if additional in direct_csvs:continue
  records.extend(adapt_additional_ncl_rows(read(ROOT/'derived'/additional)))
 for group in direct_groups:
  name=group['canonical_jsonl']
  if name not in group['outputs']:raise ValueError('Canonical adapter input must be a reviewed output')
  records.extend(record_io.rows(ROOT,name))
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
 gap_metadata=ROOT/'raw/ncl-historical/gap-tables-metadata.json'
 if gap_metadata.exists():
  for table in json.loads(gap_metadata.read_text()).get('tables',[]):
   for check in table.get('validation_checks',[]):
    if check.get('passed') is not False:continue
    geo=check.get('entity','總計');metric=check['metric']
    matches=[r for r in records if r['source_id']==table['table_id'] and r['geography']==geo and r['series_id'].endswith('_'+metric)]
    if len(matches)!=1:raise ValueError('Source issue does not identify one original cell')
    r=matches[0];r['quality_flags']='source_arithmetic_inconsistency';r['notes']+='；原刊合計與可見分項計算不同，原值保留；詳原表metadata。'
    issues.append({'issue':'source_arithmetic_inconsistency','observation_id':r['observation_id'],'source_id':r['source_id'],'source_locator':r['source_locator'],'reported_value':r['value'],'calculated_from_visible_components':check['calculated'],'inference_not_applied_to_source_value':True})
 ids=[r['observation_id'] for r in records]
 if len(ids)!=len(set(ids)):raise ValueError('Component semantic key collision: review before exporting')
 checked_hashes={}
 for row in records:
  p=ROOT/row['source_snapshot_path']
  if str(p) not in checked_hashes:checked_hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
  if checked_hashes[str(p)]!=row['source_sha256']:raise ValueError('Component snapshot mismatch')
 from metadata_corrections import apply as apply_metadata_corrections
 metadata_changes=apply_metadata_corrections(records)
 metadata_path=ROOT/'derived/metadata-corrections-20261029.jsonl'
 metadata_path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in metadata_changes))
 record_io.write(ROOT,'data/component_records.jsonl',records)
 (ROOT/'data/component_quality.json').write_text(json.dumps({'records':len(records),'local_duplicate_observations_excluded':duplicates,'issues':issues},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'records':len(records),'local_duplicate_observations_excluded':duplicates,'issues':len(issues)},ensure_ascii=False))
if __name__=='__main__':main()
