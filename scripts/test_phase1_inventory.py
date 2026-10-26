import unittest
from build_phase1_inventory import (authority_and_candidate_rows,discovery_matrix,geography_uncertain,profile_rows,quantity_role,temporal_resolution,topics_for)
class Phase1InventoryTests(unittest.TestCase):
 def row(self,**extra):
  return {'observation_id':'a','source_id':'source-a','source_family':'source-facts','series_id':'series-a','data_year':2012,'geography':'臺南市','geographic_scope':'county_source','indicator':'借閱冊數','indicator_group':'','source_field':'借閱冊數','value':1,'value_status':'reported','unit':'冊次','source_url':'https://example.gov.tw/table','source_sha256':'a'*64,'temporal_kind':'flow_calendar_year',**extra}
 def scope(self):return {'years':{'first':2012,'last':2012},'current_county_navigation':['臺南市','新北市'],'topics':[{'id':'loan_volumes','label':'借閱冊數'}]}
 def cells(self,rows):return discovery_matrix(rows,profile_rows(rows),self.scope(),[])
 def test_original_per_capita_cannot_fill_original_quantity_gap(self):
  r=self.row(indicator='每人借閱冊數',source_field='每人借閱冊數',unit='冊／人');self.assertIn('ratio',quantity_role(r));self.assertFalse(any(x['matched_source_observations'] for x in self.cells([r])))
 def test_raw_county_not_reassigned_to_current_name(self):
  r=self.row(geography='臺北縣');self.assertFalse(any(x['matched_source_observations'] for x in self.cells([r])));self.assertEqual(profile_rows([r])[0]['geography'],'臺北縣')
 def test_uncertain_geography_does_not_become_confirmed_value(self):
  r=self.row(geographic_scope='county_source_label_uncertain');self.assertTrue(geography_uncertain(r));cell=next(x for x in self.cells([r]) if x['navigation_region_current_name']=='臺南市');self.assertEqual(cell['confirmed_label_value_records'],0);self.assertEqual(cell['unconfirmed_geography_records'],1)
 def test_unit_or_period_uncertainty_not_geography_uncertainty(self):
  for flag in ('source_heading_body_counting_unit_conflict_unresolved','source_period_punctuation_unresolved','population_scope_unresolved'):
   self.assertFalse(geography_uncertain(self.row(quality_flags=flag,entity_label_status='printed_source_label_retained')))
 def test_source_marker_not_counted_as_numeric_or_zero(self):
  r=self.row(value=None,raw_value='未統計',value_status='source_marker');p=profile_rows([r])[0];self.assertEqual(p['nonmissing_value_records'],0);self.assertEqual(p['reported_zero_records'],0);self.assertEqual(p['null_status_counts'],{'source_marker':1})
 def test_reported_zero_retained_without_certification(self):
  p=profile_rows([self.row(value=0)])[0];self.assertEqual(p['nonmissing_value_records'],1);self.assertEqual(p['reported_zero_records'],1);self.assertEqual(p['compatibility_status'],'not_certified_by_phase1_inventory')
 def test_monthly_data_not_called_annual(self):
  r=self.row(temporal_kind='source_period_月',periodicity_raw='月');self.assertEqual(temporal_resolution(r),'monthly_source_not_annual_total');cell=next(x for x in self.cells([r]) if x['matched_source_observations']);self.assertEqual(cell['temporal_resolution_counts'],{'monthly_source_not_annual_total':1})
 def test_population_and_source_keep_profiles_separate(self):
  a=self.row();b=self.row(observation_id='b',national_libraries_scope='excludes_national');c=self.row(observation_id='c',source_id='source-c');self.assertEqual(len(profile_rows([a,b,c])),3)
 def test_budget_not_classified_as_book_holdings(self):
  topics=topics_for(self.row(indicator='圖書(決算)',source_field='圖書(決算)'));self.assertIn('purchase_expenditure',topics);self.assertNotIn('holdings',topics)
 def test_reservations_are_not_loans(self):
  r=self.row(indicator='預約冊數',source_field='預約冊數');self.assertNotIn('loan_volumes',topics_for(r));self.assertEqual(quantity_role(r),'other_original_statistic_outside_ten_topics')
 def test_book_loans_do_not_fill_holdings(self):
  r=self.row(indicator='圖書借閱冊數',source_field='圖書借閱冊數');self.assertIn('loan_volumes',topics_for(r));self.assertNotIn('holdings',topics_for(r))
 def test_explicit_derived_ratio_not_population_quantity(self):
  r=self.row(indicator='服務人口（A/B）',source_field='服務人口（A/B）',temporal_kind='derived_ratio');self.assertEqual(quantity_role(r),'ratio_or_per_capita_not_original_quantity')
 def test_operating_cost_not_book_purchase_cost(self):
  for i in ('營運總經費','資本門','經常門'):
   r=self.row(indicator=i,source_field=i,indicator_group='圖書館營運經費');self.assertNotIn('purchase_expenditure',topics_for(r))
 def test_financial_subperiod_not_calendar_year(self):
  self.assertEqual(temporal_resolution(self.row(temporal_kind='annual_financial',period_basis='source_printed_subperiod')),'partial_or_programme_period')
  self.assertEqual(temporal_resolution(self.row(temporal_kind='annual_financial',period_basis='unresolved_candidate_dates')),'time_basis_unconfirmed')
 def test_all_ids_remain_in_profiles(self):
  rows=[self.row(observation_id=str(i),value=i) for i in range(5)];profiles=profile_rows(rows);self.assertEqual(sorted(x for p in profiles for x in p['observation_ids']),['0','1','2','3','4'])
 def test_temporal_and_edition_are_not_implicitly_joined(self):
  a=self.row(source_edition='95');b=self.row(observation_id='b',source_edition='96');c=self.row(observation_id='c',temporal_kind='source_period_月');self.assertEqual(len(profile_rows([a,b,c])),3)
if __name__=='__main__':unittest.main()
