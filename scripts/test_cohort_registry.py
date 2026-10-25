import copy,json,tempfile,unittest
from pathlib import Path
from cohort_registry import load,csv_names

class ReviewedInventoryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);(self.root/'data').mkdir()
  self.group={'id':'reviewed','review_status':'source_reviewed','script':'extract_reviewed.py','args':[],
   'inputs':['raw/reviewed/source.pdf'],'outputs':['derived/reviewed.csv'],
   'derived_csv':'derived/reviewed.csv','raw_directories':['raw/reviewed']}
 def write(self,groups):
  (self.root/'data/reviewed_historical_cohorts.json').write_text(json.dumps({'schema_version':'1.0.0','cohorts':groups}))
 def test_unreviewed_sources_are_not_executed_or_adapted(self):
  pending=copy.deepcopy(self.group);pending.update(id='pending',review_status='not_yet_reviewed',derived_csv='derived/unknown.csv')
  self.write([self.group,pending]);self.assertEqual([g['id'] for g in load(self.root)],['reviewed'])
  self.assertEqual(csv_names(self.root,()),['reviewed.csv'])
 def test_traversal_and_absolute_inputs_are_rejected(self):
  for name in ['raw/../secret.pdf','/private/secret.pdf']:
   with self.subTest(name=name):
    group=copy.deepcopy(self.group);group['inputs']=[name];self.write([group])
    with self.assertRaises(ValueError):load(self.root)
 def test_one_cohort_cannot_overwrite_another(self):
  second=copy.deepcopy(self.group);second['id']='second';self.write([self.group,second])
  with self.assertRaises(ValueError):load(self.root)
 def test_named_csv_must_be_a_tracked_output(self):
  self.group['derived_csv']='derived/untracked.csv';self.write([self.group])
  with self.assertRaises(ValueError):load(self.root)
 def test_external_extractor_paths_are_rejected(self):
  self.group['script']='../outside.py';self.write([self.group])
  with self.assertRaises(ValueError):load(self.root)

if __name__=='__main__':unittest.main()
