#!/usr/bin/env python3
"""Anonymous public-source acquisition, immutable versions, deterministic normalization."""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json, re, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]
BASE='https://publibstat.nlpi.edu.tw'
CHART_URL=BASE+'/Frontend/Dynamic/BindTypeSelect'
PAGE=BASE+'/Frontend/Dynamic/ImportantInfomation'
UA='TaiwanPublicLibraryStatistics/0.1 (public-data research; conditional requests)'
TOPICS={
 'Bacol00282':('全年圖書資訊借閱人次','flow_calendar_year','人次'),
 'Bacol00283':('全年圖書資訊借閱冊數','flow_calendar_year','冊次'),
 'Bacol00284':('全國推廣活動場次','flow_calendar_year','場次'),
 'Bacol00285':('全國推廣活動人次','flow_calendar_year','人次'),
 'Bacol00286':('館舍面積級距分布（館舍間數）','stock_year_end','間'),
 'Bacol00287':('圖書館人員編制','stock_year_end','人'),
 'Bacol00288':('圖書及非書資料收藏','stock_year_end',None),
 'Bacol00289':('全年購買圖書資料費-預算','annual_financial','元'),
 'Bacol00290':('全年購買圖書資料費-決算','annual_financial','元'),
 'Bacol00291':('圖書館數(閱覽室,巡迴車等)','stock_year_end',None),
}
META={
 'portal-news-index':(BASE+'/','GET',None,'metadata'),
 'catalog-6425':('https://data.gov.tw/dataset/6425','GET',None,'metadata'),
 'ogdl-1':('https://data.gov.tw/license','GET',None,'license'),
 'public-year-selector':(PAGE,'GET',None,'metadata'),
 'public-chart-script':(BASE+'/Areas/Frontend/Scripts/ImportantInformation.js','GET',None,'interface_evidence'),
 'current-definitions':(BASE+'/Frontend/Definition/DefinitionItem','GET',None,'definition_reference'),
 'current-scope':(BASE+'/Frontend/About/AboutpLibSTAT','GET',None,'scope_reference'),
 'policy-20260917':(BASE+'/Frontend/News/IndexDataView','POST',{'key':'News000050'},'policy_reference'),
}
def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
def load(path,default): return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def specs(years):
 out=[]
 for sid,(url,method,body,kind) in META.items(): out.append(dict(source_id=sid,url=url,method=method,body=body,kind=kind,year=None))
 # Exactly the resource explicitly linked by the OGDL metadata. Do not extrapolate its license to other Year parameters.
 out.append(dict(source_id='ogdl-api-2023',url=BASE+'/api/API/ConsolidationData?Year=2023',method='GET',body=None,kind='licensed_api',year=2023))
 for year in years:
  for topic in TOPICS:
   out.append(dict(source_id=f'public-chart-{year}-{topic}',url=CHART_URL,method='POST',body=dict(Years=str(year),Topic=topic,SelectLevel=[],SelectCity=['-1']),kind='public_national_chart',year=year,topic=topic))
 return out

def validate_response(spec,raw):
 if spec['kind'] in ('public_national_chart','licensed_api'):
  data=json.loads(raw.decode('utf-8-sig'))
  if not isinstance(data,list) or not data or not all(isinstance(x,dict) for x in data): raise ValueError('Empty/non-list data response')
  if spec['kind']=='licensed_api':
   if not all(str(x.get('縣市別','')).startswith(str(spec['year'])+'-') for x in data): raise ValueError('Wrong reference year')
   if len([x for x in data if x['縣市別']==str(spec['year'])+'-全國'])!=1: raise ValueError('National row missing/duplicate')
  else:
   if not all('ItemName' in x for x in data): raise ValueError('Unexpected chart schema')
   if spec['topic'] in ('Bacol00282','Bacol00283','Bacol00287','Bacol00288') and any(x['ItemName']!='全國' for x in data): raise ValueError('Non-public geographic scope returned')
   for row in data:
    if not any(k.startswith('ItemAmount') for k in row): raise ValueError('No values')
  return data
 if len(raw)<100: raise ValueError('Unexpectedly short metadata')
 text=raw.decode('utf-8-sig')
 markers={'portal-news-index':['最新消息','公共圖書館統計'],'catalog-6425':['公共圖書館統計','Year=2023','https://data.gov.tw/license'],'ogdl-1':['不可撤回','政府資料開放授權條款'],'current-definitions':['統計項目定義','靜態資料','動態資料'],'current-scope':['不含學校圖書館'],'public-chart-script':['BindTypeSelect','SelectCity']}
 if any(marker not in text for marker in markers.get(spec['source_id'],[])):raise ValueError('Metadata identity/content check failed')
 if spec['source_id']=='policy-20260917' and '自115年起' not in raw.decode('utf-8-sig'): raise ValueError('Policy did not return expected news')
 if spec['source_id']=='public-year-selector' and 'ddl_Year' not in raw.decode('utf-8-sig'): raise ValueError('Missing year selector')
 return None

def fetch_one(spec,old):
 headers={'User-Agent':UA,'Referer':PAGE}
 body=spec['body']
 if body is not None:
  if spec['kind']=='policy_reference':
   payload=urllib.parse.urlencode(body).encode();headers['Content-Type']='application/x-www-form-urlencoded'
  else: payload=json.dumps(body,separators=(',',':')).encode();headers['Content-Type']='application/json; charset=utf-8'
 else: payload=None
 if old.get('etag'):headers['If-None-Match']=old['etag']
 if old.get('last_modified'):headers['If-Modified-Since']=old['last_modified']
 checked=now()
 try:
  with urllib.request.urlopen(urllib.request.Request(spec['url'],data=payload,headers=headers,method=spec['method']),timeout=50) as resp:
   raw=resp.read();ct=resp.headers.get('Content-Type','');etag=resp.headers.get('ETag');modified=resp.headers.get('Last-Modified');final_url=resp.url
  validate_response(spec,raw)
  h=sha(raw);suffix='.json' if spec['kind'] in ('public_national_chart','licensed_api') else ('.js' if spec['source_id'].endswith('script') else '.html')
  relative=f'raw/snapshots/{spec["source_id"]}/{h}{suffix}';p=ROOT/relative;p.parent.mkdir(parents=True,exist_ok=True)
  if not p.exists():p.write_bytes(raw)
  entry={**spec,'snapshot_id':'sha256:'+h,'sha256':h,'snapshot_path':relative,'retrieved_at':checked,'last_checked_at':checked,'etag':etag,'last_modified':modified,'content_type':ct,'response_url':final_url}
  # retrieved_at describes this immutable body first observed; checks are separately recorded.
  if old.get('sha256')==h:entry['retrieved_at']=old['retrieved_at']
  return entry,'unchanged' if old.get('sha256')==h else ('revised' if old else 'new')
 except urllib.error.HTTPError as e:
  if e.code==304 and old:
   return {**old,'last_checked_at':checked},'not_modified'
  raise

def acquire(years,limit=None):
 (ROOT/'data').mkdir(parents=True,exist_ok=True)
 manifest_path=ROOT/'data/source_manifest.json';manifest=load(manifest_path,{'schema_version':'1.0.0','sources':{}});old_sources=manifest['sources'];todo=specs(years)
 if limit:todo=[s for s in todo if s['source_id'] in limit]
 events=[];errors=[]
 # Two anonymous requests maximum; no source discovery through guessed year parameters.
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(fetch_one,s,old_sources.get(s['source_id'],{})):s for s in todo}
  for f in as_completed(futures):
   s=futures[f]
   try:
    entry,status=f.result();old=old_sources.get(s['source_id']);old_sources[s['source_id']]=entry
    if status in ('new','revised'):
     event={'observed_at':now(),'source_id':s['source_id'],'previous_sha256':old.get('sha256') if old else None,'sha256':entry['sha256'],'snapshot_path':entry['snapshot_path'],'event':status};events.append(event)
     with (ROOT/'data/source_history.jsonl').open('a',encoding='utf-8') as journal:
      journal.write(json.dumps(event,ensure_ascii=False)+'\n');journal.flush()
      import os
      os.fsync(journal.fileno())
    print(f'{s["source_id"]}: {status}',flush=True)
   except Exception as e:errors.append({'source_id':s['source_id'],'at':now(),'error':str(e)});print(f'{s["source_id"]}: ERROR {e}',flush=True)
   dump(manifest_path,manifest)
   time.sleep(.1)
 dump(ROOT/'data/last_acquisition.json',{'completed_at':now(),'checked_sources':len(todo),'changed_sources':len(events),'errors':errors})
 return errors

def parse_number(raw):
 if raw is None:return None,'source_null'
 if isinstance(raw,bool):return None,'unparsed'
 if isinstance(raw,(int,float)):return raw,'reported'
 s=str(raw).strip()
 if s=='':return None,'source_blank'
 if s in ('-','—','–','…','...','N/A','NA'):return None,'source_marker'
 s=s.replace(',','').replace('，','')
 if re.fullmatch(r'-?\d+',s):return int(s),'reported'
 if re.fullmatch(r'-?\d+\.\d+',s):
  from decimal import Decimal
  return str(Decimal(s)),'reported_decimal'
 return None,'unparsed'

def rowid(series,year,geo):return 'obs-'+sha(f'{series}|{year}|{geo}'.encode())[:22]
def pointer_part(s):return str(s).replace('~','~0').replace('/','~1')
def chart_series(topic,row,key):
 # Only columns with a nonempty legend are rendered by the official chart. ItemAmount3=0/null legend is a placeholder, not an observation.
 label=row['ItemName'] if key=='ItemAmount' else row.get('legendName'+key.removeprefix('ItemAmount'))
 return label

def chart_definition(topic,label):
 title,period,unit=TOPICS[topic];notes=[]
 if topic=='Bacol00286':notes.append('ItemName為原始面積級距，數值是館舍間數，不是平方公尺。級距端點依來源原字串，未自行修正重疊邊界。')
 if topic=='Bacol00288':
  unit=None;notes.append('異質單位彙總：冊、種、片、件等；不能統一稱為冊，也不能將三類相加後當成圖書冊數。')
 if topic=='Bacol00291':
  unit='台' if label=='巡迴車' else ('個' if label in ('社群網站','館外服務站') else '所')
 if topic=='Bacol00287':notes.append('現行一般靜態規則為年底；各年人員類別與約用／派遣歸類未逐年核實。')
 if topic in ('Bacol00282','Bacol00283'):
  notes.append('圖書列含圖書與非書、排除電子資源；電子書／電子書刊歷年定義適用性待核。人次不是去重人數。')
 notes.append('現行定義僅作參照，未證實自2011年全程相同；原圖表年度值按其原樣保留。')
 return {'title':title+'｜'+label,'group':title,'source_label':label,'unit':unit,'temporal_kind':period,'definition_status':'current_reference_historical_applicability_unverified','notes':notes}

def normalize():
 manifest=load(ROOT/'data/source_manifest.json',{})['sources'];defs=load(ROOT/'research/definitions.json',{});field_defs={x['raw_name']:x for x in defs.get('fields',[])}
 observations=[];dictionary={};coverage=[];errors=[];reused=0;parsed=0
 signature=sha(Path(__file__).read_bytes()+(ROOT/'research/definitions.json').read_bytes())
 for sid,src in sorted(manifest.items()):
  if src['kind'] not in ('public_national_chart','licensed_api'):continue
  raw=(ROOT/src['snapshot_path']).read_bytes()
  if sha(raw)!=src['sha256']:raise ValueError('Snapshot hash mismatch '+sid)
  cache_path=ROOT/'data/cache'/f'{sid}.json';cache=load(cache_path,{})
  if cache.get('signature')==signature and cache.get('source_sha256')==src['sha256']:
   observations.extend(cache['observations']);coverage.append(cache['coverage']);errors.extend(cache['issues']);reused+=1
   for item in cache['indicators']:
    series=item['series_id']
    if series in dictionary:dictionary[series]['observed_years']=sorted(set(dictionary[series]['observed_years']+item['observed_years']))
    else:dictionary[series]=item
   continue
  parsed+=1
  data=validate_response(src,raw);year=src['year'];count_before=len(observations)
  def emit(series,label,rawvalue,locator,geo,scope,definition,source_field):
   value,status=parse_number(rawvalue);did='def-'+series
   dictionary.setdefault(series,{'series_id':series,'definition_id':did,**definition,'source_family':src['kind'],'source_url':PAGE if src['kind']=='public_national_chart' else src['url'],'definition_url':BASE+'/Frontend/Definition/DefinitionItem','observed_years':[]})
   if year not in dictionary[series]['observed_years']:dictionary[series]['observed_years'].append(year)
   period=definition['temporal_kind'];notes=definition.get('notes',[])
   record={'observation_id':rowid(series,year,geo+'|'+scope),'data_year':year,'geography':geo,'geographic_scope':scope,'population_scope':'公立公共圖書館（不含學校圖書館）；依來源年度填報範圍','series_id':series,'indicator':label,'source_field':source_field,'value':value,'raw_value':rawvalue,'value_status':status,'zero_interpretation':'source_returned_zero_true_zero_or_uncollected_unconfirmed' if value==0 else None,'collection_year':None,'publication_year':None,'unit':definition.get('unit'),'unit_status':'source_or_definition' if definition.get('unit') else 'not_uniform_or_unconfirmed','temporal_kind':period,'period_start':f'{year}-01-01' if period in ('flow_calendar_year','annual_financial') else None,'period_end':f'{year}-12-31','period_basis':'current_general_rule_historical_applicability_unverified','definition_id':did,'definition_source_id':'current-definitions','definition_sha256':manifest.get('current-definitions',{}).get('sha256'),'definition_retrieved_at':manifest.get('current-definitions',{}).get('retrieved_at'),'indicator_group':definition.get('group'),'definition_status':definition.get('definition_status'),'source_id':sid,'source_url':src['url'],'source_page_url':PAGE if src['kind']=='public_national_chart' else 'https://data.gov.tw/dataset/6425','source_method':src['method'],'source_request':json.dumps(src['body'],ensure_ascii=False,separators=(',',':')) if src['body'] else None,'source_locator':locator,'source_sha256':src['sha256'],'source_snapshot_path':src['snapshot_path'],'retrieved_at':src['retrieved_at'],'snapshot_distribution':'included','license_status':'OGDL-1.0_explicit_link_2023' if src['kind']=='licensed_api' else 'publicly_published_statistical_facts','license_url':'https://data.gov.tw/license' if src['kind']=='licensed_api' else None,'comparability':'not_certified_across_years_or_source_families','notes':'；'.join(notes+(['來源回傳0，未證實是實際零或當年未蒐集／系統補零。'] if value==0 else []))}
   if status=='unparsed':errors.append({'observation_id':record['observation_id'],'issue':'unparsed_value','raw_value':rawvalue})
   observations.append(record)
  if src['kind']=='public_national_chart':
   topic=src['topic']
   for i,row in enumerate(data):
    for key,rawvalue in row.items():
     if not key.startswith('ItemAmount'):continue
     label=chart_series(topic,row,key)
     if not label:continue
     series='chart-'+topic+'-'+sha(label.encode())[:10];definition=chart_definition(topic,label)
     emit(series,definition['title'],rawvalue,f'/{i}/{key}','全國','national_total',definition,label)
  else:
   for i,row in enumerate(data):
    orig=row['縣市別'];geo=orig.split('-',1)[1];scope='national_total' if geo=='全國' else ('county_excluding_national_alternative' if '(不含國立館)' in geo else 'county_default_includes_national_where_applicable')
    for ordinal,(key,rawvalue) in enumerate(row.items(),1):
     if key=='縣市別':continue
     definition=field_defs.get(key)
     if not definition:raise ValueError('Unknown API field requires dictionary review: '+key)
     definition={**definition,'notes':list(definition.get('notes',[])),'title':key,'source_label':key}
     u=definition.get('unit')
     if u in ('自購或自行建置','包含於總館藏量下') or (u and u.startswith('混合單位')):
      definition['notes'].append('原欄未提供單一可確認單位；括號中的敘述不是單位。');definition['unit']=None
     elif u=='所／個，依原名':definition['unit']='所' if '(所)' in key else '個'
     elif u=='冊數':definition['unit']='冊'
     elif u=='種數':definition['unit']='種'
     series='api-'+sha((definition.get('group','')+'|'+key).encode())[:14]
     emit(series,key,rawvalue,f'/{i}/{pointer_part(key)}',geo,scope,definition,key)
  c={'source_id':sid,'year':year,'scope':src['kind'],'topic':src.get('topic'),'rows_in_source':len(data),'observations':len(observations)-count_before,'status':'acquired_and_normalized'};coverage.append(c)
  subset=observations[count_before:];source_series={r['series_id'] for r in subset}
  dump(cache_path,{'signature':signature,'source_sha256':src['sha256'],'observations':subset,'indicators':[{**dictionary[k],'observed_years':[year]} for k in source_series],'coverage':c,'issues':[e for e in errors if e['observation_id'] in {r['observation_id'] for r in subset}]})
 # Different interfaces remain distinct source series; no double counting as unique official facts.
 ids=[x['observation_id'] for x in observations]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate observations')
 observations.sort(key=lambda x:(x['source_id'],x['geography'],x['series_id']))
 cols=list(observations[0]) if observations else []
 out=ROOT/'data/observations.jsonl'
 with out.open('w',encoding='utf-8') as f:
  for r in observations:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
 with (ROOT/'data/observations.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(observations)
 dump(ROOT/'data/indicators.json',list(dictionary.values()));dump(ROOT/'data/coverage.json',coverage);dump(ROOT/'data/quality_issues.json',errors)
 summary={'built_at':now(),'records':len(observations),'source_series':len(dictionary),'chart_years':sorted({s['year'] for s in manifest.values() if s['kind']=='public_national_chart'}),'licensed_county_years':sorted({s['year'] for s in manifest.values() if s['kind']=='licensed_api'}),'national_chart_observations':sum(r['source_id'].startswith('public-chart') for r in observations),'explicitly_licensed_api_observations':sum(r['source_id'].startswith('ogdl-api') for r in observations),'source_snapshots':len(manifest),'quality_issues':len(errors),'reparsed_sources':parsed,'reused_normalized_sources':reused,'not_all_taiwan_history_complete':True,'coverage_boundary':'2011–2025 normal public national charts, explicitly OGDL-linked 2023 national/county API; earlier separately published tables inventoried independently'}
 dump(ROOT/'data/summary.json',summary)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
 return summary

def policy_digest(src):
 import html
 text=(ROOT/src['snapshot_path']).read_text(encoding='utf-8-sig')
 # News body, excluding layout scripts, visit counters, cookies and update footer.
 match=re.search(r'<p><p style=.*?(?=<input id="DataView_News_NewsID")',text,re.S)
 if not match:raise ValueError('Policy article locator changed; needs review')
 body=html.unescape(re.sub('<[^>]+>',' ',match.group(0)))
 return sha(re.sub(r'\s+','',body).encode('utf-8'))

def policy_news_digest(src):
 import html
 text=(ROOT/src['snapshot_path']).read_text(encoding='utf-8-sig')
 matches=re.findall(r'<a[^>]*title="([^"]+)"[^>]*data-key="(News\d+)"',text)
 relevant=sorted(set((key,html.unescape(title)) for title,key in matches if any(t in title for t in ('數據','公開','申請','授權'))))
 if not relevant:raise ValueError('Policy news index locator requires review')
 return sha(json.dumps(relevant,ensure_ascii=False).encode())

def due_sources(all_specs,force=False):
 manifest=load(ROOT/'data/source_manifest.json',{'sources':{}})['sources'];latest=max((x['year'] or 0 for x in all_specs),default=0);result=[]
 for spec in all_specs:
  old=manifest.get(spec['source_id'])
  if force or not old:result.append(spec['source_id']);continue
  interval=7 if spec['kind'] not in ('public_national_chart','licensed_api') else (90 if spec['kind']=='licensed_api' else (14 if spec['year']>=latest-1 else 365))
  age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(old['last_checked_at'])).total_seconds()/86400
  if age>=interval:result.append(spec['source_id'])
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['fetch','build','update']);p.add_argument('--years',default=None,help='optional inclusive lo:hi; default all years offered by the public UI');p.add_argument('--source',action='append');p.add_argument('--refresh-all',action='store_true');p.add_argument('--accept-policy-current',action='store_true',help='maintainer has reviewed the saved current policy');a=p.parse_args()
 if a.command in ('fetch','update'):
  # Metadata first: a change in access policy suspends automatic data expansion for review.
  meta_due=due_sources(specs([]),a.refresh_all)
  meta_due=[x for x in meta_due if x in META]
  if meta_due:
   if acquire([],meta_due):raise SystemExit('Metadata incomplete; preserved previous data.')
  manifest=load(ROOT/'data/source_manifest.json',{})['sources']
  src=manifest['public-year-selector'];text=(ROOT/src['snapshot_path']).read_text(encoding='utf-8-sig')
  block=re.search(r'<select[^>]*id="ddl_Year".*?</select>',text,re.S).group(0);offered={int(x) for x in re.findall(r'value="(\d{4})"',block)}
  years=sorted(offered)
  if a.years:
   lo,hi=map(int,a.years.split(':'));years=list(range(lo,hi+1))
  if not set(years)<=offered:raise ValueError('Requested years absent from public UI')
  policy=policy_digest(manifest['policy-20260917']);news=policy_news_digest(manifest['portal-news-index']);approved=load(ROOT/'data/reviewed_policy.json',{})
  if not approved or a.accept_policy_current:dump(ROOT/'data/reviewed_policy.json',{'sha256':policy,'news_digest':news,'reviewed_at':now(),'basis':'public national charts plus exact OGDL-linked 2023 resource; no applicant-only data'})
  elif approved['sha256']!=policy or approved.get('news_digest') not in (None,news):raise SystemExit('POLICY_CHANGED: new snapshot saved; review it before data acquisition. Existing data preserved.')
  candidates=specs(years);due=due_sources(candidates,a.refresh_all)
  if a.source:due=[x for x in due if x in a.source]
  due=[x for x in due if x not in META]
  errors=acquire(years,due) if due else []
  if not due:dump(ROOT/'data/last_acquisition.json',{'completed_at':now(),'checked_sources':0,'changed_sources':0,'errors':[],'note':'No sources due; latest two years every14d, older years every365d, explicit2023 every90d, metadata every7d'})
  if errors:raise SystemExit('Acquisition incomplete; saved completed snapshots. Rerun selected failed sources.')
 if a.command in ('build','update'):normalize()
if __name__=='__main__':main()
