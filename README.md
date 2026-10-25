# 臺灣公共圖書館跨年度統計

[![資料與程式檢查](https://github.com/poplolioi11/tw-public-library-statistics/actions/workflows/check.yml/badge.svg)](https://github.com/poplolioi11/tw-public-library-statistics/actions/workflows/check.yml)

將分散在官方圖表、開放資料及歷史統計表中的公共圖書館數據，整理成可查詢、可回到來源的觀測資料，協助公眾理解圖書館服務，也讓研究者與 AI 使用者能重現整理結果。

版本 **0.3.0**；資料建置日 **2026-10-25**。已公開：[https://github.com/poplolioi11/tw-public-library-statistics](https://github.com/poplolioi11/tw-public-library-statistics)；[v0.3.0下載](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.3.0)。

本專案先查重再整理。國立公共資訊圖書館已有跨年圖表、國家圖書館已有統計名詞字典，SEGIS 及地方開放資料亦有相關歷年成果。本專案的新增值是**跨來源的統一讀取方式、逐筆來源定位、期間與口徑標記，以及可追溯的內容版本**；不宣稱是第一份跨年統計或第一個名詞字典。查閱[查重報告](research/prior-art.md)及[官方範圍與定義](research/official-scope.md)。

## 目前收錄什麼

目前 **26,725 筆來源觀測紀錄**，含 **200 格明示缺值**、**876 格原印留白**及不同出版版本。紀錄數不是圖書館間數，也不能整表相加。

| 來源族群 | 已整理的範圍 | 紀錄數 |
|---|---|---:|
| 國資圖公開全國圖表 | 2011–2025年公開全國圖表；只有全國 | 855 |
| 國資圖2023開放資料（含縣市） | 2023年明確OGDL年度資源；全國、縣市與替代口徑分列，不相加 | 2,236 |
| 國家圖書館年鑑統計事實 | 96–105卷指定核心表／公共館子群／原文數字；資料年2006–2015年，保留不同出版版本 | 7,865 |
| 國家圖書館閱讀報告統計事實 | 2011–2012年5張全國閱讀報告表；包括跨年比較，不是縣市表 | 154 |
| 主計總處歷史全國統計 | 3個來源版本；資料年1991–2011年，重疊版本分開 | 220 |
| 主計總處縣市公共館數 | 1998–2025年官方重編地域；來源含國家圖書館，缺值不補0 | 644 |
| 地方政府開放歷史表 | 新竹市、臺中市已確認系列；保留原年／月期間與館藏地 | 14,751 |

逐批格數、資料年、版次與指定表／原文範圍見[已覆核歷史批次](docs/historical-batches.md)及[COVERAGE.md](COVERAGE.md)。

2012年原文中每人購書／擁書／借閱比率分別列22／22／22縣市；館員服務人口只列21縣市，未列連江縣。22縣市核心原量表仍未取得，不能由比率反算。閱讀報告所列表只有全國彙總，不能冒充縣市表。 2015原刊部分縣市標籤未確認、兩列均印金門，保留183筆標籤不確定觀測，不補成連江或硬接現行界線。 2015表17標題「場次」與正文「人次」衝突，161格單位保留null及source_heading_conflict_unresolved；人次僅是unit_interpretation_candidate，不是已確認單位。

**完整性指「所列來源的已確認表格／資源全量」，不代表全臺各縣市全部歷年都已完成。** 整體參照年範圍為 1991–2026，各年可用指標、地域及口徑不同，不能將這個範圍當成連續一致的全國縣市面板。未取得、尚未解析或權利未確認的部分列為缺口，不能解讀成官方沒有資料。

2023 年的 26 列包括全國、22 縣市，以及新北／臺中／南投「不含國立館」的三個替代口徑，不是 26 個縣市。地方資料中，新竹涵蓋民國 105–114 年每個月份、115 年 1–8 月，另有 104 年 12 月；臺中年報、月報、分館借閱與購書資料各保留原期間。詳見[完整度與缺口](COVERAGE.md)、[來源覆蓋清單](data/combined/coverage.json)、[目前摘要](data/combined/summary.json)與[地方整包查核](research/local-history.md)。

主計總處縣市館數收錄 **28 年 × 23 列＝644 格**。1998–2005 年全部以 `-` 明示缺值，共 184 格；2006–2025 年有 460 格數值（含各年總計）。它採官方「改制後縣市別」，2006–2010 年歷史值也已按官方重編為 22 縣市，並非本專案自行合併。來源現行定義包含**國家圖書館、國立公共資訊圖書館與國立臺灣圖書館**；母體與國資圖公共館數不同，不能直接互補缺年或接成同口徑序列，歷年定義適用性亦未逐年獨立認證。

該系列可回[官方查詢頁](https://winstacity.dgbas.gov.tw/DgbasWeb/ZWeb/StateFile_ZWeb.aspx?Type=table)，或核對[原始格子事實 JSON](raw/segis-history/dgbas_county_original_cells.json)與[正常公開表單 POST 重現腳本](scripts/fetch_segis_history.py)。原始 HTML 不隨公開包提供。

## 下載與讀取

[版本與完整下載](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.3.0) · [按年度讀取 JSONL](data/by_year/index.json)

公開副本移除22份原始檔的無關聯絡欄，以另有雜湊的統計投影提供；原始來源網址、原件SHA及每筆統計值均保留。詳[公開副本與來源原件的區別](docs/PUBLICATION.md)。

## 從哪裡開始

- [互動閱讀頁](site/index.html)：按來源、指標及年度查看紀錄與來源。
- [JSONL](data/combined/observations.jsonl)：每行一筆完整觀測，適合 AI 與程式處理。
- [CSV](data/combined/observations.csv)：同一批正式觀測，適合表格工具。
- [SQLite](data/combined/library_statistics.sqlite)：同一批正式觀測；資料表為 `observations`。
- [觀測結構](data/combined/observation.schema.json)、[指標清單](data/combined/indicators.json)、[資料包描述](datapackage.json)。
- [AI 與分析使用說明](AI_USAGE.md)、[授權說明](LICENSE.md)、[機器閱讀入口](llms.txt)、[補充文件目錄](docs/)。

**分析的正式讀取入口只用 `data/combined/` 中的上述三種觀測檔。** `data/observations.*`、`data/component_records.jsonl` 及 `derived/` 為來源組件或中間觀測；其中可能保留重複，不能再接到正式觀測後面。

## 比較前先確認口徑

每筆紀錄保留來源 URL、原頁／表／列欄定位、SHA-256、取得時間、來源與出版版本，以及可確認的資料期間、單位、母體和地域範圍。未知處保留未知，不以現行定義回填所有舊年。

先選定 `source_family` 或 `source_id`，再確認 `series_id`、`geographic_scope`、`national_libraries_scope`、`temporal_kind`、`period_basis`、`unit`、`source_edition` 及註記，才進行比較：

- 全國總計、縣市、國立館及「含／不含國立館」列可能重疊，不能整表加總。
- 月度流量不能直接當成全年數；年底存量、年度新增量及借閱流量也不同。
- 國圖等歷史原表的舊臺北縣、臺中縣／市名稱保留原貌；主計縣市館數另採官方重編後地域。請檢查 `geography_vintage`，不能把兩種地域口徑視為相同或再自行合併。
- `value=null` 須搭配 `value_status`：`source_blank` 是原刊留白，`not_available_in_source` 是明示缺值；兩者都不補零。來源回傳的 `0` 保留為原報值；須讀 `zero_interpretation`，不能逕認為真實零或已完整調查。
- 人次不是不重複人數；館藏地可能是閱覽室或微型館，不能直接換算成實體館數。比率不跨地區相加。

忠實轉錄與檢查通過，不等於原始填報必然正確。地方來源已發現 28 個合計算術不一致，國圖年鑑亦有原表內部差異；原值均保留，請讀 `quality_flags`、`notes` 與[品質查核](derived/local_historical_quality.json)。

## 來源、權利與重現

2023 年及地方資料有明確 OGDL 第 1 版標示；主計歷史表另依官方開放宣告記錄。主計縣市查詢子站採母站廣泛宣告的適用推論，標記 `license_scope_inference=true`；子站未另列獨立條款，不將它冒充為子站單獨授權。國圖年鑑及公開圖表在本專案中整理的是公開統計事實，沒有將專章全文、PDF、原始 HTML／JavaScript 宣稱為開放內容。公開包不再散布 NCL PDF 或網頁原始 HTML／JS，引用與權利分類詳見 [LICENSE.md](LICENSE.md)。

國資圖 [2026-09-17 公告](https://publibstat.nlpi.edu.tw/Frontend/News/ShareNewsView?NewsID=News000050)另規範現行公開範圍與申請資料用途。既有明確開放版本與新申請資料必須分別處理；本專案不以舊目錄授權推定其他年度或申請資料可再公開。

已提供來源分組、內容雜湊快取、來源版本與更新腳本。更新主入口為 [`scripts/run_update.py`](scripts/run_update.py)，來源／解析查核紀錄見 [research/](research/)；腳本與來源條件以當前版本為準。相同內容保留首次取得時間，複查時間另記；更新失敗保留仍可驗證的前版並標示狀態。維護端採來源分組與定期檢查；下載或複製此專案不會自動啟用排程。

重現分析時，請記錄本專案版本、`observation_id`、來源 `source_id`／`source_sha256`，以及所選口徑；對資料表更動保留版本，不覆蓋來源原值。


## 執行更新與重現

分析既有資料不需要下載來源或安裝套件。更新環境需 Python 3.12 及 `requirements.txt` 所列套件，執行 `python scripts/run_update.py`。本機已完成一次端到端驗收與不變資料的再次執行。

公開包刻意不含原PDF或完整網頁；若要從PDF重做擷取與完整來源驗收，先執行 `python scripts/restore_originals.py`，它只依明列官方URL取得並核對指定SHA，原版變更時會停止覆核，然後執行 `python scripts/run_update.py --offline`。重建程式保留原值與明示缺值，不會用推算值補齊。圖表與政策頁若已改版，需先重新覆核來源選單與新公告，才接受新版本。
