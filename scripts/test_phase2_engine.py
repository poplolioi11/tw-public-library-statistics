import copy,unittest
from phase2_engine import annotate,compare,measure
def row(**kw):
 r={'observation_id':'synthetic-a','source_id':'synthetic-official-panel','source_sha256':'a'*64,'source_url':'https://example.invalid/official.pdf#page=1','source_locator':'synthetic page1/table1/row1','source_table':'1','source_edition':'test-edition','series_id':'same-printed-metric','source_field':'借閱人次','indicator':'借閱人次','data_year':2018,'geography':'全國','geographic_scope':'national_total','geography_vintage':'source2018 reference','population_scope':'printed public-library subset','national_libraries_scope':'printed subset','unit':'人次','unit_status':'printed_unit','temporal_kind':'flow_calendar_year','period_basis':'source_calendar_year_flow','value':7,'raw_value':'7','value_status':'reported','aggregation_role':'published_total','quality_flags':'[]'}
 r.update(kw);return r
def card(**kw):
 c={'evidence_id':'synthetic-card','source_id':'synthetic-official-panel','source_sha256':'a'*64,'reviewed_original':True,'supported_comparison_scope':{'status':'published_panel_limited','panel_id':'same-original-table'}};c.update(kw);return c
class Phase2EngineTests(unittest.TestCase):
 def test_only_same_reviewed_published_panel_is_limited(self):
  a=annotate('canonical',row(),card());b=annotate('canonical',row(observation_id='b',data_year=2019,geography_vintage='source2019 reference'),card());self.assertEqual(compare(a,b)['status'],'published_panel_limited')
 def test_unknown_year_cannot_inherit_panel_year(self):
  a=annotate('canonical',row(data_year=None),card());self.assertEqual(a['comparison_status'],'unresolved');self.assertIsNone(a['comparison_year'])
 def test_direct_checker_has_unknown_year_guard(self):
  a=annotate('canonical',row(),card());b=copy.deepcopy(a);b.update(record_key='canonical:b',comparison_year=None);self.assertEqual(compare(a,b)['status'],'unresolved')
 def test_invalid_month_cannot_be_approved(self):
  r=row(period_year=2020,period_month=13,period_status='matching_sheet_name_and_header_month');a=annotate('local_statistical_cells',r,card());self.assertEqual(a['comparison_status'],'unresolved')
 def test_exact_thousand_scale_uses_decimal(self):
  a=annotate('canonical',row(unit='千冊',value='0.125',raw_value='0.125'),card());self.assertEqual(a['comparison_value'],'125.000');self.assertEqual(a['unit_scale'],'1000')
 def test_reported_zero_survives(self):
  a=annotate('canonical',row(value=0,raw_value='0'),card());self.assertEqual(a['comparison_value'],'0');self.assertIn('not_certified',a['zero_interpretation'])
 def test_display_marker_typed_zero_not_a_final_zero(self):
  a=annotate('local_statistical_cells',row(value=None,value_raw='-',source_typed_numeric_value='0',value_status='source_display_typed_value_conflict_unresolved',period_year=2020,period_month=1,period_status='matching_sheet_name_and_header_month'),card());self.assertIsNone(a['comparison_value']);self.assertEqual(a['comparison_status'],'unresolved')
 def test_blank_is_not_zero(self):
  a=annotate('canonical',row(value=None,raw_value='',value_status='source_blank'),card());self.assertIsNone(a['comparison_value']);self.assertEqual(a['raw_value'],'')
 def test_mixed_units_not_book_volumes(self):
  a=annotate('canonical',row(unit='冊、件'),card());self.assertIsNone(a['comparison_unit']);self.assertIsNone(a['comparison_value'])
 def test_budget_and_final_expenditure_cannot_be_spliced(self):
  a=annotate('canonical',row(indicator='圖書預算',source_field='圖書預算',unit='元'),card());b=annotate('canonical',row(observation_id='b',data_year=2019,indicator='圖書決算',source_field='圖書決算',unit='元'),card());self.assertEqual(compare(a,b)['status'],'incompatible')
 def test_book_volumes_and_visits_differ(self):
  a=annotate('canonical',row(indicator='借閱冊數',source_field='借閱冊數',unit='冊'),card());b=annotate('canonical',row(observation_id='b',data_year=2019),card());self.assertEqual(compare(a,b)['status'],'incompatible')
 def test_current_reference_does_not_certify_old_years(self):
  c=card(supported_comparison_scope={'status':'source_series_only'});a=annotate('canonical',row(period_basis='current_general_rule_historical_applicability_unverified'),c);b=annotate('canonical',row(observation_id='b',data_year=2019,period_basis='current_general_rule_historical_applicability_unverified'),c);self.assertEqual(compare(a,b)['status'],'unresolved')
 def test_catalogue_year_is_not_verified_sheet_year(self):
  a=annotate('local_statistical_cells',row(period_year=2024,period_status='catalog_title_year_only_attachment_undated'),card());self.assertIsNone(a['comparison_year']);self.assertEqual(a['comparison_status'],'unresolved')
 def test_literal_month_and_unit_are_new_layer_only(self):
  r=row(source_family='地方政府開放歷史表',unit=None,unit_status='unconfirmed',period_raw='10512',period_basis='observation_field');before=copy.deepcopy(r);c=card(source_fields=['統計年月','借閱人次']);a=annotate('canonical',r,c);self.assertEqual((a['comparison_year'],a['comparison_month'],a['comparison_unit']),(2016,12,'人次'));self.assertEqual(r,before)
 def test_truncated_month_code_does_not_become_a_year(self):
  r=row(source_family='地方政府開放歷史表',period_raw='105',period_basis='observation_field');a=annotate('canonical',r,card(source_fields=['統計年月']));self.assertEqual(a['period_kind'],'unresolved')
 def test_explicit_annual_field_allows_three_digit_year(self):
  r=row(source_family='地方政府開放歷史表',period_raw='105',period_basis='observation_field');a=annotate('canonical',r,card(source_fields=['年度']));self.assertEqual((a['comparison_year'],a['period_kind']),(2016,'annual_source_reference'))
 def test_programme_reference_year_does_not_become_annual(self):
  a=annotate('programme_quantities',row(data_year=2005),card());self.assertIsNone(a['comparison_year']);self.assertEqual(a['period_kind'],'programme_not_annual')
 def test_different_workbook_grid_does_not_merge(self):
  a=annotate('canonical',row(),card(supported_comparison_scope={'status':'published_panel_limited','require_matching_grid_signature':'one'}));b=annotate('canonical',row(observation_id='b',data_year=2019),card(supported_comparison_scope={'status':'published_panel_limited','require_matching_grid_signature':'two'}));self.assertEqual(compare(a,b)['status'],'unresolved')
 def test_old_county_not_recoded(self):
  a=annotate('canonical',row(geography='臺北縣',geographic_scope='county'),card());b=annotate('canonical',row(observation_id='b',data_year=2019,geography='新北市',geographic_scope='county'),card());self.assertEqual(compare(a,b)['status'],'incompatible')
 def test_independent_record_required(self):
  a=annotate('canonical',row(),card());self.assertEqual(compare(a,a)['status'],'unresolved')
 def test_source_fields_policy_uses_exact_ids(self):
  c=card(field_policies=[{'selector':{'series_ids':['same-printed-metric']},'year_segments':[[2018],[2019]],'unresolved_years':[],'status':'published_panel_limited'}]);a=annotate('canonical',row(),c);b=annotate('canonical',row(observation_id='b',data_year=2019),c);self.assertEqual(compare(a,b)['status'],'incompatible')
 def test_quality_flags_empty_json_is_not_error(self):
  a=annotate('canonical',row(quality_flags='[]'),card());self.assertEqual(a['quality_flags_original'],[]);self.assertEqual(a['comparison_status'],'published_panel_limited')
 def test_response_count_subrow_is_not_a_partial_period(self):
  a=annotate('canonical',row(source_subrow_label_raw='括號填答館數',source_response_notation_kind='responding_libraries'),card());self.assertEqual(a['period_kind'],'annual_flow_source')
 def test_renewal_only_is_explicit(self):
  a=annotate('canonical',row(indicator='續借冊數',source_field='續借冊數',unit='冊'),card());self.assertEqual(a['facets']['renewal_scope'],'explicit_renewal_only')
 def test_public_private_populations_stay_distinct(self):
  a=annotate('canonical',row(ownership_scope='public'),card());b=annotate('canonical',row(observation_id='b',data_year=2019,ownership_scope='private'),card());self.assertEqual(compare(a,b)['status'],'incompatible')
if __name__=='__main__':unittest.main()
