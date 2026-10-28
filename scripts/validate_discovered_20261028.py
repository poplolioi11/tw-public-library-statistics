#!/usr/bin/env python3
"""Independent cell-to-canonical acceptance, not an extraction-code self test."""
import argparse, collections, decimal, hashlib, json
from pathlib import Path
from urllib.parse import urldefrag
import record_io

ROOT=Path(__file__).resolve().parents[1]


def need(condition,message):
    if not condition:raise ValueError(message)


def validate(root=ROOT,require_originals=False):
    root=Path(root)
    meta=json.loads((root/'raw/discovered-20261028/extraction-metadata.json').read_text())
    docs={r['candidate_id']:r for r in json.loads((root/'raw/discovered-20261028/documents.json').read_text())['documents']}
    cells=[]
    for group in ('central','local','ncl_early'):
        cells.extend(json.loads(x) for x in (root/f'derived/discovered_{group}_20261028_cells.jsonl').read_text().splitlines())
    need(len(docs)==meta['source_documents']==12,'Incomplete official-document batch')
    need(len(cells)==len({r['cell_id'] for r in cells})==meta['source_cells'],'Incomplete or duplicate physical cells')
    need(dict(collections.Counter(c['source_document_id'] for c in cells))==meta['source_counts'],'Complete-source counts differ')
    need({c['source_document_id'] for c in cells}==set(docs),'A selected original was omitted')
    expected=list(record_io.rows(root,'derived/discovered_20261028_observations.jsonl'))
    canonical=[r for r in record_io.rows(root) if str(r['source_id']).startswith('discovered-')]
    need(len(canonical)==len(expected)==len(cells),'Full source batch not present in canonical')
    by_cell={r['source_record_id']:r for r in canonical}
    need(len(by_cell)==len(canonical),'Duplicated physical source cell in canonical')
    expected_by_id={r['observation_id']:r for r in expected}
    for target in canonical:
        e=expected_by_id.get(target['observation_id']);need(e is not None,'Unexpected canonical original')
        for k,v in e.items():
            if k=='snapshot_distribution':continue  # existing public projection field
            need(target.get(k)==v,'Canonical mapped field differs: '+target['observation_id']+'/'+k)
    originals=0
    for sid,doc in docs.items():
        p=root/doc['source_local_path']
        if require_originals or p.is_file():
            need(p.is_file(),'Restore pinned original: '+sid)
            body=p.read_bytes()
            need(hashlib.sha256(body).hexdigest()==doc['source_sha256'] and len(body)==doc['source_bytes'],'Original body differs: '+sid)
            originals+=1
    for c in cells:
        d=docs[c['source_document_id']];r=by_cell[c['cell_id']]
        need(c['source_sha256']==d['source_sha256']==r['source_sha256'],'Original SHA lost')
        need(urldefrag(c['source_url'])[0]==d['official_url'],'Cell no longer points at official original')
        for out,src in [('raw_value','value_raw'),('value_status','value_status'),('data_year','data_year'),
                        ('geography','entity_raw'),('geographic_scope','entity_kind'),('indicator','metric_raw'),
                        ('unit','unit'),('unit_raw','unit_raw'),('temporal_kind','temporal_kind'),
                        ('population_scope','population_scope'),('aggregation_role','aggregation_role'),
                        ('period_raw','period_raw'),('source_locator','source_locator'),('source_url','source_url')]:
            need(r[out]==c[src],'Literal source field differs: '+c['cell_id']+'/'+out)
        need((r['value'] is None)==(c['value'] is None),'Null was filled or numeric cell dropped')
        if c['value'] is not None:
            need(decimal.Decimal(str(r['value']))==decimal.Decimal(c['value']),'Exact decimal number changed')
        if c.get('data_month') is not None:
            need(r['period_effective']==f"{c['data_year']:04d}-{c['data_month']:02d}" and r['periodicity_raw']=='月','Monthly cell was annualized')
        if c['data_year'] is None:
            need(r['period_start'] is None and r['period_end'] is None,'Unknown period assigned calendar dates')
        if 'unresolved' in c['temporal_kind']:
            need(r['period_end'] is None,'Unresolved annual aggregation was declared year-end stock')
        context=json.loads(r['source_time_reference'])
        for k in ('source_formula_raw','source_formula_denominator_raw','merged_cell_scope','source_display_region','source_table_year_context'):
            if k in c:need(context.get(k)==c[k],'Original qualifier was discarded: '+k)
    need(sum(r['data_year'] is None for r in canonical)==meta['unresolved_period_records'],'Unknown-year count differs')
    need(dict(collections.Counter(r['value_status'] for r in canonical))==meta['value_statuses'],'Original missing-state counts differ')
    need(not any(r['component_source_id']=='tpml-annual-2012' for r in canonical),'Rights-held annual publication leaked')
    return {'status':'PASS','official_originals':len(docs),'complete_source_cells':len(cells),
            'canonical_records':len(canonical),'original_bodies_verified':originals,
            'unresolved_period_records':meta['unresolved_period_records'],
            'null_cells':sum(r['value'] is None for r in canonical),'zero_cells':sum(r['value']==0 for r in canonical),
            'source_periods_units_and_qualifiers_preserved':True,'human_double_collation_claimed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--require-originals',action='store_true');a=p.parse_args()
    print(json.dumps(validate(a.root.resolve(),a.require_originals),ensure_ascii=False))
