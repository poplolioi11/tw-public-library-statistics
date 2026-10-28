#!/usr/bin/env python3
"""Register complete, pinned source tables as canonical facts without imputation.

Each extractor is cached by its own original-document and code hashes. A changed
original fails the pinned-SHA gate and retains the last accepted batch. Originals
are restored from official URLs; this program does not redistribute their PDFs.
"""
import argparse, calendar, collections, csv, decimal, hashlib, io, json, re, subprocess, sys
from pathlib import Path
import record_io

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    'central': ['ntpc-cultural-2015', 'tainan-bulletin-10505', 'dgbas-yearbook-113', 'moe-16years-T403'],
    'local': ['taoyuan-yearbook-ch8-2021', 'tpml-2012-12', 'changhua-bulletin-2021-ctrl', 'kaohsiung-cultural-2012'],
    'ncl_early': [f'ncl-ed{n}-public-libraries' for n in (91, 92, 93, 94)],
}


def stable(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(body):
    return hashlib.sha256(body).hexdigest()


def text_value(value):
    return stable(value) if isinstance(value, (dict, list)) else value


def source_id(cell):
    table = re.sub(r'[^A-Za-z0-9-]+', '-', str(cell['source_table'])).strip('-')
    if not table:
        table = sha(str(cell['source_table']).encode())[:12]
    return 'discovered-' + cell['source_document_id'] + '-t' + table


def family(document_id):
    if document_id.startswith('ncl-'):
        return '國家圖書館年鑑統計事實'
    if document_id.startswith('dgbas-'):
        return '主計總處後續全國出版統計'
    if document_id.startswith('moe-'):
        return '教育部歷史公共館統計'
    return '地方官方出版統計事實'


def adapt(cell, document):
    """Pure mapping; unknown periods and source markers remain unknown."""
    value = cell['value']
    if value is not None:
        number = decimal.Decimal(str(value))
        if not number.is_finite():
            raise ValueError('Non-finite original value')
        value = int(number) if number == number.to_integral_value() else float(number)
        if decimal.Decimal(str(value)) != number:
            raise ValueError('Literal decimal cannot be represented without loss: ' + cell['cell_id'])
        if value == 0 and not re.fullmatch(r'\s*[+-]?0+(?:\.0+)?\s*', cell['value_raw'].replace(',', '')):
            raise ValueError('Zero requires an original numeric zero, not a symbol: ' + cell['cell_id'])
    status = cell['value_status']
    if (value is None) != (status != 'reported'):
        raise ValueError('Value/status disagreement: ' + cell['cell_id'])
    year, month = cell['data_year'], cell.get('data_month')
    if year is not None and (type(year) is not int or not 1000 <= year <= 9999):
        raise ValueError('Invalid literal source year')
    if month is not None and (year is None or type(month) is not int or not 1 <= month <= 12):
        raise ValueError('Invalid literal source month')
    sid = source_id(cell)
    notes = cell.get('source_notes', [])
    period_status = cell['period_status']
    basis = 'literal_original_year_month' if month else 'source_reference_year_exact_date_unconfirmed' if year else 'original_period_unresolved'
    temporal = cell['temporal_kind']
    if month and ('annual' in temporal or temporal in ('flow_calendar_year','flow_source_year','stock_year_end')):
        raise ValueError('Annual or cumulative quantity cannot be relabelled as a month: ' + cell['cell_id'])
    if 'multi_year' in temporal:
        basis = 'multi_year_change_unresolved_as_single_year'
    # No invented calendar dates for yearly references or monthly stock cells.
    # The source's literal period is sufficient to support a bounded panel.
    period_effective = f'{year:04d}-{month:02d}' if month else str(year) if year else None
    if 'week' in temporal:
        basis = 'weekly_quantity_exact_week_unresolved_not_annual_total'
        period_effective = None
    if temporal == 'stock_year_end' and year is not None:
        basis = 'source_year_end_explicit_in_chapter'
    context_keys = ('source_table_year_context', 'data_month', 'period_status',
                    'collection_segment', 'source_table_column_block', 'source_period_pdf_page',
                    'source_display_status', 'source_stored_value_raw', 'source_display_region',
                    'source_merged_cell', 'source_original_required_to_reproduce')
    context = {k: cell[k] for k in context_keys if k in cell}
    # Preserve source-specific formulae, denominators, merged-region metadata,
    # OCR review receipts and other literal qualifiers in the existing schema.
    core = {'aggregation_role','cell_id','column_label_raw','data_year','entity_kind','entity_raw',
            'geography_vintage','independent_check','license_status','metric_id','metric_raw',
            'national_libraries_scope','period_raw','period_status','population_scope','quality_flags',
            'row_label_raw','source_catalogue_url','source_cell_bbox','source_column','source_document_id',
            'source_edition','source_edition_roc','source_locator','source_notes','source_pdf_page',
            'source_printed_page','source_retrieved_at','source_row','source_sha256','source_table',
            'source_table_title','source_url','source_version_id','temporal_kind','unit','unit_raw',
            'unit_status','value','value_raw','value_status'}
    context.update({k: v for k, v in cell.items() if k not in core})
    check = cell.get('independent_check', {})
    row = {
        'collection_year': None, 'publication_year': None, 'definition_source_id': sid,
        'definition_sha256': cell['source_sha256'], 'definition_retrieved_at': document['retrieved_at'],
        'source_method': 'GET', 'source_request': None,
        'comparability': 'same_original_table_only_subject_to_field_period_and_population_review',
        'observation_id': 'obs-' + sha((cell['source_sha256'] + '|' + cell['cell_id']).encode())[:22],
        'data_year': year, 'geography': cell['entity_raw'], 'geography_contextual_name': cell['entity_raw'],
        'geographic_scope': cell['entity_kind'], 'geography_vintage': cell['geography_vintage'],
        'national_libraries_scope': cell['national_libraries_scope'], 'population_scope': cell['population_scope'],
        'series_id': sid + '-' + cell['metric_id'] + '-' + sha(stable([cell['entity_raw'],cell['entity_kind'],temporal,cell['unit'],cell['aggregation_role']]).encode())[:12], 'indicator': cell['metric_raw'],
        'indicator_group': cell['metric_raw'], 'source_field': cell['column_label_raw'],
        'value': value, 'raw_value': cell['value_raw'], 'value_status': status,
        'zero_interpretation': 'literal_original_reported_zero_not_inferred' if value == 0 else None,
        'unit': cell['unit'], 'unit_raw': cell['unit_raw'], 'unit_status': cell['unit_status'],
        'unit_basis': 'original_heading_and_reviewed_table_notes', 'temporal_kind': temporal,
        'period_start': None, 'period_end': f'{year}-12-31' if year and temporal == 'stock_year_end' else None,
        'period_raw': cell['period_raw'], 'period_effective': period_effective,
        'periodicity_raw': '每週' if 'week' in temporal else '月' if month else '年' if year else None,
        'period_basis': basis, 'source_period_interpretation_status': period_status,
        'source_time_reference': stable(context), 'definition_id': 'def-' + sid + '-' + cell['metric_id'],
        'definition_status': 'original_table_heading_notes_and_complete_cells_reviewed',
        'source_id': sid, 'source_family': family(cell['source_document_id']),
        'source_url': cell['source_url'], 'source_page_url': document.get('catalogue_url') or document['official_url'],
        'source_locator': cell['source_locator'], 'source_sha256': cell['source_sha256'],
        'source_version_id': cell['source_version_id'], 'source_snapshot_path': document['source_local_path'],
        'retrieved_at': document['retrieved_at'],
        'license_status': 'published_statistical_facts_document_license_unconfirmed',
        'license_url': None, 'snapshot_distribution': 'not_in_public_bundle',
        'extraction_status': 'reviewed_original_cell; ' + str(check.get('method') or 'see_extraction_metadata'),
        'quality_flags': stable(cell.get('quality_flags', [])), 'notes': '；'.join(notes),
        'source_pdf_page': cell.get('source_pdf_page'), 'source_printed_page': cell.get('source_printed_page'),
        'source_table': str(cell['source_table']), 'source_table_title': cell['source_table_title'],
        'source_row': str(cell['source_row']), 'source_column': str(cell['source_column']),
        'source_column_path': cell['column_label_raw'],
        'source_cell_bbox': text_value(cell.get('source_cell_bbox')),
        'source_location_kind': 'verified_original_cell', 'source_row_label_raw': cell['row_label_raw'],
        'aggregation_role': cell['aggregation_role'], 'original_source_note': '；'.join(notes),
        'source_cell_note_raw': stable(check), 'source_cell_note_status': 'verification_method_preserved_not_confidence_score',
        'source_edition': cell.get('source_edition') or document.get('edition_raw'),
        'source_edition_roc': cell.get('source_edition_roc'),
        'component_source_id': cell['source_document_id'], 'source_record_id': cell['cell_id'],
        'value_parse_rule': 'literal_decimal_cell_only; source_markers_composites_and_blanks_preserved',
    }
    return row


def run(root=ROOT, force=False, skip_extract=False):
    documents = {d['candidate_id']: d for d in json.loads((root/'raw/discovered-20261028/documents.json').read_text())['documents']}
    expected_ids = {sid for ids in GROUPS.values() for sid in ids}
    if set(documents) != expected_ids:
        raise ValueError('Unreviewed or missing source document')
    for doc in documents.values():
        if sha((root/doc['source_local_path']).read_bytes()) != doc['source_sha256']:
            raise ValueError('Original changed; review new version before replacing accepted source: ' + doc['candidate_id'])
    state_path = root/'data/discovered_20261028_extractor_cache.json'
    old = json.loads(state_path.read_text()) if state_path.exists() else {}
    states, cells = {}, []
    for group, ids in GROUPS.items():
        script = root/'scripts'/f'extract_discovered_{group}_20261028.py'
        outputs = [f'derived/discovered_{group}_20261028_cells.jsonl', f'derived/discovered_{group}_20261028_metadata.json']
        inputs = {sid: documents[sid]['source_sha256'] for sid in ids}
        inputs['extractor_sha256'] = sha(script.read_bytes())
        inputs['documents_sha256'] = sha(stable([documents[s] for s in ids]).encode())
        if group == 'central':
            inputs['probe_extractor_sha256'] = sha((root/'scripts/probe_library_source_tables.py').read_bytes())
        output_hashes = {name: sha((root/name).read_bytes()) if (root/name).is_file() else None for name in outputs}
        unchanged = old.get(group) == {'inputs': inputs, 'outputs': output_hashes} and all(output_hashes.values())
        if skip_extract and not unchanged:
            raise ValueError('Cannot skip changed or uncached original extraction: ' + group)
        if not skip_extract and (force or not unchanged):
            subprocess.run([sys.executable, str(script), '--root', str(root), '--source-root', str(root/'raw/discovered-20261028')], cwd=root, check=True, stdout=subprocess.DEVNULL)
        batch = [json.loads(line) for line in (root/outputs[0]).read_text().splitlines()]
        if {r['source_document_id'] for r in batch} != set(ids):
            raise ValueError('Extractor did not produce every reviewed document: ' + group)
        for cell in batch:
            if cell['source_sha256'] != documents[cell['source_document_id']]['source_sha256']:
                raise ValueError('Cell lineage differs from pinned original')
            if not cell['source_locator'] or not cell['source_url'].startswith('https://'):
                raise ValueError('Missing original-cell locator')
            check = cell.get('independent_check', {})
            if not (check.get('matched') or check.get('numeric_and_status_agree') or check.get('original_image_reviewed')):
                raise ValueError('Unverified original cell: ' + cell['cell_id'])
        cells.extend(batch)
        states[group] = {'inputs': inputs, 'outputs': {n: sha((root/n).read_bytes()) for n in outputs}}
    if len({c['cell_id'] for c in cells}) != len(cells):
        raise ValueError('Duplicated original physical cell')
    rows = [adapt(c, documents[c['source_document_id']]) for c in cells]
    columns = json.loads((root/'scripts/discovered_20261028_canonical_columns.json').read_text())['columns']
    if any(set(r)-set(columns) for r in rows):
        raise ValueError('New canonical fields require an explicit schema review')
    rows = [{k:r.get(k) for k in columns} for r in rows]
    if len({r['observation_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicated canonical observation identity')
    body = ''.join(stable(r)+'\n' for r in rows)
    with record_io.write_text(root,'derived/discovered_20261028_observations.jsonl') as stream:
        stream.write(body)
    trace = []
    for c, r in zip(cells, rows, strict=True):
        d = documents[c['source_document_id']]
        trace.append({**{k: text_value(v) for k, v in c.items()}, 'source_id': r['source_id'],
                      'source_download_url': d['official_url'], 'source_url': r['source_page_url'],
                      'source_local_path': d['source_local_path'], 'source_retrieved_at': d['retrieved_at'],
                      'source_title': d['title'], 'source_edition_roc': c.get('source_edition_roc'),
                      'publication_date': '', 'observation_id': r['observation_id']})
    names = list(dict.fromkeys(k for r in trace for k in r))
    with (root/'derived/discovered_20261028_long.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=names); writer.writeheader(); writer.writerows(trace)
    report = {'schema_version': '1.0.0', 'source_documents': len(documents), 'source_cells': len(rows),
              'canonical_observations_added': len(rows), 'source_counts': dict(collections.Counter(c['source_document_id'] for c in cells)),
              'table_counts': dict(collections.Counter(r['source_id'] for r in rows)),
              'value_statuses': dict(collections.Counter(r['value_status'] for r in rows)),
              'unresolved_period_records': sum(r['data_year'] is None for r in rows),
              'monthly_records': sum(bool(c.get('data_month')) for c in cells),
              'canonical_batch_sha256': sha(body.encode()), 'no_imputation': True,
              'full_originals_distributed': False, 'cross_source_panel_permission': False,
              'complete_scope': 'All physical cells of the selected tables and continuations listed in the three extractor inventories; not all tables of each publication.'}
    (root/'raw/discovered-20261028/extraction-metadata.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    state_path.write_text(json.dumps(states, ensure_ascii=False, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--skip-extract', action='store_true', help='Validate already extracted complete batches; no partial sources accepted.')
    args = parser.parse_args()
    print(json.dumps(run(args.root.resolve(), args.force, args.skip_extract), ensure_ascii=False))
