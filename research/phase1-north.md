# 北中11縣市官方來源盤點（第一階段）

查核日：2026-10-26。已逐縣完成44角色的列明頁面查核/失敗紀錄，尚非2005–2025全期來源窮盡，更未新增正式觀測。

完整機器清單：raw/phase1-inventory/county-north.json。每候選保留來源catalog、實際附件或待展開詳情URL、格式、已驗檔內年度/目錄hint分欄、授權與取得狀態。候選數是資源/入口數，不是統計資料列數；CSV/XML/JSON可能為同一數據的不同格式。

body_retained=false代表當時HTTP body僅在RAM，SHA辨識回應版本，不能當原件可readback。後續body_retained=true者已保存私人Drive串流原件與ledger，但尚未雲端讀回，僅標待同步；本facts檔不含其實體路徑。若HTTP200為空body/錯頁或TLS失敗，仍列失敗。

|縣市|圖書館主管|文化主管|主計主管|開放目錄|候選資源/入口|
|---|---|---|---|---|---:|
|臺北市|checked_relevant_source_found|checked_no_relevant_dataset_in_checked_page|checked_relevant_source_found|checked_relevant_source_found|219|
|新北市|checked_entry_only|checked_relevant_source_found|checked_relevant_source_found|checked_relevant_source_found|51|
|基隆市|checked_entry_only|checked_entry_only|checked_relevant_source_found|checked_relevant_source_found|11|
|桃園市|checked_entry_only|checked_relevant_source_found|checked_relevant_source_found|checked_entry_only|2|
|新竹縣|checked_entry_only|checked_relevant_source_found|checked_relevant_source_found|checked_entry_only|4|
|新竹市|checked_entry_only|checked_relevant_source_found|checked_relevant_source_found|checked_relevant_source_found|49|
|苗栗縣|checked_entry_only|checked_no_relevant_dataset_in_checked_page|checked_relevant_source_found|checked_relevant_source_found|6|
|臺中市|checked_relevant_source_found|checked_relevant_source_found|checked_entry_only|checked_relevant_source_found|45|
|彰化縣|checked_relevant_source_found|checked_relevant_source_found|checked_relevant_source_found|checked_no_relevant_dataset_in_checked_page|20|
|南投縣|checked_relevant_source_found|checked_relevant_source_found|checked_entry_only|checked_relevant_source_found|5|
|雲林縣|checked_relevant_source_found|request_failed|checked_entry_only|checked_relevant_source_found|1|

狀態found只表示本次找到相關來源，不能解讀成檔內年表全驗。entry_only僅入口；no_relevant僅該已查頁面；request_failed不推稱官方無公布。搜尋摘要來源另有evidence_level，不冒充全文HTTP讀回。

## 優先系列與可重播線索

- 臺中文化局：索引完整可見104–114年共11份文化統計年報。已讀104年83頁與114年140頁PDF文字，前者表5-1圖書館概況印63–66頁；後者表6-1概況印113–116頁，另列圖書活動、行動圖書車。114年年報封面印115年4月出版，出版年不得當資料年。早期這兩PDF未保留body，不稱本機原件readback。
  https://www.culture.taichung.gov.tw/2061062/2074984/2079404/2079424

- 臺中既有目錄117921四資源、127807十八資源，以及84379借閱、84915購書全部本次JSON-LD格式已列。既有period_effective逐來源精確列在JSON：年度概況2015–2018，其他是零散月份/分館/購書系列；不能把幾個月份當全年。

- 新竹市新增購書/採購五目錄：2017=164573、2018=164572、2019=164571、2020=164570、2021=164569，每目錄四格式完整列明。實檔本輪urllib及系統curl皆TLS驗證失敗，沒有跳過TLS；data_years_verified留空。年份只核目錄標題，不冒稱檔內已驗。
  https://data.gov.tw/dataset/164573

- 新竹市主計年報可見100–114年，舊年部分須詳情頁展開。104年附件IncompleteRead，114年附件HTTP200空body，均不算成功PDF。115借閱檔也失敗，現有2026月資料另列，不當全年。
  https://dep-auditing.hccg.gov.tw/ch/home.jsp?id=10112&parentpath=0%2C3%2C22

- 北市圖工作報告四段：110年至今本頁69個PDF、106–109年48個、101–105年60個、96–100年16個。這是本頁下載URL數，不是各月齊全聲明；全部檔名/URL已留，2026月暫計須另列。另年刊索引尚有分頁，不把首頁當全歷年。
  https://tpml.gov.taipei/News.aspx?n=2E864DF7B9B80664&sms=D68D52DD3BA6F406

- 苗栗主計年報分類04實際列出公共館圖書/期刊/電子書/借閱人次等查詢頁；不沿用其他縣市分類代碼。苗栗公共館主管由教育處圖書資訊科職掌證實，文化局統計頁主要為觀光/古蹟，不能混稱公共館母體。

- 南投109年1月至12月公共館概況1頁PDF已讀期別；本頁另列108/110。新竹縣服務概況7頁PDF明列表1/2為110–112年，但僅文化局本館，不當全縣合計。

- 基隆73325舊目錄官方明示已下架整併；候選保留歷史狀態，不把JSON-LD舊URL當仍可取。雲林年中館藏附件只有官方搜尋摘要，112/6/30不得當全年；文化觀光處現站403。

## 各角色實際入口與限制

### 臺北市

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。

- library_authority：臺北市立圖書館；checked_relevant_source_found
  https://tpml.gov.taipei/News.aspx?_CSN=8B955A773A9CA3D7&n=CCE9A5BD7807F8A9&sms=EBF5ED68A2F6E55D
- culture_authority：臺北市政府文化局；checked_no_relevant_dataset_in_checked_page
  https://culture.gov.taipei/News.aspx?n=A8119241A80ABDDB&sms=1383E2E37FFBDF0E
- statistics_authority：臺北市政府主計處；checked_relevant_source_found
  https://dbas.gov.taipei/News_Content.aspx?n=72EB69FFAC3565DF&s=E53B12DEEB01184E&sms=96C0B436A542605B
- open_data_catalog：臺北市政府主計處／政府資料開放平臺；checked_relevant_source_found
  https://data.gov.tw/dataset/131724

### 新北市

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。

- library_authority：新北市立圖書館；checked_entry_only
  https://www.library.ntpc.gov.tw/multiplehtml/362b256880954587af96d285bc46e72c
- culture_authority：新北市政府文化局；checked_relevant_source_found
  https://www.culture.ntpc.gov.tw/xmfile?xsmsid=0G289525863862276539
- statistics_authority：新北市政府主計處；checked_relevant_source_found
  https://www.bas.ntpc.gov.tw/home.jsp?id=468e7f1294d86c36
- open_data_catalog：新北市政府主計處／資料開放平臺；checked_relevant_source_found
  https://data.ntpc.gov.tw/datasets/173f88e4-7718-4fcd-a32c-467f78aeffc8

### 基隆市

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。

- library_authority：基隆市文化觀光局／公共圖書館；checked_entry_only
  https://kllib.klcg.gov.tw/
- culture_authority：基隆市文化觀光局；checked_entry_only
  https://klctb.klcg.gov.tw/
- statistics_authority：基隆市政府主計處；checked_relevant_source_found
  https://www.klcg.gov.tw/tw/klcg1/2420.html
- open_data_catalog：基隆市文化局／政府資料開放平臺；checked_relevant_source_found
  https://data.gov.tw/dataset/73325

### 桃園市

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。 圖書館Statistical及Research兩頁僅取得前端外殼，文化局另見107–108借閱分析；不拿其他文化場館統計充當公共館。

- library_authority：桃園市立圖書館；checked_entry_only
  https://www.typl.gov.tw/zh-tw/About/Research
- culture_authority：桃園市政府文化局；checked_relevant_source_found
  https://culture.tycg.gov.tw/News.aspx?n=11157&sms=14593
- statistics_authority：桃園市政府主計處；checked_relevant_source_found
  https://statisticsinfo.tycg.gov.tw/TaoyuanSTYB/DownLoadConfirmSTYReport.aspx
- open_data_catalog：桃園市政府／資料開放平台；checked_entry_only
  https://opendata.tycg.gov.tw/

### 新竹縣

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。

- library_authority：新竹縣政府文化局／公共圖書館；checked_entry_only
  https://www.hchcc.gov.tw/Tw/Service/Detail?filter=5099a13a-9328-45f1-ba2b-fd30e7e6eb6b&id=ffee6f83-ff6b-419b-9837-192aa8fc091f
- culture_authority：新竹縣政府文化局；checked_relevant_source_found
  https://www.hchcc.gov.tw/Tw/common/Downloader?id=873db808-3811-4f67-8efb-ba2fb0cc735e
- statistics_authority：新竹縣政府主計處；checked_relevant_source_found
  https://hsinchu.dgbas.gov.tw/statweb/Page/BookCatalog_Main.aspx
- open_data_catalog：新竹縣政府；checked_entry_only
  https://www.hsinchu.gov.tw/OpenData

### 新竹市

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。 2017–2021購書五目錄各四格式全列；odws附件urllib與curl皆失敗，檔內年未驗。104主計PDF為IncompleteRead，114主計PDF為HTTP200空body，均不稱取得原件。2026借閱單月不當全年。

- library_authority：新竹市文化局圖書館；checked_entry_only
  https://library.hccg.gov.tw/
- culture_authority：新竹市文化局；checked_relevant_source_found
  https://culture.hccg.gov.tw/uploaddowndoc?file=infopublic%2F201908260952520.pdf&filedisplay=107%E5%B9%B4%E9%87%8D%E8%A6%81%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1.pdf&flag=doc
- statistics_authority：新竹市政府主計處；checked_relevant_source_found
  https://dep-auditing.hccg.gov.tw/uploaddowndoc?file=StatisticalYearbook/202610111559140.pdf&filedisplay=114%E6%96%B0%E7%AB%B9%E5%B8%82%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1.pdf&flag=doc
- open_data_catalog：新竹市文化局／政府資料開放平臺；checked_relevant_source_found
  https://data.gov.tw/dataset/164570

### 苗栗縣

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。

- library_authority：苗栗縣政府教育處圖書資訊科；checked_entry_only
  https://www.mlc.edu.tw/System/bis/Org/Member.php
- culture_authority：苗栗縣政府文化觀光局；checked_no_relevant_dataset_in_checked_page
  https://www.mlc.gov.tw/form/index.aspx?Parser=28,10,124
- statistics_authority：苗栗縣政府主計處；checked_relevant_source_found
  https://miaoli.dgbas.gov.tw/DgbasWeb/statfile2.aspx?Mode=3&CateNo=04
- open_data_catalog：苗栗縣政府／政府資料開放平臺；checked_relevant_source_found
  https://data.gov.tw/dataset/173129

### 臺中市

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。

- library_authority：臺中市立圖書館；checked_relevant_source_found
  https://www.library.taichung.gov.tw/form/index?Parser=28%2C3%2C98%2C32%2C76
- culture_authority：臺中市政府文化局；checked_relevant_source_found
  https://www.culture.taichung.gov.tw/media/1433826/114文化局統計年報-410-陳核稿.pdf
- statistics_authority：臺中市政府主計處；checked_entry_only
  https://govstat.taichung.gov.tw/DgbasWeb/statfile3.aspx?cateno=01&mode=2
- open_data_catalog：臺中市政府文化局／政府資料開放平臺；checked_relevant_source_found
  https://data.gov.tw/dataset/84915

### 彰化縣

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。 開放資料角色目前僅舊跨機關服務系統；圖書館政府出版品目錄非館務統計，仍待沿文化局年報及主計附表確認。

- library_authority：彰化縣文化局圖書館；checked_relevant_source_found
  https://lib.bocach.gov.tw/cp.aspx?n=967
- culture_authority：彰化縣文化局；checked_relevant_source_found
  https://ws.bocach.gov.tw/Download.ashx?icon=.pdf&n=MTEy5bm05b2w5YyW57ij5paH5YyW5bGA57Wx6KiI5bm05aCxLnBkZg%3D%3D&u=LzAwMS9VcGxvYWQvMS9yZWxmaWxlLzk5OTQvNDkzODMvN2NiYTZiMzEtMGQ1Zi00MTRmLTk4MDMtNGM0MTM5ZTJkZDhjLnBkZg%3D%3D
- statistics_authority：彰化縣政府主計處；checked_relevant_source_found
  https://ctrl.chcg.gov.tw/main/main_act3/main.aspx?act_id=413&main_id=30276
- open_data_catalog：彰化縣政府；checked_no_relevant_dataset_in_checked_page
  https://data.chcg.gov.tw/

### 南投縣

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。

- library_authority：南投縣政府文化局圖書科／圖書館；checked_relevant_source_found
  https://www.nthcc.gov.tw/A6_3/list/2
- culture_authority：南投縣政府文化局；checked_relevant_source_found
  https://www.nthcc.gov.tw/Uploads/userfile/A6_3/2021-04-21_0809106229.pdf
- statistics_authority：南投縣政府主計處；checked_entry_only
  https://www.nantou.gov.tw/big5/bureau/content.php?cid=1386&dptid=376480000AU230000
- open_data_catalog：南投縣政府／政府資料開放平臺；checked_relevant_source_found
  https://data.gov.tw/dataset/168915

### 雲林縣

已逐角色查明列URL，候選只及本輪可見索引/附件/JSON-LD。未找到只限已查頁面；未宣稱2005–2025全期齊全。沒有新增正式觀測、登入後端、限用申請或外聯。 文化觀光處現站HTTP403，稅務局線索已排除；主計歷史頁互動外殼未展開，待後續正常公開查詢。

- library_authority：雲林縣政府文化觀光處圖書館；checked_relevant_source_found
  https://lib.ylccb.gov.tw/wSite/public/Attachment/f1704252060713.pdf
- culture_authority：雲林縣政府文化觀光處；request_failed
  https://content.yunlin.gov.tw/
- statistics_authority：雲林縣政府主計處；checked_entry_only
  https://yunlin.dgbas.gov.tw/STATWeb/Page/BookCatalog_Record.aspx?bookname=%E9%9B%B2%E6%9E%97%E7%B8%A3%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1&orgno=3001&rbno=1&uid=37
- open_data_catalog：雲林縣政府；checked_relevant_source_found
  https://opendata.yunlin.gov.tw/OpenDataList.aspx?kw=%E6%95%99%E8%82%B2&n=8350

## 權利、完整性與後續

data.gov.tw明列license URL的目錄標verified_open，證據為本次Dataset JSON-LD；一般政府PDF、年報不因.gov.tw推定全文授權，標not_confirmed。只整理必要統計facts/links/短摘錄，未散布完整PDF、HTML、PNG、cookie或聯絡值。

complete_resource_list=true僅表示該次具體catalog response的全部JSON-LD distributions已列，完全不表示2005–2025全期或縣市全部資源完整。其他索引一律只限可見頁面；詳情頁/下一頁未處理者仍待辦，沒有以未查到宣稱不存在。

PDF探查限文字、表目與明列期別，不是逐頁影像或逐格校對。固定清理/計數/期間列舉由Python完成；沒有模型推算缺值或數據。所有尚未下載/解析候選均不稱已入庫。

機器計數：{"counties": 11, "authority_slots": 44, "checks_including_shared_rejected": 91, "unique_checked_urls": 88, "candidate_resources": 413, "retained_response_checks": 9, "role_status_counts": {"checked_relevant_source_found": 28, "checked_no_relevant_dataset_in_checked_page": 3, "checked_entry_only": 12, "request_failed": 1}, "candidate_unique_target_urls": 413}
