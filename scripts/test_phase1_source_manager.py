"""Offline fixtures for independent phase1 cache, failure and monitoring boundaries."""
import datetime,hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest import mock
import phase1_source_manager as manager
import phase1_source_registry as registry
import restore_originals
import run_update

def sha(b):return hashlib.sha256(b).hexdigest()
class Phase1ManagerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.calls=[]
  self.groups=[]
  for n in (1,2):
   script=f'extract_fixture{n}.py';original=f'raw/source{n}.bin';out=f'derived/out{n}.json'
   self.put('scripts/'+script,'# reviewed fixture');self.put(original,'original'+str(n));self.put(out,'approved output'+str(n))
   inputs=[original];outputs=[out]
   self.groups.append(dict(id=f'phase1_fixture{n}',layer='source_cells_not_canonical',review_status='source_reviewed',script=script,args=['--offline'],inputs=inputs,outputs=outputs,
     originals=[dict(path=original,sha256=sha((self.root/original).read_bytes()))],reviewed_inputs={p:sha((self.root/p).read_bytes()) for p in ['scripts/'+script,*inputs]},reviewed_outputs={out:sha((self.root/out).read_bytes())}))
  self.registry=dict(schema_version='1.0.0',canonical_union_permitted=False,batches=self.groups,content_inputs=['derived/out*.json'],monitor_policy={'source_manifest':'raw/phase1_local_sources/sources.json','interval_days':14})
  self.put('data/reviewed_phase1_batches.json',json.dumps(self.registry))
  self.source=dict(source_id='reviewed',source_filename='one.ods',format='ODS',source_download_url='https://example.invalid/one.ods',source_sha256=sha(b'approved'),source_retrieved_at='2026-10-26T00:00:00+00:00',license_status='not_confirmed')
  self.put('raw/phase1_local_sources/sources.json',json.dumps({'sources':[self.source]}));self.put('raw/phase1_local_sources/originals/one.ods',b'approved')
 def put(self,p,b):
  p=self.root/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b.encode() if isinstance(b,str) else b)
 def snapshot(self):
  return {str(p.relative_to(self.root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file() and (p.parent.name=='derived' or p.name.endswith('_extraction_state.json'))}
 def runner(self,script,*args):
  self.calls.append(script)
  g=next(g for g in self.groups if g['script']==script)
  self.put(g['outputs'][0],'rebuilt '+script)
 def test_bootstrap_and_second_run_reuse_verified_outputs_without_producer(self):
  before=self.snapshot();manager.run_batches(self.root,runner=self.runner);self.assertEqual(self.calls,[])
  for path,old in before.items():self.assertEqual(self.snapshot()[path],old)
  before=self.snapshot();manager.run_batches(self.root,runner=self.runner);self.assertEqual(self.snapshot(),before);self.assertEqual(self.calls,[])
 def test_script_change_rebuilds_only_its_batch_then_noop(self):
  manager.run_batches(self.root,runner=self.runner);self.put('scripts/extract_fixture1.py','# reviewed change')
  manager.run_batches(self.root,runner=self.runner);self.assertEqual(self.calls,['extract_fixture1.py'])
  before=self.snapshot();manager.run_batches(self.root,runner=self.runner);self.assertEqual(self.snapshot(),before);self.assertEqual(len(self.calls),1)
 def test_environment_source_root_works_without_local_original_symlinks(self):
  destination=self.root/'private-originals';destination.mkdir()
  for group in self.groups:
   original=group['originals'][0];original['source_filename']=Path(original['path']).name;group['accepts_source_root']=True
   old=self.root/original['path'];(destination/original['source_filename']).write_bytes(old.read_bytes());old.unlink()
  self.put('data/reviewed_phase1_batches.json',json.dumps(self.registry))
  with mock.patch.dict('os.environ',{'TW_LIBRARY_PHASE1_SOURCE_ROOT':str(destination)}):
   result=manager.run_batches(self.root,runner=self.runner)
  self.assertEqual(self.calls,[]);self.assertTrue(all(x['status']=='cached_verified_outputs' for x in result['batches']))
 def test_missing_and_changed_original_fail_before_any_output_or_state_change(self):
  manager.run_batches(self.root,runner=self.runner)
  for fault in ('missing','changed'):
   with self.subTest(fault=fault):
    p=self.root/'raw/source2.bin';p.unlink() if fault=='missing' else p.write_bytes(b'new unreviewed source')
    before=self.snapshot()
    with self.assertRaises((FileNotFoundError,ValueError)):manager.run_batches(self.root,runner=self.runner)
    self.assertEqual(self.snapshot(),before);self.assertEqual(self.calls,[]);self.put('raw/source2.bin','original2')
 def test_partial_write_failure_restores_bytes_mtime_and_state(self):
  manager.run_batches(self.root,runner=self.runner);self.put('scripts/extract_fixture1.py','# trigger');before=self.snapshot()
  def fail(script,*args):self.runner(script,*args);raise RuntimeError('synthetic failure')
  with self.assertRaises(RuntimeError):manager.run_batches(self.root,runner=fail)
  self.assertEqual(self.snapshot(),before)
 def test_missing_output_or_input_change_during_extract_rolls_back(self):
  manager.run_batches(self.root,runner=self.runner);self.put('scripts/extract_fixture1.py','# trigger')
  for fault in ('output','input'):
   with self.subTest(fault=fault):
    before=self.snapshot()
    def fail(script,*args):
     self.runner(script,*args)
     (self.root/'derived/out1.json').unlink() if fault=='output' else self.put('raw/source1.bin','unreviewed concurrent change')
    with self.assertRaises((FileNotFoundError,ValueError)):manager.run_batches(self.root,runner=fail)
    self.assertEqual(self.snapshot(),before);self.put('raw/source1.bin','original1')
 def test_monitor_today_uses_initial_retrieval_date_and_makes_no_request(self):
  fetch=mock.Mock();r=manager.monitor_sources(self.root,now=datetime.datetime(2026,10,26,tzinfo=datetime.timezone.utc),fetcher=fetch)
  self.assertEqual(r['requests_made'],0);fetch.assert_not_called();self.assertFalse((self.root/'data/phase1_source_monitor_state.private.json').exists())
 def test_changed_remote_SHA_does_not_replace_original_or_retrieve_time(self):
  path=self.root/'raw/phase1_local_sources/originals/one.ods';before=(path.read_bytes(),path.stat().st_mtime_ns);manifest=(self.root/'raw/phase1_local_sources/sources.json').read_bytes()
  with mock.patch.dict('os.environ',{},clear=True):
   r=manager.monitor_sources(self.root,now=datetime.datetime(2026,11,10,tzinfo=datetime.timezone.utc),fetcher=lambda url:(b'PKchanged',url,'application/zip'))
  self.assertTrue(r['review_required']);self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before);self.assertEqual((self.root/'raw/phase1_local_sources/sources.json').read_bytes(),manifest)
  state=json.loads((self.root/'data/phase1_source_monitor_state.private.json').read_text())['sources']['reviewed'];self.assertFalse(state['candidate_body_retained']);self.assertEqual(state['candidate_sha256'],sha(b'PKchanged'))
 def test_monitor_failure_preserves_success_metadata_and_retries_next_normal_run(self):
  now=datetime.datetime(2026,11,10,tzinfo=datetime.timezone.utc)
  manager.monitor_sources(self.root,now=now,fetcher=lambda url:(b'approved',url,'application/zip'))
  prior=json.loads((self.root/'data/phase1_source_monitor_state.private.json').read_text())['sources']['reviewed']
  def fail(url):raise OSError('synthetic HTTP failure')
  result=manager.monitor_sources(self.root,now=now+datetime.timedelta(days=15),fetcher=fail)
  after=json.loads((self.root/'data/phase1_source_monitor_state.private.json').read_text())['sources']['reviewed'];self.assertEqual(after['last_verified_approved_SHA_at'],prior['last_verified_approved_SHA_at']);self.assertEqual(after['next_due_basis_at'],prior['next_due_basis_at']);self.assertEqual(result['requests_made'],1)
 def test_content_signature_detects_sidecar_change_when_canonical_is_unchanged(self):
  before=run_update.content_signature(self.root);self.put('derived/out1.json','new sidecar');self.assertNotEqual(run_update.content_signature(self.root),before)
 def test_update_stage_order_then_noop_skips_release_and_phase1_builders(self):
  stages=['adapt_components.py','build_release.py','build_coverage.py','build_documentation.py','build_phase1_inventory.py','build_phase1_supplements.py','build_phase1_reader.py','build_phase1_documentation.py','validate_phase1_inventory.py','validate_phase1_supplements.py']
  for name in stages:self.put('scripts/'+name,'# fixture stage')
  self.put('VERSION','0.6.0');self.put('data/observations.jsonl','{}\n');calls=[]
  def call(name,*args):
   calls.append(name)
   if name=='adapt_components.py':self.put('data/component_records.jsonl','{}\n')
   if name=='build_release.py':self.put('data/combined/observations.jsonl','{}\n');self.put('data/combined/summary.json','{}')
   if name=='build_phase1_inventory.py':self.put('docs/phase1-summary.json','{}')
  with mock.patch.object(run_update,'ROOT',self.root),mock.patch.object(run_update,'call',side_effect=call):
   self.assertTrue(run_update.run_canonical_build());self.assertTrue(run_update.run_phase1_hooks()['rebuilt']);self.assertEqual(calls,stages)
   before={str(p.relative_to(self.root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()};calls.clear()
   self.assertFalse(run_update.run_canonical_build());self.assertFalse(run_update.run_phase1_hooks()['rebuilt'])
   self.assertEqual(calls,['validate_phase1_inventory.py','validate_phase1_supplements.py'])
   for p,old in before.items():self.assertEqual(((self.root/p).read_bytes(),(self.root/p).stat().st_mtime_ns),old)
 def test_offline_due_monitor_never_fetches(self):
  fetch=mock.Mock();r=manager.monitor_sources(self.root,offline=True,now=datetime.datetime(2027,1,1,tzinfo=datetime.timezone.utc),fetcher=fetch)
  self.assertEqual(r['requests_made'],0);fetch.assert_not_called()
 def test_restore_exact_workbook_and_changed_or_existing_source_preservation(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w') as z:z.writestr('mimetype',b'application/vnd.oasis.opendocument.spreadsheet');z.writestr('content.xml','<document/>')
  body=buf.getvalue();self.source['source_sha256']=sha(body);self.put('raw/phase1_local_sources/sources.json',json.dumps({'sources':[self.source]}));dest=self.root/'restored'
  with self.assertRaises(ValueError):restore_originals.restore_phase1(self.root,dest,fetcher=lambda url:b'changed');self.assertFalse((dest/'one.ods').exists())
  restore_originals.restore_phase1(self.root,dest,fetcher=lambda url:body);self.assertEqual((dest/'one.ods').read_bytes(),body)
  (dest/'one.ods').write_bytes(b'prior unreviewed local body');before=(dest/'one.ods').read_bytes()
  with self.assertRaises(ValueError):restore_originals.restore_phase1(self.root,dest,fetcher=lambda url:body)
  self.assertEqual((dest/'one.ods').read_bytes(),before)

if __name__=='__main__':unittest.main(verbosity=2)
