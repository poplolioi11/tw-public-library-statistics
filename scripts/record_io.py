"""Lossless, profile-declared transport for research and public distributions."""
import gzip,hashlib,io,json,os,re,shutil,tempfile
from contextlib import contextmanager
from pathlib import Path,PurePosixPath
PROFILE='data/combined/publication-profile.json'
COMPRESSIBLE={'data/combined/observations.jsonl','data/component_records.jsonl'}

def safe_relative(relative):
 if not isinstance(relative,str) or not relative or '\\' in relative or re.match(r'^[A-Za-z]:',relative):raise ValueError('Record path must be a safe relative dataset path')
 p=PurePosixPath(relative)
 if not p.parts or p.is_absolute() or '..' in p.parts or str(p)!=relative or relative.endswith('/'):raise ValueError('Record path must remain inside the dataset')
 return relative

def checked_path(root,relative):
 relative=safe_relative(relative);base=Path(root).resolve();path=Path(root)/relative
 if not path.resolve().is_relative_to(base):raise ValueError('Record path leaves the dataset through a symlink')
 return path

def publication_profile(root):
 p=Path(root)/PROFILE
 if not p.exists():return None
 p=checked_path(root,PROFILE)
 profile=json.loads(p.read_text())
 if not isinstance(profile,dict) or profile.get('schema_version')!='1.0.0' or profile.get('jsonl_compression')!='gzip':raise ValueError('Unknown JSONL publication profile')
 extra=profile.get('lossless_gzip_paths',[])
 if not isinstance(extra,list) or any(not isinstance(name,str) for name in extra):raise ValueError('lossless_gzip_paths must be a list of relative logical paths')
 for name in extra:
  safe_relative(name)
  if name==PROFILE or name.endswith('.gz'):raise ValueError('lossless_gzip_paths must name uncompressed logical files')
 if len(extra)!=len(set(extra)):raise ValueError('Duplicate lossless gzip logical path')
 return profile

def compressed(root):return publication_profile(root) is not None

def path_for(root,relative):
 relative=safe_relative(relative);profile=publication_profile(root)
 compressed_paths=COMPRESSIBLE|set(profile.get('lossless_gzip_paths',[])) if profile else set()
 return checked_path(root,relative+'.gz' if relative in compressed_paths else relative)
def open_text(root,relative,encoding='utf-8',newline=None):
 path=path_for(root,relative)
 return gzip.open(path,'rt',encoding=encoding,newline=newline) if path.suffix=='.gz' else path.open(encoding=encoding,newline=newline)

@contextmanager
def materialized_file(root,relative):
 """Yield a local file; gzip transports are fully decoded into a readonly temp."""
 path=path_for(root,relative)
 if path.suffix!='.gz':
  yield path
  return
 with tempfile.TemporaryDirectory(prefix='library-materialized-') as directory:
  target=Path(directory)/PurePosixPath(relative).name.removesuffix('.gz')
  with gzip.open(path,'rb') as source,target.open('wb') as output:shutil.copyfileobj(source,output,length=1024*1024)
  target.chmod(0o400)
  yield target

@contextmanager
def write_text(root,relative,encoding='utf-8',newline=None):
 """Atomically write text, with deterministic gzip only when declared."""
 target=path_for(root,relative);target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.tmp')
 try:
  with temporary.open('wb') as raw:
   if target.suffix=='.gz':
    with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as binary:
     with io.TextIOWrapper(binary,encoding=encoding,newline=newline) as text:yield text
   else:
    with io.TextIOWrapper(raw,encoding=encoding,newline=newline) as text:yield text
  os.replace(temporary,target)
 except BaseException:
  temporary.unlink(missing_ok=True);raise

def write_file(root,relative,source_path):
 """Atomically store an existing plain file without changing its logical bytes."""
 target=path_for(root,relative);source_path=Path(source_path)
 if target.resolve()==source_path.resolve():return target
 target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.tmp')
 try:
  with source_path.open('rb') as source,temporary.open('wb') as raw:
   if target.suffix=='.gz':
    with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as output:shutil.copyfileobj(source,output,length=1024*1024)
   else:shutil.copyfileobj(source,raw,length=1024*1024)
  os.replace(temporary,target)
 except BaseException:
  temporary.unlink(missing_ok=True);raise
 return target
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
