#!/usr/bin/env python3
"""Task-owned background update; only verified source groups, no external publishing."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def call(name,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/name),*args],cwd=ROOT,check=True)
def run_extension_groups():
 # Each reviewed cohort has its own input signature; no internet discovery or
 # whole-history re-extraction is performed by a normal scheduled check.
 groups=[
  ('ncl_gap','extract_ncl_gap_tables.py',[],['raw/ncl-historical/yearbook-98-public-library.pdf','raw/ncl-historical/yearbook-99-public-library.pdf','raw/ncl-historical/yearbook-100-public-library.pdf'],['derived/ncl_gap_tables_long.csv','derived/ncl_gap_tables_long.jsonl','raw/ncl-historical/gap-tables-metadata.json']),
  ('ncl_earlier','extract_ncl_earlier_years.py',[],['raw/ncl-earlier/yearbook-96-public-library.pdf','raw/ncl-earlier/yearbook-97-public-library.pdf','raw/ncl-earlier/yearbook-96-download.json','raw/ncl-earlier/yearbook-97-download.json','raw/ncl-earlier/table-specifications.json'],['derived/ncl_earlier_years_long.csv','derived/ncl_earlier_years_long.jsonl','raw/ncl-earlier/metadata.json']),
  ('ncl_additional','extract_ncl_additional_years.py',['--offline'],[f'raw/ncl-additional/yearbook-{edition}-{kind}.{suffix}' for edition,kind in [(101,'public-library'),(103,'public-library'),(101,'statistics'),(102,'statistics'),(103,'statistics')] for suffix in ['pdf','metadata.json']],['derived/ncl_additional_years_long.csv','derived/ncl_additional_years_long.jsonl','raw/ncl-additional/extracted-operational-cells.json','raw/ncl-additional/documents.json','raw/ncl-additional/extraction-validation.json'])]
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
def main():
 p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');p.add_argument('--refresh-local',action='store_true');p.add_argument('--refresh-all-core',action='store_true');a=p.parse_args()
 canonical=ROOT/'data/combined/observations.jsonl';before=digest(canonical)
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
 call('adapt_components.py');call('build_release.py');call('build_coverage.py');call('build_documentation.py');call('verify_release.py')
 after=digest(canonical);result={'completed_at':now.isoformat(),'before_sha256':before,'after_sha256':after,'data_changed':before!=after,'external_publication':False,'stale_local_sources':stale}
 (ROOT/'data/last_update.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
