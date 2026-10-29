"""Guard that a selected table's continuation pages remain discoverable."""
import json,unittest
from pathlib import Path
import record_io

class SourceSummaryPages(unittest.TestCase):
    def test_ncl91_summary_covers_every_published_scan_cell(self):
        root=Path(__file__).resolve().parents[1]
        docs=json.loads((root/'raw/discovered-20261028/documents.json').read_text())['documents']
        doc=next(r for r in docs if r['candidate_id']=='ncl-ed91-public-libraries')
        rows=[r for r in record_io.rows(root,'derived/discovered_ncl_early_20261028_cells.jsonl') if r['source_document_id']==doc['candidate_id']]
        self.assertEqual(len(rows),369)
        listed={page for loc in doc['locators'] for page in loc['pdf_pages']}
        actual={r['source_pdf_page'] for r in rows}
        self.assertTrue(actual<=listed,(actual,listed))
        self.assertEqual(sum(r['source_pdf_page']==5 for r in rows),9)
        printed={page for loc in doc['locators'] for page in loc['printed_pages']}
        self.assertTrue({r['source_printed_page'] for r in rows}<=printed)

if __name__=='__main__':unittest.main()
