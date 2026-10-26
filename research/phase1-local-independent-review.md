# 四份地方來源獨立原件核對

核對日期：2026-10-26。結果：**PASS**。已先獨立建立原件期待，再讀製表輸出全量比對；初始數量與規則已知，`seen_initial=true`，不稱盲校。未讀取或 import 製表程式。

共核對 4 份原件、146 個統計工作表、**18,486 個統計位置**；同時核對 cells 表 **33,705 個位置**的來源值、型別、公式、style、merge 與 sheet/cell 定位。最終 **3,699,444 項檢查，0 失配**。CSV 與 JSONL 亦逐欄核對；CSV 額外欄位僅允許空的選用欄位。

| 來源 | 原件統計範圍 | 統計格 | 核對結果 |
|---|---|---:|---|
| [連江113年概況 ODS](https://data.gov.tw/dataset/173786) | 工作表1 B2:H6 | 35 | 全量相符 |
| [花蓮讀者身分借閱 ODS](https://www.hccc.gov.tw/zh-tw/Download/Statistics/409) | 72個月表 B10:I20 | 6,336 | 全量相符 |
| [花蓮館藏室借閱 ODS](https://www.hccc.gov.tw/zh-tw/Download/Statistics/409) | 72個月表 B10:I末個具名資料列，隨館藏室清單變動 | 12,080 | 全量相符 |
| [連江114年概況 XLSX](https://matsucc.gov.tw/%E8%AA%8D%E8%AD%98%E6%96%87%E5%8C%96%E8%99%95/%E9%A0%90%E5%91%8A%E7%B5%B1%E8%A8%88%E6%AA%94%E6%A1%88%E4%B8%8A%E5%82%B3%E5%8D%80/) | 11014-03-01-2 C8:I12 | 35 | 全量相符 |

花蓮兩份原件各有空白範本及72個月表，涵蓋109年9月至115年8月。2026年月份只視為月報。連江113年附件內未印日期，2024僅來自catalog題名，沒有借用114年定義補出時點；114年XLSX原表明印114年度。

## 重要語義與原件疑義

- 5,098格原顯示 `-`、typed numeric為 `0`，全部保留 `source_display_typed_value_conflict_unresolved` 且 `value=null`，typed原值仍留存；未把它們說成已知零或一般缺值。另連江114年 I9 是沒有typed數值的原字 `-`，以 `source_marker` 保留。原印數字0另行維持為0。
- 花蓮讀者表113年6月工作表的A6印「中華民國113年7月」；109年10月工作表的A6印「中華民國1109年10月」。共176格的正式year/month保留未知，沒有把1109改為109；3020僅是原字機械轉換候選，不作正式年月。
- 花蓮「借閱人數」與單位「人次」有計數基礎疑義，normalized unit保持未知。連江114年借閱原欄單位「人」另由同工作簿A24的定義支持人次，原欄仍完整保存。不同表的借閱數不能逕行加總。
- 連江114年總計觀測取原印C6「總計」；C7「館別」是通用欄頭，完整階層兩者均保留。實際換行與原字保留，未雙重反跳脫。

## 最小補正與變動界線

獨立解析發現花蓮讀者表109年9月 B9:I9 的 `office:string-value` 被製表漏存。製表者僅補這8個非統計表頭的 `source_stored_value_raw`。本報告保留修正前差異與雜湊，並將最終8欄復原為舊CSV空字串／JSONL null，精確重建原檔SHA；證明其他欄位、列序與序列化未變。**兩份long檔位元組完全未變**。

原件期待在讀製表之前先凍結，初凍格期待SHA為 `af3c712dc905bcea82eb582b0de0530a790e699fa192393d3b952acadcb01bf4`。審查者自身範圍、字面年月與格式契約的更正另列於JSON，不改原件數值以迎合製表。

## 排除與隱私

空白範本468個cells保留作結構證據，但0格進入long；讀者表每月第21列空白分隔不算統計格。連江114年「古蹟概況」原件105個數字格屬別的資料，不進入輸出。「背景說明-圖書館概況」聯絡欄A7:A9不輸出，僅留統計定義A17/A24/A26三格。已以原件聯絡字串核對四份輸出，0洩漏；本報告不附實際聯絡值、本機／Drive絕對路徑或認證資料。

## 方法與限制

ODS使用獨立ZIP/XML程式展開重複列欄、text:s／換行、型別、公式、style及合併範圍；XLSX獨立讀ZIP/XML、shared strings、cached value、formula、原style index與number format，再以openpyxl的data_only true/false交叉核全3工作表267個非空格，0差異。未啟動原生試算表軟體，未渲染或重算公式。XLSX數字的格式化顯示字串不在XML內，未宣稱核對實際畫面；只比對原快取及格式定義。原件業務母體與下載權利不因格式核對而自動認定可互比或可再授權。

## 最終輸出綁定

| 檔案 | SHA256 |
|---|---|
| `derived/phase1_local_sources_cells.csv` | `5a8e944da84092c48a550cf2d5068c52939b7f167b0615ff92e1ba135c1427c2` |
| `derived/phase1_local_sources_cells.jsonl` | `e7eace84cf6338294f659f48a246ecea41213ad1fe4027f225273db598d8c7a5` |
| `derived/phase1_local_sources_long.csv` | `2e855af5b5c545f24e05b14f13d7acc16939b691024ace0baa6e8f064e3ea55f` |
| `derived/phase1_local_sources_long.jsonl` | `804f4b9e5dcd0de6cd4be6f869343e7302ac2044cdd7ab33bc44dd92ecc00b80` |

原件SHA：

- `south-lienchiang-opendata-173786`：`de3b86da388ef7337e4996c06cde88fb1dd52ed0b95bfdd8186e545d1f94000b`
- `south-hualien-library-lending-409-reader`：`205a79d6aadce9f4580664d6b67078e5446b6e7fedab366b971b312f31fed1d2`
- `south-hualien-library-lending-409-room`：`69881ded57b1ede472a6f41cfb48f256d3963b0dba7d1b493d5e29a646b5c998`
- `south-lienchiang-culture-library-overview-114`：`cb7f4f0a2d8817e5c0ab6168d874ffa7c7e21104b871bbd8706ffc6e2f6512d4`

可重播期待、逐格定位、初凍與後續更正、修正前8格差異及完整核對結果：[phase1-local-independent-review.json](phase1-local-independent-review.json)。
