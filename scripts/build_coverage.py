#!/usr/bin/env python3
import csv,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
rows=[json.loads(x) for x in (R/'data/combined/observations.jsonl').read_text().splitlines()]
counties=['基隆市','臺北市','新北市','桃園市','新竹縣','新竹市','苗栗縣','臺中市','彰化縣','南投縣','雲林縣','嘉義縣','嘉義市','臺南市','高雄市','屏東縣','臺東縣','花蓮縣','宜蘭縣','澎湖縣','金門縣','連江縣']
index={}
for row in rows:
 if row['geography'] in counties:index.setdefault((row['data_year'],row['geography']),[]).append(row)
entries=[]
for year in range(1991,2027):
 for geo in counties:
  subset=index.get((year,geo),[]);has2023=any(r['source_id']=='ogdl-api-2023' for r in subset)
  status='complete_for_6425_explicit_2023_resource' if has2023 else (('source_null_cells_only_see_value_status' if all(r['value'] is None for r in subset) else 'partial_sources_obtained') if subset else 'not_obtained_or_not_yet_checked')
  entries.append({'data_year':year,'requested_county_current_name':geo,'status':status,'records':len(subset),'sources':'|'.join(sorted({r['source_id'] for r in subset})),'boundary_warning':'依現行名稱僅做缺口索引，未將早期臺北縣／桃園縣或合併前縣市重劃；不能拿此矩陣當同界線比較。','absence_meaning':'not_obtained_or_not_yet_checked不是無資料；不證明政府沒有公開。'})
with (R/'data/combined/coverage_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(entries[0]));w.writeheader();w.writerows(entries)
quality=json.loads((R/'derived/local_historical_quality.json').read_text());c=json.loads((R/'data/component_quality.json').read_text())
(R/'data/combined/quality_flags.json').write_text(json.dumps({'source_internal_issues':c['issues'],'local_arithmetic_checks':quality['hsinchu_arithmetic_checks'],'local_arithmetic_issues':quality['hsinchu_arithmetic_errors'],'historical_table_checks':['raw/ncl-historical/gap-tables-metadata.json','raw/ncl-earlier/metadata.json','raw/ncl-additional/extraction-validation.json'],'flagged_historical_cells':[{k:r.get(k) for k in ['observation_id','source_id','source_locator','quality_flags']} for r in rows if r.get('source_family')=='國家圖書館年鑑統計事實' and r.get('quality_flags') not in (None,'','[]')],'source_faithfulness_is_not_statistical_certification':True},ensure_ascii=False,indent=2)+'\n')
summary=json.loads((R/'data/combined/summary.json').read_text())
from collections import Counter
families=Counter(r['source_family'] for r in rows)
nulls=Counter(r['value_status'] for r in rows if r['value'] is None)
ncl=[r for r in rows if r['source_family']=='國家圖書館年鑑統計事實']
byyear=Counter(r['data_year'] for r in ncl)
text=f"""# 涵蓋範圍與完整度

資料版本：v{summary['version']}，查核日2026-10-25。**下列明確來源已整批整理；全臺各縣市所有歷年尚未齊全。** 全部{len(rows):,}格，包含{nulls.get('not_available_in_source',0):,}個來源明示缺值格、{nulls.get('source_blank',0):,}個原印留白格，以及不同出版版本。紀錄數不是圖書館間數。

| 來源族群 | 已取得的範圍 | 正式資料格 | 界線 |
|---|---|---:|---|
| 國資圖公開全國圖表 | 2011–2025，15年×10類公開圖表 | {families['國資圖公開全國圖表']:,} | 只有全國；不代表全縣市歷年 |
| 6425明確OGDL年度資源 | 2023，全國＋22縣市＋3替代口徑，86數值欄 | {families['國資圖2023開放資料（含縣市）']:,} | 替代列重疊；其他年度授權未核實 |
| 主計總處縣市館數 | 1998–2025×22縣市＋總計 | {families['主計總處縣市公共館數']:,} | 1998–2005為184格明示缺值；2006–2025有460格數值。官方改制後地域；母體包含國家圖書館 |
| 國圖年鑑 | 96–103卷已列核心表、統計章公共館子表 | {len(ncl):,} | 按表保存；102卷沒有本輪所查公共館章完整縣市核心表。不宣稱整冊入庫 |
| 主計總處年報 | 2005/2008/2011三版，資料年1991–2011 | {families['主計總處歷史全國統計']:,} | 保留重疊出版版本；4格原刊未提供 |
| 地方開放資料 | 臺中與新竹14目錄、35 JSON | {families['地方政府開放歷史表']:,} | 排除10,433個同值重複。新竹129個月份；月份存在不等於所有館填報齊全 |

國圖逐表完成清單與來源格數在 `raw/ncl-historical/gap-tables-metadata.json`、`raw/ncl-earlier/metadata.json`、`raw/ncl-additional/extraction-validation.json`；舊版指定表另見 `research/ncl-historical-validation.json`。各資料年格數（包含不同卷與不同表重疊的來源版本）：{dict(sorted(byyear.items()))}。

`data/combined/coverage.json` 按來源列出；`coverage_matrix.csv` 是資料年×現行22縣市的缺口索引。歷史臺北縣／桃園縣等未硬轉現行界線，因此不能以矩陣作同界線比較。`docs/source-backlog.json` 按來源批次分類，不會每次重新搜索所有機關。

## 尚未完成

- 尚未完成全臺各縣市所有年度、所有指標的同口徑資料。全國歷年子表和縣市單一館數不能冒充全面板。
- 國圖104卷以後及95卷以前等目錄已見版本仍待逐表查核。102卷本輪只完整收錄統計章的公共館群，不從敘述估算縣市值。
- 臺中、新竹以外地方統計未逐機關全盤核查；不能標成不存在或沒有公開。
- 1991以前、實際填報率與全部歷史定義版次仍待查。
- PDF經影像表頭／註腳與來源定位核對；2008–2010四張新增缺表另有1,180格獨立全表比對。其他新卷的製表與來源檢查範圍另列；沒有人工逐格雙校或官方認證。

## 原值與口徑

原表的零、留白、缺值符號分開保存，留白不推定不適用，零不逕認為真零。單位由上下文推得時保留 `unit_basis` 與推論標記。館數表有些年度另列國立分館，有些沒有；不補出原刊不存在的欄位。2006年未開放館、閱覽室及第二館保留各自原分類。

原刊內部合計差異保留原值，詳 `quality_flags.json`、逐表metadata及 `research/source-verification.md`。包括2010每人購書費27.72與正文／重算約22.72、2008借閱總計與分項差18,000、2009分館合計差異，以及2006人員分類加總差異。地方2,400組合計檢查中28組不一致。可追溯性不代表替官方填報作正確性保證。

特定閱讀空間改造、工程計畫成果與個案未納入；一般公共館營運統計中的面積、經費仍依原表口徑保存。完整署名章節、照片及PDF未隨公開包再散布。
"""
(R/'COVERAGE.md').write_text(text)
print('coverage entries',len(entries))
