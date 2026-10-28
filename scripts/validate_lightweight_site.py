#!/usr/bin/env python3
"""Independently compare every lazy chart with the frozen, reviewed readers."""
import argparse,gzip,hashlib,json,re
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import record_io
import reader_transport

ROOT=Path(__file__).resolve().parents[1]
def sha(body):return hashlib.sha256(body).hexdigest()
def load(path):return json.loads(path.read_text())
def embedded(root,stage):
 body=(root/'site'/f'{stage}.html').read_text()
 return reader_transport.decode(re.search(r'<script type="application/json" id="'+stage+r'-data">(.*?)</script>',body,re.S).group(1))
def decode(data,name):
 t=data['tables'][name]
 return [{k:data['pool'][i] for k,i in zip(t['columns'],r,strict=True) if i!=-1} for r in t['rows']]
def validate(root):
 site=root/'site/light';manifest=load(site/'manifest.json');summary=load(root/'docs/light-site-summary.json');checks=0
 def check(condition,message):
  nonlocal checks
  checks+=1
  if not condition:raise ValueError(message)
 def asset(url):
  check(bool(re.fullmatch(r'data/[a-f0-9]{64}\.json',url)),'Unsafe shard path')
  body=(site/url).read_bytes();check(sha(body)==Path(url).stem,'Content-addressed shard hash mismatch')
  return json.loads(body)
 check(manifest['data_version']==(root/'VERSION').read_text().strip()==summary['dataset_version'],'Data version drift')
 check(not summary['statistical_values_or_definitions_modified'],'Display cannot alter data definitions')
 d2=embedded(root,'phase2');d3=embedded(root,'phase3')
 with gzip.open(root/'derived/phase2/annotations.jsonl.gz','rt') as f:ann={r['record_key']:r for r in map(json.loads,f)}
 originals={'canonical:'+r['observation_id']:r for r in record_io.rows(root)}
 queries={q['profile_id']:q for q in decode(d3,'queries')};seen={};points=0;edges=0;positions=0
 def series(entry,c):
  nonlocal points,edges,positions
  data=asset(entry['url']);oldpoints={r['record_key']:r for r in c['source_points']};oldkeys=set(oldpoints)|{r['record_key'] for r in c['omitted_points']}
  check(data['id']==entry['id']==c['comparison_group_id'],'Series identity changed')
  for key in ('entity','facility','indicator','unit','source_id','source_edition_raw'):check(data[key]==c[key],f'Series scope changed: {key}')
  check({r['record_key'] for r in data['records']}==oldkeys and len(data['records'])==c['original_positions'],'Original positions lost or duplicated')
  check(data['lines']==[{'left':e['left'],'right':e['right']} for e in c['segments']],'Approved edge set changed')
  for r in data['records']:
   a=ann[r['record_key']];point=oldpoints.get(r['record_key']);orig=originals.get(r['record_key'],{})
   for f in ('raw_value','original_value','value_status','comparison_status','zero_interpretation','source_id','source_url','source_sha256','source_locator','source_version_id','evidence_id','facets'):
    check(r[f]==a.get(f),f'Raw/source field changed: {f}')
   check(r['year']==a['comparison_year'] and r['month']==a['comparison_month'] and r['original_unit']==a.get('unit_raw_preserved'),'Period or original unit changed')
   check(all(orig.get(k)==v for k,v in r['original_context'].items()),'Original context changed')
   check(r['official_url'] in (a['source_url'],orig.get('source_page_url')),'Official URL was invented')
   u=urlsplit(r['official_url']);check(u.scheme in ('http','https') and u.netloc and not u.username and not u.password,'Nonpublic source link')
   check(r['official_url']==a['source_url'] or bool(r['official_link_note']),'Dynamic source link must disclose reproduction requirement')
   check(r['plot_value']==(point['comparison_value'] if point else None),'Previously approved point value changed')
   if point:
    check(Decimal(r['plot']['x_pct'])==Decimal(format((Decimal(point['x'])-76)/7,'.5f')) and Decimal(r['plot']['y_pct'])==Decimal(format((Decimal(point['y'])-50)/Decimal('1.7'),'.5f')),'Plot geometry changed')
    check(Decimal(r['display_value'].replace(',',''))==Decimal(point['comparison_value']),'Display number differs')
   else:check(r['plot'] is None,'Missing value received a plotted point')
  axes=ET.fromstring('<svg>'+c['axes_svg']+'</svg>')
  check([t['label'] for t in data['y_ticks']]==[t.text for t in axes.findall('text') if t.get('y')!='246'],'Y ticks changed')
  check([t['label'] for t in data['x_ticks']]==[t.text for t in axes.findall('text') if t.get('y')=='246'],'X ticks changed')
  check(len(data['mobile_x_ticks'])<=3 and all(t in data['x_ticks'] for t in data['mobile_x_ticks']),'Mobile tick projection changed values')
  points+=len(oldpoints);edges+=len(c['segments']);positions+=len(oldkeys);seen[entry['url']]=True
 raw=asset(manifest['original_catalog_url']);oldraw={c['comparison_group_id']:c for c in d2['examples'].values()}
 check({s['id'] for s in raw['series']}==set(oldraw),'Not all original chart groups exported')
 for entry in raw['series']:series(entry,oldraw[entry['id']])
 check({p['id'] for p in manifest['profiles']}=={p['id'] for p in d3['profiles']},'Profile missing')
 def selection(got,old,groups,available):
  check(got['status']==old.get('selection_status') and got['explanation']==old.get('selection_explanation',[]),'Selection status/reason changed')
  check(got['series_ids']==[g for g in groups if g in available],'Selected source grouping changed')
  check(got['selected_record_keys']==(old.get('selected_record_keys',[]) if available else []),'Selected record set changed')
  check(got['trend_summary']==old.get('trend_summary',{}),'Original trend conditions changed')
 intervals=0
 for profile in manifest['profiles']:
  catalog=asset(profile['catalog_url']);pid=profile['id'];charts={c['comparison_group_id']:c for c in d3['charts'].values() if c['profile_id']==pid};available=set(charts)
  check({s['id'] for s in catalog['series']}==available,'Question chart omitted')
  check(catalog['years']==d3['chart_year_options'][pid],'Period options changed')
  selection(catalog['default_selection'],queries[pid],d3['default_chart_groups'][pid],available)
  oldintervals=d3['interval_queries'].get(pid,{})
  check(set(catalog['intervals'] or {})==set(oldintervals),'Compiled interval lost or invented')
  for key,value in oldintervals.items():selection(catalog['intervals'][key],value,value['comparison_group_ids'],available);intervals+=1
  for entry in catalog['series']:series(entry,charts[entry['id']])
 for name,item in summary['outputs'].items():
  path=root/name;check(path.is_file() and sha(path.read_bytes())==item['sha256'] and path.stat().st_size==item['bytes'],'Website output checksum drift: '+name)
  check(path.stat().st_size<100*1024*1024,'Website asset exceeds GitHub file limit')
 for name in ('index.html','app.css','app.js'):check((site/name).read_bytes()==(root/'site/light-src'/name).read_bytes(),'Frontend source/build differs')
 default=next(p for p in manifest['profiles'] if p['id']==manifest['default_profile_id']);catalog=asset(default['catalog_url']);first=next(s for s in catalog['series'] if s['id'] in catalog['default_selection']['series_ids'])
 initial=sum((site/n).stat().st_size for n in ('index.html','app.css','app.js','manifest.json',default['catalog_url'],first['url']))
 check(initial<1024*1024,'Initial-load uncompressed budget exceeded')
 for path in site.rglob('*'):
  if not path.is_file():continue
  body=path.read_bytes();check(not any(token in body for token in (b'/Users/',b'original_fields',b'private_source_root',b'contactEmail',b'contactPhone',b'workspace_relative_path')),'Private routing or unrelated contact field leaked')
 return {'passed':True,'assertions':checks,'original_chart_groups':len(oldraw),'question_chart_groups':len(d3['charts']),'profiles':len(manifest['profiles']),'compiled_intervals':intervals,'point_entries_checked':points,'line_entries_checked':edges,'original_positions_checked':positions,'unique_chart_shards':len(seen),'initial_uncompressed_bytes':initial,'data_version':manifest['data_version'],'viewer_version':manifest['viewer_version']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(validate(a.root.resolve()),ensure_ascii=False))
if __name__=='__main__':main()
