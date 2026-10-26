#!/usr/bin/env python3
"""Hash-gated phase2 refresh; no source acquisition or external publication."""
from __future__ import annotations
import argparse,gzip,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
import phase2_engine

ROOT=Path(__file__).resolve().parents[1]
STAGES=('build_phase2.py','build_phase2_reader.py','build_phase2_documentation.py')
CODE=(*STAGES,'phase2_engine.py','validate_phase2.py','phase2_update.py')
SHARED=('README.md','AI_USAGE.md','COVERAGE.md','llms.txt','datapackage.json','docs/publishing-channels.json')

def stable(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def enabled(root):return (root/'scripts/build_phase2.py').is_file()
def write(path,value):
 b=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
 if path.exists() and path.read_bytes()==b:return
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(b);tmp.replace(path)
def source_path(root,name):
 p=root/name
 if p.is_file():return p
 p=p.with_suffix(p.suffix+'.gz')
 if not p.is_file():raise FileNotFoundError('Required phase2 source missing; previous output retained: '+name)
 return p
def statistical_fingerprint(path):
 h=hashlib.sha256();h.update(b'[');first=True
 with (gzip.open(path,'rt',encoding='utf-8-sig') if path.suffix=='.gz' else path.open(encoding='utf-8-sig')) as f:
  for line in f:
   r=json.loads(line)
   if not first:h.update(b',')
   # Publication/projection duplicates carry no independent statistical fact.
   excluded=phase2_engine.IGNORED_PUBLICATION_FIELDS|{'original_fields'}
   h.update(stable({k:v for k,v in r.items() if k not in excluded}).encode());first=False
 h.update(b']');return h.hexdigest()
def input_signature(root):
 layers={layer:statistical_fingerprint(source_path(root,name)) for layer,name in phase2_engine.LAYERS.items()}
 files=[*phase2_engine.EVIDENCE_FILES,'raw/phase2-definitions/current-reference-sources.json','docs/phase2-contract.json','VERSION','site/phase2-template.html',*('scripts/'+n for n in CODE)]
 if (root/'scripts/series_charts.py').is_file():files.append('scripts/series_charts.py')
 hashes={}
 for name in files:
  p=root/name
  if not p.is_file():raise FileNotFoundError('Required phase2 definition/code input missing: '+name)
  hashes[name]=digest(p)
 return {'statistical_source_fingerprints':layers,'definition_and_code_hashes':hashes}
def output_paths(root):
 files=set()
 for pattern in ['derived/phase2/**/*','docs/*phase2*','docs/PHASE2.md','site/phase2.html',*SHARED]:
  files.update(p for p in root.glob(pattern) if p.is_file() and '.private' not in p.name and str(p.relative_to(root))!='docs/phase2-contract.json')
 return sorted(files)
def output_hashes(root):return {str(p.relative_to(root)):digest(p) for p in output_paths(root)}
def reviewed_bootstrap(root,inputs):
 path=root/'docs/phase2-summary.json'
 if not path.is_file() or not all((root/name).is_file() for name in ('site/phase2.html','docs/PHASE2.md','docs/phase2-statuses.json')):return False
 summary=json.loads(path.read_text());required=[*phase2_engine.EVIDENCE_FILES,'raw/phase2-definitions/current-reference-sources.json','docs/phase2-contract.json','scripts/phase2_engine.py','scripts/build_phase2.py']
 return (summary.get('dataset_version')==(root/'VERSION').read_text().strip()
         and summary.get('layer_raw_fingerprints')==inputs['statistical_source_fingerprints']
         and all(summary.get('inputs',{}).get(name)==inputs['definition_and_code_hashes'].get(name) for name in required))
def content_digest(root=ROOT):
 root=Path(root)
 if not (root/'derived/phase2/annotations.jsonl.gz').is_file():return None
 # Physical SQLite layout, gzip encoding, summaries, runtime receipts and
 # code-only provenance checksums do not create a new statistical release.
 values={}
 for name in ['annotations.jsonl.gz','groups.jsonl','evidence_cards.jsonl','breakpoints.jsonl']:
  p=root/'derived/phase2'/name
  if not p.is_file():raise FileNotFoundError('Incomplete phase2 data layer: '+name)
  h=hashlib.sha256()
  with (gzip.open(p,'rb') if p.suffix=='.gz' else p.open('rb')) as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  values[name.removesuffix('.gz')]=h.hexdigest()
 return hashlib.sha256(stable(values).encode()).hexdigest()
def snapshot(root,directory):
 paths=output_paths(root);result={}
 for p in paths:
  relative=str(p.relative_to(root));target=directory/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);result[relative]=p.stat().st_mtime_ns
 return result
def rollback(root,directory,before):
 for p in output_paths(root):
  if str(p.relative_to(root)) not in before:p.unlink()
 for relative in before:
  target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(directory/relative,target)
def run(root=ROOT,runner=None):
 root=Path(root)
 if not enabled(root):return {'enabled':False,'rebuilt':False}
 inputs=input_signature(root);statepath=root/'data/phase2_update_state.json';previous=json.loads(statepath.read_text()) if statepath.exists() else {};current=output_hashes(root)
 unchanged=previous.get('inputs')==inputs and previous.get('outputs')==current and bool(current)
 def execute(name):
  if runner:runner(name,'--root',str(root))
  else:subprocess.run([sys.executable,str(root/'scripts'/name),'--root',str(root)],cwd=root,check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 if not previous and current and reviewed_bootstrap(root,inputs):
  # Existing reviewed build artifacts may initialize the cache only after all
  # source fingerprints, code-bound summary and output/reader checks pass.
  execute('validate_phase2.py')
  if input_signature(root)!=inputs:raise ValueError('Phase2 inputs changed during bootstrap; previous outputs retained')
  write(statepath,{'schema_version':'1.0.0','inputs':inputs,'outputs':current})
  return {'enabled':True,'rebuilt':False,'bootstrap_verified_outputs':True,'source_audits_rerun':False,'content_sha256':content_digest(root)}
 if unchanged:
  execute('validate_phase2.py');return {'enabled':True,'rebuilt':False,'source_audits_rerun':False,'content_sha256':content_digest(root)}
 with tempfile.TemporaryDirectory(prefix='phase2-previous-') as temp:
  backup=Path(temp);before=snapshot(root,backup)
  try:
   for name in STAGES:execute(name)
   execute('validate_phase2.py')
   if input_signature(root)!=inputs:raise ValueError('Phase2 inputs changed during build; previous outputs retained')
   after=output_hashes(root)
   if not (root/'docs/phase2-summary.json').is_file() or not (root/'derived/phase2/definitions.sqlite').is_file():raise FileNotFoundError('Phase2 builders omitted required outputs')
   write(statepath,{'schema_version':'1.0.0','inputs':inputs,'outputs':after})
  except BaseException:rollback(root,backup,before);raise
 return {'enabled':True,'rebuilt':True,'source_audits_rerun':False,'changed_output_paths':[k for k,v in after.items() if current.get(k)!=v],'content_sha256':content_digest(root)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(run(a.root),ensure_ascii=False))
if __name__=='__main__':main()
