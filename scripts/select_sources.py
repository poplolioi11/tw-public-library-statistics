#!/usr/bin/env python3
"""Read-only, reproducible source selection for registered questions."""
import argparse,csv,io,json,sys
from pathlib import Path
import phase3_engine as engine
import phase2_engine
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--list',action='store_true');p.add_argument('--lookup');p.add_argument('--profile');p.add_argument('--purpose',choices=['source-facts','trend']);p.add_argument('--start-year',type=int);p.add_argument('--end-year',type=int);p.add_argument('--month',type=int);p.add_argument('--entity');p.add_argument('--facility');p.add_argument('--metric');p.add_argument('--source-id');p.add_argument('--facet',action='append',default=[]);p.add_argument('--operation');p.add_argument('--format',choices=['json','jsonl','csv'],default='json');p.add_argument('--output',type=Path);a=p.parse_args()
 if a.operation:
  result=phase2_engine.guard_operation(a.operation)
  if result is None:result={'status':'unresolved','reasons':['Use a registered question and its explicit series_edges; no unrestricted source joins.']}
  print(json.dumps(result,ensure_ascii=False,indent=2));return
 policy=engine.load_policy(a.root)
 if a.lookup:
  records=[r for r in engine.load_annotations(a.root) if r['record_key']==a.lookup]
  if len(records)!=1:p.error('Exact layer:observation_id not found')
  route=engine.route_records(records,policy)[0]
  print(json.dumps({'record_route':route,'original_annotation':records[0],'interpretation':'Read-only literal original-source view; lookup does not grant a new default quantity, source equivalence or trend certification.'},ensure_ascii=False,indent=2));return
 if a.list:
  print(json.dumps({'policy_version':policy['policy_version'],'profiles':policy['profiles']},ensure_ascii=False,indent=2));return
 if not a.profile:p.error('Choose a registered --profile; use --list first')
 facets={}
 for text in a.facet:
  if '=' not in text:p.error('--facet needs original_field=value')
  k,v=text.split('=',1)
  if k in facets:p.error('Duplicate facet filter')
  try:facets[k]=json.loads(v)
  except json.JSONDecodeError:facets[k]=v
 try:answer=engine.select(policy,engine.load_annotations(a.root),a.profile,purpose=a.purpose,start_year=a.start_year,end_year=a.end_year,month=a.month,entity=a.entity,facility=a.facility,metric=a.metric,source_id=a.source_id,facets=facets)
 except ValueError as exc:p.error(str(exc))
 if a.format=='json':body=json.dumps(answer,ensure_ascii=False,indent=2)+'\n'
 elif a.format=='jsonl':body=''.join(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n' for d in answer['decisions'])
 else:
  rows=answer['decisions'];keys=list(dict.fromkeys(k for r in rows for k in r));buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=keys);writer.writeheader()
  for r in rows:writer.writerow({k:engine.stable(v) if isinstance(v,(dict,list,bool)) else v for k,v in r.items()})
  body=buffer.getvalue()
 if a.output:
  if a.output.exists():raise FileExistsError('Refuse to overwrite an existing selection export')
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(body,encoding='utf-8-sig' if a.format=='csv' else 'utf-8')
 else:sys.stdout.write(body)
if __name__=='__main__':main()
