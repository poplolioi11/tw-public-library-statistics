#!/usr/bin/env python3
"""Create a source-cell SQLite mirror; do not append these rows to canonical data."""
import hashlib,json,sqlite3
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def stable(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def clean(row):return {k:v for k,v in row.items() if k!='original_fields'}
def value(x):return stable(x) if isinstance(x,(dict,list,bool)) else x
def ident(x):return '"'+x.replace('"','""')+'"'
def write_if_changed(path,body):
 if path.exists() and path.read_bytes()==body:return False
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body);return True
def main():
 sources={'programme_rows':'ncl_2005_programmes','programme_quantities':'ncl_2005_programmes_long','local_original_cells':'phase1_local_sources_cells','local_statistical_cells':'phase1_local_sources_long'}
 db=ROOT/'derived/phase1_supplements.sqlite';tmp=db.with_suffix('.sqlite.tmp');tmp.unlink(missing_ok=True);con=sqlite3.connect(tmp);metadata=[]
 for table,name in sources.items():
  path=ROOT/'derived'/(name+'.jsonl')
  if not path.exists():raise FileNotFoundError('Reviewed source batch missing: '+name)
  rows=[clean(json.loads(x)) for x in path.read_text().splitlines()];fields=list(dict.fromkeys(k for r in rows for k in r));con.execute('CREATE TABLE '+ident(table)+' ('+','.join(ident(k)+' TEXT' for k in fields)+')')
  con.executemany('INSERT INTO '+ident(table)+' VALUES ('+','.join('?' for _ in fields)+')',[[value(r.get(k)) for k in fields] for r in rows])
  metadata.append({'table':table,'csv':'derived/'+name+'.csv','jsonl':str(path.relative_to(ROOT)),'records':len(rows),'private_producer_jsonl_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'normalization':'Source-cell or programme facts. Do not union with canonical observations or sum original-cell and statistical-cell tables.','omitted_fields':['original_fields'] if any('original_fields'in json.loads(x) for x in path.read_text().splitlines()) else []})
  if table=='local_statistical_cells':
   groups=defaultdict(list)
   for r in rows:groups[(r['source_id'],r['source_sheet'])].append(r)
   partitions=[]
   for (source,sheet),items in sorted(groups.items()):
    relative='derived/phase1_by_sheet/'+source+'/'+hashlib.sha256(sheet.encode()).hexdigest()[:16]+'.jsonl';p=ROOT/relative;body=''.join(stable(r)+'\n' for r in items).encode();write_if_changed(p,body)
    partitions.append({'source_id':source,'source_sheet':sheet,'path':relative,'records':len(items),'sha256':hashlib.sha256(body).hexdigest(),'period_status_counts':{s:sum(r['period_status']==s for r in items) for s in sorted({r['period_status'] for r in items})}})
   write_if_changed(ROOT/'docs/phase1-source-cell-partitions.json',(json.dumps({'schema_version':'1.0.0','parent_jsonl':'derived/phase1_local_sources_long.jsonl','records':len(rows),'partitions':partitions,'union_equals_parent':True,'note':'These are the same source-cell rows, not additional observations. Select by exact sheet name; do not infer period from the hash filename.'},ensure_ascii=False,indent=2)+'\n').encode())
 con.commit();con.close()
 if db.exists() and tmp.read_bytes()==db.read_bytes():tmp.unlink()
 else:tmp.replace(db)
 manifest={'schema_version':'1.0.0','dataset_version':(ROOT/'VERSION').read_text().strip(),'sqlite':'derived/phase1_supplements.sqlite','tables':metadata,'canonical_observations_unchanged':True,'period_policy':'Programme reference years are not annual data years. Sheet/header conflicts retain unknown formal period; raw candidates remain.','value_policy':'ODS display markers and typed zeros are separate. Unresolved display/typed conflicts are not silently zero or source missingness.','publication_policy':'Only statistical projection; full workbooks with unrelated contacts or unrelated heritage sheets are not redistributed.'}
 write_if_changed(ROOT/'docs/phase1-supplements.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
 write_if_changed(ROOT/'docs/phase1-supplements.md','''# 新增的完整來源格子資料

這層保留原表及工作表格子，不直接加入既有正式觀測，也不認證跨年可比。`phase1_local_sources_cells`是含表頭與結構空白的原格事實；`phase1_local_sources_long`是同一原件中選定統計格，不可兩表相加。

- 2005年表6／7：[計畫列CSV](../derived/ncl_2005_programmes.csv)、[數量格CSV](../derived/ncl_2005_programmes_long.csv)。119列計畫紀錄、123個原數量格；兩種不參與／留白狀態與兩個日期期間另存，不改0或年度量。原PDF不隨包散布，CSV內下載網址與PDF頁／表／列／欄可回到原件。
- 地方四附件：[統計格CSV](../derived/phase1_local_sources_long.csv)、[JSONL](../derived/phase1_local_sources_long.jsonl)，18,486格；[安全範圍原格CSV](../derived/phase1_local_sources_cells.csv)含33,705個表頭、數值及結構位置。114連江工作簿無關古蹟與個人聯絡背景不公開。
- [SQLite](../derived/phase1_supplements.sqlite)的四表與各CSV／JSONL內容相同；[機器清單](phase1-supplements.json)列出表名及範圍。
- AI或程式不必先讀完整大檔：[按來源及原工作表的分檔索引](phase1-source-cell-partitions.json)提供小型JSONL、來源工作表原名、格數與SHA。分檔聯集是同一批18,486格，不是額外數據。

## 使用前須讀的原件差異

花蓮兩份ODS各有72個月份與空白模板；模板不當觀測。sheet名與表頭的兩個月份矛盾仍保留兩說、正式期間未知。連江113附件本身未印年，只能看到目錄113年的對應，不冒稱附件已有確證資料年；114工作表明印年度另列。

5,098個來源顯示「-」而底層為0的格子，`value=null`及`source_display_typed_value_conflict_unresolved`只標示兩種原表示未解；底層0仍在`source_typed_numeric_value`／`source_stored_value_raw`，不能自動認為缺值或實測零。另一個原字串「-」另存`source_marker`。每格同時保留display、typed、原公式、樣式／number format與合併來源。

2005計畫不當全年營運：各館計畫窗與全國閱讀運動各項期間分開；原表人次合計與細項加總有差異時原值照留。館名、原標籤及已更正的擷取差異見獨立報告，不以常識修正來源館名或地理歸屬。

公開的是統計投影；原工作簿、PDF、無關聯絡欄與原頁全文不在包內。OGDL只適用逐來源已核的版本；其餘公開統計事實之原件全文權利仍未確認。來源忠實度／格式驗證不是官方填報正確性或人類雙校認證。
'''.encode())
 print(json.dumps({'source_tables':len(metadata),'rows':{x['table']:x['records'] for x in metadata},'sqlite_bytes':db.stat().st_size},ensure_ascii=False))
if __name__=='__main__':main()
