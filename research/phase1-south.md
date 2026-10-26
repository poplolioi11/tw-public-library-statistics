# 第一階段：南東離島官方來源盤點

本檔是來源／缺口盤點與可整批處理的候選清單；沒有新增數值觀測，也沒有發布資料檔。
範圍為 2005–2025 年公共圖書館營運十主題。2026 年月／暫計另列。2012 年未取得原量表仍保留缺口，不推算。
本輪只查列明頁面；入口成功不表示歷年全站已查齊。目錄標示年份與已開原件核對年份分開，未取得原檔不稱已入庫。

## 可重跑證據

以本機 bundled Python 建置 JSON，實際計數為 11 縣市、44 角色、94 次不同 URL HTTP 查核；85 個成功回應原件已保留並本機讀回 SHA 驗證。雲端讀回仍待主代理核對，不聲稱已完成雲端驗收。
私人 ledger 保存 HTTP 狀態、取得時間、SHA 與原件快照識別；公開候選只保留統計事實、短證據與 URL，不包含全文、聯絡值或實體儲存路徑。
資料盤點程式：`tmp/phase1-south-build.py`；HTTP 取得程式：`tmp/phase1-south-fetch.py`；私人查核帳：`raw/phase1-inventory/south-http-checks.private.json`。

## 角色結果

| 縣市 | 圖書館 | 文化 | 主計 | 開放資料 |
|---|---|---|---|---|
| 嘉義市 | 請求失敗／保留缺口 | 找到相關來源 | 找到相關來源 | 請求失敗／保留缺口 |
| 嘉義縣 | 已查入口／待原表 | 已查入口／待原表 | 找到相關來源 | 已查頁未見營運統計 |
| 臺南市 | 已查入口／待原表 | 找到相關來源 | 已查入口／待原表 | 找到相關來源 |
| 高雄市 | 找到相關來源 | 找到相關來源 | 已查入口／待原表 | 找到相關來源 |
| 屏東縣 | 已查入口／待原表 | 找到相關來源 | 找到相關來源 | 已查頁未見營運統計 |
| 宜蘭縣 | 已查入口／待原表 | 已查入口／待原表 | 已查入口／待原表 | 已查頁未見營運統計 |
| 花蓮縣 | 已查入口／待原表 | 找到相關來源 | 已查入口／待原表 | 已查入口／待原表 |
| 臺東縣 | 已查入口／待原表 | 已查頁未見營運統計 | 已查入口／待原表 | 請求失敗／保留缺口 |
| 澎湖縣 | 已查入口／待原表 | 找到相關來源 | 已查入口／待原表 | 找到相關來源 |
| 金門縣 | 已查入口／待原表 | 已查入口／待原表 | 找到相關來源 | 請求失敗／保留缺口 |
| 連江縣 | 已查入口／待原表 | 找到相關來源 | 已查入口／待原表 | 找到相關來源 |

狀態為「已查頁未見」僅限列明頁面；請求失敗不代表機關沒有資料。每個角色的精確範圍、URL、時間、SHA、定位與短證據均在 JSON `checks`。

## 先做完整來源批次

1. 臺南館藏：目錄 6 個資源頁、109–114 年標期；全部 CSV 下載與 JSON view 已列。館藏欄位跨年有電子期刊欄差異，需保留來源欄。
2. 臺南借閱：目錄完整 10 個獨立資源頁；113、114 年各 3 個同名資源，109–112 年各 1 個。不能先按同名／年份去重；須按各原件 SHA、發布資訊與逐值比較釐清。
3. 屏東：已列 109–113 年 5 個詳細頁全部 8 附件；109 年含 ODS、XLSX、2 PDF，其餘每年各 1 PDF。未下載原件，資料年仍是目錄提示。
4. 花蓮 409：單頁共有 6 群組、46 個真實附件；圖書館借閱範圍為 2 ODS，其他 44 附件完整列在 `catalog_all_attachments` 並標範圍外。目錄為 109 年 9 月至 115 年 8 月；檔內 sheet／年月尚未核。館藏地為借閱分組，不是館藏量。
5. 連江 173786：Dataset JSON-LD 完整 1 ODS，標期 113 年、明載 OGDL 第 1 版；原件尚未下載。文化處另列 114 年 XLSX，與該 ODS 分開成批，未確認 XLSX 再公開授權。
6. 澎湖：113 年借閱完整 3 格式（CSV／XML／JSON）已列，但 CKAN 側欄未指定授權、額外欄寫 OGDL、授權網址值卻是「免費」，須先覆核。
7. 已保留 PDF 的可核完整表：臺南閱讀風貌表 1（108–112 年）、高雄文化年報表 7（109–113 年）與表 8（113 年）、澎湖文化年報表 5-2（109–113 年）。只核原件定位／期別與部分定義，未宣稱全表已解析。

## 口徑與更新界線

嘉義縣 110 年館藏發展政策記載：100 年圖書資訊科改隸教育處，108 年 7 月併教育處社會教育科。這項沿革僅作機關脈絡，不自動套成全部歷年統計母體或 2026 組織。PDF 第 1 頁可追溯；原文原件 SHA 已保留。
臺南分析 PDF 第 2 頁註 2–6 定義館藏為年底實有數（含電子資源），借閱人次一人一次多冊仍計一次，借閱冊數含電子書。須與開放平台逐欄比較後才能跨表／跨年接續。
高雄借閱年齡／性別表使用萬冊次，不直接當冊次；澎湖表中「-」不改為 0。澎湖縣館與澎南分館 113 年進館數變動大，不憑合理性猜測對調。
下一步依候選 source ID 與原件 URL、SHA 做來源級更新；未變動來源不重解析。每檔保留目錄 SHA、原件 SHA、工作表／原表定位、期間、單位、館別母體與版本關係。已列真實附件後沿該連結續查，不重新地毯搜尋。

## 逐縣來源與實際範圍

### 嘉義市

- `library_authority`：嘉義市政府文化局圖書館；請求失敗／保留缺口。[已查頁](https://www.cabcy.gov.tw/)。國圖名錄列出的館網；HTTPS 取得失敗，另查國圖名錄確認機關與原網址。
- `culture_authority`：嘉義市政府文化局；找到相關來源。[已查頁](https://chiayi.dgbas.gov.tw/statweb/Page/stat01_1.aspx?Mid=5006)。文化局公務統計預告發布時間表；未取得實際 XLS。
- `statistics_authority`：嘉義市政府主計處；找到相關來源。[已查頁](https://chiayi.dgbas.gov.tw/DgbasWeb/statfile2.aspx?cateno=01&mode=3)。資料庫教育文化項目清單；不把列出的指標當作已匯出歷年數值。
- `open_data_catalog`：嘉義市政府資料開放平臺；請求失敗／保留缺口。[已查頁](https://data.chiayi.gov.tw/opendata/)。財政稅務局網站導覽所連的資料開放入口；HTTP 400。

- 候選 `south-chiayi-city-db`：[來源](https://chiayi.dgbas.gov.tw/DgbasWeb/statfile2.aspx?cateno=01&mode=3)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。
- 候選 `south-chiayi-city-culture-schedule`：[來源](https://chiayi.dgbas.gov.tw/statweb/Page/stat01_1.aspx?Mid=5006)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 嘉義縣

- `library_authority`：嘉義縣政府教育處／嘉義縣公共圖書館；已查入口／待原表。[已查頁](https://www.cycab.gov.tw/)。圖書館入口與館藏發展政策 PDF；入口不是歷年完整統計。
- `culture_authority`：嘉義縣文化觀光局；已查入口／待原表。[已查頁](https://tbocc.cyhg.gov.tw/)。現行文化觀光局首頁與公開連結；本頁未取得公共館歷年統計。
- `statistics_authority`：嘉義縣政府主計處；找到相關來源。[已查頁](https://cyhg.dgbas.gov.tw/dgbasweb/statfile2.aspx?CateNo=33&Mode=3)。教育文化（年）指標清單及統計年報目錄。
- `open_data_catalog`：嘉義縣政府／政府資料開放平臺；已查頁未見營運統計。[已查頁](https://data.gov.tw/dataset/132161)。嘉義縣政府公開資料集提供機關紀錄；該筆為主管會報，並非圖書館資料集。

- 候選 `south-chiayi-county-collection-policy`：[來源](https://www.cycab.gov.tw/wSite/public/Attachment/f1638168730232.pdf)；列 1 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。
- 候選 `south-chiayi-county-db`：[來源](https://cyhg.dgbas.gov.tw/dgbasweb/statfile2.aspx?CateNo=33&Mode=3)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。
- 候選 `south-chiayi-county-yearbooks`：[來源](https://cyhg.dgbas.gov.tw/statweb/Page/BookCatalog_Main.aspx)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 臺南市

- `library_authority`：臺南市立圖書館；已查入口／待原表。[已查頁](https://www.tnpl.tn.edu.tw/)。館網首頁及公開選單；營運統計另由市府資料開放目錄確認。
- `culture_authority`：臺南市政府文化局；找到相關來源。[已查頁](https://culture.tainan.gov.tw/df_ufiles/071/閱讀閱有趣112年臺南市閱讀風貌概況.pdf)。112 年閱讀風貌官方分析 PDF；已核表 1、註 2–6，未入庫。
- `statistics_authority`：臺南市政府主計處；已查入口／待原表。[已查頁](https://account.tainan.gov.tw/News.aspx?n=44&sms=9367)。統計年報列表；當前頁見 100–114 年刊年標籤，未逐年下載原表。
- `open_data_catalog`：臺南市政府資料開放平台；找到相關來源。[已查頁](https://data.tainan.gov.tw/DataSet/Detail/80b958cc-682b-47ff-8cf9-1c140e6ef26b)。館藏完整目錄 6 資源；借閱完整目錄 10 資源，資源頁逐頁取得，資料檔尚未下載。

- 候選 `south-tainan-holdings`：[來源](https://data.tainan.gov.tw/DataSet/Detail/80b958cc-682b-47ff-8cf9-1c140e6ef26b)；列 6 個資料資源，已驗原檔資料年 尚未核定，授權 `OGDL-1.0_explicit_in_catalog`，未入庫。
- 候選 `south-tainan-lending`：[來源](https://data.tainan.gov.tw/DataSet/Detail/c2e72bd1-cd4c-46a5-9913-197953789c46)；列 10 個資料資源，已驗原檔資料年 尚未核定，授權 `OGDL-1.0_explicit_in_catalog`，未入庫。
- 候選 `south-tainan-reading-analysis-112`：[來源](https://culture.tainan.gov.tw/df_ufiles/071/閱讀閱有趣112年臺南市閱讀風貌概況.pdf)；列 1 個資料資源，已驗原檔資料年 [2019, 2020, 2021, 2022, 2023]，授權 `unconfirmed`，未入庫。
- 候選 `south-tainan-yearbooks`：[來源](https://account.tainan.gov.tw/News.aspx?n=44&sms=9367)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 高雄市

- `library_authority`：高雄市立圖書館；找到相關來源。[已查頁](https://www.ksml.edu.tw/form/index.aspx?Parser=28%2C3%2C32)。統計數據目錄當前頁、圖書概況／借閱冊數／通閱分類及下一頁連結；未窮盡後頁。
- `culture_authority`：高雄市政府文化局；找到相關來源。[已查頁](https://khcc.kcg.gov.tw/PhotoData/TyzRJWC16kxBNJp.pdf)。113 年文化統計年報；已核表 7 與表 8 標題和期間。
- `statistics_authority`：高雄市政府主計處；已查入口／待原表。[已查頁](https://kcgdg.kcg.gov.tw/StatWebRWD/Page/)。統計資訊入口及市府網站導覽所列入口；未匯出統計資料庫。
- `open_data_catalog`：高雄市政府主計處／政府資料開放平臺；找到相關來源。[已查頁](https://data.gov.tw/dataset/173509)。統計快報資料集 JSON-LD 與資源目錄。

- 候選 `south-kaohsiung-library-monthly`：[來源](https://www.ksml.edu.tw/form/index.aspx?Parser=28%2C3%2C32)；列 10 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。
- 候選 `south-kaohsiung-culture-113`：[來源](https://khcc.kcg.gov.tw/PhotoData/TyzRJWC16kxBNJp.pdf)；列 1 個資料資源，已驗原檔資料年 [2020, 2021, 2022, 2023, 2024]，授權 `unconfirmed`，未入庫。
- 候選 `south-kaohsiung-statistical-flash`：[來源](https://data.gov.tw/dataset/173509)；列 2 個資料資源，已驗原檔資料年 尚未核定，授權 `OGDL-1.0_catalog_label_pending_file_specific_review`，未入庫。

### 屏東縣

- `library_authority`：屏東縣政府文化處圖書館；已查入口／待原表。[已查頁](https://library.pthg.gov.tw/)。目前館藏查詢入口及舊館網失效狀態；不是營運統計目錄。
- `culture_authority`：屏東縣政府文化處；找到相關來源。[已查頁](https://www.cultural.pthg.gov.tw/News12.aspx?n=FE3F3A54BD25C385&sms=83339E065E5F593D)。業務統計目錄內 109–113 年公共圖書館 5 個詳細頁及 8 個附件，未下載資料檔。
- `statistics_authority`：屏東縣政府主計處；找到相關來源。[已查頁](https://pthg.dgbas.gov.tw/DgbasWeb/index.aspx)。統計年報資料庫目錄與歷史年報目錄。
- `open_data_catalog`：屏東縣政府；已查頁未見營運統計。[已查頁](https://www.pthg.gov.tw/Cus_OpenData_Default1.aspx?n=481C53E05C1D2D97&sms=354B0B57F2762613)。資料開放專區當前頁可見清單，僅本頁；未完成全部分類與後頁查核。

- 候選 `south-pingtung-library-statistics-109-113`：[來源](https://www.cultural.pthg.gov.tw/News12.aspx?n=FE3F3A54BD25C385&sms=83339E065E5F593D)；列 8 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。
- 候選 `south-pingtung-yearbooks`：[來源](https://pthg.dgbas.gov.tw/STATWeb/Page/BookCatalog_Record.aspx?bookname=%E5%B1%8F%E6%9D%B1%E7%B8%A3%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1&orgno=3001&rbno=4&uid=43)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 宜蘭縣

- `library_authority`：宜蘭縣政府文化局文學及圖書資訊科；已查入口／待原表。[已查頁](https://www.ilccb.gov.tw/cp.aspx?n=10213)。文學及圖書資訊科職掌及官方公共圖書館入口；舊館頁失敗另記。
- `culture_authority`：宜蘭縣政府文化局；已查入口／待原表。[已查頁](https://www.ilccb.gov.tw/News.aspx?n=14079&sms=12964)。網站導覽所連業務統計資料頁；回應可讀但未擷取到原統計附件。
- `statistics_authority`：宜蘭縣政府主計處；已查入口／待原表。[已查頁](https://bgacst.e-land.gov.tw/cp.aspx?n=11386&s=6762)。統計刊物專區／統計年報入口與教育文化類別。
- `open_data_catalog`：宜蘭縣政府資料開放平臺；已查頁未見營運統計。[已查頁](https://opendata.e-land.gov.tw/dataset/?q=%E5%9C%96%E6%9B%B8%E9%A4%A8)。依實際公開搜尋表單 GET q=圖書館；兩個結果逐目錄查欄位。

- 候選 `south-yilan-directory-1`：[來源](https://opendata.e-land.gov.tw/dataset/122034-2016-12-16-1481883463)；列 3 個資料資源，已驗原檔資料年 尚未核定，授權 `metadata_license_fields_inconsistent_or_legacy_requires_review`，未入庫。
- 候選 `south-yilan-directory-2`：[來源](https://opendata.e-land.gov.tw/dataset/110013-2020-11-08-1604804585)；列 3 個資料資源，已驗原檔資料年 尚未核定，授權 `metadata_license_fields_inconsistent_or_legacy_requires_review`，未入庫。
- 候選 `south-yilan-yearbooks`：[來源](https://bgacst.e-land.gov.tw/cp.aspx?n=11386&s=6762)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 花蓮縣

- `library_authority`：花蓮縣文化局圖書館；已查入口／待原表。[已查頁](https://library.hccc.gov.tw/)。館網首頁與文化局統計目錄；首頁不是歷年統計全集。
- `culture_authority`：花蓮縣文化局；找到相關來源。[已查頁](https://www.hccc.gov.tw/zh-tw/Download/Statistics/409)。統計報表單頁的 6 群組、46 個附件全清單；圖書館範圍為前兩個 ODS。
- `statistics_authority`：花蓮縣政府主計處；已查入口／待原表。[已查頁](https://hl.dgbas.gov.tw/STATWeb/Page/BookCatalog_Main.aspx)。統計年報與歷史刊物入口；未逐年逐表匯出。
- `open_data_catalog`：花蓮縣政府行研處資訊科；已查入口／待原表。[已查頁](https://ra.hl.gov.tw/Detail_sp/a1b55c83a93a4e9f9f2cb9f1576e26b9)。資料開放平台帳號申請的官方資訊頁，未取得公共 catalog 根入口。

- 候選 `south-hualien-library-lending-409`：[來源](https://www.hccc.gov.tw/zh-tw/Download/Statistics/409)；列 2 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。
- 候選 `south-hualien-library-analysis-411`：[來源](https://www.hccc.gov.tw/zh-tw/Download/Statistics/411)；列 2 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。
- 候選 `south-hualien-yearbooks`：[來源](https://hl.dgbas.gov.tw/STATWeb/Page/BookCatalog_Main.aspx)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 臺東縣

- `library_authority`：臺東縣政府文化處／臺東縣立圖書館；已查入口／待原表。[已查頁](https://culture.taitung.gov.tw/facility/%E8%87%BA%E6%9D%B1%E7%B8%A3%E7%AB%8B%E5%9C%96%E6%9B%B8%E9%A4%A8)。官方館舍介紹、沿革與目前館網連結；未把沿革零星數字當完整館務統計。
- `culture_authority`：臺東縣政府文化處；已查頁未見營運統計。[已查頁](https://culture.taitung.gov.tw/publication)。文化出版品查詢目前頁面；不是完整歷年公務統計索引。
- `statistics_authority`：臺東縣政府主計處；已查入口／待原表。[已查頁](https://taitung.dgbas.gov.tw/StatWebRWD/page/HitCount.aspx?PageName=WebMenu&PageNameC=%e7%b5%b1%e8%a8%88%e5%88%8a%e7%89%a9&Mid=33&Menuid=33&ItemName=%e7%b5%b1%e8%a8%88%e5%88%8a%e7%89%a9&Kind=1)。由已觀察的統計刊物連結跳轉到年報目錄；統計查詢另為 Power BI 外部頁。
- `open_data_catalog`：臺東縣政府；請求失敗／保留缺口。[已查頁](http://www.taitung.gov.tw/opendata/)。既有公開資料專區舊入口，HTTP 404；目前入口未定位。

- 候選 `south-taitung-yearbooks`：[來源](https://taitung.dgbas.gov.tw/StatWebRWD/page/HitCount.aspx?PageName=WebMenu&PageNameC=%e7%b5%b1%e8%a8%88%e5%88%8a%e7%89%a9&Mid=33&Menuid=33&ItemName=%e7%b5%b1%e8%a8%88%e5%88%8a%e7%89%a9&Kind=1)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 澎湖縣

- `library_authority`：澎湖縣政府文化局／澎湖縣圖書館；已查入口／待原表。[已查頁](https://www.phlib.nat.gov.tw/wSite/sp?mp=1&orgId=004&xdUrl=%2FwSite%2FApBlock%2FLibrary.jsp)。澎南分館官方介紹，含館藏時點；不是全縣歷年母體。
- `culture_authority`：澎湖縣政府文化局；找到相關來源。[已查頁](https://www.penghu.gov.tw/uploaddowndoc?file=unit02%2F202508111721160.pdf&filedisplay=113%E6%BE%8E%E6%B9%96%E7%B8%A3%E6%96%87%E5%8C%96%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1.pdf&flag=doc)。113 年文化統計年報 PDF；已核圖書館營運績效表，尚未入庫。
- `statistics_authority`：澎湖縣政府主計處；已查入口／待原表。[已查頁](https://www.penghu.gov.tw/accounting/home.jsp?id=449)。統計年報歷史列表；另核統計資訊網目前刊物入口。
- `open_data_catalog`：澎湖縣政府資料開放平臺；找到相關來源。[已查頁](https://opendata.penghu.gov.tw/zh_Hans_CN/dataset/fs30000-2017-05-31-1496212101)。113 年公共圖書館借閱目錄完整 3 格式資源；授權欄位有衝突。

- 候選 `south-penghu-library-lending-113`：[來源](https://opendata.penghu.gov.tw/zh_Hans_CN/dataset/fs30000-2017-05-31-1496212101)；列 3 個資料資源，已驗原檔資料年 尚未核定，授權 `metadata_conflict_requires_review`，未入庫。
- 候選 `south-penghu-culture-113`：[來源](https://www.penghu.gov.tw/uploaddowndoc?file=unit02%2F202508111721160.pdf&filedisplay=113%E6%BE%8E%E6%B9%96%E7%B8%A3%E6%96%87%E5%8C%96%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1.pdf&flag=doc)；列 1 個資料資源，已驗原檔資料年 [2020, 2021, 2022, 2023, 2024]，授權 `unconfirmed`，未入庫。
- 候選 `south-penghu-yearbooks`：[來源](https://www.penghu.gov.tw/accounting/home.jsp?id=449)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 金門縣

- `library_authority`：金門縣文化局／金門縣立圖書館；已查入口／待原表。[已查頁](https://cabkc.kinmen.gov.tw/informationlists?uid=9)。圖書館服務／公告專區；本輪當前頁沒有完整營運統計批次。
- `culture_authority`：金門縣文化局；已查入口／待原表。[已查頁](https://cabkc.kinmen.gov.tw/archive?uid=6)。組織職掌；確認圖書資訊科職掌，不等同年度統計。
- `statistics_authority`：金門縣政府主計處；找到相關來源。[已查頁](https://kinmen.dgbas.gov.tw/DgbasWeb/statfile3.aspx?cateno=01&mode=2)。統計資料庫指標定義清單與已觀察年報 PXWeb 連結。
- `open_data_catalog`：金門縣政府資料開放平台；請求失敗／保留缺口。[已查頁](https://data.kinmen.gov.tw/Default.aspx?Create=1)。公開資料平台入口請求失敗；不做資料集無資料結論。

- 候選 `south-kinmen-library-count-definition`：[來源](https://kinmen.dgbas.gov.tw/DgbasWeb/statfile3.aspx?cateno=01&mode=2)；列 0 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

### 連江縣

- `library_authority`：連江縣政府文化處／馬祖圖書館；已查入口／待原表。[已查頁](https://www.matsucc.gov.tw/%e6%96%87%e5%8c%96%e8%99%95%e9%a6%ac%e7%a5%96%e5%9c%96%e6%9b%b8%e9%a4%a8/)。馬祖圖書館及各分館官方介紹；不是全年度統計資料集。
- `culture_authority`：連江縣政府文化處；找到相關來源。[已查頁](https://matsucc.gov.tw/%E8%AA%8D%E8%AD%98%E6%96%87%E5%8C%96%E8%99%95/%E9%A0%90%E5%91%8A%E7%B5%B1%E8%A8%88%E6%AA%94%E6%A1%88%E4%B8%8A%E5%82%B3%E5%8D%80/)。預告統計檔案上傳區全部 4 個附件；圖書館範圍只有 114 年 XLSX。
- `statistics_authority`：連江縣政府主計處／政府公開資料服務；已查入口／待原表。[已查頁](https://eip.matsu.gov.tw/matsuopendata/chhtml/dataquery/4?tmpcode=07)。政府公開資料服務的主計處刊物分類；未取得指定圖書館數據表。
- `open_data_catalog`：連江縣政府／政府資料開放平臺；找到相關來源。[已查頁](https://data.gov.tw/dataset/173786)。113 年公共圖書館概況資料集與全部 1 個 ODS distribution。

- 候選 `south-lienchiang-opendata-173786`：[來源](https://data.gov.tw/dataset/173786)；列 1 個資料資源，已驗原檔資料年 尚未核定，授權 `OGDL-1.0_explicit_in_Dataset_JSONLD_and_catalog`，未入庫。
- 候選 `south-lienchiang-culture-library-overview-114`：[來源](https://matsucc.gov.tw/%E8%AA%8D%E8%AD%98%E6%96%87%E5%8C%96%E8%99%95/%E9%A0%90%E5%91%8A%E7%B5%B1%E8%A8%88%E6%AA%94%E6%A1%88%E4%B8%8A%E5%82%B3%E5%8D%80/)；列 1 個資料資源，已驗原檔資料年 尚未核定，授權 `unconfirmed`，未入庫。

## 驗證結果

```json
{
  "county_count": 11,
  "role_count": 44,
  "http_checks_in_private_ledger": 94,
  "retained_original_count_sha_readback": 85,
  "status_counts": {
    "request_failed": 4,
    "checked_relevant_source_found": 16,
    "checked_entry_only": 20,
    "checked_no_relevant_dataset_in_checked_page": 4
  },
  "source_candidate_count": 27,
  "resource_count_in_candidates": 55,
  "new_numeric_observations_ingested": 0,
  "numeric_imputation_count": 0,
  "validation_method": "bundled_local_Python_JSON_schema_checks_and_original_SHA_readback; not_model_generated_counts"
}
```

本輪未聯絡機關、未申請帳號或限用資料、未購買服務，未操作使用者目前畫面。未修改既有觀測／公開 checkout，未提交或推送 GitHub。
