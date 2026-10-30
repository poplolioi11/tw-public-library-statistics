import copy, json, unittest
from collections import Counter
from pathlib import Path
import record_io
from backlog_ingestion_status import reconcile

ROOT=Path(__file__).resolve().parents[1]

class BacklogReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch=json.loads((ROOT/'raw/discovered-20261028/extraction-metadata.json').read_text())
        cls.rows=[{k:r.get(k) for k in ('component_source_id','source_id','source_family','source_url','data_year')}
                  for r in record_io.rows(ROOT) if r.get('component_source_id') in cls.batch['source_counts']]
        cls.current=json.loads((ROOT/'docs/source-backlog.json').read_text())

    def test_ingested_cells_replace_probe_only_state_without_counting_probe_twice(self):
        b=copy.deepcopy(self.current)
        local=next(f for f in b['families'] if f['family_id']=='local_publication_statistical_facts')
        local.update(status='complete_bounded_table_probes_only',completed_scope={'formal_observations':0})
        reconcile(b,self.rows,self.batch)
        expected=sum(r['source_family']=='地方官方出版統計事實' for r in self.rows)
        self.assertEqual(local['completed_scope']['formal_observations'],expected)
        self.assertEqual(local['status'],'completed_bounded_scope')
        self.assertEqual(local['historical_probe_scope']['role'],'v0.8 discovery snapshot; not additional formal observations')
        dgbas=next(t for t in b['backlog'] if t['task_id']=='B07')
        actual_nulls=sum(r['component_source_id']=='dgbas-yearbook-113' and r['data_year'] is None for r in self.rows)
        self.assertEqual(dgbas['completed_scope']['period_unresolved_records'],actual_nulls)
        self.assertGreater(actual_nulls,0)
        self.assertEqual(dgbas['status'],'partially_completed_known_tables')

    def test_missing_cell_cannot_silently_mark_batch_complete(self):
        b=copy.deepcopy(self.current);before=copy.deepcopy(b)
        with self.assertRaisesRegex(ValueError,'source counts differ'):
            reconcile(b,self.rows[:-1],self.batch)
        self.assertEqual(b,before)

    def test_completed_other_layer_does_not_return_to_core_pending(self):
        b=copy.deepcopy(self.current)
        family=next(f for f in b['families'] if f['family_id']=='ncl_yearbook_public_library_chapters')
        completed=family['completed_other_layer'][0]
        old=copy.deepcopy(completed);old.pop('status');family['known_not_ingested'].append(old)
        different=copy.deepcopy(old);different['tables']=[{'new_table':'not_yet_completed'}]
        family['known_not_ingested'].append(different)
        reconcile(b,self.rows,self.batch)
        self.assertNotIn(old,family['known_not_ingested'])
        self.assertIn(different,family['known_not_ingested'])
        self.assertIn(completed,family['completed_other_layer'])

    def test_rebuild_is_idempotent_preserves_source_dates_rows_and_no_human_result(self):
        b=copy.deepcopy(self.current);old_checked=b['checked_at'];old_rows=copy.deepcopy(self.rows)
        reconcile(b,self.rows,self.batch);first=copy.deepcopy(b)
        reconcile(b,self.rows,self.batch)
        self.assertEqual(b,first);self.assertEqual(b['checked_at'],old_checked)
        self.assertEqual(self.rows,old_rows)
        self.assertIs(b['status_reconciliation']['human_reading_completed'],False)
        self.assertIs(b['status_reconciliation']['human_double_collation_completed'],False)
        self.assertIsNone(b['status_reconciliation']['human_accuracy_estimate'])

if __name__=='__main__':unittest.main()
