#!/usr/bin/env python3
"""Refresh bounded coverage documentation from the actual canonical records."""
import json,re
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def replace_between(text,start,end,body):
 a=text.index(start)+len(start);b=text.index(end,a)
 return text[:a]+'\n\n'+body.strip()+'\n\n'+text[b:]
def main():
 summary=json.loads((R/'data/combined/summary.json').read_text());version=summary['version'];count=summary['records'];nulls=summary['null_value_status_counts']
 rows=[json.loads(x) for x in (R/'data/combined/observations.jsonl').read_text().splitlines()]
 ncl=[r for r in rows if r['source_family']=='國家圖書館年鑑統計事實'];n=len(ncl)
 description=f"目前 **{count:,} 筆來源觀測紀錄**，含 **{nulls.get('not_available_in_source',0):,} 格明示缺值**、**{nulls.get('source_blank',0):,} 格原印留白**及不同出版版本。紀錄數不是圖書館間數，也不能整表相加。"
 p=R/'README.md';s=p.read_text();s=re.sub(r'版本 \*\*[^*]+\*\*',f'版本 **{version}**',s);s=re.sub(r'v[0-9.]+下載',f'v{version}下載',s);s=re.sub(r'/releases/tag/v[\d.]+',f'/releases/tag/v{version}',s)
 body=description+f'''

| 來源族群 | 已整理的範圍 | 紀錄數 |
|---|---|---:|
| 國資圖公開全國圖表 | 2011–2025 年公開全國圖表 | 855 |
| 國資圖 2023 開放資料 | 明確 OGDL；86數值欄×26地理／口徑列 | 2,236 |
| 國家圖書館年鑑 | 96–103卷所列核心表及公共館統計子表，含不同版本 | {n:,} |
| 主計總處歷史全國統計 | 3出版版本，資料年1991–2011 | 220 |
| 主計總處縣市館數 | 1998–2025年×23列，1998–2005為來源缺值 | 644 |
| 地方政府歷史表 | 新竹與臺中已確認系列，保留年／月原期間 | 14,751 |

國圖本次補齊2008–2010年四張缺表，並整批整理2006／2007／2011／2013年所列核心表，以及101–103卷統計章公共館子表。102卷已查公共館章沒有同樣的全縣市核心表，本輪只收實際找到的全國子表。原始留白、零、明示缺值、歷史舊縣市、國立館與替代範圍分開保存。逐表格數及完整性見 [COVERAGE.md](COVERAGE.md)。
'''
 s=replace_between(s,'## 目前收錄什麼','**完整性指',body)
 s=s.replace('`value=null` 是缺值。','`value=null` 須搭配 `value_status`：`source_blank` 是原刊留白，`not_available_in_source` 是明示缺值；兩者都不補零。')
 p.write_text(s)
 p=R/'AI_USAGE.md';s=p.read_text();s=re.sub(r'目前 [\d,]+ 筆[^\n]+',description.replace('**','')+'「所列來源全量」不等於所有縣市、所有年度或每間館完整。缺口不表示官方沒有公布。',s)
 s=s.replace('`ncl-yearbook-98-public`、`ncl-yearbook-99-public`、`ncl-yearbook-100-public`','以來源清單為準；`ncl-yearbook-*`、`ncl-gap-*`、`ncl-earlier-*` 各表／出版版本分開')
 s=re.sub(r"- `value_status = 'not_available_in_source'`／`value IS NULL`：[^\n]+",f"- `value IS NULL` 必須同讀 `value_status` 與 `raw_value`。本版 `{nulls.get('not_available_in_source',0)}` 格 `not_available_in_source` 保留明示缺值符號，`{nulls.get('source_blank',0)}` 格 `source_blank` 保留原刊留白；留白不推定不適用，均不補零。",s)
 s=re.sub(r'^- `value IS NULL` 必須同讀[^\n]+',f"- `value IS NULL` 必須同讀 `value_status` 與 `raw_value`。本版 `{nulls.get('not_available_in_source',0)}` 格 `not_available_in_source` 保留明示缺值符號，`{nulls.get('source_blank',0)}` 格 `source_blank` 保留原刊留白；留白不推定不適用，均不補零。",s,flags=re.M)
 s=s.replace('檢查 `source_edition`、','檢查 `source_edition`／`source_edition_roc`、`aggregation_role`、`institutional_level`、`unit_raw`／`unit_basis`／`unit_status`、')
 p.write_text(s)
 p=R/'llms.txt';s=p.read_text();s=re.sub(r'版本 [\d.]+；',f'版本 {version}；',s);s=re.sub(r'/releases/tag/v[\d.]+',f'/releases/tag/v{version}',s)
 s=re.sub(r'(?:19,975 筆是觀測／來源版本紀錄|目前 [\d,]+ 筆來源觀測紀錄)[^\n]+',description.replace('**','')+f' 國圖已列統計表{n:,}格；詳COVERAGE及逐表metadata，不宣稱全臺歷年皆完整。',s)
 s=s.replace('全包188缺值=原主計歷史表4格+新增184格。','該族群184明示缺值須與其他來源的缺值／留白分開。')
 s=s.replace('value=null／not_available_in_source 是缺值，不補零。','value=null 要看value_status；source_blank是原印留白，not_available_in_source是明示缺值，均不補零。')
 p.write_text(s)
 p=R/'CITATION.cff';s=p.read_text();s=re.sub(r'^version: .+$','version: '+version,s,flags=re.M);p.write_text(s)
 backlog=R/'docs/source-backlog.json';b=json.loads(backlog.read_text());b['scope_claims']=[x for x in b['scope_claims'] if not x.startswith(('NCL3年','NCL96–103卷'))]+['NCL96–103卷僅已列核心表與公共館子表；非整冊所有表，102卷縣市核心表缺口仍存。']
 b['constraints']=[x for x in b['constraints'] if not x.startswith('本清單未新下載')]
 for family in b['families']:
  if family['family_id']!='ncl_yearbook_public_library_chapters':continue
  groups={}
  for row in ncl:
   key=(row['source_id'],row.get('source_table'),row.get('source_pdf_page'))
   entry=groups.setdefault(key,{'source_id':row['source_id'],'source_table':row.get('source_table'),'pdf_page':row.get('source_pdf_page'),'printed_page':row.get('source_printed_page'),'data_years':set(),'source_cells':0})
   entry['data_years'].add(row['data_year']);entry['source_cells']+=1
  tables=[{**x,'data_years':sorted(x['data_years'])} for x in groups.values()]
  family['completed_scope']={'data_years':sorted({r['data_year'] for r in ncl}),'long_rows':n,'tables':tables,'completion_statement':'僅所列核心表或公共館子表完整，不是整冊／整章所有表。'}
  family['known_not_ingested']=[{'edition_roc':102,'data_year':2012,'scope':'本輪公共館章未發現相同完整縣市核心表；已收統計章全國子表，其他來源仍待查。'}]
  family['unknown_scope']=['95卷以前及104卷以後尚未逐表核對；其他卷統計章與地方補充表仍有缺口。','官方目錄可見不等於所有欄位或歷年可比性已確認。']
  family['evidence']+=['raw/ncl-historical/gap-tables-metadata.json','raw/ncl-earlier/metadata.json','raw/ncl-additional/extraction-validation.json']
  family['evidence']=list(dict.fromkeys(family['evidence']))
 for task in b['ordered_batches'] if 'ordered_batches' in b else b.get('backlog',[]):
  if task['task_id']=='B01':task.update(status='completed_bounded_scope',completion='四張既有缺表全量1180格：830數值、350留白；另經獨立全格回查。',known_not_ingested=[],unknowns=['三項原刊算術差異已記錄，未改官方值。'])
  if task['task_id']=='B03':task.update(status='partially_completed_known_tables',completion='本輪96/97卷8張核心表1686格；101/103卷14張核心表與101–103統計章公共館子表1707格。其他卷維持待查。')
  if task['task_id']=='B08':task['unknowns']=['歷年定義是否完全相容仍待逐年認證；實際表已取得。']
 for item in b['official_yearbook_inventory']['items']:
  ed=item.get('edition_roc_raw')
  if ed in range(96,104):item.update(data_year_verified=ed+1910,ingestion_status='specific_operational_tables_or_public_subset_completed_only',scope_evidence='逐表清單見raw/ncl-historical/gap-tables-metadata.json、raw/ncl-earlier/metadata.json、raw/ncl-additional/extraction-validation.json；102卷不宣稱縣市核心表齊全。')
 b['official_yearbook_inventory']['checked_via']='官方目錄盤點與本輪96–103卷指定章／表原件核對；其他卷僅目錄。'
 backlog.write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
 (R/'docs/source-backlog.md').write_text('# 來源分組待辦\n\n以 [source-backlog.json](source-backlog.json) 為機器可讀主檔；已完成只限列出的表，未查不代表無資料。\n\n本輪完成 B01 四張缺表；B03 已整批處理96/97/101/103卷所列核心表及101–103卷公共館統計子表。102卷未有本輪所查完整縣市核心表。其餘版本與地方來源仍依來源批次逐一處理；不重搜已驗證且未變動的歷史來源。\n')
 print('documentation',version,count,nulls)
if __name__=='__main__':main()
