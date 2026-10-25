# SEGIS 線索與主計總處縣市館數取得

查核日：2026-10-25。採背景 HTTP 與檔案處理，沒有操作使用者畫面、登入或繞過權限。

## 已取得的完整來源包

本次循行政院主計總處縣市重要統計指標查詢系統的正常匿名表單，取得 **Z091101a029「公立公共圖書館個數(所)」全部可選年份與全部地理欄**。

- 正式入口：<https://winstacity.dgbas.gov.tw/DgbasWeb/ZWeb/StateFile_ZWeb.aspx?Type=table>
- 原始指標定義：「公立公共圖書館館數（包含國家圖書館、國立公共資訊圖書館及國立臺灣圖書館）。」資料來源列教育部。
- 選單為 1998–2025 共 28 年、22 縣市及總計，共 **644 格**。每一格均已回查，沒有以抽樣代替整包取得。
- **2006–2025 共 20 年 × 23 欄＝460 格有數值**；1998–2005 的 184 格全部為官方「-」，長表保留 `not_available_in_source` 與原符號，數值留空。
- 所選為官方「改制後縣市別」。2006–2010 的歷史值同樣依官方發布的改制後地理範圍保存；沒有自行把舊縣市加總成新縣市。
- 來源未明示本表每年特定測量日期，保留參考年、`period_start/period_end=null`，沒有把選單的 1 月 1 日當成統計調查日。
- 本指標納入國家圖書館，與國資圖公立公共館序列未證同母體。使用獨立 source family，不相加、不互相補值。

## 正常公開取得流程

1. GET `StateFile_ZWeb.aspx?Type=table`，讀取該次公開表單 hidden fields。目錄中本指標核取值為 `Y967`，定義代碼為 `Z091101a029`。
2. 依表單的「完成挑選」動作 POST `Varval.aspx`，設定 `UID=Y967`，其餘 `Type/Area` 使用原表單的值。
3. 讀取回傳頁的全部年度選項及全部地理選項，依頁內 `beforeShowQuery()` 的實際欄位 POST `ShowQuery.aspx?Z=`。選取 `axEffect=967`、`axX=[Measures]`、`axY=[Date];[Place]`，年度與地理值均來自選單，沒有猜測私人 API。
4. 回應的 `#dataTable` 已含全部值；網站的 CSV／Excel 匯出由前端以這個資料表在本機產生。本案保存完整官方 HTML，再轉出全部原格 JSON、原表 CSV 及可追溯長表，沒有宣稱這些轉出檔是獨立官方下載 URL。

完整公開選取參數保存在 `raw/segis-history/dgbas-query-request.json`，長表的 `source_request` 亦保留選取參數。暫時性 ViewState 取自每次新表單；沒有私人登入或會話憑證。

## 檔案

| 用途 | 路徑 |
|---|---|
| 全部 644 格長表 | `derived/dgbas_county_historical_long.csv` |
| 欄位 schema | `raw/segis-history/schema.json` |
| 原始完整 HTML | `raw/segis-history/dgbas-showquery-76a80eb8b8c69eeb8f9ec0260169c50e3a99c1a5ce746199a7a56b6b8fa7a13b.html` |
| 全部原格與 HTML 屬性 | `raw/segis-history/dgbas_county_original_cells.json` |
| 原表完整 CSV 轉出 | `raw/segis-history/dgbas_county_original_table.csv` |
| 來源、年度完整格數與權利證據 | `raw/segis-history/metadata.json` |
| 取得／離線解析程式 | `scripts/fetch_segis_history.py` |
| 獨立驗收 | `scripts/verify_release.py`、`research/source-verification.json` |

每一筆長表含原始值、狀態、單位、原年度、地理代碼、母體、來源 URL、POST 選取參數、原始回應 SHA-256、不可變原檔路徑，以及 HTML 表格列、欄與屬性定位。原始回應 SHA-256 為 `76a80eb8b8c69eeb8f9ec0260169c50e3a99c1a5ce746199a7a56b6b8fa7a13b`。

## 授權證據與界線

[主計總處政府網站資料開放宣告](https://www.stat.gov.tw/cp.aspx?n=3164) 明列網站資料與素材得受著作權保護之範圍「採政府資料開放授權條款-第1版發布」，使用時應註明出處，並保留特別聲明第三方著作等例外。本次取得的母站宣告 HTML 已以雜湊副本存入 `raw/segis-history/licence-*.html`。

查詢子站這幾個公開頁沒有另列一份獨立授權條款。因此以 `OGDL-1.0_site_declaration` 記錄母站宣告，並明示 `license_scope_inference=true` 與套用子站的判斷界線；沒有把同屬 gov 網域本身當作授權證據。資料包整理的是官方數值統計事實，未包含機關標誌與其他文章／第三方作品。

## 重現與安全更新

```text
python3 scripts/fetch_segis_history.py --offline
python3 scripts/fetch_segis_history.py --refresh
python3 scripts/verify_release.py
python3 -m unittest discover -s scripts -p 'test_*.py'
```

`--offline` 只解析已存的官方回應。`--refresh` 才重新走匿名公開表單，需有效網路。新下載的 ViewState 等暫時欄位可能使 HTML 雜湊改變，不代表統計資料改版。

程式以完整指標註解、全部年度選項、地理代碼與名稱、全部 644 原始值計算內容指紋。舊原始 HTML 存在且雜湊正確、內容指紋未變時，保留原長表、首次下載引用與原始 HTML 版本，只記錄最近檢查及本次回應證據。定義／口徑改變則保留新原檔供覆核，停止替換舊 CSV。

若公開包沒有完整 HTML，重現必須重新下載；舊原檔不存在或損壞時禁止命中舊快取。即使統計格相同，也會以本次完整回應建立可驗證的新來源版本，不保留失蹤的舊原檔雜湊。新 HTML 的 ViewState 雜湊不保證與首版相同。

連線錯誤、缺格、結構或口徑變更不覆寫既有最終長表；最近失敗另記於 metadata。改版前的 CSV／metadata 保留在 `raw/segis-history/versions/`。未建立排程；90 天檢查週期可由主管線使用，但不等於已啟動監測。

本次離線測試實測：只有 ViewState／版面差異時不改觀測引用；原 HTML 缺失／損壞時建立新來源引用；網路失敗、缺格、定義變更時保留舊長表。所有測試使用臨時目錄，沒有重刷剛取得的正式來源。

## SEGIS 本身仍未完成的部分

[SEGIS 官方目錄](https://segis.moi.gov.tw/STATCloud/Catalog) 完整 HTML 已保存，確列「行政區公立公共圖書館統計」民國 95–114 年、全國／縣市、公立公共圖書館個數。[資料利用規範](https://segis.moi.gov.tw/STATCloud/DataUseInfo) 區分公開免申請與公開需申請資料；免申請資料依其政府資訊開放授權規範利用，不能把平台內所有產品一律當成相同授權。

SEGIS 目錄腳本 `pages/Dataset/SC_Catalog.js` 本輪兩次背景 HTTP 讀取逾時，未取得其個別產品識別碼、底層整包與個別授權。本次完成的是同題目的主計總處官方完整來源包，不把 SEGIS 產品標成已下載，也不將這個逾時解讀為沒有公開資料。
