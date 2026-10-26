#!/usr/bin/env python3
"""Version-consistent selection documentation and the main visible source plot."""
import argparse,hashlib,html,json
from pathlib import Path
from build_phase2 import replace_if_changed
ROOT=Path(__file__).resolve().parents[1]
def save(root,name,value):replace_if_changed(root/name,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
def block(root,name,body):
 p=root/name;s=p.read_text();start='<!-- BEGIN phase3 -->';end='<!-- END phase3 -->';new=start+'\n'+body.strip()+'\n'+end
 if start in s:s=s[:s.index(start)]+new+s[s.index(end)+len(end):]
 else:s=s.rstrip()+'\n\n'+new+'\n'
 replace_if_changed(p,s.encode())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);args=ap.parse_args();root=args.root.resolve();version=(root/'VERSION').read_text().strip();summary=json.loads((root/'docs/phase3-summary.json').read_text());reader=json.loads((root/'docs/phase3-reader-summary.json').read_text());policy=json.loads((root/'docs/phase3-profiles.json').read_text());plot=json.loads((root/'docs/phase3-default-chart.json').read_text());p2reader=json.loads((root/'docs/phase2-reader-summary.json').read_text())
 if {summary['dataset_version'],reader['dataset_version'],plot['dataset_version'],p2reader['dataset_version']}!={version}:raise ValueError('Rebuild all readers for the current version before documentation')
 brief=f'''## 第三階段：依問題選來源，直接看折線圖

v{version}有{summary['registered_profiles']}個明確母體／用途的預設問題，完整路由{summary['counts']['record_routes']:,}筆既有量化紀錄，保留{summary['counts']['candidate_decisions']:,}筆候選決策與來源理由。這些是選源註記，不是新增館數或營運量，原統計值不變。

[直接看折線圖與選源](site/phase3.html#line-charts) · [全部原刊數列](site/phase2.html#line-charts) · [問題索引](docs/phase3-question-index.json) · [範圍與用法](docs/PHASE3.md) · [按問題／年度小檔](docs/phase3-partitions.json)

主入口直接顯示已核國圖原刊借閱折線。第二階段有{p2reader['charts']}組已核數列圖；第三階段有{reader['charts']}組問題內原數列圖與{reader['interval_queries']}個由同一Python選源器預算的區間結果。原報點可回官方來源，缺值、缺期與口徑切換不連線。

選定來源與跨年可比分開；selected可能仍是缺值或不可用。版次優先是維護者政策，其他版本照留。2012全22縣市核心原量表仍缺；已取得的少量分館／閱覽室原文分項照留，不冒充完整核心量。'''
 for name in ('README.md','COVERAGE.md'):block(root,name,brief)
 ai='''## 第三階段機器讀取契約

先讀docs/phase3-question-index.json，選profile，再依docs/phase3-partitions.json取小檔。全量CSV／JSONL／SQLite在derived/phase3/。record_routes每個P2 record_key恰一次；candidate_decisions主鍵為profile_id+record_key，具體採納、其他版本與拒用理由在此。queries是預設快照，series_edges列候選接續與drawable許可；四表不可union成原始營運量。

逐筆保留官方URL、原件SHA、locator、source_version_id、evidence。政策同時綁來源body及P2證據內容SHA；新版本或同ID定義改變須覆核。原PDF／工作簿／HTML、無關聯絡欄與私人路由仍不公開。公開格式驗收與原件覆核不同。

selected=true只代表選定來源決策。數值回答須同讀selection_status、point_value、point_unit、value_status、raw_value與facets。一般原缺漏為selected_source_missing；顯示/typed0衝突為selected_source_unusable，point_value均null但原狀態不改。原報0的zero_interpretation不能升為測量真零認證。

source_series_only可作單期原來源事實，不獲得跨年連線許可。只用drawable=true的edge；query.trend_summary明示是否單一連續原序列。年份位置齊、同值或selected=true，都不證明全段可連。year_counts分開原位置、有數值、缺漏與不可用；原位置不是數值完整率。

單一面板依用途先核定義／單位／期間，再選完整覆蓋所請區間的原刊與版次；原缺值不降排名，不偷換另一版有值。相同優先序仍歧義；pin source_id禁止fallback；無一面板覆期不跨版拼接。選較舊合格原刊不等於官方訂正較新版。

原行政區／官方重編、含不含國家圖書館、預算／決算、借閱／續借、存量／流量、總計／分項各自保留。不加總、不補值、不推估去重人數、不重編地理。未知欄位拒絕，缺path不等於null。

圖表座標及區間選源由Python產生，前端只篩既有點與核准線段。圖表區間可改選原刊；下方全量表仍是預設決策快照，表格顯示篩選不重算選版。新用途／source-id／facet條件用select_sources.py重播，保留requested_filters。自由文字須先對應已登錄問題與原欄；無預設範圍可用--lookup讀原Annotation，不自動變成新原量或認證趨勢。'''
 block(root,'AI_USAGE.md',ai);block(root,'llms.txt',f'第三階段v{version}：docs/phase3-question-index.json與docs/PHASE3.md為入口；小檔docs/phase3-partitions.json。scripts/select_sources.py --list / --profile ID / --lookup layer:ID。selected包含missing/unusable；只用drawable=true的edge，不反推2012核心原量。互動折線site/phase3.html#line-charts；完整原刊數列site/phase2.html#line-charts。')
 guide=f'''# 第三階段：有界預設選源與折線圖

資料版本v{version}；政策{policy['policy_version']}；來源審查基線v{policy['reviewed_dataset_version']}。本階段不新增／改寫原量。{summary['registered_profiles']}個登錄問題、{summary['counts']['record_routes']:,}筆原紀錄路由、{summary['counts']['candidate_decisions']:,}筆候選決策；{summary['counts']['series_edges']:,}個候選接續中{summary['drawable_edges']:,}個可畫線。這是紀錄／決策數，不是館數或額外營運量。

## 直接看圖與來源

[互動折線圖](../site/phase3.html#line-charts)預設顯示國圖原刊借閱面板，每點可回官方原件。可切換問題、原對象、原指標與期間。原值或原表明示單位倍數換算另標；缺期、缺值與口徑切換斷線。單期資料在原表保留，不捏造跨年折線。

[全部原刊數列](../site/phase2.html#line-charts)有{p2reader['charts']}組，不限舊版12示例；第三階段有{reader['charts']}組圖表及{reader['interval_queries']}個同源Python選源的區間結果。原刊有限對照仍不認證所有歷年方法／涵蓋率不變。

## 選用政策

問題包括主計改制後縣市／全國館數、國資圖2023原報與歷年公開圖表、國圖六種原刊回溯、縣市年度原量、新竹月值、臺中採購冊數、花蓮兩種分類、連江明示年度、特定計畫及主計歷史單版原報。[輕量問題索引](phase3-question-index.json)列原用途；[完整政策](phase3-profiles.json)保留來源與證據SHA。

原行政區、官方重編地域、母體與國立館範圍不默換。單期原報可用，跨年連線另驗。新版優先是維護者政策，不是官方勘誤；原版與其他候選照留。缺值是面板合法成分，不以數字大小／有無值排名。新來源或同ID的證據內容SHA變更必須覆核；相同優先序保持歧義。指定source-id後不換版。無單一面板覆蓋所請區間時不拼線。

## 重播查詢

~~~sh
python scripts/select_sources.py --list
python scripts/select_sources.py --profile national-ncl-book-loans-panel --start-year 2020 --end-year 2024
python scripts/select_sources.py --profile county-library-count-dgbas --entity 臺北市 --start-year 2010 --end-year 2025
python scripts/select_sources.py --profile historical-national-dgbas-source-facts --purpose trend --metric 圖書借閱人數 --start-year 2005 --end-year 2005
python scripts/select_sources.py --lookup canonical:obs-28edaf7217be5d3c0c4546
python scripts/select_sources.py --operation impute
~~~

--source-id固定版本；--facility及--facet 原欄路徑=原值精確篩選，不猜近義。缺欄不等於null。CSV／JSONL匯出candidate_decisions；整體選版與edge許可需讀JSON，不能只憑CSV補線。--output不覆寫既有匯出。

## 機器格式與更新

四表CSV／JSONL／SQLite逐欄一致。SQLite的record_routes、candidate_decisions、queries、series_edges為wide views；scalar是TEXT、結構欄JSON、缺值SQL NULL。內表字典編碼。按profile／年度小檔的聯集等於candidate_decisions；未知年另檔，不塞回目錄年。

selected=true可包含missing或unusable，須同讀point_value及原狀態。顯示/typed0衝突不叫一般缺漏，更不改0。year_counts分開原位置、數值、缺漏與不可用；trend_summary.single_continuous_series明列整段是否單一原序列。只連drawable=true的邊。

更新入口仍run_update.py。來源群／政策／程式指紋快取；未變不建置，失敗保留前版。公開包不含私人排程、憑證、無關聯絡欄或原件全文。

## 缺口與驗證

2012原文有少量分館／閱覽室分項，完整22縣市核心原量表仍未取得；不拿components、比率或人口乘算補成原量。全臺歷年仍未齊，未登錄範圍完整保留在原路由，缺口不表示官方沒公布。

[固定來源案例驗收](../research/phase3-engine-review.md)保留24例、CLI、缺值／0／分類roundtrip與拒用反例；格式與更新另由獨立validator檢查。[Gemini文字邊界檢視](../research/phase3-gemini-boundary-review.json)只讀提供的契約，未查網；擴大成測量真零、重寫原狀態或假設圖表皆近似值的推論未採納。數值、雜湊與座標均由Python實際執行，非官方背書或人類逐格雙校。
'''
 replace_if_changed(root/'docs/PHASE3.md',guide.encode())
 for name in ('README.md','AI_USAGE.md','COVERAGE.md','llms.txt','docs/PHASE2.md','docs/PHASE1.md'):
  p=root/name;s=p.read_text()
  for old in ('自動選擇預設分析口徑屬第三階段。','自動選預設來源屬第三階段。','自動選口徑屬第三階段。'):s=s.replace(old,'第三階段已提供有界預設選源，見docs/PHASE3.md。')
  replace_if_changed(p,s.encode())
 p=root/'README.md';s=p.read_text().replace('- [互動閱讀頁](site/index.html)：按來源、指標及年度查看紀錄與來源。','- [折線圖與依問題選源](site/phase3.html#line-charts)；[全部原刊數列](site/phase2.html#line-charts)；[逐筆原值閱覽](site/index.html)。');replace_if_changed(p,s.encode())
 package=json.loads((root/'datapackage.json').read_text());package['resources']=[x for x in package['resources'] if not x['name'].startswith('phase3-')];ids={x['name'] for x in package['resources']}
 for t in summary['tables']:
  for kind in ('csv','jsonl'):
   name='phase3-'+t['table']+'-'+kind
   if name not in ids:package['resources'].append({'name':name,'path':t[kind],'format':kind,'compression':'gzip' if t[kind].endswith('.gz') else None,'layer':'source_selection_annotations; not additional operational statistics','hash':'sha256:'+hashlib.sha256((root/t[kind]).read_bytes()).hexdigest()})
 if 'phase3-selection-sqlite' not in ids:package['resources'].append({'name':'phase3-selection-sqlite','path':'derived/phase3/selection.sqlite','format':'sqlite','layer':'source_selection_annotations','hash':'sha256:'+hashlib.sha256((root/'derived/phase3/selection.sqlite').read_bytes()).hexdigest()})
 save(root,'datapackage.json',package);channels=json.loads((root/'docs/publishing-channels.json').read_text());channels['version']=version
 for c in channels['channels']:
  if c['kind']=='public_release_latest':c['expected_tag']='v'+version
 for path in ('site/index.html','site/phase3.html'):
  if not any(c.get('path')==path for c in channels['channels']):channels['channels'].append({'kind':'portable_reader','path':path,'update_policy':'same current package; no external hosting assumed'})
 save(root,'docs/publishing-channels.json',channels)
 preview='<section class="panel phase3-preview"><h2>直接看折線圖</h2><p><strong>'+html.escape(plot['label'])+'</strong> · 資料版本v'+html.escape(version)+'</p>'+plot['svg']+'<p class="hint">同一已核原刊範圍；缺值、缺期與口徑邊界不連線。每個點可回官方來源。</p><p><a href="phase3.html#line-charts">切換問題、地區、指標與期間</a> · <a href="phase2.html#line-charts">全部已核原刊數列</a></p></section>'
 p=root/'site/index.html';s=p.read_text();start='<!-- BEGIN phase3-chart-preview -->';end='<!-- END phase3-chart-preview -->'
 if start not in s or end not in s:raise ValueError('Main template needs a source-qualified preview slot')
 replace_if_changed(p,(s[:s.index(start)]+start+preview+end+s[s.index(end)+len(end):]).encode());print(json.dumps({'phase3_documentation_version':version,'main_visible_chart_points':plot['plotted_points'],'main_visible_chart_lines':plot['drawable_segments']},ensure_ascii=False))
if __name__=='__main__':main()
