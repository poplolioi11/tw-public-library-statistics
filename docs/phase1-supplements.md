# 新增的完整來源格子資料

這層保留原表及工作表格子，不直接加入既有正式觀測，也不認證跨年可比。`phase1_local_sources_cells`是含表頭與結構空白的原格事實；`phase1_local_sources_long`是同一原件中選定統計格，不可兩表相加。

- 2005年表6／7：[計畫列CSV](../derived/ncl_2005_programmes.csv)、[數量格CSV](../derived/ncl_2005_programmes_long.csv)。119列計畫紀錄、123個原數量格；兩種不參與／留白狀態與兩個日期期間另存，不改0或年度量。原PDF不隨包散布，CSV內下載網址與PDF頁／表／列／欄可回到原件。
- 地方四附件：[統計格CSV](../derived/phase1_local_sources_long.csv)、[JSONL](../derived/phase1_local_sources_long.jsonl)，18,486格；[安全範圍原格CSV](../derived/phase1_local_sources_cells.csv)含33,705個表頭、數值及結構位置。114連江工作簿無關古蹟與個人聯絡背景不公開。
- [SQLite](../derived/phase1_supplements.sqlite)的四表與各CSV／JSONL內容相同；[機器清單](phase1-supplements.json)列出表名及範圍。
- AI或程式不必先讀完整大檔：[按來源及原工作表的分檔索引](phase1-source-cell-partitions.json)提供小型JSONL、來源工作表原名、格數與SHA。分檔聯集是同一批18,486格，不是額外數據。

## 使用前須讀的原件差異

花蓮兩份ODS各有72個月份與空白模板；模板不當觀測。sheet名與表頭的兩個月份矛盾仍保留兩說、正式期間未知。連江113附件本身未印年，只能看到目錄113年的對應，不冒稱附件已有確證資料年；114工作表明印年度另列。

5,098個來源顯示「-」而底層為0的格子，`value=null`及`source_display_typed_value_conflict_unresolved`只標示兩種原表示未解；底層0仍在`source_typed_numeric_value`／`source_stored_value_raw`，不能自動認為缺值或實測零。另一個原字串「-」另存`source_marker`。每格同時保留display、typed、原公式、樣式／number format與合併來源。

2005計畫不當全年營運：各館計畫窗與全國閱讀運動各項期間分開；原表人次合計與細項加總有差異時原值照留。館名、原標籤及已更正的擷取差異見獨立報告，不以常識修正來源館名或地理歸屬。

公開的是統計投影；原工作簿、PDF、無關聯絡欄與原頁全文不在包內。OGDL只適用逐來源已核的版本；其餘公開統計事實之原件全文權利仍未確認。來源忠實度／格式驗證不是官方填報正確性或人類雙校認證。
