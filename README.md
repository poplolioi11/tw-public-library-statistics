# 臺灣公共圖書館跨年度統計

[![資料與程式檢查](https://github.com/poplolioi11/tw-public-library-statistics/actions/workflows/check.yml/badge.svg)](https://github.com/poplolioi11/tw-public-library-statistics/actions/workflows/check.yml)

查臺灣公共圖書館的館藏、借閱、館數與服務統計，並追溯每個數字出自哪份官方資料。可以直接看圖，也可以下載資料交給表格工具、程式或 AI 使用。

## 三個常見問題，從這裡開始

| 你想知道什麼？ | 直接使用 |
|---|---|
| 全國圖書借閱冊數近年如何變化？ | [看2020–2024年借閱折線圖](https://poplolioi11.github.io/tw-public-library-statistics/?profile=national-ncl-book-loans-panel&from=2020&to=2024)：採同一已核原刊面板，每個數字可回官方來源。 |
| 縣市歷年館數或分館月表在哪裡？ | [查縣市歷年館數（主計口徑）](https://poplolioi11.github.io/tw-public-library-statistics/?profile=county-library-count-dgbas&entity=%E8%87%BA%E5%8D%97%E5%B8%82)，或[查分館月表（三民分館範例）](https://poplolioi11.github.io/tw-public-library-statistics/?profile=discovered-official-monthly-tables&series=comparison-9d8764a5d362caefbadaac33)。 |
| 我想自行分析，或交給AI使用。 | 下載 [CSV](https://github.com/poplolioi11/tw-public-library-statistics/releases/download/v0.9.1/observations.csv)、[JSONL.gz](https://github.com/poplolioi11/tw-public-library-statistics/releases/download/v0.9.1/observations.jsonl.gz) 或 [SQLite](https://github.com/poplolioi11/tw-public-library-statistics/releases/download/v0.9.1/library_statistics.sqlite)；需要小檔可用[年度索引](data/by_year/index.json)，讀取方式見[AI與分析指南](AI_USAGE.md)。 |

**使用前先知道：**資料仍有歷年缺口，部分來源口徑不同；掃描年鑑轉錄未經人工雙校。圖表與原報值的詳細界線見[完整度與缺口](COVERAGE.md)及[比較規則](#比較前先確認口徑)。

<!-- BEGIN human-review-status -->
文件狀態核對：2026-10-30；資料仍為v0.9.1。**人工抽樣核讀與雙校尚未完成**，沒有預填人工讀值、錯誤率或模型準確率。程式、原件雜湊及AI原圖核對不替代人工參考。[目前待辦與已完成範圍](docs/source-backlog.md)另列；固定引用見[CITATION.cff](CITATION.cff)。
<!-- END human-review-status -->

## 版本、引用與方法

版本 **0.9.1**；資料建置日 **2026-10-29**。已公開：[https://github.com/poplolioi11/tw-public-library-statistics](https://github.com/poplolioi11/tw-public-library-statistics)；[v0.9.1下載](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.9.1)。

引用可使用右側 **Cite this repository** 或 [CITATION.cff](CITATION.cff)，並保留使用版本、所選口徑及官方原表來源。v0.9.1於2026-10-30封存至Zenodo，版本DOI為[10.5281/zenodo.23788194](https://doi.org/10.5281/zenodo.23788194)；固定GitHub Release仍可辨識原公開版本。

[資料說明稿：來源、方法、驗證與限制](docs/DATA_PAPER_DRAFT.md)是**未投稿、未經同儕審查的草稿**。[採用證據與回饋方式](docs/REUSE.md)說明如何回報實際使用；star、fork或下載次數不直接當成研究採用證據。

整理與維護：曲宸宇（Chu, Chen-Yu；GitHub：[poplolioi11](https://github.com/poplolioi11)；[ORCID](https://orcid.org/0009-0003-9738-6914)）。中英文姓名與帳號指同一位作者；官方統計作者及權利仍依各筆來源。

本專案先查重再整理。國立公共資訊圖書館已有跨年圖表、國家圖書館已有統計名詞字典，SEGIS 及地方開放資料亦有相關歷年成果。本專案的新增值是**跨來源的統一讀取方式、逐筆來源定位、期間與口徑標記，以及可追溯的內容版本**；不宣稱是第一份跨年統計或第一個名詞字典。查閱[查重報告](research/prior-art.md)及[官方範圍與定義](research/official-scope.md)。

## 目前收錄什麼

目前 **58,245 筆來源觀測紀錄**，含 **206 格明示缺值**、**1,303 格原印留白**、**5,413 格原印文字狀態**及不同出版版本。紀錄數不是圖書館間數，也不能整表相加。

| 來源族群 | 已整理的範圍 | 紀錄數 |
|---|---|---:|
| 國資圖公開全國圖表 | 2011–2025年公開全國圖表；只有全國 | 855 |
| 國資圖2023開放資料（含縣市） | 2023年明確OGDL年度資源；全國、縣市與替代口徑分列，不相加 | 2,236 |
| 國家圖書館年鑑統計事實 | 91–114卷指定核心表／公共館子群／原文數字；資料年2001–2024年，保留不同出版版本 | 20,795 |
| 國家圖書館閱讀報告統計事實 | 2011–2012年5張全國閱讀報告表；包括跨年比較，不是縣市表 | 154 |
| 主計總處歷史全國統計 | 3個來源版本；資料年1991–2011年，重疊版本分開 | 220 |
| 主計總處縣市公共館數 | 1998–2025年官方重編地域；來源含國家圖書館，缺值不補0 | 644 |
| 地方政府開放歷史表 | 新竹市、臺中市已確認系列；保留原年／月期間與館藏地 | 14,751 |
| 主計總處後續全國出版統計 | 2010–2024年113年統計年鑑表4-22；全國含國家圖書館，機關／縣市列未逐列年份保留未知 | 312 |
| 地方官方出版統計事實 | 2006–2021年所列新北、臺南、桃園、彰化、高雄及臺北原刊；全國／縣市／行政區／分館與年／月分開，未明年另存 | 18,230 |
| 教育部歷史公共館統計 | 1994–2009年近16年統計社3表，含國家圖書館；單位千冊／千人次，不與重疊出版版本相加 | 48 |

逐批格數、資料年、版次與指定表／原文範圍見[已覆核歷史批次](docs/historical-batches.md)及[COVERAGE.md](COVERAGE.md)。

2012年原文中每人購書／擁書／借閱比率分別列22／22／22縣市；館員服務人口只列21縣市，未列連江縣。22縣市核心原量表仍未取得，不能由比率反算。閱讀報告所列表只有全國彙總，不能冒充縣市表。 2015原刊部分縣市標籤未確認、兩列均印金門，保留183筆標籤不確定觀測，不補成連江或硬接現行界線。 其他原刊地理標籤疑義按資料年分列：2024年36格；原印名稱與數字保留，這些格不計為已確認縣市覆蓋。 2015表17標題「場次」與正文「人次」衝突，161格單位保留null及source_heading_conflict_unresolved；人次僅是unit_interpretation_candidate，不是已確認單位。 其他原欄頭與正文計量口徑衝突：2005年51格；unit留空，原單位與出處另存，不視為純圖書冊數。 原表人數／人次的計數口徑未釐清之格位保留unit=null：2005年3格、2016年23格；unit_raw照原欄頭保留。

**完整性指「所列來源的已確認表格／資源全量」，不代表全臺各縣市全部歷年都已完成。** 整體參照年範圍為 1991–2026，各年可用指標、地域及口徑不同，不能將這個範圍當成連續一致的全國縣市面板。未取得、尚未解析或權利未確認的部分列為缺口，不能解讀成官方沒有資料。

2023 年的 26 列包括全國、22 縣市，以及新北／臺中／南投「不含國立館」的三個替代口徑，不是 26 個縣市。地方資料中，新竹涵蓋民國 105–114 年每個月份、115 年 1–8 月，另有 104 年 12 月；臺中年報、月報、分館借閱與購書資料各保留原期間。詳見[完整度與缺口](COVERAGE.md)、[來源覆蓋清單](data/combined/coverage.json)、[目前摘要](data/combined/summary.json)與[地方整包查核](research/local-history.md)。

主計總處縣市館數收錄 **28 年 × 23 列＝644 格**。1998–2005 年全部以 `-` 明示缺值，共 184 格；2006–2025 年有 460 格數值（含各年總計）。它採官方「改制後縣市別」，2006–2010 年歷史值也已按官方重編為 22 縣市，並非本專案自行合併。來源現行定義包含**國家圖書館、國立公共資訊圖書館與國立臺灣圖書館**；母體與國資圖公共館數不同，不能直接互補缺年或接成同口徑序列，歷年定義適用性亦未逐年獨立認證。

該系列可回[官方查詢頁](https://winstacity.dgbas.gov.tw/DgbasWeb/ZWeb/StateFile_ZWeb.aspx?Type=table)，或核對[原始格子事實 JSON](raw/segis-history/dgbas_county_original_cells.json)與[正常公開表單 POST 重現腳本](scripts/fetch_segis_history.py)。原始 HTML 不隨公開包提供。

## 下載與讀取

[版本與完整下載](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.9.1) · [按年度讀取 JSONL](data/by_year/index.json)

公開副本移除22份原始檔的無關聯絡欄，以另有雜湊的統計投影提供；原始來源網址、原件SHA及每筆統計值均保留。詳[公開副本與來源原件的區別](docs/PUBLICATION.md)。

## 從哪裡開始

- [公開輕量圖表網站](https://poplolioi11.github.io/tw-public-library-statistics/)：直接查閱、可分享查詢網址，逐筆回官方來源。
- [折線圖與依問題選源](site/phase3.html#line-charts)；[全部原刊數列](site/phase2.html#line-charts)；[逐筆原值閱覽](site/index.html)。
- [JSONL](data/combined/observations.jsonl.gz)：每行一筆完整觀測，適合 AI 與程式處理。
- [CSV](data/combined/observations.csv.gz)：同一批正式觀測，適合表格工具。
- [SQLite](data/combined/library_statistics.sqlite.gz)：同一批正式觀測；資料表為 `observations`。
- [觀測結構](data/combined/observation.schema.json)、[指標清單](data/combined/indicators.json)、[資料包描述](datapackage.json)。
- [AI 與分析使用說明](AI_USAGE.md)、[授權說明](LICENSE.md)、[機器閱讀入口](llms.txt)、[補充文件目錄](docs/)。

**分析的正式讀取入口只用 `data/combined/` 中的上述三種觀測檔。** `data/observations.*`、`data/component_records.jsonl` 及 `derived/` 為來源組件或中間觀測；其中可能保留重複，不能再接到正式觀測後面。

## 比較前先確認口徑

每筆紀錄保留來源 URL、原頁／表／列欄定位、SHA-256、取得時間、來源與出版版本，以及可確認的資料期間、單位、母體和地域範圍。未知處保留未知，不以現行定義回填所有舊年。

先選定 `source_family` 或 `source_id`，再確認 `series_id`、`geographic_scope`、`national_libraries_scope`、`temporal_kind`、`period_basis`、`unit`、`source_edition` 及註記，才進行比較：

- 全國總計、縣市、國立館及「含／不含國立館」列可能重疊，不能整表加總。
- 月度流量不能直接當成全年數；年底存量、年度新增量及借閱流量也不同。
- 國圖等歷史原表的舊臺北縣、臺中縣／市名稱保留原貌；主計縣市館數另採官方重編後地域。請檢查 `geography_vintage`，不能把兩種地域口徑視為相同或再自行合併。
- `value=null` 須搭配 `value_status`：`source_blank` 是原刊留白，`not_available_in_source` 是明示缺值，`source_marker` 保留原印「無」「未新增」等文字狀態；都不推定為零或不適用。來源回傳的 `0` 保留為原報值；須讀 `zero_interpretation`，不能逕認為真實零或已完整調查。
- 人次不是不重複人數；館藏地可能是閱覽室或微型館，不能直接換算成實體館數。比率不跨地區相加。

忠實轉錄與檢查通過，不等於原始填報必然正確。地方來源已發現 28 個合計算術不一致，國圖年鑑亦有原表內部差異；原值均保留，請讀 `quality_flags`、`notes` 與[品質查核](derived/local_historical_quality.json)。

## 來源、權利與重現

來源擴充的研究快照見[2026-10-28研究報告](research/source-discovery-20261028.md)與[候選清單](docs/source-discovery-20261028.json)：當時取得16份原件、另核396格。這是入庫前的歷史紀錄；v0.9.0其後正式納入12份原件的完整指定表，詳見[本版整批入庫](#2026-10-28官方原表入庫批次)。研究probe不重複加進正式資料，2012全22縣市核心原量仍缺。

2023 年及地方資料有明確 OGDL 第 1 版標示；主計歷史表另依官方開放宣告記錄。主計縣市查詢子站採母站廣泛宣告的適用推論，標記 `license_scope_inference=true`；子站未另列獨立條款，不將它冒充為子站單獨授權。國圖年鑑及公開圖表在本專案中整理的是公開統計事實，沒有將專章全文、PDF、原始 HTML／JavaScript 宣稱為開放內容。公開包不再散布 NCL PDF 或網頁原始 HTML／JS，引用與權利分類詳見 [LICENSE.md](LICENSE.md)。

國資圖 [2026-09-17 公告](https://publibstat.nlpi.edu.tw/Frontend/News/ShareNewsView?NewsID=News000050)另規範現行公開範圍與申請資料用途。既有明確開放版本與新申請資料必須分別處理；本專案不以舊目錄授權推定其他年度或申請資料可再公開。

已提供來源分組、內容雜湊快取、來源版本與更新腳本。更新主入口為 [`scripts/run_update.py`](scripts/run_update.py)，來源／解析查核紀錄見 [research/](research/)；腳本與來源條件以當前版本為準。相同內容保留首次取得時間，複查時間另記；更新失敗保留仍可驗證的前版並標示狀態。維護端每月檢查；沒有資料變動時保持安靜，重要新增、修訂或失敗才通知。公開包不包含私人排程設定，不會因下載而啟用。

重現分析時，請記錄本專案版本、`observation_id`、來源 `source_id`／`source_sha256`，以及所選口徑；對資料表更動保留版本，不覆蓋來源原值。


## 執行更新與重現

分析既有資料不需要下載來源或安裝套件。更新環境需 Python 3.12 及 `requirements.txt` 所列套件，執行 `python scripts/run_update.py`。本機已完成一次端到端驗收與不變資料的再次執行。

公開包刻意不含原PDF或完整網頁；若要從PDF重做擷取與完整來源驗收，先執行 `python scripts/restore_originals.py`，它只依明列官方URL取得並核對指定SHA，原版變更時會停止覆核，然後執行 `python scripts/run_update.py --offline`。重建程式保留原值與明示缺值，不會用推算值補齊。圖表與政策頁若已改版，需先重新覆核來源選單與新公告，才接受新版本。

<!-- BEGIN phase1 -->
## 第一階段：全臺來源與缺口清冊

第一階段完成的是2005–2025年的來源導航、原口徑清冊及已取得來源批次；不宣稱全臺歷年值皆已齊全。

- 現行22縣市×4個機關角色，共88項有實際查核紀錄；不是每個機關檔案庫都已窮盡。440個候選項分開標示入口、下載失敗、尚待解析及已完成的附件。
- 第一階段當時的4,830格「年×導航地區×主題」呈現來源出現情形；29,337組原口徑精確保留當時37,887筆觀測，不合併不同原地區、母體、單位、期間或版本。
- 新增2005計畫表6／7整批119列／123個數量格，以及花蓮、連江4附件的18,486個統計格。另有33,705個安全範圍原格含表頭及結構空白；這些是不同視圖，不可相加，也未混入既有正式觀測。
- 花蓮兩份ODS各保留72個月工作表（2020年9月至2026年8月）及空白模板；176格年月矛盾留未知。連江113年目錄附件未印年份，與工作表明印114年的來源分開。

[來源與缺口互動頁](site/phase1.html) · [範圍與驗收](docs/PHASE1.md) · [新增來源資料](docs/phase1-supplements.md) · [小型工作表分檔](docs/phase1-source-cell-partitions.json) · [機器字典](docs/phase1-data-dictionary.json)

2012縣市核心原量仍未取得，不由比率反算。第二階段已另附逐筆口徑與原刊有限對照規則；完整歷史方法認證仍未成立，第三階段已提供有界預設選源，見docs/PHASE3.md。
<!-- END phase1 -->

<!-- BEGIN phase2 -->
## 第二階段：有來源依據的口徑檢視

v0.9.1逐筆檢視現有76,854個量化紀錄：58,245筆正式觀測、18,486個地方來源格、123個計畫數量格，三層分開，不相加成業務量。445張來源證據卡及100項斷點／欄位規則可回官方原件、SHA與原表位置。

- 原刊／原件範圍內有1,677組支援多個期間的有限對照，其中554組涉及不同年度；不是同方法、全歷年或跨來源面板認證。
- 0筆原null單位可依已核原欄「冊數／人次」另附單位解讀；14,400筆五碼原年月嚴格解碼。原值、原unit與原data_year保持不變。
- 未解的定義、生效年、單位、地理及期間留在理由欄。相同標籤、數字相同、同一表或當代標準公布年，均不直接證明歷年方法相同。2012原量缺口不推算。

[口徑與來源互動頁](site/phase2.html) · [第二階段說明](docs/PHASE2.md) · [逐筆JSONL（gzip）](derived/phase2/annotations.jsonl.gz) · [逐筆CSV（gzip）](derived/phase2/annotations.csv.gz) · [SQLite](derived/phase2/definitions.sqlite) · [按層／年度小檔](docs/phase2-partitions.json)
<!-- END phase2 -->

<!-- BEGIN phase3 -->
## 第三階段：依問題選來源，直接看折線圖

v0.9.1有22個明確母體／用途的預設問題，完整路由76,854筆既有量化紀錄，保留115,356筆候選決策與來源理由。這些是選源註記，不是新增館數或營運量，原統計值不變。

[直接看折線圖與選源](site/phase3.html#line-charts) · [全部原刊數列](site/phase2.html#line-charts) · [問題索引](docs/phase3-question-index.json) · [範圍與用法](docs/PHASE3.md) · [按問題／年度小檔](docs/phase3-partitions.json)

主入口直接顯示已核國圖原刊借閱折線。第二階段有1677組已核數列圖；第三階段有2767組問題內原數列圖與847個由同一Python選源器預算的區間結果。原報點可回官方來源，缺值、缺期與口徑切換不連線。

選定來源與跨年可比分開；selected可能仍是缺值或不可用。版次優先是維護者政策，其他版本照留。2012全22縣市核心原量表仍缺；已取得的少量分館／閱覽室原文分項照留，不冒充完整核心量。
<!-- END phase3 -->

<!-- BEGIN discovered-20261028 -->
## 2026-10-28官方原表入庫批次

v0.9.1沿用2026-10-28已入庫的20,358個原格，來自12份官方原件的完整指定表及續頁；這不是本次中繼資料修訂新增的觀測。早期年鑑2001–2004、教育部1994–2009、主計2010–2024全國原表，以及新北、臺南、桃園、彰化、高雄和臺北所列原刊分開保存。高雄含表3-2全部52頁、各館年度及12個月；臺北本批僅2012年12月。

新增格包含14,540個數值、427個原刊留白、5,391個原刊符號／複合格；467格期間未確認。原格數不是館數，合計、分項、年合計與月值不得整表相加。原年份不明不填出版年；原件缺值不補0。新北館藏2010前後分段；高雄年度館藏／期刊彙計與借閱率口徑未明，不當年底庫存趨勢。

[完整來源／表格範圍](raw/discovered-20261028/extraction-metadata.json)與[逐筆原格驗收](scripts/validate_discovered_20261028.py)可重跑。各格保留原字串、單位、官方原件URL、SHA、原頁表列欄、版本及公式／分母；讀source_time_reference的JSON可取原表脈絡、合併格與公式等額外來源限定，source_cell_note_raw保留核對方法。369格掃描資料以Apple Vision及AI原圖核讀，沒有宣稱人類逐格雙校；重複OCR不是獨立引擎。

原始發現登錄及396格研究probe是v0.8歷史快照，不算額外觀測；正式映射見本批metadata與derived/discovered_20261028_observations.jsonl.gz。臺北2012年刊權利衝突及三份跨館型統計章待核子群仍隔離。2012完整22縣市核心原量仍缺，不從比率推算，不跨來源拼成全臺面板。

16個複合／非單一量原格另逐格登錄於scripts/reviewed_non_scalar_literals.json（含原件SHA、原文及定位）。例如主館／括弧分館、各1人、每鄉各2不能任挑一個數字作總量；source_marker及selected_source_missing在這些格表示沒有單一可用純量，不表示原件沒有資料。必須同讀raw_value、原註與該登錄，不推算補值。

沿用每月維護；新增歷史固定原件每365天到期回查，來源與擷取器未變則沿用完整批次。原件更動暫存待覆核、失敗保留前版，不把新下載內容自動當作可公開授權。
<!-- END discovered-20261028 -->

<!-- BEGIN metadata-review-20261029 -->
## v0.9.1 單位與來源定位修訂

按固定原件確認14,596筆單位（地方原欄名14,584、同卷全國電子資源合計12），單位缺值由16,286降至1,690。數字、原字串、缺值、識別碼及期間不變；467筆年度缺值已逐組覆核，仍保留未知／跨年狀態。91年卷來源摘要補上第5頁續表。**人工雙校仍未完成**，2012核心原量缺口不推算。見[逐筆修訂與未解清單](docs/metadata-review-20261029.md)。
<!-- END metadata-review-20261029 -->

<!-- BEGIN lightweight-site -->
## 公開輕量圖表網站

[直接開啟圖表](https://poplolioi11.github.io/tw-public-library-statistics/)。不必下載整份HTML；先載入問題目錄，再按所選數列讀取小型JSON。手機刻度文字使用固定字級；每個點位及表格數值都能回官方原件或官方動態查詢入口，另附原件SHA、原表位置與版次。

資料版本仍為 **v0.9.1**，閱覽器另列 **v1.0.0**。既有1677組原刊數列、2767組問題內數列與847個預算區間完整轉出；相同原數列可出現在不同問題，這些數量不可相加成統計觀測。只改呈現與傳輸，原值、缺值、口徑、選源及准許線段不變。單期事實與沒有合格圖表的問題仍請查完整資料包；沒有圖不表示沒有資料。

[網站範圍、重建與驗收](docs/LIGHTWEIGHT_SITE.md)。既有單檔閱覽頁仍作離線用途，GitHub Pages只部署 `site/light/`。
<!-- END lightweight-site -->


完整CSV及SQLite以gzip無損壓縮提供；先解壓即可用一般CSV／SQLite工具，Release另附相同解壓後檔案。`record_io`依publication-profile自動讀取JSONL／CSV，SQLite驗證以暫存解壓檔查核；壓縮前後的統計值、SQL NULL與來源定位不變。
