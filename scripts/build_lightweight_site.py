#!/usr/bin/env python3
"""Export immutable, lazy chart shards from the already-reviewed portable readers.

No source acquisition, source selection, statistical conversion or imputation.
Original values, qualifiers and permitted line pairs are copied without change.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,re,shutil
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import xml.etree.ElementTree as ET
import record_io
import reader_transport
ROOT=Path(__file__).resolve().parents[1]
VIEWER_VERSION='1.0.0'
REPOSITORY='https://github.com/poplolioi11/tw-public-library-statistics'
EXTRA_FIELDS=('notes','quality_flags','source_footnotes_raw','source_table_title','source_cell_annotation','unit_raw','unit_basis','unit_status','period_raw','period_effective','temporal_kind','population_scope','national_libraries_scope','geography_vintage','source_time_reference','source_survey_population_libraries')
def stable(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def write(path,body):
 if path.is_file() and path.read_bytes()==body:return False
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(body);tmp.replace(path);return True
def read_rows(path):
 with (gzip.open(path,'rt',encoding='utf-8') if path.suffix=='.gz' else path.open(encoding='utf-8')) as stream:return [json.loads(x) for x in stream if x.strip()]
def payload(root,stage):
 text=(root/'site'/f'{stage}.html').read_text();m=re.search(r'<script type="application/json" id="'+stage+r'-data">(.*?)</script>',text,re.S)
 if not m:raise ValueError('Reviewed reader payload missing: '+stage)
 return reader_transport.decode(m.group(1))
def table(data,name):
 t=data['tables'][name];return [{k:data['pool'][i] for k,i in zip(t['columns'],row,strict=True) if i!=-1} for row in t['rows']]
def safe_url(url):
 u=urlsplit(url or '')
 if u.scheme not in ('http','https') or not u.netloc or u.username or u.password:raise ValueError('Not a public official source URL')
 return url
def pct(value,offset,span):return format((Decimal(value)-Decimal(offset))/Decimal(span)*100,'.5f')
def period_label(a):
 y,m=a['comparison_year'],a['comparison_month']
 if y is None:return '期間未確認'
 return str(y)+(('-'+str(m).zfill(2)) if m is not None else '')
def source_link(a,original):
 raw=safe_url(a['source_url']);page=original.get('source_page_url');u=urlsplit(raw)
 stateful=u.path.endswith('/ShowQuery.aspx') and parse_qs(u.query,keep_blank_values=True).get('Z')==['']
 post='POST' in str(original.get('source_method','')).upper()
 if page and (stateful or post):
  return safe_url(page),'此官方來源使用動態查詢，需依原表代碼、年度與地區重現。原始網址、原件SHA及格位完整保留於下方。'
 return raw,''
def build_series(c,annotations,originals):
 points={p['record_key']:p for p in c['source_points']};keys=set(points)|{p['record_key'] for p in c['omitted_points']}
 if len(keys)!=c['original_positions']:raise ValueError('Do not truncate original positions')
 records=[]
 for key in sorted(keys,key=lambda k:(annotations[k]['comparison_year'] is None,annotations[k]['comparison_year'] or 0,annotations[k]['comparison_month'] or 0,k)):
  a=annotations[key];p=points.get(key);original=originals.get(key,{})
  if a['comparison_group_id']!=c['comparison_group_id']:raise ValueError('Mixed original definition group')
  if p:
   for f in ('source_url','source_sha256','source_locator','source_version_id','raw_value'):
    if p[f]!=a[f]:raise ValueError('Reviewed source-point identity changed: '+f)
   if p['reported_value']!=a['original_value']:raise ValueError('Original value changed')
  url,note=source_link(a,original);plot_value=p['comparison_value'] if p else None
  records.append({'record_key':key,'year':a['comparison_year'],'month':a['comparison_month'],'period_label':p['period_label'] if p else period_label(a),'plot_value':plot_value,'display_value':format(Decimal(plot_value),',f') if plot_value is not None else '未提供可用點值','raw_value':a['raw_value'],'original_value':a['original_value'],'original_unit':a.get('unit_raw_preserved'),'unit':c['unit'],'comparison_status':a['comparison_status'],'value_status':a['value_status'],'zero_interpretation':a.get('zero_interpretation'),'source_url':a['source_url'],'official_url':url,'official_link_note':note,'source_sha256':a['source_sha256'],'source_id':a['source_id'],'source_locator':a['source_locator'],'source_version_id':a['source_version_id'],'evidence_id':a['evidence_id'],'facets':a['facets'],'original_context':{k:original[k] for k in EXTRA_FIELDS if k in original},'plot':{'x_pct':pct(p['x'],76,700),'y_pct':pct(p['y'],50,170)} if p else None})
 line_pairs=[{'left':e['left'],'right':e['right']} for e in c['segments']]
 for e in line_pairs:
  if e['left'] not in points or e['right'] not in points:raise ValueError('Missing endpoint may never be bridged')
 axes=ET.fromstring('<svg>'+c['axes_svg']+'</svg>');xticks=[];yticks=[]
 for t in axes.findall('text'):
  if t.get('y')=='246':xticks.append({'position_pct':pct(t.get('x'),76,700),'label':t.text})
  else:yticks.append({'position_pct':pct(Decimal(t.get('y'))-4,50,170),'label':t.text})
 mobile=[xticks[i] for i in sorted({0,len(xticks)//2,len(xticks)-1})] if xticks else []
 return {'schema_version':1,'id':c['comparison_group_id'],'label':c['label'],'entity':c['entity'],'facility':c['facility'],'indicator':c['indicator'],'unit':c['unit'],'source_id':c['source_id'],'source_edition_raw':c['source_edition_raw'],'scope_note':'僅同一已核原刊／原件及原對象範圍；選定來源不代表所有歷年填報方法一致。未知點不畫0，僅連接原已核准線段。','records':records,'lines':line_pairs,'x_ticks':xticks,'mobile_x_ticks':mobile,'y_ticks':yticks}
def input_hashes(root):
 names=['VERSION','site/phase2.html','site/phase3.html','derived/phase2/annotations.jsonl.gz','docs/phase3-profiles.json','docs/phase3-contract.json','scripts/build_lightweight_site.py','scripts/reader_transport.py']
 names.extend(str(p.relative_to(root)) for p in sorted((root/'site/light-src').glob('*')) if p.is_file())
 names.append(str(record_io.path_for(root,'data/combined/observations.jsonl').relative_to(root)))
 return {name:sha((root/name).read_bytes()) for name in names}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--output',type=Path);ap.add_argument('--data-only',action='store_true');args=ap.parse_args();root=args.root.resolve();dest=(args.output or root/'site/light').resolve();version=(root/'VERSION').read_text().strip()
 before=input_hashes(root);d2=payload(root,'phase2');d3=payload(root,'phase3')
 if d2['summary']['dataset_version']!=version or d3['dataset_version']!=version:raise ValueError('Rebuild reviewed readers before the lightweight export')
 annotations={a['record_key']:a for a in read_rows(root/'derived/phase2/annotations.jsonl.gz')};originals={'canonical:'+r['observation_id']:r for r in record_io.rows(root,'data/combined/observations.jsonl')}
 queries={q['profile_id']:q for q in table(d3,'queries')};assets={};series_count=0;point_count=0;edge_count=0
 def asset(data):
  body=stable(data);name='data/'+sha(body)+'.json';write(dest/name,body);assets[name]={'sha256':sha(body),'bytes':len(body)};return name
 def entry(c):
  nonlocal series_count,point_count,edge_count
  data=build_series(c,annotations,originals);url=asset(data);series_count+=1;point_count+=len(c['source_points']);edge_count+=len(c['segments'])
  return {'id':c['comparison_group_id'],'url':url,'label':c['label'],'entity':c['entity'],'facility':c['facility'],'indicator':c['indicator'],'unit':c['unit'],'source_id':c['source_id'],'years':c['years']}
 raw=[entry(c) for c in d2['examples'].values()];raw.sort(key=lambda x:x['label']);preferred=next((x['id'] for x in raw if x['source_id']=='ncl-yearbook-114-statistics' and x['indicator']=='圖書借閱冊數'),raw[0]['id'])
 original_url=asset({'schema_version':1,'mode':'original','id':'all-original-series','title':'全部已核原刊數列','description':f'完整列出既有{len(raw)}組合格原刊數列；不混合來源或自行補值。','purpose':'original-series','years':sorted({y for c in raw for y in c['years']}),'series':raw,'default_selection':{'status':'original_published_group','explanation':['僅顯示所選原刊分組，不跨來源加總。'],'series_ids':[preferred],'selected_record_keys':[]},'intervals':{},'full_data_url':REPOSITORY+'/releases/tag/v'+version,'scope_note':'原刊限定的可對照期間，不認證所有歷年調查方法一致。'})
 grouped=defaultdict(list)
 for c in d3['charts'].values():grouped[c['profile_id']].append(c)
 profiles=[]
 for p in d3['profiles']:
  pid=p['id'];series=[entry(c) for c in grouped[pid]];series.sort(key=lambda x:x['label']);available={x['id'] for x in series};q=queries[pid]
  def selection(obj,groups):return {'status':obj.get('selection_status'),'explanation':obj.get('selection_explanation',[]),'series_ids':[g for g in groups if g in available],'selected_record_keys':obj.get('selected_record_keys',[]) if available else [],'trend_summary':obj.get('trend_summary',{})}
  intervals={k:selection(v,v['comparison_group_ids']) for k,v in d3['interval_queries'].get(pid,{}).items()} or None
  data={'schema_version':1,'mode':'profile','id':pid,'title':p['title'],'description':p.get('description',''),'purpose':p['default_purpose'],'years':d3['chart_year_options'][pid],'series':series,'default_selection':selection(q,d3['default_chart_groups'][pid]),'intervals':intervals,'full_data_url':REPOSITORY+'/releases/tag/v'+version,'scope_note':'圖表只展示符合既有繪圖條件的原數列。單期、未知及未解記錄仍完整保留於資料包；沒有數列不表示官方沒有資料。'}
  profiles.append({'id':pid,'title':p['title'],'description':p.get('description',''),'purpose':p['default_purpose'],'catalog_url':asset(data)})
 manifest={'schema_version':1,'viewer_version':VIEWER_VERSION,'data_version':version,'title':'臺灣公共圖書館統計','repository_url':REPOSITORY,'release_url':REPOSITORY+'/releases/tag/v'+version,'default_profile_id':'national-ncl-book-loans-panel','original_catalog_url':original_url,'profiles':profiles,'scope_note':'可追溯的原報數列。資料仍有缺口；不推算補值，不把所有來源視為同一全臺歷年面板。'}
 manifest_body=stable(manifest);write(dest/'manifest.json',manifest_body)
 if not args.data_only:
  for name in ('index.html','app.css','app.js'):
   p=root/'site/light-src'/name
   if not p.is_file():raise FileNotFoundError('Frontend source missing: '+name)
   write(dest/name,p.read_bytes())
 write(dest/'.nojekyll',b'')
 if input_hashes(root)!=before:raise ValueError('Source input changed while producing the website')
 outputs={str(p.relative_to(root)):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(dest.rglob('*')) if p.is_file() and p.is_relative_to(root)}
 summary={'schema_version':1,'viewer_version':VIEWER_VERSION,'dataset_version':version,'source_charts':{'phase2':len(d2['examples']),'phase3':len(d3['charts']),'rendered_series_entries':series_count,'displayed_point_entries':point_count,'approved_line_entries':edge_count},'registered_profiles':len(profiles),'precomputed_interval_queries':sum(len(d) for d in d3['interval_queries'].values()),'unique_data_shards':len(assets),'all_existing_charts_exported':True,'statistical_values_or_definitions_modified':False,'inputs_sha256':before,'outputs':outputs,'manifest_bytes':len(manifest_body),'data_only':args.data_only,'public_url':'https://poplolioi11.github.io/tw-public-library-statistics/'}
 write(root/'docs/light-site-summary.json',stable(summary));print(json.dumps({k:v for k,v in summary.items() if k not in ('inputs_sha256','outputs')},ensure_ascii=False))
if __name__=='__main__':main()
