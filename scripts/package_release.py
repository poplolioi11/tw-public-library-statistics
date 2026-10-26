#!/usr/bin/env python3
"""Create immutable, auditable local release. No uploading or publishing."""
import argparse,datetime,hashlib,json,zipfile
from pathlib import Path
import record_io
R=Path(__file__).resolve().parents[1]
from cohort_registry import load as load_cohorts
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--force-new',action='store_true',help='archive a reviewed code/document revision even when canonical facts did not change');args=parser.parse_args()
 version=(R/'VERSION').read_text().strip() if (R/'VERSION').exists() else '0.1.0'
 manifest=[];selected={}
 root_files=['README.md','AI_USAGE.md','LICENSE.md','LICENSE_CODE','COVERAGE.md','CHANGELOG.md','CITATION.cff','VERSION','requirements.txt','requirements-lock.txt','llms.txt','datapackage.json','.gitignore']
 for name in root_files:
  p=R/name
  if not p.exists():raise FileNotFoundError(p)
  selected[name]=p.read_bytes()
 for directory,extensions in [('scripts',{'.py','.json'}),('tests',{'.py'}),('docs',{'.md','.json'}),('research',{'.md','.json'}),('derived',{'.csv','.json','.jsonl'}),('data/combined',{'.csv','.json','.jsonl','.sqlite','.gz'})]:
  for p in (R/directory).rglob('*'):
   if p.is_file() and p.suffix in extensions and '__pycache__' not in p.parts and not any('private' in part.lower() for part in p.relative_to(R).parts):selected[str(p.relative_to(R))]=p.read_bytes()
 for name in ['observations.jsonl','indicators.json','source_manifest.json','source_history.jsonl','historical_source_history.jsonl','reviewed_historical_cohorts.json','reviewed_policy.json','component_records.jsonl','component_records.jsonl.gz','component_quality.json','summary.json','coverage.json']:
  p=R/'data'/name
  if p.exists():selected[str(p.relative_to(R))]=p.read_bytes()
 selected['site/index.html']=(R/'site/index.html').read_bytes();selected['site/template.html']=(R/'site/template.html').read_bytes()
 # Include exact statistical JSON snapshots; website HTML/JS and full PDFs are intentionally omitted.
 directories=['raw/snapshots','raw/official-local','raw/ncl-historical','raw/ncl-additional','raw/ncl-earlier','raw/segis-history']
 for group in load_cohorts(R) or []:directories.extend(group.get('raw_directories',[]))
 for directory in dict.fromkeys(directories):
  for p in (R/directory).rglob('*'):
   if not p.is_file() or p.suffix not in {'.json','.jsonl','.pem','.crt'}:continue
   if directory=='raw/ncl-historical' and p.name not in {'documents.json','dgbas-documents.json','gap-tables-metadata.json'}:continue
   if any('private' in part.lower() for part in p.relative_to(R).parts) or 'page-text' in p.name:continue
   selected[str(p.relative_to(R))]=p.read_bytes()
 selected['raw/ncl-extension-documents.json']=(R/'raw/ncl-extension-documents.json').read_bytes()
 if (R/'raw/ncl-supporting-documents.json').exists():selected['raw/ncl-supporting-documents.json']=(R/'raw/ncl-supporting-documents.json').read_bytes()
 for path,body in sorted(selected.items()):manifest.append({'path':path,'sha256':sha(body),'bytes':len(body)})
 meta={'version':version,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'canonical_sha256':record_io.logical_sha(R),'files':manifest,'omitted':['NCL/DGBAS full PDFs','website raw HTML/JavaScript','working normalized cache','local automation settings'],'external_publication':False}
 checksums=json.dumps(meta,ensure_ascii=False,indent=2).encode();selected['RELEASE_MANIFEST.json']=checksums
 history_path=R/'data/release_history.jsonl';history=[json.loads(x) for x in history_path.read_text().splitlines()] if history_path.exists() else []
 for previous in history:
  if previous['canonical_sha256']==meta['canonical_sha256'] and not args.force_new:
   print(json.dumps({'status':'existing_data_version','release_path':previous['release_path'],'canonical_sha256':meta['canonical_sha256']},ensure_ascii=False));return
 name='tw-public-library-statistics-v'+version+'.zip' if not history else 'tw-public-library-statistics-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.zip'
 target=R/'dist'/name;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():raise FileExistsError('Immutable archive already exists '+str(target))
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for path,body in sorted(selected.items()):z.writestr('tw-public-library-statistics/'+path,body)
 with zipfile.ZipFile(target) as z:
  if z.testzip():raise ValueError('ZIP validation failed')
  for item in manifest:
   if sha(z.read('tw-public-library-statistics/'+item['path']))!=item['sha256']:raise ValueError('Archive member hash mismatch')
 event={'created_at':meta['created_at'],'version':meta['version'],'canonical_sha256':meta['canonical_sha256'],'archive_sha256':sha(target.read_bytes()),'archive_bytes':target.stat().st_size,'release_path':str(target),'file_count':len(selected)}
 with history_path.open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
 (R/'data/last_release.json').write_text(json.dumps(event,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(event,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
