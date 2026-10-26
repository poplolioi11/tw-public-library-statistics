# 第三階段：獨立來源選項案例

固定資料：v0.7.0；seen_phase2=true；seen_phase3_engine=false。

這是引擎出現前的24個真實ID案例與預期條件，不是第三階段引擎已通過的測試報告。單年來源事實可引用，與跨年趨勢可串接，是兩個分開判斷。

|案例|單年用途|跨年判定|候選格數|
|---|---|---|---|
|S01 全國單年：選最新且實際含該年的原刊面板|permitted_as_scoped_source_fact|not_certified|5|
|S02 跨七年不能把兩張五年面板拼成同口徑趨勢|each_published_year_fact_available_with_edition|refuse_automatic_cross_edition_splice|10|
|S03 同一已核五年表可作有限原刊面板比較|permitted_as_scoped_source_fact|published_panel_limited_only|5|
|S04 縣市館數明確要求包含三個國立館|permitted_as_scoped_source_fact|not_certified|3|
|S05 國圖縣市表與國資圖API不可僅依中文近義欄互補|both_original_source_facts_may_be_shown_with_scope|refuse_automatic_population_or_collection_equivalence|2|
|S06 2012人均館藏不能補縣市館藏原量|ratio_source_fact_only_not_requested_total|refuse_imputation_or_ratio_back_calculation|1|
|S07 指定版次的缺值不可被另一版有值偷偷取代|permitted_source_fact_with_reported_missing|no_numeric_trend_point_for_this_missing_cell|3|
|S08 購書預算與決算不是同一數值欄|permitted_as_scoped_source_fact|not_certified|2|
|S09 借閱人次不能回答有多少不重複讀者|original_visit_fact_only_not_unique_people|not_a_unique_person_time_series|1|
|S10 同一歷年資料可有原行政區與官方重編系列|permitted_original_historical_source_fact|no_automatic_old_to_current_boundary_series|2|
|S11 同年同地同單位同數值仍不能視為同指標|both_distinct_source_facts|no_equivalence_or_deduplication_from_numeric_equality|2|
|S12 地方單館單月原格可引用，但不能當全縣年度|permitted_scoped_local_source_cell_with_unknowns|monthly_source_only_no_annual_total|1|
|S13 地方空白表頭不能只按冊單位猜借閱或館藏|raw_grid_cells_only_until_header_evidence_matches|no_semantic_series_from_blank_field_name|2|
|S14 年度館藏原量不等於確定12月31日的快照|permitted_annual_reference_source_stock_fact|stock_series_only_if_matching_reference_basis|1|
|S15 目錄113年不能取代無日期附件的正式統計年|undated_source_fact_with_catalogue_hint_only|refuse_verified_year_placement|1|
|S16 工作表名與表頭月份或四位年字衝突不擇一修正|raw_conflicting_period_source_facts_only|refuse_formal_period_series|2|
|S17 複合表頭同時匹配借閱冊數/女/一般讀者|permitted_exact_source_grid_fact|same_grid_classification_only_no_other_axis_substitution|4|
|S18 顯示破折號/typed0衝突不是明報0|reported_zero_fact_and_separate_unresolved_display_fact|no_numeric_use_of_display_typed_conflict|2|
|S19 新書入庫不是館藏淨增加，也不是館藏存量|two_distinct_original_source_metrics_only|refuse_stock_flow_or_net_change_substitution|2|
|S20 source_series_only的單年已報數仍可回答原來源事實|permitted_single_year_source_fact_with_limits|no_cross_year_certification_from_source_series_only|1|
|S21 版本優先不能壓過新版定義的中英矛盾|prefer_latest_applicable_unconflicted_definition_within_fixed_options|only_2008_edition_segment_since_2000_if_used_as_panel|3|
|S22 同題活動表須拒用題名與正文單位矛盾格|reported_event_count_only; conflicting_table_remains_raw_fact|no_person_visit_or_event_count_equivalence|2|
|S23 2005計畫參照年不能成全年推廣活動總量|scoped_programme_facts_only|not_annual_operations_series|2|
|S24 同版回溯表也要尊重分館納入斷點|all_four_published_year_facts_available|refuse_cross_segment_comparability; 1998_1999_limited_subpanel_only|4|

## 可重現證據

每個候選都有實際observation_id／record_key、官方URL、SHA、原表定位、P2 evidence ID、原值／原狀態及原口徑facets。拒用理由不等於原資料錯誤，只表示不回答該案例的明確範圍。

重跑：`python scripts/audit_phase3_source_options.py`。程式不讀phase3引擎、不改canonical/P2/原件或公開checkout；只輸出本案例清冊。

```json
{
  "cases": 24,
  "distinct_real_candidate_observation_ids": 56,
  "candidate_occurrences": 63,
  "all_candidate_ids_resolved_in_P2": true,
  "all_primary_evidence_ids_resolved": true,
  "fixed_inputs_unchanged": true,
  "current_engine_tested": false,
  "fixture_build_execution": "bundled_local_Python; real-ID selection, P2 joins, hashes and assertions actually executed"
}
```
