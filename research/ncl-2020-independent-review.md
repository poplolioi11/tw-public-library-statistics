# 2020 年公共館統計獨立原件查核

資料年 2020（原表民國109年），年鑑卷號110；選定統計表／子群 15 個，共 **1,250 格**。先讀原PDF的文字與影像、保存原格期待後，才讀producer CSV。完整逐格比對原字（排版空白除外）、數值/null、狀態、資料年、PDF頁與印頁，**0差異、0漏格、0多格**。

另有 42 格由原件影像直接讀得的文字錨點；逐格期待來自獨立定位的PDF字詞。本工作是AI輔助的選定表格全量核對，並非人類雙校，也不涵蓋整卷全文、其他館類、工程／得獎榜單及地方措施個案。

- producer CSV：`derived/ncl_2020_long.csv`
- 最終CSV SHA-256：`dd434d82bf62b2ae44b69594e5f1f339f371daa0563f33f8edb18f4a283ec8ae`
- 盲讀期待凍結副本：`research/ncl-mid-independent/2020-expectations-frozen.json`
- 凍結副本 SHA-256：`63cf081f8f515b618b99aacad195a81178192ca0fa9443ab6f4e20310359504b`
- 可重播逐格報告：`research/ncl-2020-independent-review.json`
- 逐格語義檢查 1,471 項，全部通過。

## 範圍與表結構

| 原表 | 章節 | 格數 | 結構／範圍 |
|---|---|---:|---|
| 10 | public-library | 36 | levels_counts |
| 11 | public-library | 138 | county_counts |
| 12 | public-library | 69 | purchase |
| 13 | public-library | 48 | levels_staffing |
| 14 | public-library | 161 | staffing |
| 15 | public-library | 60 | levels_holdings |
| 16 | public-library | 69 | holdings |
| 17 | public-library | 92 | loans |
| 18 | public-library | 161 | events |
| 19 | public-library | 161 | attendance |
| 22 | public-library | 75 | budget |
| 24 | public-library | 144 | acquisitions_2020 |
| 186 | statistics | 7 | public library subgroup including private; excludes National Central Library |
| 187 | statistics | 4 | 公立公共圖書館; 館藏量原欄頭（冊、件） |
| 189 | statistics | 25 | 公立公共圖書館；五年資料 2016–2020 |

## 原值與語義

原印零值 55 格仍為0；明示標記 {"無": 3, "未新增": 7}，一律保留字樣與null，不推成零。此批沒有原印留白格。

原層級欄「鄉鎮市區立圖書館」完整保留。人力表原頭「服務轄區人口數(A)」、「編制內專業人員(C)」與來源一致；沒有增添「數」字或略掉服務轄區。歷史表「館藏量」未印單位，unit及unit_raw留空，狀態為source_unit_unconfirmed_or_not_printed；沒有把同卷單年度基本表的（冊、件）定義套給歷史五年。

本年基本表所取原印資料行名為「公立公共圖書館」；全國只放情境描述，仍為公布合計。五年歷史表沒有實體地理列，「全國」明示為contextual_national_aggregate_inferred。分類表首行原名「公共圖書館」包含私立分項，不能與公立館基本／歷史表當作同一館數母體直接串接。

全國、各層級、分項與公布合計彼此可能重疊，不能把這些格再混加。國資圖與國臺圖為個別國立公共館，不是「國家圖書館」。原表冊／件／種及混合小計分開保留；活動場次、參與人次也不合併。

流量／年度經費依每格原資料年標年度；存量或比率未明載精確時點時不補年末日期。未使用卷號、刊登日或存取日當資料時點。

原版權頁出版月讀為 **2022-12**；這與官方入口刊登日是不同欄位，不由月份杜撰出版日。

原圖印86的臺北市視聽資料為跨行「2萬／9,225」，確定性轉為29,225件；電子書另為7,063種。原圖印87的臺東電子書為「分區資源中心新增80」，80僅代表這個分區資源中心，population_scope明確記非全縣完整新增總量。七格「未新增」保留source_marker/null，未將其推為0。

CSV parser確認這兩格的排版分隔是實際換行碼10：actual_newline=true、literal_backslash_n=false。比較只移除實際排版空白，不做literal反跳脫或任意文字刪除。JSON另保留producer原換行表示與codepoints。

## 館類與地理欄位 schema 修正

本報告schema版本2：歷史表189的25格，初始盲讀期待曾把表題館類「公立公共圖書館」放入entity_raw。現保留為source_category_raw；entity_raw=null明示沒有原印地理列，另列expected_geography_contextual_name=全國與expected_entity_label_status=contextual_national_aggregate_inferred。這兩項與producer的entity_raw、entity_contextual_name及entity_label_status逐格核對，不略過地理檢查。

初始盲讀副本及其SHA完全保留；數字、原字、缺值狀態、格位與CSV SHA皆未變。本年基本表有明示原行名的4格，仍嚴格核對entity_raw=公立公共圖書館，未套用此歷史表crosswalk。

## 定位與回放

分類／本年基本統計採選定子群列號，與原完整表的實體資料列差1；原完整表列號另存source_original_complete_table_row。所有cells以原件SHA、表、producer列／欄唯一定位，並保留PDF頁與印頁；原件數值期待在任何crosswalk之前已另存凍結副本。

原件凍結cells內容指紋：`70f77091e639a8135fc3a8855d92a038acad6834932f1d6cbfbed7741124f5a9`。JSON內comparison綁最終CSV SHA，null、value_status與0均逐格比對；不只比總和。

## 官方原件

- [public-library 官方下載](https://www.ncl.edu.tw/files/file_pool/1/0Q083566954845461293/94e39cac-191c-4202-ba9f-9724ef68ed6b.pdf)；[官方年鑑入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566955493654718)；SHA-256 `4d95c7af8993461b0395b331e2d60a221e1eaeac80bf7def28a86ee6fb2009cf`。
- [statistics 官方下載](https://www.ncl.edu.tw/files/file_pool/1/0Q083566968103532229/f5ea4a52-d924-47bb-9f62-8a6dc9d688f7.pdf)；[官方年鑑入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083566955493654718)；SHA-256 `5d6ca64e8a9cd1c05fc5b2ed97c48ad8f54dcaea3072062c3f85bfd35227ceb9`。

原PDF、完整文字層、HTML與全頁PNG維持私有；本報告和逐格JSON僅保留選定統計事實與來源定位。全文授權不能由.gov網域或可下載推定。完整影像證據置於research/ncl-mid-independent/images.private/，全文文字檔名為*.private.json，均不應進公開包。
