# 第二階段：跨年口徑與來源證據

資料版本v0.9.1。完成的是現有資料的逐筆口徑檢視與有界比較規則；不是全臺歷年資料已齊，也未證明所有歷年填報方法一致。

## 完成範圍

76,854個量化紀錄全數綁定原件證據，三層為58,245正式觀測、18,486地方來源格及123計畫數量格。119個programme列視圖與33,705個含表頭原格是同來源的其他視圖，不能再相加。445張卡、28,119個口徑組；1677組有多個可對照期間，其中554組跨不同年度。計數是資料組，不是圖書館數或完整率。

原數值、原單位、原狀態、原年月、原地名與原來源SHA全部保留。新解讀另列comparison_unit/comparison_year、依據及狀態。14,584個已核冊數／人次原欄可另註單位；14,400個新竹原統計年月只接受有效五碼ROC年月；原欄年度另有三碼年份規則，不能把截斷年月當成年。

## 已核的實際差異

- 主計2005／2008版英文原註明確自2000年改為外借者；兩版依該斷點分段。2011版英文before1999和中文閱覽定義方向不一致，該版相關借閱／利用率保留未解。1998、1999分館納入另按該版註腳限制，不能憑同表全段放行。
- 國圖回溯表限定同表同指標，鄰表國家圖書館的館內調閱註腳不移植到公立公共館表；冊／件混合或未印單位仍不轉為純冊。
- 花蓮同一工作簿的欄頭／讀者類別grid改變時分組，讀者身分／館藏地／性別／總計不混併。5,098顯示符號而typed0、176年月矛盾保持未解。
- 連江113只在目錄對應年，原附件未印年；114同工作簿的年末／全年與借閱計數定義可引用，但不回填113。
- 計畫表是特定活動與期間。第5項日期跨2005–2006，第6項是2006年4–5月；其餘未知不能套成整年，也不把參加人數當全年獨立讀者。

以上以[國圖／主計證據](../research/phase2-ncl-evidence.md)、[地方證據](../research/phase2-local-evidence.md)、[逐卡JSONL](../derived/phase2/evidence_cards.jsonl)及[斷點規則](../derived/phase2/breakpoints.jsonl)回原件，不代替機關填報正確性保證。

## 讀取與查兩筆

開[互動頁](../site/phase2.html)，或讀[機器摘要](phase2-summary.json)與[年度索引](phase2-partitions.json)。全量逐筆註記CSV／JSONL以gzip無損傳輸；SQLite提供annotations、comparison_groups、evidence_cards、breakpoints等view／表。scalar欄為TEXT，結構欄為JSON；內表字典編碼避免重複長字串，讀view即可。

```sh
python scripts/compare_definitions.py --left canonical:obs-28edaf7217be5d3c0c4546 --right canonical:obs-7cf1a460cecd982fbf291f
python scripts/compare_definitions.py --lookup canonical:obs-28edaf7217be5d3c0c4546
python scripts/compare_definitions.py --operation impute
```

首例是同一原刊表208的2018／2019借閱人次，只及原刊範圍內的有限對照；不是跨來源或所有方法已認證。相同版本、標籤或數值都不足以證明其他觀測可接續。加總／推估／轉成去重人數等沒有供給已核規則的操作明確拒絕，第三階段已提供有界預設選源，見docs/PHASE3.md。

## 重現與更新

```sh
python scripts/build_phase2.py
python scripts/build_phase2_reader.py
python scripts/build_phase2_documentation.py
python scripts/validate_phase2.py
```

更新主入口仍為run_update.py。按原來源群、原件SHA、證據卡與規則程式作快取；未變來源的註記沿用，整體無變則不建置，失敗保留前版。原PDF／工作簿／HTML重播需還原已核原件，取得不同SHA必須先覆核。私有原件查讀、來源覆核與公開副本格式驗收分開，不宣稱只有投影也重讀了全部原件。現行定義參照不外推到所有舊年。

## 明確保留的限制

2012縣市核心原量仍缺，不從比率反算。來源清冊中的候選依各自完成狀態處理；本階段未窮盡所有候選。未知單位、原地理疑義、統計填報涵蓋率、現行標準的歷史採用日與未出版方法變更仍可能無法判定。原報0不等於認證實測0，來源表算術差異照留。這是AI／程式及獨立來源案例核對，非人類逐格雙校或官方背書。
