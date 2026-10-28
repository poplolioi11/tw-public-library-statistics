#!/usr/bin/env python3
"""Validate the bounded source-discovery register without claiming formal coverage.

Default checks are offline and use only the public JSON evidence. With
--source-root, additionally verify all acquired originals and reproduce the PDF
probes using their pinned versions; no originals are downloaded automatically.
"""
import argparse
import collections
import decimal
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTER = 'docs/source-discovery-20261028.json'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def numeric(raw):
    clean = re.sub(r'[\s,]', '', raw)
    if clean in ('--', '…', '-'):
        return None
    need(bool(re.fullmatch(r'\d+(?:\.\d+)?', clean)), 'unreviewed numeric token')
    return decimal.Decimal(clean)


def validate(root, source_root=None):
    register = read(root / REGISTER)
    need(register['role'] == 'official_source_discovery_not_formal_coverage', 'wrong register role')
    need(register['formal_observations_added'] == 0, 'research must not claim formal additions')
    need(register['source_probes_are_formal_observations'] is False, 'probe/formal boundary missing')
    for key in ('all_history_complete', 'cross_source_panel_permission', 'full_originals_distributed'):
        need(register[key] is False, 'unsafe scope claim: ' + key)
    need(register['dataset_version'] == (root / 'VERSION').read_text().strip(), 'dataset version differs')
    candidates = register['candidates']
    backlog = read(root / 'docs/source-backlog.json')
    ncl = next(x for x in backlog['families'] if x['family_id'] == 'ncl_yearbook_public_library_chapters')
    need(all(isinstance(x, dict) for x in ncl.get('known_not_ingested', [])), 'NCL backlog item must be an object for documentation rebuild')
    by_id = {x['candidate_id']: x for x in candidates}
    need(len(by_id) == len(candidates) == register['candidate_count'] == 16, 'candidate originals differ')
    for source in candidates:
        need(bool(re.fullmatch(r'[a-f0-9]{64}', source['source_sha256'])), 'source SHA missing')
        need(source['source_bytes'] > 0 and source['official_url'].startswith('https://'), 'source not pinned')
        need(source['source_version_id'] == source['candidate_id'] + '@sha256:' + source['source_sha256'], 'version differs')
        need(source['canonical_observations_added'] == 0 and source['cross_source_panel_permission'] is False, 'candidate presented as panel')
        need(source['full_original_redistributed'] is False and source['rights_status'], 'rights boundary missing')
        years = source['data_years_verified_for_listed_tables_only']
        need(all(type(y) is int and 1850 <= y <= 2100 for y in years), 'invalid verified year')
        need(not years or source['locators'], 'verified year without table locator')
    held = by_id['tpml-annual-2012']
    need(held['ingestion_status'].endswith('rights_hold'), 'conflicting Taipei rights must remain held')
    need(not held.get('bounded_probe_path'), 'held source must not publish a quantitative probe')
    for unresolved in register['not_acquired_or_unresolved']:
        need(unresolved['source_sha256'] is None, 'unacquired original must not invent a SHA')
        need(not unresolved['data_years_verified_for_listed_tables_only'], 'unverified table year must remain unknown')

    info = register['bounded_probe']
    path = root / info['path']
    need(hashlib.sha256(path.read_bytes()).hexdigest() == info['sha256'], 'probe file differs')
    probe = read(path)
    need(probe['canonical_data_modified'] is False and probe['cross_source_aggregation_permitted'] is False, 'probe scope differs')
    need(probe['role'] == 'source_discovery_bounded_cell_evidence_not_formal_observations', 'wrong probe role')
    rows = probe['records']
    need(len(rows) == 396 and len({x['probe_record_id'] for x in rows}) == len(rows), 'incomplete or duplicate cell IDs')
    need(collections.Counter(x['source_id'] for x in rows) == {'tainan-bulletin-10505': 240, 'ntpc-cultural-2015': 156}, 'source cell totals differ')
    need(collections.Counter((x['source_id'], x['source_locator']['table']) for x in rows) == {('tainan-bulletin-10505', '1'): 192, ('tainan-bulletin-10505', '2'): 48, ('ntpc-cultural-2015', '6-2'): 156}, 'whole-table boundaries differ')
    for row in rows:
        source = by_id[row['source_id']]
        need(row['source_sha256'] == source['source_sha256'] and row['source_version_id'] == source['source_version_id'], 'cell source version differs')
        split = urlsplit(row['source_url'])
        need(urlunsplit(split._replace(fragment='')) == source['official_url'], 'cell official URL differs')
        need(split.fragment == 'page=' + str(row['source_locator']['pdf_page']), 'page link differs')
        need(row['source_locator']['row_label_raw'] and row['source_locator']['column_label_raw'], 'cell locator absent')
        a, b = numeric(row['raw_value_pdfminer']), numeric(row['raw_value_pdfium'])
        need(a == b, 'PDF engines disagree')
        if a is None:
            need(row['value'] is None and row['value_status'] == 'source_marker_uninterpreted', 'source marker was guessed')
        else:
            need(isinstance(row['value'], str) and decimal.Decimal(row['value']) == a and row['value_status'] == 'reported', 'numeric value differs')
        need(row['comparison_permission'] == 'none_probe_not_canonical_or_panel', 'probe granted comparison permission')
        if row['source_id'] == 'ntpc-cultural-2015':
            if row['source_row_label_raw'].endswith('區'):
                need(row['data_year'] is None and row['source_table_year_context'] == 2015, 'district year guessed')
            if row['source_locator']['column_label_raw'] == '辦證人數':
                need(row['unit'] is None, 'unresolved card unit guessed')
        if row['source_row_label_raw'] == '100-104變動情形':
            need(row['data_year'] is None and row['temporal_interpretation'] == 'multi_year_change', 'multi-year change was annualized')
    need(sum(x['value'] is None for x in rows) == info['source_marker_cells'] == 12, 'missing marker count differs')
    need(probe['validation']['independent_pdf_engine_numeric_checks'] == info['independent_pdf_engine_numeric_checks'] == 396, 'source checks incomplete')
    need(register['existing_layer_fingerprints'] == read(root/'docs/phase2-summary.json')['layer_raw_fingerprints'], 'existing quantitative layer fingerprints differ')

    originals = 0
    if source_root is not None:
        for sid, source in by_id.items():
            ext = '.xls' if sid == 'moe-16years-T403' else '.pdf'
            body = (source_root / (sid + ext)).read_bytes()
            need(hashlib.sha256(body).hexdigest() == source['source_sha256'] and len(body) == source['source_bytes'], 'original differs: ' + sid)
            originals += 1
        from probe_library_source_tables import extract
        with tempfile.TemporaryDirectory(prefix='library-source-probe-') as tmp:
            extract(Path(tmp), source_root)
            need((Path(tmp)/info['path']).read_bytes() == path.read_bytes(), 'reproduced source probes differ')
    return {'official_original_candidates': len(candidates), 'pdf_source_cells_checked': len(rows),
            'source_marker_cells': 12, 'raw_originals_verified': originals,
            'formal_observations_added': 0, 'all_history_complete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.root.resolve(), args.source_root.resolve() if args.source_root else None), ensure_ascii=False))


if __name__ == '__main__':
    main()
