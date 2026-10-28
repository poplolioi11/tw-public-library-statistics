#!/usr/bin/env python3
"""Complete standalone source-selection reader with Python-rendered source plots."""
from __future__ import annotations
import argparse,gzip,hashlib,json
from build_phase3_charts import compile_charts
from pathlib import Path
import reader_transport
ROOT=Path(__file__).resolve().parents[1]
PRODUCTS={'record_routes':'derived/phase3/record_routes.jsonl.gz','candidate_decisions':'derived/phase3/candidate_decisions.jsonl.gz','queries':'derived/phase3/queries.jsonl','series_edges':'derived/phase3/series_edges.jsonl'}

def stable(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def replace_if_changed(path,body):
    if path.exists() and path.read_bytes()==body:return False
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.tmp');temporary.write_bytes(body);temporary.replace(path);return True

def read_rows(path):
    with (gzip.open(path,'rt',encoding='utf-8') if path.suffix=='.gz' else path.open(encoding='utf-8')) as stream:
        return [json.loads(line) for line in stream if line.strip()]

def assert_public_facts(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in {'original_fields','source_workspace_relative_path','private_storage_root','drive_root','workspace_root'}:raise ValueError('Private routing or duplicate whole-row field in reader input: '+key)
            assert_public_facts(item)
    elif isinstance(value,list):
        for item in value:assert_public_facts(item)
    elif isinstance(value,str) and any(token in value for token in ('/Users/','file:///','/Volumes/')):raise ValueError('Private absolute storage location in reader input')

def load_source_products(root):
    version=(root/'VERSION').read_text().strip();summary=json.loads((root/'docs/phase3-summary.json').read_text());contract=json.loads((root/'docs/phase3-contract.json').read_text());manifest=json.loads((root/'docs/phase3-profiles.json').read_text())
    if summary['dataset_version']!=version:raise ValueError('Rebuild phase3 before its reader/documentation')
    if manifest.get('dataset_version',version)!=version:raise ValueError('Profile and dataset version differ')
    profiles=manifest['profiles'];ids=[profile['id'] for profile in profiles]
    if len(ids)!=len(set(ids)) or set(ids)!=set(contract['profiles']):raise ValueError('Registered profile IDs differ from contract')
    tables={name:read_rows(root/relative) for name,relative in PRODUCTS.items()}
    counts={name:len(rows) for name,rows in tables.items()}
    for name,required in [('record_routes',contract['required_route_fields']),('candidate_decisions',contract['required_decision_fields']),('series_edges',contract.get('edge_fields',[]))]:
        for row in tables[name]:
            if set(required)-set(row):raise ValueError('Missing '+name+' reader fields: '+','.join(sorted(set(required)-set(row))))
    if len({row['record_key'] for row in tables['record_routes']})!=counts['record_routes']:raise ValueError('Duplicate record-route identity')
    if len({row['decision_id'] for row in tables['candidate_decisions']})!=counts['candidate_decisions']:raise ValueError('Duplicate candidate-decision identity')
    if {row['profile_id'] for row in tables['queries']}!=set(ids) or counts['queries']!=len(ids):raise ValueError('Default query/profile coverage differs')
    if any(row['profile_id'] not in ids for name in ('candidate_decisions','series_edges') for row in tables[name]):raise ValueError('Unregistered profile in reader records')
    declared=summary.get('counts',{})
    if isinstance(declared,dict):
        for name,total in counts.items():
            if name in declared and isinstance(declared[name],int) and declared[name]!=total:raise ValueError('Summary reader count differs: '+name)
    bindings={relative:sha(root/relative) for relative in PRODUCTS.values()}
    for relative,digest in bindings.items():
        expected=summary.get('outputs',{}).get(relative)
        if expected is not None:
            expected=expected.get('sha256') if isinstance(expected,dict) else expected
            if expected!=digest:raise ValueError('Phase3 output changed after summary: '+relative)
    for relative in ('VERSION','docs/phase3-summary.json','docs/phase3-profiles.json','docs/phase3-contract.json'):bindings[relative]=sha(root/relative)
    return {'version':version,'summary':summary,'contract':contract,'profile_manifest':manifest,'profiles':profiles,'tables':tables,'counts':counts,'input_sha256':bindings}

def pack_tables(tables):
    """Intern exact JSON values; -1 distinguishes absent keys from JSON null."""
    pool=[];index={};packed={}
    for name,rows in tables.items():
        columns=list(dict.fromkeys(key for row in rows for key in row));vectors=[]
        for row in rows:
            vector=[]
            for field in columns:
                if field not in row:vector.append(-1);continue
                value=row[field];key=stable(value)
                if key not in index:index[key]=len(pool);pool.append(value)
                vector.append(index[key])
            vectors.append(vector)
        packed[name]={'columns':columns,'rows':vectors,'records':len(rows)}
        # Full roundtrip, not a sample, including sparse keys and null/zero.
        for source,vector in zip(rows,vectors,strict=True):
            restored={field:pool[value] for field,value in zip(columns,vector,strict=True) if value!=-1}
            if stable(restored)!=stable(source):raise ValueError('Reader dictionary roundtrip differs: '+name)
    return pool,packed

def build_payload(root):
    products=load_source_products(root);routes=products['tables']['record_routes'];wanted={row['record_key'] for row in routes};context=[]
    p2=root/'derived/phase2/annotations.jsonl.gz'
    annotations=read_rows(p2)
    for row in annotations:
        if row['record_key'] not in wanted:continue
        facet=row.get('facets',{})
        context.append({'record_key':row['record_key'],'raw_indicator':row.get('raw_indicator'),'entity':facet.get('entity'),'facility_or_reader_category':facet.get('facility_or_reader_category'),'period_kind':row.get('period_kind')})
    if len(context)!=len(wanted) or {row['record_key'] for row in context}!=wanted:raise ValueError('P2 presentation context does not exactly cover routes')
    products['input_sha256']['derived/phase2/annotations.jsonl.gz']=sha(p2)
    inputs={**products['tables'],'record_context':context};assert_public_facts({'profiles':products['profiles'],'tables':inputs})
    pool,tables=pack_tables(inputs)
    chart_data=compile_charts(root,products['tables'],products['profiles'],annotations)
    return {**chart_data,'schema_version':'phase3-standalone-reader-1.0','dataset_version':products['version'],'summary':products['summary'],'profiles':products['profiles'],'counts':products['counts'],'pool':pool,'tables':tables,'input_sha256':products['input_sha256'],'coverage':'All four phase3 source tables; record_context is presentation metadata, not another observation layer.','filter_semantics':'Display-only filtering of precomputed default decisions. Run select_sources.py to recompute a purpose/interval/fixed-source selection.','chart_policy':'Complete qualified original groups with direct source links; interval presets execute the same Python source selector.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args();root=args.root.resolve();payload=build_payload(root)
    template=(root/'site/phase3-template.html').read_text();token='__PHASE3_DATA__'
    if template.count(token)!=1:raise ValueError('Reader template needs exactly one data placeholder')
    packed=reader_transport.encode(payload)
    if reader_transport.decode(packed)!=payload:raise ValueError('Complete portable-reader compression roundtrip differs')
    text=template.replace(token,packed.replace('</','<\\/'));body=text.encode()
    if len(body)>=104857600:raise ValueError('Complete standalone reader exceeds100MiB; do not publish a truncated sample')
    changed=replace_if_changed(root/'site/phase3.html',body)
    preferred=[c for c in payload['charts'].values() if c['profile_id']=='national-ncl-book-loans-panel' and c['default_selected']]
    if not preferred:raise ValueError('Expected visible default national original-panel chart')
    from series_charts import svg
    plot=preferred[0];default={'dataset_version':payload['dataset_version'],'profile_id':plot['profile_id'],'label':plot['label'],'svg':svg(plot),'source_points':plot['source_points'],'plotted_points':plot['plotted_points'],'drawable_segments':plot['drawable_segments'],'scope':'Same reviewed original published panel only; no imputation or method-invariance certification.'}
    replace_if_changed(root/'docs/phase3-default-chart.json',(json.dumps(default,ensure_ascii=False,indent=2)+'\n').encode())
    replace_if_changed(root/'docs/phase3-reader-summary.json',(json.dumps({'dataset_version':payload['dataset_version'],'profiles':len(payload['profiles']),'charts':payload['chart_count'],'interval_queries':payload['interval_query_count'],'counts':payload['counts'],'reader_bytes':len(body),'reader_sha256':hashlib.sha256(body).hexdigest(),'input_sha256':payload['input_sha256'],'only_authorized_adjacent_lines':True},ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({'version':payload['dataset_version'],'profiles':len(payload['profiles']),'complete_table_counts':payload['counts'],'pool_values':len(payload['pool']),'reader_bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'changed':changed,'roundtrip':'all source rows and fields exactly restored; missing keys remain distinct from null'},ensure_ascii=False))
if __name__=='__main__':main()
