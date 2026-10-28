#!/usr/bin/env python3
"""Hash-gated viewer rebuild with rollback; no source acquisition or publishing."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from build_lightweight_site import input_hashes,stable,write
ROOT=Path(__file__).resolve().parents[1]
DOCS=('docs/light-site-summary.json','docs/publishing-channels.json','README.md','COVERAGE.md','AI_USAGE.md','llms.txt')
def outputs(root):
 paths=[p for p in (root/'site/light').rglob('*') if p.is_file()]+[root/n for n in DOCS if (root/n).is_file()]
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def run(root=ROOT,runner=None):
 root=Path(root)
 if not (root/'scripts/build_lightweight_site.py').is_file():return {'enabled':False,'rebuilt':False}
 signature=dict(input_hashes(root))
 for n in ('light_site_update.py','validate_lightweight_site.py','build_lightweight_documentation.py'):signature['scripts/'+n]=hashlib.sha256((root/'scripts'/n).read_bytes()).hexdigest()
 state=root/'data/light_site_update_state.json';old=json.loads(state.read_text()) if state.is_file() else {};current=outputs(root)
 if old.get('inputs')==signature and old.get('outputs')==current:return {'enabled':True,'rebuilt':False,'source_acquisition':False}
 with tempfile.TemporaryDirectory(prefix='library-viewer-backup-') as folder:
  backup=Path(folder)
  if (root/'site/light').exists():shutil.copytree(root/'site/light',backup/'site/light')
  existed={n:(root/n).exists() for n in DOCS}
  for n in DOCS:
   if existed[n]:(backup/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/n,backup/n)
  try:
   for name in ('build_lightweight_site.py','validate_lightweight_site.py','build_lightweight_documentation.py'):
    if runner:runner(name,'--root',str(root))
    else:subprocess.run([sys.executable,str(root/'scripts'/name),'--root',str(root)],cwd=root,check=True)
   if input_hashes(root)!={k:v for k,v in signature.items() if k not in {'scripts/light_site_update.py','scripts/validate_lightweight_site.py','scripts/build_lightweight_documentation.py'}}:raise ValueError('Viewer inputs changed during rebuild; restoring previous site')
   write(state,stable({'schema_version':1,'inputs':signature,'outputs':outputs(root)}))
  except BaseException:
   shutil.rmtree(root/'site/light',ignore_errors=True)
   if (backup/'site/light').exists():shutil.copytree(backup/'site/light',root/'site/light')
   for n in DOCS:
    if existed[n]:shutil.copy2(backup/n,root/n)
    else:(root/n).unlink(missing_ok=True)
   raise
 return {'enabled':True,'rebuilt':True,'source_acquisition':False,'statistical_values_modified':False}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(run(a.root),ensure_ascii=False))
if __name__=='__main__':main()
