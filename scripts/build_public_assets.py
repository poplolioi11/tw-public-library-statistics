#!/usr/bin/env python3
"""Build assets only from a verified public tag; optionally finish its existing draft.

No source downloads or data extraction. Published releases and mismatched assets
are never replaced. The draft checksum can be refreshed before first publication.
"""
import argparse,hashlib,json,re,shutil,subprocess,zipfile
from pathlib import Path
REPOSITORY='poplolioi11/tw-public-library-statistics'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api',path]))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--commit',required=True);p.add_argument('--repository',default=REPOSITORY);p.add_argument('--publish-draft',action='store_true');a=p.parse_args();r=a.root.resolve();out=a.output.resolve()
 if a.repository!=REPOSITORY:raise ValueError('Repository outside the authorized publication scope')
 if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',a.tag) or not re.fullmatch('[a-f0-9]{40}',a.commit):raise ValueError('Invalid fixed tag/commit')
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip()!=a.commit:raise ValueError('Checkout differs from the requested fixed commit')
 if subprocess.check_output(['git','status','--porcelain'],cwd=r,text=True).strip():raise ValueError('Fixed dataset checkout must be clean')
 m=json.loads((r/'PUBLICATION_MANIFEST.json').read_text());version=(r/'VERSION').read_text().strip()
 if m['version']!=version or a.tag!='v'+version or m['publication_profile']!='statistical_fields_only':raise ValueError('Not the requested public profile/version')
 ref=api('repos/'+a.repository+'/git/ref/tags/'+a.tag)['object']
 while ref['type']=='tag':ref=api('repos/'+a.repository+'/git/tags/'+ref['sha'])['object']
 if ref['type']!='commit' or ref['sha']!=a.commit:raise ValueError('Existing immutable tag differs from requested commit')
 out.mkdir(parents=True,exist_ok=True);archive=out/('tw-public-library-statistics-'+a.tag+'.zip')
 names=set();entries=m['files']+[{'path':'PUBLICATION_MANIFEST.json','sha256':sha(r/'PUBLICATION_MANIFEST.json')}]
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for e in entries:
   rel=Path(e['path'])
   if rel.is_absolute() or '..' in rel.parts or any('private' in x.lower() for x in rel.parts) or e['path'] in names:raise ValueError('Unsafe or duplicate public manifest member')
   names.add(e['path']);body=(r/rel).read_bytes()
   if hashlib.sha256(body).hexdigest()!=e['sha256']:raise ValueError('Public member SHA mismatch: '+e['path'])
   info=zipfile.ZipInfo(e['path'],date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o600<<16;z.writestr(info,body,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
 with zipfile.ZipFile(archive) as z:
  if z.testzip() is not None or set(z.namelist())!=names:raise ValueError('Incomplete archive')
  for e in entries:
   if hashlib.sha256(z.read(e['path'])).hexdigest()!=e['sha256']:raise ValueError('Archive member SHA mismatch')
 files={'PUBLICATION_MANIFEST.json':'PUBLICATION_MANIFEST.json','observations.csv':'data/combined/observations.csv','observations.jsonl.gz':'data/combined/observations.jsonl.gz','library_statistics.sqlite':'data/combined/library_statistics.sqlite','phase1-statistical-cells.csv':'derived/phase1_local_sources_long.csv','phase1-statistical-cells.jsonl':'derived/phase1_local_sources_long.jsonl','phase1_supplements.sqlite':'derived/phase1_supplements.sqlite','phase2-annotations.csv.gz':'derived/phase2/annotations.csv.gz','phase2-annotations.jsonl.gz':'derived/phase2/annotations.jsonl.gz','phase2-definitions.sqlite':'derived/phase2/definitions.sqlite'}
 for name,src in files.items():shutil.copyfile(r/src,out/name)
 expected={f.name:{'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted(out.iterdir()) if f.is_file() and f.name!='SHA256SUMS.txt'}
 checksums=out/'SHA256SUMS.txt';checksums.write_text(''.join(x['sha256']+'  '+name+'\n' for name,x in sorted(expected.items())));expected[checksums.name]={'sha256':sha(checksums),'bytes':checksums.stat().st_size}
 if a.publish_draft:
  releases=api('repos/'+a.repository+'/releases?per_page=100')
  release=next((x for x in releases if x['tag_name']==a.tag),None)
  if release is None:raise ValueError('Existing release not found; do not create one automatically')
  if not release['draft']:raise ValueError('Only an existing unpublished draft may be completed')
  remote={f['name']:f for f in release['assets']}
  if set(remote)-set(expected):raise ValueError('Unexpected draft asset; review before modifying it')
  for name,e in expected.items():
   prior=remote.get(name)
   if prior and prior['state']=='uploaded' and prior['size']==e['bytes'] and prior.get('digest')=='sha256:'+e['sha256']:continue
   if prior:
    if name!='SHA256SUMS.txt' or not release['draft']:raise ValueError('Refuse to replace a mismatched existing asset: '+name)
    if not api('repos/'+a.repository+'/releases/'+str(release['id']))['draft']:raise ValueError('Draft was published while packaging; refuse checksum replacement')
    subprocess.run(['gh','api','--method','DELETE','repos/'+a.repository+'/releases/assets/'+str(prior['id'])],check=True)
   subprocess.run(['gh','release','upload',a.tag,str(out/name),'--repo',a.repository],check=True)
 print(json.dumps({'tag':a.tag,'commit':a.commit,'public_manifest_members':len(names),'assets':expected,'execution':'Packaging only; data computed and reviewed before publication. No omitted originals retrieved.'},indent=2))
if __name__=='__main__':main()
