#!/usr/bin/env python3
"""Task-owned background update; only verified source groups, no external publishing."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
import record_io
from phase1_source_registry import content_digest as phase1_content_digest,load as load_phase1
from phase1_source_manager import run_batches as run_phase1_batches,monitor_sources as monitor_phase1_sources
ROOT=Path(__file__).resolve().parents[1]
from cohort_registry import load as load_cohorts
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def call(name,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/name),*args],cwd=ROOT,check=True)
def run_extension_groups():
 # Each reviewed cohort has its own input signature; no internet discovery or
 # whole-history re-extraction is performed by a normal scheduled check.
 groups=[
  ('ncl_gap','extract_ncl_gap_tables.py',[],['raw/ncl-historical/yearbook-98-public-library.pdf','raw/ncl-historical/yearbook-99-public-library.pdf','raw/ncl-historical/yearbook-100-public-library.pdf'],['derived/ncl_gap_tables_long.csv','derived/ncl_gap_tables_long.jsonl','raw/ncl-historical/gap-tables-metadata.json']),
  ('ncl_earlier','extract_ncl_earlier_years.py',[],['raw/ncl-earlier/yearbook-96-public-library.pdf','raw/ncl-earlier/yearbook-97-public-library.pdf','raw/ncl-earlier/yearbook-96-download.json','raw/ncl-earlier/yearbook-97-download.json','raw/ncl-earlier/table-specifications.json'],['derived/ncl_earlier_years_long.csv','derived/ncl_earlier_years_long.jsonl','raw/ncl-earlier/metadata.json']),
  ('ncl_additional','extract_ncl_additional_years.py',['--offline'],[f'raw/ncl-additional/yearbook-{edition}-{kind}.{suffix}' for edition,kind in [(101,'public-library'),(103,'public-library'),(101,'statistics'),(102,'statistics'),(103,'statistics')] for suffix in ['pdf','metadata.json']],['derived/ncl_additional_years_long.csv','derived/ncl_additional_years_long.jsonl','raw/ncl-additional/extracted-operational-cells.json','raw/ncl-additional/documents.json','raw/ncl-additional/extraction-validation.json'])]
 inventory=load_cohorts(ROOT)
 if inventory is not None:groups=[(g['id'],g['script'],g.get('args',[]),g['inputs']+g.get('dependencies',[]),g['outputs']) for g in inventory]
 for key,script,args,patterns,outputs in groups:
  if not (ROOT/'scripts'/script).exists():raise FileNotFoundError('Reviewed extractor is missing: '+script)
  for pattern in patterns:
   if not list(ROOT.glob(pattern)):raise FileNotFoundError('Restore required reviewed input: '+pattern)
  inputs=sorted({p for pattern in patterns for p in ROOT.glob(pattern)})
  if not inputs:raise FileNotFoundError('Restore reviewed originals before rebuilding '+key)
  def signature():return {str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'scripts'/script,*inputs]}
  statefile=ROOT/'data'/(key+'_extraction_state.json')
  old=json.loads(statefile.read_text()) if statefile.exists() else {}
  missing=[p for p in old.get('inputs',{}) if not (ROOT/p).is_file()]
  if missing:raise FileNotFoundError('Previously reviewed input disappeared; restore before rebuilding: '+', '.join(missing))
  unchanged=signature()==old.get('inputs') and all(digest(ROOT/p)==old.get('outputs',{}).get(p) for p in outputs)
  if unchanged:continue
  backup={p:(ROOT/p).read_bytes() if (ROOT/p).exists() else None for p in outputs}
  try:
   call(script,*args)
   if any(not (ROOT/p).is_file() for p in outputs):raise FileNotFoundError('Extractor did not produce every reviewed output: '+key)
  except Exception:
   for p,body in backup.items():
    if body is None:(ROOT/p).unlink(missing_ok=True)
    else:(ROOT/p).write_bytes(body)
   raise
  statefile.write_text(json.dumps({'inputs':signature(),'outputs':{p:digest(ROOT/p) for p in outputs}},indent=2)+'\n')
def content_signature(root=None):
 root=Path(root or ROOT)
 content={'canonical':record_io.logical_sha(root),'phase1':phase1_content_digest(root)}
 return hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def file_signature(patterns):
 paths=sorted({p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file() and '.private' not in p.as_posix()})
 return {str(p.relative_to(ROOT)):digest(p) for p in paths}
def canonical_build_inputs():
 groups=load_cohorts(ROOT) or []
 names=['derived/ncl_historical_long.csv','derived/dgbas_historical_long.csv','derived/local_historical_long.csv','derived/dgbas_county_historical_long.csv','derived/local_historical_quality.json',*[g['derived_csv'] for g in groups]]
 return file_signature([*names,'data/observations.jsonl','data/source_manifest.json','raw/official-local/catalog-*/resource-*.metadata.json','raw/ncl-extension-documents.json','raw/ncl-supporting-documents.json','raw/ncl-historical/gap-tables-metadata.json','research/definitions.json','research/definitions.csv','data/reviewed_historical_cohorts.json','VERSION','site/template.html','scripts/adapt_components.py','scripts/build_release.py','scripts/build_coverage.py','scripts/build_documentation.py','scripts/cohort_registry.py','scripts/record_io.py'])
def run_canonical_build():
 inputs=canonical_build_inputs();path=ROOT/'data/canonical_build_state.json';old=json.loads(path.read_text()) if path.exists() else {}
 outputs=['data/combined/*','data/component_records.jsonl','data/component_records.jsonl.gz','site/index.html']
 current=file_signature(outputs)
 if old.get('inputs')==inputs and old.get('outputs')==current and current:return False
 call('adapt_components.py');call('build_release.py');call('build_coverage.py');call('build_documentation.py')
 if not (ROOT/'data/combined/summary.json').is_file():raise FileNotFoundError('Canonical builder omitted summary')
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'inputs':inputs,'outputs':file_signature(outputs)},indent=2)+'\n')
 return True
def phase1_hook_inputs():
 return {'canonical_logical_sha256':record_io.logical_sha(ROOT),'phase1_content_sha256':phase1_content_digest(ROOT),
         'files':file_signature(['VERSION','data/reviewed_phase1_batches.json','data/reviewed_historical_cohorts.json','scripts/build_phase1_inventory.py','scripts/build_phase1_supplements.py','scripts/build_phase1_reader.py','scripts/build_phase1_documentation.py','site/phase1-template.html'])}
def run_phase1_hooks():
 if load_phase1(ROOT) is None:return {'enabled':False,'rebuilt':False}
 stages=[('build_phase1_inventory.py',('--require-survey-complete',)),('build_phase1_supplements.py',()),('build_phase1_reader.py',()),('build_phase1_documentation.py',())]
 for name,_ in stages:
  if not (ROOT/'scripts'/name).is_file():raise FileNotFoundError('Registered phase1 stage missing: '+name)
 path=ROOT/'data/phase1_hook_state.json';old=json.loads(path.read_text()) if path.exists() else {};inputs=phase1_hook_inputs()
 patterns=['derived/phase1_*.csv','derived/phase1_*.jsonl','derived/phase1_*.sqlite','derived/phase1_by_sheet/**/*.jsonl','docs/*phase1*','docs/PHASE1.md','docs/source-backlog.*','site/phase1.html','README.md','AI_USAGE.md','COVERAGE.md','llms.txt','datapackage.json']
 current=file_signature(patterns);rebuild=not (old.get('inputs')==inputs and old.get('outputs')==current and current)
 if rebuild:
  for name,args in stages:call(name,*args)
  if not (ROOT/'docs/phase1-summary.json').is_file():raise FileNotFoundError('Phase1 builder omitted summary')
 # Source-format verification remains local. Public publication/CI runs the
 # supplement validator's stricter default without --allow-private-fields.
 call('validate_phase1_inventory.py');call('validate_phase1_supplements.py','--allow-private-fields')
 if rebuild:
  path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'inputs':inputs,'outputs':file_signature(patterns)},indent=2)+'\n')
 return {'enabled':True,'rebuilt':rebuild,'source_entry_recrawl':False}
def main():
 p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');p.add_argument('--refresh-local',action='store_true');p.add_argument('--refresh-all-core',action='store_true');a=p.parse_args()
 canonical=record_io.path_for(ROOT,'data/combined/observations.jsonl');before=record_io.logical_sha(ROOT)
 prior_path=ROOT/'data/last_update.json';prior=json.loads(prior_path.read_text()) if prior_path.exists() else {}
 # Phase1 originals pass the immutable-source gate before any update work.
 phase1_batches=run_phase1_batches(ROOT)
 phase1_monitor=monitor_phase1_sources(ROOT,offline=a.offline)
 current_before_signature=content_signature()
 if a.offline:call('library_pipeline.py','build')
 else:call('library_pipeline.py','update',*(['--refresh-all'] if a.refresh_all_core else []))
 statefile=ROOT/'data/local_update_state.json';state=json.loads(statefile.read_text()) if statefile.exists() else {};now=datetime.datetime.now(datetime.timezone.utc)
 last=datetime.datetime.fromisoformat(state['last_refresh_at']) if state.get('last_refresh_at') else now
 # The most recent local monthly source is checked at most every14d. Historical packets are cached and hash-checked.
 refresh=not a.offline and (a.refresh_local or not state or (now-last).total_seconds()>=14*86400)
 call('fetch_local_history.py',*(['--refresh'] if refresh else []))
 local_manifest=json.loads((ROOT/'derived/local_historical_metadata.json').read_text());stale=[str(p.relative_to(ROOT)) for p in (ROOT/'raw/official-local').glob('catalog-*/resource-*.metadata.json') if json.loads(p.read_text()).get('last_check_status')=='failed']
 if refresh and not stale:statefile.write_text(json.dumps({'last_refresh_at':now.isoformat(),'policy':'14d; exact public catalogue links only; failures retain prior verified body'},ensure_ascii=False,indent=2)+'\n')
 county_statefile=ROOT/'data/county_update_state.json';county_state=json.loads(county_statefile.read_text()) if county_statefile.exists() else {}
 county_last=datetime.datetime.fromisoformat(county_state['last_refresh_at']) if county_state.get('last_refresh_at') else now
 county_refresh=not a.offline and county_state and (now-county_last).total_seconds()>=90*86400
 call('fetch_segis_history.py',*(['--refresh'] if county_refresh else ['--offline']))
 if county_refresh or not county_state:county_statefile.write_text(json.dumps({'last_refresh_at':now.isoformat(),'policy':'90d; semantic digest excludes layout/ViewState; failure keeps original CSV'},ensure_ascii=False,indent=2)+'\n')
 # The historical CSV extraction is regenerated only when a source PDF or extractor changed.
 source_state=ROOT/'data/historical_extraction_state.json';old=json.loads(source_state.read_text()) if source_state.exists() else {};signature={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'raw/ncl-historical').glob('*.pdf') if 'excluded' not in p.name and 'all-types' not in p.name}
 signature['extractor']=digest(ROOT/'scripts/fetch_ncl_historical.py');signature['dgbas_extractor']=digest(ROOT/'scripts/extract_dgbas_historical.py')
 if signature!=old:
  if not (ROOT/'raw/ncl-historical').exists():raise SystemExit('Historical raw files missing; download with fetch_ncl_historical.py before rebuilding these components.')
  call('fetch_ncl_historical.py','--offline');call('extract_dgbas_historical.py');source_state.write_text(json.dumps(signature,indent=2)+'\n')
 run_extension_groups();call('register_historical_sources.py')
 canonical_rebuilt=run_canonical_build()
 phase1_hooks=run_phase1_hooks();call('verify_release.py')
 after=record_io.logical_sha(ROOT);after_signature=content_signature()
 # Legacy updates had no phase1 layer. Comparing against that explicit null
 # detects a newly added sidecar even when all canonical observations are equal.
 previous_signature=prior.get('all_layers_sha256')
 if previous_signature is None:
  previous_signature=hashlib.sha256(json.dumps({'canonical':prior.get('after_sha256',before),'phase1':None},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 result={'completed_at':now.isoformat(),'before_sha256':before,'after_sha256':after,'canonical_data_changed':before!=after,
         'before_run_all_layers_sha256':current_before_signature,'previous_update_all_layers_sha256':previous_signature,
         'all_layers_sha256':after_signature,'phase1_content_sha256':phase1_content_digest(ROOT),
         'data_changed':previous_signature!=after_signature,'canonical_rebuilt':canonical_rebuilt,'phase1_batches':phase1_batches,
         'phase1_monitor':phase1_monitor,'phase1_hooks':phase1_hooks,'external_publication':False,'stale_local_sources':stale}
 (ROOT/'data/last_update.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
