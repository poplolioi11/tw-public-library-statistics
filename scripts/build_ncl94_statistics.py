#!/usr/bin/env python3
"""Build the complete public-library subsets of NCL94 tables145/146/147.

Sixteen physical cells contain24 distinct reported quantities. The eight
parenthesized response counts are separate indicators, never library totals.
Only statistical facts and necessary labels are exported, not the full PDF.
"""
import csv, hashlib, json, re, subprocess, sys
from pathlib import Path
from build_discovered_20261028 import adapt
import record_io

ROOT = Path(__file__).resolve().parents[1]
TITLES = {
    '145': '臺閩地區各類型圖書館數量統計表（民國93年）',
    '146': '臺閩地區各類型圖書館基本資料統計表（民國93年）',
    '147': '中華圖書資訊館際合作協會各類型會員數量統計表（民國93年）',
}


def main():
    document = json.loads((ROOT/'raw/ncl94-statistics/documents.json').read_text())['documents'][0]
    output = ROOT/'derived/ncl94_statistics_source_cells.json'
    subprocess.run([sys.executable, str(ROOT/'scripts/extract_ncl94_statistics.py'),
                    '--source', str(ROOT/document['source_local_path']),
                    '--output', str(output)], check=True)
    batch = json.loads(output.read_text())
    rows, trace = [], []
    for physical in batch['cells']:
        table = physical['source_table']
        responding = physical['parenthesized_responding_libraries']
        quantities = [('primary', physical['value'])]
        if responding is not None:
            quantities.append(('responding_libraries', responding['value']))
        numeral_strings = re.findall(r'\d[\d,]*', physical['source_raw_pdfminer'])
        assert len(numeral_strings) == len(quantities)
        for i, (role, value) in enumerate(quantities):
            is_response = role == 'responding_libraries'
            raw = numeral_strings[i]
            metric = ('圖書館數量' if table == '145' else
                      '公共類會員數量' if table == '147' else
                      physical['source_column_context'])
            indicator = metric+'／填答館數' if is_response else metric
            entity = physical['source_row_label_raw'] if table != '147' else '公共'
            population = physical['population_scope']
            if is_response:
                population += '；僅此指標填答館數，不含分館，分館資料併入總館，非總館數'
            bbox = (responding['source_bbox_points_top_origin'] if is_response
                    else physical['source_bbox_points_top_origin'])
            context = {**physical, 'physical_cell_id': physical['cell_id'],
                       'quantity_role': role,
                       'reported_quantity_raw': raw,
                       'parenthetical_response_is_total_library_count': False,
                       'full_cell_punctuation_review': 'AI visual transcription; native PDF engines omit parentheses; not human review'}
            cell = {
                'cell_id': physical['cell_id']+'/'+role,
                'source_document_id': 'ncl-ed94-statistics',
                'source_url': physical['source_url'],
                'source_catalogue_url': physical['source_catalogue_url'],
                'source_sha256': physical['source_sha256'],
                'source_version_id': physical['source_version_id'],
                'source_pdf_page': physical['source_pdf_page'],
                'source_printed_page': physical['source_printed_page'],
                'source_table': table, 'source_table_title': TITLES[table],
                'source_row': physical['source_row'],
                'source_column': physical['source_column'],
                'source_locator': physical['source_locator']+'; quantity '+role,
                'source_cell_bbox': bbox, 'row_label_raw': entity,
                'column_label_raw': ('填答館數' if is_response else physical['source_column_label_raw']),
                'entity_raw': entity,
                'entity_kind': 'cooperation_membership_public_category' if table == '147' else 'published_public_library_type',
                'geography_vintage': '臺閩地區原刊館型分類，非縣市面板',
                'data_year': 2004, 'period_raw': '民國93年',
                'period_status': 'explicit_original_table_ROC_year_exact_dates_unconfirmed',
                'metric_id': 't'+table+'-c'+physical['source_column']+'-'+role,
                'metric_raw': indicator, 'value': value, 'value_raw': raw,
                'value_status': 'reported',
                'unit': '館' if is_response else physical['unit'],
                'unit_raw': '填答館數' if is_response else physical['unit_raw'],
                'unit_status': responding['unit_status'] if is_response else physical['unit_status'],
                'temporal_kind': 'annual_source_reference_exact_period_unconfirmed',
                'population_scope': population,
                'national_libraries_scope': 'national_library_separately_listed_not_in_selected_public_subgroup',
                'aggregation_role': 'responding_libraries_not_total_libraries' if is_response else 'published_subtotal' if table == '145' and physical['source_row']=='7' else 'source_type_quantity',
                'source_notes': physical['notes']+['公私立、圖書館類型、小計及會員母體分開；不與其他版本或館型相加。'],
                'quality_flags': ['AI_visual_review_not_human_collation', 'exact_dates_unconfirmed'],
                'independent_check': {'method': physical['numeric_check']['method'],
                                      'matched': physical['numeric_check']['matched'],
                                      'numeric_tokens': physical['numeric_check'],
                                      'human_review': False},
                'source_edition': '中華民國九十四年圖書館年鑑',
                'source_edition_roc': 94,
                'physical_source_context': context,
            }
            row = adapt(cell, document)
            row['value_parse_rule'] = 'separate_literal_quantity_in_same_physical_cell; original_full_cell_and_response_role_in_source_time_reference'
            row['unit_basis'] = 'literal_column_label' if row['unit'] else 'no_independent_unit_printed; counting_object_in_caption_and_population'
            rows.append(row)
            trace.append({**cell, 'source_id': row['source_id'],
                          'source_download_url': document['official_url'],
                          'source_url': document['catalogue_url'],
                          'source_local_path': document['source_local_path'],
                          'source_retrieved_at': document['retrieved_at'],
                          'source_title': document['title'], 'publication_date': '',
                          'observation_id': row['observation_id']})
    assert len(rows) == len({x['observation_id'] for x in rows}) == 24
    columns = json.loads((ROOT/'scripts/discovered_20261028_canonical_columns.json').read_text())['columns']
    assert all(not (set(row)-set(columns)) for row in rows)
    rows = [{k: row.get(k) for k in columns} for row in rows]
    record_io.write(ROOT, 'derived/ncl94_statistics_observations.jsonl', rows)
    target = ROOT/'derived/ncl94_statistics_long.csv'
    fields = list(dict.fromkeys(k for row in trace for k in row))
    with target.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({k: json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in trace)
    summary = {k:v for k,v in batch.items() if k!='cells'}
    summary.update(formal_observations=24, new_source_tables=['145','146','147'],
                   unit_null_observations=8, source_edition_roc=94, data_year=2004,
                   quantity_roles={'primary':16,'responding_libraries':8},
                   excluded_scope='國家圖書館及非公共館列；圖10–29非公共館或混合母體圖表；全文與照片未散布',
                   statistical_facts_only=True, no_cross_source_panel=True)
    (ROOT/'raw/ncl94-statistics/extraction-metadata.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    cards=[]
    for table in TITLES:
        subset=[r for r in rows if r['source_table']==table]
        first=subset[0]
        cards.append({
            'evidence_id':'p2-ncl94-statistics-'+table+'-'+document['source_sha256'][:16],
            'source_id':first['source_id'], 'source_sha256':document['source_sha256'],
            'layer':'canonical', 'source_url':first['source_url'],
            'source_urls':sorted({r['source_url'] for r in subset}),
            'source_locator':{'table':table,'pdf_pages':[first['source_pdf_page']],
                              'raw_locator_examples':[r['source_locator'] for r in subset[:3]]},
            'source_table':table,'source_table_title':TITLES[table],
            'source_fields':list(dict.fromkeys(r['source_field'] for r in subset)),
            'indicators':sorted({r['indicator'] for r in subset}),
            'series_ids':sorted({r['series_id'] for r in subset}),
            'data_years_present':[2004],'unresolved_period_records':0,
            'reviewed_original':True,
            'review_method':'Complete public subgroup; pinned PDF; two text-engine numeric checks and AI page-image review. Not human reading or independent double collation.',
            'semantic_facts':{'retained_units':sorted({r['unit'] for r in subset if r['unit'] is not None}),
                              'population_scopes':sorted({r['population_scope'] for r in subset}),
                              'aggregation_roles':sorted({r['aggregation_role'] for r in subset}),
                              'cross_source_equivalence_confirmed':False,
                              'responding_libraries_not_total_libraries':True,
                              'exact_period_dates_unconfirmed':True},
            'original_notes_short':list(dict.fromkeys(r['notes'] for r in subset)),
            'supported_comparison_scope':{'status':'source_series_only',
                'positive_scope':'Single printed reference year only; no cross-source/year equivalence or additional line segments certified.',
                'data_years':[2004],'monthly_original_labels':False},
            'field_policies':[],
            'observation_ids':sorted(r['observation_id'] for r in subset),
            'human_review_completed':False,'human_double_collation_completed':False,
            'full_originals_distributed':False,'numeric_values_modified':False,
        })
    evidence={'schema_version':'1.0.0','source_cards':cards,
              'scope':'NCL94 statistics145/146/147 public-library subsets only; single reference year; no panel certification',
              'canonical_observations':24,'source_documents':1,
              'human_double_collation_completed':False,'cross_source_panel_permission':False}
    (ROOT/'raw/ncl94-statistics/definition-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'formal_observations':24,'physical_cells':16,'source_sha256':batch['source_sha256']}))


if __name__ == '__main__':
    main()
