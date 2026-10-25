"""Offline regression: an unavailable source must not erase prior observations."""
import contextlib, importlib.util, io, json, re, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'fetch_local_history.py'

class RefreshPersistence(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('local_history_fixture',SCRIPT)
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.m.ROOT=Path(self.tmp.name);self.m.RAW=self.m.ROOT/'raw'/'official-local';self.m.OUT=self.m.ROOT/'derived'
        self.m.RAW.mkdir(parents=True);self.m.SEEDS=[1]
        self.resource_url='https://public.example.test/observations.json'
        dataset={'@type':'Dataset','name':'臺中市 fixture 統計','license':'https://data.gov.tw/license',
                 'creator':{'name':'fixture agency'},'distribution':[{'encodingFormat':'JSON','contentUrl':self.resource_url}]}
        self.page=('<script type="application/ld+json">'+json.dumps(dataset,ensure_ascii=False)+'</script>'
                   '政府資料開放授權條款-第1版'
                   '<li class="resource-item"><a href="'+self.resource_url+'">JSON</a>檢視資料<span>2020_fixture.JSON</span></li>').encode()
        self.body=json.dumps([{'地區':'臺中市','項目':'借閱(單位:冊)','欄位名稱':'借閱冊數','數值':'7',
                               '資料時間日期':'2020-01-01','資料週期':'年'}],ensure_ascii=False).encode()
        self.http={'retrieved_at':'2026-10-25T00:00:00+00:00','http_status':200,
                   'headers':{'Content-Type':'application/json','Set-Cookie':'fixture-only-secret'}}
        self.m.get=lambda u:(self.page if u=='https://data.gov.tw/dataset/1' else self.body,self.http)
        self.ds=self.m.catalog(1);self.meta=self.m.resource(self.ds,self.ds['resources'][0])

    def fail(self,url):
        raise OSError('offline source unavailable')

    def test_refresh_failure_preserves_full_long_output_and_history(self):
        self.m.get=self.fail
        with patch.object(sys,'argv',['fetch_local_history.py','--refresh']),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.m.main(),0)
        manifest=json.loads((self.m.OUT/'local_historical_metadata.json').read_text())
        self.assertEqual(manifest['summary']['raw_rows'],1)
        self.assertEqual(manifest['summary']['long_rows'],1)
        self.assertEqual(manifest['documents'][0]['source_sha256'],self.meta['source_sha256'])
        self.assertEqual(manifest['documents'][0]['last_check_status'],'failed')
        self.assertEqual(manifest['documents'][0]['freshness'],'stale_after_failed_check')
        self.assertEqual(manifest['catalogues'][0]['last_check_status'],'failed')
        text=(self.m.OUT/'local_historical_long.csv').read_text()
        self.assertIn('借閱冊數',text);self.assertIn('stale_after_failed_check',text)
        self.assertNotIn('Set-Cookie',json.dumps(manifest))
        self.assertNotIn('fixture-only-secret',json.dumps(manifest))
        self.assertGreaterEqual(len(list(self.m.RAW.rglob('*-revision-*.json'))),4)
        self.assertTrue(any(self.m.RAW.rglob('*-revisions.jsonl')))

    def test_corrupt_cache_cannot_be_used_as_fallback(self):
        (self.m.ROOT/self.meta['raw_path']).write_bytes(b'corrupt')
        self.m.get=self.fail
        failed=self.m.resource(self.ds,self.ds['resources'][0],refresh=True)
        self.assertEqual(failed['status'],'failed')
        self.assertFalse(self.m.valid_cached_resource(failed))

    def test_source_failure_without_prior_version_remains_error(self):
        self.m.get=self.fail
        with self.assertRaises(OSError):self.m.catalog(2,refresh=True)

    def test_identical_sha_keeps_first_retrieval_timestamp(self):
        new_http={**self.http,'retrieved_at':'2026-10-26T00:00:00+00:00'}
        self.m.get=lambda url:(self.body,new_http)
        checked=self.m.resource(self.ds,self.ds['resources'][0],refresh=True)
        self.assertEqual(checked['source_sha256'],self.meta['source_sha256'])
        self.assertEqual(checked['source_retrieved_at'],self.meta['source_retrieved_at'])
        self.assertEqual(checked['last_checked_at'],new_http['retrieved_at'])
        raw_files=[p for p in (self.m.RAW/'catalog-1').glob('resource-*.json')
                   if re.fullmatch(r'resource-[0-9a-f]{16}-[0-9a-f]{64}\.json',p.name)]
        self.assertEqual(len(raw_files),1)

    def test_new_sha_preserves_previous_raw_and_metadata(self):
        new_body=self.body.replace(b'"7"',b'"8"')
        new_http={**self.http,'retrieved_at':'2026-10-26T00:00:00+00:00'}
        self.m.get=lambda url:(new_body,new_http)
        changed=self.m.resource(self.ds,self.ds['resources'][0],refresh=True)
        self.assertNotEqual(changed['source_sha256'],self.meta['source_sha256'])
        self.assertEqual(changed['source_retrieved_at'],new_http['retrieved_at'])
        self.assertEqual((self.m.ROOT/self.meta['raw_path']).read_bytes(),self.body)
        revisions=list((self.m.RAW/'catalog-1').glob('resource-*.metadata-revision-*.json'))
        self.assertTrue(any(json.loads(p.read_text()).get('source_sha256')==self.meta['source_sha256'] for p in revisions))

if __name__=='__main__':unittest.main()
