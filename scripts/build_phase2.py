#!/usr/bin/env python3
"""Materialize a complete, separate definition audit with stable three-format views."""
import argparse,csv,gzip,hashlib,io,json,sqlite3,tempfile
from collections import Counter,defaultdict
from pathlib import Path
from phase2_engine import ROOT,EVIDENCE_FILES,LAYERS,annotate,card_index,compare,evidence_cards,fingerprint,load_inputs,sha,stable
def cell(v):return stable(v) if isinstance(v,(dict,list,bool)) else v
def fields(rows):return list(dict.fromkeys(k for r in rows for k in r))
def gzip_body(body):
 out=io.BytesIO()
 with gzip.GzipFile(filename='',mode='wb',fileobj=out,compresslevel=9,mtime=0) as f:f.write(body)
 return out.getvalue()
def table_buffers(name,rows,compressed=False):
 keys=fields(rows);text=''.join(stable(r)+'\n' for r in rows).encode();buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=keys);writer.writeheader();writer.writerows([{k:cell(v) for k,v in r.items()} for r in rows]);data=buf.getvalue().encode('utf-8-sig')
 ext='.gz' if compressed else '';return {name+'.jsonl'+ext:gzip_body(text) if compressed else text,name+'.csv'+ext:gzip_body(data) if compressed else data}
def file_hash(path):return sha(path.read_bytes())
def replace_if_changed(path,body):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists() or path.read_bytes()!=body:
  tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(body);tmp.replace(path)
def sql_ident(x):return '"'+x.replace('"','""')+'"'
def sql_table(con,name,rows):
 keys=fields(rows);con.execute('CREATE TABLE '+sql_ident(name)+' ('+','.join(sql_ident(k)+' TEXT' for k in keys)+')');con.executemany('INSERT INTO '+sql_ident(name)+' VALUES ('+','.join('?' for _ in keys)+')',[[cell(r.get(k)) for k in keys] for r in rows]);return keys
def compact_annotations(con,annotations,groups):
 keys=[k for k in fields(annotations) if k not in ('record_key','facets')];values={};coded=[]
 for r in annotations:
  codes=[]
  for k in keys:
   value=cell(r.get(k));value=None if value is None else str(value)
   if value is not None and value not in values:values[value]=len(values)+1
   codes.append(None if value is None else values[value])
  coded.append([r['record_key'],*codes])
 con.execute('CREATE TABLE value_dictionary(value_id INTEGER PRIMARY KEY, value TEXT NOT NULL)');con.executemany('INSERT INTO value_dictionary VALUES (?,?)',[(i,v) for v,i in values.items()]);con.execute('CREATE TABLE annotation_codes(record_key TEXT PRIMARY KEY,'+','.join(sql_ident(k)+' INTEGER' for k in keys)+')');con.executemany('INSERT INTO annotation_codes VALUES ('+','.join('?' for _ in range(len(keys)+1))+')',coded)
 sql_table(con,'comparison_definitions',[{'comparison_group_id':g['comparison_group_id'],'facets':g['facets']} for g in groups]);con.execute('CREATE UNIQUE INDEX definition_key ON comparison_definitions(comparison_group_id)')
 cols=['r.record_key'];joins=[]
 for i,k in enumerate(keys):
  alias='v'+str(i);cols.append(alias+'.value AS '+sql_ident(k));joins.append(' LEFT JOIN value_dictionary '+alias+' ON '+alias+'.value_id=r.'+sql_ident(k))
 group_alias='v'+str(keys.index('comparison_group_id'));cols.append('d.facets AS facets');con.execute('CREATE VIEW annotations AS SELECT '+','.join(cols)+' FROM annotation_codes r'+''.join(joins)+' JOIN comparison_definitions d ON d.comparison_group_id='+group_alias+'.value')
 group_data=[{k:v for k,v in g.items() if k!='facets'} for g in groups];group_keys=sql_table(con,'group_records',group_data);con.execute('CREATE UNIQUE INDEX group_record_key ON group_records(comparison_group_id)');con.execute('CREATE VIEW comparison_groups AS SELECT g.*,d.facets FROM group_records g JOIN comparison_definitions d USING(comparison_group_id)')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();root=a.root.resolve();version=(root/'VERSION').read_text().strip()
 input_paths=[*EVIDENCE_FILES,'raw/phase2-definitions/current-reference-sources.json','docs/phase2-contract.json','scripts/phase2_engine.py','scripts/build_phase2.py']
 before={name:file_hash(root/name) for name in input_paths};cards=evidence_cards(root);index=card_index(cards);inputs=list(load_inputs(root));annotations=[];covered=set();source_groups=defaultdict(list);runtime=[]
 for layer,r in inputs:source_groups[(layer,r['source_id'],r['source_sha256'])].append(r)
 for group_key,group_rows_input in sorted(source_groups.items()):
  layer=group_key[0];selected_cards={}
  for r in group_rows_input:
   key=(layer,r['observation_id'])
   if key in covered:raise ValueError('Duplicate quantitative source identity: '+str(key))
   covered.add(key)
   if key not in index:raise ValueError('No reviewed source-definition card: '+str(key))
   card=index[key]
   if card['source_id']!=r['source_id'] or card['source_sha256']!=r['source_sha256']:raise ValueError('Evidence original SHA/source mismatch: '+str(key))
   selected_cards[card['evidence_id']]=card
  signature=sha(stable({'source_group':group_key,'records':fingerprint(group_rows_input),'cards':selected_cards,'engine':before['scripts/phase2_engine.py']}).encode());cache=root/'data/cache/phase2-annotations'/signature;cache_body=cache.with_suffix('.jsonl');cache_hash=cache.with_suffix('.sha256')
  reused=cache_body.exists() and cache_hash.exists() and file_hash(cache_body)==cache_hash.read_text().strip()
  if reused:batch=[json.loads(x) for x in cache_body.read_text().splitlines()]
  else:
   batch=[annotate(layer,r,index[(layer,r['observation_id'])]) for r in group_rows_input];body=''.join(stable(r)+'\n' for r in batch).encode();replace_if_changed(cache_body,body);replace_if_changed(cache_hash,(sha(body)+'\n').encode())
  if [r['observation_id'] for r in batch]!=[r['observation_id'] for r in group_rows_input]:raise ValueError('Cached source annotation identities differ')
  annotations+=batch;runtime.append({'layer':layer,'source_id':group_key[1],'source_sha256':group_key[2],'records':len(batch),'reused':reused})
 if set(index)-covered:raise ValueError('Evidence points at unknown quantitative records')
 annotations.sort(key=lambda r:r['record_key']);groups=defaultdict(list)
 for r in annotations:groups[r['comparison_group_id']].append(r)
 group_rows=[]
 for gid,items in sorted(groups.items()):
  first=items[0];periods=sorted({(r['comparison_year'],r['comparison_month']) for r in items if r['comparison_year'] is not None},key=lambda x:(x[0],x[1] or 0));eligible=[r for r in items if r['comparison_status']=='published_panel_limited'];eligible_periods={(r['comparison_year'],r['comparison_month']) for r in eligible}
  group_rows.append({'comparison_group_id':gid,'definition_signature':first['definition_signature'],'layer':first['layer'],'raw_indicator':first['raw_indicator'],'source_ids':sorted({r['source_id'] for r in items}),'evidence_ids':sorted({r['evidence_id'] for r in items}),'source_urls':sorted({r['source_url'] for r in items}),'source_sha256s':sorted({r['source_sha256'] for r in items}),'facets':first['facets'],'comparison_unit':first['comparison_unit'],'records':len(items),'periods':periods,'years':sorted({y for y,m in periods}),'status_counts':dict(sorted(Counter(r['comparison_status'] for r in items).items())),'eligible_periods':sorted(eligible_periods,key=lambda x:(x[0] or 0,x[1] or 0)),'has_multiple_eligible_periods':len(eligible_periods)>1,'record_keys':[r['record_key'] for r in items],'no_automatic_cross_source_union':True,'limitation':'Only exact original-entity/source/table/grid/metric/unit/classification/period segment. Reporting-rule invariance and completeness are not certified.'})
 card_rows=[];breaks=[]
 for c in cards:
  card_rows.append(c)
  for kind in ('field_policies','field_breaks'):
   for i,r in enumerate(c.get(kind,[])):
    breaks.append({'breakpoint_id':c['evidence_id']+':'+kind+':'+str(i),'evidence_id':c['evidence_id'],'source_id':c['source_id'],'source_sha256':c['source_sha256'],'source_url':c['source_url'],'kind':kind,'policy':r,'cross_source_application_permitted':False})
 buffers={};buffers.update(table_buffers('annotations',annotations,True));buffers.update(table_buffers('groups',group_rows));buffers.update(table_buffers('evidence_cards',card_rows));buffers.update(table_buffers('breakpoints',breaks))
 partitions=[];by_year=defaultdict(list)
 for r in annotations:by_year[(r['layer'],r['comparison_year'])].append(r)
 for (layer,year),rows in sorted(by_year.items(),key=lambda x:(x[0][0],x[0][1] or 0)):
  name='by_year/'+layer+'/'+str(year if year is not None else 'unresolved_period');parts=table_buffers(name,rows);buffers.update(parts);partitions.append({'layer':layer,'comparison_year':year,'records':len(rows),'jsonl':'derived/phase2/'+name+'.jsonl','csv':'derived/phase2/'+name+'.csv','jsonl_sha256':sha(parts[name+'.jsonl']),'csv_sha256':sha(parts[name+'.csv'])})
 # Normalize repeated definition facets once; expose a wide read-only SQL view.
 with tempfile.TemporaryDirectory(prefix='phase2-build-') as temp:
  db=Path(temp)/'definitions.sqlite';con=sqlite3.connect(db);con.execute('PRAGMA page_size=32768');compact_annotations(con,annotations,group_rows);sql_table(con,'evidence_cards',card_rows);sql_table(con,'breakpoints',breaks);con.commit();con.close();dbbody=db.read_bytes()
 if len(dbbody)>=104857600:raise ValueError('Definition database exceeds100MiB; partition before publication')
 buffers['definitions.sqlite']=dbbody
 source_counts=dict(sorted(Counter(layer for layer,r in inputs).items()));core=[r for layer,r in inputs if layer=='canonical']
 status=Counter(r['comparison_status'] for r in annotations);unit_upgrades=sum(r['unit_audit_status']=='literal_suffix_verified' for r in annotations);monthly=sum(r['period_audit_status']=='verified_original_statistical_year_month_code' for r in annotations)
 summary={'schema_version':'1.0.0','dataset_version':version,'scope':'All existing quantitative records audited in a separate evidence-qualified definition layer; raw data unchanged.','layers':source_counts,'total_quantitative_records':len(annotations),'programme_row_view_not_added':119,'original_cell_view_not_added':33705,'source_definition_cards':len(cards),'comparison_groups':len(group_rows),'groups_with_multiple_eligible_periods':sum(g['has_multiple_eligible_periods'] for g in group_rows),'groups_with_multiple_eligible_years':sum(len({y for y,m in g['eligible_periods'] if y is not None})>1 for g in group_rows),'comparison_status_counts':dict(sorted(status.items())),'literal_unit_suffix_upgrades':unit_upgrades,'strict_literal_month_code_records':monthly,'breakpoint_rules':len(breaks),'canonical_statistical_content_sha256':fingerprint(core),'canonical_values_modified':False,'all_years_all_definitions_certified':False,'all_history_complete':False,'no_imputation':True,'no_geographic_recoding':True,'positive_interpretation':'published_panel_limited permits only the original published panel and exact qualifiers, not invariant historical collection methods.','comparison_operation':'Join the same original entity into a time series. No automatic sums, unique-people inference, source selection, missing-value filling or cross-family splicing.','inputs':before,'layer_raw_fingerprints':{layer:fingerprint([r for l,r in inputs if l==layer]) for layer in LAYERS},'outputs':{('derived/phase2/'+n):{'sha256':sha(b),'bytes':len(b)} for n,b in sorted(buffers.items())},'partition_index':'docs/phase2-partitions.json'}
 if before!={name:file_hash(root/name) for name in input_paths}:raise ValueError('Definition source changed during build; previous outputs retained')
 for name,body in buffers.items():replace_if_changed(root/'derived/phase2'/name,body)
 replace_if_changed(root/'docs/phase2-partitions.json',(json.dumps({'schema_version':'1.0.0','version':version,'parent':'derived/phase2/annotations.jsonl.gz','records':len(annotations),'partitions':partitions,'unresolved_years_are_not_assigned_from_catalogues':True},ensure_ascii=False,indent=2)+'\n').encode())
 replace_if_changed(root/'docs/phase2-summary.json',(json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode())
 replace_if_changed(root/'data/phase2-build-runtime.private.json',(json.dumps({'sources':runtime,'reused_source_groups':sum(r['reused'] for r in runtime),'recomputed_source_groups':sum(not r['reused'] for r in runtime)},ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({k:summary[k] for k in ('dataset_version','total_quantitative_records','source_definition_cards','comparison_groups','groups_with_multiple_eligible_periods','comparison_status_counts','literal_unit_suffix_upgrades','strict_literal_month_code_records','breakpoint_rules')}))
if __name__=='__main__':main()
