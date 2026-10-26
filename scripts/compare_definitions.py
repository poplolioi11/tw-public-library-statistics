#!/usr/bin/env python3
"""Read-only lookup and explicit operation guards for the definition audit."""
import argparse,json,sqlite3
from pathlib import Path
from phase2_engine import ROOT,compare,guard_operation
STRUCTURED={'facets','reasons','quality_flags_original','supporting_evidence_ids'}
def decode(row):
 r=dict(row)
 for k in STRUCTURED:r[k]=json.loads(r[k]) if r.get(k) is not None else None
 for k in ('comparison_year','comparison_month'):r[k]=int(r[k]) if r.get(k) not in (None,'') else None
 return r
def lookup(con,key):
 keys=[key] if ':' in key and key.split(':',1)[0] in ('canonical','local_statistical_cells','programme_quantities') else [layer+':'+key for layer in ('canonical','local_statistical_cells','programme_quantities')]
 rows=[]
 for k in keys:
  row=con.execute('SELECT * FROM annotations WHERE record_key=?',(k,)).fetchone()
  if row is not None:rows.append(decode(row))
 if len(rows)!=1:raise ValueError('Record identity is missing or ambiguous; use exact layer:observation_id')
 return rows[0]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--left');p.add_argument('--right');p.add_argument('--lookup');p.add_argument('--group');p.add_argument('--limit',type=int,default=20);p.add_argument('--operation',default='join-time-series');a=p.parse_args();root=a.root.resolve();version=(root/'VERSION').read_text().strip();guard=guard_operation(a.operation)
 if guard:print(json.dumps({'dataset_version':version,**guard},ensure_ascii=False,indent=2));return
 con=sqlite3.connect('file:'+str(root/'derived/phase2/definitions.sqlite')+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;con.execute('PRAGMA query_only=ON')
 try:
  if a.lookup:result={'record':lookup(con,a.lookup)}
  elif a.group:
   if not 1<=a.limit<=1000:raise ValueError('limit must be1–1000')
   row=con.execute('SELECT * FROM comparison_groups WHERE comparison_group_id=?',(a.group,)).fetchone()
   if row is None:raise ValueError('Unknown definition group')
   result={'group':{k:json.loads(v) if k in ('source_ids','evidence_ids','source_urls','source_sha256s','facets','periods','years','status_counts','eligible_periods','record_keys') and v is not None else v for k,v in dict(row).items()}}
   keys=result['group']['record_keys'];result['group']['record_keys']=keys[:a.limit];result['group'].update(record_keys_total=len(keys),record_keys_returned=min(len(keys),a.limit),record_keys_truncated=len(keys)>a.limit)
  elif a.left and a.right:result=compare(lookup(con,a.left),lookup(con,a.right))
  else:p.error('Use --lookup, --group, or both --left and --right')
  print(json.dumps({'dataset_version':version,'SQL_scalar_values_are_text':True,'raw_data_modified':False,**result},ensure_ascii=False,indent=2))
 finally:con.close()
if __name__=='__main__':main()
