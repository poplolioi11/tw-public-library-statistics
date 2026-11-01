import json,unittest
import record_io
from pathlib import Path
from validate_ncl94_statistics import check_rows


class NCL94Statistics(unittest.TestCase):
    def setUp(self):
        p=Path(__file__).resolve().parents[1]/'derived/ncl94_statistics_observations.jsonl'
        self.rows=list(record_io.rows(p.parents[1], 'derived/ncl94_statistics_observations.jsonl'))

    def test_complete_original_subset(self):
        self.assertEqual(check_rows(self.rows)['physical_cells'],16)

    def test_reject_changed_literal(self):
        self.rows[0]['value']+=1
        with self.assertRaises(ValueError):check_rows(self.rows)

    def test_reject_invented_unit(self):
        self.rows[0]['unit']='館'
        with self.assertRaises(ValueError):check_rows(self.rows)

    def test_reject_response_as_library_total(self):
        row=next(r for r in self.rows if r['aggregation_role']=='responding_libraries_not_total_libraries')
        row['aggregation_role']='published_total'
        with self.assertRaises(ValueError):check_rows(self.rows)

    def test_reject_invented_exact_date(self):
        self.rows[0]['period_end']='2004-12-31'
        with self.assertRaises(ValueError):check_rows(self.rows)

    def test_reject_missing_physical_cell(self):
        with self.assertRaises(ValueError):check_rows(self.rows[:-1])


if __name__=='__main__':unittest.main()
