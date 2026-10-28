#!/usr/bin/env python3
"""Independent real-ID adapters; preserve the engine-unseen phase3 fixture."""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import phase2_engine as p2
import phase3_engine as p3
import record_io

FIXTURE = 'research/phase3-source-cases.json'
FIXTURE_SHA = '0e263e018589b033fbcc0eea3b4802e59a3c319ea529fe7d7497d3cf27703af6'
FILES = [FIXTURE, 'VERSION', 'data/combined/observations.jsonl',
         'derived/phase1_local_sources_long.jsonl', 'derived/ncl_2005_programmes_long.jsonl',
         'derived/phase2/annotations.jsonl.gz', 'derived/phase2/evidence_cards.jsonl',
         'scripts/phase2_engine.py', 'scripts/phase3_engine.py', 'scripts/select_sources.py',
         'docs/phase3-profiles.json', 'docs/phase3-contract.json', 'scripts/check_phase3_cases.py']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Review:
    def __init__(self, root):
        self.root = root
        self.files = [str(record_io.path_for(root, f).relative_to(root)) if f == 'data/combined/observations.jsonl' else f for f in FILES]
        self.before = {f: digest(root / f) for f in self.files}
        self.fixture = json.loads((root / FIXTURE).read_text())
        self.policy = p3.load_policy(root)
        self.annotations = p3.load_annotations(root)
        self.by_key = {a['record_key']: a for a in self.annotations}
        self.routes = {r['record_key']: r for r in p3.route_records(self.annotations, self.policy)}
        self.profiles = {p['id']: p for p in self.policy['profiles']}
        self.checks = []
        self.cases = []
        self.active = None
        self.answers = {}
        self.limitations = []

    def check(self, name, condition, category='semantic_default_selection', detail=None):
        self.checks.append({'case_id': self.active['case_id'] if self.active else None,
                            'category': category, 'name': name, 'passed': bool(condition),
                            'detail': detail})

    def start(self, number, coverage, limit=None):
        fixture = self.fixture['cases'][number-1]
        self.active = {'case_id': fixture['case_id'], 'title': fixture['title'],
                       'fixed_expected': fixture['expected'],
                       'semantic_coverage': coverage, 'limitations': [limit] if limit else [],
                       'candidate_lookup_checks': [], 'actual_queries': []}
        self.cases.append(self.active)
        for ref in fixture['source_references']:
            a = self.by_key.get(ref['record_key'])
            self.check('real_original_record_resolves:' + ref['record_key'], a is not None,
                       'source_fact_integrity')
            if a is None:
                continue
            comparisons = {
                'observation_id': a['observation_id'] == ref['observation_id'],
                'source_id': a['source_id'] == ref['source_id'],
                'source_sha256': a['source_sha256'] == ref['source_sha256'],
                'source_url': a['source_url'] == ref['source_url'],
                'source_locator': a['source_locator'] == ref['source_locator'],
                'primary_evidence': a['evidence_id'] == ref['p2_evidence_id'],
                'original_value': a['original_value'] == ref['original_value'],
                'raw_indicator': a['raw_indicator'] == ref['raw_indicator'],
                'p2_period': (a['comparison_year'], a['comparison_month']) ==
                             (ref['p2_comparison_year'], ref['p2_comparison_month']),
                'route_retained': ref['record_key'] in self.routes,
            }
            self.check('fixture_original_fields_preserved:' + ref['record_key'],
                       all(comparisons.values()), 'source_fact_integrity', comparisons)
            r = self.routes[ref['record_key']]
            self.active['candidate_lookup_checks'].append({
                'record_key': a['record_key'], 'observation_id': a['observation_id'],
                'source_id': a['source_id'], 'source_url': a['source_url'],
                'source_sha256': a['source_sha256'], 'source_locator': a['source_locator'],
                'evidence_id': a['evidence_id'], 'original_value': a['original_value'],
                'raw_value': a['raw_value'], 'comparison_year': a['comparison_year'],
                'comparison_month': a['comparison_month'], 'comparison_unit': a['comparison_unit'],
                'comparison_status': a['comparison_status'], 'reasons': a['reasons'],
                'raw_indicator': a['raw_indicator'], 'facets': a['facets'],
                'route_status': r['route_status'], 'candidate_profile_ids': r['candidate_profile_ids'],
                'read_method': 'loaded_current_P2_annotation_and_phase3_route; CLI_lookup_separately_tested',
            })
        return fixture

    def refs(self):
        return [self.by_key[k] for k in self.fixture['cases'][int(self.active['case_id'][1:])-1]['candidate_record_keys']]

    def query(self, label, profile, **kwargs):
        answer = p3.select(self.policy, self.annotations, profile, **kwargs)
        self.answers[(self.active['case_id'], label)] = answer
        focused = {a['record_key'] for a in self.refs()}
        selected = [d for d in answer['decisions'] if d['selected']]
        self.active['actual_queries'].append({
            'label': label, 'profile_id': profile, 'parameters': kwargs,
            'query': answer['query'],
            'fixture_decisions': [d for d in answer['decisions'] if d['record_key'] in focused],
            'selected_decisions': selected,
            'edges': answer['edges'],
            'fixture_ids_filtered_before_decisions': sorted(focused - {d['record_key'] for d in answer['decisions']}),
            'candidate_output_semantics': 'Only profile and explicit original filters match decisions; prefiltered original candidates remain in lookup/route, not an automatically reasoned semantic rejection list.',
        })
        for d in answer['decisions']:
            a = self.by_key[d['record_key']]
            self.check('decision_preserves_original:' + d['record_key'],
                       all(d[k] == a[k] for k in ('original_value', 'raw_value', 'source_id',
                           'source_sha256', 'source_url', 'source_locator', 'evidence_id')),
                       'source_fact_integrity')
        self.check('ranking_policy_explicit_and_not_numeric',
                   answer['query']['ranking_never_uses_numeric_values'] and
                   answer['query']['no_cross_source_splice'])
        return answer

    def selected_ids(self, answer):
        return {d['observation_id'] for d in answer['decisions'] if d['selected']}

    def preferred(self, answer, label='selected_exact_fixture_preference'):
        fixture = self.fixture['cases'][int(self.active['case_id'][1:])-1]
        self.check(label, self.selected_ids(answer) == set(fixture['expected']['preferred_observation_ids']),
                   detail={'actual': sorted(self.selected_ids(answer)),
                           'expected': fixture['expected']['preferred_observation_ids']})

    def guard(self, operation):
        x = p2.guard_operation(operation)
        self.check('operation_guard:' + operation,
                   isinstance(x, dict) and x['status'] in ('incompatible', 'unresolved') and
                   x.get('data_modified') is False)
        self.active.setdefault('operation_guards', []).append(x)

    def finish_case(self):
        cid = self.active['case_id']
        tests = [x for x in self.checks if x['case_id'] == cid]
        self.active['assertions'] = len(tests)
        self.active['failed_assertions'] = sum(not t['passed'] for t in tests)
        self.active['tested_checks_status'] = 'PASS' if all(t['passed'] for t in tests) else 'FAIL'


def adapters(r):
    r.start(1, 'registered_semantic_default')
    a = r.query('latest_covering_2019', 'national-ncl-count-panel', purpose='source-facts', start_year=2019, end_year=2019)
    r.preferred(a)
    r.check('all_five_historical_versions_retained', {x['record_key'] for x in r.refs()} <= {d['record_key'] for d in a['decisions']})
    r.check('single_year_has_no_trend_edge', not a['edges']);r.finish_case()

    r.start(2, 'registered_semantic_default')
    a = r.query('seven_years', 'national-ncl-book-loans-panel', purpose='trend', start_year=2018, end_year=2024)
    r.check('no_cross_edition_splice', not r.selected_ids(a) and not a['edges'])
    r.check('all_ten_fixture_options_retained', {x['record_key'] for x in r.refs()} <= {d['record_key'] for d in a['decisions']})
    r.guard('cross-source-splice');r.finish_case()

    r.start(3, 'registered_semantic_default')
    a = r.query('one_five_year_panel', 'national-ncl-book-loans-panel', purpose='trend', start_year=2020, end_year=2024)
    r.preferred(a)
    r.check('only_four_adjacent_limited_edges', len(a['edges']) == 4 and all(e['drawable'] and e['comparison_status'] == 'published_panel_limited' for e in a['edges']))
    r.check('one_source_edition', {d['source_id'] for d in a['decisions'] if d['selected']} == {'ncl-yearbook-114-statistics'})
    r.check('bounded_continuity_summary_not_method_invariance', a['query']['trend_summary']['single_continuous_series'] is True and a['query']['trend_summary']['historical_collection_method_invariance_certified'] is False)
    r.finish_case()

    r.start(4, 'registered_scope_default', 'NCL prose components are preserved through lookup and their own profile, not returned as explicit rejections by the fixed DGBAS profile.')
    a = r.query('county_scope_including_national', 'county-library-count-dgbas', start_year=2012, end_year=2012, entity='臺北市')
    r.preferred(a);r.guard('sum');r.finish_case()

    r.start(5, 'two_registered_scopes_plus_guard', 'The caller chooses which population to quote. No unified natural-language national-library/material/renewal resolver is implemented.')
    rows = r.refs()
    results = []
    for i, (row, profile) in enumerate(zip(rows, ['county-ncl-yearbook-source-facts', 'county-2023-nlpi-default'])):
        results.append(r.query('source_' + str(i), profile, purpose='source-facts', start_year=2023, end_year=2023,
                               entity='臺北市', metric=row['raw_indicator']))
    r.check('both_individual_facts_available', all(row['observation_id'] in r.selected_ids(a) for row, a in zip(rows, results)))
    r.check('neither_single_year_receives_trend_edge', all(not a['edges'] for a in results))
    r.guard('cross-source-splice');r.finish_case()

    r.start(6, 'lookup_plus_scope_guard', 'The original per-capita ratio has no registered original-total default; lookup is a raw quote, not completion of the 2012 total gap.')
    a = r.query('ratio_is_not_county_original_total', 'county-ncl-yearbook-source-facts', start_year=2012, end_year=2012, entity='臺南市', metric='每人擁有公共圖書館館藏冊數')
    target = r.refs()[0]
    d = next(d for d in a['decisions'] if d['record_key'] == target['record_key'])
    r.check('ratio_not_selected_as_original_total', not d['selected'] and d['point_value'] is None)
    r.check('ratio_original_retained', target['original_value'] == '1.41' and target['comparison_unit'] is None)
    r.guard('impute');r.finish_case()

    r.start(7, 'explicit_source_pin_plus_lookup', 'Other editions are outside source_id pin, retained by lookup. They are not in that query decisions list.')
    a = r.query('pinned_missing', 'historical-national-dgbas-source-facts', purpose='source-facts', start_year=2005, end_year=2005, entity='全國', metric='藏書冊數', source_id='dgbas-social-indicators-2005')
    r.preferred(a)
    d = next(d for d in a['decisions'] if d['selected'])
    r.check('missing_pinned_and_not_imputed', d['selection_status'] == 'selected_source_missing' and d['original_value'] is None and d['point_value'] is None)
    r.check('other_editions_have_values_but_do_not_replace_pin', all(x['original_value'] is not None for x in r.refs()[1:]))
    r.finish_case()

    r.start(8, 'explicit_original_facet_filter', 'financial_mode=final_expenditure must be supplied. Filtered budget is preserved by lookup; the engine does not parse arbitrary financial language or automatically emit a rejected-budget explanation.')
    a = r.query('final_account', 'national-2023-nlpi', start_year=2023, end_year=2023, entity='全國', metric='全年購買圖書資料費-決算(元)', facets={'financial_mode':'final_expenditure'})
    preferred = set(r.active['fixed_expected']['preferred_observation_ids'])
    selected = r.selected_ids(a)
    r.check('financial_facet_selects_final_not_budget', selected == preferred)
    r.check('original_budget_and_final_remain_distinct', [x['facets']['financial_mode'] for x in r.refs()] == ['budget','final_expenditure'])
    r.guard('sum');r.finish_case()

    r.start(9, 'operation_guard_plus_original_fact', 'A unique-person request requires the explicit guard; the profile itself returns original 人次 when asked for that original metric.')
    row = r.refs()[0]
    a = r.query('original_visits', 'national-2023-nlpi', start_year=2023, end_year=2023, metric=row['raw_indicator'])
    r.check('visits_not_renamed_people', any(d['observation_id'] == row['observation_id'] and d['point_unit'] == '人次' and d['raw_indicator'] == row['raw_indicator'] for d in a['decisions'] if d['selected']))
    r.guard('infer-unique-people');r.finish_case()

    r.start(10, 'lookup_plus_geography_guard', 'The preferred old-geography ratio remains a source quote; it is excluded from the county original-quantity default. No certified boundary conversion or current-city substitution is implemented.')
    old, new = r.refs()
    r.check('old_and_reorganized_geographies_preserved', old['facets']['entity'] == '臺北縣' and new['facets']['entity'] == '新北市' and old['facets']['geographic_scope'] != new['facets']['geographic_scope'])
    a = r.query('no_old_ratio_as_modern_original_quantity', 'county-ncl-yearbook-source-facts', start_year=2009, end_year=2009, entity='臺北縣', metric=old['raw_indicator'])
    r.check('old_raw_ratio_not_promoted', all(not d['selected'] for d in a['decisions']))
    r.guard('recode-geography');r.finish_case()

    r.start(11, 'lookup_integrity_only', 'Both actual records have an excluding-national alternative scope without a registered default profile. Identity preservation is tested; no equal-value semantic resolver is claimed.')
    left, right = r.refs()
    r.check('equal_values_distinct_indicators_and_ids', left['original_value'] == right['original_value'] and left['raw_indicator'] != right['raw_indicator'] and left['record_key'] != right['record_key'])
    r.check('routes_retain_both_without_default', all(x['record_key'] in r.routes and r.routes[x['record_key']]['route_status'] == 'no_default_profile_for_original_scope' for x in (left,right)))
    r.finish_case()

    r.start(12, 'explicit_original_month_facility_metric')
    row = r.refs()[0]
    a = r.query('monthly_facility', 'hsinchu-monthly-circulation', start_year=2016, end_year=2016, month=1, facility='新竹市圖書館視聽室', metric='借閱冊數', source_id=row['source_id'])
    r.preferred(a)
    r.check('no_annualization_or_scope_expansion', all(d['period_month'] == 1 and d['period_kind'] == 'monthly_source_statistic' and d['facility_or_reader_category'] == '新竹市圖書館視聽室' for d in a['decisions'] if d['selected']))
    r.guard('sum');r.finish_case()

    r.start(13, 'lookup_only_unregistered_header', 'No semantic default exists for these blank-field source cells. Successful lookup and refusal to relabel are narrower than answering a circulation question.')
    r.check('blank_raw_fields_and_unresolved_period_preserved', all(x['raw_indicator'] == '' and x['comparison_month'] is None and x['comparison_status'] == 'unresolved' for x in r.refs()))
    r.check('no_registered_default_for_unparsed_grid', all(r.routes[x['record_key']]['route_status'] == 'no_default_profile_for_original_scope' for x in r.refs()))
    r.finish_case()

    r.start(14, 'explicit_annual_stock_scope')
    row = r.refs()[0]
    a = r.query('annual_stock', 'lienchiang-explicit-annual-sheet', start_year=2025, end_year=2025, facility='縣立馬祖圖書館', metric='館藏數量(冊)')
    r.preferred(a)
    r.check('annual_reference_not_invented_year_end', all(d['period_year'] == 2025 and d['period_month'] is None and d['period_kind'] == 'annual_source_reference' and d['facets']['measure_class'] == 'collection_stock' for d in a['decisions'] if d['selected']))
    r.finish_case()

    r.start(15, 'registered_period_rejection')
    a = r.query('catalogue_hint_not_formal_2024', 'lienchiang-explicit-annual-sheet', start_year=2024, end_year=2024, source_id='south-lienchiang-opendata-173786', facility='縣立馬祖圖書館', metric='館藏數量(冊)')
    d = next(d for d in a['decisions'] if d['record_key'] == r.refs()[0]['record_key'])
    r.check('undated_not_selected_in_2024', not d['selected'] and d['selection_status'] == 'blocked_period' and d['period_year'] is None)
    r.finish_case()

    r.start(16, 'registered_period_rejection')
    a = r.query('all_original_loan_total_cells', 'hualien-monthly-by-reader', facility='總計', metric='借閱冊數')
    focused = [d for d in a['decisions'] if d['record_key'] in {x['record_key'] for x in r.refs()}]
    r.check('both_period_conflicts_blocked_without_repair', len(focused) == 2 and all(not d['selected'] and d['selection_status'] == 'blocked_period' and d['period_year'] is None and d['period_month'] is None for d in focused))
    r.finish_case()

    r.start(17, 'explicit_original_grid_facets', 'The caller supplies original reader class and full column path. Other axis candidates remain lookup records, not automatically explained semantic alternatives.')
    a = r.query('exact_grid', 'hualien-monthly-by-reader', start_year=2025, end_year=2025, month=12, facility='一般讀者', metric='借閱冊數', facets={'classification_dimensions.column_classification_raw':['借閱冊數','女']})
    r.preferred(a);r.finish_case()

    r.start(18, 'source_status_and_unknown_unit_guards')
    row0, row1 = r.refs()
    r.check('display_conflict_null_reported_zero_retained', row0['original_value'] is None and row1['original_value'] == '0' and row1['comparison_unit'] is None)
    a = r.query('reported_zero_unknown_unit', 'hualien-monthly-by-reader', start_year=2026, end_year=2026, month=2, facility='員工', metric='借閱人數', facets={'classification_dimensions.column_classification_raw':['借閱人數','男']})
    r.preferred(a)
    d = next(d for d in a['decisions'] if d['selected'])
    r.check('unresolved_unit_does_not_make_standardized_zero', d['original_value'] == '0' and d['point_value'] is None and d['point_unit'] is None)
    r.guard('coerce-zero');r.finish_case()

    r.start(19, 'original_metrics_plus_unsupported_operation_guard', 'No net-change calculator exists. The unknown-operation guard is conservative; it is not a full stock-flow accounting implementation.')
    a = r.query('both_original_stock_and_additions', 'lienchiang-explicit-annual-sheet', start_year=2025, end_year=2025, facility='縣立馬祖圖書館')
    target = {x['record_key'] for x in r.refs()}
    focused = [d for d in a['decisions'] if d['record_key'] in target]
    r.check('stock_and_acquisition_not_merged', len(focused) == 2 and all(d['selected'] for d in focused) and {d['facets']['measure_class'] for d in focused} == {'collection_stock','collection_addition'})
    r.guard('net-change-in-holdings');r.guard('sum');r.finish_case()

    r.start(20, 'registered_single_year_source_fact')
    a = r.query('single_year_still_usable', 'county-2023-nlpi-default', start_year=2023, end_year=2023, entity='臺北市', metric='全年圖書資訊借閱冊數')
    r.preferred(a)
    d = next(d for d in a['decisions'] if d['selected'])
    r.check('source_series_fact_point_allowed_no_join_certificate', d['comparison_status'] == 'source_series_only' and d['point_value'] == '12992355' and d['join_segment_id'] is None and not a['edges'])
    r.finish_case()

    r.start(21, 'definition_qualified_trend_selection', 'Definition-sensitive preference is obtained with purpose=trend and an exact original metric. Source-facts purpose may quote the newer unresolved source; it is not a natural-language definition constraint.')
    a = r.query('qualified_borrower_definition', 'historical-national-dgbas-source-facts', purpose='trend', start_year=2005, end_year=2005, metric='圖書借閱人數')
    r.preferred(a)
    d = next(d for d in a['decisions'] if d['selected'])
    r.check('chosen_value_still_2008_publication', d['source_id'] == 'dgbas-social-indicators-2008' and d['original_value'] == 9973 and d['source_edition_raw'] == '2008')
    r.finish_case()

    r.start(22, 'explicit_metric_with_unit_evidence', 'Both tables remain selected original records; table17 has selected_source_unusable/point null. Only table16 is a usable event-count answer, rather than deleting the conflicting original.')
    a = r.query('event_count_with_conflicting_table_retained', 'county-ncl-yearbook-source-facts', start_year=2015, end_year=2015, entity='臺北市', metric='閱讀推廣活動')
    good = set(r.active['fixed_expected']['preferred_observation_ids'])
    usable = {d['observation_id'] for d in a['decisions'] if d['selected'] and d['point_value'] is not None and d['point_unit'] == '場次'}
    r.check('only_table16_usable_as_events', usable == good)
    bad = next(d for d in a['decisions'] if d['observation_id'] == r.refs()[1]['observation_id'])
    r.check('table17_raw_fact_retained_without_unit_repair', bad['original_value'] == 797043 and bad['point_value'] is None and bad['point_unit'] is None)
    r.finish_case()

    r.start(23, 'programme_scope_and_annual_guard')
    a = r.query('programme_quotes', 'programme-source-quantities')
    target = {x['record_key'] for x in r.refs()}
    focus = [d for d in a['decisions'] if d['record_key'] in target]
    r.check('programme_quotes_not_annual_points', len(focus) == 2 and all(d['selected'] and d['period_year'] is None and d['point_value'] is None and d['period_kind'] == 'programme_not_annual' for d in focus))
    r.check('programme_has_no_drawable_annual_edges', not any(e['drawable'] for e in a['edges']))
    try:
        p3.select(r.policy, r.annotations, 'programme-source-quantities', start_year=2005, end_year=2005)
        raised = False
    except ValueError:
        raised = True
    r.check('programme_rejects_annual_filter', raised);r.guard('sum');r.finish_case()

    r.start(24, 'same_source_segment_edges')
    a = r.query('branch_inclusion_break', 'historical-national-dgbas-source-facts', purpose='trend', start_year=1997, end_year=2000, metric='家數', source_id='dgbas-social-indicators-2011')
    r.preferred(a)
    drawable = [e for e in a['edges'] if e['drawable']]
    r.check('only_1998_1999_edge', len(drawable) == 1 and drawable[0]['period_left'] == [1998,None] and drawable[0]['period_right'] == [1999,None])
    r.check('multiple_original_comparison_segments_retained', len({d['comparison_group_id'] for d in a['decisions'] if d['selected']}) == 3)
    r.check('four_year_coverage_explicitly_not_one_continuous_trend', a['query']['trend_summary']['single_continuous_series'] is False and a['query']['trend_summary']['selected_original_comparison_groups'] == 3 and a['query']['trend_summary']['drawable_edges'] == 1)
    r.finish_case()
    r.active = None


def machine_checks(r):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    base = [sys.executable, '-B', str(r.root / 'scripts/select_sources.py'), '--root', str(r.root)]
    samples = [
        ('version_alternatives', ['--profile','national-ncl-count-panel','--purpose','source-facts','--start-year','2019','--end-year','2019']),
        ('pinned_original_missing', ['--profile','historical-national-dgbas-source-facts','--purpose','source-facts','--start-year','2005','--end-year','2005','--metric','藏書冊數','--source-id','dgbas-social-indicators-2005']),
        ('reported_zero_unknown_unit', ['--profile','hualien-monthly-by-reader','--start-year','2026','--end-year','2026','--month','2','--facility','員工','--metric','借閱人數','--facet','classification_dimensions.column_classification_raw=["借閱人數","男"]']),
        ('nested_grid', ['--profile','hualien-monthly-by-reader','--start-year','2025','--end-year','2025','--month','12','--facility','一般讀者','--metric','借閱冊數','--facet','classification_dimensions.column_classification_raw=["借閱冊數","女"]']),
    ]
    for label, fmtargs in samples:
        outputs = {}
        for fmt in ('json','jsonl','csv'):
            process = subprocess.run(base + fmtargs + ['--format',fmt], capture_output=True, text=True, env=env, timeout=40)
            r.check(label + ':CLI_' + fmt + '_exit_zero', process.returncode == 0, 'machine_output', {'exit_code':process.returncode,'stderr':process.stderr[:200]})
            if process.returncode:
                continue
            if fmt == 'json':
                obj = json.loads(process.stdout); rows = obj['decisions']
                r.check(label + ':JSON_query_decisions_edges', set(('query','decisions','edges')) <= set(obj), 'machine_output')
            elif fmt == 'jsonl':
                rows = [json.loads(line) for line in process.stdout.splitlines()]
            else:
                # CSV scalar numbers are strings/empty cells; value_status preserves
                # original missingness. CSV alone does not preserve JSON scalar types.
                rows = list(csv.DictReader(io.StringIO(process.stdout)))
            outputs[fmt] = {row['record_key']:row for row in rows}
        if len(outputs) == 3:
            r.check(label + ':all_three_formats_same_candidate_IDs', set(outputs['json']) == set(outputs['jsonl']) == set(outputs['csv']), 'machine_output')
            r.check(label + ':JSON_JSONL_exact_decision_roundtrip', outputs['json'] == outputs['jsonl'], 'machine_output')
            r.check(label + ':CSV_original_scalar_and_provenance_roundtrip', all(
                all(outputs['csv'][key][field] == ('' if row[field] is None else str(row[field]))
                    for field in ('observation_id','source_id','source_sha256','source_url','source_locator','evidence_id','selection_status','original_value','raw_value','point_value','value_status'))
                for key,row in outputs['json'].items()), 'machine_output')
            r.check(label + ':CSV_nested_facets_and_reasons_roundtrip', all(
                json.loads(outputs['csv'][key]['facets']) == row['facets'] and
                json.loads(outputs['csv'][key]['selection_reasons']) == row['selection_reasons'] and
                json.loads(outputs['csv'][key]['selected']) == row['selected']
                for key,row in outputs['json'].items()), 'machine_output')
            r.check(label + ':CLI_has_original_fact_or_missing_status', any(row['selected'] for row in outputs['json'].values()), 'machine_output')
    r.limitations.append('CSV and JSONL are decision-row exports only; JSON contains query and edges. Full trend permission cannot be reconstructed from CSV/JSONL alone without a matching query/edges file.')

    cli_text = (r.root / 'scripts/select_sources.py').read_text()
    lookup_available = '--lookup' in cli_text
    r.check('CLI_lookup_is_available', lookup_available, 'machine_output')
    if lookup_available:
        wanted = sorted({k for case in r.fixture['cases'] for k in case['candidate_record_keys']})
        # One process per distinct original key, all in background and read only.
        for key in wanted:
            process = subprocess.run(base + ['--lookup',key], capture_output=True, text=True, env=env, timeout=40)
            r.check('CLI_lookup_exit_zero:' + key, process.returncode == 0, 'machine_output')
            if process.returncode:
                continue
            obj = json.loads(process.stdout)
            def find_annotation(value):
                if isinstance(value, dict):
                    if value.get('record_key') == key and 'original_value' in value and 'facets' in value:
                        return value
                    for sub in value.values():
                        found = find_annotation(sub)
                        if found is not None:return found
                if isinstance(value, list):
                    for sub in value:
                        found = find_annotation(sub)
                        if found is not None:return found
                return None
            found = find_annotation(obj)
            source = r.by_key[key]
            r.check('CLI_lookup_original_identity:' + key, found is not None and all(found.get(field) == source[field] for field in ('record_key','source_id','source_sha256','source_url','source_locator','original_value','raw_value','evidence_id','comparison_year','comparison_month','facets')), 'machine_output')
    else:
        r.limitations.append('CLI original-record lookup is not yet implemented in this tested snapshot; internal annotation/route checks are not a substitute for a user-facing lookup capability.')
    for operation in ('infer-unique-people','recode-geography','impute','cross-source-splice','coerce-zero','sum'):
        process = subprocess.run(base + ['--operation',operation], capture_output=True, text=True, env=env, timeout=40)
        obj = json.loads(process.stdout) if process.returncode == 0 else {}
        r.check('CLI_operation_guard:' + operation, process.returncode == 0 and obj.get('data_modified') is False and obj.get('status') in ('unresolved','incompatible'), 'machine_output')


def adversarial(r):
    original = r.answers[('S01','latest_covering_2019')]
    expected_ids = r.selected_ids(original)
    changed = copy.deepcopy(r.annotations)
    for a in changed:
        if a['source_id'].startswith('ncl-yearbook-') and a['facets'].get('entity') == '全國':
            a['original_value'] = None
            a['comparison_value'] = None
            a['value_status'] = 'not_available_in_source'
    result = p3.select(r.policy, changed, 'national-ncl-count-panel', purpose='source-facts', start_year=2019,end_year=2019)
    r.check('in_memory_missingness_does_not_change_version_priority', r.selected_ids(result) == expected_ids, 'adversarial_regression')
    del changed
    bad = copy.deepcopy(next(a for a in r.annotations if a['observation_id'] in expected_ids))
    bad['source_sha256'] = '0'*64
    replacement = [bad if a['record_key'] == bad['record_key'] else a for a in r.annotations]
    result = p3.select(r.policy, replacement, 'national-ncl-count-panel', purpose='source-facts',start_year=2019,end_year=2019)
    r.check('in_memory_unreviewed_source_version_blocks_latest', not r.selected_ids(result) and result['query']['selection_status'] == 'unresolved', 'adversarial_regression')
    changed_policy = copy.deepcopy(r.policy)
    changed_policy['_current_evidence_digests'][bad['evidence_id']] = '0'*64
    result = p3.select(changed_policy, r.annotations, 'national-ncl-count-panel', purpose='source-facts', start_year=2019,end_year=2019)
    r.check('in_memory_changed_P2_evidence_content_blocks_latest', not r.selected_ids(result) and result['query']['selection_status'] == 'unresolved', 'adversarial_regression')
    # A nonexistent nested path currently passes the top-level-only validation when
    # value None is requested; distinguish an API guard gap from a data bug.
    try:
        result = p3.select(r.policy, r.annotations, 'hualien-monthly-by-reader', start_year=2025,end_year=2025,month=12,facets={'classification_dimensions.nonexistent_typo':None})
        rejected = False
        detail = {'query_status':result['query']['selection_status'],'selected_records':result['query']['selected_records']}
    except ValueError as exc:
        rejected = True;detail = {'error':str(exc)}
    r.check('unknown_nested_facet_path_rejected', rejected, 'adversarial_regression', detail)


def write_report(r, final):
    after = {f:digest(r.root/f) for f in r.files}
    stable_inputs = r.before == after
    r.check('all_reviewed_inputs_unchanged_during_run', stable_inputs, 'execution_integrity')
    r.check('engine_unseen_fixture_exact_SHA_unchanged', after[FIXTURE] == FIXTURE_SHA, 'execution_integrity')
    # Fixed cases retain the original review. A later reviewed source batch may
    # advance the current policy, while the exact original baseline stays in
    # the versioned contract and the old source/case hashes are checked above.
    contract=json.loads((r.root/'docs/phase3-contract.json').read_text())
    original_baselines=[b for b in [contract['baseline'],*contract.get('previous_baselines',[])] if b.get('version')=='0.7.0']
    original_fingerprints={'canonical':'d92bb668b333d8ae24ac48362558cf011c8d7f275f1d5f60aec2c7713f702e9e','local_statistical_cells':'2f3b30127fbf12aa743de1e2844a02681e7a967a8cb1efe7cbdc4a7c83e4335f','programme_quantities':'503f2e60d56f34ddbcc7c392cb638e8e535676a7d90097331cf2470931cac662'}
    r.check('fixed_fixture_and_original_review_baseline_0_7_0', r.fixture['fixed_dataset_version']=='0.7.0' and any(b.get('layer_raw_fingerprints')==original_fingerprints for b in original_baselines), 'execution_integrity')
    categories = sorted({x['category'] for x in r.checks})
    counts = {category:{'assertions':sum(x['category']==category for x in r.checks),
                       'failed':sum(x['category']==category and not x['passed'] for x in r.checks)} for category in categories}
    failures = [x for x in r.checks if not x['passed']]
    report = {
        'schema_version':'phase3-engine-independent-review-1.0',
        'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'review_stage':'final_after_parent_freeze' if final else 'preliminary_mutating_engine',
        'dataset_version':(r.root/'VERSION').read_text().strip(),
        'fixed_source_review_baseline':r.fixture['fixed_dataset_version'],
        'seen_phase2':True,'seen_phase3_engine':True,
        'fixture_engine_seen_at_creation':False,'fixture_modified':False,
        'method':'Bundled local Python executed real select calls, CLI exports/lookups/guards and in-memory adversarial tests. No UI, no new network research, no source/P2/public edits. Not human double review.',
        'summary':{'cases':len(r.cases),'distinct_fixture_record_keys':len({k for c in r.fixture['cases'] for k in c['candidate_record_keys']}),
                   'assertions':len(r.checks),'failed_assertions':len(failures),'fixed_inputs_unchanged_during_run':stable_inputs,
                   'all_cases_have_adapters':len(r.cases)==24,
                   'test_status':'PASS' if not failures else 'FAIL',
                   'semantic_scope_note':'PASS applies only to explicit checks. Lookup/guards/explicit filters are separately labeled; they do not certify unimplemented free-text semantic requests.',
                   'by_category':counts},
        'input_sha256_before':r.before,'input_sha256_after':after,
        'cases':r.cases,'assertions':r.checks,'failures':failures,
        'limitations':r.limitations + [
            'No human source double review, unrestricted natural-language parsing, full Taiwan all-year completeness, boundary crosswalk or cross-publication trend equivalence is certified.',
            'Prefiltered candidates are excluded from a narrow API query before decisions. This report retains all fixed candidates via real-ID annotation/route/CLI lookups; that is not an engine-generated refusal explanation for each semantic alternative.',
            'A selected original record may be unusable as a standardized point; source_series_only single-year facts are allowed while join certification remains absent.',
        ]}
    dest=r.root/'research/phase3-engine-review.json'
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    md=['# 第三階段引擎獨立驗收','',
        f"檢查階段：{report['review_stage']}。保留原先未見引擎的24例，fixture SHA未改。",'',
        f"實際執行 {len(r.checks)} 個檢查，失敗 {len(failures)} 個；56個真實候選記錄皆以來源與P2證據定位。",'',
        '單年來源事實、語義預設選源與機器輸出分開驗。只核對lookup或操作guard的案例，不宣稱任意自然語言查詢已實作；不是人類雙校。','',
        '|案例|實測範圍|斷言失敗|','|---|---|---|']
    for c in r.cases:md.append(f"|{c['case_id']} {c['title']}|{c['semantic_coverage']}|{c['failed_assertions']}/{c['assertions']}|")
    md+=['','## 失敗或需補強','']
    md += [f"- {x['name']}：{json.dumps(x.get('detail'),ensure_ascii=False)}" for x in failures] or ['本輪已實測條件未發現失敗。']
    md += ['','## 能力邊界','']
    for c in r.cases:
        for x in c['limitations']:md.append(f"- {c['case_id']}：{x}")
    md += ['- '+x for x in report['limitations']]
    md += ['','重跑：`python -B scripts/check_phase3_cases.py`；root freeze後加 `--final`。完整查詢、原格證據、候選及斷言見同名JSON。',
           '',f"引擎SHA：`{after['scripts/phase3_engine.py']}`",f"政策SHA：`{after['docs/phase3-profiles.json']}`",f"固定案例SHA：`{after[FIXTURE]}`",'']
    (r.root/'research/phase3-engine-review.md').write_text('\n'.join(md))
    print(json.dumps(report['summary'],ensure_ascii=False))
    if failures:print(json.dumps(failures,ensure_ascii=False))
    return 1 if failures else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--final',action='store_true')
    args=parser.parse_args()
    r=Review(args.root)
    adapters(r)
    machine_checks(r)
    adversarial(r)
    return write_report(r,args.final)


if __name__=='__main__':raise SystemExit(main())
