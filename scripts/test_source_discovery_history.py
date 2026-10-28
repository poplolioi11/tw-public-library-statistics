#!/usr/bin/env python3
"""Small offline fixtures for immutable discovery history and later ingestion.

Original documents are never opened. Only the existing public discovery JSON
and probe JSON seed these temporary fixtures; all quantitative layers are tiny.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit

import record_io
import validate_source_discovery as validator

ROOT = Path(__file__).resolve().parents[1]


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def fingerprint(rows):
    excluded = {'snapshot_distribution', 'public_evidence_path', 'public_evidence_sha256', 'public_projection_policy', 'original_fields'}
    return hashlib.sha256(stable([{k: v for k, v in row.items() if k not in excluded} for row in rows]).encode()).hexdigest()


def jsonl(rows):
    return ''.join(stable(row) + '\n' for row in rows).encode()


class DiscoveryHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.historical_bytes = (ROOT / validator.REGISTER).read_bytes()
        cls.historical = json.loads(cls.historical_bytes)
        cls.probe_bytes = (ROOT / cls.historical['bounded_probe']['path']).read_bytes()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='library-discovery-history-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.old_rows = [
            {'observation_id': 'old-a', 'source_id': 'historical-fixture-a', 'data_year': 2020,
             'value': 0, 'raw_value': '0', 'value_status': 'reported', 'period_raw': '109年'},
            {'observation_id': 'old-b', 'source_id': 'historical-fixture-b', 'data_year': 2021,
             'value': 2, 'raw_value': '2', 'value_status': 'reported', 'period_raw': '110年'},
        ]
        self.local_rows = [{'source_record_id': 'local-fixture', 'value': 3, 'raw_value': '3'}]
        self.programme_rows = [{'source_record_id': 'programme-fixture', 'value': 4, 'raw_value': '4'}]
        self.baseline = {'canonical': fingerprint(self.old_rows),
                         'local_statistical_cells': fingerprint(self.local_rows),
                         'programme_quantities': fingerprint(self.programme_rows)}
        self.register = copy.deepcopy(self.historical)
        self.register['existing_layer_fingerprints'] = self.baseline
        self.write(validator.REGISTER, self.register)
        self.register_sha = hashlib.sha256((self.root / validator.REGISTER).read_bytes()).hexdigest()
        self.write_bytes(self.register['bounded_probe']['path'], self.probe_bytes)
        self.write('docs/source-backlog.json', {'families': [{'family_id': 'ncl_yearbook_public_library_chapters', 'known_not_ingested': [{'reason': 'fixture'}]}]})
        self.write_bytes('derived/phase1_local_sources_long.jsonl', jsonl(self.local_rows))
        self.write_bytes('derived/ncl_2005_programmes_long.jsonl', jsonl(self.programme_rows))
        self.canonical = copy.deepcopy(self.old_rows)
        self.formal = []
        self.write_bytes('VERSION', b'0.8.0\n')
        self.write_canonical()

    def write_bytes(self, name, body):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)

    def write(self, name, value):
        self.write_bytes(name, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())

    def write_canonical(self):
        record_io.write(self.root, 'data/combined/observations.jsonl', self.canonical)
        self.write('docs/phase2-summary.json', {
            'dataset_version': (self.root / 'VERSION').read_text().strip(),
            'layer_raw_fingerprints': {'canonical': fingerprint(self.canonical),
                                       'local_statistical_cells': fingerprint(self.local_rows),
                                       'programme_quantities': fingerprint(self.programme_rows)},
        })

    def validate(self):
        # Constants are rebound solely to this explicitly synthetic baseline;
        # production keeps the literal immutable v0.8 SHA and fingerprints.
        with patch.object(validator, 'HISTORICAL_REGISTER_SHA256', self.register_sha), patch.object(validator, 'HISTORICAL_LAYER_FINGERPRINTS', self.baseline):
            return validator.validate(self.root)

    def make_later_version(self):
        candidates = {item['candidate_id']: item for item in self.register['candidates']}
        self.formal = []
        for index, document_id in enumerate(sorted(validator.FORMAL_DOCUMENTS)):
            original = candidates[document_id]
            cell_id = 'synthetic-fixture-cell-' + document_id
            self.formal.append({
                'observation_id': 'obs-' + hashlib.sha256((original['source_sha256'] + '|' + cell_id).encode()).hexdigest()[:22],
                'source_record_id': cell_id, 'component_source_id': document_id,
                'source_id': 'discovered-' + document_id + '-tfixture-table', 'source_table': 'fixture-table',
                'source_sha256': original['source_sha256'], 'source_version_id': original['source_version_id'],
                'source_url': urlunsplit(urlsplit(original['official_url'])._replace(fragment='page=1')),
                'source_locator': 'synthetic fixture table / original row / original column',
                'source_time_reference': stable({'data_month': 1 if index == 0 else None,
                                                'source_table_year_context': 2024}),
                'data_year': None if index == 1 else 2024,
                'value': None if index == 1 else index, 'raw_value': '—' if index == 1 else str(index),
                'value_status': 'source_marker' if index == 1 else 'reported',
                'period_raw': '原列未標年' if index == 1 else '113年',
                'source_period_interpretation_status': 'unresolved' if index == 1 else 'explicit_original_year',
                'unit': '冊', 'unit_raw': '冊',
                'source_snapshot_path': '/originals-must-not-be-opened/' + document_id + '.pdf',
                'snapshot_distribution': 'not_in_public_bundle',
            })
        self.write_bytes('VERSION', b'0.9.0\n')
        self.canonical = copy.deepcopy(self.old_rows + self.formal)
        self.write_formal()
        self.write_canonical()

    def write_formal(self):
        body = jsonl(self.formal)
        self.write_bytes(validator.FORMAL_ROWS, body)
        source_counts, table_counts, statuses = {}, {}, {}
        for row in self.formal:
            source_counts[row['component_source_id']] = source_counts.get(row['component_source_id'], 0) + 1
            table_counts[row['source_id']] = table_counts.get(row['source_id'], 0) + 1
            statuses[row['value_status']] = statuses.get(row['value_status'], 0) + 1
        self.write(validator.FORMAL_METADATA, {
            'schema_version': '1.0.0', 'source_documents': len(source_counts),
            'source_cells': len(self.formal), 'canonical_observations_added': len(self.formal),
            'source_counts': source_counts, 'table_counts': table_counts, 'value_statuses': statuses,
            'unresolved_period_records': sum(row['data_year'] is None for row in self.formal),
            'monthly_records': sum(bool(json.loads(row['source_time_reference']).get('data_month')) for row in self.formal),
            'canonical_batch_sha256': hashlib.sha256(body).hexdigest(), 'no_imputation': True,
            'full_originals_distributed': False, 'cross_source_panel_permission': False,
        })

    def test_production_snapshot_sha_and_baseline_constants_are_unchanged(self):
        self.assertEqual(hashlib.sha256(self.historical_bytes).hexdigest(), validator.HISTORICAL_REGISTER_SHA256)
        self.assertEqual(self.historical['dataset_version'], validator.HISTORICAL_VERSION)
        self.assertEqual(self.historical['existing_layer_fingerprints'], validator.HISTORICAL_LAYER_FINGERPRINTS)
        self.assertEqual(hashlib.sha256(self.probe_bytes).hexdigest(), self.historical['bounded_probe']['sha256'])

    def test_same_version_keeps_the_original_strict_baseline(self):
        report = self.validate()
        self.assertEqual(report['formal_observations_added'], 0)
        self.assertIsNone(report['later_formal_ingestion'])
        self.assertEqual(report['historical_discovery_snapshot']['existing_layer_fingerprints'], self.baseline)

    def test_same_version_does_not_accept_a_changed_phase2_fingerprint(self):
        path = self.root / 'docs/phase2-summary.json'
        summary = json.loads(path.read_text())
        summary['layer_raw_fingerprints']['canonical'] = 'a' * 64
        self.write('docs/phase2-summary.json', summary)
        with self.assertRaisesRegex(ValueError, 'existing quantitative layer fingerprints differ'):
            self.validate()

    def test_history_cannot_be_rewritten_to_the_current_version(self):
        self.make_later_version()
        register = copy.deepcopy(self.register)
        register['dataset_version'] = '0.9.0'
        self.write(validator.REGISTER, register)
        with self.assertRaisesRegex(ValueError, 'historical discovery register SHA differs'):
            self.validate()

    def test_later_plain_version_checks_new_ingestion_and_keeps_history(self):
        self.make_later_version()
        report = self.validate()
        self.assertEqual(report['current_dataset_version'], '0.9.0')
        self.assertEqual(report['historical_discovery_snapshot']['dataset_version'], '0.8.0')
        self.assertEqual(report['later_formal_ingestion']['source_documents'], 12)
        self.assertEqual(report['later_formal_ingestion']['canonical_observations_checked'], 12)
        self.assertFalse(report['later_formal_ingestion']['original_documents_reread'])
        self.assertEqual(report['raw_originals_verified'], 0)

    def test_public_gzip_accepts_only_existing_publication_field_differences(self):
        self.make_later_version()
        self.write('data/combined/publication-profile.json', {'schema_version': '1.0.0', 'jsonl_compression': 'gzip'})
        for row in self.canonical:
            row.update(snapshot_distribution='not_in_public_bundle', public_evidence_path='raw/public-projections/fixture.json',
                       public_evidence_sha256='b' * 64, public_projection_policy='fixture statistical projection')
        self.write_canonical()
        (self.root / 'data/combined/observations.jsonl').unlink()
        report = self.validate()
        self.assertEqual(report['later_formal_ingestion']['canonical_observations_checked'], 12)

    def test_new_null_field_cannot_be_hidden_as_a_publication_difference(self):
        self.make_later_version()
        self.canonical[-1]['unreviewed_null_field'] = None
        self.write_canonical()
        with self.assertRaisesRegex(ValueError, 'formal/canonical statistical or provenance fields differ'):
            self.validate()

    def test_current_summary_rehash_does_not_allow_changes_to_old_statistics(self):
        self.make_later_version()
        self.canonical[0]['value'] = 9
        self.write_canonical()
        with self.assertRaisesRegex(ValueError, 'historical quantitative baseline differs'):
            self.validate()

    def test_batch_bytes_must_match_the_new_metadata_sha(self):
        self.make_later_version()
        path = self.root / validator.FORMAL_ROWS
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'formal canonical batch SHA differs'):
            self.validate()

    def test_rehashed_derived_value_cannot_silently_change_the_canonical_value(self):
        self.make_later_version()
        self.formal[0]['value'] = 99
        self.write_formal()
        with self.assertRaisesRegex(ValueError, 'formal/canonical statistical or provenance fields differ'):
            self.validate()

    def test_changed_original_sha_is_rejected_even_when_batch_and_summary_are_rehashed(self):
        self.make_later_version()
        self.formal[0]['source_sha256'] = 'a' * 64
        self.canonical = copy.deepcopy(self.old_rows + self.formal)
        self.write_formal()
        self.write_canonical()
        with self.assertRaisesRegex(ValueError, 'formal original source version differs'):
            self.validate()

    def test_omitted_formal_row_is_rejected_after_current_fingerprint_refresh(self):
        self.make_later_version()
        self.canonical.pop()
        self.write_canonical()
        with self.assertRaisesRegex(ValueError, 'formal observation missing from canonical'):
            self.validate()

    def test_original_rights_hold_remains_in_force(self):
        self.make_later_version()
        self.formal[0]['component_source_id'] = 'tpml-annual-2012'
        self.canonical = copy.deepcopy(self.old_rows + self.formal)
        self.write_formal()
        self.write_canonical()
        with self.assertRaisesRegex(ValueError, 'unreviewed or rights-held formal source'):
            self.validate()


if __name__ == '__main__':
    unittest.main(verbosity=2)
