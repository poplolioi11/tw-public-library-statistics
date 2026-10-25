"""Lossless JSONL transport for research copies and bounded Git distributions."""
import gzip,hashlib,json,os
from pathlib import Path,PurePosixPath
PROFILE='data/combined/publication-profile.json'
COMPRESSIBLE={'data/combined/observations.jsonl','data/component_records.jsonl'}
def compressed(root):
 p=Path(root)/PROFILE
 if not p.exists():return False
 profile=json.loads(p.read_text())
 if profile.get('schema_version')!='1.0.0' or profile.get('jsonl_compression')!='gzip':raise ValueError('Unknown JSONL publication profile')
 return True
def path_for(root,relative):
 p=PurePosixPath(relative)
 if p.is_absolute() or '..' in p.parts:raise ValueError('Record path must remain inside the dataset')
 return Path(root)/(relative+'.gz' if relative in COMPRESSIBLE and compressed(root) else relative)
def open_text(root,relative):
 path=path_for(root,relative)
 return gzip.open(path,'rt',encoding='utf-8') if path.suffix=='.gz' else path.open(encoding='utf-8')
def rows(root,relative='data/combined/observations.jsonl'):
 with open_text(root,relative) as stream:
  for line in stream:
   if line.strip():yield json.loads(line)
def body(root,relative='data/combined/observations.jsonl'):
 path=path_for(root,relative)
 return gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
def logical_sha(root,relative='data/combined/observations.jsonl'):
 path=path_for(root,relative)
 if not path.exists():return None
 digest=hashlib.sha256()
 opener=gzip.open if path.suffix=='.gz' else open
 with opener(path,'rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
 return digest.hexdigest()
def write(root,relative,records):
 target=path_for(root,relative);target.parent.mkdir(parents=True,exist_ok=True)
 temporary=target.with_name(target.name+'.tmp')
 try:
  with temporary.open('wb') as raw:
   if target.suffix=='.gz':
    with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as stream:
     for row in records:stream.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())
   else:
    for row in records:raw.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())
  os.replace(temporary,target)
 except BaseException:
  temporary.unlink(missing_ok=True);raise
 return target
