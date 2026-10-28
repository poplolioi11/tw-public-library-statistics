#!/usr/bin/env python3
"""Validate the bounded source-discovery register without claiming formal coverage.

Default checks are offline and use only the public JSON evidence. With
--source-root, additionally verify all acquired originals and reproduce the PDF
probes using their pinned versions; no originals are downloaded automatically.
"""
import argparse
import collections
import decimal
import gzip
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import record_io

ROOT = Path(__file__).resolve().parents[1]
REGISTER = 'docs/source-discovery-20261028.json'
HISTORICAL_REGISTER_SHA256 = '657c163f509e3187e2e056492cb40d5fa92894226d8acacf8fbce3cee5710d3b'
HISTORICAL_VERSION = '0.8.0'
HISTORICAL_LAYER_FINGERPRINTS = {
    'canonical': 'd92bb668b333d8ae24ac48362558cf011c8d7f275f1d5f60aec2c7713f702e9e',
    'local_statistical_cells': '2f3b30127fbf12aa743de1e2844a02681e7a967a8cb1efe7cbdc4a7c83e4335f',
    'programme_quantities': '503f2e60d56f34ddbcc7c392cb638e8e535676a7d90097331cf2470931cac662',
}
FORMAL_METADATA = 'raw/discovered-20261028/extraction-metadata.json'
FORMAL_ROWS = 'derived/discovered_20261028_observations.jsonl'
FORMAL_DOCUMENTS = {
    'ntpc-cultural-2015', 'tainan-bulletin-10505', 'dgbas-yearbook-113', 'moe-16years-T403',
    'taoyuan-yearbook-ch8-2021', 'tpml-2012-12', 'changhua-bulletin-2021-ctrl',
    'kaohsiung-cultural-2012', *(f'ncl-ed{year}-public-libraries' for year in (91, 92, 93, 94)),
}
PUBLICATION_FIELDS = {'snapshot_distribution', 'public_evidence_path', 'public_evidence_sha256', 'public_projection_policy'}
LAYER_NONSTATISTICAL_FIELDS = PUBLICATION_FIELDS | {'original_fields'}
OTHER_LAYERS = {'local_statistical_cells': 'derived/phase1_local_sources_long.jsonl',
                'programme_quantities': 'derived/ncl_2005_programmes_long.jsonl'}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def version_tuple(value):
    need(isinstance(value, str) and re.fullmatch(r'\d+\.\d+\.\d+', value), 'unreviewed dataset version')
    return tuple(map(int, value.split('.')))


class LayerFingerprint:
    """The unchanged P2 statistical fingerprint, including source order and nulls."""
    def __init__(self):
        self.digest = hashlib.sha256(b'[')
        self.first = True

    def add(self, row):
        if not self.first:
            self.digest.update(b',')
        self.digest.update(stable({k: v for k, v in row.items() if k not in LAYER_NONSTATISTICAL_FIELDS}).encode())
        self.first = False

    def finish(self):
        result = self.digest.copy()
        result.update(b']')
        return result.hexdigest()


def quantitative_layers(root):
    """Read canonical via its transport profile; never open original-document paths."""
    current, baseline = LayerFingerprint(), LayerFingerprint()
    discovered, identifiers = {}, set()
    for row in record_io.rows(root):
        identifier = row.get('observation_id')
        need(isinstance(identifier, str) and identifier and identifier not in identifiers, 'duplicate or missing canonical observation ID')
        identifiers.add(identifier)
        current.add(row)
        if str(row.get('source_id') or '').startswith('discovered-'):
            discovered[identifier] = row
        else:
            baseline.add(row)
    current_layers = {'canonical': current.finish()}
    baseline_layers = {'canonical': baseline.finish()}
    for layer, relative in OTHER_LAYERS.items():
        path = root / relative
        if not path.is_file():
            path = path.with_suffix(path.suffix + '.gz')
        fingerprint = LayerFingerprint()
        with (gzip.open(path, 'rt', encoding='utf-8-sig') if path.suffix == '.gz' else path.open(encoding='utf-8-sig')) as stream:
            for line in stream:
                if line.strip():
                    fingerprint.add(json.loads(line))
        current_layers[layer] = baseline_layers[layer] = fingerprint.finish()
    return current_layers, baseline_layers, discovered


def validate_formal_ingestion(root, candidates, canonical):
    """Bind a later complete-table batch to its pinned originals and canonical rows.

    This checks registered SHA/URL lineage and supplied extraction facts. It does
    not read PDFs, follow source_snapshot_path, or certify omitted originals anew.
    """
    metadata = read(root / FORMAL_METADATA)
    body = record_io.body(root, FORMAL_ROWS)
    need(metadata.get('schema_version') == '1.0.0', 'formal extraction metadata version differs')
    need(hashlib.sha256(body).hexdigest() == metadata.get('canonical_batch_sha256'), 'formal canonical batch SHA differs')
    need(metadata.get('no_imputation') is True and metadata.get('full_originals_distributed') is False
         and metadata.get('cross_source_panel_permission') is False, 'formal extraction policy differs')
    rows = [json.loads(line) for line in body.decode('utf-8-sig').splitlines() if line.strip()]
    by_id, source_counts, table_counts, statuses = {}, collections.Counter(), collections.Counter(), collections.Counter()
    months = 0
    for row in rows:
        need(isinstance(row, dict), 'formal row is not an object')
        identifier = row.get('observation_id')
        need(isinstance(identifier, str) and identifier and identifier not in by_id, 'duplicate or missing formal observation ID')
        by_id[identifier] = row
        document_id = row.get('component_source_id')
        need(document_id in FORMAL_DOCUMENTS and document_id in candidates, 'unreviewed or rights-held formal source')
        original = candidates[document_id]
        need(row.get('source_sha256') == original['source_sha256']
             and row.get('source_version_id') == original['source_version_id'], 'formal original source version differs')
        need(isinstance(row.get('source_url'), str), 'formal source URL absent')
        need(urlunsplit(urlsplit(row['source_url'])._replace(fragment='')) == original['official_url'], 'formal original source URL differs')
        cell_id = row.get('source_record_id')
        need(isinstance(cell_id, str) and cell_id, 'formal original cell ID absent')
        need(identifier == 'obs-' + hashlib.sha256((original['source_sha256'] + '|' + cell_id).encode()).hexdigest()[:22], 'formal observation/source-cell identity differs')
        table = row.get('source_table')
        need(isinstance(table, str) and table, 'formal original table absent')
        table_id = re.sub(r'[^A-Za-z0-9-]+', '-', table).strip('-') or hashlib.sha256(table.encode()).hexdigest()[:12]
        need(row.get('source_id') == 'discovered-' + document_id + '-t' + table_id, 'formal source/table identity differs')
        need(isinstance(row.get('source_locator'), str) and row['source_locator'].strip(), 'formal original-cell locator absent')
        need('value' in row and 'raw_value' in row and 'value_status' in row, 'formal original value or status absent')
        need('data_year' in row and (row['data_year'] is None or type(row['data_year']) is int), 'formal original year coerced')
        need((row['value'] is not None) == (row['value_status'] == 'reported'), 'formal value/status disagreement')
        need(isinstance(row.get('source_time_reference'), str), 'formal original context absent')
        context = json.loads(row['source_time_reference'])
        need(isinstance(context, dict), 'formal original context is not an object')
        months += bool(context.get('data_month'))
        source_counts[document_id] += 1
        table_counts[row['source_id']] += 1
        statuses[row['value_status']] += 1
        need(identifier in canonical, 'formal observation missing from canonical')
        expected = {k: v for k, v in row.items() if k not in PUBLICATION_FIELDS}
        actual = {k: v for k, v in canonical[identifier].items() if k not in PUBLICATION_FIELDS}
        need(stable(actual) == stable(expected), 'formal/canonical statistical or provenance fields differ: ' + identifier)
    need(set(source_counts) == FORMAL_DOCUMENTS and metadata.get('source_documents') == len(FORMAL_DOCUMENTS) == 12, 'formal document coverage differs')
    need(set(by_id) == set(canonical), 'canonical discovered rows differ from the reviewed complete batch')
    need(type(metadata.get('source_cells')) is int and metadata['source_cells'] == metadata.get('canonical_observations_added') == len(rows), 'formal batch observation count differs')
    need(metadata.get('source_counts') == dict(source_counts) and metadata.get('table_counts') == dict(table_counts), 'formal source/table counts differ')
    need(metadata.get('value_statuses') == dict(statuses), 'formal original value-state counts differ')
    need(metadata.get('unresolved_period_records') == sum(row['data_year'] is None for row in rows), 'formal unresolved-period count differs')
    need(metadata.get('monthly_records') == months, 'formal monthly count differs')
    return {'metadata_path': FORMAL_METADATA, 'canonical_batch_path': FORMAL_ROWS,
            'canonical_batch_sha256': metadata['canonical_batch_sha256'],
            'source_documents': len(source_counts), 'canonical_observations_checked': len(rows),
            'unresolved_period_records': metadata['unresolved_period_records'],
            'publication_only_field_differences_allowed': sorted(PUBLICATION_FIELDS),
            'original_documents_reread': False,
            'verification_scope': 'Pinned historical original SHA/URL/version, extraction metadata, and exact derived-to-canonical statistical/provenance fields; no fresh PDF or omitted-original verification.'}


def numeric(raw):
    clean = re.sub(r'[\s,]', '', raw)
    if clean in ('--', '…', '-'):
        return None
    need(bool(re.fullmatch(r'\d+(?:\.\d+)?', clean)), 'unreviewed numeric token')
    return decimal.Decimal(clean)


def validate(root, source_root=None):
    need(hashlib.sha256((root / REGISTER).read_bytes()).hexdigest() == HISTORICAL_REGISTER_SHA256, 'historical discovery register SHA differs; retain the original snapshot')
    register = read(root / REGISTER)
    need(register['role'] == 'official_source_discovery_not_formal_coverage', 'wrong register role')
    need(register['formal_observations_added'] == 0, 'research must not claim formal additions')
    need(register['source_probes_are_formal_observations'] is False, 'probe/formal boundary missing')
    for key in ('all_history_complete', 'cross_source_panel_permission', 'full_originals_distributed'):
        need(register[key] is False, 'unsafe scope claim: ' + key)
    current_version = (root / 'VERSION').read_text().strip()
    need(register['dataset_version'] == HISTORICAL_VERSION, 'historical discovery version changed')
    need(register['existing_layer_fingerprints'] == HISTORICAL_LAYER_FINGERPRINTS, 'historical quantitative layer fingerprints changed')
    need(version_tuple(current_version) >= version_tuple(register['dataset_version']), 'dataset predates the discovery baseline')
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
    phase2 = read(root / 'docs/phase2-summary.json')
    need(phase2.get('dataset_version') == current_version, 'current phase2 version differs')
    current_layers, baseline_layers, canonical_discovered = quantitative_layers(root)
    later_ingestion = None
    if current_version == register['dataset_version']:
        need(register['existing_layer_fingerprints'] == phase2['layer_raw_fingerprints'] == current_layers, 'existing quantitative layer fingerprints differ')
        need(not canonical_discovered, 'same-version discovery must not add formal observations')
    else:
        need(baseline_layers == register['existing_layer_fingerprints'], 'historical quantitative baseline differs after excluding the formal discovered batch')
        need(current_layers == phase2['layer_raw_fingerprints'], 'current quantitative layer fingerprints differ')
        later_ingestion = validate_formal_ingestion(root, by_id, canonical_discovered)

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
            'formal_observations_added': 0, 'all_history_complete': False,
            'historical_discovery_snapshot': {'dataset_version': register['dataset_version'],
                'register_sha256': HISTORICAL_REGISTER_SHA256,
                'existing_layer_fingerprints': register['existing_layer_fingerprints'],
                'formal_observations_added': 0, 'rights_held_candidate': held['candidate_id']},
            'current_dataset_version': current_version,
            'later_formal_ingestion': later_ingestion}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.root.resolve(), args.source_root.resolve() if args.source_root else None), ensure_ascii=False))


if __name__ == '__main__':
    main()
