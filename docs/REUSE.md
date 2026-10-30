# 使用案例、引用與回饋

這份資料的用途須由可核對的使用成果累積。目前此文件沒有列入已證實的外部採用案例；這不表示外部一定沒有人使用。

## 可以先試的三件事

1. [查看2020–2024年全國借閱冊數](https://poplolioi11.github.io/tw-public-library-statistics/?profile=national-ncl-book-loans-panel&from=2020&to=2024)，點一個數字回原刊，確認年份、單位及母體。
2. [查看各縣市歷年館數（主計原報）](https://poplolioi11.github.io/tw-public-library-statistics/?profile=county-library-count-dgbas&entity=%E8%87%BA%E5%8D%97%E5%B8%82)，可切換縣市；保留官方改制後地域、國立館範圍與來源缺值，勿與其他來源補接或把總計及縣市列直接相加。
3. 從[正式Release](https://github.com/poplolioi11/tw-public-library-statistics/releases/latest)下載CSV、JSONL或SQLite，依[AI與分析指南](../AI_USAGE.md)取出符合研究問題的來源，保留`observation_id`、來源SHA及版本。沒有合格來源時呈現未解，不補零。

## 怎樣才記為使用案例

可透過[GitHub issue](https://github.com/poplolioi11/tw-public-library-statistics/issues/new)提供公開成果網址及以下必要資訊；也可以只提出問題或改善需求。請勿貼讀者個資、私人帳密或尚未公開的研究資料。

- 用於哪個問題，以及實際採用的資料版本、來源或欄位。
- 可核對的論文、報導、分析、教材或應用成果網址；沒有公開成果時，標為需求回饋，不稱公開採用案例。
- 有無額外篩選、換算或人工核對；本資料集的缺口如何影響結果。
- 是否同意在案例清單連結該成果；尚未取得同意時，不替對方寫推薦語或公開私人往來。

star／fork記錄平台互動，下載量記錄附件取用，issue記錄回饋；三者都不能直接等同研究採用、品質審定或機構背書。維護者自己的測試、機器流量及匿名取用也可能出現在流量或下載統計中。

## 引用與驗證層級

使用v0.9.1的[Zenodo版本DOI](https://doi.org/10.5281/zenodo.23788194)、[固定版本Release](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.9.1)及[CITATION.cff](../CITATION.cff)引用本整理資料，另標示實際使用的官方原表。本頁範例對應v0.9.1，Zenodo封存日為2026-10-30；若使用其他版本，改引用實際使用的固定版本。`releases/latest`只作下載入口，不用作固定版本的引用憑據。

截至2026-10-30，人工抽樣核讀與雙校均尚未完成，沒有人工讀值結果或人工錯誤率。掃描年鑑的369個來源格有OCR及AI原圖核讀紀錄，這不等於人工雙校。若需要較高等級覆核，先取得對應官方原件，固定SHA與頁表列欄，由兩位人工分別記讀值、再裁決差異；保存每個格位的完成狀態，未完成者不改標為人工已核。此流程是下一步建議，並非已完成驗證。

資料仍有歷年缺口，跨年及跨來源使用須讀[完整度](../COVERAGE.md)、[口徑說明](PHASE2.md)與[資料說明稿](DATA_PAPER_DRAFT.md)。
