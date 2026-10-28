#!/usr/bin/env python3
"""365-day conditional official-source checks; changed originals require review."""
import argparse, datetime, hashlib, json, urllib.error, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def run(root=ROOT,offline=False):
    docs=json.loads((root/'raw/discovered-20261028/documents.json').read_text())['documents']
    statepath=root/'data/discovered_20261028_monitor_state.json'
    states=json.loads(statepath.read_text()) if statepath.exists() else {}
    now=datetime.datetime.now(datetime.timezone.utc);checked=[];changes=[];errors=[]
    for doc in docs:
        sid=doc['candidate_id'];prior=states.get(sid,{})
        previous=datetime.datetime.fromisoformat(prior.get('checked_at',doc['retrieved_at']))
        if offline or (now-previous).total_seconds()<doc.get('recheck_interval_days',365)*86400:continue
        headers={'User-Agent':'tw-public-library-statistics/1.0 (historical-source-version-check)'}
        if prior.get('etag'):headers['If-None-Match']=prior['etag']
        if prior.get('last_modified'):headers['If-Modified-Since']=prior['last_modified']
        try:
            try:
                response=urllib.request.urlopen(urllib.request.Request(doc['official_url'],headers=headers),timeout=30)
            except urllib.error.HTTPError as error:
                if error.code!=304:raise
                states[sid]={**prior,'checked_at':now.isoformat(),'status':'not_modified_304'};checked.append(sid);continue
            with response:
                body=response.read(80*1024*1024+1)
                if len(body)>80*1024*1024:raise ValueError('Source exceeds reviewed download-size limit; retain prior')
                digest=hashlib.sha256(body).hexdigest();changed=digest!=doc['source_sha256']
                states[sid]={'checked_at':now.isoformat(),'etag':response.headers.get('ETag'),
                             'last_modified':response.headers.get('Last-Modified'),'http_final_url':response.geturl(),
                             'observed_sha256':digest,'accepted_sha256':doc['source_sha256'],
                             'status':'changed_pending_source_rights_definition_review' if changed else 'unchanged_sha256'}
                if changed:
                    # Private bounded cache only; not an accepted publication
                    # input. The previous pinned original remains intact.
                    pending=root/'tmp/discovered-source-versions';pending.mkdir(parents=True,exist_ok=True)
                    name=sid+'-'+digest+Path(doc['source_local_path']).suffix
                    target=pending/name
                    if not target.exists():target.write_bytes(body)
                    changes.append({'source_id':sid,'official_url':doc['official_url'],'previous_sha256':doc['source_sha256'],
                                    'observed_sha256':digest,'status':'not_ingested_requires_review'})
                checked.append(sid)
        except Exception as error:
            errors.append({'source_id':sid,'error':str(error),'previous_verified_batch_retained':True})
    statepath.write_text(json.dumps(states,ensure_ascii=False,indent=2)+'\n')
    return {'policy':'365d; official URLs only, conditional HTTP; changes held, never auto-published',
            'checked_sources':len(checked),'changed_sources':changes,'errors':errors,'offline':offline}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--offline',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.root.resolve(),a.offline),ensure_ascii=False))
