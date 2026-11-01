import json,tempfile,unittest
from pathlib import Path
from monitor_discovered_sources_20261028 import source_documents


class HistoricalMonitorRegistry(unittest.TestCase):
    def test_optional_new_source_manifest(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for folder,sid in [('discovered-20261028','old'),('ncl94-statistics','new')]:
                p=root/'raw'/folder/'documents.json';p.parent.mkdir(parents=True)
                p.write_text(json.dumps({'documents':[{'candidate_id':sid}]}))
            self.assertEqual([x['candidate_id'] for x in source_documents(root)],['old','new'])

    def test_duplicate_source_identity_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for folder in ['discovered-20261028','ncl94-statistics']:
                p=root/'raw'/folder/'documents.json';p.parent.mkdir(parents=True)
                p.write_text(json.dumps({'documents':[{'candidate_id':'same'}]}))
            with self.assertRaises(ValueError):source_documents(root)


if __name__=='__main__':unittest.main()
