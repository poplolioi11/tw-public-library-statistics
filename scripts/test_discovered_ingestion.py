#!/usr/bin/env python3
"""Counterexamples for literal periods, source markers and source-cell identity."""
import copy, json, tempfile, unittest
from pathlib import Path
from build_discovered_20261028 import adapt, run
import phase2_engine as p2


def fixture():
    c={'cell_id':'source-cell-one','source_document_id':'example-official-table','source_sha256':'a'*64,
       'source_version_id':'example@sha256:'+'a'*64,'source_table':'1','source_table_title':'原刊表',
       'source_row':'1','source_column':'1','source_locator':'PDF page 1; row 1; column 1',
       'source_url':'https://example.gov.tw/statistics.pdf#page=1','source_pdf_page':1,'source_printed_page':'1',
       'row_label_raw':'110年','column_label_raw':'原刊借閱冊數','entity_raw':'甲縣','entity_kind':'county_original',
       'data_year':2021,'metric_id':'loans','metric_raw':'原刊借閱冊數','value_raw':'12','value':'12',
       'value_status':'reported','unit':'冊','unit_raw':'冊','unit_status':'source_heading',
       'period_raw':'110年','period_status':'explicit_original_year','temporal_kind':'flow_source_year',
       'population_scope':'原刊公共館','national_libraries_scope':'unknown','geography_vintage':'原刊界線',
       'aggregation_role':'source_component','source_notes':[],'quality_flags':[],
       'independent_check':{'matched':True,'method':'test_fixture'}}
    d={'candidate_id':'example-official-table','retrieved_at':'2026-10-28T00:00:00+00:00',
       'official_url':'https://example.gov.tw/statistics.pdf','source_local_path':'raw/example.pdf','edition_raw':'110年'}
    return c,d


class LiteralIngestion(unittest.TestCase):
    def test_unknown_year_does_not_become_publication_year_or_zero(self):
        c,d=fixture();c.update(data_year=None,period_status='year_not_printed',period_raw='同表區別列')
        r=adapt(c,d)
        self.assertIsNone(r['data_year']);self.assertIsNone(r['period_effective'])
        self.assertIsNone(r['period_start']);self.assertIsNone(r['period_end'])
        self.assertEqual(r['value'],12)

    def test_marker_cannot_be_promoted_to_zero(self):
        for raw in ('-','…','...','未統計'):
            c,d=fixture();c.update(value='0',value_raw=raw)
            with self.assertRaises(ValueError):adapt(c,d)

    def test_literal_zero_and_source_blank_are_different(self):
        c,d=fixture();c.update(value='0',value_raw='0');r=adapt(c,d)
        self.assertEqual(r['value'],0);self.assertIsNotNone(r['zero_interpretation'])
        c.update(value=None,value_raw='',value_status='source_blank');r=adapt(c,d)
        self.assertIsNone(r['value']);self.assertEqual(r['raw_value'],'')

    def test_shared_cell_kept_once_with_complete_scope(self):
        c,d=fixture();c.update(entity_raw='甲館及乙館',merged_cell_scope={'entities':['甲館','乙館']})
        r=adapt(c,d);self.assertEqual(r['geography'],'甲館及乙館')
        self.assertEqual(json.loads(r['source_time_reference'])['merged_cell_scope'],c['merged_cell_scope'])

    def test_weekly_visits_do_not_gain_an_annual_period(self):
        c,d=fixture();c.update(temporal_kind='source_reported_weekly_quantity',unit='人次/週',unit_raw='每週80人次',value='80',value_raw='每週80人次')
        r=adapt(c,d);a=p2.period_info(r,'canonical',{'reviewed_original':True})
        self.assertEqual(r['periodicity_raw'],'每週');self.assertIsNone(r['period_effective'])
        self.assertIsNone(a['comparison_year']);self.assertEqual(a['period_kind'],'weekly_source_quantity')

    def test_annual_flow_cannot_be_declared_monthly(self):
        c,d=fixture();c['data_month']=12
        with self.assertRaises(ValueError):adapt(c,d)

    def test_month_and_annual_total_have_separate_series(self):
        c,d=fixture();annual=adapt(c,d);c.update(data_month=12,temporal_kind='flow_source_month');month=adapt(c,d)
        self.assertNotEqual(annual['series_id'],month['series_id'])
        self.assertEqual(month['period_effective'],'2021-12')

    def test_entities_have_distinct_series_but_value_does_not_change_identity(self):
        c,d=fixture();a=adapt(c,d);c.update(value='13',value_raw='13');b=adapt(c,d)
        self.assertEqual(a['series_id'],b['series_id']);self.assertEqual(a['observation_id'],b['observation_id'])
        c['entity_raw']='乙縣';self.assertNotEqual(a['series_id'],adapt(c,d)['series_id'])

    def test_decimal_conversion_must_be_exact(self):
        c,d=fixture();c.update(value='0.100000000000000001',value_raw='0.100000000000000001')
        with self.assertRaises(ValueError):adapt(c,d)

    def test_source_roc_year_must_be_explicitly_converted_upstream(self):
        c,d=fixture();c['data_year']=110
        with self.assertRaises(ValueError):adapt(c,d)

    def test_formula_and_denominator_remain_source_facts(self):
        c,d=fixture();c.update(source_formula_raw='(B)/(C)*100',source_formula_denominator_raw='人口')
        r=adapt(c,d);context=json.loads(r['source_time_reference'])
        self.assertEqual(context['source_formula_denominator_raw'],'人口')
        self.assertEqual(context['source_formula_raw'],'(B)/(C)*100')

    def test_monthly_ratio_keeps_month_and_is_never_an_original_count(self):
        c,d=fixture();c.update(data_year=2012,data_month=2,temporal_kind='source_month_ratio',metric_raw='借閱率',unit='%',unit_raw='%',value='3.75',value_raw='3.75')
        r=adapt(c,d)
        card={'evidence_id':'reviewed-example','reviewed_original':True,'supported_comparison_scope':{'status':'published_panel_limited','panel_id':'same-original'}}
        a=p2.annotate('canonical',r,card)
        self.assertEqual(a['measure_class'],'ratio_or_per_capita')
        self.assertEqual((a['comparison_year'],a['comparison_month']),(2012,2))
        self.assertEqual(a['period_kind'],'monthly_source_statistic')


if __name__=='__main__':unittest.main(verbosity=2)
