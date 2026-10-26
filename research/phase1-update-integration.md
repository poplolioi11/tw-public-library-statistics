# 第一階段增量更新整合驗收

狀態：PASS。programme 與四份試算表維持獨立資料層；沒有變更來源統計值、canonical、版本或發布。

- 新增 `data/reviewed_phase1_batches.json`、`scripts/phase1_source_registry.py`、`scripts/phase1_source_manager.py` 與離線測試；更新 `run_update.py` 和 `restore_originals.py`。
- 保留修正前 freeze，新 freeze 綁定 8 個表頭 office:string-value 更正及目前程式／輸出。統計長表 SHA 不變。
- 原件 SHA、程式、輸入及輸出 hash 決定是否重建；首次可由已覆核的相同 hash 啟動快取。原件缺失或變版先停，抽取失敗回復前版輸出 bytes、mtime 與狀態。
- 四個既有下載 URL 每 14 天於正常線上更新檢查；今天以原件取得日判定尚未到期，實際 0 次下載。變版只留私人 SHA、URL 與 review_required，不覆寫已核原件；HTTP 失敗不推進成功時間。預設不保留新候選全文。
- `--phase1-only` 可精確 restore 四原件，必須符合已核 SHA。相對 originals 或 `TW_LIBRARY_PHASE1_SOURCE_ROOT` 支援可攜部署；本機四個私人 symlink 只指向既有原件，沒有搬刪。
- 新增 13 項離線測試、既有 15 項更新群組回歸測試全部通過。真實兩次批次快取讀回，22 份登錄輸出及 2 份狀態 bytes／mtime 全不變。四原件 restore 真實命中 SHA 快取。
- 更新順序：來源 hashgate／到期監測 → 既有來源流程與 canonical release／coverage／documentation → phase1 inventory／supplements／reader／documentation → validators。第二輪未變略過所有 builder，validator 仍執行。
- 全層簽章介面：`phase1_source_registry.content_digest(root)`；`run_update.content_signature(root)` 合併 canonical 與獨立層。root 負責 package_release 去重；本代理未修改發布器。

限制：未於 root 同時製版時執行完整 `run_update.py`；已用隔離 fixture 驗證順序與第二輪 no-op。到期 HTTP 分支以離線 fixture 驗證，今天無需線上重抓。來源監測不等同官方填報正確、人工雙校或新版本自動接受。公開預設 validator 仍嚴格；私人維護端允許本機部署欄位。未核全文授權的原檔均不入公開包。

精確 hash、逐檔快取讀回及驗收界線見 [phase1-update-integration.json](phase1-update-integration.json)。
