# 第一階段：來源與缺口矩陣

資料版本v0.6.0；盤點範圍2005–2025。全臺所有歷年仍未齊全，這份矩陣不認證跨年可比。

22縣市×4角色，共88個指定入口查核槽位；有記錄的查核嘗試88個。HTTP失敗、只查入口及已見相關表分列，不把連線成功當整機關查核完整。

目前正式37,887筆全部分入23,466個原來源／原指標／母體／期間／版次組，沒有合併數值或重編行政區。4,830個年×導航地區×主題格只是資料出現索引，不是完整指標或可比面板。

## 下載與重現

- [來源清單JSON](phase1-source-inventory.json)與[進度摘要](phase1-summary.json)。
- [角色查核CSV](../derived/phase1_authority_checks.csv)、[候選來源CSV](../derived/phase1_source_candidates.csv)。
- [年／地區／主題索引CSV](../derived/phase1_discovery_matrix.csv)、[逐來源口徑CSV](../derived/phase1_raw_source_profiles.csv)。
- 同名JSONL為同一批資料；[SQLite](../derived/phase1_inventory.sqlite)有四個同名表。
- 以`python scripts/build_phase1_inventory.py --require-survey-complete`重建；輸入與規則雜湊在摘要中。

## 如何讀完整度

來源查核、表格批次完成、原格有值是三個不同分母。原刊留白／未統計／明示缺值不算有值，也不改0；未取得、權利待確認與尚未查不能混成無資料。候選來源僅表示已定位，未有完整來源批次驗收前不算已入庫。

原標籤與每組來源網址、SHA、觀測ID仍保留。現行22縣市導航不會將臺北縣改成新北市，也不會將舊臺南縣市加總；舊名稱在逐來源口徑清單獨立呈現。未確認的2015/2024縣市標籤不計為已確認縣市值。

十個主題只作搜尋分類，不能把同一主題的冊／件／種、預算／決算、場次／人次相加。所有原指標保留；未能依原欄標確定主題的觀測列在逐來源清單，不猜分類。

2012縣市核心原量仍未取得，不由比率反算。2026月值／暫計與1991–2004既有資料保留在正式資料和逐來源清單，不冒稱本期核心範圍完整。

原始HTML可能含聯絡資訊，保持私人研究來源；公開清單只保留必要事實、短定位、URL與原件SHA。取得公開頁不等於已確認其所有附件可再散布。

## 各縣市角色查核

|縣市|圖書館|文化|主計／統計|開放資料|
|---|---|---|---|---|
|臺北市|[checked_relevant_source_found](https://tpml.gov.taipei/News.aspx?_CSN=8B955A773A9CA3D7&n=CCE9A5BD7807F8A9&sms=EBF5ED68A2F6E55D)|[checked_no_relevant_dataset_in_checked_page](https://culture.gov.taipei/News.aspx?n=A8119241A80ABDDB&sms=1383E2E37FFBDF0E)|[checked_relevant_source_found](https://dbas.gov.taipei/News_Content.aspx?n=72EB69FFAC3565DF&s=E53B12DEEB01184E&sms=96C0B436A542605B)|[checked_relevant_source_found](https://data.gov.tw/dataset/131724)|
|新北市|[checked_entry_only](https://www.library.ntpc.gov.tw/multiplehtml/362b256880954587af96d285bc46e72c)|[checked_relevant_source_found](https://www.culture.ntpc.gov.tw/xmfile?xsmsid=0G289525863862276539)|[checked_relevant_source_found](https://www.bas.ntpc.gov.tw/home.jsp?id=468e7f1294d86c36)|[checked_relevant_source_found](https://data.ntpc.gov.tw/datasets/173f88e4-7718-4fcd-a32c-467f78aeffc8)|
|基隆市|[checked_entry_only](https://kllib.klcg.gov.tw/)|[checked_entry_only](https://klctb.klcg.gov.tw/)|[checked_relevant_source_found](https://www.klcg.gov.tw/tw/klcg1/2420.html)|[checked_relevant_source_found](https://data.gov.tw/dataset/73325)|
|桃園市|[checked_entry_only](https://www.typl.gov.tw/zh-tw/About/Research)|[checked_relevant_source_found](https://culture.tycg.gov.tw/News.aspx?n=11157&sms=14593)|[checked_relevant_source_found](https://statisticsinfo.tycg.gov.tw/TaoyuanSTYB/default.aspx)|[checked_entry_only](https://opendata.tycg.gov.tw/)|
|新竹縣|[checked_entry_only](https://www.hchcc.gov.tw/Tw/Service/Detail?filter=5099a13a-9328-45f1-ba2b-fd30e7e6eb6b&id=ffee6f83-ff6b-419b-9837-192aa8fc091f)|[checked_relevant_source_found](https://www.hchcc.gov.tw/Tw/common/Downloader?id=873db808-3811-4f67-8efb-ba2fb0cc735e)|[checked_relevant_source_found](https://accounting.hsinchu.gov.tw/cl.aspx?n=771)|[checked_entry_only](https://www.hsinchu.gov.tw/OpenData)|
|新竹市|[checked_entry_only](https://library.hccg.gov.tw/)|[checked_relevant_source_found](https://culture.hccg.gov.tw/uploaddowndoc?file=infopublic%2F201908260952520.pdf&filedisplay=107%E5%B9%B4%E9%87%8D%E8%A6%81%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1.pdf&flag=doc)|[checked_relevant_source_found](https://dep-auditing.hccg.gov.tw/ch/home.jsp?id=10112&parentpath=0%2C3%2C22)|[checked_relevant_source_found](https://data.gov.tw/dataset/164570)|
|苗栗縣|[checked_entry_only](https://www.mlc.edu.tw/System/bis/Org/Member.php)|[checked_no_relevant_dataset_in_checked_page](https://www.mlc.gov.tw/form/index.aspx?Parser=28,10,124)|[checked_relevant_source_found](https://miaoli.dgbas.gov.tw/DgbasWeb/statfile2.aspx?Mode=3&CateNo=04)|[checked_relevant_source_found](https://data.gov.tw/dataset/173129)|
|臺中市|[checked_relevant_source_found](https://www.library.taichung.gov.tw/form/index?Parser=28%2C3%2C98%2C32%2C76)|[checked_relevant_source_found](https://www.culture.taichung.gov.tw/media/1433826/114文化局統計年報-410-陳核稿.pdf)|[checked_entry_only](https://govstat.taichung.gov.tw/DgbasWeb/statfile3.aspx?cateno=01&mode=2)|[checked_relevant_source_found](https://data.gov.tw/dataset/84915)|
|彰化縣|[checked_relevant_source_found](https://www.bocach.gov.tw/subject/library/)|[checked_relevant_source_found](https://ws.bocach.gov.tw/Download.ashx?icon=.pdf&n=MTEy5bm05b2w5YyW57ij5paH5YyW5bGA57Wx6KiI5bm05aCxLnBkZg%3D%3D&u=LzAwMS9VcGxvYWQvMS9yZWxmaWxlLzk5OTQvNDkzODMvN2NiYTZiMzEtMGQ1Zi00MTRmLTk4MDMtNGM0MTM5ZTJkZDhjLnBkZg%3D%3D)|[checked_relevant_source_found](https://ctrl.chcg.gov.tw/main/main_act3/main.aspx?act_id=413&main_id=30276)|[checked_no_relevant_dataset_in_checked_page](https://data.chcg.gov.tw/)|
|南投縣|[checked_relevant_source_found](https://www.nthcc.gov.tw/A6_3/list/2)|[checked_relevant_source_found](https://www.nthcc.gov.tw/Uploads/userfile/A6_3/2021-04-21_0809106229.pdf)|[checked_entry_only](https://www.nantou.gov.tw/big5/bureau/content.php?cid=1386&dptid=376480000AU230000)|[checked_relevant_source_found](https://data.gov.tw/dataset/168915)|
|雲林縣|[checked_relevant_source_found](https://lib.ylccb.gov.tw/wSite/public/Attachment/f1704252060713.pdf)|[request_failed](https://content.yunlin.gov.tw/)|[checked_entry_only](https://yunlin.dgbas.gov.tw/STATWeb/Page/BookCatalog_Record.aspx?bookname=%E9%9B%B2%E6%9E%97%E7%B8%A3%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1&orgno=3001&rbno=1&uid=37)|[checked_relevant_source_found](https://opendata.yunlin.gov.tw/OpenDataList.aspx?n=8350&orderby=2&sms=0)|
|嘉義市|[request_failed](https://www.cabcy.gov.tw/)|[checked_relevant_source_found](https://chiayi.dgbas.gov.tw/statweb/Page/stat01_1.aspx?Mid=5006)|[checked_relevant_source_found](https://chiayi.dgbas.gov.tw/DgbasWeb/statfile2.aspx?cateno=01&mode=3)|[request_failed](https://data.chiayi.gov.tw/opendata/)|
|嘉義縣|[checked_entry_only](https://www.cycab.gov.tw/)|[checked_entry_only](https://tbocc.cyhg.gov.tw/)|[checked_relevant_source_found](https://cyhg.dgbas.gov.tw/dgbasweb/statfile2.aspx?CateNo=33&Mode=3)|[checked_no_relevant_dataset_in_checked_page](https://data.gov.tw/dataset/132161)|
|臺南市|[checked_entry_only](https://www.tnpl.tn.edu.tw/)|[checked_relevant_source_found](https://culture.tainan.gov.tw/df_ufiles/071/閱讀閱有趣112年臺南市閱讀風貌概況.pdf)|[checked_entry_only](https://account.tainan.gov.tw/News.aspx?n=44&sms=9367)|[checked_relevant_source_found](https://data.tainan.gov.tw/DataSet/Detail/80b958cc-682b-47ff-8cf9-1c140e6ef26b)|
|高雄市|[checked_relevant_source_found](https://www.ksml.edu.tw/form/index.aspx?Parser=28%2C3%2C32)|[checked_relevant_source_found](https://khcc.kcg.gov.tw/PhotoData/TyzRJWC16kxBNJp.pdf)|[checked_entry_only](https://kcgdg.kcg.gov.tw/StatWebRWD/Page/)|[checked_relevant_source_found](https://data.gov.tw/dataset/173509)|
|屏東縣|[checked_entry_only](https://library.pthg.gov.tw/)|[checked_relevant_source_found](https://www.cultural.pthg.gov.tw/News12.aspx?n=FE3F3A54BD25C385&sms=83339E065E5F593D)|[checked_relevant_source_found](https://pthg.dgbas.gov.tw/DgbasWeb/index.aspx)|[checked_no_relevant_dataset_in_checked_page](https://www.pthg.gov.tw/Cus_OpenData_Default1.aspx?n=481C53E05C1D2D97&sms=354B0B57F2762613)|
|宜蘭縣|[checked_entry_only](https://www.ilccb.gov.tw/cp.aspx?n=10213)|[checked_entry_only](https://www.ilccb.gov.tw/News.aspx?n=14079&sms=12964)|[checked_entry_only](https://bgacst.e-land.gov.tw/cp.aspx?n=11386&s=6762)|[checked_no_relevant_dataset_in_checked_page](https://opendata.e-land.gov.tw/dataset/?q=%E5%9C%96%E6%9B%B8%E9%A4%A8)|
|花蓮縣|[checked_entry_only](https://library.hccc.gov.tw/)|[checked_relevant_source_found](https://www.hccc.gov.tw/zh-tw/Download/Statistics/409)|[checked_entry_only](https://hl.dgbas.gov.tw/STATWeb/Page/BookCatalog_Main.aspx)|[checked_entry_only](https://ra.hl.gov.tw/Detail_sp/a1b55c83a93a4e9f9f2cb9f1576e26b9)|
|臺東縣|[checked_entry_only](https://culture.taitung.gov.tw/facility/%E8%87%BA%E6%9D%B1%E7%B8%A3%E7%AB%8B%E5%9C%96%E6%9B%B8%E9%A4%A8)|[checked_no_relevant_dataset_in_checked_page](https://culture.taitung.gov.tw/publication)|[checked_entry_only](https://taitung.dgbas.gov.tw/StatWebRWD/page/HitCount.aspx?PageName=WebMenu&PageNameC=%e7%b5%b1%e8%a8%88%e5%88%8a%e7%89%a9&Mid=33&Menuid=33&ItemName=%e7%b5%b1%e8%a8%88%e5%88%8a%e7%89%a9&Kind=1)|[request_failed](http://www.taitung.gov.tw/opendata/)|
|澎湖縣|[checked_entry_only](https://www.phlib.nat.gov.tw/wSite/sp?mp=1&orgId=004&xdUrl=%2FwSite%2FApBlock%2FLibrary.jsp)|[checked_relevant_source_found](https://www.penghu.gov.tw/uploaddowndoc?file=unit02%2F202508111721160.pdf&filedisplay=113%E6%BE%8E%E6%B9%96%E7%B8%A3%E6%96%87%E5%8C%96%E7%B5%B1%E8%A8%88%E5%B9%B4%E5%A0%B1.pdf&flag=doc)|[checked_entry_only](https://www.penghu.gov.tw/accounting/home.jsp?id=449)|[checked_relevant_source_found](https://opendata.penghu.gov.tw/zh_Hans_CN/dataset/fs30000-2017-05-31-1496212101)|
|金門縣|[checked_entry_only](https://cabkc.kinmen.gov.tw/informationlists?uid=9)|[checked_entry_only](https://cabkc.kinmen.gov.tw/archive?uid=6)|[checked_relevant_source_found](https://kinmen.dgbas.gov.tw/DgbasWeb/statfile3.aspx?cateno=01&mode=2)|[request_failed](https://data.kinmen.gov.tw/Default.aspx?Create=1)|
|連江縣|[checked_entry_only](https://www.matsucc.gov.tw/%e6%96%87%e5%8c%96%e8%99%95%e9%a6%ac%e7%a5%96%e5%9c%96%e6%9b%b8%e9%a4%a8/)|[checked_relevant_source_found](https://matsucc.gov.tw/%E8%AA%8D%E8%AD%98%E6%96%87%E5%8C%96%E8%99%95/%E9%A0%90%E5%91%8A%E7%B5%B1%E8%A8%88%E6%AA%94%E6%A1%88%E4%B8%8A%E5%82%B3%E5%8D%80/)|[checked_entry_only](https://eip.matsu.gov.tw/matsuopendata/chhtml/dataquery/4?tmpcode=07)|[checked_relevant_source_found](https://data.gov.tw/dataset/173786)|
