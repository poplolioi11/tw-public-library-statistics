"""Synthetic offline counterexamples for source selection and update safety."""
import copy,gzip,hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest import mock
import validate_phase3 as v
import phase3_update as u

def sha(body):return hashlib.sha256(body).hexdigest()
def annotations():
 result=[]
 for name,year,value,status in [('zero',2018,0,'reported'),('missing',2019,None,'source_blank'),('after-gap',2020,12,'reported'),('typed',2021,None,'source_display_typed_value_conflict_unresolved'),('unknown',None,5,'reported'),('left',2022,6,'reported'),('right',2023,7,'reported')]:
  facets={'measure_class':'collection_stock','financial_mode':'not_explicit','renewal_scope':'not_applicable','unit':'冊','period_kind':'annual_source_reference','entity':'全國','facility_or_reader_category':'','geographic_scope':'national_total','geography_key':'same-source','population_scope':'same source population','national_libraries_scope':'unknown','aggregation_role':'printed_total','institutional_level':'national_total','classification_dimensions':{},'source_segment':'same-original-panel'}
  good=value is not None and year is not None;result.append({'record_key':'canonical:'+name,'layer':'canonical','observation_id':name,'source_id':'reviewed-source','source_sha256':'a'*64,'source_url':'https://example.invalid/official','source_locator':'row:'+name,'source_version_id':'reviewed-source@sha256:'+'a'*64,'source_edition_raw':114,'evidence_id':'reviewed-evidence','raw_value':'-' if value is None else str(value),'original_value':value,'value_status':status,'comparison_status':'published_panel_limited' if good else 'unresolved','comparison_unit':'冊','comparison_year':year,'comparison_month':None,'comparison_group_id':'original-group' if name in {'left','right'} else 'group-'+name,'quality_flags_original':[],'unit_raw_preserved':'冊','raw_indicator':'館藏冊數','measure_class':'collection_stock','comparison_value':None if value is None else str(value),'period_kind':'annual_source_reference' if year is not None else 'unresolved','definition_signature':'b'*64,'facets':facets,'reasons':[] if good else ['source_unknown'],'zero_interpretation':'source_reported_zero_not_certified_measured_zero' if value==0 else None})
 return result
class Phase3Rows(unittest.TestCase):
 def setUp(self):
  self.contract=json.loads((Path(__file__).resolve().parents[1]/'docs/phase3-contract.json').read_text());self.a=annotations();self.profile=self.contract['profiles'][0];self.routes=[];self.decisions=[]
  routecopy=('record_key','layer','observation_id','source_id','source_sha256','source_url','source_locator','source_version_id','evidence_id','raw_value','original_value','value_status','comparison_status','comparison_unit','comparison_year','comparison_month','comparison_group_id','quality_flags_original','zero_interpretation')
  for a in self.a:
   r={k:a.get(k) for k in routecopy};r.update(route_id='route-'+a['observation_id'],candidate_profile_ids=[self.profile],route_status='registered_profile_candidate',reason_codes=[],source_version_reviewed=True);self.routes.append(r)
   status='selected_source_missing' if a['value_status']=='source_blank' else 'selected_source_unusable' if a['comparison_status']=='unresolved' else 'selected_source_fact'
   d={k:a.get(k) for k in ('record_key','layer','observation_id','source_id','source_sha256','source_url','source_locator','source_version_id','evidence_id','source_edition_raw','raw_indicator','original_value','raw_value','unit_raw_preserved','value_status','comparison_status','comparison_group_id','definition_signature','quality_flags_original','facets','period_kind')};d.update(decision_id='decision-'+a['observation_id'],profile_id=self.profile,policy_version='fixture1',selection_status=status,selection_reasons=[],source_bundle_id='same-original',entity='全國',facility_or_reader_category='',point_value=a['comparison_value'] if status=='selected_source_fact' else None,point_unit=a['comparison_unit'],period_year=a['comparison_year'],period_month=a['comparison_month'],selected=True,source_version_reviewed=True,join_segment_id=a['comparison_group_id'] if status=='selected_source_fact' and a['comparison_status']=='published_panel_limited' else None);self.decisions.append(d)
  self.queries=[{'profile_id':p,'selected_record_keys':[a['record_key'] for a in self.a] if p==self.profile else []} for p in self.contract['profiles']]
  self.edges=[{'edge_id':'edge-good','profile_id':self.profile,'left_record_key':'canonical:left','right_record_key':'canonical:right','comparison_group_id':'original-group','drawable':True,'comparison_status':'published_panel_limited','reasons':[],'period_left':[2022,None],'period_right':[2023,None]}]
  self.edges[0]['reasons']=v.phase2_engine.compare(next(a for a in self.a if a['observation_id']=='left'),next(a for a in self.a if a['observation_id']=='right'))['reasons']
 def check(self):return v.validate_rows(self.routes,self.decisions,self.queries,self.edges,self.a,self.contract)
 def test_valid_preserves_missing_typed0_unknown_and_zero(self):
  r=self.check();self.assertEqual(r['records'],7);self.assertEqual(r['profiles'],len(self.contract['profiles']));self.assertEqual(r['drawable_edges'],1)
 def test_wrong_source_sha_or_original_value_fails(self):
  for field,value in [('source_sha256','c'*64),('original_value',99)]:
   with self.subTest(field=field):
    old=self.decisions[0][field];self.decisions[0][field]=value
    with self.assertRaisesRegex(ValueError,'changed phase2'):self.check()
    self.decisions[0][field]=old
 def test_routes_cannot_omit_or_duplicate_original(self):
  self.routes.append(dict(self.routes[0]))
  with self.assertRaisesRegex(ValueError,'duplicate routed'):self.check()
  self.routes.pop();self.routes.pop()
  with self.assertRaisesRegex(ValueError,'exactly one'):self.check()
 def test_typed_conflict_cannot_be_zero_or_missing(self):
  d=next(d for d in self.decisions if d['observation_id']=='typed');d['point_value']='0'
  with self.assertRaisesRegex(ValueError,'manufactured'):self.check()
  d['point_value']=None;d['selection_status']='selected_source_missing'
  with self.assertRaisesRegex(ValueError,'Conflict or numeric'):self.check()
 def test_unknown_date_and_facet_cannot_be_overwritten(self):
  d=next(d for d in self.decisions if d['observation_id']=='unknown');d['period_year']=2024
  with self.assertRaisesRegex(ValueError,'changed phase2'):self.check()
  d['period_year']=None;d['facets']=dict(d['facets'],unit='人次')
  with self.assertRaisesRegex(ValueError,'changed phase2'):self.check()
 def test_query_must_retain_selected_missing_and_unusable_ids(self):
  self.queries[0]['selected_record_keys'].remove('canonical:missing')
  with self.assertRaisesRegex(ValueError,'selected IDs'):self.check()
 def test_unregistered_profile_and_duplicate_profile_record_are_rejected(self):
  self.decisions[0]['profile_id']='unregistered'
  with self.assertRaisesRegex(ValueError,'profile-record'):self.check()
  self.decisions[0]['profile_id']=self.profile;self.decisions.append(dict(self.decisions[0],decision_id='other-id'))
  with self.assertRaisesRegex(ValueError,'profile-record'):self.check()
 def test_unreviewed_version_cannot_be_selected(self):
  self.routes[0]['source_version_reviewed']=False;self.routes[0]['route_status']='unreviewed_source_version';self.decisions[0]['source_version_reviewed']=False
  with self.assertRaisesRegex(ValueError,'Unreviewed version selected'):self.check()
 def test_source_series_fact_is_allowed_but_not_upgraded(self):
  left=next(a for a in self.a if a['observation_id']=='left');d=next(d for d in self.decisions if d['observation_id']=='left');r=next(r for r in self.routes if r['observation_id']=='left');left['comparison_status']=d['comparison_status']=r['comparison_status']='source_series_only';d['join_segment_id']=None;self.edges[0]['drawable']=False;self.edges[0]['comparison_status']='unresolved';self.edges[0]['reasons']=v.phase2_engine.compare(left,next(a for a in self.a if a['observation_id']=='right'))['reasons'];self.check();self.edges=[{'edge_id':'bad','profile_id':self.profile,'left_record_key':'canonical:left','right_record_key':'canonical:right','comparison_group_id':'original-group','drawable':True,'comparison_status':'published_panel_limited','reasons':[],'period_left':[2022,None],'period_right':[2023,None]}]
  with self.assertRaisesRegex(ValueError,'upgraded into trend'):self.check()
 def test_gap_and_cross_original_group_never_drawable(self):
  for oid in ('zero','after-gap'):
   next(a for a in self.a if a['observation_id']==oid)['comparison_group_id']='original-group';next(r for r in self.routes if r['observation_id']==oid)['comparison_group_id']='original-group';next(d for d in self.decisions if d['observation_id']==oid)['comparison_group_id']='original-group';next(d for d in self.decisions if d['observation_id']==oid)['join_segment_id']='original-group'
  edge=self.edges[0];edge.update(left_record_key='canonical:zero',right_record_key='canonical:after-gap',period_left=[2018,None],period_right=[2020,None])
  with self.assertRaisesRegex(ValueError,'bridges a gap'):self.check()
  next(a for a in self.a if a['observation_id']=='after-gap')['comparison_group_id']='other';next(r for r in self.routes if r['observation_id']=='after-gap')['comparison_group_id']='other';next(d for d in self.decisions if d['observation_id']=='after-gap')['comparison_group_id']='other';next(d for d in self.decisions if d['observation_id']=='after-gap')['join_segment_id']='other'
  with self.assertRaisesRegex(ValueError,'crosses original'):self.check()
 def test_wrong_edge_date_and_phase2_compare_refusal(self):
  self.edges[0]['period_right']=[2024,None]
  with self.assertRaisesRegex(ValueError,'right period'):self.check()
  self.edges[0]['period_right']=[2023,None];next(a for a in self.a if a['observation_id']=='right')['reasons']=['source_definition_unresolved']
  with self.assertRaisesRegex(ValueError,'compare refuses'):self.check()
 def test_qualified_edge_cannot_be_silently_suppressed(self):
  self.edges[0]['drawable']=False
  with self.assertRaisesRegex(ValueError,'drawable state differs'):self.check()
 def test_missingness_is_never_a_priority_ranking_dimension(self):
  v.assert_priority_choice(['new-missing-panel'],{'new-missing-panel':0,'old-populated-panel':1})
  with self.assertRaisesRegex(ValueError,'priority changed'):v.assert_priority_choice(['old-populated-panel'],{'new-missing-panel':0,'old-populated-panel':1})
  with self.assertRaisesRegex(ValueError,'ambiguous'):v.assert_priority_choice(['one'],{'one':0,'two':0})
 def test_month_adjacency_is_literal_not_guessed(self):
  self.assertEqual(v.period_index({'comparison_year':2024,'comparison_month':12,'period_kind':'monthly_source_statistic'})+1,v.period_index({'comparison_year':2025,'comparison_month':1,'period_kind':'monthly_source_statistic'}));self.assertIsNone(v.period_index({'comparison_year':2024,'comparison_month':13,'period_kind':'monthly_source_statistic'}));self.assertIsNone(v.period_index({'comparison_year':None,'comparison_month':None,'period_kind':'programme_not_annual'}))
 def test_sparse_json_and_text_sql_do_not_conflate_empty_null_zero(self):
  v.compare_formats([{'x':0,'note':''},{'x':None}],['x','note'],[{'x':'0','note':''},{'x':'','note':''}],['x','note'],[{'x':'0','note':''},{'x':None,'note':None}],'synthetic')
  with self.assertRaisesRegex(ValueError,'SQLite value'):v.compare_formats([{'x':None}],['x'],[{'x':''}],['x'],[{'x':'0'}],'synthetic')


class ProducerPolicyCounterexamples(unittest.TestCase):
 def setUp(self):
  import phase3_engine
  self.engine=phase3_engine;self.a=[];self.profile={'id':'synthetic-panel','title':'Synthetic original panel','description':'fixture','selection_mode':'latest_original_panel','default_purpose':'trend','period_requirement':'annual','candidate_filter':{'layer':'canonical','indicators':['館藏冊數']},'priority_rule':'newest qualified original edition, never a value-based rank'}
  for source,edition,letter in [('old',114,'a'),('new',115,'c')]:
   for base in annotations()[-2:]:
    a=copy.deepcopy(base);name=base['observation_id'];a.update(record_key='canonical:'+source+'-'+name,observation_id=source+'-'+name,source_id=source,source_sha256=letter*64,source_version_id=source+'@sha256:'+letter*64,source_edition_raw=edition,evidence_id='e-'+source,comparison_group_id='g-'+source);self.a.append(a)
  self.policy={'policy_version':'test1','profiles':[self.profile],'reviewed_sources':[{'layer':'canonical','source_id':s,'source_sha256':letter*64,'source_family':'fixture','evidence_ids':['e-'+s]} for s,letter in [('old','a'),('new','c')]],'no_value_based_ranking':True,'unreviewed_source_versions_require_review':True,'reviewed_panel_record_keys':[a['record_key'] for a in self.a]}
  original=json.loads((Path(__file__).resolve().parents[1]/'docs/phase3-contract.json').read_text());self.contract={**original,'profiles':['synthetic-panel']}
 def select(self,**kwargs):return self.engine.select(self.policy,self.a,'synthetic-panel',**kwargs)
 def test_newer_qualified_missing_panel_keeps_priority(self):
  for a in self.a:
   if a['source_id']=='new':a.update(original_value=None,raw_value='',value_status='source_blank',comparison_value=None,comparison_status='unresolved',reasons=['original_value_missing_marker_or_unresolved_do_not_impute'])
  result=self.select();selected=[d for d in result['decisions'] if d['selected']];self.assertEqual(len(selected),2);self.assertEqual({d['source_id'] for d in selected},{'new'});self.assertTrue(all(d['selection_status']=='selected_source_missing' for d in selected));routes=self.engine.route_records(self.a,self.policy);v.validate_rows(routes,result['decisions'],[result['query']],result['edges'],self.a,self.contract);v.validate_policy_bindings(routes,result['decisions'],[result['query']],self.a,self.policy,self.contract)
 def test_newer_definition_conflict_cannot_overrule_older_qualified_panel_or_pin(self):
  for a in self.a:
   if a['source_id']=='new':a.update(comparison_status='unresolved',reasons=['source_definition_or_effective_year_unresolved'])
  selected=[d for d in self.select()['decisions'] if d['selected']];self.assertEqual({d['source_id'] for d in selected},{'old'});pinned=self.select(source_id='new');self.assertFalse(pinned['query']['selected_record_keys']);self.assertEqual({d['source_id'] for d in pinned['decisions']},{'new'})
 def test_no_cross_panel_range_splice(self):
  for a in self.a:
   if a['source_id']=='old':a['comparison_year']-=2
  result=self.select(start_year=2020,end_year=2023);self.assertFalse(result['query']['selected_record_keys']);self.assertTrue(all(not e['drawable'] for e in result['edges']))
 def test_equal_priority_remains_ambiguous_even_when_values_match(self):
  for a in self.a:a['source_edition_raw']=114
  result=self.select();self.assertFalse(result['query']['selected_record_keys']);self.assertEqual(result['query']['selection_status'],'unresolved')
 def test_new_source_sha_requires_review(self):
  for a in self.a:
   if a['source_id']=='new':a['source_sha256']='d'*64
  result=self.select();self.assertFalse(result['query']['selected_record_keys']);self.assertTrue(any(d['selection_status']=='blocked_source_version' for d in result['decisions']))


 def test_changed_evidence_body_cannot_reuse_same_id_and_source_sha(self):
  self.policy['evidence_bindings']={'e-old':'old-card-digest','e-new':'new-card-digest'};current={'e-old':'old-card-digest','e-new':'changed-new-card-digest'};self.policy['_current_evidence_digests']=current;result=self.select();self.assertFalse(result['query']['selected_record_keys']);routes=self.engine.route_records(self.a,self.policy);self.assertTrue(all(not r['source_version_reviewed'] for r in routes if r['source_id']=='new'));v.validate_policy_bindings(routes,result['decisions'],[result['query']],self.a,self.policy,self.contract,current)
  for r in routes:
   if r['source_id']=='new':r['source_version_reviewed']=True;r['route_status']='registered_profile_candidate'
  with self.assertRaisesRegex(ValueError,'Unreviewed source'):v.validate_policy_bindings(routes,result['decisions'],[result['query']],self.a,self.policy,self.contract,current)
 def test_literal_facet_paths_and_json_types_are_exact(self):
  with self.assertRaises(ValueError):self.select(facets={'classification_dimensions.not_present':None})
  for a in self.a:a['facets']['classification_dimensions']={'flag':False}
  self.assertEqual(self.select(facets={'classification_dimensions.flag':0})['query']['candidate_records'],0);self.assertEqual(self.select(facets={'classification_dimensions.flag':False})['query']['candidate_records'],4)

class UpdateSafety(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.calls=[];self.sig={'layer_raw_fingerprints':{'canonical':'same-statistics'},'phase2_content_sha256':'same-phase2','policy_and_code_hashes':{'policy':'approved'}}
  self.put('scripts/build_phase3.py','# fixture');self.put('README.md','before');self.put('docs/phase3-contract.json','original policy input')
  for name in u.PRIOR_STATES:self.put(name,json.dumps({'inputs':{'original-source':'unchanged'},'outputs':{'README.md':sha(b'before')}}))
 def put(self,name,body):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body.encode() if isinstance(body,str) else body)
 def execute(self,name,*args):
  self.calls.append(name)
  if name=='build_phase3.py':
   for name in ('record_routes.jsonl.gz','candidate_decisions.jsonl.gz','queries.jsonl','series_edges.jsonl'):self.put('derived/phase3/'+name,gzip.compress(b'{}\n',mtime=0) if name.endswith('.gz') else b'{}\n')
   self.put('derived/phase3/selection.sqlite',b'fixture');self.put('docs/phase3-summary.json','{}')
  if name=='build_phase3_documentation.py':self.put('README.md','after phase3')
 def snapshots(self):return {str(p.relative_to(self.root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in [*u.output_paths(self.root),*(self.root/name for name in [*u.PRIOR_STATES,'data/phase3_update_state.json'])] if p.is_file()}

 def test_local_chart_helpers_are_signature_dependencies_without_execution(self):
  for name in u.CODE:self.put('scripts/'+name,'# fixture code')
  self.put('scripts/build_phase3_reader.py','import phase3_charts\n');self.put('scripts/phase3_charts.py','import phase3_chart_math\n');self.put('scripts/phase3_chart_math.py','raise RuntimeError("must only parse, never import")\n')
  names=u.local_code_dependencies(self.root);self.assertIn('scripts/phase3_charts.py',names);self.assertIn('scripts/phase3_chart_math.py',names);before={name:u.digest(self.root/name) for name in names};self.put('scripts/phase3_chart_math.py','# corrected plotting logic\n');self.assertNotEqual(before,{name:u.digest(self.root/name) for name in u.local_code_dependencies(self.root)})

 def test_order_then_noop_and_prior_inputs_untouched(self):
  with mock.patch.object(u,'input_signature',side_effect=lambda root:copy.deepcopy(self.sig)):
   u.run(self.root,self.execute);self.assertEqual(self.calls,[*u.STAGES,'validate_phase3.py']);before=self.snapshots();self.calls.clear();result=u.run(self.root,self.execute);self.assertFalse(result['rebuilt']);self.assertEqual(self.calls,['validate_phase3.py']);self.assertEqual(before,self.snapshots())
  for name in u.PRIOR_STATES:self.assertEqual(json.loads((self.root/name).read_text())['inputs'],{'original-source':'unchanged'})
 def test_failure_restores_all_bytes_mtime_and_both_earlier_states(self):
  with mock.patch.object(u,'input_signature',side_effect=lambda root:copy.deepcopy(self.sig)):
   u.run(self.root,self.execute);before=self.snapshots();self.sig['policy_and_code_hashes']['policy']='reviewed new policy'
   def fail(name,*args):self.execute(name,*args);self.put('docs/phase3-contract.json','new input must not be rolled back');raise RuntimeError('synthetic failure')
   with self.assertRaisesRegex(RuntimeError,'synthetic'):u.run(self.root,fail)
   self.assertEqual(before,self.snapshots());self.assertEqual((self.root/'docs/phase3-contract.json').read_text(),'new input must not be rolled back')
 def test_missing_input_does_not_invoke_any_builder(self):
  before=self.snapshots()
  with mock.patch.object(u,'input_signature',side_effect=FileNotFoundError('missing approved input')):
   with self.assertRaises(FileNotFoundError):u.run(self.root,self.execute)
  self.assertEqual(before,self.snapshots());self.assertFalse(self.calls)
 def test_code_only_change_is_not_raw_statistical_change(self):
  with mock.patch.object(u,'input_signature',side_effect=lambda root:copy.deepcopy(self.sig)):
   u.run(self.root,self.execute);old=u.content_digest(self.root);self.sig['policy_and_code_hashes']['policy']='new code same facts';result=u.run(self.root,self.execute);self.assertFalse(result['source_statistics_changed']);self.assertEqual(old,u.content_digest(self.root))

if __name__=='__main__':unittest.main()
