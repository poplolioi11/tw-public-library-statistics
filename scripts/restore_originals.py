#!/usr/bin/env python3
"""Restore exact omitted originals; --phase1-only restores four reviewed workbooks.
Default retains historical restoration. Downloads confer no redistribution rights.
"""
import argparse,datetime,hashlib,io,json,os,re,ssl,urllib.request,urllib.error,urllib.parse,zipfile
from pathlib import Path
from fetch_local_history import hccg_context
R=Path(__file__).resolve().parents[1]
def sha(body):return hashlib.sha256(body).hexdigest()
def fetch(url):
 p=urllib.parse.urlsplit(url)
 url=urllib.parse.urlunsplit((p.scheme,p.netloc,urllib.parse.quote(p.path,safe="/%:@!$&'()*+,;=-._~"),urllib.parse.quote(p.query,safe="=&;%:+,/?@!$'()*-._~"),''))
 req=urllib.request.Request(url,headers={'User-Agent':'TaiwanPublicLibraryStatistics (restore exact reviewed public source)'})
 try:
  with urllib.request.urlopen(req,timeout=50) as response:return response.read()
 except urllib.error.URLError as error:
  if not isinstance(error.reason,ssl.SSLCertVerificationError):raise
  # Prior observed intermediate; trusted roots and hostname verification remain.
  with urllib.request.urlopen(req,timeout=50,context=hccg_context()) as response:return response.read()
def restore_legacy(root=R):
 registries=[root/'raw/ncl-historical/documents.json',root/'raw/ncl-historical/dgbas-documents.json',root/'raw/ncl-extension-documents.json',root/'raw/ncl-supporting-documents.json']
 for registry in registries:
  if not registry.exists():continue
  for src in json.loads(registry.read_text()):
   target=root/src['local_path'];expected=src['sha256']
   if target.exists() and sha(target.read_bytes())==expected:continue
   body=fetch(src['download_url']);kind=src.get('content_kind','pdf')
   if kind not in {'pdf','html'} or (kind=='pdf' and not body.startswith(b'%PDF')) or sha(body)!=expected:raise ValueError('Original version changed; review before accepting '+src['download_url'])
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body);print('restored',target.name)
 county_meta=root/'raw/segis-history/metadata.json'
 if county_meta.exists():
  metadata=json.loads(county_meta.read_text());original=root/metadata['source_raw_path']
  if not original.exists():
   import subprocess,sys
   subprocess.run([sys.executable,str(root/'scripts/fetch_segis_history.py'),'--refresh'],cwd=root,check=True)
def restore_phase1(root=R,source_root=None,fetcher=None):
 root=Path(root);path=root/'raw/phase1_local_sources/sources.json'
 if not path.exists():return []
 destination=Path(source_root) if source_root else Path(os.environ.get('TW_LIBRARY_PHASE1_SOURCE_ROOT',str(root/'raw/phase1_local_sources/originals')))
 results=[]
 for source in json.loads(path.read_text())['sources']:
  name=source['source_filename'];expected=source['source_sha256'];kind=source['format'].lower()
  if Path(name).name!=name or not re.fullmatch('[a-f0-9]{64}',expected) or kind not in {'ods','xlsx'}:raise ValueError('Invalid reviewed phase1 specification')
  target=destination/name
  if target.is_file() and sha(target.read_bytes())==expected:
   results.append({'source_id':source['source_id'],'status':'cached_SHA_verified'});continue
  if target.exists() or target.is_symlink():raise ValueError('Existing phase1 original differs or symlink unavailable; do not overwrite: '+name)
  body=(fetcher or fetch)(source['source_download_url'])
  if sha(body)!=expected:raise ValueError('Phase1 version changed; previous approved original retained, review required: '+name)
  if not zipfile.is_zipfile(io.BytesIO(body)):raise ValueError('Not a ZIP spreadsheet: '+name)
  with zipfile.ZipFile(io.BytesIO(body)) as z:
   if kind=='ods' and ('mimetype' not in z.namelist() or z.read('mimetype')!=b'application/vnd.oasis.opendocument.spreadsheet'):raise ValueError('Invalid ODS original')
   if kind=='xlsx' and 'xl/workbook.xml' not in z.namelist():raise ValueError('Invalid XLSX original')
  destination.mkdir(parents=True,exist_ok=True);tmp=target.with_name(target.name+'.restore.tmp');tmp.write_bytes(body);tmp.replace(target)
  receipt={'source_id':source['source_id'],'source_download_url':source['source_download_url'],'source_sha256':expected,'restored_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_license_status':source['license_status'],'distribution':'private_local_cache_not_public_bundle'}
  target.with_name(target.name+'.restore.private.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
  results.append({'source_id':source['source_id'],'status':'restored_exact_reviewed_SHA'})
 return results
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase1-only',action='store_true');p.add_argument('--include-phase1',action='store_true');p.add_argument('--source-root',type=Path);a=p.parse_args()
 if not a.phase1_only:restore_legacy()
 if a.phase1_only or a.include_phase1:print(json.dumps({'phase1':restore_phase1(source_root=a.source_root)},ensure_ascii=False))
if __name__=='__main__':main()

projection_registry=R/'raw/omitted-originals.json'
if __name__=='__main__' and projection_registry.exists() and '--phase1-only' not in __import__('sys').argv:
 for item in json.loads(projection_registry.read_text())['omitted_originals']:
  path=R/item['source_snapshot_path']
  if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['source_sha256']:continue
  request=urllib.request.Request(item['source_url'],headers={'User-Agent':'TaiwanPublicLibraryStatistics/0.6.0 (restore specified source)'})
  with urllib.request.urlopen(request,timeout=50) as response:body=response.read()
  if hashlib.sha256(body).hexdigest()!=item['source_sha256']:raise ValueError('Official original changed; review before accepting new source version')
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
  print('restored specified statistical source',path.name)
