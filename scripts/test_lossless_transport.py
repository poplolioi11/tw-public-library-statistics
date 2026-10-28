#!/usr/bin/env python3
"""Bounded offline transport tests; no Git, network or real dataset rebuilds."""
import contextlib
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import build_public_assets as assets
import build_release as release
import record_io
import validate_publication as validator

CSV = 'data/combined/observations.csv'
SQLITE = 'data/combined/library_statistics.sqlite'
DERIVED = 'derived/discovered_20261028_observations.jsonl'
LOSSLESS = [CSV, SQLITE, DERIVED]


class LosslessTransport(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='library-lossless-transport-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def profile(self, root, extra=None):
        path = root / record_io.PROFILE
        path.parent.mkdir(parents=True, exist_ok=True)
        profile = {'schema_version': '1.0.0', 'jsonl_compression': 'gzip'}
        if extra is not None:
            profile['lossless_gzip_paths'] = extra
        path.write_text(json.dumps(profile))

    def fixture(self, name, compressed=False):
        root = self.base / name
        for folder in ('data', 'raw', 'site', 'docs'):
            (root / folder).mkdir(parents=True)
        source = b'{"fixture": "statistical source"}\n'
        (root / 'raw/source.json').write_bytes(source)
        original = {'source_id': 'fixture-source', 'source_family': 'fixture', 'series_id': 'fixture-series',
                    'geography': '全國', 'geographic_scope': 'national_total', 'indicator': '圖書借閱冊數',
                    'unit': '冊', 'source_url': 'https://example.gov.tw/data', 'source_locator': 'fixture table/row/column',
                    'source_sha256': hashlib.sha256(source).hexdigest(), 'source_snapshot_path': 'raw/source.json',
                    'license_status': 'source-specific', 'value_status': 'reported'}
        rows = [{**original, 'observation_id': 'known-zero', 'data_year': 2020, 'value': 0, 'raw_value': '0'},
                {**original, 'observation_id': 'unknown-year', 'data_year': None, 'value': 7, 'raw_value': '7'}]
        (root / 'data/observations.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        (root / 'data/indicators.json').write_text('[]\n')
        (root / 'site/template.html').write_text('__ROWS__\n__SUMMARY__\n__JSONL_HREF__\n__JSONL_LABEL__')
        if compressed:
            self.profile(root, LOSSLESS)
        self.build(root)
        return root

    def build(self, root):
        with patch.object(release, 'ROOT', root), patch.object(release, 'VERSION', '0.0.0'), contextlib.redirect_stdout(io.StringIO()):
            release.main()

    def manifest(self, root):
        files = {path.relative_to(root).as_posix(): assets.sha(path) for path in root.rglob('*')
                 if path.is_file() and path.name != validator.MANIFEST_NAME}
        (root / validator.MANIFEST_NAME).write_text(json.dumps({'files': files}))
        return files

    def publication(self, root):
        rows = list(record_io.rows(root))
        digest = validator.statistical_fingerprint(rows)
        (root / 'docs/publication-integrity.json').write_text(json.dumps({
            'records': len(rows), 'missing_cells': 0, 'original_statistical_content_sha256': digest,
            'public_statistical_content_sha256': digest, 'statistical_and_source_fields_unchanged': True,
        }))
        self.manifest(root)

    def test_legacy_profiles_and_safe_relative_whitelist(self):
        root = self.base / 'legacy'
        root.mkdir()
        self.assertEqual(record_io.path_for(root, CSV), root / CSV)
        self.profile(root)
        self.assertEqual(record_io.path_for(root, CSV), root / CSV)
        self.assertEqual(record_io.path_for(root, SQLITE), root / SQLITE)
        self.assertEqual(record_io.path_for(root, 'data/combined/observations.jsonl'), root / 'data/combined/observations.jsonl.gz')
        for unsafe in ('../outside.csv', '/tmp/outside.csv', 'C:/outside.csv', 'data\\outside.csv', '.', 'data/../outside.csv'):
            with self.subTest(path=unsafe):
                self.profile(root, [unsafe])
                with self.assertRaises(ValueError):
                    record_io.path_for(root, CSV)
        self.profile(root, LOSSLESS)
        outside = self.base / 'outside'
        outside.mkdir()
        (root / 'linked').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            record_io.path_for(root, 'linked/source.jsonl')

    def test_deterministic_gzip_keeps_plain_csv_sqlite_bytes_and_unknown_null(self):
        plain = self.fixture('plain')
        public = self.fixture('public', compressed=True)
        self.assertEqual(record_io.body(public, CSV), (plain / CSV).read_bytes())
        self.assertEqual(record_io.body(public, SQLITE), (plain / SQLITE).read_bytes())
        before = {name: assets.sha(record_io.path_for(public, name)) for name in (CSV, SQLITE)}
        self.build(public)
        self.assertEqual(before, {name: assets.sha(record_io.path_for(public, name)) for name in (CSV, SQLITE)})
        rows = list(record_io.rows(public))
        record_io.write(public, DERIVED, rows)
        self.assertEqual(list(record_io.rows(public, DERIVED)), rows)
        self.assertEqual(record_io.logical_sha(public, DERIVED), hashlib.sha256(record_io.body(public, DERIVED)).hexdigest())
        with record_io.materialized_file(public, SQLITE) as materialized:
            self.assertEqual(materialized.stat().st_mode & 0o222, 0)
            with sqlite3.connect(materialized.as_uri() + '?mode=ro', uri=True) as connection:
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM observations WHERE data_year IS NULL').fetchone()[0], 1)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM observations WHERE data_year=0').fetchone()[0], 0)
                self.assertEqual(connection.execute("SELECT value FROM observations WHERE observation_id='known-zero'").fetchone()[0], '0')
        self.assertFalse(materialized.exists())

    def test_strict_validation_rejects_rehashed_csv_and_sqlite_value_changes(self):
        root = self.fixture('strict', compressed=True)
        self.publication(root)
        report = validator.validate(root)
        self.assertTrue(report['publication_validation_complete'])
        self.assertEqual(report['unresolved_period_records'], 1)
        self.assertTrue(report['canonical_csv_path'].endswith('.csv.gz'))
        self.assertTrue(report['canonical_sqlite_path'].endswith('.sqlite.gz'))
        original_csv = record_io.body(root, CSV)
        reader = csv.DictReader(io.StringIO(original_csv.decode('utf-8-sig')))
        fields, rows = reader.fieldnames, list(reader)
        rows[0]['value'] = '9'
        with record_io.write_text(root, CSV, encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        self.manifest(root)
        with self.assertRaisesRegex(validator.ValidationError, 'CSV differs at value'):
            validator.validate(root)
        record_io.path_for(root, CSV).write_bytes(gzip.compress(original_csv, mtime=0))
        edited = self.base / 'edited.sqlite'
        with record_io.materialized_file(root, SQLITE) as materialized:
            shutil.copyfile(materialized, edited)
        with sqlite3.connect(edited) as connection:
            connection.execute("UPDATE observations SET value='9' WHERE observation_id='known-zero'")
        record_io.write_file(root, SQLITE, edited)
        self.manifest(root)
        with self.assertRaisesRegex(validator.ValidationError, 'SQLite differs at value'):
            validator.validate(root)

    def test_release_assets_verify_gzip_first_and_checksum_the_plain_attachment(self):
        root = self.fixture('assets', compressed=True)
        manifest = self.manifest(root)
        output = self.base / 'assets-output'
        output.mkdir()
        for logical in (CSV, SQLITE):
            target = output / Path(logical).name
            assets.copy_verified_asset(root, logical, target, manifest)
            self.assertEqual(target.read_bytes(), record_io.body(root, logical))
            self.assertEqual(assets.sha(target), hashlib.sha256(record_io.body(root, logical)).hexdigest())
            self.assertNotEqual(assets.sha(target), manifest[record_io.path_for(root, logical).relative_to(root).as_posix()])
        target = output / 'observations.csv'
        prior = assets.sha(target)
        compressed = record_io.path_for(root, CSV)
        compressed.write_bytes(compressed.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'stored-file SHA mismatch'):
            assets.copy_verified_asset(root, CSV, target, manifest)
        self.assertEqual(assets.sha(target), prior)


if __name__ == '__main__':
    unittest.main(verbosity=2)
