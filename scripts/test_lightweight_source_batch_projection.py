"""Keep canonical-only public metadata separate from source-statistic changes."""
import copy
import json
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import build_lightweight_site as builder
import validate_lightweight_site as validator


class SourceBatchProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = SCRIPTS.parent
        cls.rows = [json.loads(line) for line in
                    (cls.root / 'derived/ncl94_statistics_observations.jsonl').read_text().splitlines()
                    if line.strip()]

    def public_row(self, source):
        return {**copy.deepcopy(source),
                'public_evidence_sha256': 'f' * 64,
                'public_projection_policy': 'synthetic-public-projection-test'}

    def assert_match(self, canonical, source, expected):
        for module in (builder, validator):
            with self.subTest(module=module.__name__):
                self.assertEqual(module.source_batch_matches_canonical(canonical, source), expected)

    def test_identical_formal_rows_still_match(self):
        self.assertEqual(len(self.rows), 24)
        for source in self.rows:
            with self.subTest(observation=source['observation_id']):
                self.assert_match(copy.deepcopy(source), source, True)

    def test_only_named_canonical_annotations_may_be_added(self):
        for source in self.rows:
            with self.subTest(observation=source['observation_id']):
                self.assert_match(self.public_row(source), source, True)
        for key in ('public_evidence_sha256', 'public_projection_policy'):
            self.assert_match({**self.rows[0], key: 'synthetic'}, self.rows[0], True)

    def test_unknown_extra_field_is_not_dropped(self):
        source = self.rows[0]
        self.assert_match({**self.public_row(source), 'unexpected_public_metadata': None}, source, False)

    def test_missing_source_field_is_rejected_even_when_null(self):
        source = self.rows[0]
        canonical = self.public_row(source)
        del canonical['unit']
        self.assert_match(canonical, source, False)

    def test_source_fields_remain_exact(self):
        source = self.rows[0]
        mutations = {'value': 999, 'raw_value': '999', 'source_sha256': '0' * 64,
                     'source_locator': 'PDF 99; changed cell', 'unit': '館',
                     'period_raw': '民國94年', 'data_year': 2005,
                     'period_start': '2004-01-01', 'period_end': '2004-12-31'}
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                self.assert_match({**self.public_row(source), field: replacement}, source, False)
        canonical = self.public_row(source)
        context = json.loads(canonical['source_time_reference'])
        context['physical_source_context']['quantity_role'] = 'changed-role'
        canonical['source_time_reference'] = json.dumps(context, ensure_ascii=False)
        self.assert_match(canonical, source, False)

    def test_metadata_already_in_source_must_also_match(self):
        for key in ('public_evidence_sha256', 'public_projection_policy'):
            source = {**self.rows[0], key: 'source-value'}
            self.assert_match(dict(source), source, True)
            self.assert_match({**source, key: 'different-value'}, source, False)

    def test_missing_canonical_record_is_rejected(self):
        self.assert_match(None, self.rows[0], False)

    def test_allowed_metadata_does_not_change_built_batch(self):
        originals = {'canonical:' + row['observation_id']: row for row in self.rows}
        public = {key: self.public_row(row) for key, row in originals.items()}
        self.assertEqual(builder.build_source_batch(self.root, originals),
                         builder.build_source_batch(self.root, public))

    def test_builder_rejects_changed_source_facts(self):
        for field, replacement in (('value', 999), ('source_sha256', '0' * 64),
                                   ('source_locator', 'PDF 99; changed cell')):
            with self.subTest(field=field):
                public = {'canonical:' + row['observation_id']: self.public_row(row)
                          for row in self.rows}
                public['canonical:' + self.rows[0]['observation_id']][field] = replacement
                with self.assertRaisesRegex(ValueError, 'differs from its formally ingested canonical record'):
                    builder.build_source_batch(self.root, public)


if __name__ == '__main__':
    unittest.main()
