#!/usr/bin/env python3
"""Independent offline transport/source-preservation checks for phase3 routing.

Selection as a source fact does not confer permission to draw a trend.
No original PDF/workbook is fetched or newly source-audited here.
"""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,re,sqlite3
from decimal import Decimal
from pathlib import Path
import phase2_engine
import phase2_update
from validate_phase2 import compare_formats,compare_csv,digest,iterjson,local,require,scalar,stable,textopen

ROOT=Path(__file__).resolve().parents[1]
SELECTED={'selected_source_fact','selected_source_missing','selected_source_unusable'}
TABLES=('record_routes','candidate_decisions','queries','series_edges')

def same(actual,expected,message):require(stable(actual)==stable(expected),message)
def period_index(a):
 year=a.get('comparison_year');month=a.get('comparison_month')
 if not isinstance(year,int) or isinstance(year,bool) or year<1:return None
 if a.get('period_kind')=='monthly_source_statistic':return year*12+month-1 if isinstance(month,int) and not isinstance(month,bool) and 1<=month<=12 else None
 if month is not None or a.get('period_kind') in {'unresolved','programme_not_annual','partial_year_source','monthly_reference_month_unresolved'}:return None
 return year

def assert_priority_choice(selected_bundles,eligible_bundle_ranks):
 """Priority is metadata/policy only. Missingness never participates in ranks."""
 require(bool(eligible_bundle_ranks) or not selected_bundles,'Selected a bundle with no eligible policy binding')
 if not eligible_bundle_ranks:return
 best=min(eligible_bundle_ranks.values());winners={b for b,r in eligible_bundle_ranks.items() if r==best}
 if len(winners)>1:require(not selected_bundles,'Equal-priority distinct bundles must remain ambiguous')
 else:require(set(selected_bundles)==winners,'Source priority changed because of values/missingness or an unbound preference')

def policy_matches(a,profile,contexts):
 f=profile['candidate_filter'];facet=a['facets']
 tests=[not f.get('layer') or a['layer']==f['layer'],'source_ids' not in f or a['source_id'] in f['source_ids'],not f.get('source_id_regex') or re.fullmatch(f['source_id_regex'],a['source_id']) is not None,not f.get('source_family') or contexts.get((a['layer'],a['source_id']),{}).get('source_family')==f['source_family'],'geo_in' not in f or facet.get('geographic_scope') in f['geo_in'],not f.get('geo_prefix') or str(facet.get('geographic_scope','')).startswith(f['geo_prefix']),'entity_in' not in f or facet.get('entity') in f['entity_in'],'indicators' not in f or a['raw_indicator'] in f['indicators']]
 return all(tests)
def metadata_qualified(a,p,reviewed):
 if not reviewed:return False
 geo=str(a['facets'].get('geographic_scope') or '')
 if any(x in geo for x in ('uncertain','unresolved','ambiguous')) or p.get('required_geo') and geo not in p['required_geo'] or a['measure_class'] in p.get('exclude_measures',[]):return False
 y=a.get('comparison_year');m=a.get('comparison_month');kind=a['period_kind'];period=p['period_requirement']
 if period!='programme' and (not isinstance(y,int) or isinstance(y,bool) or not 1000<=y<=9999):return False
 if period=='monthly' and (kind!='monthly_source_statistic' or not isinstance(m,int) or isinstance(m,bool) or not 1<=m<=12):return False
 if period=='annual' and (kind.startswith('monthly') or kind in {'unresolved','partial_year_source','programme_not_annual'}):return False
 if period=='programme' and a['layer']!='programme_quantities':return False
 if p.get('expected_units') and a['comparison_unit'] is not None and a['comparison_unit'] not in p['expected_units']:return False
 return True
def validate_policy_bindings(routes,decisions,queries,annotations,policy,contract,evidence_digests=None):
 profiles={p['id']:p for p in policy['profiles']};require(set(profiles)==set(contract['profiles']) and len(profiles)==len(policy['profiles']),'Registered profile IDs differ from contract')
 require(policy.get('no_value_based_ranking') is True and policy.get('unreviewed_source_versions_require_review') is True,'Unsafe selection policy flags')
 exact={};contexts={};supported_panel_keys=set(policy.get('reviewed_panel_record_keys',[]))
 for source in policy['reviewed_sources']:
  key=(source['layer'],source['source_id'],source['source_sha256']);require(key not in exact,'Duplicate reviewed version binding');exact[key]=source;contexts[(source['layer'],source['source_id'])]=source
 if evidence_digests is not None:require(isinstance(policy.get('evidence_bindings'),dict) and set(policy['evidence_bindings'])==set(evidence_digests),'Production evidence binding inventory differs')
 amap={a['record_key']:a for a in annotations};reviewed={key:bool((s:=exact.get((a['layer'],a['source_id'],a['source_sha256']))) and a['evidence_id'] in s['evidence_ids'] and (evidence_digests is None or policy['evidence_bindings'].get(a['evidence_id'])==evidence_digests.get(a['evidence_id']))) for key,a in amap.items()}
 expected_candidates=collections.defaultdict(set)
 for r in routes:
  a=amap[r['record_key']];expected=[p['id'] for p in policy['profiles'] if policy_matches(a,p,contexts)];same(r['candidate_profile_ids'],expected,'Route scope differs from registered source/purpose filter');same(r['source_version_reviewed'],reviewed[r['record_key']],'Unreviewed source/evidence version accepted')
  expected_status='unreviewed_source_version' if not reviewed[r['record_key']] else 'registered_profile_candidate' if expected else 'no_default_profile_for_original_scope';same(r['route_status'],expected_status,'Route status differs from registered scope');same(r['route_id'],expected[0] if expected else 'no_registered_default','Default route primary question differs')
  for pid in expected:expected_candidates[pid].add(r['record_key'])
 by_profile=collections.defaultdict(list)
 for d in decisions:
  require(d['policy_version']==policy['policy_version'],'Decision policy version differs');by_profile[d['profile_id']].append(d)
 for q in queries:
  pid=q['profile_id'];p=profiles[pid];items=by_profile[pid];require({d['record_key'] for d in items}==expected_candidates[pid],'Policy-matched source records omitted or added')
  require(q['policy_version']==policy['policy_version'],'Query policy version differs');require(q['ranking_never_uses_numeric_values'] is True and q['no_cross_source_splice'] is True,'Unsafe query operation')
  require(q['selected_records']==sum(d['selected'] for d in items) and q['candidate_records']==len(items),'Query counts differ')
  require(q['alternative_records']==sum(d['selection_status']=='alternative_source_version' for d in items) and q['blocked_records']==sum(not d['selected'] and d['selection_status']!='alternative_source_version' for d in items),'Query alternative/blocked counts differ')
  selected_items=[d for d in items if d['selected']];years=sorted({d['period_year'] for d in selected_items if isinstance(d['period_year'],int) and not isinstance(d['period_year'],bool) and 1000<=d['period_year']<=9999});year_counts=[]
  for year in years:
   annual=[d for d in selected_items if d['period_year']==year];year_counts.append({'year':year,'original_positions':len(annual),'numeric_point_values':sum(d['point_value'] is not None for d in annual),'source_missing':sum(d['selection_status']=='selected_source_missing' for d in annual),'source_unusable':sum(d['selection_status']=='selected_source_unusable' for d in annual)})
  same(q['period_coverage']['selected_years'],years,'Coverage years differ');same(q['period_coverage']['year_counts'],year_counts,'Original positions confused with numeric availability');same(q['period_coverage']['known_scope_gaps'],p.get('known_scope_gaps',[]),'Known scope gap declaration dropped or changed');require(q['period_coverage']['original_positions_are_not_numeric_completeness'] is True,'Numeric completeness overclaim')
  chosen={d['source_bundle_id'] for d in items if d['selected']};same(q['selected_source_bundle_ids'],sorted(chosen),'Query chosen bundles differ')
  bundles=collections.defaultdict(list)
  for d in items:
   a=amap[d['record_key']];expected_bundle=a['source_id']+'@'+a['source_sha256']+'|'+a['evidence_id'];same(d['source_bundle_id'],expected_bundle,'Source bundle identity changed');bundles[expected_bundle].append(a)
   qualified=metadata_qualified(a,p,reviewed[a['record_key']])
   if d['selected']:require(qualified,'Metadata-unqualified source fact selected')
   if p['selection_mode']=='fixed_original_rows':require(d['selected']==qualified,'Fixed original scope dropped an eligible row because of value/missingness')
  if p['selection_mode']!='latest_original_panel':continue
  purpose=q['requested_purpose'];restrictions=purpose not in p.get('supported_purposes',['source-facts','trend']) or purpose=='trend' and p.get('require_metric_for_trend')
  ranks={};any_unreviewed=any(not reviewed[a['record_key']] for rows in bundles.values() for a in rows)
  for bid,rows in bundles.items():
   priority=p.get('priority_source_ids');rank=None
   if priority:rank=len(priority)-priority.index(rows[0]['source_id']) if rows[0]['source_id'] in priority else None
   else:
    editions={str(a.get('source_edition_raw')) for a in rows}
    if len(editions)==1 and re.fullmatch('[0-9]{1,4}',next(iter(editions))):rank=int(next(iter(editions)))
   qualified=rank is not None and all(metadata_qualified(a,p,reviewed[a['record_key']]) for a in rows)
   if purpose=='trend':
    for a in rows:
     semantic=[r for r in a['reasons'] if r not in {'original_value_missing_marker_or_unresolved_do_not_impute','original_display_vs_typed_numeric_conflict'}]
     if semantic or a['record_key'] not in supported_panel_keys:qualified=False
   if qualified:ranks[bid]=-rank
  if restrictions or any_unreviewed:require(not chosen,'Restricted or unreviewed latest selection silently fell back')
  else:assert_priority_choice(chosen,ranks)
 return {'reviewed_versions':len(exact),'registered_profiles':len(profiles),'priority_does_not_use_values':True,'evidence_bindings_checked':len(evidence_digests or {}),'changed_evidence_bodies':sum(policy['evidence_bindings'].get(eid)!=value for eid,value in (evidence_digests or {}).items())}

def validate_rows(routes,decisions,queries,edges,annotations,contract):
 amap={a['record_key']:a for a in annotations};require(len(amap)==len(annotations),'Duplicate phase2 record key')
 profiles=set(contract['profiles']);rmap={};matched=collections.defaultdict(set);dmap={};selected=collections.defaultdict(list);guards=collections.Counter()
 route_copy=('record_key','layer','observation_id','source_id','source_sha256','source_url','source_locator','source_version_id','evidence_id','raw_value','original_value','value_status','comparison_status','comparison_unit','comparison_year','comparison_month','comparison_group_id','quality_flags_original')
 for r in routes:
  require(not set(contract['required_route_fields'])-r.keys(),'Missing required route fields')
  key=r['record_key'];require(key in amap and key not in rmap,'Unknown or duplicate routed record');a=amap[key];rmap[key]=r
  for field in route_copy:same(r[field],a.get(field),'Route changed phase2 field: '+key+':'+field)
  if 'zero_interpretation' in r:same(r['zero_interpretation'],a.get('zero_interpretation'),'Route zero interpretation upgraded')
  if 'facets' in r:same(r['facets'],a['facets'],'Route facets changed')
  ids=r['candidate_profile_ids'];require(len(ids)==len(set(ids)) and set(ids)<=profiles,'Route names duplicate/unknown profiles');require(r['route_status'] in contract['route_statuses'],'Unknown route status')
  require(isinstance(r['source_version_reviewed'],bool),'Review state is not Boolean')
  if not r['source_version_reviewed']:require(r['route_status']=='unreviewed_source_version','Unreviewed route promoted')
 require(set(rmap)==set(amap),'Routes are not exactly one per phase2 record')
 decision_copy={'record_key':'record_key','layer':'layer','observation_id':'observation_id','source_id':'source_id','source_sha256':'source_sha256','source_url':'source_url','source_locator':'source_locator','source_version_id':'source_version_id','evidence_id':'evidence_id','source_edition_raw':'source_edition_raw','raw_indicator':'raw_indicator','original_value':'original_value','raw_value':'raw_value','unit_raw_preserved':'unit_raw_preserved','value_status':'value_status','comparison_status':'comparison_status','comparison_group_id':'comparison_group_id','definition_signature':'definition_signature','quality_flags_original':'quality_flags_original','facets':'facets','period_year':'comparison_year','period_month':'comparison_month','period_kind':'period_kind'}
 decision_ids=set()
 for d in decisions:
  require(not set(contract['required_decision_fields'])-d.keys(),'Missing required decision fields')
  p=d['profile_id'];key=d['record_key'];pair=(p,key);require(p in profiles and key in amap and pair not in dmap,'Unknown or duplicate profile-record decision');require(d['decision_id'] not in decision_ids,'Duplicate decision ID');decision_ids.add(d['decision_id']);dmap[pair]=d;matched[key].add(p);a=amap[key]
  for out,source in decision_copy.items():same(d[out],a.get(source),'Decision changed phase2 field: '+key+':'+out)
  same(d['entity'],a['facets'].get('entity'),'Decision entity changed');same(d['facility_or_reader_category'],a['facets'].get('facility_or_reader_category'),'Decision classification changed')
  require(d['selection_status'] in contract['selection_statuses'],'Unknown selection status');require(isinstance(d['selected'],bool),'Selected state is not Boolean');require(d['selected']==(d['selection_status'] in SELECTED),'Selected/status disagree');require(isinstance(d['source_version_reviewed'],bool),'Decision review state is not Boolean')
  same(d['source_version_reviewed'],rmap[key]['source_version_reviewed'],'Route/decision review states differ')
  if d['selected']:require(d['source_version_reviewed'],'Unreviewed version selected');selected[p].append(key)
  value=d['point_value']
  same(d['point_unit'],a.get('comparison_unit'),'Point unit differs from phase2')
  if value is not None:
   require(a.get('comparison_value') is not None and a.get('comparison_unit'),'Value manufactured without phase2 value/unit')
   require(Decimal(str(value))==Decimal(str(a['comparison_value'])),'Point value differs from preserved phase2 decimal');same(d['point_unit'],a['comparison_unit'],'Point unit changed')
  if d['selection_status']=='selected_source_fact':require(d['original_value'] is not None and value is not None,'Missing/unusable row called selected fact')
  if d['selection_status']=='selected_source_missing':require(d['original_value'] is None and value is None and d['value_status']!='source_display_typed_value_conflict_unresolved','Conflict or numeric row called source missing')
  if d['selection_status']=='selected_source_unusable':require(value is None,'Unusable selection has point value')
  if a['value_status']=='source_display_typed_value_conflict_unresolved':require(value is None,'Typed0 conflict coerced to number');guards['typed_conflict_preserved']+=1
  if a['comparison_year'] is None:require(d['period_year'] is None,'Unknown formal year filled');guards['unknown_year_preserved']+=1
  if a.get('original_value') is not None and Decimal(str(a['original_value']))==0:require(d['original_value'] is not None,'Original zero lost');guards['zero_preserved']+=1
  if 'zero_interpretation' in d:same(d['zero_interpretation'],a.get('zero_interpretation'),'Original zero interpretation upgraded')
  same(d['join_segment_id'],a['comparison_group_id'] if value is not None and a['comparison_status']=='published_panel_limited' else None,'Join segment crosses original phase2 permission')
 for key,r in rmap.items():require(set(r['candidate_profile_ids'])==matched[key],'Route candidate memberships differ')
 qmap={}
 for q in queries:
  p=q['profile_id'];require(p in profiles and p not in qmap,'Unknown or duplicate query profile');qmap[p]=q
  ids=q['selected_record_keys'];require(len(ids)==len(set(ids)) and set(ids)==set(selected[p]),'Query selected IDs disagree with decisions')
 require(set(qmap)==profiles,'Default queries do not cover every registered profile')
 edge_ids=set();edge_pairs=set();drawable=0
 for e in edges:
  require(not set(contract.get('edge_fields',[]))-e.keys(),'Required edge fields missing')
  require(e['edge_id'] not in edge_ids,'Duplicate edge ID');edge_ids.add(e['edge_id']);p=e['profile_id'];left=e['left_record_key'];right=e['right_record_key'];require((p,left,right) not in edge_pairs,'Duplicate trend edge');edge_pairs.add((p,left,right))
  require(p in profiles and (p,left) in dmap and (p,right) in dmap,'Edge refers to unknown candidate');a=amap[left];b=amap[right]
  require(dmap[p,left]['selected'] and dmap[p,right]['selected'],'Edge uses an unselected candidate');require(a['comparison_group_id']==b['comparison_group_id'],'Edge crosses original phase2 groups');require(isinstance(e['drawable'],bool),'Drawable state is not Boolean')
  require(period_index(a) is not None and period_index(b) is not None,'Edge invents a relation to an unknown/programme period')
  same(e['comparison_group_id'],a['comparison_group_id'],'Edge original group label changed');same(e['period_left'],[a['comparison_year'],a['comparison_month']],'Edge left period changed');same(e['period_right'],[b['comparison_year'],b['comparison_month']],'Edge right period changed')
  if e['drawable']:
   require(e['comparison_status']=='published_panel_limited','Drawable edge status not limited')
   require(a['comparison_status']==b['comparison_status']=='published_panel_limited','Selected fact upgraded into trend certification');require(dmap[p,left]['point_value'] is not None and dmap[p,right]['point_value'] is not None,'Edge touches missing/unusable value')
   ai=period_index(a);bi=period_index(b);require(ai is not None and bi is not None and bi-ai==1 and a['period_kind']==b['period_kind'],'Edge bridges a gap, invalid date or period kind');comparison=phase2_engine.compare(a,b);require(comparison['status']=='published_panel_limited','Phase2.compare refuses drawable edge');drawable+=1
  comparison=phase2_engine.compare(a,b);adjacent=period_index(b)==period_index(a)+1 and a['period_kind']==b['period_kind'];same(e['drawable'],adjacent and comparison['status']=='published_panel_limited','Edge drawable state differs from P2/calendar');same(e['comparison_status'],comparison['status'] if adjacent else 'unresolved','Edge comparison status differs from P2/calendar');required_reasons=set(comparison['reasons'])| (set() if adjacent else {'calendar_periods_not_adjacent_do_not_bridge_gaps'});require(required_reasons<=set(e['reasons']),'Edge dropped an original refusal/permission reason')
 expected_pairs=set();groups=collections.defaultdict(list)
 for (pid,key),d in dmap.items():
  if d['selected'] and period_index(amap[key]) is not None:groups[pid,d['comparison_group_id']].append(amap[key])
 for (pid,gid),items in groups.items():
  ordered=sorted(items,key=lambda a:(period_index(a) is None,period_index(a) or 0,a['record_key']))
  expected_pairs.update((pid,a['record_key'],b['record_key']) for a,b in zip(ordered,ordered[1:]))
 require(edge_pairs==expected_pairs,'Consecutive selected-group edge inventory incomplete or added')
 for pid,q in qmap.items():
  if 'trend_summary' not in q:continue
  items=[d for d in decisions if d['profile_id']==pid and d['selected']];links=[e for e in edges if e['profile_id']==pid];groups={d['comparison_group_id'] for d in items};drawn=sum(e['drawable'] for e in links);expected={'single_continuous_series':len(items)>1 and len(groups)==1 and len(links)==len(items)-1 and drawn==len(links),'selected_original_comparison_groups':len(groups),'drawable_edges':drawn,'blocked_candidate_edges':len(links)-drawn,'selected_missing_or_unusable':sum(d['selection_status']!='selected_source_fact' for d in items),'historical_collection_method_invariance_certified':False}
  for field,value in expected.items():same(q['trend_summary'].get(field),value,'Trend continuity summary overclaim/different count: '+field)
 return {'records':len(routes),'decisions':len(decisions),'profiles':len(qmap),'edges':len(edges),'drawable_edges':drawable,'guards':dict(guards),'all_route_zeros_preserved':sum(a['original_value'] is not None and Decimal(str(a['original_value']))==0 for a in annotations)}

def validate(root=ROOT):
 root=Path(root).resolve();summary=json.loads((root/'docs/phase3-summary.json').read_text());contract=json.loads((root/'docs/phase3-contract.json').read_text());require(summary['dataset_version']==(root/'VERSION').read_text().strip(),'Phase3 version differs')
 for name,expected in summary['inputs'].items():require(local(root,name).is_file() and digest(local(root,name))==expected,'Phase3 input checksum differs: '+name)
 for name,spec in summary['outputs'].items():
  p=local(root,name);require(p.is_file() and digest(p)==spec['sha256'] and p.stat().st_size==spec['bytes'],'Phase3 output checksum differs: '+name)
 datasets={};formats={};con=sqlite3.connect((root/'derived/phase3/selection.sqlite').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 try:
  require(con.execute('PRAGMA quick_check').fetchone()[0]=='ok','Selection SQLite integrity failed')
  order={'record_routes':'record_key','candidate_decisions':'decision_id','queries':'profile_id','series_edges':'edge_id'}
  specs={s['table']:s for s in summary['tables']};require(set(specs)==set(TABLES),'Phase3 table inventory differs')
  for name in TABLES:
   spec=specs[name];rows=list(iterjson(local(root,spec['jsonl'])));datasets[name]=rows;require(len(rows)==spec['records'],'Phase3 table row count differs');fields=[r[1] for r in con.execute('PRAGMA table_info("'+name+'")')]
   csv_report=compare_csv(rows,local(root,spec['csv']),name)
   ordered=sorted(rows,key=lambda r:r[order[name]]);virtual_csv=({k:'' if scalar(r.get(k)) is None else scalar(r.get(k)) for k in fields} for r in ordered)
   formats[name]=compare_formats(ordered,fields,virtual_csv,fields,con.execute('SELECT * FROM "'+name+'" ORDER BY "'+order[name]+'"'),name);formats[name]['csv_original_row_order_verified']=True
 finally:con.close()
 p2summary=json.loads((root/'docs/phase2-summary.json').read_text())
 for name in ('derived/phase2/annotations.jsonl.gz','derived/phase2/evidence_cards.jsonl','derived/phase2/groups.jsonl'):
  spec=p2summary['outputs'][name];require(digest(root/name)==spec['sha256'] and (root/name).stat().st_size==spec['bytes'],'Reviewed phase2 input checksum differs: '+name)
 annotations=list(iterjson(root/'derived/phase2/annotations.jsonl.gz'));report=validate_rows(*(datasets[n] for n in TABLES),annotations,contract)
 evidence_rows=list(iterjson(root/'derived/phase2/evidence_cards.jsonl'));evidence_digests={r['evidence_id']:hashlib.sha256(stable(r).encode()).hexdigest() for r in evidence_rows};require(len(evidence_digests)==len(evidence_rows),'Duplicate phase2 evidence identity')
 report['policy_bindings']=validate_policy_bindings(datasets['record_routes'],datasets['candidate_decisions'],datasets['queries'],annotations,json.loads((root/'docs/phase3-profiles.json').read_text()),contract,evidence_digests)
 same(summary['counts'],{name:len(rows) for name,rows in datasets.items()},'Summary table counts differ')
 same(summary['registered_profiles'],len(contract['profiles']),'Summary profile count differs')
 same(summary['route_status_counts'],dict(collections.Counter(r['route_status'] for r in datasets['record_routes'])),'Route status counts differ')
 same(summary['selection_status_counts'],dict(collections.Counter(r['selection_status'] for r in datasets['candidate_decisions'])),'Selection status counts differ')
 require(summary['selected_decisions']==sum(d['selected'] for d in datasets['candidate_decisions']) and summary['drawable_edges']==sum(e['drawable'] for e in datasets['series_edges']),'Summary selection/edge counts differ')
 require(summary['canonical_values_modified'] is False and summary['no_imputation'] is True and summary['no_aggregation'] is True and summary['no_geographic_recoding'] is True,'Unsafe phase3 data policy')
 part_index=json.loads((root/'docs/phase3-partitions.json').read_text());require(part_index['dataset_version']==summary['dataset_version'] and part_index['union_equals_candidate_decisions'] is True,'Partition index version/policy differs');expected_parts=collections.defaultdict(list)
 for d in datasets['candidate_decisions']:expected_parts[d['profile_id'],d['period_year']].append(d)
 seen_parts=set()
 for part in part_index['partitions']:
  key=(part['profile_id'],part['period_year']);require(key in expected_parts and key not in seen_parts,'Duplicate/unknown phase3 partition');seen_parts.add(key);path=local(root,part['path']);require(digest(path)==part['sha256'] and path.stat().st_size==part['bytes'],'Partition bytes/SHA differs');rows=list(iterjson(path));same(rows,expected_parts[key],'Partition union or row order differs');require(len(rows)==part['records'] and sum(r['selected'] for r in rows)==part['selected_records'],'Partition count differs')
 require(seen_parts==set(expected_parts) and len(seen_parts)==summary['partitions'],'Partition union incomplete')
 for filename in ('phase3-question-index.json','phase3-data-dictionary.json'):
  obj=json.loads((root/'docs'/filename).read_text());same(obj['dataset_version'],summary['dataset_version'],'Sidecar version differs')
  if filename=='phase3-question-index.json':same(obj['profiles'],json.loads((root/'docs/phase3-profiles.json').read_text())['profiles'],'Question index policy differs')
  else:
   require(set(obj['tables'])==set(TABLES),'Dictionary tables differ')
   for name,rows in datasets.items():
    fields=set().union(*(r.keys() for r in rows));require(set(obj['tables'][name])==fields,'Dictionary columns differ')
    for field in fields:same(obj['tables'][name][field],{'json_types':sorted({type(r[field]).__name__ for r in rows if field in r}),'present_in_all_records':all(field in r for r in rows)},'Dictionary field types differ')
 require(summary['layer_raw_fingerprints']==json.loads((root/'docs/phase2-summary.json').read_text())['layer_raw_fingerprints']==contract['baseline']['layer_raw_fingerprints'],'Original statistical fingerprint changed')
 fingerprints={layer:phase2_update.statistical_fingerprint(phase2_update.source_path(root,path)) for layer,path in phase2_engine.LAYERS.items()};require(fingerprints==summary['layer_raw_fingerprints'],'Raw source fingerprint differs from phase3/P2/baseline')
 amap={a['record_key']:a for a in annotations};seen=set();supported=set();p2cards=phase2_engine.card_index(list(iterjson(root/'derived/phase2/evidence_cards.jsonl')))
 for layer,path in phase2_engine.LAYERS.items():
  for raw in iterjson(phase2_update.source_path(root,path)):
   key=layer+':'+raw['observation_id'];require(key in amap and key not in seen,'Original quantitative identity missing/duplicated');seen.add(key);a=amap[key]
   expected={'source_id':raw['source_id'],'source_sha256':raw['source_sha256'],'source_url':raw.get('source_url') or raw.get('source_download_url'),'source_locator':raw['source_locator'],'raw_value':raw.get('raw_value',raw.get('value_raw')),'original_value':raw.get('value'),'value_status':raw.get('value_status')}
   for field,value in expected.items():same(a.get(field),value,'Underlying source changed: '+key+':'+field)
   card=p2cards[layer,raw['observation_id']]
   if phase2_engine.is_reviewed(card) and phase2_engine.policy_for(raw,card)['status']=='published_panel_limited':supported.add(key)
 require(seen==set(amap),'P2 inventory differs from original quantitative layers')
 policy=json.loads((root/'docs/phase3-profiles.json').read_text());keys=policy.get('reviewed_panel_record_keys',[]);require(len(keys)==len(set(keys)) and set(keys)==supported,'Static panel support differs from original P2 field/year policy')
 return {'status':'PASS','dataset_version':summary['dataset_version'],**report,'formats':formats,'source_audit_claim':'Format/preservation review only; no new independent phase2 source audit.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(validate(a.root),ensure_ascii=False))
if __name__=='__main__':main()
