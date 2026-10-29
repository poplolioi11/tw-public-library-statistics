# 第三階段引擎獨立驗收

檢查階段：final_after_parent_freeze。保留原先未見引擎的24例，fixture SHA未改。

實際執行 1403 個檢查，失敗 0 個；56個真實候選記錄皆以來源與P2證據定位。

單年來源事實、語義預設選源與機器輸出分開驗。只核對lookup或操作guard的案例，不宣稱任意自然語言查詢已實作；不是人類雙校。

|案例|實測範圍|斷言失敗|
|---|---|---|
|S01 全國單年：選最新且實際含該年的原刊面板|registered_semantic_default|0/74|
|S02 跨七年不能把兩張五年面板拼成同口徑趨勢|registered_semantic_default|0/89|
|S03 同一已核五年表可作有限原刊面板比較|registered_semantic_default|0/80|
|S04 縣市館數明確要求包含三個國立館|registered_scope_default|0/37|
|S05 國圖縣市表與國資圖API不可僅依中文近義欄互補|two_registered_scopes_plus_guard|0/21|
|S06 2012人均館藏不能補縣市館藏原量|lookup_plus_scope_guard|0/7|
|S07 指定版次的缺值不可被另一版有值偷偷取代|explicit_source_pin_plus_lookup|0/25|
|S08 購書預算與決算不是同一數值欄|explicit_original_facet_filter|0/9|
|S09 借閱人次不能回答有多少不重複讀者|operation_guard_plus_original_fact|0/6|
|S10 同一歷年資料可有原行政區與官方重編系列|lookup_plus_geography_guard|0/11|
|S11 同年同地同單位同數值仍不能視為同指標|lookup_integrity_only|0/6|
|S12 地方單館單月原格可引用，但不能當全縣年度|explicit_original_month_facility_metric|0/131|
|S13 地方空白表頭不能只按冊單位猜借閱或館藏|lookup_only_unregistered_header|0/6|
|S14 年度館藏原量不等於確定12月31日的快照|explicit_annual_stock_scope|0/7|
|S15 目錄113年不能取代無日期附件的正式統計年|registered_period_rejection|0/5|
|S16 工作表名與表頭月份或四位年字衝突不擇一修正|registered_period_rejection|0/294|
|S17 複合表頭同時匹配借閱冊數/女/一般讀者|explicit_original_grid_facets|0/81|
|S18 顯示破折號/typed0衝突不是明報0|source_status_and_unknown_unit_guards|0/80|
|S19 新書入庫不是館藏淨增加，也不是館藏存量|original_metrics_plus_unsupported_operation_guard|0/18|
|S20 source_series_only的單年已報數仍可回答原來源事實|registered_single_year_source_fact|0/6|
|S21 版本優先不能壓過新版定義的中英矛盾|definition_qualified_trend_selection|0/56|
|S22 同題活動表須拒用題名與正文單位矛盾格|explicit_metric_with_unit_evidence|0/31|
|S23 2005計畫參照年不能成全年推廣活動總量|programme_scope_and_annual_guard|0/132|
|S24 同版回溯表也要尊重分館納入斷點|same_source_segment_edges|0/29|

## 失敗或需補強

本輪已實測條件未發現失敗。

## 能力邊界

- S04：NCL prose components are preserved through lookup and their own profile, not returned as explicit rejections by the fixed DGBAS profile.
- S05：The caller chooses which population to quote. No unified natural-language national-library/material/renewal resolver is implemented.
- S06：The original per-capita ratio has no registered original-total default; lookup is a raw quote, not completion of the 2012 total gap.
- S07：Other editions are outside source_id pin, retained by lookup. They are not in that query decisions list.
- S08：financial_mode=final_expenditure must be supplied. Filtered budget is preserved by lookup; the engine does not parse arbitrary financial language or automatically emit a rejected-budget explanation.
- S09：A unique-person request requires the explicit guard; the profile itself returns original 人次 when asked for that original metric.
- S10：The preferred old-geography ratio remains a source quote; it is excluded from the county original-quantity default. No certified boundary conversion or current-city substitution is implemented.
- S11：Both actual records have an excluding-national alternative scope without a registered default profile. Identity preservation is tested; no equal-value semantic resolver is claimed.
- S13：No semantic default exists for these blank-field source cells. Successful lookup and refusal to relabel are narrower than answering a circulation question.
- S17：The caller supplies original reader class and full column path. Other axis candidates remain lookup records, not automatically explained semantic alternatives.
- S19：No net-change calculator exists. The unknown-operation guard is conservative; it is not a full stock-flow accounting implementation.
- S21：Definition-sensitive preference is obtained with purpose=trend and an exact original metric. Source-facts purpose may quote the newer unresolved source; it is not a natural-language definition constraint.
- S22：Both tables remain selected original records; table17 has selected_source_unusable/point null. Only table16 is a usable event-count answer, rather than deleting the conflicting original.
- CSV and JSONL are decision-row exports only; JSON contains query and edges. Full trend permission cannot be reconstructed from CSV/JSONL alone without a matching query/edges file.
- No human source double review, unrestricted natural-language parsing, full Taiwan all-year completeness, boundary crosswalk or cross-publication trend equivalence is certified.
- Prefiltered candidates are excluded from a narrow API query before decisions. This report retains all fixed candidates via real-ID annotation/route/CLI lookups; that is not an engine-generated refusal explanation for each semantic alternative.
- A selected original record may be unusable as a standardized point; source_series_only single-year facts are allowed while join certification remains absent.

重跑：`python -B scripts/check_phase3_cases.py`；root freeze後加 `--final`。完整查詢、原格證據、候選及斷言見同名JSON。

引擎SHA：`c37ffc648ab0efb176a95468288e1d2dfaca1351f1ae69a9ab8cee9531223301`
政策SHA：`c58dc3d0fc52ea43d156c35ca106861ba2f6af481555742ad1afa3066e2be704`
固定案例SHA：`0e263e018589b033fbcc0eea3b4802e59a3c319ea529fe7d7497d3cf27703af6`
