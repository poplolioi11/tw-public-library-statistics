#!/usr/bin/env python3
"""Phase3 hash-gated selection-layer updates; no acquisition or publication."""
from __future__ import annotations
import argparse,ast,gzip,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
import phase2_update
import phase2_engine

ROOT=Path(__file__).resolve().parents[1]
STAGES=('build_phase3.py','build_phase3_reader.py','build_phase3_documentation.py')
CODE=(*STAGES,'phase3_engine.py','select_sources.py','validate_phase3.py','phase3_update.py','series_charts.py','build_phase3_charts.py')
SHARED=('README.md','AI_USAGE.md','COVERAGE.md','llms.txt','datapackage.json','docs/publishing-channels.json','docs/PHASE1.md','docs/PHASE2.md','site/index.html','site/phase1.html','site/phase2.html')
INPUT_DOCS={'docs/phase3-contract.json','docs/phase3-profiles.json'}
INPUT_OUTPUT_EXCLUSIONS=INPUT_DOCS|{'docs/phase2-summary.json','docs/phase2-contract.json'}
PRIOR_STATES=('data/phase1_hook_state.json','data/phase2_update_state.json','data/canonical_build_state.json')

def stable(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(path):return phase2_update.digest(path)
def enabled(root):return (root/'scripts/build_phase3.py').is_file()
def write(path,value):
 b=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
 if path.exists() and path.read_bytes()==b:return
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(b);tmp.replace(path)
def local_code_dependencies(root):
 # Reader/chart helpers are source code too; hash local imports without
 # importing/executing them. Standard-library/installed modules are ignored.
 pending=['scripts/'+name for name in CODE];seen=set()
 while pending:
  name=pending.pop()
  if name in seen:continue
  path=root/name
  if not path.is_file():raise FileNotFoundError('Required phase3 code missing: '+name)
  seen.add(name)
  for node in ast.walk(ast.parse(path.read_text(),filename=name)):
   modules=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) and node.module else []
   for module in modules:
    relative='scripts/'+module.replace('.','/')+'.py'
    if (root/relative).is_file():pending.append(relative)
 return sorted(seen)
def input_signature(root):
 fingerprints={layer:phase2_update.statistical_fingerprint(phase2_update.source_path(root,name)) for layer,name in phase2_engine.LAYERS.items()}
 names=[*sorted(INPUT_DOCS),'docs/phase2-summary.json','VERSION',*local_code_dependencies(root)]
 if (root/'site/phase3-template.html').is_file():names.append('site/phase3-template.html')
 hashes={}
 for name in names:
  path=root/name
  if not path.is_file():raise FileNotFoundError('Phase3 input missing; previous output retained: '+name)
  hashes[name]=digest(path)
 p2=phase2_update.content_digest(root)
 if p2 is None:raise FileNotFoundError('Required reviewed phase2 layer missing')
 return {'layer_raw_fingerprints':fingerprints,'phase2_content_sha256':p2,'policy_and_code_hashes':hashes}
def earlier_document_paths(root):
 names=set(SHARED)
 for name in PRIOR_STATES:
  p=root/name
  if p.is_file():
   for output in json.loads(p.read_text()).get('outputs',{}):
    if output.startswith(('docs/','site/')) and output not in INPUT_OUTPUT_EXCLUSIONS and 'contract' not in Path(output).name:names.add(output)
 return names

def output_paths(root):
 paths=set()
 for pattern in ['derived/phase3/**/*','docs/*phase3*','docs/PHASE3.md','site/phase3.html',*earlier_document_paths(root)]:
  paths.update(p for p in root.glob(pattern) if p.is_file() and '.private' not in p.name and str(p.relative_to(root)) not in INPUT_OUTPUT_EXCLUSIONS)
 return sorted(paths)
def output_hashes(root):return {str(p.relative_to(root)):digest(p) for p in output_paths(root)}
def content_digest(root=ROOT):
 root=Path(root)
 if not (root/'derived/phase3/record_routes.jsonl.gz').is_file():return None
 values={}
 for name in ('record_routes.jsonl.gz','candidate_decisions.jsonl.gz','queries.jsonl','series_edges.jsonl'):
  p=root/'derived/phase3'/name
  if not p.is_file():raise FileNotFoundError('Incomplete phase3 layer: '+name)
  h=hashlib.sha256()
  with (gzip.open(p,'rb') if p.suffix=='.gz' else p.open('rb')) as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  values[name.removesuffix('.gz')]=h.hexdigest()
 return hashlib.sha256(stable(values).encode()).hexdigest()
def refresh_prior_states(root):
 refreshed=[]
 for name in PRIOR_STATES:
  path=root/name
  if not path.is_file():continue
  old=json.loads(path.read_text());outputs={}
  for output in old.get('outputs',{}):
   p=root/output
   if not p.is_file():raise FileNotFoundError('Successful earlier-stage output missing: '+output)
   outputs[output]=digest(p)
  if outputs!=old.get('outputs',{}):write(path,{**old,'outputs':outputs});refreshed.append(name)
 return refreshed

def run(root=ROOT,runner=None):
 root=Path(root)
 if not enabled(root):return {'enabled':False,'rebuilt':False}
 inputs=input_signature(root);statepath=root/'data/phase3_update_state.json';old=json.loads(statepath.read_text()) if statepath.is_file() else {};current=output_hashes(root)
 def execute(name):
  if runner:runner(name,'--root',str(root))
  else:subprocess.run([sys.executable,str(root/'scripts'/name),'--root',str(root)],cwd=root,check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 if old.get('inputs')==inputs and old.get('outputs')==current and current:
  execute('validate_phase3.py');return {'enabled':True,'rebuilt':False,'source_audits_rerun':False,'content_sha256':content_digest(root)}
 with tempfile.TemporaryDirectory(prefix='phase3-previous-') as temp:
  backup=Path(temp);before={};states=[*PRIOR_STATES,'data/phase3_update_state.json']
  for p in [*output_paths(root),*(root/n for n in states)]:
   name=str(p.relative_to(root))
   if name in before:continue
   before[name]=p.is_file()
   if p.is_file():target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
  try:
   for name in STAGES:execute(name)
   execute('validate_phase3.py')
   if input_signature(root)!=inputs:raise ValueError('Phase3 inputs changed during update; previous output retained')
   if not (root/'docs/phase3-summary.json').is_file() or not (root/'derived/phase3/selection.sqlite').is_file():raise FileNotFoundError('Phase3 stage omitted required output')
   refreshed=refresh_prior_states(root);after=output_hashes(root);write(statepath,{'schema_version':'1.0.0','inputs':inputs,'outputs':after})
  except BaseException:
   for p in output_paths(root):
    if str(p.relative_to(root)) not in before:p.unlink()
   for name,existed in before.items():
    target=root/name
    if existed:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(backup/name,target)
    else:target.unlink(missing_ok=True)
   raise
 return {'enabled':True,'rebuilt':True,'source_audits_rerun':False,'source_statistics_changed':bool(old and old.get('inputs',{}).get('layer_raw_fingerprints')!=inputs['layer_raw_fingerprints']),'earlier_output_hash_states_refreshed':refreshed,'content_sha256':content_digest(root),'changed_output_paths':[p for p,v in after.items() if current.get(p)!=v]}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(run(a.root),ensure_ascii=False))
if __name__=='__main__':main()
