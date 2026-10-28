#!/usr/bin/env python3
"""Registered source selection, independent from permission to compare years."""
from __future__ import annotations
import gzip,hashlib,json,re
from collections import defaultdict
from pathlib import Path
import phase2_engine as p2
ROOT=Path(__file__).resolve().parents[1]
MISSING=object()
VALUE_ONLY_REASONS={'original_value_missing_marker_or_unresolved_do_not_impute','original_display_vs_typed_numeric_conflict'}
SELECTED={'selected_source_fact','selected_source_missing','selected_source_unusable'}
def stable(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def hashed(x):return hashlib.sha256(stable(x).encode()).hexdigest()
def load_annotations(root=ROOT):
 with gzip.open(Path(root)/'derived/phase2/annotations.jsonl.gz','rt',encoding='utf-8') as f:return [json.loads(x) for x in f]
def load_policy(root=ROOT):
 root=Path(root);policy=json.loads((root/'docs/phase3-profiles.json').read_text())
 if not policy.get('evidence_bindings'):raise ValueError('Selection policy lacks reviewed phase2 evidence content versions')
 policy['_current_evidence_digests']={c['evidence_id']:hashed(c) for c in (json.loads(x) for x in (root/'derived/phase2/evidence_cards.jsonl').read_text().splitlines())}
 return policy
def source_maps(policy):
 current=policy.get('_current_evidence_digests');bound=policy.get('evidence_bindings',{})
 exact={}
 for c in policy['reviewed_sources']:
  ids=[eid for eid in c['evidence_ids'] if current is None or current.get(eid) is not None and current.get(eid)==bound.get(eid)]
  exact[(c['layer'],c['source_id'],c['source_sha256'])]={**c,'evidence_ids':ids}
 ids={(c['layer'],c['source_id']):c for c in policy['reviewed_sources']}
 return exact,ids
def reviewed(a,exact):
 c=exact.get((a['layer'],a['source_id'],a['source_sha256']))
 return bool(c and a['evidence_id'] in c['evidence_ids'])
def matches(a,profile,contexts):
 f=profile['candidate_filter'];fac=a['facets']
 if f.get('layer') and a['layer']!=f['layer']:return False
 if 'source_ids' in f and a['source_id'] not in f['source_ids']:return False
 if f.get('source_id_regex') and not re.fullmatch(f['source_id_regex'],a['source_id']):return False
 if f.get('source_family') and contexts.get((a['layer'],a['source_id']),{}).get('source_family')!=f['source_family']:return False
 if 'geo_in' in f and fac.get('geographic_scope') not in f['geo_in']:return False
 if f.get('geo_prefix') and not str(fac.get('geographic_scope','')).startswith(f['geo_prefix']):return False
 if 'entity_in' in f and fac.get('entity') not in f['entity_in']:return False
 if 'indicators' in f and a['raw_indicator'] not in f['indicators']:return False
 return True
def route_records(annotations,policy):
 exact,contexts=source_maps(policy);out=[]
 for a in annotations:
  ids=[p['id'] for p in policy['profiles'] if matches(a,p,contexts)];ok=reviewed(a,exact)
  fields=('record_key','layer','observation_id','source_id','source_sha256','source_url','source_locator','source_version_id','evidence_id','raw_value','original_value','value_status','comparison_status','comparison_unit','comparison_year','comparison_month','comparison_group_id','quality_flags_original')
  out.append({**{k:a[k] for k in fields},'zero_interpretation':a.get('zero_interpretation'),'source_version_reviewed':ok,'route_id':ids[0] if ids else 'no_registered_default','candidate_profile_ids':ids,'route_status':'unreviewed_source_version' if not ok else 'registered_profile_candidate' if ids else 'no_default_profile_for_original_scope','reason_codes':[] if ok and ids else ['source_or_evidence_version_requires_policy_review'] if not ok else ['original_scope_not_covered_by_a_registered_default_question']})
 return sorted(out,key=lambda x:x['record_key'])
def valid_year(x):return isinstance(x,int) and not isinstance(x,bool) and 1000<=x<=9999
def eligibility(a,p,exact):
 reasons=[]
 if not reviewed(a,exact):return 'blocked_source_version',['source_or_evidence_version_requires_policy_review']
 fac=a['facets'];geo=str(fac.get('geographic_scope') or '')
 if any(x in geo for x in ('uncertain','unresolved','ambiguous')):return 'blocked_scope',['original_geography_or_entity_unresolved']
 if p.get('required_geo') and geo not in p['required_geo']:return 'blocked_scope',['original_scope_is_not_the_requested_full_county_quantity']
 if a['measure_class'] in p.get('exclude_measures',[]):return 'blocked_scope',['ratio_or_derived_measure_not_original_quantity']
 period=p['period_requirement'];kind=a['period_kind']
 if period not in ('programme','original') and not valid_year(a['comparison_year']):return 'blocked_period',['formal_source_year_unknown_or_conflicting']
 if period=='monthly' and (kind!='monthly_source_statistic' or not isinstance(a['comparison_month'],int) or isinstance(a['comparison_month'],bool) or not 1<=a['comparison_month']<=12):return 'blocked_period',['formal_month_unknown_or_not_a_monthly_observation']
 if period=='annual' and (kind.startswith('monthly') or kind in ('unresolved','partial_year_source','programme_not_annual')):return 'blocked_period',['original_period_not_verified_as_an_annual_reference']
 if period=='programme' and a['layer']!='programme_quantities':return 'blocked_scope',['not_an_original_programme_quantity']
 expected=p.get('expected_units')
 if expected and a['comparison_unit'] not in expected and a['comparison_unit'] is not None:return 'blocked_scope',['original_unit_differs_from_requested_measure']
 return None,reasons
def period_index(a):
 y=a['comparison_year'];m=a['comparison_month']
 if not valid_year(y):return None
 if a['period_kind']=='monthly_source_statistic':
  return y*12+m-1 if isinstance(m,int) and not isinstance(m,bool) and 1<=m<=12 else None
 if a['comparison_month'] is not None or a['period_kind'] in ('unresolved','partial_year_source','programme_not_annual','monthly_reference_month_unresolved'):return None
 return y
def trend_semantic_reasons(a):
 return [r for r in a['reasons'] if r not in VALUE_ONLY_REASONS]
def bundle_id(a):return a['source_id']+'@'+a['source_sha256']+'|'+a['evidence_id']
def rank_bundle(items,profile):
 priorities=profile.get('priority_source_ids')
 if priorities:
  sid=items[0]['source_id']
  return len(priorities)-priorities.index(sid) if sid in priorities else None
 values={str(a['source_edition_raw']) for a in items}
 if len(values)!=1 or not re.fullmatch('[0-9]{1,4}',next(iter(values))):return None
 return int(next(iter(values)))
def decision(a,p,policy,status,reasons):
 selected=status in SELECTED;semantic=trend_semantic_reasons(a)
 usable=selected and a['comparison_value'] is not None and a['comparison_unit'] is not None and not semantic
 if a['layer']=='programme_quantities':usable=False
 return {'decision_id':'selection-'+hashed([p['id'],a['record_key']])[:24],'profile_id':p['id'],'policy_version':policy['policy_version'],'record_key':a['record_key'],'layer':a['layer'],'observation_id':a['observation_id'],'source_id':a['source_id'],'source_sha256':a['source_sha256'],'source_url':a['source_url'],'source_locator':a['source_locator'],'source_version_id':a['source_version_id'],'evidence_id':a['evidence_id'],'selection_status':status,'selection_reasons':sorted(set(reasons)),'source_bundle_id':bundle_id(a),'source_edition_raw':a['source_edition_raw'],'raw_indicator':a['raw_indicator'],'entity':a['facets'].get('entity'),'facility_or_reader_category':a['facets'].get('facility_or_reader_category'),'original_value':a['original_value'],'raw_value':a['raw_value'],'unit_raw_preserved':a['unit_raw_preserved'],'value_status':a['value_status'],'point_value':a['comparison_value'] if usable else None,'point_unit':a['comparison_unit'],'period_year':a['comparison_year'],'period_month':a['comparison_month'],'period_kind':a['period_kind'],'comparison_status':a['comparison_status'],'comparison_group_id':a['comparison_group_id'],'definition_signature':a['definition_signature'],'quality_flags_original':a['quality_flags_original'],'facets':a['facets'],'selected':selected,'source_version_reviewed':not status=='blocked_source_version','join_segment_id':a['comparison_group_id'] if usable and a['comparison_status']=='published_panel_limited' else None}
def edges_for(decisions,annotations):
 by_key={a['record_key']:a for a in annotations};groups=defaultdict(list);out=[]
 for d in decisions:
  if d['selected'] and period_index(by_key[d['record_key']]) is not None:groups[(d['profile_id'],d['comparison_group_id'])].append(d)
 for (pid,gid),items in sorted(groups.items()):
  items=sorted(items,key=lambda d:(period_index(by_key[d['record_key']]) is None,period_index(by_key[d['record_key']]) or 0,d['record_key']))
  for left,right in zip(items,items[1:]):
   a,b=by_key[left['record_key']],by_key[right['record_key']];i,j=period_index(a),period_index(b)
   adjacent=i is not None and j is not None and j==i+1 and a['period_kind']==b['period_kind']
   result=p2.compare(a,b);drawable=adjacent and result['status']=='published_panel_limited'
   reasons=result['reasons']+([] if adjacent else ['calendar_periods_not_adjacent_do_not_bridge_gaps'])
   out.append({'edge_id':'edge-'+hashed([pid,a['record_key'],b['record_key']])[:24],'profile_id':pid,'left_record_key':a['record_key'],'right_record_key':b['record_key'],'comparison_group_id':gid,'drawable':drawable,'comparison_status':result['status'] if adjacent else 'unresolved','reasons':sorted(set(reasons)),'period_left':[a['comparison_year'],a['comparison_month']],'period_right':[b['comparison_year'],b['comparison_month']]})
 return out
def facet_value(a,key):
 value=a['facets']
 for part in key.split('.'):
  if not isinstance(value,dict) or part not in value:return MISSING
  value=value[part]
 return value
def facet_matches(a,key,value):
 actual=facet_value(a,key)
 return actual is not MISSING and stable(actual)==stable(value)
def select(policy,annotations,profile_id,*,purpose=None,start_year=None,end_year=None,entity=None,metric=None,source_id=None,month=None,facility=None,facets=None):
 profiles={p['id']:p for p in policy['profiles']}
 if profile_id not in profiles:raise ValueError('Unknown registered profile')
 p=profiles[profile_id];purpose=purpose or p['default_purpose']
 if purpose not in ('source-facts','trend'):raise ValueError('Unsupported purpose')
 for y in (start_year,end_year):
  if y is not None and not valid_year(y):raise ValueError('Invalid requested year')
 if start_year is not None and end_year is not None and start_year>end_year:raise ValueError('Requested years are reversed')
 if month is not None and (not isinstance(month,int) or isinstance(month,bool) or not 1<=month<=12):raise ValueError('Invalid requested month')
 if month is not None and p['period_requirement']!='monthly':raise ValueError('Month filter is not supported by this annual/programme question')
 if p['period_requirement']=='programme' and any(x is not None for x in (start_year,end_year,month)):raise ValueError('Programme quantities are not annual/monthly observations')
 exact,contexts=source_maps(policy);all_candidates=[a for a in annotations if matches(a,p,contexts)]
 facets=facets or {}
 for key in facets:
  if not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?',key):raise ValueError('Invalid original facet filter')
  if all_candidates and not any(facet_value(a,key) is not MISSING for a in all_candidates):raise ValueError('Unknown original facet filter')
 candidates=[a for a in all_candidates if (entity is None or a['facets'].get('entity')==entity) and (facility is None or a['facets'].get('facility_or_reader_category')==facility) and (metric is None or a['raw_indicator']==metric) and (source_id is None or a['source_id']==source_id) and all(facet_matches(a,k,v) for k,v in facets.items())]
 restrictions=[]
 if purpose not in p.get('supported_purposes',['source-facts','trend']):restrictions.append('purpose_not_supported_for_original_source_scope')
 if purpose=='trend' and p.get('require_metric_for_trend') and metric is None:restrictions.append('select_one_original_metric_before_a_historical_trend')
 groups=defaultdict(list)
 for a in candidates:groups[bundle_id(a)].append(a)
 chosen=set();bundle_reasons={};ranks={};requested_years=set(range(start_year,end_year+1)) if start_year is not None and end_year is not None else None
 if p['selection_mode']=='latest_original_panel' and not restrictions:
  if any(not reviewed(a,exact) for a in candidates):restrictions.append('new_source_or_evidence_version_requires_policy_review_before_latest_selection')
  qualified=[]
  for bid,items in groups.items():
   rank=rank_bundle(items,p);ranks[bid]=rank;reasons=[]
   if rank is None:reasons.append('source_edition_priority_unknown')
   years={a['comparison_year'] for a in items if valid_year(a['comparison_year'])}
   if requested_years is not None and not requested_years<=years:reasons.append('requested_year_range_not_covered_by_this_original_panel')
   elif start_year is not None and end_year is None and (not years or min(years)>start_year):reasons.append('requested_start_not_covered_by_original_panel')
   elif end_year is not None and start_year is None and (not years or max(years)<end_year):reasons.append('requested_end_not_covered_by_original_panel')
   supported_panel_keys=set(policy.get('reviewed_panel_record_keys',[]))
   for a in items:
    status,why=eligibility(a,p,exact)
    if status:reasons.extend(why)
    if purpose=='trend':
     reasons.extend(trend_semantic_reasons(a))
     if a['record_key'] not in supported_panel_keys:reasons.append('original_panel_definition_not_qualified_for_trend')
   bundle_reasons[bid]=sorted(set(reasons))
   if not reasons:qualified.append(bid)
  if qualified and not restrictions:
   best=max(ranks[b] for b in qualified);winners=[b for b in qualified if ranks[b]==best]
   if len(winners)==1:chosen=set(winners)
   else:restrictions.append('equal_priority_distinct_original_panels_remain_ambiguous')
  elif not restrictions:restrictions.append('no_single_qualified_original_panel_covers_requested_scope')
 elif not restrictions:chosen=set(groups)
 decisions=[]
 for a in candidates:
  bid=bundle_id(a);blocked,why=eligibility(a,p,exact)
  within=(start_year is None or valid_year(a['comparison_year']) and a['comparison_year']>=start_year) and (end_year is None or valid_year(a['comparison_year']) and a['comparison_year']<=end_year) and (month is None or a['comparison_month']==month)
  if blocked:status,reasons=blocked,why
  elif not within:status,reasons='blocked_period',['outside_explicitly_requested_period']
  elif restrictions:
   if any('ambiguous' in x for x in restrictions):status='ambiguous_priority'
   elif any('requires_policy_review' in x for x in restrictions):status='policy_review_required'
   elif any('select_one_original_metric' in x for x in restrictions):status='query_requires_explicit_scope'
   elif any('purpose_not_supported' in x for x in restrictions):status='blocked_scope'
   elif requested_years and not any(requested_years<={r['comparison_year'] for r in rows if valid_year(r['comparison_year'])} for rows in groups.values()):status='range_not_covered_by_one_panel'
   else:status='no_qualified_original_panel'
   reasons=restrictions+bundle_reasons.get(bid,[])
  elif bid not in chosen:status,reasons='alternative_source_version',bundle_reasons.get(bid,[])+['another_original_panel_selected_by_explicit_purpose_policy']
  else:
   semantic=trend_semantic_reasons(a)
   status='selected_source_unusable' if a['value_status']=='source_display_typed_value_conflict_unresolved' else 'selected_source_missing' if a['original_value'] is None else 'selected_source_unusable' if semantic or a['comparison_value'] is None or a['layer']=='programme_quantities' else 'selected_source_fact'
   reasons=['original_record_selected_no_imputation_or_aggregation']+a['reasons']
   if p['selection_mode']=='latest_original_panel':reasons+=['edition_preference_is_curator_policy_not_official_correction']
   if a['comparison_status']=='source_series_only':reasons+=['original_period_fact_only_historical_comparability_unproven']
  d=decision(a,p,policy,status,reasons);d['source_version_reviewed']=reviewed(a,exact);d['zero_interpretation']=a.get('zero_interpretation');decisions.append(d)
 decisions.sort(key=lambda d:d['record_key']);selected=[d for d in decisions if d['selected']];years=sorted({d['period_year'] for d in selected if valid_year(d['period_year'])})
 coverage=requested_years
 if coverage is None and p.get('default_coverage_years'):coverage=set(range(p['default_coverage_years'][0],p['default_coverage_years'][1]+1))
 gaps=sorted((coverage or set())-set(years));limits=any(d['selection_status']!='selected_source_fact' or d['comparison_status']!='published_panel_limited' for d in selected)
 yearly=[]
 for year in years:
  rows=[d for d in selected if d['period_year']==year];yearly.append({'year':year,'original_positions':len(rows),'numeric_point_values':sum(d['point_value'] is not None for d in rows),'source_missing':sum(d['selection_status']=='selected_source_missing' for d in rows),'source_unusable':sum(d['selection_status']=='selected_source_unusable' for d in rows)})
 query={'profile_id':p['id'],'title':p['title'],'policy_version':policy['policy_version'],'default_purpose':p['default_purpose'],'requested_purpose':purpose,'selection_status':'unresolved' if restrictions else 'no_matching_record_in_reviewed_snapshot' if not selected else 'selected_with_limits' if limits or gaps else 'selected_original_scope','selection_explanation':restrictions or [p['priority_rule'],'Source selection is not independent certification of original reporting or historical comparability.'],'requested_filters':{'start_year':start_year,'end_year':end_year,'entity':entity,'metric':metric,'source_id':source_id,'month':month,'facility':facility,'facets':facets},'selected_source_bundle_ids':sorted({d['source_bundle_id'] for d in selected}),'candidate_source_bundle_ids':sorted(groups),'selected_record_keys':[d['record_key'] for d in selected],'selected_records':len(selected),'candidate_records':len(decisions),'alternative_records':sum(d['selection_status']=='alternative_source_version' for d in decisions),'blocked_records':sum(not d['selected'] and d['selection_status']!='alternative_source_version' for d in decisions),'period_coverage':{'selected_years':years,'year_counts':yearly,'uncovered_requested_or_default_years':gaps,'known_scope_gaps':p.get('known_scope_gaps',[]),'original_positions_are_not_numeric_completeness':True,'gap_meaning':'No matched original record under this exact reviewed question; not a claim that the agency published nothing.'},'sources':sorted({d['source_url'] for d in selected if d['source_url']}),'ranking_never_uses_numeric_values':True,'source_edition_ranks':ranks,'no_cross_source_splice':True}
 query['profile_scope_records']=len(all_candidates);query['excluded_by_explicit_entity_metric_source_facets']=len(all_candidates)-len(candidates)
 query['candidate_scope_statement']='Candidates are within the registered question and explicit filters; full routes/default decisions retain the other original records.'
 edges=edges_for(decisions,annotations);gids={d['comparison_group_id'] for d in selected};drawable=sum(e['drawable'] for e in edges)
 query['trend_summary']={'single_continuous_series':len(selected)>1 and len(gids)==1 and len(edges)==len(selected)-1 and drawable==len(edges),'selected_original_comparison_groups':len(gids),'drawable_edges':drawable,'blocked_candidate_edges':len(edges)-drawable,'selected_missing_or_unusable':sum(d['selection_status']!='selected_source_fact' for d in selected),'permission':'Only the explicit drawable edges; selection_status and period coverage do not certify global continuity.','historical_collection_method_invariance_certified':False}
 return {'query':query,'decisions':decisions,'edges':edges}
