#!/usr/bin/env python3
"""Hash-gated phase1 batches and14-day monitoring of four exact known URLs.

No source discovery, canonical union, publishing or automatic source-version
acceptance. Full changed bodies are private candidate cache only.
"""
import argparse,datetime,hashlib,json,os,subprocess,sys,urllib.request,urllib.parse
from pathlib import Path
from phase1_source_registry import load,digest
ROOT=Path(__file__).resolve().parents[1]

def stable_write(path,body):
    body=body.encode() if isinstance(body,str) else body
    if path.exists() and path.read_bytes()==body:return
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(body);tmp.replace(path)

def json_write(path,value):stable_write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def source_path(root,entry,source_root=None):
    return Path(source_root)/entry['source_filename'] if source_root is not None and entry.get('source_filename') else root/entry['path']

def signatures(root,group,source_root=None):
    original_map={x['path']:x for x in group['originals']};result={}
    for name in ['scripts/'+group['script'],*group['inputs']]:
        path=source_path(root,original_map[name],source_root) if name in original_map else root/name
        if not path.is_file():raise FileNotFoundError('Required reviewed phase1 input missing; previous outputs retained: '+name)
        actual=digest(path)
        if name in original_map and actual!=original_map[name]['sha256']:
            raise ValueError('Reviewed phase1 original changed; review required, previous outputs retained: '+name)
        result[name]=actual
    return result

def output_hashes(root,group):return {name:digest(root/name) for name in group['outputs']}

def snapshot(root,names):
    result={}
    for name in names:
        p=root/name
        result[name]=(p.read_bytes(),p.stat().st_atime_ns,p.stat().st_mtime_ns) if p.is_file() else None
    return result

def rollback(root,previous):
    for name,old in previous.items():
        path=root/name
        if old is None:path.unlink(missing_ok=True)
        else:
            if not path.is_file() or path.read_bytes()!=old[0]:stable_write(path,old[0])
            os.utime(path,ns=(old[1],old[2]))

def run_batches(root=ROOT,source_root=None,runner=None):
    if source_root is None:source_root=os.environ.get('TW_LIBRARY_PHASE1_SOURCE_ROOT')
    root=Path(root);registry=load(root)
    if registry is None:return {'enabled':False,'batches':[]}
    # Validate *all* original inputs before invoking any batch extractor.
    plans=[(g,signatures(root,g,source_root)) for g in registry['batches']]
    results=[]
    for group,inputs in plans:
        statepath=root/'data'/(group['id']+'_extraction_state.json')
        old=json.loads(statepath.read_text()) if statepath.exists() else None
        current=output_hashes(root,group)
        same=old and old.get('inputs')==inputs and old.get('outputs')==current and all(current.values())
        reviewed_bootstrap=(old is None and inputs==group['reviewed_inputs'] and current==group['reviewed_outputs'] and all(current.values()))
        if same or reviewed_bootstrap:
            if reviewed_bootstrap:json_write(statepath,{'schema_version':'1.0.0','layer':group['layer'],'inputs':inputs,'outputs':current})
            results.append({'id':group['id'],'status':'cached_verified_outputs','bootstrap_state':bool(reviewed_bootstrap)});continue
        before=snapshot(root,[*group['outputs'],str(statepath.relative_to(root))])
        args=list(group.get('args',['--offline']))
        if source_root is not None and group.get('accepts_source_root'):args+=['--source-root',str(source_root)]
        try:
            if runner:runner(group['script'],*args)
            else:subprocess.run([sys.executable,str(root/'scripts'/group['script']),*args],cwd=root,check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            after=output_hashes(root,group)
            if not all(after.values()):raise FileNotFoundError('Extractor omitted reviewed phase1 output: '+group['id'])
            if signatures(root,group,source_root)!=inputs:raise ValueError('Phase1 input changed during extraction; previous outputs retained')
            json_write(statepath,{'schema_version':'1.0.0','layer':group['layer'],'inputs':inputs,'outputs':after})
        except BaseException:
            rollback(root,before);raise
        results.append({'id':group['id'],'status':'rebuilt','changed_output_paths':[p for p in after if current[p]!=after[p]]})
    return {'enabled':True,'canonical_union_permitted':False,'batches':results}

def iso(value):return datetime.datetime.fromisoformat(value.replace('Z','+00:00'))

def fetch_exact(url):
    p=urllib.parse.urlsplit(url)
    encoded=urllib.parse.urlunsplit((p.scheme,p.netloc,urllib.parse.quote(p.path,safe="/%:@!$&'()*+,;=-._~"),urllib.parse.quote(p.query,safe="=&;%:+,/?@!$'()*-._~"),''))
    request=urllib.request.Request(encoded,headers={'User-Agent':'tw-public-library-statistics exact-reviewed-source-monitor'})
    with urllib.request.urlopen(request,timeout=25) as response:
        body=response.read(25*1024*1024+1);final=response.url;content_type=response.headers.get('Content-Type','')
    if len(body)>25*1024*1024:raise ValueError('Reviewed source monitor limit25MiB exceeded')
    return body,final,content_type

def monitor_sources(root=ROOT,offline=False,now=None,fetcher=None):
    root=Path(root);registry=load(root)
    if registry is None:return {'enabled':False,'sources':[]}
    policy=registry['monitor_policy'];manifest=root/policy['source_manifest']
    sources=json.loads(manifest.read_text())['sources'];now=now or datetime.datetime.now(datetime.timezone.utc)
    statepath=root/'data/phase1_source_monitor_state.private.json';old=json.loads(statepath.read_text()) if statepath.exists() else {'schema_version':'1.0.0','sources':{}}
    state=json.loads(json.dumps(old));results=[];events=[];interval=datetime.timedelta(days=policy['interval_days'])
    cache_config=os.environ.get('TW_LIBRARY_PHASE1_MONITOR_CACHE')
    cache=Path(cache_config) if cache_config else None
    for source in sources:
        sid=source['source_id'];prior=state['sources'].get(sid,{})
        last=prior.get('next_due_basis_at') or source['source_retrieved_at'];due=now-iso(last)>=interval
        if offline or not due:
            results.append({'source_id':sid,'status':'offline_cached_only' if offline else 'not_due','next_due_at':(iso(last)+interval).isoformat(),'review_required':prior.get('review_required',False)});continue
        entry=dict(prior);entry.update(source_id=sid,source_url=source['source_download_url'],approved_original_sha256=source['source_sha256'],last_checked_at=now.isoformat())
        try:
            body,final,ct=(fetcher or fetch_exact)(source['source_download_url']);observed=hashlib.sha256(body).hexdigest()
            entry.update(last_HTTP_success_at=now.isoformat(),last_response_sha256=observed,final_url=final,next_due_basis_at=now.isoformat(),last_check_error=None)
            if observed==source['source_sha256']:
                entry.update(status='approved_SHA_unchanged',last_verified_approved_SHA_at=now.isoformat())
            else:
                entry.update(status='review_required_candidate_only',review_required=True,candidate_sha256=observed,
                             candidate_body_retained=False,candidate_format_magic_valid=body.startswith(b'PK'),
                             candidate_content_type=ct,approved_original_replaced=False)
                if cache is not None:
                    target=cache/(sid+'-'+observed+'.private.'+source['format'].lower())
                    if target.exists() and digest(target)!=observed:raise ValueError('Private immutable candidate cache collision')
                    stable_write(target,body);entry.update(private_candidate_path=str(target),candidate_body_retained=True)
        except Exception as exc:
            # No next_due_basis advance on failure: the next normal scheduled
            # run may retry, while earlier successful metadata remains intact.
            entry.update(status='request_failed_previous_approved_version_retained',last_check_error=type(exc).__name__,approved_original_replaced=False)
        state['sources'][sid]=entry;events.append(entry)
        results.append({k:entry.get(k) for k in ('source_id','status','review_required','last_check_error','last_response_sha256')})
    if events:
        json_write(statepath,state)
        history=root/'data/phase1_source_monitor_history.private.jsonl';history.parent.mkdir(parents=True,exist_ok=True)
        with history.open('a') as f:
            for event in events:f.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n')
    return {'enabled':True,'interval_days':policy['interval_days'],'known_URLs_only':True,'sources':results,'requests_made':len(events),
            'review_required':any(x.get('review_required') for x in results),'approved_originals_modified':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--source-root',type=Path,default=os.environ.get('TW_LIBRARY_PHASE1_SOURCE_ROOT'));p.add_argument('--offline',action='store_true');a=p.parse_args()
    result=run_batches(a.root,a.source_root);result['monitor']=monitor_sources(a.root,a.offline);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
