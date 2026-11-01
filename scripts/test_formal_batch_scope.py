"""New whole-source batches cannot broaden or replace the old twelve-source set."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch
import cohort_registry
import record_io
from validate_source_discovery import partition_formal_batches
from verify_release import canonical_adapter_count

ROOT=Path(__file__).resolve().parents[1]


class FormalBatchScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new_rows=list(record_io.rows(ROOT,'derived/ncl94_statistics_observations.jsonl'))

    def new_canonical(self):
        return {row['observation_id']:copy.deepcopy(row) for row in self.new_rows}

    def test_complete_new_source_is_separate_from_legacy(self):
        legacy,reports=partition_formal_batches(ROOT,self.new_canonical())
        self.assertEqual(legacy,{})
        self.assertEqual(reports['ncl-ed94-statistics']['canonical_observations_checked'],24)
        self.assertFalse(reports['ncl-ed94-statistics']['human_double_collation_completed'])

    def test_unknown_discovered_document_is_rejected(self):
        rows=self.new_canonical()
        next(iter(rows.values()))['component_source_id']='unreviewed-new-source'
        with self.assertRaisesRegex(ValueError,'unreviewed or rights-held'):
            partition_formal_batches(ROOT,rows)

    def test_missing_new_quantity_is_rejected(self):
        rows=self.new_canonical();rows.pop(next(iter(rows)))
        with self.assertRaisesRegex(ValueError,'observation set differs'):
            partition_formal_batches(ROOT,rows)

    def test_new_value_change_cannot_hide_in_canonical(self):
        rows=self.new_canonical();next(iter(rows.values()))['value']+=1
        with self.assertRaisesRegex(ValueError,'statistical or provenance fields differ'):
            partition_formal_batches(ROOT,rows)

    def test_missing_reviewed_registration_is_rejected(self):
        with patch.object(cohort_registry,'load',return_value=[]):
            with self.assertRaisesRegex(ValueError,'no reviewed canonical-adapter registration'):
                partition_formal_batches(ROOT,self.new_canonical())

    def test_only_publication_fields_may_differ(self):
        rows=self.new_canonical()
        for row in rows.values():
            row['public_projection_policy']='fixture projection metadata'
        partition_formal_batches(ROOT,rows)
        next(iter(rows.values()))['unreviewed_null_field']=None
        with self.assertRaisesRegex(ValueError,'statistical or provenance fields differ'):
            partition_formal_batches(ROOT,rows)

    def test_adapter_registry_full_id_union(self):
        rows=[]
        for group in cohort_registry.load(ROOT):
            if group.get('adapter_kind')=='canonical_observations_jsonl':
                rows.extend(record_io.rows(ROOT,group['canonical_jsonl']))
        self.assertEqual(canonical_adapter_count(ROOT,rows),len(rows))
        with self.assertRaisesRegex(ValueError,'observation set differs'):
            canonical_adapter_count(ROOT,rows[:-1])
        changed=copy.deepcopy(rows);changed[-1]['value']+=1
        with self.assertRaisesRegex(ValueError,'fields differ'):
            canonical_adapter_count(ROOT,changed)
        with self.assertRaisesRegex(ValueError,'Duplicate component'):
            canonical_adapter_count(ROOT,rows+[rows[-1]])
        unknown=copy.deepcopy(rows[-1]);unknown['observation_id']='unregistered-extra'
        with self.assertRaisesRegex(ValueError,'observation set differs'):
            canonical_adapter_count(ROOT,rows+[unknown])


if __name__=='__main__':unittest.main()
