# 2021 年公共館統計獨立原件查核

資料年 2021（原表民國110年），年鑑卷號111；選定統計表／子群 15 個，共 **1,236 格**。先讀原PDF的文字與影像、保存原格期待後，才讀producer CSV。完整逐格比對原字（排版空白除外）、數值/null、狀態、資料年、PDF頁與印頁，**0差異、0漏格、0多格**。

另有 33 格由原件影像直接讀得的文字錨點；逐格期待來自獨立定位的PDF字詞。本工作是AI輔助的選定表格全量核對，並非人類雙校，也不涵蓋整卷全文、其他館類、工程／得獎榜單及地方措施個案。

- producer CSV：`derived/ncl_2021_long.csv`
- 最終CSV SHA-256：`138097c9a37bd7deb49bbf46a96a8f67850988da3b125f2c4aba86e430976b81`
- 盲讀期待凍結副本：`research/ncl-mid-independent/2021-expectations-frozen.json`
- 凍結副本 SHA-256：`7d45c165a678cfbc78610a983d4899baa102bd14f443fdc05682dcbc4e530208`
- 可重播逐格報告：`research/ncl-2021-independent-review.json`
- 逐格語義檢查 1,586 項，全部通過。

## 範圍與表結構

| 原表 | 章節 | 格數 | 結構／範圍 |
|---|---|---:|---|
| 7 | public-library | 36 | levels_counts |
| 8 | public-library | 138 | county_counts |
| 9 | public-library | 69 | purchase |
| 10 | public-library | 48 | levels_staffing |
| 11 | public-library | 161 | staffing |
| 12 | public-library | 60 | levels_holdings |
| 13 | public-library | 69 | holdings |
| 14 | public-library | 92 | loans |
| 15 | public-library | 161 | events |
| 16 | public-library | 161 | attendance |
| 19 | public-library | 75 | budget |
| 21 | public-library | 120 | acquisitions_2021 |
| 203 | statistics | 7 | public library subgroup including private; excludes National Central Library |
| 204 | statistics | 4 | 公立公共圖書館; 館藏量原欄頭（冊、件） |
| 206 | statistics | 35 | 公立公共圖書館；五年資料 2017–2021 |

## 原值與語義

原印零值 35 格仍為0；明示標記 {"-": 6, "無": 2}，一律保留字樣與null，不推成零。此批沒有原印留白格。

原層級欄「鄉鎮市區立圖書館」完整保留。人力表原頭「服務轄區人口數(A)」、「編制內專業人員(C)」與來源一致；沒有增添「數」字或略掉服務轄區。歷史表「館藏量」未印單位，unit及unit_raw留空，狀態為source_unit_unconfirmed_or_not_printed；沒有把同卷單年度基本表的（冊、件）定義套給歷史五年。

本年基本表所取原印資料行名為「公立公共圖書館」；全國只放情境描述，仍為公布合計。五年歷史表沒有實體地理列，「全國」明示為contextual_national_aggregate_inferred。分類表首行原名「公共圖書館」包含私立分項，不能與公立館基本／歷史表當作同一館數母體直接串接。

全國、各層級、分項與公布合計彼此可能重疊，不能把這些格再混加。國資圖與國臺圖為個別國立公共館，不是「國家圖書館」。原表冊／件／種及混合小計分開保留；活動場次、參與人次也不合併。

流量／年度經費依每格原資料年標年度；存量或比率未明載精確時點時不補年末日期。未使用卷號、刊登日或存取日當資料時點。

原版權頁出版月讀為 **2023-08**；這與官方入口刊登日是不同欄位，不由月份杜撰出版日。

採編表21原實體第1欄為序號、第2欄館別、第3–7欄為五個數值欄；producer既有source_column排除序號而採第2–6欄。報告逐格保留source_original_physical_column；這是欄號慣例crosswalk，數字沒有換格或換縣市。

表11題為110年，但服務轄區人口合計仍印23,561,236，同章購書／館藏／借閱表人口合計印23,375,315。逐格保留這些來源版本；沒有換成別表人口或推定人口測量時點。表21的雲林／臺南等原分項與合計不一致，也照原印留存，未配平。

## 館類與地理欄位 schema 修正

本報告schema版本2：歷史表206的35格，初始盲讀期待曾把表題館類「公立公共圖書館」放入entity_raw。現保留為source_category_raw；entity_raw=null明示沒有原印地理列，另列expected_geography_contextual_name=全國與expected_entity_label_status=contextual_national_aggregate_inferred。這兩項與producer的entity_raw、entity_contextual_name及entity_label_status逐格核對，不略過地理檢查。

初始盲讀副本及其SHA完全保留；數字、原字、缺值狀態、格位與CSV SHA皆未變。本年基本表有明示原行名的4格，仍嚴格核對entity_raw=公立公共圖書館，未套用此歷史表crosswalk。

## 定位與回放

分類／本年基本統計採選定子群列號，與原完整表的實體資料列差1；原完整表列號另存source_original_complete_table_row。所有cells以原件SHA、表、producer列／欄唯一定位，並保留PDF頁與印頁；原件數值期待在任何crosswalk之前已另存凍結副本。

原件凍結cells內容指紋：`75840a2e8b31a84bf440d9bf7f88a64b1248065c9a9c6a5f3e93a0b9dce571d0`。JSON內comparison綁最終CSV SHA，null、value_status與0均逐格比對；不只比總和。

## 官方原件

- [public-library 官方下載](https://www.ncl.edu.tw/files/file_pool/1/0Q083566968812945804/579a8905-5c4c-467b-8e88-2821ddf7e60e.pdf)；[官方年鑑入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566960460238329)；SHA-256 `838912481fc982e958e9487c0ac0c3211cfb2e77eb7ea7aeda357bdf4bd36454`。
- [statistics 官方下載](https://www.ncl.edu.tw/files/file_pool/1/0Q083566972170116821/897aa07f-e657-4894-bf6b-31d3f964abc5.pdf)；[官方年鑑入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566960460238329)；SHA-256 `52972fc3abd675dc808b8e70a8f8132611cd5d7087adfa5b3e7b6d3ec24ff882`。

原PDF、完整文字層、HTML與全頁PNG維持私有；本報告和逐格JSON僅保留選定統計事實與來源定位。全文授權不能由.gov網域或可下載推定。完整影像證據置於research/ncl-mid-independent/images.private/，全文文字檔名為*.private.json，均不應進公開包。
