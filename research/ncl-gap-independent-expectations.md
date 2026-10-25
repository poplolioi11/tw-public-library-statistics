# 國圖缺表獨立核對基準

本盲核階段只讀三份原始 PDF，以 PDFium 獨立渲染並視讀四張完整表；未讀新抽取程式或 derived/ncl_gap* 結果。這是獨立 AI 視讀，不稱人工雙校。

全表共 1180 個位置：830 個印刷數字、350 個印刷留白。JSON逐格記錄值、留白狀態、欄位及原頁列欄；不強求千分位標點逐字相同。

## 表格與印刷全國總數

### 2008 表3：印刷78頁（PDF第2頁）

全國公立公共圖書館統計表（97年）。26列 × 11個數值欄，數字162格、留白124格。

| 欄位 | 印刷全國總數 | 非總計列加總 | 差異 |
|---|---:|---:|---:|
| national_main | 2 | 2 | 0 |
| national_branch | 1 | 1 | 0 |
| municipal_main | 2 | 2 | 0 |
| municipal_branch | 55 | 55 | 0 |
| county_main | 24 | 24 | 0 |
| county_branch | 13 | 13 | 0 |
| town_main | 335 | 335 | 0 |
| town_branch | 110 | 110 | 0 |
| provincial_other | 1 | 1 | 0 |
| total_main | 364 | 364 | 0 |
| total_branch | 179 | 179 | 0 |

原表來源註：資料來源：「公共圖書館統計系統」http://publibstat.lib.nctu.edu.tw/，上網日期：98.7.15。

### 2008 表5：印刷80頁（PDF第4頁）

全國各縣市暨鄉鎮圖書館人員及服務統計表（97年）。29列 × 12個數值欄，數字348格、留白0格。

| 欄位 | 印刷全國總數 | 非總計列加總 | 差異 |
|---|---:|---:|---:|
| professional_staff | 469 | 469 | 0 |
| administrative_staff | 665 | 665 | 0 |
| technical_staff | 63 | 63 | 0 |
| temporary_staff | 1,479 | 1,479 | 0 |
| contract_staff | 339 | 339 | 0 |
| volunteers | 8,645 | 8,645 | 0 |
| student_staff | 211 | 211 | 0 |
| other_staff | 438 | 438 | 0 |
| all_staff | 12,309 | 12,309 | 0 |
| physical_borrower_visits | 11,964,492 | 11,946,492 | 18,000 |
| promotion_events | 66,145 | 66,145 | 0 |
| promotion_attendance | 7,407,494 | 7,407,494 | 0 |

原表來源註：資料來源：「公共圖書館統計系統」http://publibstat.lib.nctu.edu.tw/，上網日期：98年7月15日。

### 2009 表1：印刷74頁（PDF第2頁）

全國公立公共圖書館統計表（98年）。26列 × 10個數值欄，數字159格、留白101格。

| 欄位 | 印刷全國總數 | 非總計列加總 | 差異 |
|---|---:|---:|---:|
| national_main | 2 | 2 | 0 |
| municipal_main | 3 | 3 | 0 |
| municipal_branch | 56 | 56 | 0 |
| county_main | 23 | 23 | 0 |
| county_branch | 15 | 15 | 0 |
| town_main | 335 | 335 | 0 |
| town_branch | 105 | 105 | 0 |
| provincial_other | 1 | 1 | 0 |
| total_main | 364 | 364 | 0 |
| total_branch | 177 | 177 | 0 |

逐列合計差異（保留原值）：`[{"entity": "臺中市", "visible_main_sum": 13, "printed_main_total": 13, "visible_branch_sum": 3, "printed_branch_total": 4}]`

原表來源註：資料來源：國家圖書館。「國家圖書館2009至2012中程發展策略計畫」。臺北市：該館，民98.4。

### 2010 表1：印刷34頁（PDF第2頁）

全國公立公共圖書館統計表（99年）。26列 × 11個數值欄，數字161格、留白125格。

| 欄位 | 印刷全國總數 | 非總計列加總 | 差異 |
|---|---:|---:|---:|
| national_main | 2 | 2 | 0 |
| national_branch | 1 | 1 | 0 |
| municipal_main | 3 | 3 | 0 |
| municipal_branch | 61 | 61 | 0 |
| county_main | 23 | 23 | 0 |
| county_branch | 15 | 15 | 0 |
| town_main | 335 | 335 | 0 |
| town_branch | 108 | 108 | 0 |
| provincial_other | 1 | 1 | 0 |
| total_main | 364 | 364 | 0 |
| total_branch | 185 | 185 | 0 |

原表來源註：資料來源：公共圖書館統計系統。上網日期：100年5月15日，http://publibstat.lib.nctu.edu.tw/stat/showStat.aspx/。

## 必須保留的欄序與範圍差異

- Count tables use 25 historical county/city row labels; no remapping to current 22 counties.
- National main libraries are geographically placed in 臺中市 and 臺北縣; the visible national branch is placed in 臺中市 in 2008/2010. Provincial other is placed in 南投縣. This differs from staff/service tables with separately listed institutions.
- 2009 table has no printed national-branch column. Keep its 10 printed numeric columns; do not manufacture an eleventh numeric column.
- 2009 臺中市 visible branch components 1+2=3 while printed total is4; national visible branch components 56+15+105=176 while printed branch total is177. Preserve this source discrepancy.
- 2008 staff/services header places 志工 before 工讀生. It matches2009 staffing order and differs from2010.
- No explanatory county-exclusion footnote is printed on these four target tables; do not import another table footnote as if printed here. Explicit institution rows and count-category placement are the evidence.
- Counts printed blank cells are not explicit missing markers and must not be rewritten to zeros. Numeric-only long extraction may omit printed blanks if their absence and table geometry remain documented.

## 固定值基準

- 2008館數總館364、分館179；臺中市國立總館1、國立分館1，縣市總館1、分館1，鄉鎮總館11、分館2，合計13／4。
- 2009館數總館364、分館177；國立圖書館僅印總館欄，沒有國立分館欄。
- 2010館數總館364、分館185；直轄市總館3、分館61；臺北縣鄉鎮分館54。
- 2008人員總數12,309；志工8,645、工讀生211；圖書借閱11,964,492人次、推廣66,145場次、7,407,494人次。
- 2008國立中央圖書館臺灣分館志工357、工讀生0、合計446；國立臺中圖書館志工168、工讀生19、合計278；省政府館志工67、工讀生0、合計82。

所有固定值皆有JSON逐格基準，後續比對不得以加總或其他年度替代原印值。

## 2008人次原表算術差異

28個非總計列的圖書借閱人次加總為11,946,492，原印全國總計為11,964,492，相差18,000。澎湖縣原印32,272已以放大影像與原PDF文字再確認。這是原表差異，不能以加總值覆蓋原印總計。

館數欄的「所」為館數單位的推定，目標館數表未另印單位字樣；人員服務表的「人／人次／場次」則明列於表頭，JSON已分開unit_status。
