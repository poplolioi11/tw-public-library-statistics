#!/usr/bin/env python3
"""Fetch only resources explicitly linked by allowlisted OGDL public catalogues.

No inferred year URLs, no authentication, no private endpoints. Immutable raw bytes
and catalogue evidence are retained by SHA256. Defaults to the entire exposed JSON
resource list; CSV fallback is used only if a catalogue has no JSON resource.
"""
import argparse, csv, datetime as dt, hashlib, html, io, json, re, ssl, subprocess, urllib.request
from functools import lru_cache
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'raw'/'official-local'
OUT=ROOT/'derived'
SEEDS=[127807,117921,84379,84915,164580,164579,164577,164576,164575,164568,168119,173850,177249]
UA='Taiwan-public-library-statistics/0.1 (source-linked public-data research)'

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
@lru_cache(maxsize=1)
def hccg_context():
    try: import certifi
    except ImportError: from pip._vendor import certifi
    cert=RAW/'tls'/'hccg-intermediate.pem'
    # Supplement only this observed intermediate after validating it against
    # public certifi roots. Do not disable certificate or hostname verification.
    check=subprocess.run(['openssl','verify','-CAfile',certifi.where(),str(cert)],capture_output=True,text=True)
    if check.returncode: raise ValueError('AIA intermediate root verification failed: '+check.stdout+check.stderr)
    ctx=ssl.create_default_context(cafile=certifi.where())
    ctx.load_verify_locations(cafile=str(cert))
    assert ctx.check_hostname and ctx.verify_mode==ssl.CERT_REQUIRED
    return ctx

def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':UA})
    with urllib.request.urlopen(req, timeout=18, context=hccg_context() if urlparse(url).hostname=='odws.hccg.gov.tw' else None) as r:
        return r.read(), {'retrieved_at':utc(),'final_url':r.url,'http_status':r.status,'headers':safe_headers(dict(r.headers))}
def snap(path,b):
    if not path.exists(): path.write_bytes(b)
    assert path.read_bytes()==b

def safe_headers(headers):
    allowed={'content-type','content-length','last-modified','etag','content-disposition','cache-control'}
    return {k:v for k,v in headers.items() if k.lower() in allowed}

def public_metadata(value):
    if isinstance(value,list): return [public_metadata(v) for v in value]
    if isinstance(value,dict):
        return {k:(safe_headers(v) if k=='headers' and isinstance(v,dict) else public_metadata(v)) for k,v in value.items()}
    return value

def save_revision(cache, record):
    record=public_metadata(record)
    b=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
    digest=sha(b)
    revision=cache.parent/f'{cache.stem}-revision-{digest}.json'
    snap(revision,b)
    history=cache.parent/f'{cache.stem}-revisions.jsonl'
    line=json.dumps({'recorded_at':utc(),'metadata_sha256':digest,'metadata_path':str(revision.relative_to(ROOT)),
                     'last_check_status':record.get('last_check_status'),'raw_sha256':record.get('source_sha256') or record.get('catalog_sha256')},ensure_ascii=False)
    with history.open('a') as fh: fh.write(line+'\n')
    cache.write_bytes(b)
    return record

def valid_cached_resource(record):
    if not record or record.get('status')!='downloaded': return False
    path=ROOT/record.get('raw_path','')
    return path.is_file() and sha(path.read_bytes())==record.get('source_sha256')

def first_retrieval_for_sha(directory, uid, digest, retrieved_at):
    dates=[retrieved_at]
    for path in directory.glob(f'resource-{uid}.metadata*.json'):
        previous=json.loads(path.read_text())
        if previous.get('source_sha256')==digest and previous.get('source_retrieved_at'):
            dates.append(previous['source_retrieved_at'])
    return min(dates,key=lambda x:dt.datetime.fromisoformat(x.replace('Z','+00:00')))

def catalog(dataset_id, refresh=False):
    url=f'https://data.gov.tw/dataset/{dataset_id}'
    directory=RAW/f'catalog-{dataset_id}'; directory.mkdir(parents=True,exist_ok=True)
    cache=directory/'catalog-record.json'
    old=public_metadata(json.loads(cache.read_text())) if cache.exists() else None
    if old and not refresh: return old
    if old: save_revision(cache,old)
    try:
        b,http=get(url); digest=sha(b); filename=f'catalog-{digest}.html';snap(directory/filename,b)
        s=b.decode('utf-8-sig'); dataset=None
        for v in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',s,re.S):
            j=json.loads(v)
            for o in j if isinstance(j,list) else [j]:
                if o.get('@type')=='Dataset':dataset=o
        if not dataset: raise ValueError('No Dataset JSON-LD')
        text=html.unescape(re.sub('<[^>]+>',' ',s)); text=re.sub(r'\s+',' ',text)
        if dataset.get('license')!='https://data.gov.tw/license' or '政府資料開放授權條款' not in text:
            raise ValueError('Explicit OGDL evidence absent; refusing new resource fetch')
    except Exception as e:
        if not old: raise
        previous=ROOT/old.get('catalog_path','')
        if not previous.is_file() or sha(previous.read_bytes())!=old.get('catalog_sha256'): raise
        old.update(last_check_status='failed',freshness='stale_after_failed_check',last_check_at=utc(),
                   last_check_error={'type':type(e).__name__,'message':str(e)})
        old['last_checked_at']=old['last_check_at']
        return save_revision(cache,old)
    ds={'dataset_id':str(dataset_id),'source_url':url,'source_title':dataset['name'],
        'source_agency':dataset.get('creator',{}).get('name'),'license_status':'verified_open',
        'license_name':'政府資料開放授權條款-第1版','license_url':dataset['license'],
        'license_evidence':'Catalogue JSON-LD license plus visible government open-data licence statement.',
        'catalog_sha256':digest,'catalog_path':str((directory/filename).relative_to(ROOT)),
        'catalog_http':http,'catalog_metadata':dataset,'resources':[],
        'last_check_status':'success','freshness':'current','last_check_at':utc(),'last_checked_at':http['retrieved_at'],'last_check_error':None}
    resources=dataset.get('distribution',[])
    selected=[r for r in resources if r.get('encodingFormat','').upper()=='JSON']
    if not selected:selected=[r for r in resources if r.get('encodingFormat','').upper()=='CSV']
    # Resource titles are text following each observed download anchor; keep best
    # effort label only. Observation periods always come from actual raw rows.
    for idx,r in enumerate(selected,1):
        u=r.get('contentUrl'); ext=r['encodingFormat'].lower()
        if not u:continue
        pos=s.find(html.escape(u,quote=True)); pos=pos if pos>=0 else s.find(u)
        near=html.unescape(re.sub('<[^>]+>',' ',s[max(0,pos):pos+1800])) if pos>=0 else ''
        near=re.sub(r'\s+',' ',near)
        ds['resources'].append({'resource_index':idx,'source_download_url':u,'format':ext,'nearby_catalog_text':near[:700]})
    return save_revision(cache,ds)

def resource(ds,r,refresh=False):
    directory=RAW/f'catalog-{ds["dataset_id"]}'
    url=r['source_download_url']; uid=sha(url.encode())[:16]
    cache=directory/f'resource-{uid}.metadata.json'
    old=public_metadata(json.loads(cache.read_text())) if cache.exists() else None
    if old and not refresh and valid_cached_resource(old): return old
    if old: save_revision(cache,old)
    meta={**r,'dataset_id':ds['dataset_id'],'source_url':ds['source_url'],
          'source_title':ds['source_title'],'source_agency':ds['source_agency'],
          'license_status':ds['license_status'],'license_url':ds['license_url'],
          'catalog_sha256':ds['catalog_sha256'],'status':'failed'}
    try:
        b,http=get(url); digest=sha(b)
        path=directory/f'resource-{uid}-{digest}.{r["format"]}'
        snap(path,b)
        if r['format']=='json':
            obj=json.loads(b.decode('utf-8-sig'))
            if not isinstance(obj,list) or any(not isinstance(x,dict) for x in obj):
                raise ValueError('Expected complete JSON array of objects, not a paginated wrapper')
        else:obj=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
        first_retrieved_at=first_retrieval_for_sha(directory,uid,digest,http['retrieved_at'])
        meta.update(status='downloaded',source_sha256=digest,source_retrieved_at=first_retrieved_at,
                    raw_path=str(path.relative_to(ROOT)),row_count=len(obj),http=http,
                    fields=sorted({k for row in obj for k in row}),last_check_status='success',
                    freshness='current',last_check_at=utc(),last_checked_at=http['retrieved_at'],last_check_error=None)
    except Exception as e:
        error={'type':type(e).__name__,'message':str(e)}
        if valid_cached_resource(old):
            old.update(last_check_status='failed',freshness='stale_after_failed_check',last_check_at=utc(),last_check_error=error)
            old['last_checked_at']=old['last_check_at']
            return save_revision(cache,old)
        meta.update(error_type=type(e).__name__,error=str(e),attempted_at=utc(),last_check_status='failed',last_check_error=error)
    return save_revision(cache,meta)

def load_rows(meta):
    b=(ROOT/meta['raw_path']).read_bytes();assert sha(b)==meta['source_sha256']
    return json.loads(b.decode('utf-8-sig')) if meta['format']=='json' else list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))

def resource_title(meta):
    ds=json.loads((RAW/f'catalog-{meta["dataset_id"]}'/'catalog-record.json').read_text())
    s=(ROOT/ds['catalog_path']).read_text()
    for block in re.findall(r'<li class="resource-item"[^>]*>.*?</li>',s,re.S):
        if meta['source_download_url'] in html.unescape(block):
            text=html.unescape(re.sub('<[^>]+>',' ',block))
            return re.sub(r'^(?:JSON|CSV)\s*檢視資料\s*','',re.sub(r'\s+',' ',text).strip()).strip()
    return ''

def normalize(meta, row, i):
    county=row.get('地區') or ('新竹市' if '新竹市' in meta['source_title'] else '臺中市' if '臺中市' in meta['source_title'] else '')
    period=str(row.get('資料時間日期') or row.get('統計年月') or row.get('年度') or '')
    item=str(row.get('項目') or '')
    unit_match=re.search(r'單位[：:]\s*([^）)]+)',item)
    unit=unit_match.group(1).strip() if unit_match else ''
    title=meta.get('resource_title','')
    hint=re.search(r'(?<![0-9])([0-9]{3,4})(?:年|_)',title)
    period_hint=hint.group(1) if hint else ''
    if '數值' in row and not any(str(row.get(k,'')).strip() for k in ['項目','欄位名稱','數值','資料時間日期']):
        return []
    base={'county':county,'source_id':f'local-{meta["dataset_id"]}-{meta["resource_index"]:02d}',
        'source_title':meta['source_title'],'source_agency':meta['source_agency'],
        'source_url':meta['source_url'],'source_download_url':meta['source_download_url'],
        'source_sha256':meta['source_sha256'],'source_retrieved_at':meta['source_retrieved_at'],
        'source_freshness':meta.get('freshness','current'),'source_last_check_status':meta.get('last_check_status','success'),
        'source_locator':f'JSON array[{i-1}]' if meta['format']=='json' else f'CSV row {i+1}',
        'license_status':meta['license_status'],'license_url':meta['license_url'],
        'period_raw':period,'period_catalog_hint':period_hint,'period_hint_source':'resource_title' if period_hint else '',
        'period_effective':period or period_hint,'period_effective_basis':'observation_field' if period else 'resource_title' if period_hint else 'unknown',
        'resource_title':title,'periodicity_raw':row.get('資料週期',''),
        'geography_code_raw':row.get('縣市別代碼',''),'district_code_raw':row.get('行政區域代碼',''),
        'facility_raw':row.get('館藏地') or row.get('館別') or '',
        'original_fields':json.dumps(row,ensure_ascii=False,separators=(',',':'))}
    if '數值' in row:
        return [{**base,'metric_group_raw':item,'metric_raw':str(row.get('欄位名稱','')),'unit_raw':unit,
                 'value_raw':str(row['數值']),'value_status':'as_published'}]
    excluded={'統計年月','館藏地','機關代碼','縣市別代碼','郵遞區號','館別','年度','新竹市代碼','更新日期'}
    return [{**base,'metric_group_raw':'','metric_raw':k,'unit_raw':'','value_raw':str(v),'value_status':'as_published'}
            for k,v in row.items() if k not in excluded]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refresh',action='store_true');args=ap.parse_args()
    RAW.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    datasets=[];catalog_errors=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        future={ex.submit(catalog,x,args.refresh):x for x in SEEDS}
        for f in as_completed(future):
            try:datasets.append(f.result())
            except Exception as e:catalog_errors.append({'dataset_id':str(future[f]),'error':str(e),'checked_at':utc()})
    # Follow only actual related-catalogue links for the same Hsinchu borrowing
    # series. No numeric identifier or year is guessed.
    seen_ids={str(x) for x in SEEDS}
    for discovery_round in range(3):
        discovered=set()
        for ds in datasets:
            if '新竹市公共圖書館圖書借閱量統計表' not in ds['source_title']: continue
            page=(ROOT/ds['catalog_path']).read_text()
            for href,body in re.findall(r'<a[^>]*href="(/dataset/[0-9]+)"[^>]*>(.*?)</a>',page,re.S):
                title=html.unescape(re.sub('<[^>]+>','',body)).strip()
                if re.fullmatch(r'(?:[0-9]+年)?新竹市公共圖書館圖書借閱量統計表',title):
                    candidate=href.rsplit('/',1)[-1]
                    if candidate not in seen_ids: discovered.add(candidate)
        if not discovered: break
        seen_ids.update(discovered)
        with ThreadPoolExecutor(max_workers=5) as ex:
            future={ex.submit(catalog,x,args.refresh):x for x in sorted(discovered)}
            for f in as_completed(future):
                try: datasets.append(f.result())
                except Exception as e:catalog_errors.append({'dataset_id':str(future[f]),'error':str(e),'checked_at':utc()})
    docs=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        future=[ex.submit(resource,ds,r,args.refresh) for ds in datasets for r in ds['resources']]
        for f in as_completed(future):docs.append(f.result())
    docs.sort(key=lambda x:(x['dataset_id'],x['resource_index']))
    rows=[];raw_rows=0
    for d in docs:
        if d['status']!='downloaded':continue
        d['resource_title']=resource_title(d)
        obj=load_rows(d);assert len(obj)==d['row_count'];raw_rows+=len(obj)
        for i,row in enumerate(obj,1):rows.extend(normalize(d,row,i))
    # Preserve all published occurrences. A duplicate flag allows use without
    # silent double counting; source-specific metadata remains on every row.
    seen={}
    for i,row in enumerate(rows,1):
        row['record_id']=f'local-observation-{i:06d}'
        key=(row['county'],row['period_effective'],row['periodicity_raw'],row['facility_raw'],row['metric_group_raw'],row['metric_raw'],row['unit_raw'],row['value_raw'])
        row['duplicate_of']=seen.get(key,'');seen.setdefault(key,row['record_id'])
    value_groups={}
    for row in rows:
        key=tuple(row[k] for k in ['county','period_effective','periodicity_raw','facility_raw','metric_group_raw','metric_raw','unit_raw'])
        value_groups.setdefault(key,set()).add(row['value_raw'])
    for row in rows:
        key=tuple(row[k] for k in ['county','period_effective','periodicity_raw','facility_raw','metric_group_raw','metric_raw','unit_raw'])
        row['conflicting_values']='true' if len(value_groups[key])>1 else 'false'
    fields=list(rows[0]) if rows else []
    with (OUT/'local_historical_long.csv').open('w',encoding='utf-8',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    manifest={'generated_at':utc(),'script':'scripts/fetch_local_history.py','seed_catalog_ids':[str(x) for x in SEEDS],'all_discovered_catalog_ids':sorted(seen_ids),
      'tls_supplementation_evidence':'raw/official-local/tls/verification.json',
      'discovery_policy':'Only exact public catalogue URLs found through search or linked related datasets. No inferred year-resource URLs.',
      'data_scope':'All JSON resources exposed by each successful allowlisted catalogue (CSV only if no JSON); no API pagination or private endpoints.',
      'catalogues':sorted(datasets,key=lambda d:d['dataset_id']),'catalog_errors':catalog_errors,'documents':docs,
      'summary':{'catalogue_count':len(datasets),'downloaded_documents':sum(d['status']=='downloaded' for d in docs),
                 'failed_documents':sum(d['status']!='downloaded' for d in docs),'raw_rows':raw_rows,
                 'long_rows':len(rows),'blank_non_observation_raw_rows':sum(1 for d in docs if d['status']=='downloaded' for rr in load_rows(d) if '數值' in rr and not any(str(rr.get(k,'')).strip() for k in ['項目','欄位名稱','數值','資料時間日期'])),'exact_observation_duplicate_rows':sum(bool(r['duplicate_of']) for r in rows),
                 'conflicting_value_groups':sum(len(values)>1 for values in value_groups.values()),
                 'counties':sorted({r['county'] for r in rows}),'periods_raw':sorted({r['period_raw'] for r in rows}),'periods_effective':sorted({r['period_effective'] for r in rows})},
      'caveats':['This is the complete exposed resource package for selected local catalogues, not complete all-Taiwan history.',
                 'Missing months or years remain missing. Catalogue titles do not override row-level observation periods.',
                 'Monthly and annual observations retain separate published periodicities. Do not sum annual and monthly counts.',
                 'No hard merge with NLPI observations; scope may differ, especially national libraries.',
                 'All original fields retained verbatim in each row JSON. No canonical unit conversion or imputation.',
                 'Rows with all observation fields blank remain in raw documents and are excluded from the observation long table.',
                 'period_catalog_hint is read from the exact exposed resource title and never silently replaces period_raw.',
                 'Duplicate rows remain with duplicate_of; use the flag to avoid silent double counting.',
                 'HTTP TLS certificate checks remain enabled. Any failed downloads remain explicit gaps.']}
    manifest=public_metadata(manifest)
    archive=RAW/'manifests';archive.mkdir(exist_ok=True)
    save_revision(archive/'current-manifest.json',manifest)
    (OUT/'local_historical_metadata.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest['summary'],ensure_ascii=False),flush=True)
    return 0 if rows else 1
if __name__=='__main__':raise SystemExit(main())
