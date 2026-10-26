#!/usr/bin/env python3
"""Create a self-contained source/availability reader without remote scripts."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 summary=json.loads((ROOT/'docs/phase1-summary.json').read_text());scope=json.loads((ROOT/'scripts/phase1_scope.json').read_text());inventory=json.loads((ROOT/'docs/phase1-source-inventory.json').read_text())
 grid=[json.loads(x) for x in (ROOT/'derived/phase1_discovery_matrix.jsonl').read_text().splitlines()]
 links={}
 for line in (ROOT/'derived/phase1_raw_source_profiles.jsonl').read_text().splitlines():
  r=json.loads(line);links.setdefault(r['source_id'],set()).update(r['source_urls'])
 for r in summary.get('supplemental_source_batches',[]):links.setdefault(r['source_id'],set()).add(r['download_url'])
 payload={'summary':summary,'scope':scope,'authorities':inventory['authority_checks'],'candidates':inventory['source_candidates'],'cells':[{k:r[k] for k in ('data_year','navigation_region_current_name','topic_id','topic_label','availability_status','matched_source_observations','confirmed_label_value_records','unconfirmed_geography_records','temporal_resolution_counts','null_status_counts','source_ids','supplementary_source_cells','supplementary_nonmissing_cells','supplementary_source_ids','supplementary_period_basis')} for r in grid]}
 payload['source_links']={k:sorted(v) for k,v in sorted(links.items())}
 text=(ROOT/'site/phase1-template.html').read_text().replace('__PHASE1_DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
 (ROOT/'site/phase1.html').write_text(text);print('phase1 reader bytes',len(text.encode()))
if __name__=='__main__':main()
