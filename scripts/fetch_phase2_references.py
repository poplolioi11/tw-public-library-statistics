#!/usr/bin/env python3
"""Check only recorded definition references. Never adopt a changed body or publish HTML.

--target explicitly restores exact recorded versions outside the public package.
Unchanged files are reused; a different SHA requires a fresh source review.
"""
import argparse,hashlib,json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path);a=p.parse_args()
 sources=json.loads((ROOT/'raw/phase2-definitions/current-reference-sources.json').read_text())['sources'];results=[]
 for item in sources:
  expected=item.get('source_sha256');entry={'evidence_id':item['evidence_id'],'source_url':item['source_url'],'expected_sha256':expected}
  if not expected:entry['status']='no_accepted_body_version';results.append(entry);continue
  filename=item['evidence_id']+'-'+expected+'.private.html';target=a.target/filename if a.target else None
  if target and not target.exists() and a.target.is_dir():
   matches=[f for f in a.target.glob('*'+expected+'*.private.html') if f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==expected]
   if matches:target=matches[0]
  if target and target.exists():
   actual=hashlib.sha256(target.read_bytes()).hexdigest()
   if actual!=expected:raise ValueError('Existing reference body differs; refusing to overwrite '+item['evidence_id'])
   entry['status']='reused_exact_body';results.append(entry);continue
  try:
   request=urllib.request.Request(item['source_url'],headers={'User-Agent':'TaiwanPublicLibraryStatistics/source-reference-check'})
   with urllib.request.urlopen(request,timeout=40) as response:body=response.read();entry['final_url']=response.url
   actual=hashlib.sha256(body).hexdigest();entry['observed_sha256']=actual
   entry['status']='unchanged' if actual==expected else 'changed_requires_review'
   if actual==expected and target:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
  except Exception as exc:entry.update(status='request_failed',error=type(exc).__name__)
  results.append(entry)
 print(json.dumps({'reference_only_not_historical_effective_dates':True,'results':results},ensure_ascii=False,indent=2))
 return 1 if any(x['status'] in {'changed_requires_review','request_failed'} for x in results) else 0
if __name__=='__main__':sys.exit(main())
