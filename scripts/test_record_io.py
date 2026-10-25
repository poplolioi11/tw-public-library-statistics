import gzip,hashlib,json,tempfile,unittest
from pathlib import Path
import record_io

class RecordTransportTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.records=[{'id':'blank','value':None,'raw_value':'無'},{'id':'zero','value':0,'raw_value':'0'},{'id':'decimal','value':'0.85','raw_value':'0.85%'}]
 def enable_gzip(self):
  p=self.root/record_io.PROFILE;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(json.dumps({'schema_version':'1.0.0','jsonl_compression':'gzip'}))
 def test_lossless_bytes_deterministic_gzip_and_all_rows(self):
  plain=record_io.write(self.root,'data/combined/observations.jsonl',self.records).read_bytes()
  self.enable_gzip();path=record_io.write(self.root,'data/combined/observations.jsonl',self.records);first=path.read_bytes()
  self.assertEqual(gzip.decompress(first),plain)
  self.assertEqual(record_io.logical_sha(self.root),hashlib.sha256(plain).hexdigest())
  self.assertEqual(list(record_io.rows(self.root)),self.records)
  record_io.write(self.root,'data/combined/observations.jsonl',self.records)
  self.assertEqual(path.read_bytes(),first)
 def test_failed_serialization_preserves_previous_transport(self):
  for use_gzip in (False,True):
   if use_gzip:self.enable_gzip()
   path=record_io.write(self.root,'data/combined/observations.jsonl',self.records);before=path.read_bytes()
   with self.assertRaises(TypeError):record_io.write(self.root,'data/combined/observations.jsonl',[*self.records,{'bad':{1,2}}])
   self.assertEqual(path.read_bytes(),before)
 def test_corrupt_or_truncated_gzip_is_not_silently_read(self):
  self.enable_gzip();path=record_io.write(self.root,'data/combined/observations.jsonl',self.records)
  path.write_bytes(path.read_bytes()[:-4])
  with self.assertRaises((OSError,EOFError)):list(record_io.rows(self.root))
 def test_profile_does_not_fall_back_to_stale_plain_body(self):
  record_io.write(self.root,'data/combined/observations.jsonl',self.records);self.enable_gzip()
  with self.assertRaises(FileNotFoundError):list(record_io.rows(self.root))
 def test_components_follow_same_profile_and_source_core_remains_plain(self):
  self.enable_gzip()
  self.assertTrue(str(record_io.write(self.root,'data/component_records.jsonl',self.records)).endswith('.gz'))
  self.assertFalse(str(record_io.write(self.root,'data/observations.jsonl',self.records)).endswith('.gz'))
 def test_path_cannot_escape_dataset(self):
  with self.assertRaises(ValueError):record_io.path_for(self.root,'../other.jsonl')

if __name__=='__main__':unittest.main()
