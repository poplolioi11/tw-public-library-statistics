#!/usr/bin/env python3
"""Source-bound definition cards for the twelve fully inventoried originals."""
import argparse, collections, hashlib, json
from pathlib import Path
import record_io

ROOT=Path(__file__).resolve().parents[1]


def stable(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def build(root=ROOT):
    rows=[r for r in record_io.rows(root) if str(r['source_id']).startswith('discovered-')]
    report=json.loads((root/'raw/discovered-20261028/extraction-metadata.json').read_text())
    if len(rows)!=report['canonical_observations_added']:
        raise ValueError('Definition review requires the complete formally ingested batch')
    groups=collections.defaultdict(list)
    for r in rows:groups[r['source_id']].append(r)
    cards=[]
    for sid,batch in sorted(groups.items()):
        first=batch[0];digest=first['source_sha256']
        if any(r['source_sha256']!=digest for r in batch):raise ValueError('Mixed original versions')
        path=root/first['source_snapshot_path']
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Original SHA differs from reviewed source')
        years=sorted({r['data_year'] for r in batch if r['data_year'] is not None})
        monthly=any(r['period_basis']=='literal_original_year_month' for r in batch)
        eid='p2-discovered-'+hashlib.sha256((sid+'|'+digest).encode()).hexdigest()[:24]
        panel=len(years)>1 or monthly
        policies=[]
        unresolved=[r['observation_id'] for r in batch if r['data_year'] is None
                    or 'unresolved' in r['temporal_kind'] or 'week' in r['temporal_kind']
                    or any('conflict' in str(f) and 'publication_month' not in str(f) or 'requires_context_review' in str(f) for f in json.loads(r.get('quality_flags') or '[]'))
                    or r['aggregation_role'] in ('source_graph_reference','reference_line_not_business_total','published_rank_not_business_quantity')]
        if unresolved:
            policies.append({'rule_id':'original_period_or_aggregation_not_annual_business_series',
                             'observation_ids':unresolved,'status':'unresolved',
                             'reason':'original_period_unit_or_aggregation_basis_unresolved_or_reference_only'})
        if first['component_source_id']=='ntpc-cultural-2015':
            policies.append({'rule_id':'ntpc_collection_inclusion_break_2010','indicators':['藏書冊數'],
                             'year_segments':[{'years':list(range(2006,2010))},{'years':list(range(2010,2016))}],
                             'reason':'95至98年不含非書；99年起含圖書電子與非書，不跨斷點接線。'})
        cards.append({'evidence_id':eid,'source_id':sid,'source_sha256':digest,
                      'source_url':first['source_url'],'source_urls':sorted({r['source_url'] for r in batch}),
                      'source_locator':{'table':first['source_table'],'pdf_pages':sorted({r['source_pdf_page'] for r in batch if r['source_pdf_page'] is not None}),
                                        'raw_locator_examples':[r['source_locator'] for r in batch[:3]]},
                      'layer':'canonical','source_table':first['source_table'],
                      'source_table_title':first['source_table_title'],
                      'source_fields':sorted({r['source_field'] for r in batch}),
                      'indicators':sorted({r['indicator'] for r in batch}),
                      'series_ids':sorted({r['series_id'] for r in batch}),
                      'data_years_present':years,'unresolved_period_records':sum(r['data_year'] is None for r in batch),
                      'reviewed_original':True,
                      'review_method':'Pinned original SHA; complete physical-cell inventory; per-cell extraction and original-label checks preserved in source_cell_note_raw and extraction metadata. Two text engines are not independent image review; scanned cells identify their OCR and image-review limits.',
                      'semantic_facts':{'retained_original_temporal_kinds':sorted({r['temporal_kind'] for r in batch}),
                                        'retained_units':sorted({r['unit'] for r in batch if r['unit'] is not None}),
                                        'population_scopes':sorted({r['population_scope'] for r in batch}),
                                        'aggregation_roles':sorted({r['aggregation_role'] for r in batch}),
                                        'source_qualifiers_preserved_in':'canonical source_time_reference/source_cell_note_raw/notes; full extracted source-cell files',
                                        'full_original_table_scope_not_entire_publication':True,
                                        'annual_and_monthly_rows_not_additive':True,
                                        'cross_source_equivalence_confirmed':False},
                      'original_notes_short':list(dict.fromkeys(r['notes'] for r in batch if r['notes']))[:12],
                      'supported_comparison_scope':{'status':'published_panel_limited' if panel else 'source_series_only',
                                                    'panel_id':eid+'-panel',
                                                    'positive_scope':'Same original table, exact entity, field, unit, period kind and reviewed segment only. No source-version splicing, imputation or aggregation; source publication does not certify invariant collection methodology.',
                                                    'data_years':years,'monthly_original_labels':monthly},
                      'field_policies':policies,'observation_ids':sorted(r['observation_id'] for r in batch),
                      'full_originals_distributed':False,'numeric_values_modified':False})
    obj={'schema_version':'1.0.0','scope':'Twelve newly incorporated originals; complete selected tables and continuations only.',
         'source_cards':cards,'canonical_observations':len(rows),'source_documents':report['source_documents'],
         'cross_source_panel_permission':False,'unknowns_imputed':False,
         'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out=root/'research/phase2-discovered-evidence.json';body=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    if not out.exists() or out.read_text()!=body:out.write_text(body)
    return {'source_cards':len(cards),'records':len(rows),'definition_breaks':sum(len(c['field_policies']) for c in cards)}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);args=ap.parse_args()
    print(json.dumps(build(args.root.resolve()),ensure_ascii=False))
