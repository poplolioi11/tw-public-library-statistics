# 94年卷統計章：完整公共館相關子群

本批v0.9.2整理《中華民國九十四年圖書館年鑑》統計章的三張表。資料年依各表明印「民國93年」確認為2004年，精確起訖未確認，不填年底日期。

| 原表 | 官方原件定位 | 完整選入範圍 | 實體格／獨立數量 |
|---|---|---|---|
| 145 圖書館數量 | [PDF5／印440](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | 公共館區塊全部7列，含私立與小計；國家圖書館另列不納入 | 7／7 |
| 146 基本資料 | [PDF6／印441](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 公立、私立公共館2列×館藏、席位、借閱人次、借閱冊數4欄，主值及括號填答數全部保留 | 8／16 |
| 147 館際合作協會會員 | [PDF11／印446](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=11) | 「公共」類會員欄完整1格；獨立會員母體 | 1／1 |

合計16個實體格、24筆來源觀測。8筆括號填答館數是另一項數量，與主值共用physical_cell_id；不是24個獨立實體格，也不是新增24間圖書館。表146原註：填答館數不含分館，分館統計併入總館；表145數量含分館。兩者不能互補、相除推算或混接。私立列、含私立小計、公共會員與國家圖書館各保留原母體，沒有合成全臺面板。

原件SHA-256：`2db33efbce20154623b6ba7398e2cfa40af8116578264889d380ab41520c44cf`。完整原件12頁已盤點；學校、其他館型、混合全館型及出版統計圖10–29未納此公共館子群，不標為無資料。沒有散布原PDF、整頁圖或署名全文。

每筆正式觀測保留原件URL、SHA、PDF／印頁／表／列／欄及bbox。`source_time_reference`的`physical_source_context`保留完整原格文字、兩引擎數字、主值／填答角色、共用實體格識別及括號標點的AI原圖補錄說明；原PDF的CMap漏括號，兩份原生擷取文字也另留，不將補錄說成原生文字層。表145與147沒有獨立印出單位，8筆unit保持null；計數對象保留在標題與母體。沒有推算期間或補零。

逐格[統計投影](../derived/ncl94_statistics_source_cells.json)、[正式24筆](../derived/ncl94_statistics_observations.jsonl)、[批次說明](../raw/ncl94-statistics/extraction-metadata.json)及[驗證器](../scripts/validate_ncl94_statistics.py)可重跑。雙PDF引擎比對與主代理／助手原圖核讀是AI與程式查核，**人工核讀與人工雙校仍未完成**，不能報人類錯誤率或當作正式比較測試集的標準答案。該來源不在既有未參與訂規則的正式保留測試集。

2012完整22縣市核心原量缺口不變。原有58,245筆觀測逐筆全欄不變；本版另增24筆，主資料共58,269筆，數值缺值仍6,922筆，期間未確認467筆。全庫單位未知增加8筆為1,698筆，是忠實保留原刊未印單位，沒有以減少缺值為目標猜補。

## 完整原報數量（不是抽樣）

| 表／原列 | 原欄 | 主量 | 括號填答館數 | 主量單位 |
|---|---|---:|---:|---|
| 145／公共圖書館／國立 | 數量 | [3](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | — | 未獨立印出，保留null |
| 145／公共圖書館／直轄市立 | 數量 | [53](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | — | 未獨立印出，保留null |
| 145／公共圖書館／縣市立 | 數量 | [40](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | — | 未獨立印出，保留null |
| 145／公共圖書館／鄉鎮、市、區立 | 數量 | [413](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | — | 未獨立印出，保留null |
| 145／公共圖書館／社教館 | 數量 | [3](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | — | 未獨立印出，保留null |
| 145／公共圖書館／私立 | 數量 | [124](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | — | 未獨立印出，保留null |
| 145／公共圖書館／小計 | 數量 | [636](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=5) | — | 未獨立印出，保留null |
| 146／公立公共圖書館 | 館藏圖書冊數 | [23,071,122](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [509](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 冊 |
| 146／公立公共圖書館 | 閱覽席位 | [71,588](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [509](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 席位 |
| 146／公立公共圖書館 | 借閱人次 | [10,329,679](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [509](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 人次 |
| 146／公立公共圖書館 | 借閱冊數 | [30,498,418](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [509](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 冊 |
| 146／私立公共圖書館 | 館藏圖書冊數 | [743,056](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [58](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 冊 |
| 146／私立公共圖書館 | 閱覽席位 | [8,265](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [58](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 席位 |
| 146／私立公共圖書館 | 借閱人次 | [188,701](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [58](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 人次 |
| 146／私立公共圖書館 | 借閱冊數 | [659,228](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | [58](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=6) | 冊 |
| 147／數量 | 公共 | [37](https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf#page=11) | — | 未獨立印出，保留null |
