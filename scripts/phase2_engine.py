#!/usr/bin/env python3
"""Evidence-qualified definitions; never overwrite or silently splice raw values."""
from __future__ import annotations
import calendar,datetime,hashlib,json,re
from collections import defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path
import record_io
ROOT=Path(__file__).resolve().parents[1]
LAYERS={'canonical':'data/combined/observations.jsonl','local_statistical_cells':'derived/phase1_local_sources_long.jsonl','programme_quantities':'derived/ncl_2005_programmes_long.jsonl'}
IGNORED_PUBLICATION_FIELDS={'snapshot_distribution','public_evidence_path','public_evidence_sha256','public_projection_policy','original_fields'}
EVIDENCE_FILES=('research/phase2-ncl-evidence.json','research/phase2-local-evidence.json','research/phase2-nlpi-evidence.json','research/phase2-discovered-evidence.json')
OPERATION_GUARDS={'sum':'No validated aggregation policy is supplied; totals/components, classifications and versions may overlap.','impute':'Unknown, missing and2012 original-quantity gaps must remain unknown.','infer-unique-people':'Visits/transactions/programme attendance are not independently deduplicated people.','recode-geography':'Original historical geography cannot be renamed or summed into current boundaries without a separate verified crosswalk.','coerce-zero':'Original markers, blanks and display/typed conflicts are not measured zero.','cross-source-splice':'Cross-source historical definition equivalence is not supplied by matching labels or numbers.'}
def guard_operation(operation):
 if operation in OPERATION_GUARDS:return {'status':'incompatible','requested_operation':operation,'reasons':[OPERATION_GUARDS[operation]],'data_modified':False}
 if operation!='join-time-series':return {'status':'unresolved','requested_operation':operation,'reasons':['Unsupported operation; only source-qualified same-entity time-series checking is implemented.'],'data_modified':False}
 return None
def stable(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(x):return hashlib.sha256(x).hexdigest()
def load_inputs(root=ROOT):
 for layer,path in LAYERS.items():
  rows=record_io.rows(root,path) if layer=='canonical' else (json.loads(x) for x in (root/path).read_text().splitlines())
  for row in rows:yield layer,row
def fingerprint(rows):return sha(stable([{k:v for k,v in r.items() if k not in IGNORED_PUBLICATION_FIELDS} for r in rows]).encode())
def flags(row):
 x=row.get('quality_flags')
 if isinstance(x,list):return x
 if not x:return []
 try:v=json.loads(x);return v if isinstance(v,list) else [str(v)]
 except (ValueError,TypeError):return [str(x)]
def geo_unresolved(r):
 s=' '.join(str(r.get(k) or '') for k in ('geographic_scope','entity_label_status'))
 return bool(re.search('uncertain|ambiguous|unresolved',s)) or any(re.search(r'(?:geograph\w*|county_label|entity_label).*?(?:uncertain|ambiguous|unresolved)',str(f)) for f in flags(r))
def evidence_cards(root=ROOT):
 result=[]
 for name in EVIDENCE_FILES:
  path=root/name
  if not path.is_file():raise FileNotFoundError('Definition evidence has not been reviewed: '+name)
  obj=json.loads(path.read_text());cards=obj.get('source_cards',obj.get('evidence_cards',obj.get('cards',[])))
  aliases={'canonical_quantitative':'canonical','canonical_local_history':'canonical','phase1_local_statistical_cells':'local_statistical_cells','phase1_programme_rows_and_quantities':'programme_quantities','phase1_programme_quantities':'programme_quantities'}
  for c in cards:result.append({**c,'layer':aliases.get(c.get('layer'),c.get('layer','canonical')),'evidence_register':name})
 return result
def card_index(cards):
 out={}
 for c in cards:
  if not c.get('evidence_id'):raise ValueError('Evidence card lacks stable ID')
  for oid in c.get('observation_ids',[]):
   key=(c.get('layer','canonical'),oid)
   if key in out:
    if out[key]['source_sha256']!=c['source_sha256'] or out[key]['source_id']!=c['source_id']:raise ValueError('Conflicting original-source evidence: '+str(key))
    out[key].setdefault('supporting_evidence_ids',[]).append(c['evidence_id'])
   else:out[key]=dict(c,supporting_evidence_ids=[])
 return out
def is_reviewed(card):
 value=card.get('reviewed_original')
 return value is True or isinstance(value,dict) and value.get('sha_verified') is True and bool(card.get('review_method'))
def support(card):
 x=card.get('supported_comparison_scope',{})
 return x if isinstance(x,dict) else {'status':'unresolved','note':x}
def raw_label(r):return str(r.get('indicator') or r.get('metric_raw') or r.get('source_field') or '')
def context(r):return ' '.join(str(r.get(k) or '') for k in ('indicator','metric_raw','indicator_group','source_field','source_column_path'))
def measure(r):
 s=context(r);label=raw_label(r);kind=str(r.get('temporal_kind') or '')
 if 'ratio' in kind or any(x in label for x in ('每人','每10萬','每十萬','利用率','成長率','借閱率','比率','比例','百分比')):return 'ratio_or_per_capita'
 if any(x in label for x in ('預算','決算')) or any(x in s for x in ('購書經費','購買圖書資料費','購置經費','acquisition_spending','acquisition_budget','acquisition_final_expenditure')):return 'financial'
 if any(x in label for x in ('借閱','外借','續借')):
  if any(x in label for x in ('人次','人數')):return 'circulation_people'
  return 'circulation_volumes'
 if any(x in label for x in ('還書','預約')):return 'other_circulation'
 if any(x in label for x in ('採購冊數','新書入庫','新增圖書','館藏增加量')):return 'collection_addition'
 if any(x in label for x in ('進館','入館','到館')):return 'in_person_visits'
 if any(x in label for x in ('人口','population')):return 'population'
 if any(x in s for x in ('人力','館員','專業人員','行政人員','技術人員','工讀','志工','員工')):return 'staff'
 if any(x in label for x in ('活動','說故事','影片欣賞','參加')):return 'programme_events_or_participants'
 if any(x in s for x in ('館藏','藏書','圖書資料收藏','非書資料收藏')) and not any(x in s for x in ('借閱','還書','購書','經費')):return 'collection_stock'
 if any(x in label for x in ('圖書館數','圖書館個數','館數','總館','分館','區館','服務站','巡迴車','家數','館舍間數')):return 'facilities'
 if any(x in label for x in ('面積','樓地板')):return 'area'
 if any(x in label for x in ('席位','座位','閱覽席')):return 'seats'
 return 'source_specific_measure'
def unit_info(r,layer,card):
 unit=r.get('unit');state=str(r.get('unit_status') or '')
 basis='original_normalized_unit_with_original_status';upgraded=False
 if unit in (None,'') and layer=='canonical' and r.get('source_family')=='地方政府開放歷史表' and is_reviewed(card):
  label=raw_label(r)
  if label.endswith('冊數'):unit='冊';basis='verified_original_field_literal_suffix_冊數';upgraded=True
  elif label.endswith('人次'):unit='人次';basis='verified_original_field_literal_suffix_人次';upgraded=True
 mixed=bool(unit and any(x in str(unit) for x in ('、','／','冊件','冊／件','冊、件','不含電子')))
 unresolved=(unit in (None,'') or mixed or any(x in state for x in ('unresolved','unconfirmed','mixed','no_uniform','not_uniform')) and not upgraded)
 # Source-label suffix is an explicit new layer, not an edit of canonical unit.
 if unresolved:return {'unit_raw_preserved':r.get('unit_raw') or r.get('unit'),'comparison_unit':None,'unit_scale':'1','unit_audit_status':'unresolved_or_mixed','unit_audit_basis':basis}
 aliases={'元':('新臺幣元','1'),'新臺幣元':('新臺幣元','1'),'千冊':('冊','1000'),'千人次':('人次','1000'),'千人':('人','1000'),'千元':('新臺幣元','1000')}
 normalized,scale=aliases.get(str(unit),(str(unit),'1'))
 return {'unit_raw_preserved':r.get('unit_raw') or r.get('unit'),'comparison_unit':normalized,'unit_scale':scale,'unit_audit_status':'literal_suffix_verified' if upgraded else 'original_unit_preserved','unit_audit_basis':basis if scale=='1' else 'exact_decimal_scale_from_explicit_original_unit; '+basis}
def period_info(r,layer,card):
 state=str(r.get('period_status') or '');basis=str(r.get('period_basis') or '');kind=str(r.get('temporal_kind') or '');year=r.get('data_year');month=None
 if r.get('source_location_kind')=='verified_original_cell' and 'week' in kind:
  return {'comparison_year':None,'comparison_month':None,'period_kind':'weekly_source_quantity','period_audit_status':'weekly_quantity_not_annual_total','period_audit_basis':basis}
 if r.get('source_location_kind')=='verified_original_cell' and basis=='literal_original_year_month' and is_reviewed(card):
  code=str(r.get('period_effective') or '')
  if re.fullmatch(r'[0-9]{4}-[0-9]{2}',code) and int(code[:4])==year and 1<=int(code[-2:])<=12:
   return {'comparison_year':year,'comparison_month':int(code[-2:]),'period_kind':'monthly_source_statistic','period_audit_status':'reviewed_literal_original_year_month','period_audit_basis':'Literal year/month in the reviewed original table; annual totals remain separate.'}
  return {'comparison_year':None,'comparison_month':None,'period_kind':'unresolved','period_audit_status':'invalid_original_year_month','period_audit_basis':basis}
 if layer=='programme_quantities':return {'comparison_year':None,'comparison_month':None,'period_kind':'programme_not_annual','period_audit_status':'programme_period_only','period_audit_basis':r.get('period_interpretation_basis') or r.get('time_reference')}
 if state in ('catalog_title_year_only_attachment_undated','source_sheet_name_header_period_conflict_unresolved'):
  return {'comparison_year':None,'comparison_month':None,'period_kind':'unresolved','period_audit_status':state,'period_audit_basis':basis}
 if layer=='local_statistical_cells':
  year=r.get('period_year');month=r.get('period_month')
  if state=='matching_sheet_name_and_header_month':return {'comparison_year':year,'comparison_month':month,'period_kind':'monthly_source_statistic','period_audit_status':'matching_original_sheet_and_header','period_audit_basis':basis}
  if state=='explicit_sheet_year':return {'comparison_year':year,'comparison_month':None,'period_kind':'annual_source_reference','period_audit_status':'explicit_original_sheet_year','period_audit_basis':basis}
 if any(x in basis+str(r.get('source_period_interpretation_status') or '') for x in ('unresolved','candidate')):
  return {'comparison_year':year,'comparison_month':None,'period_kind':'unresolved','period_audit_status':'unresolved_original_period','period_audit_basis':basis}
 if 'subperiod' in basis or any(x in kind for x in ('partial','subperiod','campaign')):
  return {'comparison_year':year,'comparison_month':None,'period_kind':'partial_year_source','period_audit_status':'subperiod_not_annual_total','period_audit_basis':basis}
 if r.get('source_family')=='地方政府開放歷史表':
  code=str(r.get('period_raw') or '')
  if basis=='observation_field' and re.fullmatch(r'[0-9]{5}',code) and 1<=int(code[-2:])<=12 and is_reviewed(card):
   year=int(code[:3])+1911;month=int(code[-2:]);return {'comparison_year':year,'comparison_month':month,'period_kind':'monthly_source_statistic','period_audit_status':'verified_original_statistical_year_month_code','period_audit_basis':'Strict five-digit original 統計年月; ROCyear+1911, month01–12; not title-derived.'}
  if basis=='observation_field' and '年度' in card.get('source_fields',[]) and re.fullmatch(r'[0-9]{3}',code) and is_reviewed(card):
   return {'comparison_year':int(code)+1911,'comparison_month':None,'period_kind':'annual_source_reference','period_audit_status':'verified_literal_original_年度_field','period_audit_basis':'Original field年度, exactly three ROCyear digits; does not apply to truncated 統計年月.'}
  if r.get('periodicity_raw')=='月' and basis=='observation_field' and is_reviewed(card):
   try:
    date=datetime.date.fromisoformat(code)
    return {'comparison_year':date.year,'comparison_month':date.month,'period_kind':'monthly_source_statistic','period_audit_status':'original_monthly_period_label_and_ISO_date_field','period_audit_basis':'Original period explicitly月; date field supplies year/month only, no invented day-level coverage.'}
   except ValueError:pass
  if r.get('periodicity_raw')=='月':return {'comparison_year':year,'comparison_month':None,'period_kind':'monthly_reference_month_unresolved','period_audit_status':'original_monthly_label_exact_month_unresolved','period_audit_basis':basis}
  if r.get('periodicity_raw')=='年':return {'comparison_year':year,'comparison_month':None,'period_kind':'annual_source_reference','period_audit_status':'original_annual_label','period_audit_basis':basis}
  return {'comparison_year':year,'comparison_month':None,'period_kind':'unresolved','period_audit_status':'source_period_not_verified','period_audit_basis':basis}
 if 'ratio' in kind:return {'comparison_year':year,'comparison_month':None,'period_kind':'source_ratio_period','period_audit_status':'read_original_ratio_window_and_denominator','period_audit_basis':basis}
 if 'current_general_rule' in basis:return {'comparison_year':year,'comparison_month':None,'period_kind':'annual_reference_current_definition_only','period_audit_status':'historical_effective_dates_not_confirmed','period_audit_basis':basis}
 if kind=='annual_financial':p='annual_financial_source'
 elif 'flow' in kind:p='annual_flow_source'
 elif 'stock' in kind:p='year_end_stock_explicit' if basis=='source_year_end_explicit_in_chapter' else 'annual_stock_reference_exact_date_unconfirmed'
 else:p='annual_source_reference'
 return {'comparison_year':year,'comparison_month':None,'period_kind':p,'period_audit_status':'original_reference_year; exact timing only when explicit','period_audit_basis':basis}
def policy_for(r,card):
 """Field/year-specific exclusions must be explicit source evidence, never fuzzy labels."""
 rules=card.get('field_policies',card.get('field_breaks',[]));result={'status':support(card).get('status','unresolved'),'segment':'source_panel','reasons':[]}
 for rule in support(card).get('field_rules',[]):
  if r.get('observation_id') in rule.get('observation_ids',[]) and rule.get('comparison_status')=='published_panel_limited':result['status']='published_panel_limited'
 for rule in rules:
  sel=rule.get('selector',{})
  if rule.get('observation_ids'):
   if r.get('observation_id') not in rule['observation_ids']:continue
  elif not all(r.get({'series_ids':'series_id','indicators':'indicator','source_fields':'source_field'}.get(k,k)) in (v if isinstance(v,list) else [v]) for k,v in sel.items()):continue
  if rule.get('series_ids') and r.get('series_id') not in rule['series_ids']:continue
  if rule.get('indicators') and r.get('indicator') not in rule['indicators']:continue
  if rule.get('source_fields') and r.get('source_field') not in rule['source_fields']:continue
  year=r.get('data_year',r.get('period_year'))
  if year in rule.get('unresolved_years',[]):result.update(status='unresolved',segment='unresolved_year_'+str(year));result['reasons'].append(rule.get('reason','source_break_boundary_unresolved'))
  segments=rule.get('year_segments',[])
  if segments:
   matched=False
   for i,segment in enumerate(segments):
    years=segment.get('years',segment.get('data_years',[])) if isinstance(segment,dict) else segment
    if year in years:result['segment']=str(rule.get('rule_id','field_break'))+':'+str(i);matched=True
   if not matched:result.update(status='unresolved',segment='unresolved_outside_reviewed_segments');result['reasons'].append('outside_reviewed_source_year_segments')
  if rule.get('status') in ('unresolved','incompatible','source_series_only'):
   result['status']=rule['status']
   if rule['status']!='source_series_only':result['reasons'].append(rule.get('reason','field_definition_unresolved'))
 return result
def dimension_value(x):return '' if x in (None,'') else stable(x) if isinstance(x,(list,dict)) else str(x)
def annotate(layer,r,card):
 oid=r['observation_id'];label=raw_label(r);u=unit_info(r,layer,card);t=period_info(r,layer,card);policy=policy_for(r,card);s=context(r)
 material='electronic' if '電子' in s else 'mixed_or_nonbook_collection' if any(x in s for x in ('非書','冊、件','冊、種','冊/件')) else 'source_label_scope'
 finance='budget' if '預算' in s or 'budget' in str(r.get('indicator_group')) else 'final_expenditure' if '決算' in s or 'final_expenditure' in str(r.get('indicator_group')) else 'not_explicit'
 renewal='explicit_borrow_plus_renewal' if any(x in label for x in ('借閱及續借','借閱與續借','借閱暨續借')) else 'explicit_renewal_only' if '續借' in label else 'original_borrow_field_unspecified_renewal' if any(x in label for x in ('借閱','外借')) else 'not_applicable'
 entity=r.get('geography') or r.get('county_raw') or r.get('county') or ''
 facility=r.get('facility') or r.get('entity_raw') or ''
 dimensions={k:r.get(k) for k in ('age_group_raw','sex_raw','book_class_raw','source_header_hierarchy_raw','ownership_scope','source_response_notation_kind','source_subrow_label_status') if r.get(k) not in (None,'')}
 if layer=='local_statistical_cells':dimensions['row_classification_raw']=r.get('source_row_label_raw');dimensions['column_classification_raw']=r.get('source_column_path')
 measure_source=r.get('series_id') or r.get('metric_id') or r.get('metric_raw') or label
 if layer=='local_statistical_cells':measure_source=r.get('metric_raw')
 reviewed=is_reviewed(card);positive=policy['status']=='published_panel_limited' and reviewed
 reasons=list(policy['reasons'])
 if not reviewed:reasons.append('original_definition_not_reviewed_for_this_record')
 if not u['comparison_unit']:reasons.append('unit_unknown_conflicting_or_mixed')
 if geo_unresolved(r):reasons.append('original_geographic_identity_unresolved')
 if t['period_kind'] in ('unresolved','monthly_reference_month_unresolved'):reasons.append('original_period_unresolved')
 if not isinstance(t['comparison_year'],int) or isinstance(t['comparison_year'],bool) or not 1000<=t['comparison_year']<=9999:reasons.append('comparison_year_unknown_or_invalid')
 if t['period_kind']=='monthly_source_statistic' and (not isinstance(t['comparison_month'],int) or isinstance(t['comparison_month'],bool) or not 1<=t['comparison_month']<=12):reasons.append('comparison_month_unknown_or_invalid')
 if t['period_kind']=='partial_year_source':reasons.append('partial_year_period_not_annual_series')
 if layer=='programme_quantities':reasons.append('programme_not_annual_operational_quantity')
 if r.get('value') is None:reasons.append('original_value_missing_marker_or_unresolved_do_not_impute')
 if r.get('value_status')=='source_display_typed_value_conflict_unresolved':reasons.append('original_display_vs_typed_numeric_conflict')
 if policy['status']=='unresolved':reasons.append('source_definition_or_effective_year_unresolved')
 if policy['status']=='incompatible':reasons.append('explicit_source_definition_conflict')
 # Only a reviewed national panel may hold its own geography reference fixed.
 geo_key='same_reviewed_national_published_panel' if positive and entity=='全國' and r.get('geographic_scope')=='national_total' else r.get('geography_vintage')
 status='published_panel_limited' if positive and not reasons else 'unresolved' if reasons else 'source_series_only'
 number=None
 if r.get('value') is not None and u['comparison_unit']:
  try:number=format(Decimal(str(r['value']))*Decimal(u['unit_scale']),'f')
  except InvalidOperation:reasons.append('value_not_parseable_as_exact_decimal');status='unresolved'
 facets={'measure_source_key':measure_source,'measure_class':measure(r),'financial_mode':finance,'material_scope':material,'renewal_scope':renewal,'unit':u['comparison_unit'],'period_kind':t['period_kind'],'entity':entity,'facility_or_reader_category':facility,'geographic_scope':r.get('geographic_scope') or 'source_workbook_original_scope','geography_key':geo_key,'population_scope':r.get('population_scope') or r.get('source_title'),'national_libraries_scope':r.get('national_libraries_scope'),'aggregation_role':r.get('aggregation_role'),'institutional_level':r.get('institutional_level'),'classification_dimensions':dimensions,'source_segment':policy['segment']}
 # Grouping never crosses an edition/snapshot family. Chart year bodies share
 # their literal series ID but retain source_series_only, never a certified panel.
 scope_identity=r.get('source_id') if positive else r.get('series_id') or r.get('source_id')
 signature={'layer':layer,'source_scope':scope_identity,'reviewed_panel_or_grid':support(card).get('require_matching_grid_signature') or support(card).get('panel_id') or card['evidence_id'] if positive else None,'source_table':r.get('source_table'),'source_edition':r.get('source_edition') or r.get('source_edition_roc'),'facets':facets}
 group='comparison-'+sha(stable(signature).encode())[:24]
 return {'record_key':layer+':'+oid,'layer':layer,'observation_id':oid,'source_id':r['source_id'],'source_sha256':r['source_sha256'],'source_url':r.get('source_url') or r.get('source_download_url'),'source_locator':r['source_locator'],'source_version_id':r.get('source_version_id') or r['source_id']+'@sha256:'+r['source_sha256'],'source_edition_raw':r.get('source_edition') or r.get('source_edition_roc'),'source_retrieved_at':r.get('retrieved_at') or r.get('source_retrieved_at'),'source_license_status':r.get('license_status'),'source_license_url':r.get('license_url'),'evidence_id':card['evidence_id'],'supporting_evidence_ids':card.get('supporting_evidence_ids',[]),'raw_indicator':label,'raw_value':r.get('raw_value',r.get('value_raw')),'original_value':r.get('value'),'value_status':r.get('value_status'),'zero_interpretation':r.get('zero_interpretation') or ('source_reported_zero_not_certified_measured_zero' if number is not None and Decimal(number)==0 else None),'raw_geography_vintage':r.get('geography_vintage'),'raw_definition_status':r.get('definition_status'),'measure_class':facets['measure_class'],'comparison_status':status,'comparison_scope':'same_original_entity_time_series; source published panel only when explicitly reviewed','comparison_group_id':group,'definition_signature':sha(stable(signature).encode()),'comparison_value':number,'reasons':sorted(set(reasons)),'facets':facets,'quality_flags_original':flags(r),**u,**t}
def compare(left,right):
 """Decide whether two raw records can be joined into one time-series scope."""
 base={'left':left['record_key'],'right':right['record_key'],'comparison_goal':'same_original_entity_time_series','status':'unresolved','differences':[],'reasons':[],'caveat':'Limited published-panel use is not a claim that historical reporting definitions, response rates or collection methods were invariant.'}
 a,b=left['facets'],right['facets'];hard=[];soft=[]
 if left['record_key']==right['record_key']:base['reasons']=['same_record_is_not_an_independent_time_point'];return base
 for key in ('measure_class','financial_mode','renewal_scope','unit','period_kind','entity','facility_or_reader_category','geographic_scope','geography_key','population_scope','national_libraries_scope','aggregation_role','institutional_level','classification_dimensions','source_segment'):
  av,bv=a.get(key),b.get(key)
  if av==bv:continue
  base['differences'].append({'dimension':key,'left':av,'right':bv})
  if av in (None,'','not_explicit') or bv in (None,'','not_explicit'):soft.append('unknown_'+key)
  elif key in ('renewal_scope','institutional_level','geographic_scope','geography_key','population_scope','national_libraries_scope'):soft.append('unproven_equivalent_'+key)
  else:hard.append('different_'+key)
 if hard:base.update(status='incompatible',reasons=hard+soft);return base
 if left['comparison_year']==right['comparison_year'] and left['comparison_month']==right['comparison_month']:base['reasons']=['same_period_records_must_not_be_treated_as_successive_time_points'];return base
 if left['reasons'] or right['reasons']:base['reasons']=sorted(set(left['reasons']+right['reasons']+soft));return base
 if any(not isinstance(r['comparison_year'],int) or isinstance(r['comparison_year'],bool) or not 1000<=r['comparison_year']<=9999 for r in (left,right)):
  base['reasons']=['comparison_year_unknown_or_invalid'];return base
 if any(r['facets']['period_kind']=='monthly_source_statistic' and (not isinstance(r['comparison_month'],int) or isinstance(r['comparison_month'],bool) or not 1<=r['comparison_month']<=12) for r in (left,right)):
  base['reasons']=['comparison_month_unknown_or_invalid'];return base
 if soft:base['reasons']=soft;return base
 if left['comparison_group_id']!=right['comparison_group_id']:
  base['reasons']=['source_definition_edition_geography_or_population_scope_not_proven_equivalent'];return base
 if left['comparison_status']==right['comparison_status']=='published_panel_limited':
  base['status']='published_panel_limited';base['reasons']=['same_reviewed_official_panel_metric_unit_entity_period_and_segment'];return base
 base['reasons']=['same_labelled_source_series_but_historical_definition_not_certified'];return base
