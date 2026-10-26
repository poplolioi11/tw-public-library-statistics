#!/usr/bin/env python3
"""Version-consistent human and AI entry points for the definition audit."""
import json
from pathlib import Path
from build_phase2 import replace_if_changed
ROOT=Path(__file__).resolve().parents[1]
def save(name,obj):replace_if_changed(ROOT/name,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())
def block(name,body):
 p=ROOT/name;s=p.read_text();start='<!-- BEGIN phase2 -->';end='<!-- END phase2 -->';b=start+'\n'+body.strip()+'\n'+end
 if start in s:s=s[:s.index(start)]+b+s[s.index(end)+len(end):]
 else:s=s.rstrip()+'\n\n'+b+'\n'
 replace_if_changed(p,s.encode())
def main():
 s=json.loads((ROOT/'docs/phase2-summary.json').read_text());v=(ROOT/'VERSION').read_text().strip()
 if s['dataset_version']!=v:raise ValueError('Rebuild phase2 before documentation')
 brief=f'''## 第二階段：有來源依據的口徑檢視

v{v}逐筆檢視現有{s['total_quantitative_records']:,}個量化紀錄：37,887筆正式觀測、18,486個地方來源格、123個計畫數量格，三層分開，不相加成業務量。{s['source_definition_cards']}張來源證據卡及{s['breakpoint_rules']}項斷點／欄位規則可回官方原件、SHA與原表位置。

- 原刊／原件範圍內有{s['groups_with_multiple_eligible_periods']:,}組支援多個期間的有限對照，其中{s['groups_with_multiple_eligible_years']:,}組涉及不同年度；不是同方法、全歷年或跨來源面板認證。
- {s['literal_unit_suffix_upgrades']:,}筆原null單位可依已核原欄「冊數／人次」另附單位解讀；{s['strict_literal_month_code_records']:,}筆五碼原年月嚴格解碼。原值、原unit與原data_year保持不變。
- 未解的定義、生效年、單位、地理及期間留在理由欄。相同標籤、數字相同、同一表或當代標準公布年，均不直接證明歷年方法相同。2012原量缺口不推算。

[口徑與來源互動頁](site/phase2.html) · [第二階段說明](docs/PHASE2.md) · [逐筆JSONL（gzip）](derived/phase2/annotations.jsonl.gz) · [逐筆CSV（gzip）](derived/phase2/annotations.csv.gz) · [SQLite](derived/phase2/definitions.sqlite) · [按層／年度小檔](docs/phase2-partitions.json)
'''
 block('README.md',brief);block('COVERAGE.md',brief)
 ai='''## 第二階段讀取契約

先讀`docs/phase2-summary.json`、`docs/phase2-statuses.json`及`docs/PHASE2.md`。原數值仍在原有三層，`derived/phase2/annotations.*`是其口徑註記，使用`layer + observation_id`連接，不能union成額外統計量。每筆有原URL/SHA/locator/source_version_id、原值/原狀態、單位及年月的依據、evidence_id與拒用理由。

`published_panel_limited`僅支援相同已核原刊／原件面板、原對象、原分類、指標、單位與有效期間分段。`source_series_only`只是相同來源標籤，不能當跨年認證；`unresolved`保留尚缺證據。群組數／紀錄數不是圖書館家數。不同原件grid signature不併成同一群，原地理名稱不重新對位。

`comparison_value`是原值或原表明示千單位的精確十進位倍數換算，仍需同讀comparison_status/reasons；有數字不代表可比較。未知unit不正規化，冊／種／件不互換。原顯示與typed0衝突仍是null；catalog-only與年月矛盾的正式comparison_year仍未知。原報0另有zero_interpretation，不能自行稱實測真零。預算／決算、續借／借閱、人次／去重人數、私立／公立、總計／分項不能默併。

原刊已明說的斷點只用於那一版／欄／年份。DGBAS不同版本有分館納入及借閱／閱覽定義的註釋，中英方向衝突時保留unresolved，不訂正官方數值。現行NLPI/CNS定義是分開的參照，未把公布或抓取日當歷史採用日。

程式比較兩筆使用`scripts/compare_definitions.py --left layer:ID --right layer:ID`。結果只回答同一原對象能否接續成指定原刊時間序列；不是自動選來源、合計、填補或因果分析。`--operation sum/impute/infer-unique-people/recode-geography/coerce-zero/cross-source-splice`會明確拒絕沒有已驗證規則的操作。SQL用唯讀`annotations`與`comparison_groups` view，內表採字典編碼；SQL scalar值為文字、結構欄為JSON，分析者須依欄定義解析，不能讓失敗轉型變0。

完整三格式傳輸可用gzip；小檔在`docs/phase2-partitions.json`，未解年度分檔不塞回候選年份。官方原件全文仍未隨公開包散布，來源覆核與公版格式驗收是不同範圍。自動選擇預設分析口徑屬第三階段。'''
 block('AI_USAGE.md',ai);block('llms.txt',f'第二階段 v{v}：docs/phase2-summary.json與docs/phase2-statuses.json為入口；derived/phase2/annotations.csv.gz、annotations.jsonl.gz及definitions.sqlite是口徑註記，不是新增營運量。按年度小檔：docs/phase2-partitions.json。比較工具scripts/compare_definitions.py；source_series_only/unresolved不准默接，published_panel_limited只限原刊面板，所有原值不變。')
 statuses={'schema_version':'1.0.0','dataset_version':v,'row_statuses':{'published_panel_limited':'有來源證據的同原刊／原件面板有限對照；不保證歷年收集方法或涵蓋率不變。','source_series_only':'只確認同來源標籤系列，歷年定義或相容性未證實。','unresolved':'必要原單位、期間、地域、欄位定義、生效年或值狀態有未解條件。'},'pair_statuses':{'published_panel_limited':'兩筆同已核原面板、指標、單位、對象、分類與有效期間分段；只及這個比較目標。','incompatible':'有已知維度差異，或所請操作沒有已驗證的安全處理規則，拒絕自動串接／運算。','unresolved':'來源／版次／歷史定義或必要條件缺少同等性證據。'},'comparison_goal':'same_original_entity_time_series','no_global_compatible_status':True,'no_automatic_sums_or_source_selection':True}
 save('docs/phase2-statuses.json',statuses)
 guide=f'''# 第二階段：跨年口徑與來源證據

資料版本v{v}。完成的是現有資料的逐筆口徑檢視與有界比較規則；不是全臺歷年資料已齊，也未證明所有歷年填報方法一致。

## 完成範圍

{s['total_quantitative_records']:,}個量化紀錄全數綁定原件證據，三層為37,887正式觀測、18,486地方來源格及123計畫數量格。119個programme列視圖與33,705個含表頭原格是同來源的其他視圖，不能再相加。{s['source_definition_cards']}張卡、{s['comparison_groups']:,}個口徑組；{s['groups_with_multiple_eligible_periods']}組有多個可對照期間，其中{s['groups_with_multiple_eligible_years']}組跨不同年度。計數是資料組，不是圖書館數或完整率。

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

首例是同一原刊表208的2018／2019借閱人次，只及原刊範圍內的有限對照；不是跨來源或所有方法已認證。相同版本、標籤或數值都不足以證明其他觀測可接續。加總／推估／轉成去重人數等沒有供給已核規則的操作明確拒絕，自動選預設來源屬第三階段。

## 重現與更新

```sh
python scripts/build_phase2.py
python scripts/build_phase2_reader.py
python scripts/build_phase2_documentation.py
python scripts/validate_phase2.py
```

更新主入口仍為run_update.py。按原來源群、原件SHA、證據卡與規則程式作快取；未變來源的註記沿用，整體無變則不建置，失敗保留前版。原PDF／工作簿／HTML重播需還原已核原件，取得不同SHA必須先覆核。私有原件查讀、來源覆核與公開副本格式驗收分開，不宣稱只有投影也重讀了全部原件。現行定義參照不外推到所有舊年。

## 明確保留的限制

2012縣市核心原量仍缺，不從比率反算。437候選來源仍待完整處理；本階段沒有把所有候選入庫。未知單位、原地理疑義、統計填報涵蓋率、現行標準的歷史採用日與未出版方法變更仍可能無法判定。原報0不等於認證實測0，來源表算術差異照留。這是AI／程式及獨立來源案例核對，非人類逐格雙校或官方背書。
'''
 replace_if_changed(ROOT/'docs/PHASE2.md',guide.encode())
 for name in ('README.md','AI_USAGE.md','COVERAGE.md','llms.txt'):
  p=ROOT/name;t=p.read_text();t=t.replace('跨年相容性認證及自動選口徑屬後續階段；本階段保留差異而不自動決定可比。','第二階段已另附逐筆口徑與原刊有限對照規則；完整歷史方法認證仍未成立，自動選口徑屬第三階段。');replace_if_changed(p,t.encode())
 package=json.loads((ROOT/'datapackage.json').read_text());existing={r['name'] for r in package['resources']}
 for name,format_,compression in (('annotations.csv.gz','csv','gzip'),('annotations.jsonl.gz','jsonl','gzip'),('definitions.sqlite','sqlite',None),('groups.jsonl','jsonl',None),('evidence_cards.jsonl','jsonl',None),('breakpoints.jsonl','jsonl',None)):
  key='phase2-'+name
  if key not in existing:package['resources'].append({'name':key,'path':'derived/phase2/'+name,'format':format_,'compression':compression,'layer':'definition_annotations; join by layer+observation_id, never union as new quantities'})
 save('datapackage.json',package)
 channels=json.loads((ROOT/'docs/publishing-channels.json').read_text());channels['version']=v
 for c in channels['channels']:
  if c['kind']=='public_release_latest':c['expected_tag']='v'+v
 if not any(c.get('path')=='site/phase2.html' for c in channels['channels']):channels['channels'].append({'kind':'portable_reader','path':'site/phase2.html','update_policy':'same version as the package; no external hosting assumed'})
 save('docs/publishing-channels.json',channels)
 print('phase2 documentation',v)
if __name__=='__main__':main()
