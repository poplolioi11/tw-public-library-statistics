# AI 與分析使用說明

本資料包協助理解公共圖書館統計與重現資料整理。它保留多來源、多期間與多版本，不能直接視為同口徑面板或用來推論服務因果效果。

## 唯一正式觀測入口

只讀取以下任一格式，它們是同一批正式觀測：

- `data/combined/observations.jsonl`
- `data/combined/observations.csv`
- `data/combined/library_statistics.sqlite` 的 `observations` 表

先讀 `data/combined/summary.json`、`coverage.json`、`indicators.json` 與 `observation.schema.json`。`data/observations.*`、`data/component_records.jsonl` 和 `derived/` 是組件或中間結果，可能保留重複；不得再併入正式入口。資料筆數不是館數。

目前 26,725 筆來源觀測紀錄，含 200 格明示缺值、876 格原印留白及不同出版版本。紀錄數不是圖書館間數，也不能整表相加。「所列來源全量」不等於所有縣市、所有年度或每間館完整。缺口不表示官方沒有公布。

## 先選來源，再選可比較的觀測

1. 固定 `source_family` 或 `source_id`，使用 `series_id` 識別指標系列；不要只用相似中文指標名合併。
2. 檢查 `data_year`、`period_start`／`period_end`、`period_raw`／`period_effective`、`periodicity_raw`、`temporal_kind` 與 `period_basis`。資料年、出版年、填報年及取得時間不可互換。
3. 檢查 `geography`、`geographic_scope`、`geography_vintage`、`population_scope`、`national_libraries_scope`、`facility` 與單位。舊行政區保留原名；館藏地類別不是實體館識別碼。
4. 檢查 `source_edition`／`source_edition_roc`、`aggregation_role`、`institutional_level`、`unit_raw`／`unit_basis`／`unit_status`、`definition_id`／`definition_status`、`comparability`、`notes` 及 `quality_flags`。尚未確認歷年相容性，不得自行認證。
5. 每個結論附 `source_url`、`source_locator`、`source_sha256` 與所用版本。保留 `observation_id`，讓別人找到完全相同的輸入。

### 來源族群

| `source_family` | 適用的來源選擇 |
|---|---|
| 國資圖公開全國圖表 | 2011–2025年公開全國圖表；只有全國 |
| 國資圖2023開放資料（含縣市） | 2023年明確OGDL年度資源；全國、縣市與替代口徑分列，不相加；`ogdl-api-2023` |
| 國家圖書館年鑑統計事實 | 96–105卷指定核心表／公共館子群／原文數字；資料年2006–2015年，保留不同出版版本 |
| 國家圖書館閱讀報告統計事實 | 2011–2012年5張全國閱讀報告表；包括跨年比較，不是縣市表 |
| 主計總處歷史全國統計 | 3個來源版本；資料年1991–2011年，重疊版本分開；`dgbas-social-indicators-2005`、`dgbas-social-indicators-2008`、`dgbas-social-indicators-2011` |
| 主計總處縣市公共館數 | 1998–2025年官方重編地域；來源含國家圖書館，缺值不補0；`dgbas-county-library-Z091101a029` |
| 地方政府開放歷史表 | 新竹市、臺中市已確認系列；保留原年／月期間與館藏地 |

2012年原文中每人購書／擁書／借閱比率分別列22／22／22縣市；館員服務人口只列21縣市，未列連江縣。22縣市核心原量表仍未取得，不能由比率反算。閱讀報告所列表只有全國彙總，不能冒充縣市表。 2015原刊部分縣市標籤未確認、兩列均印金門，保留183筆標籤不確定觀測，不補成連江或硬接現行界線。 2015表17標題「場次」與正文「人次」衝突，161格單位保留null及source_heading_conflict_unresolved；人次僅是unit_interpretation_candidate，不是已確認單位。

原表、原文數字與閱讀五表的批次範圍見[歷史批次](docs/historical-batches.md)。

### 數值與缺值

- `value IS NULL` 必須同讀 `value_status` 與 `raw_value`。本版 `200` 格 `not_available_in_source` 保留明示缺值符號，`876` 格 `source_blank` 保留原刊留白；留白不推定不適用，均不補零。
- `raw_value` 保留原表字串與註腳標記；例如 `79a` 的數值為79，`source_cell_annotation` 保留a，須同讀 `source_footnotes_raw`／`source_footnotes_status`。`quality_flags` 可為單一代碼或原組件保留的JSON陣列字串；不把單純多層合計旗標當成數值錯誤。
- `raw_value` 保留原表字串；`value` 的小數可能使用十進位字串。SQLite 的 `value` 欄是文字型別，分析前須明確選定解析規則，不能以不受檢查的轉型把異常字串變成零。
- 原報 `0` 未必是已確認的真零；讀 `zero_interpretation`、註腳及資料蒐集範圍。
- `quality_flags = 'source_arithmetic_inconsistency'` 表示原表合計算術不一致，原值未更改。另讀 `notes` 與品質紀錄，並非所有不確定性都有單一旗標。
- 比較前統一且說明單位；「千冊」「冊」「種」「件」「人次」不是可互換單位。未知單位保留未知，不能自行當作冊數。

## 避免重複或錯誤加總

2023 資源的 26 個地理／口徑列包含全國、22 縣市及三個「不含國立館」替代列。不能將全國再加縣市，也不能將兩種國立館口徑相加。歷史國圖表可能另外列國立／省設館，和現行縣市母體不同。

主計縣市館數的 644 格為 1998–2025 年 ×（22 縣市＋總計）；只有 2006–2025 年的 460 格有數值。採官方「改制後縣市別」，2006–2010 年也已按官方重編，不可當成當年的舊縣市行政區或自行再合併。來源現行定義包含國家圖書館、國立公共資訊圖書館及國立臺灣圖書館；與國資圖公共館數母體不同，不能直接互補。`temporal_kind` 仍標記年度參照、存量具體時點未確認，不自行填上年底日期。

該查詢子站的 `license_status='OGDL-1.0_site_declaration'` 搭配 `license_scope_inference=true`，表示援引主計母站廣泛宣告，子站沒有另列條款；不能省略推論狀態後稱為明確的子站獨立授權。原 HTML 不入公開包，原格子事實 JSON、查詢頁與正常 POST 重現腳本另有保留。

地方月值不是全年值；完整年度的流量加總也須先確認各月不重疊、館藏地與定義一致。年底館藏、人員等存量不能跨月份相加。借閱人次不是獨立人數，不能用來推計有多少不同讀者。

不同出版版本的同年觀測會同時保留。先選版本，再比較；不要把主計三個版本的重疊年度當成三筆獨立業務量。正式入口已排除地方來源中已確認的同值重複；中間檔仍保留來源重複，請勿自行接回。

## 唯讀 SQL 範例

以唯讀模式連線 `data/combined/library_statistics.sqlite`。以下只列出已指定口徑的觀測，不進行加總。若由應用接收篩選條件，使用查詢參數。

先查看來源及口徑；`COUNT(*)` 是紀錄數：

```sql
SELECT source_family, source_id, geographic_scope, COUNT(*) AS records
FROM observations
GROUP BY source_family, source_id, geographic_scope
ORDER BY source_family, source_id, geographic_scope;
```

選取 2023 年借閱冊數的 22 個預設縣市列，保留其國立館範圍說明；不混入全國與替代列：

```sql
SELECT geography, value, raw_value, unit, value_status,
       national_libraries_scope, definition_status,
       source_id, source_locator, source_sha256, source_url
FROM observations
WHERE source_id = 'ogdl-api-2023'
  AND data_year = 2023
  AND indicator = '全年圖書資訊借閱冊數'
  AND geographic_scope = 'county_default_includes_national_where_applicable'
ORDER BY geography;
```

選取新竹 115 年 8 月的館藏地借閱冊數，仍保留月別而非假稱全年：

```sql
SELECT facility, period_effective, periodicity_raw, value, unit,
       quality_flags, notes, source_id, source_locator, source_sha256
FROM observations
WHERE source_family = '地方政府開放歷史表'
  AND geography = '新竹市'
  AND data_year = 2026
  AND period_effective = '11508'
  AND indicator = '借閱冊數'
ORDER BY facility, source_id;
```

選取主計縣市館數 2006–2025 年實際有值的 22 縣市列，排除各年總計，並呈現授權推論與地域範圍。這會列出 440 個數值，不會拿 1998–2005 年缺值補零：

```sql
SELECT data_year, geography, value, raw_value, value_status, unit,
       geography_vintage, national_libraries_scope,
       license_status, license_scope_inference,
       source_id, source_locator, source_sha256
FROM observations
WHERE source_id = 'dgbas-county-library-Z091101a029'
  AND geographic_scope = 'county_official_reorganized'
  AND data_year BETWEEN 2006 AND 2025
  AND value IS NOT NULL
ORDER BY data_year, geography;
```

以上條件可用於檢視，不能自動證明跨年可比。若要作跨年圖、地理整併、單位換算或月值加總，另保存明確的選擇與轉換規則，並將衍生值和原始觀測分開。

## AI 整理與引用界線

資料取得、表格解析、欄位整備與文件撰寫使用 AI 協作及程式輔助；可追溯來源、逐值讀回、表頭與註腳核對、算術檢查及回歸測試用於發現問題。這些工作不等於官方認證、專家定本或原始填報零錯誤。不要宣稱已有人工逐格雙校。

回答使用者時，說明所選來源族群、資料年／期間、地域與館種範圍、單位、版本及重要缺口。對因果、讀者個人行為或完整服務品質的推論，不能只靠這組業務統計得出。

再利用請讀 [LICENSE.md](LICENSE.md)。本專案不替原機關背書，不授予原始 PDF、敘述、圖像、網頁程式或第三方內容額外權利。更新入口為 `scripts/run_update.py`。維護端定期檢查；公開包不含私人排程設定，不會因取得檔案而自動啟用。更新與原檔還原步驟見 [README.md](README.md)。


## 公開副本

可以先讀 `data/by_year/index.json`，按年度取得相同的正式觀測。含無關聯絡欄的原件不再散布，改附數值欄位投影；`source_sha256` 驗原件，`public_evidence_sha256` 驗投影。投影不改統計原值、期間、單位、地理口徑或原件定位。完整來源驗收須先依 README 復原原件；公開副本的離線檢查並不等於重查全部原件。
