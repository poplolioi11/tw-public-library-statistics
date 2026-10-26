# 授權與來源權利

本專案分別處理自行撰寫的程式／說明與上游資料權利。MIT 不會改變政府資料、原文件或第三方內容的授權；資料也不因被整理進同一個檔案，就一律變成同一種授權。

## 資料按來源標記

| 資料範圍 | 本專案記錄方式 | 再利用依據與界線 |
|---|---|---|
| 國資圖 2023 明列開放資源 | `OGDL-1.0_explicit_link_2023` | [資料集 6425](https://data.gov.tw/dataset/6425)明列[政府資料開放授權條款第 1 版](https://data.gov.tw/license)；只及該明列資源版本，不自動延伸其他年度或申請資料。 |
| 新竹市、臺中市地方開放歷史表 | `OGDL-1.0_explicit_local_catalog` | 各官方目錄同時確認 OGDL 標示及資源連結；來源與授權證據逐檔保留於 [地方 metadata](derived/local_historical_metadata.json)。 |
| 主計總處歷史公立公共圖書館統計表 | `OGDL-1.0_site_declaration` | [官方政府網站資料開放宣告](https://www.stat.gov.tw/cp.aspx?n=3164)採 OGDL 第 1 版，另有特別聲明／第三方內容的例外。擷取範圍限所列官方統計表；[來源 CSV](derived/dgbas_historical_long.csv)的 `license_code` 與正式觀測的 `license_status` 保留此區別，沒有將整本報告其他內容納入。 |
| 主計總處縣市公共館數查詢子站 | `OGDL-1.0_site_declaration`；`license_scope_inference=true` | [主計母站廣泛開放宣告](https://www.stat.gov.tw/cp.aspx?n=3164)為適用推論依據；[查詢子站](https://winstacity.dgbas.gov.tw/DgbasWeb/ZWeb/StateFile_ZWeb.aspx?Type=table)未另列條款，不能稱為子站獨立授權。保留 [來源 CSV](derived/dgbas_county_historical_long.csv)的 `license_scope_note`／`license_scope_inference`；只整理官方統計事實，不納標誌或第三方作品。 |
| 國資圖現行公開全國圖表 | `publicly_published_statistical_facts` | 重整公開統計事實，保留 URL、定位與內容雜湊；沒有據此宣稱網站 HTML、JavaScript、圖像或全部資料庫具有 OGDL 授權。 |
| 國家圖書館年鑑所列統計事實 | `published_statistical_facts_document_license_unconfirmed` | 僅重整所列數字、指標、必要口徑與來源定位；未確認署名專章全文的開放授權，不將全文當作開放著作。 |

OGDL 資料再利用時請遵守其條款，包括適當標示提供機關與資料來源。本專案另保留原始資料 URL 與版本，便於使用者查核。

經濟部智慧財產局[〈智慧財產權答客問：利用政府機關公開的經濟數據及表格〉](https://www.tipo.gov.tw/wSite/public/Attachment/0/f1748337027939.pdf)說明，單純數據羅列可能不具著作所需的原創性／創作性，數表等亦可能屬著作權法排除範圍。本專案對公開統計事實的整理與引用採此區分；這不代表所有政府出版品、編排、署名論述或附件都自動開放。

公開交付包不再散布 NCL PDF、網頁原始 HTML 或 JavaScript。部分 `source_snapshot_path` 是本機研究證據路徑，可能未包含於公開包；應依 `snapshot_distribution` 及實際交付清單判斷，原文件可回官方 `source_url`／`source_page_url` 查閱。其他有明確授權的來源原檔，仍按其原授權處理。

主計縣市館數的原始 HTML 亦不入公開包。交付[擷取的原始格子事實 JSON](raw/segis-history/dgbas_county_original_cells.json)、官方查詢頁連結與[正常公開表單 POST 重現腳本](scripts/fetch_segis_history.py)，保留數值、明示缺值、口徑與定位；這不將查詢子站的原始網頁程式或整體編排改授 MIT。

國資圖[現行數據申請公告](https://publibstat.nlpi.edu.tw/Frontend/News/ShareNewsView?NewsID=News000050)另限制申請資料用途與再提供。本專案沒有將舊目錄授權泛用至新申請資料，也不因這份公告逕稱既有合法開放版本的授權被撤銷。

## 第一階段新增來源的權利範圍

連江113年附件沿用[官方目錄173786](https://data.gov.tw/dataset/173786)所列該資源的OGDL及顯名要求。花蓮兩份借閱ODS、連江114年XLSX與國圖2005計畫表只公開數字、必要分類／口徑及來源定位；其原件全文授權未確認，逐筆license_status保留此狀態，不宣稱整份工作簿適用OGDL。

本專案以[著作權法第9條](https://www.tipo.gov.tw/tw/copyright/694-17733.html)及智慧財產局對單純統計事實的說明作為區分依據；這是本專案對已選統計投影的適用判斷，不是官方對本資料集的授權認證。原件的特殊編排、署名論述、圖像、標誌及其他受保護內容不以此概括授權。公開來源格含必要原表頭、數字／缺值字串、公式與格式代碼以說明顯示／底層差異；沒有附原工作簿、版面全圖或聯絡欄。

來源入口清冊只列官方URL、查核時間、內容雜湊、必要標題／定位及本專案寫的狀態說明；原網頁全文、HTTP憑證與cookie不公開。候選權利有衝突或未解時維持pending，未經覆核不發布原件。

## 本專案原創程式與說明：MIT License

以下 MIT 授權適用本專案自行撰寫的程式與說明文件；上游資料、原文件、標誌及第三方內容依前述來源權利處理。

Copyright (c) 2026 tw-public-library-statistics contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


## 無關聯絡欄的最小化公開

部分明確OGDL原始檔含與統計無關的電話與電子郵件，本公開副本不再散布這些原件或中間表的完整原列欄位。另提供保留統計欄位及原列次序的公開投影；投影仍依原OGDL與顯名條件使用。原件與投影分別記錄SHA，原件官方網址與定位保留，沒有把經刪除欄位的投影冒充原始檔。
