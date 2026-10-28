"""Regression checks for source-evidence boundaries; no government requests."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from validate_source_discovery import REGISTER, ROOT, validate


class SourceDiscoveryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.register = json.loads((ROOT / REGISTER).read_text())
        for name in (REGISTER, 'VERSION', 'docs/phase2-summary.json', 'docs/source-backlog.json', self.register['bounded_probe']['path']):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def mutate_probe(self, change):
        path = self.root / self.register['bounded_probe']['path']
        probe = json.loads(path.read_text())
        change(probe['records'])
        path.write_text(json.dumps(probe, ensure_ascii=False) + '\n')
        self.register['bounded_probe']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root / REGISTER).write_text(json.dumps(self.register, ensure_ascii=False) + '\n')

    def test_complete_bounded_evidence(self):
        report = validate(self.root)
        self.assertEqual(report['pdf_source_cells_checked'], 396)
        self.assertEqual(report['formal_observations_added'], 0)

    def test_cross_page_id_collision_is_rejected(self):
        def collision(rows):
            rows[4]['probe_record_id'] = rows[0]['probe_record_id']
        self.mutate_probe(collision)
        with self.assertRaisesRegex(ValueError, 'duplicate cell IDs'):
            validate(self.root)

    def test_unknown_marker_cannot_become_zero(self):
        def guess(rows):
            row = next(x for x in rows if x['value'] is None)
            row['value'] = '0'
        self.mutate_probe(guess)
        with self.assertRaisesRegex(ValueError, 'marker was guessed'):
            validate(self.root)

    def test_district_context_cannot_become_explicit_year(self):
        def guess(rows):
            row = next(x for x in rows if x['period_status'] == 'district_row_year_not_explicit')
            row['data_year'] = 2015
        self.mutate_probe(guess)
        with self.assertRaisesRegex(ValueError, 'district year guessed'):
            validate(self.root)

    def test_multi_year_change_cannot_become_annual(self):
        def guess(rows):
            row = next(x for x in rows if x['source_row_label_raw'] == '100-104變動情形')
            row['data_year'] = 2015
        self.mutate_probe(guess)
        with self.assertRaisesRegex(ValueError, 'annualized'):
            validate(self.root)

    def test_rights_hold_cannot_publish_probe(self):
        source = next(x for x in self.register['candidates'] if x['candidate_id'] == 'tpml-annual-2012')
        source['bounded_probe_path'] = self.register['bounded_probe']['path']
        (self.root / REGISTER).write_text(json.dumps(self.register, ensure_ascii=False) + '\n')
        with self.assertRaisesRegex(ValueError, 'held source must not publish'):
            validate(self.root)

    def test_backlog_rebuild_shape_is_preserved(self):
        path = self.root / 'docs/source-backlog.json'
        backlog = json.loads(path.read_text())
        source = next(x for x in backlog['families'] if x['family_id'] == 'ncl_yearbook_public_library_chapters')
        source['known_not_ingested'].append('unstructured addition')
        path.write_text(json.dumps(backlog, ensure_ascii=False) + '\n')
        with self.assertRaisesRegex(ValueError, 'backlog item must be an object'):
            validate(self.root)


if __name__ == '__main__':
    unittest.main()
