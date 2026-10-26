#!/usr/bin/env python3
"""Standalone definition/group reader; no external JavaScript, fonts or telemetry."""
import gzip,html,json
from decimal import Decimal
from pathlib import Path
from build_phase2 import replace_if_changed
ROOT=Path(__file__).resolve().parents[1]
def read_lines(path):return [json.loads(x) for x in path.read_text().splitlines()]
def chart(items):
 points=sorted(items,key=lambda r:(r['comparison_year'],r['comparison_month'] or 0));by_year={r['comparison_year']:r for r in points}
 if len(by_year)!=len(points) or len(points)<2:return None
 years=sorted(by_year);values=[Decimal(by_year[y]['comparison_value']) for y in years];low=min(Decimal(0),min(values));high=max(values);span=high-low or Decimal(1);year_span=max(years)-min(years) or 1
 dots=[];paths=[];previous=None
 for year,value in zip(years,values):
  x=60+660*(year-years[0])/year_span;y=200-float((value-low)/span)*160;paths.append(('M' if previous is None or year!=previous+1 else 'L')+f'{x:.2f},{y:.2f}');previous=year;label=html.escape(str(year)+'：'+str(value));dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4"><title>{label}</title></circle><text x="{x:.2f}" y="225" text-anchor="middle">{year}</text>')
 svg='<svg viewBox="0 0 780 245" role="img" aria-label="同原刊面板的來源年度數列"><path d="M60,35V200H735" fill="none" stroke="#adbdb6"/><path d="'+' '.join(paths)+'" fill="none" stroke="#226758" stroke-width="2"/><g fill="#226758">'+''.join(dots)+'</g></svg>'
 return {'source_points':[{'record_key':by_year[y]['record_key'],'year':y,'reported_value':by_year[y]['original_value'],'comparison_value':by_year[y]['comparison_value'],'source_url':by_year[y]['source_url'],'source_locator':by_year[y]['source_locator'],'zero_interpretation':by_year[y]['zero_interpretation']} for y in years],'svg':svg,'gap_policy':'Missing years break the line; no interpolation. Values are original or explicit decimal-unit-scale only.'}
def main():
 summary=json.loads((ROOT/'docs/phase2-summary.json').read_text());groups=read_lines(ROOT/'derived/phase2/groups.jsonl');cards=read_lines(ROOT/'derived/phase2/evidence_cards.jsonl');light=[]
 keys=('comparison_group_id','layer','raw_indicator','source_ids','source_urls','comparison_unit','records','years','status_counts','eligible_periods','has_multiple_eligible_periods')
 for g in groups:
  light.append({**{k:g[k] for k in keys},'scope_summary':{k:g['facets'].get(k) for k in ('entity','facility_or_reader_category','geographic_scope','population_scope','national_libraries_scope','period_kind','financial_mode','classification_dimensions','source_segment')},'sample_record_keys':g['record_keys'][:2]})
 selected=[g for g in groups if g['has_multiple_eligible_periods'] and len({y for y,m in g['eligible_periods'] if y is not None})>=2 and len(g['record_keys'])<=8 and g['facets']['period_kind']!='monthly_source_statistic' and g['facets']['measure_class'] in ('circulation_people','facilities','collection_stock')][:12];wanted={g['comparison_group_id'] for g in selected};points={g:[] for g in wanted}
 with gzip.open(ROOT/'derived/phase2/annotations.jsonl.gz','rt',encoding='utf-8') as f:
  for line in f:
   r=json.loads(line)
   if r['comparison_group_id'] in wanted and r['comparison_status']=='published_panel_limited' and r['comparison_value'] is not None:points[r['comparison_group_id']].append(r)
 examples={gid:graph for gid,items in points.items() if (graph:=chart(items)) is not None}
 evidence_index={c['evidence_id']:{'title':c.get('source_table_title'),'source_url':c['source_url'],'source_sha256':c['source_sha256'],'data_years_present':c.get('data_years_present',[]),'unresolved':c.get('unresolved',[]),'review_method':c.get('review_method')} for c in cards}
 payload={'summary':summary,'groups':light,'evidence_index':evidence_index,'examples':examples};body=(ROOT/'site/phase2-template.html').read_text().replace('__PHASE2_DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
 replace_if_changed(ROOT/'site/phase2.html',body.encode());print(json.dumps({'phase2_reader_bytes':len(body.encode()),'groups':len(light),'examples':len(examples),'version':summary['dataset_version']}))
if __name__=='__main__':main()
