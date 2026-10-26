import copy,unittest,xml.etree.ElementTree as ET
from series_charts import chart,svg
def point(year,value,key=None,month=None,status='published_panel_limited'):
 return {'record_key':key or str(year)+str(month),'comparison_group_id':'group','comparison_year':year,'comparison_month':month,'period_kind':'monthly_source_statistic' if month is not None else 'annual_flow_source','comparison_value':None if value is None else str(value),'original_value':value,'raw_value':'-' if value is None else str(value),'comparison_unit':'冊次','comparison_status':status,'reasons':['original_value_missing_marker_or_unresolved_do_not_impute'] if value is None else [],'facets':{'entity':'原地名','facility_or_reader_category':'原館藏地','unit':'冊次','period_kind':'monthly_source_statistic' if month is not None else 'annual_flow_source'},'raw_indicator':'原借閱冊數','source_id':'fixture','source_sha256':'a'*64,'source_url':'https://example.invalid/original.pdf#page=2','source_locator':'原頁2；格B3','source_version_id':'fixture@'+('a'*64),'source_edition_raw':114,'value_status':'source_blank' if value is None else 'reported','zero_interpretation':'source_reported_zero_not_certified_measured_zero' if value==0 else None}
class SourceCharts(unittest.TestCase):
 def test_adjacent_original_points(self):
  c=chart([point(2020,1),point(2021,2)]);self.assertEqual(c['drawable_segments'],1);ET.fromstring(c['svg'])
 def test_missing_year_is_not_interpolated(self):
  c=chart([point(2020,1),point(2022,2)]);self.assertEqual(c['drawable_segments'],0)
 def test_null_original_breaks_line(self):
  c=chart([point(2020,1),point(2021,None,status='unresolved'),point(2022,2)]);self.assertEqual((c['plotted_points'],c['drawable_segments'],len(c['omitted_points'])),(2,0,1))
 def test_original_zero_keeps_interpretation(self):
  c=chart([point(2020,0),point(2021,2)]);p=c['source_points'][0];self.assertEqual(p['comparison_value'],'0');self.assertIn('not_certified',p['zero_interpretation'])
 def test_source_series_only_is_points_without_lines(self):
  a=[point(2020,1,status='source_series_only'),point(2021,2,status='source_series_only')];c=chart(a,values={p['record_key']:p['comparison_value'] for p in a});self.assertEqual((c['plotted_points'],c['drawable_segments']),(2,0))
 def test_p2_default_never_upgrades_source_series(self):
  self.assertIsNone(chart([point(2020,1,status='source_series_only')]))
 def test_explicit_edge_permission_required(self):
  a=[point(2020,1),point(2021,2)];self.assertEqual(chart(a,allowed_edges=set())['drawable_segments'],0)
 def test_reversed_edge_does_not_authorize_line(self):
  a=[point(2020,1),point(2021,2)];self.assertEqual(chart(a,allowed_edges={(a[1]['record_key'],a[0]['record_key'])})['drawable_segments'],0)
 def test_source_url_sha_locator_unchanged(self):
  a=point(2020,2);p=chart([a])['source_points'][0]
  for k in ('source_url','source_sha256','source_locator','source_version_id','raw_value'):self.assertEqual(p[k],a[k])
 def test_duplicate_period_same_value_is_ambiguous(self):
  self.assertIsNone(chart([point(2020,1,'a'),point(2020,1,'b')]))
 def test_different_original_group_rejected(self):
  a,b=point(2020,1),point(2021,2);b['comparison_group_id']='other'
  with self.assertRaises(ValueError):chart([a,b])
 def test_unknown_unit_not_normalized(self):
  a=point(2020,2);a['comparison_unit']=None;self.assertIsNone(chart([a]))
 def test_unknown_year_not_guessed(self):
  a=point(None,2);self.assertIsNone(chart([a]))
 def test_month_boundary_uses_calendar(self):
  c=chart([point(2020,1,month=12),point(2021,2,month=1)]);self.assertEqual(c['drawable_segments'],1)
 def test_missing_month_no_line(self):
  c=chart([point(2020,1,month=1),point(2020,2,month=3)]);self.assertEqual(c['drawable_segments'],0)
 def test_invalid_month_not_a_year_point(self):
  self.assertIsNone(chart([point(2020,1,month=0)]))
 def test_display_filter_never_connects_hidden_point(self):
  c=chart([point(2020,1),point(2021,2),point(2022,3)]);visible=svg(c,2021,2022);self.assertEqual(visible.count('<circle'),2);self.assertEqual(visible.count('stroke="#226758"'),1)
 def test_unusable_zero_display_remains_missing(self):
  a,b=point(2020,1),point(2021,0);b['comparison_status']='unresolved';b['comparison_value']=None;b['original_value']=None;b['raw_value']='-';b['value_status']='source_display_typed_value_conflict_unresolved';c=chart([a,b]);self.assertEqual((c['plotted_points'],c['drawable_segments']),(1,0));self.assertEqual(c['omitted_points'][0]['value_status'],b['value_status'])
 def test_non_http_source_not_injected(self):
  a=point(2020,1);a['source_url']='javascript:alert(1)';a['raw_value']='<script>';c=chart([a]);self.assertNotIn('<script>',c['svg']);self.assertNotIn('href="javascript:',c['svg'])
if __name__=='__main__':unittest.main()
