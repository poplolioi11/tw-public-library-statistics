# 第二階段更新與格式驗收

狀態：PASS；版本v0.7.0。

正常phase2_update流程已依序執行build_phase2、reader、documentation、validator。之後連續兩輪均只執行validator，0次builder；全部輸出與state的bytes／mtime不變。三層原始統計fingerprint前後一致，未重跑原件source audit，未改任何原統計值。

56,496筆量化ID逐層恰一次：37,887正式觀測、18,486地方來源格、123計畫數量。409張證據卡不增加觀測；CSV、JSONL與SQLite wide views逐欄一致；3291個稀疏卡片缺key依NULL核對；45個分割檔的SHA、聯集、順序及CSV投影一致。來源URL／SHA／locator／原值／狀態與新增版本、取得、授權欄逐筆回原資料。

5,098顯示／typed衝突保持null；176期間矛盾與35個catalog-only年份保持未知；114筆2012原比率未冒充原量；94筆千單位以Decimal精確換算；2,944個原報0未丟失。Reader內嵌summary同版，22,825組完整ID與原欄位、scope_summary及前2個sample IDs均回母表。

22項新合成測試及既有13＋15項更新回歸測試通過。合成測試涵蓋失敗回復bytes／mtime與狀態、並行輸入變更不回寫、缺原層停止、metadata-only來源不重建、code-only更新不製造資料內容變動、shared phase1文件hash同步及reader錯值反例。

這是來源量化層的格式／保留與更新驗收，不聲稱重驗未附原件全文、官方填報正確或人類雙校。未改public checkout、Git或發布。精確執行、code SHA、逐檔hash與mtime見[JSON報告](phase2-update-verification.json)。
