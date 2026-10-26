# 第三階段：有界預設選源與折線圖

資料版本v0.8.0；政策1.0.0；來源審查基線v0.7.0。本階段不新增／改寫原量。19個登錄問題、56,496筆原紀錄路由、52,689筆候選決策；32,993個候選接續中20,375個可畫線。這是紀錄／決策數，不是館數或額外營運量。

## 直接看圖與來源

[互動折線圖](../site/phase3.html#line-charts)預設顯示國圖原刊借閱面板，每點可回官方原件。可切換問題、原對象、原指標與期間。原值或原表明示單位倍數換算另標；缺期、缺值與口徑切換斷線。單期資料在原表保留，不捏造跨年折線。

[全部原刊數列](../site/phase2.html#line-charts)有639組，不限舊版12示例；第三階段有691組圖表及847個同源Python選源的區間結果。原刊有限對照仍不認證所有歷年方法／涵蓋率不變。

## 選用政策

問題包括主計改制後縣市／全國館數、國資圖2023原報與歷年公開圖表、國圖六種原刊回溯、縣市年度原量、新竹月值、臺中採購冊數、花蓮兩種分類、連江明示年度、特定計畫及主計歷史單版原報。[輕量問題索引](phase3-question-index.json)列原用途；[完整政策](phase3-profiles.json)保留來源與證據SHA。

原行政區、官方重編地域、母體與國立館範圍不默換。單期原報可用，跨年連線另驗。新版優先是維護者政策，不是官方勘誤；原版與其他候選照留。缺值是面板合法成分，不以數字大小／有無值排名。新來源或同ID的證據內容SHA變更必須覆核；相同優先序保持歧義。指定source-id後不換版。無單一面板覆蓋所請區間時不拼線。

## 重播查詢

~~~sh
python scripts/select_sources.py --list
python scripts/select_sources.py --profile national-ncl-book-loans-panel --start-year 2020 --end-year 2024
python scripts/select_sources.py --profile county-library-count-dgbas --entity 臺北市 --start-year 2010 --end-year 2025
python scripts/select_sources.py --profile historical-national-dgbas-source-facts --purpose trend --metric 圖書借閱人數 --start-year 2005 --end-year 2005
python scripts/select_sources.py --lookup canonical:obs-28edaf7217be5d3c0c4546
python scripts/select_sources.py --operation impute
~~~

--source-id固定版本；--facility及--facet 原欄路徑=原值精確篩選，不猜近義。缺欄不等於null。CSV／JSONL匯出candidate_decisions；整體選版與edge許可需讀JSON，不能只憑CSV補線。--output不覆寫既有匯出。

## 機器格式與更新

四表CSV／JSONL／SQLite逐欄一致。SQLite的record_routes、candidate_decisions、queries、series_edges為wide views；scalar是TEXT、結構欄JSON、缺值SQL NULL。內表字典編碼。按profile／年度小檔的聯集等於candidate_decisions；未知年另檔，不塞回目錄年。

selected=true可包含missing或unusable，須同讀point_value及原狀態。顯示/typed0衝突不叫一般缺漏，更不改0。year_counts分開原位置、數值、缺漏與不可用；trend_summary.single_continuous_series明列整段是否單一原序列。只連drawable=true的邊。

更新入口仍run_update.py。來源群／政策／程式指紋快取；未變不建置，失敗保留前版。公開包不含私人排程、憑證、無關聯絡欄或原件全文。

## 缺口與驗證

2012原文有少量分館／閱覽室分項，完整22縣市核心原量表仍未取得；不拿components、比率或人口乘算補成原量。全臺歷年仍未齊，未登錄範圍完整保留在原路由，缺口不表示官方沒公布。

[固定來源案例驗收](../research/phase3-engine-review.md)保留24例、CLI、缺值／0／分類roundtrip與拒用反例；格式與更新另由獨立validator檢查。[Gemini文字邊界檢視](../research/phase3-gemini-boundary-review.json)只讀提供的契約，未查網；擴大成測量真零、重寫原狀態或假設圖表皆近似值的推論未採納。數值、雜湊與座標均由Python實際執行，非官方背書或人類逐格雙校。
