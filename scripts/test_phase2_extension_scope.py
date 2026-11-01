"""The phase2 frozen scope admits only complete, explicitly verified additions."""
import copy
import unittest
from pathlib import Path
import record_io
from check_phase2_cases import accepted_extension_scope

ROOT=Path(__file__).resolve().parents[1]


class Phase2ExtensionScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows={}
        for name in ['derived/discovered_20261028_observations.jsonl','derived/ncl94_statistics_observations.jsonl']:
            cls.rows.update({row['observation_id']:row for row in record_io.rows(ROOT,name)})

    def changed(self,document):
        rows=dict(self.rows)
        identifier=next(key for key,row in rows.items() if row['component_source_id']==document)
        rows[identifier]=copy.deepcopy(rows[identifier])
        return rows,identifier

    def test_old_and_new_complete_sources_have_distinct_scope(self):
        report=accepted_extension_scope(ROOT,self.rows)
        self.assertEqual(report['legacy_extension']['canonical_observations_checked'],20358)
        self.assertEqual(report['additional_batches']['ncl-ed94-statistics']['canonical_observations_checked'],24)
        self.assertEqual(report['accepted_records'],20382)

    def test_unknown_source_is_not_accepted_by_prefix(self):
        rows,key=self.changed('ncl-ed94-statistics');rows[key]['component_source_id']='unknown-source'
        with self.assertRaisesRegex(ValueError,'unreviewed or rights-held'):
            accepted_extension_scope(ROOT,rows)

    def test_changed_new_value_is_not_accepted(self):
        rows,key=self.changed('ncl-ed94-statistics');rows[key]['value']+=1
        with self.assertRaisesRegex(ValueError,'statistical or provenance fields differ'):
            accepted_extension_scope(ROOT,rows)

    def test_missing_new_quantity_is_not_accepted(self):
        rows,key=self.changed('ncl-ed94-statistics');del rows[key]
        with self.assertRaisesRegex(ValueError,'observation set differs'):
            accepted_extension_scope(ROOT,rows)

    def test_missing_legacy_quantity_is_not_accepted(self):
        rows,key=self.changed('ntpc-cultural-2015');del rows[key]
        with self.assertRaisesRegex(ValueError,'formal observation missing from canonical'):
            accepted_extension_scope(ROOT,rows)


if __name__=='__main__':unittest.main()
