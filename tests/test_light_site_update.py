import importlib,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import light_site_update as update
class ViewerUpdate(unittest.TestCase):
 def test_unchanged_inputs_skip_and_failed_rebuild_restores_previous_site(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'scripts').mkdir();(root/'docs').mkdir();(root/'site/light/data').mkdir(parents=True)
   for name in ('build_lightweight_site.py','light_site_update.py','validate_lightweight_site.py','build_lightweight_documentation.py'):(root/'scripts'/name).write_text('fixture')
   (root/'site/light/index.html').write_text('verified old chart')
   (root/'README.md').write_text('verified documentation')
   calls=[]
   def success(name,*args):calls.append(name)
   with patch.object(update,'input_hashes',return_value={'fixture':'same'}):
    self.assertTrue(update.run(root,success)['rebuilt']);before={str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
    self.assertFalse(update.run(root,success)['rebuilt']);self.assertEqual(len(calls),3)
    self.assertEqual(before,{str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()})
   def failed(name,*args):
    (root/'site/light/index.html').write_text('unverified new chart');(root/'site/light/data/new.json').write_text('partial');(root/'README.md').write_text('partial');raise RuntimeError('injected validation failure')
   with patch.object(update,'input_hashes',return_value={'fixture':'changed'}):
    with self.assertRaisesRegex(RuntimeError,'injected'):update.run(root,failed)
   self.assertEqual((root/'site/light/index.html').read_text(),'verified old chart');self.assertEqual((root/'README.md').read_text(),'verified documentation');self.assertFalse((root/'site/light/data/new.json').exists())
if __name__=='__main__':unittest.main()
