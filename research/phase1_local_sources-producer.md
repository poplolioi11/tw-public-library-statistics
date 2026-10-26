# 第一階段地方來源：南組四附件整批製表

四份已定位的官方附件已完整擷取相關統計工作表，產出 **18,486 個資料格**，另有含表頭、模板及結構空白的 **33,705 個來源格事實**。這是獨立的 phase1 source-cell 資料層，沒有加進原有年度 canonical，也不把全部格數稱為數值或館數。

## 來源與完整範圍

|來源|原件 SHA256|完整相關範圍|
|---|---|---|
|[113 年連江縣公共圖書館概況](https://data.gov.tw/dataset/173786) [ODS](https://www.matsu.gov.tw/chhtml/adddownloadcount/371030000A/101571?mcfilename=Mcfile2&type=D)|`de3b86da388ef7337e4996c06cde88fb1dd52ed0b95bfdd8186e545d1f94000b`|1 工作表，5 指標 × 6 原館名及總計＝35 格；完整原格 48。|
|[花蓮縣借閱概況／讀者身分別](https://www.hccc.gov.tw/zh-tw/Download/Statistics/409) [ODS](https://www.hccc.gov.tw/Utility/DisplayFile?id=16274)|`205a79d6aadce9f4580664d6b67078e5446b6e7fedab366b971b312f31fed1d2`|73 sheets＝1 空白模板＋72 個名義月份；11 讀者身分列 × 8 原欄 × 72＝6,336 格；原格 13,797。|
|[花蓮縣借閱概況／館藏地（室）](https://www.hccc.gov.tw/zh-tw/Download/Statistics/409) [ODS](https://www.hccc.gov.tw/Utility/DisplayFile?id=16275)|`69881ded57b1ede472a6f41cfb48f256d3963b0dba7d1b493d5e29a646b5c998`|73 sheets＝1 空白模板＋72 個名義月份；每月全部原館／室列及 8 原欄，共 12,080 格；原格 19,701。列數隨來源版本月份變動，不套固定館名清單。|
|[連江文化處 114 年公共館概況](https://matsucc.gov.tw/%E8%AA%8D%E8%AD%98%E6%96%87%E5%8C%96%E8%99%95/%E9%A0%90%E5%91%8A%E7%B5%B1%E8%A8%88%E6%AA%94%E6%A1%88%E4%B8%8A%E5%82%B3%E5%8D%80/) XLSX|`cb7f4f0a2d8817e5c0ab6168d874ffa7c7e21104b871bbd8706ffc6e2f6512d4`|全部 3 sheets 已盤點。圖書館表 `C8:I12` 全 35 格，必要背景定義另存 3 格；含表頭共 159 原格。聯絡背景及不相關古蹟表明確排除。|

花蓮兩附件各有 109 年 9 月至 115 年 8 月的 72 個名義月（2020-09 至 2026-08），兩份是不同統計分組，不能相加為不同人口或相異月份。完整表頭原文、sex／總計維度、來源行名、原空白與合併格均保留；沒有只取第一個月、第一頁或第一個館。

## 期間與統計口徑

- 113 連江 ODS 附件本身未印年度；正式目錄標題的「113年」另以 catalog-year basis 記錄，不假稱附件內有年，也不借用 114 工作簿定義補精確日期。
- 114 工作表 A4 明列 114 年度。來源背景 A17 的靜態／動態時點、A24 的借閱人次、A26 的冊次定義只用於同份工作簿，未套到另一年來源。原表 A25「總館計入分館中」照留，不自行修正。
- 花蓮讀者身分別 `113年6月` 工作表 A6 寫「中華民國113年7月」；`109年10月` A6 寫「中華民國1109年10月」。兩組原字與各自候選都保留，正式 period year／month 均 null，**不選其中一邊**。其他已對應月以原表頭及 sheet 名相符為依據，未用出版日填月份。
- 花蓮原上層欄頭「借閱人數」與全表原單位「人次」並存；原字分欄保存，計數口徑未釐清時 normalized unit 留空。來源「借閱冊數」保留原單位冊，不替來源改成別的欄頭。
- 多層表頭不以第 1 列硬當 header。保留原層級、原合併起點／範圍及 covered-cell 狀態；年度、月度、模板與資料列分開。

## 0、顯示符號、空白與公式

18,486 格中，**13,387** 格保留可解析的來源數值；另 **5,098** 格的 ODS 顯示文字是「-」等標記、底層 typed value 卻為 `0`。這 5,098 格保留 display raw、stored raw、typed numeric value 及格式 style；`value=null`、狀態 `source_display_typed_value_conflict_unresolved`，不只按顯示叫它缺值，也不逕稱實測零。另 114 XLSX 1 格原字「-」為沒有 typed 數字的字串標記，獨立 `source_marker`。

ODS 原格式中的空格／tab／換行按 XML 展開，保留原文。XLSX 不存已格式化的數字顯示文字，因此不捏造畫面：保留 cached 原數值、字串、formula、style 及 number-format code，明示未渲染／未重算。所有原公式仍是來源公式及其 cache，不宣稱本次執行過 Excel 計算。

空白模板保留在 source-cell 層，**不灌入 18,486 觀測格**。ODS 尾部重複到 1,048,576 行的純空白格式區不是資料；metadata 保留宣告尺寸與實際 used bounds，未將格式空行展開成虛構觀測。

## 隱私、授權與排除

113 連江來源由 discovery inventory 核實 data.gov.tw 目錄的明示 OGDL-1.0；其餘兩機關的統計文件完整附件授權仍未確認，不因官網可下載便宣稱整份開放。僅輸出統計事實與必要欄頭／定義，原 workbook 不列公開包。

114 工作簿「背景說明-圖書館概況」A7:A9 聯絡欄不輸出；只取必要統計定義 A17、A24、A26。古蹟概況 sheet 的 A3 原題已記錄為不相關排除證據，不取其統計。各月簽章／人事 footer 不公開；必要修訂註、統計資料來源及原表定位留在 metadata。公開候選 cell text 掃描沒有電子郵件、聯絡電話／傳真字樣，未用手機 regex 去刪 SHA、官方 URL 或一般統計數字。

## 重播與驗證

```sh
python3 scripts/extract_phase1_local_sources.py --offline --self-test
```

依賴只有 bundled Python 3.12 標準庫的 ZIP／XML／Decimal。公開預設原件目錄為相對 `raw/phase1_local_sources/originals/`；私人維護端可用 `--source-root` 或 `TW_LIBRARY_PHASE1_SOURCE_ROOT` 指定來源目錄，參數值不寫入資料或公開契約。原件已下載至既有 Drive 專案的 `原始資料/phase1-local-20261026/`，下載工具保留 source URL、final URL、SHA 與取得時間，沒有 cookie／憑證。113 來源在系統 Python 遇 TLS protocol-version 錯誤；改以 bundled Python 執行同下載器，正常憑證驗證成功，沒有關閉 TLS 驗證。

程式先驗全部四份 SHA，再處理任何輸出。已驗完整相關 sheet／原格對帳、原 display／typed／formula／style roundtrip、唯一識別、CSV／JSONL 逐欄一致、兩輪離線 bytes＋mtime no-op、缺原件／變更 SHA 均停止並保留前版。這是來源格事實驗證，不代表官方填報正確、已重算公式或人類雙校。

## 交付

- `derived/phase1_local_sources_cells.csv/.jsonl`：33,705 原格事實，含必要原表頭、模板及結構空白。
- `derived/phase1_local_sources_long.csv/.jsonl`：18,486 完整統計資料格，保留未知狀態，不直接加入年度 canonical。
- `raw/phase1_local_sources/sources.json`：四份來源版本鎖定。
- `raw/phase1_local_sources/<source_id>/metadata.json`、`contract.json`：每來源全部 sheet、範圍、排除、期間衝突、完整格數與精確依賴／輸出 SHA。
- `raw/phase1_local_sources/summary.json`、`verification.json`：總對帳及自驗。

cells CSV SHA256 `d55b0b3109b8373a5e6de9d630b2b4fe8ff371e97da7be199eded01ea7016f13`。

long CSV SHA256 `2e855af5b5c545f24e05b14f13d7acc16939b691024ace0baa6e8f064e3ea55f`。

新的原件／成果在掛載 Drive 中僅標 **待 root 雲端列檔讀回**，尚不宣稱已同步完成。不改既有 canonical、adapter、registry、build、docs、版本、public checkout 或 Git；已 freeze 的 programme 數值亦未動。
