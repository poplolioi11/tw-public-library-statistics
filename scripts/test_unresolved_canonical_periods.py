#!/usr/bin/env python3
"""Isolated regressions for canonical null periods; no real dataset is rebuilt.

Run with Python's standard library. The reader's pure year predicate is also
executed when node is on PATH or LIBRARY_TEST_NODE names an installed runtime.
All generated observations, SQLite files and inventories live in temporary dirs.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build_phase1_inventory as phase1
import build_release as release
import publication_statistics as publication
import record_io
import validate_phase1_inventory as phase1_validator
import validate_publication as publication_validator


ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get('LIBRARY_TEST_NODE') or shutil.which('node')


def read_json(path):
    return json.loads(path.read_text())


class UnresolvedCanonicalPeriods(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='library-null-period-fixture-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for folder in ('data', 'site', 'scripts', 'raw', 'docs'):
            (self.root / folder).mkdir()
        (self.root / 'VERSION').write_text('0.0.0\n')
        (self.root / 'data/indicators.json').write_text('[]\n')
        shutil.copyfile(ROOT / 'site/template.html', self.root / 'site/template.html')
        source = b'{"statistical_fixture": true}\n'
        (self.root / 'raw/source.json').write_bytes(source)
        base = {
            'source_id': 'fixture-source', 'source_family': 'fixture',
            'series_id': 'fixture-series', 'geography': '全國',
            'geographic_scope': 'national_total', 'indicator': '圖書館數',
            'indicator_group': '館數', 'source_field': '原欄圖書館數', 'unit': '館',
            'temporal_kind': 'annual', 'source_url': 'https://example.gov.tw/statistics',
            'source_sha256': hashlib.sha256(source).hexdigest(),
            'source_locator': 'fixture table / original row / original column',
            'source_snapshot_path': 'raw/source.json', 'license_status': 'source-specific',
            'period_effective': None, 'period_raw': None, 'period_basis': None,
            'period_status': None, 'source_period_interpretation_status': None,
            'source_subrow_label_raw': None, 'value_status': 'reported',
        }
        self.input_rows = [
            {**base, 'observation_id': 'known-2021', 'data_year': 2021,
             'value': 5, 'raw_value': '5', 'period_effective': '2021',
             'period_raw': '110年', 'period_basis': 'explicit_table_year'},
            {**base, 'observation_id': 'known-zero-2020', 'data_year': 2020,
             'value': 0, 'raw_value': '0', 'period_effective': '2020',
             'period_raw': '109年', 'period_basis': 'explicit_table_year'},
            {**base, 'observation_id': 'unknown-subrow', 'data_year': None,
             'value': 7, 'raw_value': '7', 'period_raw': '部分區列（原刊未明印年份）',
             'source_subrow_label_raw': '部分區', 'period_basis': 'unresolved_original_subrow',
             'period_status': 'unresolved', 'source_period_interpretation_status': 'unresolved'},
            {**base, 'observation_id': 'unknown-multiyear-change', 'data_year': None,
             'value': -2, 'raw_value': '-2', 'period_raw': '108年至110年增減',
             'period_effective': '108–110年變動', 'period_basis': 'multi_year_change',
             'period_status': 'multi_year_original_period', 'source_period_interpretation_status': 'unresolved'},
            {**base, 'observation_id': 'unknown-marker', 'data_year': None,
             'value': None, 'raw_value': '—', 'value_status': 'not_available_in_source',
             'period_raw': '原列未標年', 'period_basis': 'unresolved_original_subrow'},
        ]
        self.rebuild_fixture()

    def rebuild_fixture(self):
        known = [row for row in self.input_rows if row['data_year'] is not None]
        unresolved = [row for row in self.input_rows if row['data_year'] is None]
        for name, rows in [('data/observations.jsonl', known), ('data/component_records.jsonl', unresolved)]:
            (self.root / name).write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        with patch.object(release, 'ROOT', self.root), patch.object(release, 'VERSION', '0.0.0'), contextlib.redirect_stdout(io.StringIO()):
            release.main()
        self.rows = list(record_io.rows(self.root))
        self.summary = read_json(self.root / 'data/combined/summary.json')

    def prepare_fixture_partitions(self):
        return publication.write_period_partitions(self.root, self.rows, self.summary['canonical_jsonl_path'])

    def prepare_publication_fixture(self):
        fingerprint = publication_validator.statistical_fingerprint(self.rows)
        (self.root / 'docs/publication-integrity.json').write_text(json.dumps({
            'records': len(self.rows), 'missing_cells': self.summary['missing_cells'],
            'original_statistical_content_sha256': fingerprint,
            'public_statistical_content_sha256': fingerprint,
            'statistical_and_source_fields_unchanged': True,
        }))
        self.prepare_fixture_partitions()
        self.write_publication_manifest()

    def write_publication_manifest(self):
        files = {path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in self.root.rglob('*') if path.is_file() and path.name != publication_validator.MANIFEST_NAME}
        (self.root / publication_validator.MANIFEST_NAME).write_text(json.dumps({'files': files}))

    def validate_publication_fixture(self):
        return publication_validator.validate(self.root)

    def build_phase1_fixture(self):
        scope = {'scope_id': 'fixture', 'version': '1.0.0',
                 'years': {'first': 2020, 'last': 2021},
                 'current_county_navigation': ['臺北市'], 'authority_roles': ['library'],
                 'topics': [{'id': 'library_count', 'label': '館數'}]}
        (self.root / 'scripts/phase1_scope.json').write_text(json.dumps(scope, ensure_ascii=False))
        shutil.copyfile(ROOT / 'scripts/build_phase1_inventory.py', self.root / 'scripts/build_phase1_inventory.py')
        with patch.object(sys, 'argv', ['build_phase1_inventory.py', '--root', str(self.root)]), contextlib.redirect_stdout(io.StringIO()):
            phase1.main()

    def validate_phase1_fixture(self):
        with patch.object(sys, 'argv', ['validate_phase1_inventory.py', '--root', str(self.root), '--allow-incomplete-survey']), contextlib.redirect_stdout(io.StringIO()):
            phase1_validator.main()

    def test_mixed_year_sort_preserves_every_original_value_and_period(self):
        self.assertEqual([row['data_year'] for row in self.rows], [2020, 2021, None, None, None])
        self.assertEqual({row['observation_id'] for row in self.rows}, {row['observation_id'] for row in self.input_rows})
        by_id = {row['observation_id']: row for row in self.rows}
        for original in self.input_rows:
            for field, value in original.items():
                self.assertEqual(by_id[original['observation_id']][field], value, (original['observation_id'], field))
        self.assertFalse(any(row['data_year'] == 0 for row in self.rows))

    def test_schema_summary_source_coverage_and_indicator_keep_unknown(self):
        schema = read_json(self.root / 'data/combined/observation.schema.json')
        self.assertEqual(schema['properties']['data_year']['type'], ['integer', 'null'])
        self.assertIn('never replace it with zero', schema['properties']['data_year']['description'])
        self.assertEqual(self.summary['reference_years'], [2020, 2021])
        self.assertEqual(self.summary['unresolved_period_records'], 3)
        coverage = read_json(self.root / 'data/combined/coverage.json')[0]
        self.assertEqual(coverage['data_years'], [2020, 2021, None])
        self.assertEqual(coverage['unresolved_period_records'], 3)
        self.assertIn(None, coverage['periods'])
        self.assertNotIn('None', coverage['periods'])
        indicator = read_json(self.root / 'data/combined/indicators.json')[0]
        self.assertEqual(indicator['observed_years'], [2020, 2021, None])
        self.assertEqual(indicator['unresolved_period_records'], 3)

    def test_all_unresolved_source_does_not_invent_a_reference_year(self):
        self.input_rows = [row for row in self.input_rows if row['data_year'] is None]
        self.rebuild_fixture()
        self.assertEqual(self.summary['reference_years'], [])
        self.assertEqual(self.summary['unresolved_period_records'], 3)
        coverage = read_json(self.root / 'data/combined/coverage.json')[0]
        self.assertEqual(coverage['data_years'], [None])
        self.assertIsNone(coverage['year'])
        self.assertEqual(read_json(self.root / 'data/combined/indicators.json')[0]['observed_years'], [None])

    def test_csv_empty_year_and_sqlite_null_are_not_zero(self):
        with (self.root / 'data/combined/observations.csv').open(encoding='utf-8-sig', newline='') as stream:
            csv_rows = list(csv.DictReader(stream))
        self.assertEqual([row['data_year'] for row in csv_rows if row['observation_id'].startswith('unknown-')], ['', '', ''])
        with sqlite3.connect(self.root / 'data/combined/library_statistics.sqlite') as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM observations WHERE data_year IS NULL').fetchone()[0], 3)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM observations WHERE data_year = 0').fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT value FROM observations WHERE observation_id='known-zero-2020'").fetchone()[0], '0')

    def test_partition_union_is_byte_exact_and_keeps_original_unknown_rows(self):
        index = self.prepare_fixture_partitions()
        self.assertEqual([item['data_year'] for item in index['partitions']], [2020, 2021, None])
        self.assertEqual(index['partitions'][-1]['path'], 'data/by_year/unresolved_period.jsonl')
        self.assertEqual(index['unresolved_period_records'], 3)
        union = b''.join((self.root / item['path']).read_bytes() for item in index['partitions'])
        self.assertEqual(union, record_io.body(self.root))
        unknown = [json.loads(line) for line in (self.root / 'data/by_year/unresolved_period.jsonl').read_text().splitlines()]
        self.assertEqual(unknown, [row for row in self.rows if row['data_year'] is None])
        self.assertFalse((self.root / 'data/by_year/0.jsonl').exists())

    def test_publication_count_review_keeps_unknown_separate_from_value_missingness(self):
        counts = publication.publication_counts(self.summary, self.rows)
        self.assertEqual(counts['reference_years'], [2020, 2021])
        self.assertEqual(counts['unresolved_period_records'], 3)
        self.assertEqual(counts['missing_cells'], 1)
        broken = {**self.summary, 'unresolved_period_records': 0}
        with self.assertRaisesRegex(ValueError, 'unresolved_period_records'):
            publication.publication_counts(broken, self.rows)

    def test_strict_publication_accepts_null_years_in_all_formats_and_partitions(self):
        self.prepare_publication_fixture()
        report = self.validate_publication_fixture()
        self.assertEqual(report['unresolved_period_records'], 3)
        self.assertEqual(report['annual_partition_union_checked'], 3)
        self.assertEqual(report['reported_zero_cells'], 1)
        self.assertEqual(report['missing_cells'], 1)
        self.assertTrue(report['publication_validation_complete'])

    def test_gzip_canonical_with_unresolved_partition_keeps_exact_logical_union(self):
        self.prepare_publication_fixture()
        plain = self.root / 'data/combined/observations.jsonl'
        body = plain.read_bytes()
        (self.root / 'data/combined/observations.jsonl.gz').write_bytes(publication.gzip_bytes(body))
        plain.unlink()
        summary = {**self.summary, 'canonical_jsonl_path': 'data/combined/observations.jsonl.gz',
                   'jsonl_compression': 'gzip', 'canonical_uncompressed_sha256': hashlib.sha256(body).hexdigest()}
        (self.root / 'data/combined/summary.json').write_text(json.dumps(summary))
        index_path = self.root / 'data/by_year/index.json'
        index = read_json(index_path)
        index['canonical_path'] = summary['canonical_jsonl_path']
        index_path.write_text(json.dumps(index))
        self.write_publication_manifest()
        report = self.validate_publication_fixture()
        self.assertEqual(report['unresolved_period_records'], 3)
        self.assertEqual(report['annual_partition_union_checked'], 3)
        self.assertEqual(report['canonical_uncompressed_sha256'], hashlib.sha256(body).hexdigest())
        self.assertTrue(report['publication_validation_complete'])

    def test_strict_publication_rejects_lost_unknown_partition(self):
        self.prepare_publication_fixture()
        path = self.root / 'data/by_year/index.json'
        index = read_json(path)
        index['partitions'] = [item for item in index['partitions'] if item['data_year'] is not None]
        path.write_text(json.dumps(index))
        self.write_publication_manifest()
        with self.assertRaisesRegex(publication_validator.ValidationError, 'partition union'):
            self.validate_publication_fixture()

    def test_strict_publication_rejects_unknown_rows_assigned_to_zero_year(self):
        self.prepare_publication_fixture()
        path = self.root / 'data/by_year/index.json'
        index = read_json(path)
        index['partitions'][-1]['data_year'] = 0
        path.write_text(json.dumps(index))
        self.write_publication_manifest()
        with self.assertRaisesRegex(publication_validator.ValidationError, 'rows/year mismatch'):
            self.validate_publication_fixture()

    def test_strict_publication_rejects_unknown_rows_hidden_from_summary(self):
        self.prepare_publication_fixture()
        path = self.root / 'data/combined/summary.json'
        broken = {**self.summary, 'unresolved_period_records': 0}
        path.write_text(json.dumps(broken))
        self.write_publication_manifest()
        with self.assertRaisesRegex(publication_validator.ValidationError, 'Unresolved period count'):
            self.validate_publication_fixture()

    def test_profiles_are_complete_but_unknown_years_never_enter_p1_annual_grid(self):
        self.build_phase1_fixture()
        self.validate_phase1_fixture()
        profiles = [json.loads(line) for line in (self.root / 'derived/phase1_raw_source_profiles.jsonl').read_text().splitlines()]
        matrix = [json.loads(line) for line in (self.root / 'derived/phase1_discovery_matrix.jsonl').read_text().splitlines()]
        self.assertEqual({identifier for item in profiles for identifier in item['observation_ids']}, {row['observation_id'] for row in self.rows})
        unknown_profiles = {item['profile_id'] for item in profiles if item['data_year'] is None}
        self.assertTrue(unknown_profiles)
        self.assertTrue(all(item['temporal_resolution'] == 'time_basis_unconfirmed' for item in profiles if item['data_year'] is None))
        self.assertTrue(all(unknown_profiles.isdisjoint(cell['profile_ids']) for cell in matrix))
        self.assertEqual(sum(cell['matched_source_observations'] for cell in matrix), 2)
        self.assertEqual(read_json(self.root / 'docs/phase1-summary.json')['unresolved_period_records'], 3)

    def test_p1_validator_rejects_unknown_profile_inserted_into_annual_slot(self):
        self.build_phase1_fixture()
        names = ('phase1_authority_checks', 'phase1_source_candidates', 'phase1_raw_source_profiles', 'phase1_discovery_matrix')
        tables = {name: [json.loads(line) for line in (self.root / 'derived' / (name + '.jsonl')).read_text().splitlines()] for name in names}
        unknown = next(item for item in tables['phase1_raw_source_profiles'] if item['data_year'] is None)
        tables['phase1_discovery_matrix'][0]['profile_ids'].append(unknown['profile_id'])
        for name, rows in tables.items():
            phase1.write_table(self.root, name, rows)
        phase1.write_database(self.root, tables)
        with self.assertRaisesRegex(ValueError, 'Unknown period'):
            self.validate_phase1_fixture()

    def test_year_type_validation_does_not_coerce_strings_bools_or_floats(self):
        for year in ('2020', False, True, 2020.0):
            with self.subTest(year=year):
                with self.assertRaises(ValueError):
                    release.period_year_key(year)
                with self.assertRaises(ValueError):
                    publication.period_partition_key(year)

    @unittest.skipUnless(NODE, 'Reader predicate execution requires an already installed node runtime')
    def test_reader_unresolved_filter_excludes_null_from_every_numeric_year(self):
        template = (ROOT / 'site/template.html').read_text()
        self.assertIn('<option value="__unresolved__">期間未確認</option>', template)
        predicate = next(line for line in template.splitlines() if line.startswith('function periodMatches('))
        program = "const assert=require('node:assert/strict');\n" + predicate + "\n" + """
          const unknown={data_year:null}, known={data_year:2020}, zero={data_year:0};
          assert.equal(periodMatches(unknown,''),true);
          assert.equal(periodMatches(unknown,'__unresolved__'),true);
          assert.equal(periodMatches(known,'__unresolved__'),false);
          assert.equal(periodMatches(unknown,'0'),false);
          assert.equal(periodMatches(unknown,'2020'),false);
          assert.equal(periodMatches(known,'2020'),true);
          assert.equal(periodMatches(known,'2021'),false);
          assert.equal(periodMatches(zero,'0'),true);
          assert.equal(periodMatches({data_year:false},'0'),false);
        """
        subprocess.run([NODE, '-'], input=program, text=True, check=True, capture_output=True)
        script = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', template, re.S)[-1]
        subprocess.run([NODE, '--check', '-'], input=script, text=True, check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
