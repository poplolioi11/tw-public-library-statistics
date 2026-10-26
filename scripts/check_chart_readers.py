#!/usr/bin/env python3
"""Verify every exported plot point, original source, interval decision and line."""
import argparse,gzip,hashlib,json,re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET
import phase2_engine as p2
import phase3_engine as p3
from series_charts import period
def payload(path,stage):
 text=path.read_text();match=re.search(r'<script type="application/json" id="'+stage+r'-data">(.*?)</script>',text,re.S)
 if not match:raise AssertionError('Missing complete embedded payload')
 return json.loads(match.group(1))
def rows(root,name):
 path=root/name
 with (gzip.open(path,'rt',encoding='utf-8') if name.endswith('.gz') else path.open()) as f:return [json.loads(x) for x in f if x.strip()]
def unpack(data,name):
 t=data['tables'][name];return [{k:data['pool'][i] for k,i in zip(t['columns'],row) if i!=-1} for row in t['rows']]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=ap.parse_args();root=a.root.resolve()
 annotations=rows(root,'derived/phase2/annotations.jsonl.gz');amap={x['record_key']:x for x in annotations};bygroup=defaultdict(list)
 for x in annotations:bygroup[x['comparison_group_id']].append(x)
 d2=payload(root/'site/phase2.html','phase2');d3=payload(root/'site/phase3.html','phase3');policy=p3.load_policy(root)
 decisions=unpack(d3,'candidate_decisions');edges=unpack(d3,'series_edges');profile_decisions=defaultdict(list);values=defaultdict(dict);allowed=defaultdict(set)
 def accept(pid,ds,es):
  for d in ds:
   if d['selected']:
    k=d['record_key'];v=d['point_value']
    if k in values[pid]:assert values[pid][k]==v
    values[pid][k]=v
  allowed[pid].update((e['left_record_key'],e['right_record_key']) for e in es if e['drawable'])
 for d in decisions:profile_decisions[d['profile_id']].append(d)
 for pid,ds in profile_decisions.items():accept(pid,ds,[e for e in edges if e['profile_id']==pid])
 intervals=0
 for pid,presets in d3['interval_queries'].items():
  for bounds,expected in presets.items():
   lo,hi=map(int,bounds.split(':'));answer=p3.select(policy,annotations,pid,start_year=lo,end_year=hi);q=answer['query']
   actual={'selection_status':q['selection_status'],'selection_explanation':q['selection_explanation'],'selected_record_keys':q['selected_record_keys'],'comparison_group_ids':sorted({d['comparison_group_id'] for d in answer['decisions'] if d['selected']}),'selected_source_bundle_ids':q['selected_source_bundle_ids'],'trend_summary':q['trend_summary']}
   assert actual==expected,(pid,bounds,'compiled interval differs from complete selector')
   accept(pid,answer['decisions'],answer['edges']);intervals+=1
 stats={'charts':0,'points':0,'lines':0,'reported_zero_points':0,'omitted_positions':0,'parsed_svg':0}
 for stage,charts in [('phase2',d2['examples']),('phase3',d3['charts'])]:
  for c in charts.values():
   gid=c['comparison_group_id'];pid=c.get('profile_id');items=bygroup[gid] if stage=='phase2' else [x for x in bygroup[gid] if x['record_key'] in values[pid]]
   assert c['original_positions']==len(items)
   positions={period(x)[0]:x for x in items if period(x) is not None};assert len(positions)==sum(period(x) is not None for x in items)
   numeric=[]
   for p in c['source_points']:
    original=amap[p['record_key']];assert original['comparison_group_id']==gid
    for displayed,field in [('reported_value','original_value'),('raw_value','raw_value'),('source_id','source_id'),('source_url','source_url'),('source_sha256','source_sha256'),('source_locator','source_locator'),('source_version_id','source_version_id'),('zero_interpretation','zero_interpretation')]:assert p[displayed]==original.get(field),(stage,displayed,p['record_key'])
    v=original['comparison_value'] if stage=='phase2' else values[pid][p['record_key']]
    assert v is not None and Decimal(p['comparison_value'])==Decimal(str(v))
    numeric.append(Decimal(p['comparison_value']));stats['reported_zero_points']+=Decimal(p['comparison_value'])==0
    node=ET.fromstring(p['markup']);assert node.tag=='a' and node.attrib['href']==original['source_url'];circle=node.find('circle');assert circle is not None
    assert circle.attrib['cx']==p['x'] and circle.attrib['cy']==p['y']
   low=min(Decimal(0),min(numeric));high=max(numeric);dy=high-low or Decimal(1);lo=min(positions);dx=Decimal(max(positions)-lo or 1)
   for p in c['source_points']:
    i=period(amap[p['record_key']])[0];v=Decimal(p['comparison_value']);assert p['x']==f'{Decimal(76)+Decimal(i-lo)/dx*700:.2f}';assert p['y']==f'{Decimal(220)-(v-low)/dy*170:.2f}'
   pointids={p['record_key'] for p in c['source_points']}
   assert pointids.isdisjoint({p['record_key'] for p in c['omitted_points']})
   for edge in c['segments']:
    left,right=edge['left'],edge['right'];assert left in pointids and right in pointids
    assert period(amap[right])[0]-period(amap[left])[0]==1
    assert p2.compare(amap[left],amap[right])['status']=='published_panel_limited'
    if stage=='phase3':assert (left,right) in allowed[pid]
   svg='<svg>'+c['axes_svg']+''.join(e['markup'] for e in c['segments'])+''.join(p['markup'] for p in c['source_points'])+'</svg>';ET.fromstring(svg)
   assert c['plotted_points']==len(pointids) and c['drawable_segments']==len(c['segments'])
   stats['charts']+=1;stats['points']+=len(pointids);stats['lines']+=len(c['segments']);stats['omitted_positions']+=len(c['omitted_points']);stats['parsed_svg']+=1
 report={'status':'PASS','dataset_version':(root/'VERSION').read_text().strip(),'phase2_charts':len(d2['examples']),'phase3_charts':len(d3['charts']),'full_selector_interval_replays':intervals,**stats,'checks':['all point original values and source URL/SHA/locator/version','all Decimal coordinates','all lines approved and adjacent with usable endpoints','all SVG parses','every compiled interval equals full-input Python selector'],'scope':'Rendered data and SVG structure, not a browser layout or all historical definition certification.','inputs':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'site/phase2.html',root/'site/phase3.html',root/'scripts/phase3_engine.py',root/'docs/phase3-profiles.json']}}
 output=root/'research/phase3-chart-review.json';output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='inputs'},ensure_ascii=False))
if __name__=='__main__':main()
