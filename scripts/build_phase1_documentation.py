#!/usr/bin/env python3
"""Maintain phase-one scope, layer entry points and machine dictionaries."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text())
def save(path,obj):
 p=ROOT/path;body=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
 if not p.exists() or p.read_bytes()!=body:p.write_bytes(body)
def block(path,body):
 p=ROOT/path;s=p.read_text();start='<!-- BEGIN phase1 -->';end='<!-- END phase1 -->';v=start+'\n'+body.strip()+'\n'+end
 if start in s:s=s[:s.index(start)]+v+s[s.index(end)+len(end):]
 else:s=s.rstrip()+'\n\n'+v+'\n'
 p.write_text(s)
def main():
 if not (ROOT/'docs/phase1-summary.json').exists():return
 s=read('docs/phase1-summary.json');version=(ROOT/'VERSION').read_text().strip()
 text=f'''## 第一階段：全臺來源與缺口清冊

第一階段完成的是2005–2025年的來源導航、原口徑清冊及已取得來源批次；不宣稱全臺歷年值皆已齊全。

- 現行22縣市×4個機關角色，共{s['authority_slots_with_recorded_attempt']}項有實際查核紀錄；不是每個機關檔案庫都已窮盡。{s['source_candidates_listed']}個候選項分開標示入口、下載失敗、尚待解析及已完成的附件。
- {s['discovery_matrix_cells']:,}格「年×導航地區×主題」呈現來源出現情形；{s['raw_source_profiles']:,}組原口徑精確保留既有37,887筆觀測，不合併不同原地區、母體、單位、期間或版本。
- 新增2005計畫表6／7整批119列／123個數量格，以及花蓮、連江4附件的18,486個統計格。另有33,705個安全範圍原格含表頭及結構空白；這些是不同視圖，不可相加，也未混入既有正式觀測。
- 花蓮兩份ODS各保留72個月工作表（2020年9月至2026年8月）及空白模板；176格年月矛盾留未知。連江113年目錄附件未印年份，與工作表明印114年的來源分開。

[來源與缺口互動頁](site/phase1.html) · [範圍與驗收](docs/PHASE1.md) · [新增來源資料](docs/phase1-supplements.md) · [小型工作表分檔](docs/phase1-source-cell-partitions.json) · [機器字典](docs/phase1-data-dictionary.json)

2012縣市核心原量仍未取得，不由比率反算。跨年相容性認證及自動選口徑屬後續階段；本階段保留差異而不自動決定可比。'''
 block('README.md',text)
 block('COVERAGE.md',text.replace('(site/','(site/').replace('## 第一階段：','## 第一階段覆蓋：'))
 p=ROOT/'COVERAGE.md';v=p.read_text().replace('臺中、新竹以外地方來源未逐機關全盤核查','本階段已做22縣市各4個角色的有界入口查核；其他歷年附件仍未逐件處理')
 p.write_text(v)
 ai='''## 第一階段的新資料層

先讀`docs/phase1-summary.json`、`docs/phase1-source-inventory.json`及`docs/phase1-data-dictionary.json`。`derived/phase1_authority_checks`是88項來源查核；`phase1_source_candidates`是候選項，不能當觀測。`phase1_discovery_matrix`是來源出現索引，原量和比率分開，月值不當全年，現行地名不改寫舊縣市。`phase1_raw_source_profiles`精確分組既有正式觀測及其ID，不認證跨年可比。

`docs/phase1-supplements.json`列新來源層CSV、JSONL和SQLite四表。programme_rows與programme_quantities是同一來源的列／數量視圖；data_year為null，不拿計畫參照年當全年統計。local_original_cells與local_statistical_cells同樣不可相加；按來源／原工作表的小分檔在`docs/phase1-source-cell-partitions.json`，分檔聯集等於後一表。

來源格使用`value_raw`、`source_display_raw`、`source_stored_value_raw`、`source_typed_numeric_value`。5,098格顯示「-」而typed為0，value=null和source_display_typed_value_conflict_unresolved表示兩種來源表示未解，不能擅改0或一般缺值。原公式只保留原字及快取，不宣稱重新計算。176格sheet/header年月矛盾保持period_year/month=null；catalog_title_year_only_attachment_undated也不是原表已確證年份。未解單位、總計重疊、原分類及來源註解均須同讀。

重建新來源層前，以`python scripts/restore_originals.py --phase1-only`只還原四個已覆核工作簿；`--include-phase1`則連同舊來源還原。可用`--source-root`指定本機研究原件位置。腳本依已記錄SHA驗證，既有不同版本不覆寫，新版須先覆核。

候選不等於完成，查頁沒看到不等於官方無資料。每個結果附來源URL、原件SHA、原表／工作表／儲存格定位及資料版本。新來源格尚未接入canonical observations，不能自行union。'''
 block('AI_USAGE.md',ai)
 p=ROOT/'AI_USAGE.md';p.write_text(p.read_text().replace('表6特定計畫與表7跨年活動是已知來源待辦，不是找不到。','表6特定計畫與表7跨年活動已完整另存programme來源層，未當成年度核心量。'))
 block('llms.txt','第一階段版本 '+version+'：先讀docs/phase1-summary.json與docs/phase1-data-dictionary.json。來源角色、候選與年主題索引不是營運觀測；來源格新層和canonical保持分開。按工作表小量讀取：docs/phase1-source-cell-partitions.json。未知不補值，2012原量缺口保留，跨年可比尚未認證。')
 b=read('docs/source-backlog.json');tasks=b.get('ordered_batches',b.get('backlog',[]))
 for t in tasks:
  if t.get('task_id')=='B06':t.update(status='source_role_inventory_completed_candidate_ingestion_pending',completion='22縣市各4個角色共88次有界入口查核完成；440候選列明，只有明確完成附件計入source-cell層。',evidence=['docs/PHASE1.md','docs/phase1-source-inventory.json'],unknowns=['不是機關全部歷年檔案庫窮盡；候選附件仍需逐批查核。'])
 for f in b['families']:
  if f.get('family_id')=='ncl_yearbook_public_library_chapters':
   pending=[]
   for item in f.get('known_not_ingested',[]):
    if item.get('cohort')=='ncl_2005':
     item.update(scope='表6／7已完整另存programme層；不屬canonical年度核心表。',status='completed_in_separate_programme_layer',evidence='docs/phase1-supplements.json');f['completed_other_layer']=[item]
    else:pending.append(item)
   f['known_not_ingested']=pending
 b['phase1_inventory']={'version':version,'scope':'22 current counties x4 roles; bounded source-entry survey, not exhaustive all-history ingestion','authority_slots':88,'candidates':s['source_candidates_listed'],'summary':'docs/phase1-summary.json','supplements':'docs/phase1-supplements.json','cross_year_comparability_certified':False}
 save('docs/source-backlog.json',b)
 block('docs/source-backlog.md','第一階段已完成22縣市×4角色的來源入口盤點。候選與附件處理進度見[清冊](phase1-source-inventory.json)；已完成來源格見[新增資料層](phase1-supplements.json)。後續按已定位附件逐批補齊，不把未解析或連線失敗當成官方無資料。')
 package=read('datapackage.json');names={x['name'] for x in package['resources']}
 for name in ('phase1_authority_checks','phase1_source_candidates','phase1_raw_source_profiles','phase1_discovery_matrix','ncl_2005_programmes','ncl_2005_programmes_long','phase1_local_sources_cells','phase1_local_sources_long'):
  for ext in ('csv','jsonl'):
   path='derived/'+name+'.'+ext;key=name+'-'+ext
   if key not in names:package['resources'].append({'name':key,'path':path,'format':ext,'hash':'sha256:'+hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'layer':'source_inventory' if name.startswith(('phase1_authority','phase1_source_candidates','phase1_raw_source','phase1_discovery')) else 'source_cells_separate_from_canonical'})
 for name in ('phase1_inventory','phase1_supplements'):
  if name not in names:package['resources'].append({'name':name,'path':'derived/'+name+'.sqlite','format':'sqlite','layer':'separate_from_canonical'})
 save('datapackage.json',package)
 dictionary={'schema_version':'1.0.0','dataset_version':version,'type_policy':'Observed JSON types below describe this version, not certified statistical meaning. SQLite stores structured values as JSON text; CSV null is empty.','layers':[]}
 for path in ('derived/phase1_authority_checks.jsonl','derived/phase1_source_candidates.jsonl','derived/phase1_raw_source_profiles.jsonl','derived/phase1_discovery_matrix.jsonl','derived/ncl_2005_programmes.jsonl','derived/ncl_2005_programmes_long.jsonl','derived/phase1_local_sources_cells.jsonl','derived/phase1_local_sources_long.jsonl'):
  rows=[json.loads(x) for x in (ROOT/path).read_text().splitlines()];types={};present={}
  for row in rows:
   for k,v in row.items():
    if k=='original_fields':continue
    typ='null' if v is None else 'boolean' if isinstance(v,bool) else 'integer' if isinstance(v,int) else 'number' if isinstance(v,float) else 'string' if isinstance(v,str) else 'array' if isinstance(v,list) else 'object'
    types.setdefault(k,set()).add(typ);present[k]=present.get(k,0)+1
  dictionary['layers'].append({'jsonl':path,'records':len(rows),'fields':{k:{'observed_json_types':sorted(v),'present_in_all_records':present[k]==len(rows)} for k,v in types.items()},'semantic_rules':'AI_USAGE.md and docs/phase1-supplements.md; preserve source identity, scope, periods and unresolved statuses.'})
 save('docs/phase1-data-dictionary.json',dictionary)
 candidates=[json.loads(x) for x in (ROOT/'derived/phase1_source_candidates.jsonl').read_text().splitlines()]
 queue=[]
 for c in candidates:
  if c.get('ingestion_status')=='source_cell_batch_verified_not_harmonised':continue
  queue.append({'candidate_id':c['candidate_id'],'county':c['county'],'title':c.get('title'),'catalog_url':c.get('catalog_url'),'download_url':c.get('source_download_url'),'discovery_status':c.get('ingestion_status'),'rights_status':c.get('license_status',c.get('rights_status')),'next_action':'Review exact listed original resource and all related statistical tables/sheets; no guessed values or automatic publication. Preserve all same-year resource versions.','selection_key':'Known resource URL first, then county/candidate ID; a filename year remains a hint until the original is reviewed.'})
 queue.sort(key=lambda c:(not bool(c['download_url']),c['county'],c['candidate_id']))
 save('docs/phase1-next-batches.json',{'schema_version':'1.0.0','dataset_version':version,'candidates':queue,'normal_run_does_not_crawl_this_queue':True,'batch_policy':'Work on one complete bounded source batch. This is a review queue, not a declaration that every listed attachment belongs to operational library statistics or has redistribution rights.'})
 print('phase1 documentation',version)
if __name__=='__main__':main()
