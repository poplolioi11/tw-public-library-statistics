# 官方來源分類與補齊清單

查核日：2026-10-25。本清單盤點來源與後續批次；主計縣市館數於同日後續批次完成並回填，排程另由本機部署管理。

## 已完成範圍的界線

- 2011–2025已完整的是公開10類全國圖表。
- 2023是目前唯一證實同一6425官方OGDL年度縣市包。
- NCL3年只完整指定表，而非整冊。
- 其他縣市地方統計尚未逐機關核查。

未查、下載逾時或舊連結失效都不等於無資料。以完整來源包與可核對表為完成單位，不用新增縣市數量代表進度。

## 來源家族

### nlpi_public_national_charts

**主管／提供機關：**國立公共資訊圖書館。狀態：`completed_bounded_scope`。

**已完成：**2011–2025已完整的是公開10類全國圖表；不是每年完整縣市包或單館資料。

官方入口：
- [https://publibstat.nlpi.edu.tw/Frontend/Dynamic/ImportantInfomation](https://publibstat.nlpi.edu.tw/Frontend/Dynamic/ImportantInfomation)
- [https://publibstat.nlpi.edu.tw/Frontend/Point/Index](https://publibstat.nlpi.edu.tw/Frontend/Point/Index)

**明確尚未入庫／未處理：**
- 公開10類以外的其他主題未因此視為已完成。
- 縣市、圖書館層級及各館年度資料未由此圖表批次完成。

**尚未查明：**
- 每年來源回傳0是否為實測0、未蒐集或系統補零，不能單憑回應判定。
- 歷史修訂版及新增主題的官方發布時點尚未全面追蹤。

**授權界線：**保留現行公開指標供應範圍與2026公告證據；不泛用至未公開層級。

已完成證據：`research/source-verification.md`、`research/acquisition.md`。

### nlpi_ogdl_6425

**主管／提供機關：**國立公共資訊圖書館（data.gov.tw分發目錄）。狀態：`completed_bounded_scope`。

**已完成：**2023是目前唯一已證實以同一6425官方OGDL分發資源對應的年度縣市包。

官方入口：
- [https://data.gov.tw/dataset/6425](https://data.gov.tw/dataset/6425)
- [https://publibstat.nlpi.edu.tw/api/API/ConsolidationData?Year=2023](https://publibstat.nlpi.edu.tw/api/API/ConsolidationData?Year=2023)

**明確尚未入庫／未處理：**
- 2011–2022、2024–2025未納入同等授權已證年度縣市包。
- 各館年度營運包尚未取得同等公開授權鏈。

**尚未查明：**
- 2024、2025 API曾技術回應26列87欄，仍未核得各自具體年度開放分發版本；技術可下載不等於再公開授權。
- 其他年份過去是否有已明示OGDL的正式分發版本，尚未找到完整版本鏈；不可說它們從未公開。

**授權界線：**已確認的6425 Year=2023分發資源為OGDL1；申請限用或登入資料不自動適用。

已完成證據：`research/acquisition.md`、`research/endpoints.json`、`research/source-verification.md`。

### ncl_yearbook_public_library_chapters

**主管／提供機關：**國家圖書館；各卷公共圖書館章署名作者與當時資料提供機關另記。狀態：`partially_completed_known_tables`。

**已完成：**NCL這3個資料年只完整指定表，而非整冊、整章或所有統計表。

官方入口：
- [https://www.ncl.edu.tw/librarianship-yearbook](https://www.ncl.edu.tw/librarianship-yearbook)
- [https://www.ncl.edu.tw/librarianship-yearbook?page=2](https://www.ncl.edu.tw/librarianship-yearbook?page=2)
- [https://www.ncl.edu.tw/librarianship-yearbook?page=3](https://www.ncl.edu.tw/librarianship-yearbook?page=3)

**明確尚未入庫／未處理：**
- 2008年：館數交叉表；PDF第2頁／印刷78頁；正式表號待影像再核。已下載原檔，尚未完整表格擷取。
- 2008年：人員及服務表；PDF第4頁／印刷80頁；正式表號待影像再核。文字層數字黏連，尚未完成可靠逐格解析。
- 2009年：表1：公立公共圖書館館數；PDF第2頁／印刷74頁。已下載原檔，尚未入庫。
- 2010年：表1：公立公共圖書館館數；PDF第2頁／印刷34頁。已下載原檔，尚未入庫。

**尚未查明：**
- 97年及以前、101年及以後各卷的資料年、完整公共館表、欄位與修訂情形，除既有明列研究外尚未逐卷盤點。
- 新版列表29筆只證明入口可見，不能證明每卷有相同欄位、可讀文字層或完整縣市資料。
- 年鑑標年、出版年與表內資料年不能互換；早期跨年卷須按表逐一確認。

**授權界線：**署名專章全文PDF授權未確認；本機保存原檔，公開衍生表只取統計事實與來源定位，不轉發全文/影像。

已完成證據：`research/ncl-historical-verification.md`、`research/official-scope.md`、`raw/ncl-historical/documents.json`。

### dgbas_social_indicator_history

**主管／提供機關：**行政院主計總處（舊稱行政院主計處）。狀態：`completed_bounded_scope`。

**已完成：**完整的是3個已列官方版本中的公立公共圖書館指標區塊，不是全部社會指標年報或縣市指標。

官方入口：
- [https://ws.dgbas.gov.tw/public/data/331311404571.pdf](https://ws.dgbas.gov.tw/public/data/331311404571.pdf)
- [https://ws.dgbas.gov.tw/001/Upload/466/ebook/ebook_88839/pdf/full.pdf](https://ws.dgbas.gov.tw/001/Upload/466/ebook/ebook_88839/pdf/full.pdf)
- [https://ws.dgbas.gov.tw/public/attachment/211231530971.pdf](https://ws.dgbas.gov.tw/public/attachment/211231530971.pdf)

**明確尚未入庫／未處理：**
- 3份PDF中其他領域未匯入，屬有意排除，不能當公共館缺值。
- 2005版最後年4格原刊…，保留缺值，不能補成0。

**尚未查明：**
- 1991以前、2011以後及其他年報版本的官方公共館歷史表尚未系統盤點。
- 各版對同年數值的修訂關係及國立館/國家圖書館納入細節，未逐年完全釐清。

**授權界線：**已核官方網站OGDL1宣告；適用本次擷取的機關統計表，第三方另聲明素材仍有例外。

已完成證據：`research/ncl-historical-verification.md`、`research/dgbas-historical-validation.json`、`raw/ncl-historical/dgbas-documents.json`。

### local_explicit_ogdl_catalogs

**主管／提供機關：**臺中市政府及新竹市政府之實際資料提供機關；各目錄owner保留在原metadata。狀態：`completed_bounded_scope`。

**已完成：**完整取得上述14個明確OGDL目錄所列資源；不是臺中/新竹全部地方統計已完成。

官方入口：
- [https://data.gov.tw/dataset/117921](https://data.gov.tw/dataset/117921)
- [https://data.gov.tw/dataset/127807](https://data.gov.tw/dataset/127807)
- [https://data.gov.tw/dataset/130199](https://data.gov.tw/dataset/130199)
- [https://data.gov.tw/dataset/164568](https://data.gov.tw/dataset/164568)
- [https://data.gov.tw/dataset/164575](https://data.gov.tw/dataset/164575)
- [https://data.gov.tw/dataset/164576](https://data.gov.tw/dataset/164576)
- [https://data.gov.tw/dataset/164577](https://data.gov.tw/dataset/164577)
- [https://data.gov.tw/dataset/164579](https://data.gov.tw/dataset/164579)
- [https://data.gov.tw/dataset/164580](https://data.gov.tw/dataset/164580)
- [https://data.gov.tw/dataset/168119](https://data.gov.tw/dataset/168119)
- [https://data.gov.tw/dataset/173850](https://data.gov.tw/dataset/173850)
- [https://data.gov.tw/dataset/177249](https://data.gov.tw/dataset/177249)
- [https://data.gov.tw/dataset/84379](https://data.gov.tw/dataset/84379)
- [https://data.gov.tw/dataset/84915](https://data.gov.tw/dataset/84915)

**明確尚未入庫／未處理：**
- 臺中已列目錄未出現的其他年份/月分，尚未從其他官方系列補齊。
- 新竹2026年9月以後尚不在本次成功取得範圍；不能判定來源尚未發布。

**尚未查明：**
- 其他縣市地方統計尚未逐機關核查；臺中/新竹其他主管機關、統計年報與舊版網站亦未窮盡。
- 目錄標年與檔內統計年月不一致時要保留版本，不可硬套標題年。

**授權界線：**OGDL判斷只及上述具體目錄明列資源。

已完成證據：`research/local-history.md`、`research/source-verification.md`。

### segis_public_library_counts

**主管／提供機關：**內政部SEGIS平台；各產品實際提供機關待逐筆核對。狀態：`catalog_confirmed_acquisition_incomplete`。

**已完成：**已讀官方目錄，確認民國95–114年全國/縣市公立公共圖書館數線索；尚未取得底層整包。

官方入口：
- [https://segis.moi.gov.tw/STATCloud/Catalog](https://segis.moi.gov.tw/STATCloud/Catalog)

**明確尚未入庫／未處理：**
- 目錄所見95–114年公立公共圖書館數產品均尚未正式入庫。

**尚未查明：**
- 底層下載格式、產品識別碼、個別授權、國家/國立館納入與資料年定義仍待確認。
- 前端腳本本輪逾時，屬取得未完成，不能標成無公開資料。

**授權界線：**未確認個別產品授權，不用平台名稱或gov網域替代授權證據。

已完成證據：`research/local-history.md`。

### dgbas_county_indicators

**主管／提供機關：**行政院主計總處，指標資料來源教育部。狀態：`completed_bounded_scope`。

已取得[官方公開查詢](https://winstacity.dgbas.gov.tw/DgbasWeb/ZWeb/StateFile_ZWeb.aspx?Type=table)指標Z091101a029的全部選單年度與地區：1998–2025共28年×22縣市及總計23欄＝644來源格。1998–2005為184格官方明示缺值；有數值範圍是2006–2025，共460格。不是28年都有數值。

地區為官方「改制後縣市別」，2006–2010亦依官方重編範圍；母體包括國家圖書館、國立公共資訊圖書館及國立臺灣圖書館，不直接接NLPI公共館數。母站開放宣告與子站適用的推論標記保留於每筆。原始全表資料格、查詢參數、原始HTML雜湊、完整取得腳本與驗收均保留；公開包不再散布完整HTML。

完成證據：`derived/dgbas_county_historical_long.csv`、`raw/segis-history/metadata.json`、`research/segis-acquisition.md`。後續依原來源更新，不重新當作待取得任務。

### ncl_all_type_statistical_chapters

**主管／提供機關：**國家圖書館。狀態：`reference_only_mixed_scope`。

**已完成：**100年鑑圖書館統計章僅為口徑參考；未把各類型全表匯入公共館統計。

官方入口：
- [https://www.ncl.edu.tw/files/file_pool/1/0Q083565498436657138/44dcadf4-3eb1-4dd5-9d23-9ffa6632d41c.pdf](https://www.ncl.edu.tw/files/file_pool/1/0Q083565498436657138/44dcadf4-3eb1-4dd5-9d23-9ffa6632d41c.pdf)
- [https://libstat.ncl.edu.tw/dynamicreport/9af813704342469f9ebbecd93a94f527](https://libstat.ncl.edu.tw/dynamicreport/9af813704342469f9ebbecd93a94f527)

**明確尚未入庫／未處理：**
- 100年鑑表100/101的各類型數量/基本資料表未作公共館正式長表。

**尚未查明：**
- 公共館列是否同時含公立/私立、回覆率及與公立公共館章的關係須逐表再核。
- 國圖現行動態報表各類型可用資料未逐類核；不得把學校/大專館填入公共館缺口。

**授權界線：**統計事實與全文/文章授權分別處理。

已完成證據：`research/official-scope.md`。

## 建議批次順序

| 批次 | 優先 | 狀態 | 工作 | 一批的界線 |
|---|---:|---|---|---|
| B01 | 1 | todo_source_confirmed | 先完成已下載3卷的未入庫表 | 一張表完成、核對並記錄後再處理下一張 |
| B02 | 2 | todo_catalog_confirmed | 完成一個SEGIS公立公共館產品的正式取得 | 先一個產品，再完整其可下載年份 |
| B03 | 3 | todo_official_entry_confirmed | 由97年卷往前逐卷完成公共館年度表 | 每批一卷，先做章節及表清單，再完成該卷核心表 |
| B04 | 3 | todo_rights_and_version_chain | 補其他年度縣市包的官方分發授權鏈 | 每次一個有官方分發線索的年度 |
| B05 | 4 | todo_known_local_series_gap | 補臺中與新竹已確認系列的期間缺口 | 一次一個官方系列的全部資源 |
| B06 | 5 | unknown_not_checked_by_agency | 其他縣市逐機關盤點與完整單包取得 | 每批一縣市、一機關或一來源系列，先完成再擴張 |
| B07 | 5 | todo_official_entry_confirmed | 盤點1991以前及其他年報版本 | 先一個確切官方版本的公共館區塊 |
| B08 | 5 | todo_catalog_definition_seen | 核實縣市指標Z091101a029全量年度表 | 先一個指標完整可得年份 |

### B01 先完成已下載3卷的未入庫表

2008館數與人力服務；2009/2010表1館數；正式表號與頁碼先對原影像。

驗收條件：
- 逐格保留全部資料列、空白與異質單位，補PDF頁/印刷頁/表/列/欄定位。
- 館數表可能將國立館按所在地交叉列，不能沿用館藏表的排除口徑。
- 先驗表頭、人員欄順序及全國組成總和，遇到官方差異保留原值另記。

待查：2008人力表的數字黏連是否可可靠按座標解析，未確認。

### B02 完成一個SEGIS公立公共館產品的正式取得

核實95–114目錄線索的下載格式、授權與母體，再取完整可下載表。

驗收條件：
- 先讀官方目錄與正常前端下載說明，不猜API或繞登入。
- 保存產品id、授權原文與來源機關、全部年份列數和雜湊。
- 明確區分圖書館數與服務站/閱覽室，確認是否包含國家/國立館。

待查：格式/下載權限/授權尚未確認；失敗不等於不存在。

### B03 由97年卷往前逐卷完成公共館年度表

依新版官方入口延伸97、96、95年卷；實際資料年逐表核定，不預先扣一年。

驗收條件：
- 不能只下載目錄就記為完成統計。
- 保留舊行政區、國立館另列與公私立分類，不強轉今日22縣市。
- 無文字層或表格缺漏時如實留unknown，不猜數字。

待查：各卷表格數、資料年、文字層與統計完整率尚未逐卷確認。

### B04 補其他年度縣市包的官方分發授權鏈

找具體年度的正式資源、歷史目錄版本或開放頁；先釐清授權才納入對外年度縣市包。

驗收條件：
- Year參數能下載只記技術證據，不當作年度OGDL證據。
- 保存具體下載URL、統計年、發布/更新/抓取日及授權版本。
- 不呼叫Backend匯出或登入資料，不把申請限用資料公開。

待查：其他年度是否曾有不可撤回的既有開放版，尚未找到完整來源鏈。

### B05 補臺中與新竹已確認系列的期間缺口

先確認既有目錄是否新增期間或變更內容，再找相鄰官方年份；不得只加新縣市數。

驗收條件：
- 以檔內統計年月優先；標題年有差異要保留。
- 月分齊全與應填館別完整分別驗證。
- 重複來源保留追溯；異值版本不得靜默覆寫。

待查：未出現在既有目錄的期間是否另由地方統計年報提供，尚未查明。

### B06 其他縣市逐機關盤點與完整單包取得

其他20縣市及臺中/新竹未涵蓋機關均尚未逐機關查核。

驗收條件：
- 先記主管機關、統計主管機關、圖書館與開放平台的實際入口。
- 有合格來源則取全部可下載表；未找到只記本輪未找到。
- 列出政策/聯絡/熱門書清單等錯範圍排除原因，不為湊數納入。

待查：完整官方地方統計來源地圖尚未建立；不能標成各縣市無資料。

### B07 盤點1991以前及其他年報版本

沿官方年報入口找更早或較新的可取得歷史指標，不沿用猜測檔名大量探測。

驗收條件：
- 保留版本、每個同年異值與定義註腳。
- 1998/1999分館排除、早年閱覽/借閱及中英文註差異必須隨值保留。
- 藏書千冊不能與NCL含非書電子資源的總館藏混接。

待查：1991以前可下載版本及2012以後同系列延續情形尚未全面核實。

### B08 核實縣市指標Z091101a029全量年度表

核對下載、授權、年份及納入國家圖書館的範圍，保留為獨立來源家族。

驗收條件：
- 不能將此指標直接當NLPI同母體館數。
- 保留各年行政區與原單位，完整取可下載表。

待查：此輪僅見定義，尚無可入庫實際表。

## NCL新版年鑑入口盤點

官方列表本輪3頁共29筆。以下僅列可見入口；除98/99/100年卷已核指定表外，其他卷的資料年、表清單與下載完整性仍是待查。不能把年鑑標年或出版年直接當成資料年。

| 年鑑原名 | 官方新版頁面 | 已驗資料年 | 狀態 |
|---|---|---|---|
| 中華民國一一四年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q274523227242755591) | 未確認 | 只核目錄入口 |
| 中華民國一一三年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566989318922413) | 未確認 | 只核目錄入口 |
| 中華民國一一二年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566974538712820) | 未確認 | 只核目錄入口 |
| 中華民國一一一年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566960460238329) | 未確認 | 只核目錄入口 |
| 中華民國一一O年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566955493654718) | 未確認 | 只核目錄入口 |
| 中華民國一○九年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566931435160107) | 未確認 | 只核目錄入口 |
| 中華民國一O八年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566927823718578) | 未確認 | 只核目錄入口 |
| 中華民國一O七年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566871687476012) | 未確認 | 只核目錄入口 |
| 中華民國一O六年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566866897276439) | 未確認 | 只核目錄入口 |
| 中華民國一O五年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565641689945340) | 未確認 | 只核目錄入口 |
| 中華民國一O四年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565626433613784) | 未確認 | 只核目錄入口 |
| 中華民國一O三年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565350919926814) | 未確認 | 只核目錄入口 |
| 中華民國一O二年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565374511489343) | 未確認 | 只核目錄入口 |
| 中華民國一O一年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565430946568943) | 未確認 | 只核目錄入口 |
| 中華民國一百年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565466726779537) | 2010 | 只完成指定表 |
| 中華民國九十九年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565491338132165) | 2009 | 只完成指定表 |
| 中華民國九十八年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565548575038748) | 2008 | 只完成指定表 |
| 中華民國九十七年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565555623845321) | 未確認 | 只核目錄入口 |
| 中華民國九十六年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565568411570887) | 未確認 | 只核目錄入口 |
| 中華民國九十五年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565572390216434) | 未確認 | 只核目錄入口 |
| 中華民國九十四年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565585645073973) | 未確認 | 只核目錄入口 |
| 中華民國九十三年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565582148900528) | 未確認 | 只核目錄入口 |
| 中華民國九十二年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565619396807101) | 未確認 | 只核目錄入口 |
| 中華民國九十一年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566087370545104) | 未確認 | 只核目錄入口 |
| 中華民國九十年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565818875133522) | 未確認 | 只核目錄入口 |
| 中華民國八十九年圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565657469156923) | 未確認 | 只核目錄入口 |
| 第三次中華民國圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566284973572760) | 未確認 | 只核目錄入口 |
| 第二次中華民國圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566602665258360) | 未確認 | 只核目錄入口 |
| 中華民國圖書館年鑑 | [入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566755809015809) | 未確認 | 只核目錄入口 |

## 尚未逐機關核查的地方範圍

臺北市、新北市、桃園市、臺南市、高雄市、基隆市、新竹縣、苗栗縣、彰化縣、南投縣、雲林縣、嘉義市、嘉義縣、屏東縣、宜蘭縣、花蓮縣、臺東縣、澎湖縣、金門縣、連江縣。臺中市與新竹市也只是已列14個具體目錄完整，未代表兩地所有機關、所有年度與館別均已窮盡。

機器可讀的同份清單在 `source-backlog.json`。所有待辦都應新增實際來源證據再更新狀態；沒有取得表前，不記為完成，也不記為不存在。
