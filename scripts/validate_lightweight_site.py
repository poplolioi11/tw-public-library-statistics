#!/usr/bin/env python3
"""Independently compare every lazy chart with the frozen, reviewed readers."""
import argparse,gzip,hashlib,json,re
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
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
def source_batch_matches_canonical(canonical,source):
 """Allow only named canonical-only public metadata; compare every source field."""
 if not isinstance(canonical,dict):return False
 added={key:canonical[key] for key in ('public_evidence_sha256','public_projection_policy') if key in canonical and key not in source}
 return canonical=={**source,**added}
def validate(root,site=None,summary_path=None):
 site=site or root/'site/light';manifest=load(site/'manifest.json');summary=load(summary_path or root/'docs/light-site-summary.json');checks=0
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
 check(manifest['review_status']=={'human_review_completed':0,'human_review_planned':120,'human_double_collation_completed':False},'Human review status overstated')
 check(len(manifest['source_batches'])==1 and manifest['source_batches'][0]['id']=='ncl94-statistics','Unreviewed source batch added')
 batch_entry=manifest['source_batches'][0];batch=asset(batch_entry['catalog_url'])
 expected={r['observation_id']:r for r in map(json.loads,(root/'derived/ncl94_statistics_observations.jsonl').read_text().splitlines()) if r}
 check(batch['mode']=='batch' and batch['id']==batch_entry['id'],'Source batch identity changed')
 check(len(batch['records'])==len(expected)==24 and {r['observation_id'] for r in batch['records']}==set(expected),'Source batch ID set changed or duplicated')
 check(batch['review_status']==manifest['review_status'],'Batch human review status overstated')
 check(batch['lines']==[],'Single-period source batch gained unapproved lines')
 check({r['data_year'] for r in batch['records']}=={2004},'Single-period source batch changed year')
 check(len({r['physical_cell_id'] for r in batch['records']})==16,'Physical cell count changed')
 check(sum(r['quantity_role']=='primary' for r in batch['records'])==16 and sum(r['quantity_role']=='responding_libraries' for r in batch['records'])==8,'Primary and response roles changed')
 check(sum(r['unit'] is None for r in batch['records'])==8,'Unprinted original units were inferred')
 copied_fields=('observation_id','source_record_id','source_id','source_edition','source_table_title','data_year','period_raw','period_start','period_end','source_period_interpretation_status','indicator','geography','raw_value','value','value_status','unit','unit_raw','unit_status','unit_basis','population_scope','aggregation_role','national_libraries_scope','source_url','source_pdf_page','source_printed_page','source_table','source_row','source_column','source_row_label_raw','source_column_path','source_cell_bbox','source_locator','source_sha256','source_version_id','original_source_note','source_footnotes_raw')
 context_fields={'physical_cell_id':'physical_cell_id','quantity_role':'quantity_role','physical_cell_raw':'value_raw','source_column_context':'source_column_context','physical_source_row_label_raw':'source_row_label_raw','raw_transcription_method':'raw_transcription_method','source_context_notes':'notes','cross_source_panel_permission':'cross_source_panel_permission'}
 for record in batch['records']:
  original=expected[record['observation_id']];context=json.loads(original['source_time_reference'])['physical_source_context']
  check(source_batch_matches_canonical(originals['canonical:'+record['observation_id']],original),'Dedicated batch differs from canonical record')
  check(set(record)==set(copied_fields)|set(context_fields),'Source batch field allowlist changed')
  for key in copied_fields:check(record[key]==original.get(key),'Source batch original field changed: '+key)
  for key,sourcekey in context_fields.items():check(record[key]==context[sourcekey],'Physical cell context changed: '+key)
  check(record['period_start'] is None and record['period_end'] is None and record['period_raw']=='民國93年','Source batch exact dates were inferred')
  check(record['cross_source_panel_permission'] is False,'Source batch comparability widened')
  u=urlsplit(record['source_url']);page={'145':5,'146':6,'147':11}[record['source_table']]
  check(u.scheme=='https' and u.netloc=='www.ncl.edu.tw' and u.path.endswith('.pdf') and parse_qs(u.fragment)=={'page':[str(page)]},'Source batch official PDF page link changed')
  check(record['source_pdf_page']==page and record['source_printed_page']=={'145':'440','146':'441','147':'446'}[record['source_table']],'Source batch printed/PDF locator changed')
  check(record['source_sha256']=='2db33efbce20154623b6ba7398e2cfa40af8116578264889d380ab41520c44cf' and record['source_version_id']=='ncl-ed94-statistics@sha256:'+record['source_sha256'],'Source batch original SHA/version changed')
 check(batch_entry['record_count']==24 and batch_entry['physical_cells']==16 and batch_entry['years']==[2004],'Source batch manifest scope changed')
 check(summary['source_batches']=={'batches':1,'records':24,'physical_cells':16,'new_line_entries':0},'Source batch summary changed')
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
 return {'passed':True,'assertions':checks,'original_chart_groups':len(oldraw),'question_chart_groups':len(d3['charts']),'profiles':len(manifest['profiles']),'compiled_intervals':intervals,'point_entries_checked':points,'line_entries_checked':edges,'original_positions_checked':positions,'unique_chart_shards':len(seen),'source_batches':1,'source_batch_records_checked':24,'source_batch_physical_cells':16,'source_batch_new_lines':0,'initial_uncompressed_bytes':initial,'data_version':manifest['data_version'],'viewer_version':manifest['viewer_version']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--site',type=Path);p.add_argument('--summary',type=Path);a=p.parse_args();print(json.dumps(validate(a.root.resolve(),a.site.resolve() if a.site else None,a.summary.resolve() if a.summary else None),ensure_ascii=False))
if __name__=='__main__':main()
