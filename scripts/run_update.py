#!/usr/bin/env python3
"""Task-owned background update; only verified source groups, no external publishing."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def call(name,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/name),*args],cwd=ROOT,check=True)
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
 call('adapt_components.py');call('build_release.py');call('build_coverage.py');call('verify_release.py')
 after=digest(canonical);result={'completed_at':now.isoformat(),'before_sha256':before,'after_sha256':after,'data_changed':before!=after,'external_publication':False,'stale_local_sources':stale}
 (ROOT/'data/last_update.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
