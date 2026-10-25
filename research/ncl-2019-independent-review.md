# 2019 年公共館統計獨立原件查核

資料年 2019（原表民國108年），年鑑卷號109；選定統計表／子群 14 個，共 **1,173 格**。先讀原PDF的文字與影像、保存原格期待後，才讀producer CSV。完整逐格比對原字（排版空白除外）、數值/null、狀態、資料年、PDF頁與印頁，**0差異、0漏格、0多格**。

另有 33 格由原件影像直接讀得的文字錨點；逐格期待來自獨立定位的PDF字詞。本工作是AI輔助的選定表格全量核對，並非人類雙校，也不涵蓋整卷全文、其他館類、工程／得獎榜單及地方措施個案。

- producer CSV：`derived/ncl_2019_long.csv`
- 最終CSV SHA-256：`1a81468bd4866c5f5eb53f6d8a146c9f07f9cb859cf8f3e9b96aef739a1e0b4c`
- 盲讀期待凍結副本：`research/ncl-mid-independent/2019-expectations-frozen.json`
- 凍結副本 SHA-256：`f86d11ee8117559555479790e3eae7b1d36990d70131a38e1981fda652284226`
- 可重播逐格報告：`research/ncl-2019-independent-review.json`
- 逐格語義檢查 1,345 項，全部通過。

## 範圍與表結構

| 原表 | 章節 | 格數 | 結構／範圍 |
|---|---|---:|---|
| 15 | public-library | 36 | levels_counts |
| 16 | public-library | 138 | county_counts |
| 17 | public-library | 69 | purchase |
| 18 | public-library | 161 | staffing |
| 19 | public-library | 60 | levels_holdings |
| 20 | public-library | 69 | holdings |
| 21 | public-library | 92 | loans |
| 22 | public-library | 161 | events |
| 23 | public-library | 161 | attendance |
| 24 | public-library | 115 | migrant |
| 26 | public-library | 75 | budget |
| 205 | statistics | 7 | public library subgroup including private; excludes National Central Library |
| 206 | statistics | 4 | 公立公共圖書館; 館藏量原欄頭（冊、件） |
| 208 | statistics | 25 | 公立公共圖書館；五年資料 2015–2019 |

## 原值與語義

原印零值 60 格仍為0；明示標記 {"無": 5}，一律保留字樣與null，不推成零。此批沒有原印留白格。

原層級欄「鄉鎮市區立圖書館」完整保留。人力表原頭「服務轄區人口數(A)」、「編制內專業人員(C)」與來源一致；沒有增添「數」字或略掉服務轄區。歷史表「館藏量」未印單位，unit及unit_raw留空，狀態為source_unit_unconfirmed_or_not_printed；沒有把同卷單年度基本表的（冊、件）定義套給歷史五年。

本年基本表所取原印資料行名為「公立公共圖書館」；全國只放情境描述，仍為公布合計。五年歷史表沒有實體地理列，「全國」明示為contextual_national_aggregate_inferred。分類表首行原名「公共圖書館」包含私立分項，不能與公立館基本／歷史表當作同一館數母體直接串接。

全國、各層級、分項與公布合計彼此可能重疊，不能把這些格再混加。國資圖與國臺圖為個別國立公共館，不是「國家圖書館」。原表冊／件／種及混合小計分開保留；活動場次、參與人次也不合併。

流量／年度經費依每格原資料年標年度；存量或比率未明載精確時點時不補年末日期。未使用卷號、刊登日或存取日當資料時點。

原版權頁出版月讀為 **2021-12**；這與官方入口刊登日是不同欄位，不由月份杜撰出版日。

## 館類與地理欄位 schema 修正

本報告schema版本2：歷史表208的25格，初始盲讀期待曾把表題館類「公立公共圖書館」放入entity_raw。現保留為source_category_raw；entity_raw=null明示沒有原印地理列，另列expected_geography_contextual_name=全國與expected_entity_label_status=contextual_national_aggregate_inferred。這兩項與producer的entity_raw、entity_contextual_name及entity_label_status逐格核對，不略過地理檢查。

初始盲讀副本及其SHA完全保留；數字、原字、缺值狀態、格位與CSV SHA皆未變。本年基本表有明示原行名的4格，仍嚴格核對entity_raw=公立公共圖書館，未套用此歷史表crosswalk。

## 定位與回放

分類／本年基本統計採選定子群列號，與原完整表的實體資料列差1；原完整表列號另存source_original_complete_table_row。所有cells以原件SHA、表、producer列／欄唯一定位，並保留PDF頁與印頁；原件數值期待在任何crosswalk之前已另存凍結副本。

原件凍結cells內容指紋：`5f493e527bd987fe8100919aba39f02db945e64a5cd2d55985ee00075f0c0a8f`。JSON內comparison綁最終CSV SHA，null、value_status與0均逐格比對；不只比總和。

## 官方原件

- [public-library 官方下載](https://www.ncl.edu.tw/files/file_pool/1/0Q083566940887988692/a98bc225-8586-48ed-93f9-a09afb925ea5.pdf)；[官方年鑑入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566931435160107)；SHA-256 `843d4bcbbd7ff4f646332eb833800fbac12c7e6f5d333eb3700657267d5a903a`。
- [statistics 官方下載](https://www.ncl.edu.tw/files/file_pool/1/0Q083566954135058718/92098800-f891-465e-aafd-33c45a7d56bc.pdf)；[官方年鑑入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566931435160107)；SHA-256 `604081327bb97f8d4ce811917312ad5e6842749c2fe3b6529bf8c4a8464afc5d`。

原PDF、完整文字層、HTML與全頁PNG維持私有；本報告和逐格JSON僅保留選定統計事實與來源定位。全文授權不能由.gov網域或可下載推定。完整影像證據置於research/ncl-mid-independent/images.private/，全文文字檔名為*.private.json，均不應進公開包。
