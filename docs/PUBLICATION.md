# 公開副本與來源原件

正式資料為19,975筆、188個來源明示缺值格。這次公開不修改統計原值、來源網址、原件SHA、定位、期間、地區或單位。22份OGDL原始檔含與統計無關的聯絡欄，公開副本省略這些原件，另提供欄位投影；中間表的 original_fields 也不再散布。完整原始工作檔未改寫。

- source_sha256：政府原件的SHA256，未套用投影雜湊。
- public_evidence_path / public_evidence_sha256：另附的統計欄位投影及其雜湊。
- public_projection_policy：刪除的無關欄位與保留規則。
- snapshot_distribution=not_in_public_bundle：原件未附於公開版本；不表示統計值遺失。

raw/omitted-originals.json保留原件網址、雜湊、公開投影位置與被省略欄名，不含實際聯絡值。原件可透過README的restore_originals流程重新取得並核對指定SHA，僅寫入本地研究副本。來源如改版會停止要求覆核，不默認新內容就是舊版。

公開前的完整來源回查記錄於research/source-verification.md；PDF影像抽查範圍仍有明確限制。公開副本離線驗證只確認資料格式、數值不變、分割檔聯集及投影／檔案完整性，不會把省略原件當成已重新下載核對。

分析可直接使用三格式或data/by_year/index.json中的年度分割；不需要下載完整PDF或聯絡欄。公開程式的單元測試均使用合成資料，不需要憑證、私人排程或政府網站連線。
