# 公開副本與來源原件

資料版本v0.9.0。正式資料58,245筆，value=null共6,922格，其中原刊留白1,303格、原刊明示缺值206格、原印文字狀態（不自行解讀為0或不適用）5,413格。原刊留白不推定為0或不適用，明示缺值保留原符號，未解析數字不能改標為缺值。這次公開不修改統計原值、來源網址、原件SHA、定位、期間、地區或單位。22份OGDL原始檔含與統計無關的聯絡欄，公開副本省略這些原件，另提供欄位投影；中間表的 original_fields 也不再散布。完整原始工作檔未改寫。

- source_sha256：政府原件的SHA256，未套用投影雜湊。
- public_evidence_path / public_evidence_sha256：另附的統計欄位投影及其雜湊。
- public_projection_policy：刪除的無關欄位與保留規則。
- snapshot_distribution=not_in_public_bundle：原件未附於公開版本；不表示統計值遺失。

raw/omitted-originals.json保留原件網址、雜湊、公開投影位置與被省略欄名，不含實際聯絡值。原件可透過README的restore_originals流程重新取得並核對指定SHA，僅寫入本地研究副本。來源如改版會停止要求覆核，不默認新內容就是舊版。

公開前的完整來源回查記錄於research/source-verification.md；PDF影像抽查範圍仍有明確限制。公開副本離線驗證只確認資料格式、數值不變、分割檔聯集及投影／檔案完整性，不會把省略原件當成已重新下載核對。

分析可直接使用三格式或data/by_year/index.json中的年度分割；不需要下載完整PDF或聯絡欄。公開程式的單元測試使用隨包公開檔案或合成案例，不需要憑證、私人排程或政府網站連線。

正式 data_year=null 保留原刊未明印年份或跨年期間，不以出版年、版次年或0補填。年度索引另列 data_year=null 的 unresolved_period.jsonl；已確認年度與未知期別分檔的聯集完整等於 canonical，原期間文字、狀態、數值與定位均不改寫。

本版所有derived CSV／JSONL省略original_fields整列副本；統計欄位與列序不變。私有製表檔SHA與公開投影SHA分列docs/derived-field-projections.json，原件source_sha256仍是政府原件。公開前來源驗收綁私有製表CSV；復原原件並重建後才可重跑該驗收，公開投影離線驗證另驗本公開manifest，不假稱兩種衍生檔bytes相同。

新增來源格只公開統計投影；完整原工作簿、PDF與網頁不再散布。私有儲存路由欄不屬統計來源，公私metadata雜湊與刪除規則見docs/metadata-field-projections.json；原件SHA、URL及格位不改。

第二階段口徑註記另附逐筆CSV／JSONL／SQLite與年度分檔；三個原量化層的語意指紋不變。口徑檔沒有新增營運量；來源證據卡與當代定義參照不認證所有歷年方法。公開格式驗收不假稱重查未附原件全文。

第三階段選源四表與SQLite按已驗來源包原樣公開，P1／P2文檔後再產生第三階段入口與折線說明。record_routes、candidate_decisions、queries與series_edges是選源註記，不是新增營運量；選定來源、原缺值與可畫線許可分開保留，無關聯絡欄及原件全文仍不公開。

完整CSV與SQLite亦以gzip無損壓縮。先解壓即可使用標準工具；GitHub Release另附解壓後同內容CSV與SQLite，附件SHA256SUMS對實際附件計算，不把gzip雜湊當解壓後檔案雜湊。原件SHA、來源定位、原值及NULL均不變。
