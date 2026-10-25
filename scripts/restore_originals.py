#!/usr/bin/env python3
"""Restore omitted official PDFs by exact metadata URLs; verify their expected SHA256."""
import hashlib,json,ssl,urllib.request,urllib.error
from pathlib import Path
from fetch_local_history import hccg_context
R=Path(__file__).resolve().parents[1]
registries=[R/'raw/ncl-historical/documents.json',R/'raw/ncl-historical/dgbas-documents.json',R/'raw/ncl-extension-documents.json',R/'raw/ncl-supporting-documents.json']
for registry in registries:
 if not registry.exists():continue
 for src in json.loads(registry.read_text()):
  target=R/src['local_path'];expected=src['sha256']
  if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==expected:continue
  url=src['download_url'];req=urllib.request.Request(url,headers={'User-Agent':'TaiwanPublicLibraryStatistics/0.2 (restore exact public source)'})
  try:
   with urllib.request.urlopen(req,timeout=50) as response:body=response.read()
  except urllib.error.URLError as error:
   if not isinstance(error.reason,ssl.SSLCertVerificationError):raise
   # Same observed TWCA intermediate, root-validated by hccg_context. Hostname verification remains required.
   with urllib.request.urlopen(req,timeout=50,context=hccg_context()) as response:body=response.read()
  kind=src.get('content_kind','pdf')
  if kind not in {'pdf','html'} or (kind=='pdf' and not body.startswith(b'%PDF')) or hashlib.sha256(body).hexdigest()!=expected:raise ValueError('Original version changed; review before accepting '+url)
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body);print('restored',target.name)

# The query system returns changing form state. Reacquire a complete current public
# table when the old HTML is omitted, then create a new source version after verification.
county_meta=R/'raw/segis-history/metadata.json'
if county_meta.exists():
 metadata=json.loads(county_meta.read_text());original=R/metadata['source_raw_path']
 if not original.exists():
  import subprocess,sys
  subprocess.run([sys.executable,str(R/'scripts/fetch_segis_history.py'),'--refresh'],cwd=R,check=True)

projection_registry=R/'raw/omitted-originals.json'
if projection_registry.exists():
 for item in json.loads(projection_registry.read_text())['omitted_originals']:
  path=R/item['source_snapshot_path']
  if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['source_sha256']:continue
  request=urllib.request.Request(item['source_url'],headers={'User-Agent':'TaiwanPublicLibraryStatistics/0.4.0 (restore specified source)'})
  with urllib.request.urlopen(request,timeout=50) as response:body=response.read()
  if hashlib.sha256(body).hexdigest()!=item['source_sha256']:raise ValueError('Official original changed; review before accepting new source version')
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
  print('restored specified statistical source',path.name)
