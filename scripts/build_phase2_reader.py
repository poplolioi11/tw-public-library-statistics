#!/usr/bin/env python3
"""Standalone definition/group reader; no external JavaScript, fonts or telemetry."""
import gzip,html,json
from collections import defaultdict
from series_charts import chart
from pathlib import Path
from build_phase2 import replace_if_changed
ROOT=Path(__file__).resolve().parents[1]
def read_lines(path):return [json.loads(x) for x in path.read_text().splitlines()]
def main():
 summary=json.loads((ROOT/'docs/phase2-summary.json').read_text());groups=read_lines(ROOT/'derived/phase2/groups.jsonl');cards=read_lines(ROOT/'derived/phase2/evidence_cards.jsonl');light=[]
 keys=('comparison_group_id','layer','raw_indicator','source_ids','source_urls','comparison_unit','records','years','status_counts','eligible_periods','has_multiple_eligible_periods')
 for g in groups:
  light.append({**{k:g[k] for k in keys},'scope_summary':{k:g['facets'].get(k) for k in ('entity','facility_or_reader_category','geographic_scope','population_scope','national_libraries_scope','period_kind','financial_mode','classification_dimensions','source_segment')},'sample_record_keys':g['record_keys'][:2]})
 wanted={g['comparison_group_id'] for g in groups if g['has_multiple_eligible_periods']};points=defaultdict(list)
 with gzip.open(ROOT/'derived/phase2/annotations.jsonl.gz','rt',encoding='utf-8') as f:
  for line in f:
   r=json.loads(line)
   if r['comparison_group_id'] in wanted:points[r['comparison_group_id']].append(r)
 examples={gid:graph for gid,items in points.items() if (graph:=chart(items)) is not None and graph['plotted_points']>=2}
 evidence_index={c['evidence_id']:{'title':c.get('source_table_title'),'source_url':c['source_url'],'source_sha256':c['source_sha256'],'data_years_present':c.get('data_years_present',[]),'unresolved':c.get('unresolved',[]),'review_method':c.get('review_method')} for c in cards}
 payload={'summary':summary,'groups':light,'evidence_index':evidence_index,'examples':examples,'charts_are_complete_eligible_series_not_twelve_samples':True};body=(ROOT/'site/phase2-template.html').read_text().replace('__PHASE2_DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
 replace_if_changed(ROOT/'site/phase2.html',body.encode());replace_if_changed(ROOT/'docs/phase2-reader-summary.json',(json.dumps({'dataset_version':summary['dataset_version'],'groups':len(light),'charts':len(examples),'only_authorized_adjacent_lines':True,'display_is_not_method_invariance_certification':True},ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps({'phase2_reader_bytes':len(body.encode()),'groups':len(light),'examples':len(examples),'version':summary['dataset_version']}))
if __name__=='__main__':main()
