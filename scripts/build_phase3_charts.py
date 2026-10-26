#!/usr/bin/env python3
"""Compile source plots and interval choices by executing the same Python selector."""
from collections import defaultdict
import phase3_engine as engine
from series_charts import chart
def compile_charts(root,tables,profiles,annotations):
 policy=engine.load_policy(root);exact,contexts=engine.source_maps(policy);amap={a['record_key']:a for a in annotations}
 by_profile=defaultdict(list)
 for d in tables['candidate_decisions']:by_profile[d['profile_id']].append(d)
 default_queries={q['profile_id']:q for q in tables['queries']};charts={};intervals={};year_options={};default_groups={}
 for p in profiles:
  pid=p['id'];base=by_profile[pid];candidates=[amap[d['record_key']] for d in base];values={};allowed=set();authorized=set()
  def accept(decisions,edges):
   for d in decisions:
    if not d['selected']:continue
    key=d['record_key'];value=d['point_value']
    if key in values and values[key]!=value:raise ValueError('A display interval changed interpretation of the same original point')
    values[key]=value;authorized.add(key)
   allowed.update((e['left_record_key'],e['right_record_key']) for e in edges if e['drawable'])
  accept(base,[e for e in tables['series_edges'] if e['profile_id']==pid])
  years=sorted({a['comparison_year'] for a in candidates if engine.valid_year(a['comparison_year'])});year_options[pid]=years
  default_groups[pid]=sorted({d['comparison_group_id'] for d in base if d['selected']})
  if p['selection_mode']=='latest_original_panel':
   candidate_keys={a['record_key'] for a in candidates};scoped_policy={**policy,'reviewed_panel_record_keys':[key for key in policy['reviewed_panel_record_keys'] if key in candidate_keys]}
   prepared={}
   for i,start in enumerate(years):
    for end in years[i:]:
     answer=engine.select(scoped_policy,candidates,pid,start_year=start,end_year=end)
     q=answer['query'];accept(answer['decisions'],answer['edges'])
     prepared[str(start)+':'+str(end)]={'selection_status':q['selection_status'],'selection_explanation':q['selection_explanation'],'selected_record_keys':q['selected_record_keys'],'comparison_group_ids':sorted({d['comparison_group_id'] for d in answer['decisions'] if d['selected']}),'selected_source_bundle_ids':q['selected_source_bundle_ids'],'trend_summary':q['trend_summary']}
   intervals[pid]=prepared
  grouped=defaultdict(list)
  for key in authorized:grouped[amap[key]['comparison_group_id']].append(amap[key])
  for gid,items in grouped.items():
   # One-period source facts stay visible in the complete table; they are not invented time-series lines.
   if len({(a['comparison_year'],a['comparison_month']) for a in items})<2:continue
   plot=chart(items,allowed_edges=allowed,values=values)
   if plot is None or plot['plotted_points']<2:continue
   plot.pop('svg',None);plot['profile_id']=pid;plot['chart_id']=pid+'|'+gid;plot['default_selected']=gid in default_groups[pid];charts[plot['chart_id']]=plot
 return {'charts':charts,'interval_queries':intervals,'chart_year_options':year_options,'default_chart_groups':default_groups,'chart_permission':'Coordinates and interval selections computed in Python. Only explicit phase3 query drawable edges are lines. Original period facts without permission appear as points only.','chart_count':len(charts),'interval_query_count':sum(len(v) for v in intervals.values())}
