# 第二階段獨立來源案例契約

已先凍結 **37 個真實案例／53 個真實record ID**與6個明示合成反例，再驗引擎。本輪未讀主代理引擎或其輸出，不以實作結果倒推答案。分類scope已由主代理提供，並非盲選題。

全量候驗母體由本機Python計數：canonical 37,887＋地方統計格18,486＋計畫量格123＝56,496；本檔尚不代表全量引擎驗收。

expected_decision的blocked／unresolved／limited_published_panel對應契約incompatible／unresolved／published_panel_limited。blocked只拒絕案例指定的默接、默加或重解，不禁止明示差異的並列與類別分布分析。

| 案例 | 來源風險／操作 | 期待 | 真實ID |
|---|---|---|---|
| P2-C001 | 同年同單位仍須分開預算與決算 | blocked | `obs-916205835c29d81f67579d`、`obs-63075c8a8f27c327bb9015` |
| P2-C002 | 含續借總量不能和續借子量當相同系列 | blocked | `obs-60c28dca29e941288ad138`、`obs-9ad5c3d8b338ae1d6e1073` |
| P2-C003 | 未說續借納入規則的借閱量不可逕接含續借量 | unresolved | `obs-1dfdddad4c3458d7631978`、`obs-60c28dca29e941288ad138` |
| P2-C004 | 欄名人數而單位千人次，不是獨立使用者 | blocked | `obs-42d1acd6f4f6301bc0e999` |
| P2-C005 | 同一本回溯表也不能越過已知定義斷點 | unresolved | `obs-7c26d37e70562ef669b2af`、`obs-9a08f5f23e7b50ce471776` |
| P2-C006 | 圖書冊數與非書資料件數不可同單位相接 | blocked | `obs-f19eca8ec8a3639f72d0cc`、`obs-b057917eba199442cb8d53` |
| P2-C007 | 冊與資料庫種數不可按館藏二字相加 | blocked | `obs-f19eca8ec8a3639f72d0cc`、`obs-45f7f66d25e65b50ec06ee` |
| P2-C008 | 千冊與冊須明示轉換，換算本身不認證母體 | blocked | `obs-c8dfbe305cca9e5cd3f5b1`、`obs-bd551f75c0b34269130d05` |
| P2-C009 | 現行字典不能回填2011至2025的完整有效期 | unresolved | `obs-117d95cd6f34f9b8bcf2b0`、`obs-07322cb1f818c24be6b00b` |
| P2-C010 | 同年同值不同出版版仍保留兩筆 | unresolved | `obs-28edaf7217be5d3c0c4546`、`obs-b709e9cbc2e2844fee7bb7` |
| P2-C011 | 2012人均比率不能補臺北市原借閱量 | blocked | `obs-f62e84d161a23349254e91` |
| P2-C012 | 主計含國家圖書館母體不接國資圖不含國立館版 | blocked | `obs-4ac5275191211bea74bceb`、`obs-755be0063af0e04a778dd5`、`obs-ec8a6226ca4cbf4760ee86` |
| P2-C013 | 舊縣市原名不默寫為現行地名 | blocked | `obs-a8efa9497837a6543ad5b9` |
| P2-C014 | 同印臺南市亦不能忽略合併前後地域範圍 | blocked | `obs-e70d958ed0f6fed3708f9d`、`obs-20a1487cd958b4e6bb3b93` |
| P2-C015 | 2015表17場次／人次衝突不自選候選單位 | unresolved | `obs-f960a3569132a2a26dc9c2` |
| P2-C016 | 2024原印地理疑義不能當確認縣市覆蓋 | unresolved | `obs-65556868768eda7ff2e243` |
| P2-C017 | 2015兩列均印金門不能猜一列連江 | unresolved | `obs-3113176be5c12adec2f182`、`obs-434a8011ff62c36bfaae38` |
| P2-C018 | typed0與顯示符號衝突不能變已知零 | blocked | `south-hualien-library-lending-409-reader:115年8月:B17`、`south-lienchiang-opendata-173786:工作表1:G3` |
| P2-C019 | 113年6月sheet／7月header不能擇一 | unresolved | `south-hualien-library-lending-409-reader:113年6月:F10` |
| P2-C020 | 1109原字不能自動修成109或當3020有效期 | unresolved | `south-hualien-library-lending-409-reader:109年10月:F10` |
| P2-C021 | 113目錄年不是附件確證期末時點 | unresolved | `south-lienchiang-opendata-173786:工作表1:B2`、`south-lienchiang-culture-library-overview-114:11014-03-01-2:D8` |
| P2-C022 | 2005特定計畫參照年不是全年營運量 | blocked | `ncl95-table6-reading-001:participants` |
| P2-C023 | 94年12月至95年5月活動不全算2005 | blocked | `ncl95-table7-activity-05:participants` |
| P2-C024 | 總計與一般讀者子項不能一起加總 | blocked | `south-hualien-library-lending-409-reader:114年8月:F10`、`south-hualien-library-lending-409-reader:114年8月:F11` |
| P2-C025 | 總計與男性子項不能一起加總 | blocked | `south-hualien-library-lending-409-reader:114年8月:F10`、`south-hualien-library-lending-409-reader:114年8月:G10` |
| P2-C026 | 讀者類別不同不能接成同一未分組時間序列 | blocked | `south-hualien-library-lending-409-reader:114年8月:F11`、`south-hualien-library-lending-409-reader:114年8月:F12` |
| P2-C027 | 兩張分類視圖的同月總計不能加兩次 | blocked | `south-hualien-library-lending-409-reader:114年8月:F10`、`south-hualien-library-lending-409-room:114年8月:F10` |
| P2-C028 | 冊單位相同仍分館藏存量與全年借閱流量 | blocked | `south-lienchiang-culture-library-overview-114:11014-03-01-2:C8`、`south-lienchiang-culture-library-overview-114:11014-03-01-2:C12` |
| P2-C029 | 借閱人數／人次衝突未解，不宣稱去重人數 | unresolved | `south-hualien-library-lending-409-reader:114年8月:B10` |
| P2-C030 | 無typed值的原字-與原印0不同 | blocked | `south-lienchiang-culture-library-overview-114:11014-03-01-2:I9`、`south-lienchiang-opendata-173786:工作表1:G3` |
| P2-C031 | 指標填答館數不等於設施總數 | blocked | `obs-2b6773450e620a4970b3c9` |
| P2-C032 | 公立與部分填答私立館不是相同母體 | blocked | `obs-bd551f75c0b34269130d05`、`obs-31535c19d1b9c2a07e870e` |
| P2-C033 | 同卷兩表私立館藏異值不以常識擇真 | unresolved | `obs-3d77d5d6330d5ce25b79f6`、`obs-31535c19d1b9c2a07e870e` |
| P2-C034 | 同官方五年表明列借閱人次僅准原刊內比較 | limited_published_panel | `obs-28edaf7217be5d3c0c4546`、`obs-7cf1a460cecd982fbf291f` |
| P2-C035 | 同回溯表館藏量未印單位仍不補冊件 | unresolved | `obs-5daf539527794b046647c6`、`obs-0fa96e2fdb4a5ea7fd9bc4` |
| P2-C036 | 原刊分期多斜線的候選日期不當確定全年 | unresolved | `obs-a963e28f67e7a6e8fd45ef` |
| P2-C037 | 原印未統計不當零或不適用 | blocked | `obs-0dac5caf3d432d23fbfa14` |

## 有限回溯表比較的邊界

本輪另直接讀109卷統計章PDF4／印440原圖。表208題為公立公共圖書館基本統計表（104年至108年）；借閱人次同一原列提供五年。只有該表內明示兩欄可作limited_published_panel，原刊註109年各縣市填報來源須一起顯示。這不證明每年國立館納入、填報完整率或計數方式完全相同。原表館藏量未印單位，不能靠同表或本年定義補冊件後放行。

同一本主計回溯表另有1999年前借閱人數定義註記與中英文方向歧義，必須保留斷點；「在同一表」不是越過明示疑義的通行證。

## 必須拒用或降為未知的條件

- `measure`：預算/決算、借閱/續借/含續借、進館/借閱、冊次/獨立件數語義不同；未明是否含續借或是否去重則unresolved。
- `unit`：冊/件/種/千冊/人/人次不可默同；必要單位未知、混合或標題正文衝突不得自定候選。明示比例轉換也不自動認證其他維度。
- `collection_type`：實體圖書、非書、電子書、電子資源/資料庫等分類不同，總量混合不得說全是冊。
- `stock_flow_ratio_financial`：年底存量、全年流量、分期、月量、比率與財務預決算分開；2012比率不反推原量。
- `period_resolution`：sheet/header相衝、catalog-only、候選日期、活動窗或跨年不定正式全年；不以出版/卷號/檢索日補原時點。
- `population`：公私立、部分問卷回覆、學校/公共館、特定計畫或分館原母體不同，或scope未知，不默接。
- `national_library_scope`：含NCL/NLPI/NTL與不含國立館版本不同；來源未證納入規則時保留未知。
- `geography_vintage`：舊縣市原名及界線不默重編；原刊錯列疑義/重複名不自行換位、補縣或當確認覆蓋。
- `institutional_level`：總館/分館/閱覽室/館外站或不同層級不可都當全縣館數。
- `aggregation_role`：總計/小計/分項、括號填答館數、兩種分類視圖不能全加；角色未知不能因名稱為總計就抹去維度。
- `source_edition`：同年不同來源/版次/SHA重刊可並列不能默刪或接成同一歷史方法；數值相等亦然。
- `age_sex_reader_classification`：性別、年齡、讀者身分類別與總計分開；可呈現類別分布，不等於可抹分類接序列或把總計再加一遍。
- `protected_value_representation`：0、空白、未統計、字串marker與display/typed0未解衝突保留全部表示，不能轉0/NA/真零或偷補值。
- `published_panel_limited`：僅同一官方回溯表明列不同年度、同一原指標及可識別原單位/母體/地域才准原刊內比較；仍不得認證歷年方法全不變，且已知定義斷點、必要單位未知會使其失格。

## 計數與可重播性

所有數字與算術由本機Python計算，原值未改。canonical=37887；phase1_local_statistical_cells=18486；phase1_programme_quantities=123；total_quantitative_rows=56496；local_display_typed0_conflicts=5098；local_period_conflict_cells=176；local_catalog_only_period_cells=35；local_reported_numeric_zero_cells=253；canonical_2015_heading_unit_conflicts=161；canonical_2024_county_uncertain_cells=36；canonical_2015_county_uncertain_or_duplicate_cells=183。

JSON逐例保留record ID、原URL、原件SHA、原頁／表／列／欄／sheet／cell定位、數值表示、unit/period/population等必要來源欄；附來源短註、目前定義頁與原圖回溯表的證據卡。完整原件、全頁圖與私有路徑未列入公開facts。

初凍案例內容SHA：`f2e968150db64ac338543f5371a5d962d9d01301672f07430bdb3d941f22aff9`。每個來源檔及契約SHA另列於JSON；後續如因原件事實修正，須另保留更正鏈，不因引擎不同意而偷改期待。
