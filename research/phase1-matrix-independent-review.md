# 第一階段矩陣最終獨立驗收

結果：PASS（v0.6.0；僅下述範圍）

F01–F07全部修正並重新驗證；16個synthetic tests通過，matrix→reader重建後嚴格validator通過1,004,384個斷言。

## 原觀測保真

- 37,887個唯一observation ID完整保留於23,466個原口徑profile，沒有合併數值。
- 88角色、4,830導航格；歷史行政區不重編、不加總。
- 219筆2015／2024明確地名待解持續保留；原先91筆單位／母體／期間疑義不再錯列地名未解，40格confirmed筆數已重算，差異為0。
- 2,046筆明確衍生比率不填原量；2012縣市仍只有館數主題已有來源，其他主題不反算。
- 87筆明確月值不叫全年；6筆高雄分期財務分為3筆期間待確認、3筆分期。

## 獨立補充來源層

- 4個完整附件共18,486統計格；重新核原檔SHA並直接查146個統計sheet的ZIP/XML期別定位。
- 連江113年35格只有目錄年份，不進已核年格。
- 花蓮176格期別衝突不進已核年格：113年6月sheet表頭113年7月；109年10月sheet表頭原字為1109年10月，不能截尾改成109。
- 用7個確切原metric標籤的獨立對照重算補充層，與4,830格差異為0；原格、統計格、既有觀測不相加。
- 440候選只有3條標來源格已驗收，精確配對4附件（花蓮一條含2檔）；另外437條仍未入庫。
- 已核既有獨立原件審查result=PASS、0差異及4份現行輸出SHA；本輪不冒稱重新獨立完成全部數值抽取。

## 版本與界線

矩陣builder SHA：`f577b043fd450ce02dbc31b5853c220fa47a317fc0f8e11426116aaa800bdb89`。

這是分組、矩陣、來源期別和入庫狀態的驗收；不表示全臺歷年完整或跨年可比。未做UI互動、原生試算表顯示、公式重算或法律權利認證。root後續新增source_links，最終reader重建與strictvalidator由root執行；matrix builder未再變動。

```json
{
  "canonical_checks": {
    "canonical_records": 37887,
    "canonical_unique_ids": 37887,
    "source_profiles": 23466,
    "all_ids_preserved_exactly_once": true,
    "independent_group_partition_matches": true,
    "authority_slots": 88,
    "unique_authority_pairs": 88,
    "authority_status_counts": {
      "checked_relevant_source_found": 44,
      "checked_no_relevant_dataset_in_checked_page": 7,
      "checked_entry_only": 32,
      "request_failed": 5
    },
    "discovery_grid_cells": 4830,
    "historical_or_other_label_ids": 4191,
    "historical_or_other_label_ids_recoded_into_grid": 0,
    "explicit_unresolved_geography_ids": 219,
    "unresolved_geography_by_year": {
      "2015": 183,
      "2024": 36
    },
    "geography_flags_from_non_geographic_problems": 0,
    "matrix_confirmed_label_count_mismatches": 0,
    "matrix_exact_geography_mismatches": 0,
    "explicit_derived_ratio_ids": 2046,
    "derived_ratio_ids_in_quantity_grid": 0,
    "2012_nonempty_county_topic_cells": {
      "library_count": 22
    },
    "2012_non_count_quantity_topics_filled": 0,
    "explicit_monthly_records": 87,
    "monthly_resolution": {
      "monthly_source_not_annual_total": 87
    },
    "financial_subperiod_resolution": {
      "time_basis_unconfirmed": 3,
      "partial_or_programme_period": 3
    },
    "loan_flows_tagged_holdings_now": 0,
    "general_budget_tagged_book_purchase_now": 0,
    "primary_url_timestamp_mismatches_now": 0,
    "stale_inputs_pending_rebuild": [],
    "derived_profile_metadata_differences_pending_rebuild": 0,
    "candidate_count": 440,
    "candidate_ingestion_status_counts": {
      "not_ingested_unless_separate_verified_batch_evidence": 413,
      "not_ingested": 24,
      "source_cell_batch_verified_not_harmonised": 3
    }
  },
  "supplement_period_status_counts": {
    "catalog_title_year_only_attachment_undated": 35,
    "matching_sheet_name_and_header_month": 18240,
    "source_sheet_name_header_period_conflict_unresolved": 176,
    "explicit_sheet_year": 35
  },
  "supplement_grid_source_cells": 16149,
  "supplement_grid_nonmissing_cells": 11643,
  "verified_candidate_records": 3,
  "verified_attachment_ids": [
    "south-hualien-library-lending-409-reader",
    "south-hualien-library-lending-409-room",
    "south-lienchiang-culture-library-overview-114",
    "south-lienchiang-opendata-173786"
  ]
}
```

精確來源SHA、期別衝突原字／定位、全部輸入雜湊、先前問題與修正狀態見同名JSON。
