# AI 與分析使用說明

本資料包協助理解公共圖書館統計與重現資料整理。它保留多來源、多期間與多版本，不能直接視為同口徑面板或用來推論服務因果效果。

## 唯一正式觀測入口

只讀取以下任一格式，它們是同一批正式觀測：

- `data/combined/observations.jsonl.gz`
- `data/combined/observations.csv`
- `data/combined/library_statistics.sqlite` 的 `observations` 表

先讀 `data/combined/summary.json`、`coverage.json`、`indicators.json` 與 `observation.schema.json`。`data/observations.*`、`data/component_records.jsonl` 和 `derived/` 是組件或中間結果，可能保留重複；不得再併入正式入口。資料筆數不是館數。

目前 37,887 筆來源觀測紀錄，含 206 格明示缺值、876 格原印留白、22 格原印文字狀態及不同出版版本。紀錄數不是圖書館間數，也不能整表相加。「所列來源全量」不等於所有縣市、所有年度或每間館完整。缺口不表示官方沒有公布。

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
| 國家圖書館年鑑統計事實 | 95–114卷指定核心表／公共館子群／原文數字；資料年2005–2024年，保留不同出版版本 |
| 國家圖書館閱讀報告統計事實 | 2011–2012年5張全國閱讀報告表；包括跨年比較，不是縣市表 |
| 主計總處歷史全國統計 | 3個來源版本；資料年1991–2011年，重疊版本分開；`dgbas-social-indicators-2005`、`dgbas-social-indicators-2008`、`dgbas-social-indicators-2011` |
| 主計總處縣市公共館數 | 1998–2025年官方重編地域；來源含國家圖書館，缺值不補0；`dgbas-county-library-Z091101a029` |
| 地方政府開放歷史表 | 新竹市、臺中市已確認系列；保留原年／月期間與館藏地 |

2012年原文中每人購書／擁書／借閱比率分別列22／22／22縣市；館員服務人口只列21縣市，未列連江縣。22縣市核心原量表仍未取得，不能由比率反算。閱讀報告所列表只有全國彙總，不能冒充縣市表。 2015原刊部分縣市標籤未確認、兩列均印金門，保留183筆標籤不確定觀測，不補成連江或硬接現行界線。 其他原刊地理標籤疑義按資料年分列：2024年36格；原印名稱與數字保留，這些格不計為已確認縣市覆蓋。 2015表17標題「場次」與正文「人次」衝突，161格單位保留null及source_heading_conflict_unresolved；人次僅是unit_interpretation_candidate，不是已確認單位。 其他原欄頭與正文計量口徑衝突：2005年51格；unit留空，原單位與出處另存，不視為純圖書冊數。 原表人數／人次的計數口徑未釐清之格位保留unit=null：2005年3格、2016年23格；unit_raw照原欄頭保留。

原表、原文數字與閱讀五表的批次範圍見[歷史批次](docs/historical-batches.md)。

### 數值與缺值

- `value IS NULL` 必須同讀 `value_status` 與 `raw_value`。本版 `206` 格 `not_available_in_source` 保留明示缺值符號，`876` 格 `source_blank` 保留原刊留白，`22` 格 `source_marker` 保留原印「無」「未新增」「未統計」等文字狀態；這些文字不自行改成0或推定不適用，均不推算補值。
- `raw_value` 保留原表字串與註腳標記；例如 `79a` 的數值為79，`source_cell_annotation` 保留a，須同讀 `source_footnotes_raw`／`source_footnotes_status`。`quality_flags` 可為單一代碼或原組件保留的JSON陣列字串；不把單純多層合計旗標當成數值錯誤。
- `raw_value` 保留原表字串；`value` 的小數可能使用十進位字串。SQLite 的 `value` 欄是文字型別，分析前須明確選定解析規則，不能以不受檢查的轉型把異常字串變成零。
- 原報 `0` 未必是已確認的真零；讀 `zero_interpretation`、註腳及資料蒐集範圍。
- `quality_flags = 'source_arithmetic_inconsistency'` 表示原表合計算術不一致，原值未更改。另讀 `notes` 與品質紀錄，並非所有不確定性都有單一旗標。
- 比較前統一且說明單位；「千冊」「冊」「種」「件」「人次」不是可互換單位。未知單位保留未知，不能自行當作冊數。

## 新增年度的特殊狀態

- 原印「無」「未新增」保留 `value=null`、`value_status=source_marker` 與完整原字，不自行推成零、無人力或不適用。純數字的原報零另列。
- `value_parse_rule=literal_scoped_quantity` 搭配 `value_qualifier=scoped_source_component` 只表示原格明示的子範圍。2020臺東電子書80種僅是分區資源中心新增，不能當全縣完整總量。
- 2017高雄經費有分期子列。原註 `1/1-/8/31` 的標點未解，正式期間留空，`period_start_candidate`／`period_end_candidate` 只存候選，必須讀 `source_period_interpretation_status` 和 `source_subrow_label_raw`。另一子列原印9/1–12/31另存，不合併全年。
- 2016「活動（人數）」未明示去重或累計；五年館藏表未印單位，不能沿用單年基本表冊、件。`unit=null` 仍有原數值，不能自行補單位。
- `geographic_scope=county_source_label_uncertain` 保留原刊名稱及數字，含2015、2024部分表的未解地理歸屬／人口基數疑義，不當成已確認的縣市數值。`quality_flags` 和 `notes` 會交代疑義範圍，不能憑常識換位。
- `source_cell_note_raw` 保留數字格內必要的公立館名補述；`raw_value` 專存該格數字或標記，不能宣稱它包含整頁或全部原格文字。

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


## 2005年度來源範圍

95卷公共館表1–2將國立與直轄市機構另列；表3–4是23個原縣市及其原合計，不能直接當現行22縣市，也不能與前兩表整列相加而不核母體。私立公共館表5與統計章108的調查量／填答館數按來源分開；各指標填答數可能不同，不能當設施總數。`source_parenthetical_raw`保留原括號，`source_response_notation_kind`、`source_subrow_label_status`與`source_original_table_row`分辨原字和整理用子列。`ownership_scope`與`population_scope`不可省略。

`未統計`是原印文字狀態，value=null、source_marker；不解讀成真零。原印冊而正文混合冊／件／種，以及借閱人次欄印人的矛盾，以unit_status與source_unit_context_locator保留；正式unit未知時不擅加單位。表6特定計畫與表7跨年活動已完整另存programme來源層，未當成年度核心量。

<!-- BEGIN phase1 -->
## 第一階段的新資料層

先讀`docs/phase1-summary.json`、`docs/phase1-source-inventory.json`及`docs/phase1-data-dictionary.json`。`derived/phase1_authority_checks`是88項來源查核；`phase1_source_candidates`是候選項，不能當觀測。`phase1_discovery_matrix`是來源出現索引，原量和比率分開，月值不當全年，現行地名不改寫舊縣市。`phase1_raw_source_profiles`精確分組既有正式觀測及其ID，不認證跨年可比。

`docs/phase1-supplements.json`列新來源層CSV、JSONL和SQLite四表。programme_rows與programme_quantities是同一來源的列／數量視圖；data_year為null，不拿計畫參照年當全年統計。local_original_cells與local_statistical_cells同樣不可相加；按來源／原工作表的小分檔在`docs/phase1-source-cell-partitions.json`，分檔聯集等於後一表。

來源格使用`value_raw`、`source_display_raw`、`source_stored_value_raw`、`source_typed_numeric_value`。5,098格顯示「-」而typed為0，value=null和source_display_typed_value_conflict_unresolved表示兩種來源表示未解，不能擅改0或一般缺值。原公式只保留原字及快取，不宣稱重新計算。176格sheet/header年月矛盾保持period_year/month=null；catalog_title_year_only_attachment_undated也不是原表已確證年份。未解單位、總計重疊、原分類及來源註解均須同讀。

重建新來源層前，以`python scripts/restore_originals.py --phase1-only`只還原四個已覆核工作簿；`--include-phase1`則連同舊來源還原。可用`--source-root`指定本機研究原件位置。腳本依已記錄SHA驗證，既有不同版本不覆寫，新版須先覆核。

候選不等於完成，查頁沒看到不等於官方無資料。每個結果附來源URL、原件SHA、原表／工作表／儲存格定位及資料版本。新來源格尚未接入canonical observations，不能自行union。
<!-- END phase1 -->

<!-- BEGIN phase2 -->
## 第二階段讀取契約

先讀`docs/phase2-summary.json`、`docs/phase2-statuses.json`及`docs/PHASE2.md`。原數值仍在原有三層，`derived/phase2/annotations.*`是其口徑註記，使用`layer + observation_id`連接，不能union成額外統計量。每筆有原URL/SHA/locator/source_version_id、原值/原狀態、單位及年月的依據、evidence_id與拒用理由。

`published_panel_limited`僅支援相同已核原刊／原件面板、原對象、原分類、指標、單位與有效期間分段。`source_series_only`只是相同來源標籤，不能當跨年認證；`unresolved`保留尚缺證據。群組數／紀錄數不是圖書館家數。不同原件grid signature不併成同一群，原地理名稱不重新對位。

`comparison_value`是原值或原表明示千單位的精確十進位倍數換算，仍需同讀comparison_status/reasons；有數字不代表可比較。未知unit不正規化，冊／種／件不互換。原顯示與typed0衝突仍是null；catalog-only與年月矛盾的正式comparison_year仍未知。原報0另有zero_interpretation，不能自行稱實測真零。預算／決算、續借／借閱、人次／去重人數、私立／公立、總計／分項不能默併。

原刊已明說的斷點只用於那一版／欄／年份。DGBAS不同版本有分館納入及借閱／閱覽定義的註釋，中英方向衝突時保留unresolved，不訂正官方數值。現行NLPI/CNS定義是分開的參照，未把公布或抓取日當歷史採用日。

程式比較兩筆使用`scripts/compare_definitions.py --left layer:ID --right layer:ID`。結果只回答同一原對象能否接續成指定原刊時間序列；不是自動選來源、合計、填補或因果分析。`--operation sum/impute/infer-unique-people/recode-geography/coerce-zero/cross-source-splice`會明確拒絕沒有已驗證規則的操作。SQL用唯讀`annotations`與`comparison_groups` view，內表採字典編碼；SQL scalar值為文字、結構欄為JSON，分析者須依欄定義解析，不能讓失敗轉型變0。

完整三格式傳輸可用gzip；小檔在`docs/phase2-partitions.json`，未解年度分檔不塞回候選年份。官方原件全文仍未隨公開包散布，來源覆核與公版格式驗收是不同範圍。第三階段已提供有界預設選源，見docs/PHASE3.md。
<!-- END phase2 -->

<!-- BEGIN phase2-ai-disclosure -->
## 第二階段的實際協作與驗收

整理與維護者為曲宸宇（Chu, Chen-Yu；GitHub帳號poplolioi11）。主代理以程式重播來源、計算並建置所有註記；Codex助手分別完成國圖／主計來源證據、地方完整原件核對、格式與更新驗收，以及先於引擎固定的來源案例。數值與雜湊來自實際執行的Python，沒有把模型答案當計算證據。

Gemini（gemini-3.8-flash-high）只對本次提供的官方定義摘錄做文字語義檢視，未自行查網；主代理逐項回查，未採納將媒體排除、FTE／志工或歷史生效日擴大的推論。取捨記錄見research/phase2-gemini-semantic-review.json。

固定案例由來源查核助手先建立；該助手後續遇到模型容量限制，主代理接手CLI／公開投影介面並執行最終案例驗收。案例預期未為通過測試而改寫；一個主計2005版案例依原頁英文明註Since2000另列有來源的裁決。最終報告明列實際執行者與檢查範圍，不冒稱完成了另一輪獨立人類校對。原件回查與公開副本格式檢查分開報告。
<!-- END phase2-ai-disclosure -->

<!-- BEGIN phase3 -->
## 第三階段機器讀取契約

先讀docs/phase3-question-index.json，選profile，再依docs/phase3-partitions.json取小檔。全量CSV／JSONL／SQLite在derived/phase3/。record_routes每個P2 record_key恰一次；candidate_decisions主鍵為profile_id+record_key，具體採納、其他版本與拒用理由在此。queries是預設快照，series_edges列候選接續與drawable許可；四表不可union成原始營運量。

逐筆保留官方URL、原件SHA、locator、source_version_id、evidence。政策同時綁來源body及P2證據內容SHA；新版本或同ID定義改變須覆核。原PDF／工作簿／HTML、無關聯絡欄與私人路由仍不公開。公開格式驗收與原件覆核不同。

selected=true只代表選定來源決策。數值回答須同讀selection_status、point_value、point_unit、value_status、raw_value與facets。一般原缺漏為selected_source_missing；顯示/typed0衝突為selected_source_unusable，point_value均null但原狀態不改。原報0的zero_interpretation不能升為測量真零認證。

source_series_only可作單期原來源事實，不獲得跨年連線許可。只用drawable=true的edge；query.trend_summary明示是否單一連續原序列。年份位置齊、同值或selected=true，都不證明全段可連。year_counts分開原位置、有數值、缺漏與不可用；原位置不是數值完整率。

單一面板依用途先核定義／單位／期間，再選完整覆蓋所請區間的原刊與版次；原缺值不降排名，不偷換另一版有值。相同優先序仍歧義；pin source_id禁止fallback；無一面板覆期不跨版拼接。選較舊合格原刊不等於官方訂正較新版。

原行政區／官方重編、含不含國家圖書館、預算／決算、借閱／續借、存量／流量、總計／分項各自保留。不加總、不補值、不推估去重人數、不重編地理。未知欄位拒絕，缺path不等於null。

圖表座標及區間選源由Python產生，前端只篩既有點與核准線段。圖表區間可改選原刊；下方全量表仍是預設決策快照，表格顯示篩選不重算選版。新用途／source-id／facet條件用select_sources.py重播，保留requested_filters。自由文字須先對應已登錄問題與原欄；無預設範圍可用--lookup讀原Annotation，不自動變成新原量或認證趨勢。
<!-- END phase3 -->

本次閱覽器改版由主代理執行Python分檔、逐項核對與隔離瀏覽器驗收，原生背景助手協助前端三檔。助手靜態檢查不代替真實資料及瀏覽器驗收；統計值、統計定義與選源器未交由模型重寫。

## 2026-10-28來源研究層不可併入正式入口

`docs/source-discovery-20261028.json`為新取得原件的候選索引；`research/source-probes/20261028-original-cells.json`的396格只是列明三張表的完整擷取證據。`value`使用十進位字串／null，`comparison_permission=none_probe_not_canonical_or_panel`；不可併入既有正式觀測或拿來補接現行折線圖。新北區列`data_year=null`、表內2015脈絡另記；辦證單位null、來源符號null及臺南跨年變動列均不可猜補。臺北年刊權利衝突的數值沒有進此公開層。

主代理以官方HTTP、原頁影像與實際Python核對16份原件SHA及完整396格；PDF使用pdfplumber與PDFium兩種擷取結果核對，不是兩個獨立官方來源。Gemini 3.8 Flash High只查閱提供的候選摘要，協助提示年份／重複風險，未獨立瀏覽或核讀原件。來源與未解口徑見[研究報告](research/source-discovery-20261028.md)。


## 公開副本

可以先讀 `data/by_year/index.json`，按年度取得相同的正式觀測。含無關聯絡欄的原件不再散布，改附數值欄位投影；`source_sha256` 驗原件，`public_evidence_sha256` 驗投影。投影不改統計原值、期間、單位、地理口徑或原件定位。完整來源驗收須先依 README 復原原件；公開副本的離線檢查並不等於重查全部原件。


完整JSONL與中間元件以gzip無損壓縮，年度JSONL仍是純文字。Python可用 `gzip.open("data/combined/observations.jsonl.gz","rt",encoding="utf-8")` 逐行讀取。解壓後逐位元組SHA另記；gzip檔案SHA與統計內容指紋是不同層，不能互換。

<!-- BEGIN lightweight-site -->
## 輕量網站不是新的分析資料

網站 https://poplolioi11.github.io/tw-public-library-statistics/ 的JSON分檔只投影既有合格圖表，不代表全部56,496個量化紀錄。AI正式分析仍依本文件原讀取入口。畫點值可能沿用第二階段已核單位尺度；`original_value`、`raw_value`、`original_unit`與`facets`仍留原量及口徑。`source_url`／`source_sha256`／`source_locator`／`source_version_id`不改，動態查詢另附`official_url`與重現提示。不得把網站顯示值或內容雜湊檔名誤當官方原件SHA。
<!-- END lightweight-site -->
