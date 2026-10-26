"""Synthetic offline tests for phase2 formats, source guards and update rollback."""
import collections,csv,gzip,hashlib,io,json,sqlite3,sys,tempfile,unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock
import validate_phase2 as validator
import phase2_update as updater
import run_update

def stable(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def h(b):return hashlib.sha256(b).hexdigest()
def encoded(v):return stable(v) if isinstance(v,(dict,list,bool)) else None if v is None else str(v)
def union(rows):return list(dict.fromkeys(k for r in rows for k in r))
class Phase2Fixture(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.put('VERSION','0.7.0');self.put('fixture-input.txt','known-reviewed-definitions')
  self.raw={layer:[] for layer in validator.LAYERS};self.annotations=[];self.cards=[]
  self.add('canonical','zero',0,'0','冊',year=2018)
  self.add('canonical','scaled',1.25,'1.25','千冊',year=2019,scale='1000')
  self.add('canonical','ratio',.27,'0.27','冊/人',year=2012,kind='source_ratio_period',temporal='source_ratio_reference')
  self.add('local_statistical_cells','display',None,'-','冊',year=2020,status='source_display_typed_value_conflict_unresolved')
  self.add('local_statistical_cells','period',3,'3','冊',year=None,period_status='source_sheet_name_header_period_conflict_unresolved',kind='unresolved')
  self.add('local_statistical_cells','catalogue',4,'4','冊',year=None,period_status='catalog_title_year_only_attachment_undated',kind='unresolved')
  self.add('programme_quantities','programme',42,'42','人',year=None,kind='programme_not_annual')
  extra=dict(self.cards[-1],evidence_id='extra-programme-evidence');self.cards.append(extra);self.annotations[-1]['supporting_evidence_ids']=[extra['evidence_id']]
  self.annotations.sort(key=lambda r:r['record_key'])
  for layer,path in validator.LAYERS.items():self.put(path,''.join(stable(r)+'\n' for r in self.raw[layer]))
  self.groups=[{'comparison_group_id':a['comparison_group_id'],'facets':a['facets'],'record_keys':[a['record_key']],'records':1,'has_multiple_eligible_periods':False} for a in sorted(self.annotations,key=lambda a:a['comparison_group_id'])]
  self.breaks=[{'breakpoint_id':'b1','policy':{'unknown':True}},{'breakpoint_id':'b2','policy':{'years':[2012,2013]},'source_note':None}]
  self.tables={'annotations':self.annotations,'groups':self.groups,'evidence_cards':self.cards,'breakpoints':self.breaks};self.materialize();self.configure_update()
 def put(self,name,body):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body.encode() if isinstance(body,str) else body)
 def add(self,layer,oid,value,raw,unit,year,scale='1',status='reported',period_status='',kind='annual_source_reference',temporal='annual_flow'):
  source='source-'+oid;sha='a'*64;r={'observation_id':oid,'source_id':source,'source_sha256':sha,'source_url':'https://example.invalid/'+source,'source_locator':'row1/column1','value':value,'value_status':status,'unit':unit,'data_year':year,'period_status':period_status,'temporal_kind':temporal,'original_fields':{'private_duplicate':'not a separate statistic'}}
  r['raw_value' if layer=='canonical' else 'value_raw']=raw;self.raw[layer].append(r)
  eid='evidence-'+oid;key=layer+':'+oid;number=None if value is None else format(Decimal(str(value))*Decimal(scale),'f')
  ann={'record_key':key,'layer':layer,'observation_id':oid,'source_id':source,'source_sha256':sha,'source_url':r['source_url'],'source_locator':r['source_locator'],'raw_value':raw,'original_value':value,'value_status':status,'comparison_unit':'冊' if unit=='千冊' else unit,'unit_scale':scale,'comparison_value':number,'comparison_status':'unresolved' if value is None or year is None else 'source_series_only','comparison_year':year,'comparison_month':None,'period_kind':kind,'unit_audit_status':'original_unit_preserved','period_audit_status':'fixture_original','measure_class':'ratio_or_per_capita' if 'ratio' in kind else 'source_specific_measure','comparison_group_id':'group-'+oid,'facets':{'measure':oid},'evidence_id':eid,'supporting_evidence_ids':[]}
  self.annotations.append(ann);self.cards.append({'evidence_id':eid,'layer':layer,'source_id':source,'source_sha256':sha,'observation_ids':[oid]})
 def write_pair(self,name,rows,compressed=False):
  keys=union(rows);buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=keys);w.writeheader();w.writerows([{k:encoded(r.get(k)) for k in keys} for r in rows]);csvbody=buf.getvalue().encode('utf-8-sig');jsonbody=''.join(stable(r)+'\n' for r in rows).encode()
  suffix='.gz' if compressed else '';base='derived/phase2/'+name
  self.put(base+'.csv'+suffix,gzip.compress(csvbody,mtime=0) if compressed else csvbody);self.put(base+'.jsonl'+suffix,gzip.compress(jsonbody,mtime=0) if compressed else jsonbody)
 def materialize(self):
  for name,rows in self.tables.items():self.write_pair(name,rows,name=='annotations')
  db=self.root/'derived/phase2/definitions.sqlite'
  if db.exists():db.unlink()
  con=sqlite3.connect(db)
  for name,rows in self.tables.items():
   table={'annotations':'annotation_raw','groups':'group_raw'}.get(name,name);keys=union(rows);con.execute('CREATE TABLE '+table+' ('+','.join('"'+k+'" TEXT' for k in keys)+')');con.executemany('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in keys)+')',[[encoded(r.get(k)) for k in keys] for r in rows])
   if name in {'annotations','groups'}:con.execute('CREATE VIEW '+('annotations' if name=='annotations' else 'comparison_groups')+' AS SELECT * FROM '+table)
  con.commit();con.close();parts=[];by=collections.defaultdict(list)
  for a in self.annotations:by[(a['layer'],a['comparison_year'])].append(a)
  for (layer,year),rows in sorted(by.items(),key=str):
   name='by_year/'+layer+'/'+str(year if year is not None else 'unresolved_period');self.write_pair(name,rows);jp='derived/phase2/'+name+'.jsonl';cp='derived/phase2/'+name+'.csv';parts.append({'layer':layer,'comparison_year':year,'records':len(rows),'jsonl':jp,'csv':cp,'jsonl_sha256':h((self.root/jp).read_bytes()),'csv_sha256':h((self.root/cp).read_bytes())})
  self.index={'version':'0.7.0','records':len(self.annotations),'partitions':parts};self.put('docs/phase2-partitions.json',json.dumps(self.index))
  clean=lambda rows:[{k:v for k,v in r.items() if k not in validator.IGNORED} for r in rows]
  fps={l:h(stable(clean(rows)).encode()) for l,rows in self.raw.items()}
  self.summary={'dataset_version':'0.7.0','canonical_values_modified':False,'no_imputation':True,'layers':{l:len(v) for l,v in self.raw.items()},'total_quantitative_records':len(self.annotations),'source_definition_cards':len(self.cards),'comparison_groups':len(self.groups),'breakpoint_rules':len(self.breaks),'comparison_status_counts':dict(sorted(collections.Counter(a['comparison_status'] for a in self.annotations).items())),'literal_unit_suffix_upgrades':0,'strict_literal_month_code_records':0,'groups_with_multiple_eligible_periods':0,'layer_raw_fingerprints':fps,'canonical_statistical_content_sha256':fps['canonical'],'partition_index':'docs/phase2-partitions.json','inputs':{'fixture-input.txt':h(b'known-reviewed-definitions')}}
  self.refresh_hashes()
 def refresh_hashes(self):
  self.summary['outputs']={str(p.relative_to(self.root)):{'sha256':h(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted((self.root/'derived/phase2').rglob('*')) if p.is_file()};self.put('docs/phase2-summary.json',json.dumps(self.summary))
 def configure_update(self):
  for name in updater.CODE:self.put('scripts/'+name,'# reviewed fixture code '+name)
  for name in updater.phase2_engine.EVIDENCE_FILES:self.put(name,'{"source_cards":[]}')
  self.put('raw/phase2-definitions/current-reference-sources.json','{}');self.put('docs/phase2-contract.json','{}');self.put('site/phase2-template.html','<script id="phase2-data" type="application/json">__PHASE2_DATA__</script>')
 def test_complete_synthetic_three_layers_sparse_views_and_multiple_evidence_pass(self):
  report=validator.validate(self.root);self.assertEqual(report['records'],7);self.assertEqual(report['source_guards']['source_zeros_preserved'],1);self.assertEqual(report['source_guards']['exact1000_scaling_checked'],1);self.assertEqual(report['source_guards']['special_guards']['2012_original_ratios'],1)
 def test_sparse_null_and_empty_string_are_distinct_in_sql(self):
  rows=[{'a':0,'x':''},{'a':None}];fields=['a','x'];csvrows=[{'a':'0','x':''},{'a':'','x':''}];sqlrows=[{'a':'0','x':''},{'a':None,'x':None}]
  validator.compare_formats(rows,fields,csvrows,fields,sqlrows,'fixture');sqlrows[1]['x']=''
  with self.assertRaisesRegex(ValueError,'SQLite value'):validator.compare_formats(rows,fields,csvrows,fields,sqlrows,'fixture')
 def test_csv_structured_json_must_preserve_boolean_and_lists(self):
  with self.assertRaisesRegex(ValueError,'Structured value'):validator.compare_formats([{'x':[True,0,None]}],['x'],[{'x':'[1,0,null]'}],['x'],[{'x':'[true,0,null]'}],'fixture')
 def test_zero_changed_to_null_is_rejected(self):
  a=next(a for a in self.annotations if a['observation_id']=='zero');a['original_value']=None;self.materialize()
  with self.assertRaisesRegex(ValueError,'Original source representation'):validator.validate(self.root)
 def test_exact_scale_error_is_rejected(self):
  next(a for a in self.annotations if a['observation_id']=='scaled')['comparison_value']='1249.999999999999';self.materialize()
  with self.assertRaisesRegex(ValueError,'Exact Decimal'):validator.validate(self.root)
 def test_display_typed_conflict_cannot_be_zero(self):
  a=next(a for a in self.annotations if a['observation_id']=='display');a['comparison_value']='0';self.materialize()
  with self.assertRaisesRegex(ValueError,'Missing or unqualified'):validator.validate(self.root)
 def test_period_conflict_and_catalog_year_cannot_be_filled(self):
  for oid in ('period','catalogue'):
   with self.subTest(oid=oid):
    a=next(a for a in self.annotations if a['observation_id']==oid);a['comparison_year']=2024;self.materialize()
    with self.assertRaisesRegex(ValueError,'Unknown period assigned'):validator.validate(self.root)
    a['comparison_year']=None
 def test_ratio_cannot_be_relabelled_as_original_quantity(self):
  next(a for a in self.annotations if a['observation_id']=='ratio')['measure_class']='collection_stock';self.materialize()
  with self.assertRaisesRegex(ValueError,'2012 ratio'):validator.validate(self.root)
 def test_evidence_wrong_sha_and_duplicate_id_are_rejected(self):
  self.cards[0]['source_sha256']='b'*64;self.materialize()
  with self.assertRaisesRegex(ValueError,'Evidence original'):validator.validate(self.root)
  self.cards[0]['source_sha256']='a'*64;self.cards[0]['observation_ids']*=2;self.materialize()
  with self.assertRaisesRegex(ValueError,'Duplicate observation IDs'):validator.validate(self.root)
 def test_partition_row_order_is_checked_even_with_updated_file_hash(self):
  part=next(p for p in self.index['partitions'] if p['records']>1);path=self.root/part['jsonl'];lines=path.read_text().splitlines();path.write_text('\n'.join(reversed(lines))+'\n');part['jsonl_sha256']=h(path.read_bytes());self.put('docs/phase2-partitions.json',json.dumps(self.index));self.refresh_hashes()
  with self.assertRaisesRegex(ValueError,'Partition rows or row order'):validator.validate(self.root)
 def test_input_checksum_is_strict(self):
  self.put('fixture-input.txt','changed')
  with self.assertRaisesRegex(ValueError,'Summary input checksum'):validator.validate(self.root)
 def test_update_order_noop_and_metadata_only_no_data_change(self):
  calls=[]
  def execute(name,*args):
   calls.append(name)
   if name=='validate_phase2.py':validator.validate(self.root)
  updater.run(self.root,execute);self.assertEqual(calls,[*updater.STAGES,'validate_phase2.py']);before={str(p.relative_to(self.root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in updater.output_paths(self.root)};oldcontent=updater.content_digest(self.root);calls.clear()
  raw=self.raw['canonical'];raw[0]['original_fields']={'private_duplicate':'changed harmless projection'};raw[0]['snapshot_distribution']='public projection';self.put(validator.LAYERS['canonical'],''.join(stable(r)+'\n' for r in raw))
  result=updater.run(self.root,execute);self.assertFalse(result['rebuilt']);self.assertEqual(calls,['validate_phase2.py']);self.assertEqual(updater.content_digest(self.root),oldcontent)
  for name,old in before.items():self.assertEqual(((self.root/name).read_bytes(),(self.root/name).stat().st_mtime_ns),old)
 def test_update_failure_restores_output_bytes_mtime_and_state(self):
  def execute(name,*args):
   if name=='validate_phase2.py':validator.validate(self.root)
  updater.run(self.root,execute);before={str(p.relative_to(self.root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in updater.output_paths(self.root)};state=(self.root/'data/phase2_update_state.json').read_bytes();self.put('scripts/phase2_engine.py','# changed reviewed code')
  def fail(name,*args):self.put('derived/phase2/annotations.jsonl.gz',b'partial');self.put('README.md','partial shared documentation');raise RuntimeError('synthetic stage failure')
  with self.assertRaisesRegex(RuntimeError,'synthetic'):updater.run(self.root,fail)
  self.assertEqual((self.root/'data/phase2_update_state.json').read_bytes(),state);self.assertFalse((self.root/'README.md').exists())
  for name,old in before.items():self.assertEqual(((self.root/name).read_bytes(),(self.root/name).stat().st_mtime_ns),old)
 def test_missing_source_fails_before_rebuild_and_preserves_outputs(self):
  before=updater.output_hashes(self.root);(self.root/validator.LAYERS['canonical']).unlink();calls=[]
  with self.assertRaises(FileNotFoundError):updater.run(self.root,lambda *args:calls.append(args))
  self.assertFalse(calls);self.assertEqual(updater.output_hashes(self.root),before)

 def test_final_phase1_shared_doc_hash_refresh_keeps_source_inputs_unchanged(self):
  self.put('README.md','phase1 then phase2 final prose');old={'inputs':{'approved-source':'unchanged-hash'},'outputs':{'README.md':'old-phase1-hash'}};self.put('data/phase1_hook_state.json',json.dumps(old))
  with mock.patch.object(run_update,'ROOT',self.root):
   self.assertTrue(run_update.refresh_phase1_state_outputs());state=json.loads((self.root/'data/phase1_hook_state.json').read_text());self.assertEqual(state['inputs'],old['inputs']);self.assertEqual(state['outputs'],{'README.md':h((self.root/'README.md').read_bytes())});before=(self.root/'data/phase1_hook_state.json').stat().st_mtime_ns;self.assertFalse(run_update.refresh_phase1_state_outputs());self.assertEqual((self.root/'data/phase1_hook_state.json').stat().st_mtime_ns,before)


 def test_concurrent_definition_input_change_is_not_rolled_back_as_an_output(self):
  def execute(name,*args):
   if name=='validate_phase2.py':validator.validate(self.root)
  updater.run(self.root,execute);state=(self.root/'data/phase2_update_state.json').read_bytes();self.put('scripts/phase2_engine.py','# trigger rebuild')
  def changed(name,*args):
   self.put('docs/phase2-contract.json','{"new_input":true}')
   if name=='validate_phase2.py':validator.validate(self.root)
  with self.assertRaisesRegex(ValueError,'inputs changed'):updater.run(self.root,changed)
  self.assertEqual((self.root/'docs/phase2-contract.json').read_text(),'{"new_input":true}');self.assertEqual((self.root/'data/phase2_update_state.json').read_bytes(),state)
 def reader_payload(self):
  return {'summary':self.summary,'groups':[{**{k:v for k,v in g.items() if k not in {'facets','record_keys'}},'scope_summary':dict(g['facets']),'sample_record_keys':g['record_keys'][:2]} for g in self.groups]}
 def test_reader_compact_groups_complete_ids_scope_and_samples(self):
  self.put('site/phase2.html','<script id="phase2-data" type="application/json">'+stable(self.reader_payload())+'</script>');self.assertNotEqual(validator.validate(self.root)['reader'],'not_present')
 def test_reader_wrong_sample_and_version_are_rejected(self):
  payload=self.reader_payload();payload['groups'][0]['sample_record_keys']=['unknown'];self.put('site/phase2.html','<script id="phase2-data" type="application/json">'+stable(payload)+'</script>')
  with self.assertRaisesRegex(ValueError,'Reader sample IDs'):validator.validate(self.root)
  payload=self.reader_payload();payload['summary']=dict(payload['summary'],dataset_version='wrong');self.put('site/phase2.html','<script id="phase2-data" type="application/json">'+stable(payload)+'</script>')
  with self.assertRaisesRegex(ValueError,'Reader summary'):validator.validate(self.root)


 def test_reviewed_complete_current_outputs_bootstrap_without_building(self):
  inputs=updater.input_signature(self.root);required=[*updater.phase2_engine.EVIDENCE_FILES,'raw/phase2-definitions/current-reference-sources.json','docs/phase2-contract.json','scripts/phase2_engine.py','scripts/build_phase2.py'];self.summary['inputs']={name:inputs['definition_and_code_hashes'][name] for name in required};self.refresh_hashes();self.put('docs/PHASE2.md','Reviewed fixture guide');self.put('docs/phase2-statuses.json','{}');self.put('site/phase2.html','<script id="phase2-data" type="application/json">'+stable(self.reader_payload())+'</script>');calls=[]
  def execute(name,*args):
   calls.append(name)
   if name=='validate_phase2.py':validator.validate(self.root)
  result=updater.run(self.root,execute);self.assertFalse(result['rebuilt']);self.assertTrue(result['bootstrap_verified_outputs']);self.assertEqual(calls,['validate_phase2.py'])


 def test_literal_unit_suffix_promotion_cannot_change_volume_to_people(self):
  raw=self.raw['canonical'][0];raw['unit']=None;raw['source_family']='地方政府開放歷史表';raw['indicator']='借閱冊數';self.put(validator.LAYERS['canonical'],''.join(stable(r)+'\n' for r in self.raw['canonical']));ann=next(a for a in self.annotations if a['observation_id']=='zero');ann['unit_audit_status']='literal_suffix_verified';ann['comparison_unit']='人次';self.materialize();self.summary['literal_unit_suffix_upgrades']=1;self.refresh_hashes()
  with self.assertRaisesRegex(ValueError,'Unsupported literal unit'):validator.validate(self.root)
 def test_invalid_month_code_cannot_be_promoted_even_with_valid_year_label(self):
  raw=self.raw['canonical'][0];raw.update(period_raw='11213',period_basis='observation_field');self.put(validator.LAYERS['canonical'],''.join(stable(r)+'\n' for r in self.raw['canonical']));ann=next(a for a in self.annotations if a['observation_id']=='zero');ann.update(period_audit_status='verified_original_statistical_year_month_code',comparison_year=2023,comparison_month=13,period_kind='monthly_source_statistic');self.materialize();self.summary['strict_literal_month_code_records']=1;self.refresh_hashes()
  with self.assertRaisesRegex(ValueError,'Invalid original literal month'):validator.validate(self.root)

 def test_code_only_rebuild_without_data_change_does_not_create_new_content_signature(self):
  def execute(name,*args):
   if name=='validate_phase2.py':validator.validate(self.root)
  updater.run(self.root,execute);old=updater.content_digest(self.root);self.put('scripts/build_phase2_documentation.py','# new explanatory prose, same facts');self.assertTrue(updater.run(self.root,execute)['rebuilt']);self.assertEqual(updater.content_digest(self.root),old)

if __name__=='__main__':unittest.main()
