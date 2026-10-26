# 2005年公共圖書館統計：獨立原件覆核

**通過：7張指定表／子群，494個原印數字或標記位置，全量比對0差異、0漏格、0多格。** 先讀官方入口與原PDF建立期待並凍結，等producer封定後才讀CSV；未讀producer程式或表規格求答案。另137個位置由原圖直讀固定文字錨點，與獨立PDF數字字詞網格核對。

這是AI輔助的指定統計表完整格網覆核，不是整卷全文轉錄、人類逐格雙校、官方認證或原刊零錯誤保證。

## 原件、年份與範圍

年鑑卷號95；表1–5、107、108原題均明列民國94年，即資料年2005。官方入口可見出版日期2006-11-01；95年2月是問卷／名錄取得時間，不當資料年或私立館存量時點。

|指定來源|位置數|範圍|
|---|---:|---|
|公共章表1|30|5個國立／直轄市具名機構，購書、館藏與資源使用|
|公共章表2|30|同5機構的6類人員|
|公共章表3|115|23個原印縣市×5欄，PDF2–3完整續表|
|公共章表4|288|23縣市及合計×12欄，含原印未統計|
|公共章表5|8|私立公共館4指標及各自括號填答數|
|統計章表107|7|公共館完整分類子群，含私立與小計|
|統計章表108|16|公立／私立各4指標與各自括號填答數|

公共章PDF1–4為印19–22；統計章PDF4–5為印248–249。公共章表6是具名閱讀推廣／示範觀摩計畫表（PDF14–16），表7是特定閱讀運動活動，部分跨94/12–95/5（PDF34）；並非不存在，但不當成本批年度核心完整量。統計章原目次確認圖9–24為大專及中小學館，其他館際合作／出版申請圖亦不混入公共館子群。

## 值與原刊差異

446個整數、46個小數及2個「未統計」全比對通過。20個原報0仍為0；沒有原印留白。表4臺南縣進館人次與參考諮詢原印「未統計」，保留source_marker/null。這兩個中文字在PDF文字層缺失，依原圖核定，沒有誤當留白。

表5私立「館藏總數」1,293,063，表108私立「館藏圖書冊數」749,408；指標名／範圍可能不同，並列版本，不自行判誰錯或互補。私立借閱冊數兩表均466,195，但表5填答館數34、表108為35，原樣保留。

## 表頭、單位與母體

- 國立中央圖書館臺灣分館、國立臺中圖書館及另列直轄市機構照原名，不把國立館當國家圖書館或所在地縣市總量。23原縣市不重編成現行22縣市。
- 表4「合計」只及23原縣市，排除另列國立館與兩直轄市。producer context明列原表23縣市合計，不冒稱全臺所有公共館總量。
- 表107原分項只印國立、直轄市立、縣市立、鄉（鎮、市、區）立、社教館、私立、小計。沒有替raw增補圖書館或含私立字樣；小計含私立，數量包含分館。未另印計量單位，推定計量不能稱原印。
- 表108填答館數不含分館，分館統計併總館；與表107含分館館數的分母不同。12個填答數獨立標response_sample_size，不當設施總數或加回主要數量。
- 表1館藏、表3館藏及每人館藏共51格：原頭冊與正文冊（件、種）混合計量未決，保留unit=null、unit_raw=冊及source_heading_body_counting_unit_conflict_unresolved。
- 表5與108借閱人次共3格，欄名人次、括號人，保留unit=null及source_heading_counting_basis_unresolved。未知單位不等於數值缺失，也不推去重讀者。
- 年度流程／經費使用表題94年；公共章明述截至94年12月底的存量依來源語境標年末。問卷日期不補私立館存量時點；比率不反算原量。

## 明示的表示對照

1. 統計108初凍所選數字子行1–4，對應producer保留前一國家館兩行後的3–6。原實體館類列仍為2、3，逐格核對source_original_table_row；數字沒有換格。
2. 12個填答數的可見括號（表5另含館字）保留於source_parenthetical_raw／source_visible_cell_raw；raw_value僅存原數字token。括號原式與數字分別嚴格比較，不刪原符號後假稱全文相同。
3. 表5原實體列名為94，私立公共圖書館來自表題，全國是地理context。期待的entity_raw=null、source_category_raw=私立公共圖書館；producer以entity_raw存該表題館類，另以table_title_scope_not_printed_geography_row明示，entity_contextual_name=全國。類型、原年度列名、context與狀態均逐格核對，不略過地理檢查。
4. 表107中／英是同一分類標籤的兩個文字對齊區，數字使用資料欄2。初凍的第3欄概念改稱source_text_alignment_zone=3，並非原件有編號的實體欄。

## 初凍與覆核更正

- 初凍檔：[ncl-2005-independent-expectations-frozen.json](ncl-2005-independent-expectations-frozen.json)；SHA-256 `18529071806528871e512674e7e946c7f1452b8178860c011e2d2aaecdd0714f`，完全未改。
- producer讀取前依原圖重核37格單位描述：表108填答數8格改記斜欄頭原單位館；表1／4共29格借閱冊數保留原括號冊數，不改數字。詳[ncl-2005-independent-source-semantic-corrections.json](ncl-2005-independent-source-semantic-corrections.json)。
- 比對後回看原欄頭，表4的24格「進館人次」已直接在欄名印人次，補入單位原詞，不因未另加括號而漏記；這個後續表頭澄清另存[ncl-2005-independent-postcomparison-header-clarifications.json](ncl-2005-independent-postcomparison-header-clarifications.json)，沒有修改原數字或初凍副本。
- 對照只指出表5回覆數4格的原列名附加整理說明「同列括註」；producer已將raw改回94，說明另存，值、metric_id及定位未變。
- 時間metadata最後補字：重新視讀公共章PDF1／印19右欄，原文確為「截至94年12月底」。producer僅於time_reference補回底字，並明示私立95年2月是調查而非stock時點。原數字、標記與定位期待未改；JSON的method及post_freeze_time_metadata_correction記錄此步驟。
- 最終CSV SHA-256：`2444be930e34ae76107acee0f455c72a8e52bb999d70010a661b7e0299c235dc`。
- [可重播JSON](ncl-2005-independent-review.json)保存所有494位置、來源SHA、初凍SHA與後續表示／原頭更正；5,681項逐格數值、原字、狀態、表頭、標籤、單位、母體、bbox與時間引用檢查全部通過。原數格／標記／可見括號指紋初凍前後相同。

## 官方來源與公開邊界

[95卷官方入口](https://www.ncl.edu.tw/librarianship-yearbook/0Q083565572390216434)。

- [公共館章](https://www.ncl.edu.tw/files/file_pool/1/0Q083565578841549902/38a51da4-b229-49c7-9fc4-df30882cd658.pdf)，SHA-256 `b5f6a52c5b861e1d74b4d917497cd9c806286845ee9bb1a3b8349b2b23a19efe`。
- [統計章](https://www.ncl.edu.tw/files/file_pool/1/0Q083565572644598946/785730e1-bd57-49fc-8a26-6ff5c62a933a.pdf)，SHA-256 `4b725f1a7e58d3b8629f76655e0ff678d4db4dc3f8bfdbb4a721211fa9303d78`。

獨立下載副本與shared raw原件的SHA相同。僅facts報告、逐格期待及必要口徑可進公開包。原PDF、全頁PNG、完整抽字、入口HTML與私有工具在`research/ncl-2005-independent.private/`，不公開；全文授權未確認，沒有把署名專章整份改授權。未補算2012，未動producer、共用程式、canonical或Git。
