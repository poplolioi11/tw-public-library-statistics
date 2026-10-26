#!/usr/bin/env python3
"""Read-only source-version evidence audit for released local and programme layers.

No acquisition, value repair, canonical annotation or publication. Only this
script's research report is written. ZIP/XML cells are read independently of
the workbook producer; literal JSON units/ROC-month codes remain qualified
source facts, not certification of unchanged historic reporting definitions.
"""
from __future__ import annotations
import argparse,collections,csv,datetime,gzip,hashlib,json,os,re,sys,zipfile
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
T='{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
O='{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
X='{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
S='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
P='{http://schemas.openxmlformats.org/package/2006/relationships}'
CONTACT_KEYS={'電子郵件','行動電話','市話','郵遞區號','機關代碼','email','phone','telephone'}
PROTECTED=['derived/local_historical_long.csv','derived/phase1_local_sources_cells.jsonl','derived/phase1_local_sources_long.jsonl','derived/ncl_2005_programmes.jsonl','derived/ncl_2005_programmes_long.jsonl','data/combined/observations.jsonl']

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def jread(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def readjsonl(p):
 with (gzip.open(p,'rt',encoding='utf-8') if p.suffix=='.gz' else p.open(encoding='utf-8')) as f:return [json.loads(x) for x in f if x.strip()]
def path_for(root,name):
 p=root/name
 return p if p.exists() else p.with_suffix(p.suffix+'.gz')
def csvrows(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def jp(k):return k.replace('~','~0').replace('/','~1')
def stable_write(p,obj):
 b=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(obj,str) else obj.encode()
 if p.exists() and p.read_bytes()==b:return
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_bytes(b);tmp.replace(p)
def literal_month(raw):
 if not isinstance(raw,str) or not re.fullmatch(r'[0-9]{5}',raw):return None
 roc=int(raw[:3]);month=int(raw[3:])
 if roc<1 or not 1<=month<=12:return None
 return {'year':roc+1911,'month':month,'resolution':'month','basis':'literal_period_code:統計年月; exactly5ASCII digits and month01–12','raw':raw}
def literal_unit(field):
 if field.endswith('冊數'):return '冊'
 if field.endswith('人次'):return '人次'
 return None
def col(n):
 s=''
 while n:n,r=divmod(n-1,26);s=chr(65+r)+s
 return s
def coord(r,c):return col(c)+str(r)
def uncoord(s):
 m=re.fullmatch(r'([A-Z]+)([0-9]+)',s);n=0
 for x in m[1]:n=26*n+ord(x)-64
 return int(m[2]),n
def odf_text(cell):
 def text(e):
  if e.tag==X+'s':return ' '*int(e.get(X+'c','1'))
  if e.tag==X+'tab':return '\t'
  if e.tag==X+'line-break':return '\n'
  return (e.text or '')+''.join(text(c)+(c.tail or '') for c in e)
 return '\n'.join(text(p) for p in cell.findall(X+'p'))
def original_cells(path,wanted):
 """Read only requested original cells, bounding ODS repeated empty regions."""
 result={}
 with zipfile.ZipFile(path) as z:
  if path.suffix.lower()=='.ods':
   root=E.fromstring(z.read('content.xml'))
   for table in root.findall('.//'+T+'table'):
    name=table.get(T+'name');want=wanted.get(name,set())
    if not want:continue
    maxr=max(r for r,c in want);maxc=max(c for r,c in want);cells={};rr=1
    for row in table.findall(T+'table-row'):
     repeat=int(row.get(T+'number-rows-repeated','1'));cc=1
     if rr>maxr:break
     for c in row:
      if c.tag not in {T+'table-cell',T+'covered-table-cell'}:continue
      nc=int(c.get(T+'number-columns-repeated','1'))
      if cc<=maxc:
       stored=next((c.get(O+k) for k in ['value','date-value','boolean-value','string-value'] if c.get(O+k) is not None),None)
       obj={'display':odf_text(c),'stored':stored,'native':c.get(O+'value-type'),'formula':c.get(T+'formula')}
       for ri in range(rr,min(rr+repeat,maxr+1)):
        for ci in range(cc,min(cc+nc,maxc+1)):
         if (ri,ci) in want:cells[ri,ci]=obj
      cc+=nc
     rr+=repeat
    result[name]=cells
  else:
   strings=[]
   if 'xl/sharedStrings.xml' in z.namelist():strings=[''.join(si.itertext()) for si in E.fromstring(z.read('xl/sharedStrings.xml')).findall(S+'si')]
   rels={e.get('Id'):e.get('Target') for e in E.fromstring(z.read('xl/_rels/workbook.xml.rels')).findall(P+'Relationship')}
   for sheet in E.fromstring(z.read('xl/workbook.xml')).findall(S+'sheets/'+S+'sheet'):
    name=sheet.get('name');want=wanted.get(name,set())
    if not want:continue
    target=rels[sheet.get(R+'id')];part=target.lstrip('/') if target.startswith('/') else 'xl/'+target;cells={}
    for c in E.fromstring(z.read(part)).findall(S+'sheetData/'+S+'row/'+S+'c'):
     rc=uncoord(c.get('r'))
     if rc not in want:continue
     native=c.get('t','n');v=c.find(S+'v');stored=v.text if v is not None else None;display=''
     if native=='s' and stored is not None:stored=display=strings[int(stored)]
     elif native=='inlineStr':stored=display=''.join(c.find(S+'is').itertext())
     elif native in {'str','e','b'}:display=stored or ''
     formula=c.find(S+'f');cells[rc]={'display':display,'stored':stored,'native':native,'formula':formula.text if formula is not None else None}
    result[name]=cells
 return result

def get(cells,sheet,cell):
 d=cells.get(sheet,{}).get(uncoord(cell),{})
 return d.get('display') or d.get('stored') or ''
def dimension_facts():
 return {'national_library_scope':'unknown_not_merged_with_national_series','geography_vintage':'source labels retained; no county-code or historical-boundary recoding','institutional_level':'source institutional/location category only','source_edition':'exact source_sha256, never acquisition date as data period'}

def audit_json(root,canonical):
 metadata=jread(root/'derived/local_historical_metadata.json');cards=[];source_lookup={};literal_promotions=collections.Counter();period_counts=collections.Counter();arithmetic=[];checked_raw=0
 for doc in metadata['documents']:
  p=root/doc['raw_path'];assert sha(p)==doc['source_sha256'],doc['raw_path'];rows=jread(p);assert isinstance(rows,list)
  source_id='local-'+p.name.split('-')[1];source_lookup[doc['source_sha256']]={'doc':doc,'rows':rows,'source_id':source_id};checked_raw+=len(rows)
  retained=[x for x in canonical if x['source_sha256']==doc['source_sha256'] and x['source_id']==source_id]
  fields=sorted({k for r in rows for k in r if k not in CONTACT_KEYS})
  hsinchu=all('統計年月' in r and '館藏地' in r for r in rows)
  field_rules=[];months=[];raw_years=[];unresolved=['未取得各歷年填報規則生效日；同名欄不證明各年調查完整性或統計方法不變。']
  if hsinchu:
   metrics=[k for k in fields if k not in {'統計年月','館藏地'}];periods=[literal_month(r.get('統計年月')) for r in rows]
   assert all(periods),'Invalid original統計年月 code';months=sorted({x['raw'] for x in periods});raw_years=sorted({x['year'] for x in periods})
   assert len({tuple(sorted(r)) for r in rows})==1,'Headers change within JSON source'
   for field in metrics:
    unit=literal_unit(field);assert unit is not None,field
    field_rules.append({'source_field':field,'normalized_unit':unit,'unit_evidence_basis':'literal_field_suffix','unit_evidence_locator':'/0/'+jp(field),'printed_metric_raw':field,'measure':field,'unique_people':False if unit=='人次' else None,'collection_type':'圖書借閱作業量；是否含非書未明示','stock_flow_ratio_financial':'transaction_flow','comparison_status':'published_panel_limited','comparison_scope':'same exact source_sha256, source_field and館藏地 label; literal monthly periods only','not_interchangeable_with':['借閱人次','續借人次','借閱及續借人次'] if unit=='人次' else ['借閱冊數','續借冊數','借閱及續借冊數']})
   for i,r in enumerate(rows):
    for unit in ['人次','冊數']:
     a=Decimal(str(r['借閱'+unit]).replace(',',''));b=Decimal(str(r['續借'+unit]).replace(',',''));total=Decimal(str(r['借閱及續借'+unit]).replace(',',''))
     if a+b!=total:arithmetic.append({'source_id':source_id,'source_sha256':doc['source_sha256'],'source_locator':'/'+str(i),'period_raw':r['統計年月'],'location_raw':r['館藏地'],'measure':unit,'source_components_sum':str(a+b),'printed_combined_value':str(total),'policy':'retain every original value; arithmetic test is not definition evidence'})
   facts={**dimension_facts(),'measure':'12 separate named circulation actions; borrow, renew and borrow+renew are distinct','unit':'6冊數 fields→冊;6人次 fields→人次, from exact original field suffix only','period_resolution':'literal monthly ROC5 code; not exact event dates and no annual synthesis','population':'館藏地 categories, not proven distinct physical facilities or unique people','aggregation_role':'no universal total role assigned to the entire JSON array','age_sex_reader_classification':'not present; do not infer demographics','month_coverage':months,'locations_raw':sorted({r['館藏地'] for r in rows})}
   status='published_panel_limited';scope='Only this one original JSON multi-period grid, same exact field and館藏地; no certification across files, reporting-rule revisions or changed location labels.'
   unresolved+=['館藏地不是可直接計數的設施唯一識別；未取得分類異動生效表。','人次是原欄字義，不能作跨期去重人數；合計作業量不能替代單一借閱量。','ROC5解碼只適用統計年月欄；其他欄或破碼不得套用。']
  else:
   for r in rows:
    if r.get('資料週期'):
     group=r.get('項目','');u=re.search(r'單位[:：]([^)]*)',group);unit=(u[1].strip() if u else '') or None
     field_rules.append({'row_selector':{'項目':group,'欄位名稱':r.get('欄位名稱','')},'source_field':'數值','normalized_unit':unit,'unit_evidence_basis':'literal項目(單位:) token' if unit else 'source_unit_unconfirmed_or_empty','measure':group,'stock_flow_ratio_financial':'financial_amount' if '費' in group else 'stock_or_annual_flow_as_named','period_resolution':'annual' if r['資料週期']=='年' else 'month','comparison_status':'source_series_only'})
    else:
     for field in ['借閱人次','借閱冊數','採購冊數','購書經費']:
      if field in r:field_rules.append({'source_field':field,'normalized_unit':literal_unit(field),'unit_evidence_basis':'literal_field_suffix' if literal_unit(field) else 'currency_unit_not_printed_in_field','measure':field,'stock_flow_ratio_financial':'financial_amount_not_same_as_acquisition_volume' if field=='購書經費' else 'transaction_or_acquisition_flow','comparison_status':'published_panel_limited' if field=='採購冊數' and len(rows)>1 else 'source_series_only'})
   field_rules=list({json.dumps(r,ensure_ascii=False,sort_keys=True):r for r in field_rules}.values())
   years=set()
   for r in rows:
    if re.fullmatch(r'[0-9]{3}',str(r.get('年度',''))):years.add(int(r['年度'])+1911)
    elif re.match(r'\d{4}-',r.get('資料時間日期','')):years.add(int(r['資料時間日期'][:4]))
   if not years:
    m=re.match(r'(\d{3})年',doc.get('resource_title',''))
    if m:years.add(int(m[1])+1911)
   raw_years=sorted(years)
   facts={**dimension_facts(),'measure':'source項目 and欄位名稱 or literal named JSON fields; preserve distinct year/month/branch/budget/acquisition populations','unit':'only exact printed unit token or冊數/人次 suffix promoted; empty unit stays unresolved','period_resolution':sorted({r.get('資料週期') for r in rows if r.get('資料週期')}),'population':doc['source_title'],'aggregation_role':'總館/分館 and aggregate municipal data must not be mixed with per-branch circulation','age_sex_reader_classification':sorted({r.get('欄位名稱') for r in rows if r.get('欄位名稱') in {'男','女'}})}
   status='source_series_only';scope='Same original named series only; no cross-file comparison approval. Explicit年度 multi-row acquisition冊數 has a narrower same-file panel rule.'
   unresolved+=['ISO日期是資料期標記，不能因1月1日字樣認定全年流量的發生日。','資料未說明國立館是否計入；不與全國或他機關合計互補。']
   if doc['dataset_id']=='117921':unresolved+=['全年圖書及非書資料收藏數量的單位原欄為空；中文／外文／期刊／非書等不能擅配同一冊單位。','2015–2016電子資料庫／光碟資料庫與2017–2018線上資料庫欄名不同，保留系列斷點。']
   if doc['dataset_id']=='127807':unresolved+=['男／女分列只在部分月份原印，不能將男／女與未分類總量直接相加或套成固定歷年sex grid。']
   if doc['dataset_id']=='84915':unresolved+=['購書經費原值含萬，但幣別／元單位未由該欄明印；不得把採購冊數當同年度館藏增加量。']
  cards.append({'evidence_id':'phase2-json-'+doc['dataset_id']+'-'+str(doc['resource_index']).zfill(2),'source_id':source_id,'component_source_id':'local-'+doc['dataset_id']+'-'+str(doc['resource_index']).zfill(2),'source_sha256':doc['source_sha256'],'source_url':doc['source_download_url'],'source_page_url':doc['source_url'],'source_locator':{'kind':'JSON_array','rows':[0,len(rows)-1],'field_pointers':[{'field':f,'first_pointer':'/0/'+jp(f),'pointer_template':'/{array_index}/'+jp(f)} for f in fields]},'layer':'canonical_local_history','source_table':doc.get('resource_title'),'source_table_title':doc['source_title'],'source_fields':fields,'data_years_present':raw_years,'reviewed_original':{'sha_verified':True,'raw_rows':len(rows),'canonical_records_covered':len(retained),'exact_literal_headers_and_period_fields_read':True},'semantic_facts':facts,'original_notes_short':[],'supported_comparison_scope':{'status':status,'scope':scope,'must_match':['source_sha256','exact_metric_and_unit','period_resolution','same_original_location_or_population_label'],'field_rules':field_rules},'unresolved':unresolved,'review_method':'Offline full original JSON array and literal field review; all matching released canonical records rebound to original array index/metric.'})
  cards[-1]['observation_ids']=[r['observation_id'] for r in retained]
  for rule in cards[-1]['supported_comparison_scope']['field_rules']:
   if rule.get('comparison_status')=='published_panel_limited':
    rule['observation_ids']=[r['observation_id'] for r in retained if r.get('source_field')==rule['source_field']]
    assert set(rule['observation_ids'])<=set(cards[-1]['observation_ids'])
 for row in canonical:
  src=source_lookup[row['source_sha256']];m=re.search(r'JSON array\[(\d+)\]',row['source_locator']);assert m,row['observation_id'];i=int(m[1]);raw=src['rows'][i];field=row.get('source_field')
  if '數值' in raw:assert str(raw['數值'])==str(row['raw_value'])
  else:assert str(raw[field])==str(row['raw_value'])
  if '統計年月' in raw:
   decoded=literal_month(raw['統計年月']);assert decoded
   period_counts['monthly_literal_period_code']+=1
   unit=literal_unit(field);assert unit
   if row.get('unit') is None:literal_promotions[unit]+=1
  elif field in raw and literal_unit(field) and row.get('unit') is None:literal_promotions[literal_unit(field)]+=1
 assert sum(c['reviewed_original']['canonical_records_covered'] for c in cards)==len(canonical),'Each canonical record must belong to exactly one source card'
 unique_arithmetic={(e['period_raw'],e['location_raw'],e['measure'],e['source_components_sum'],e['printed_combined_value']) for e in arithmetic}
 return cards,{'original_documents':len(metadata['documents']),'unique_original_SHA_versions':len(source_lookup),'raw_rows_read':checked_raw,'canonical_records_verified':len(canonical),'literal_unit_promotions_from_null':dict(literal_promotions),'period_annotations':dict(period_counts),'json_circulation_arithmetic_mismatches':arithmetic,'arithmetic_mismatch_source_version_occurrences':len(arithmetic),'arithmetic_mismatch_unique_period_location_measure_facts':len(unique_arithmetic),'arithmetic_mismatch_policy':'all values unchanged; repeated original source versions are retained but not counted as new facts; tests do not define measure equivalence'}

def audit_workbooks(root,source_root):
 sources=jread(root/'raw/phase1_local_sources/sources.json')['sources'];allfacts=readjsonl(root/'derived/phase1_local_sources_cells.jsonl');stats=readjsonl(root/'derived/phase1_local_sources_long.jsonl');cards=[];verified=0;factverified=0;counts=collections.Counter();groups_report=[]
 for src in sources:
  sid=src['source_id'];facts=[r for r in allfacts if r['source_id']==sid];rows=[r for r in stats if r['source_id']==sid];original=source_root/src['source_filename'];assert original.is_file() and sha(original)==src['source_sha256'],sid
  wanted=collections.defaultdict(set)
  for r in facts:wanted[r['source_sheet']].add((int(r['source_row']),int(r['source_column'])))
  if '114' in sid:wanted['背景說明-圖書館概況'].update({(17,1),(24,1),(26,1)});wanted['11014-03-01-2'].add((25,1))
  original_data=original_cells(original,wanted)
  for r in facts:
   raw=original_data.get(r['source_sheet'],{}).get((int(r['source_row']),int(r['source_column'])),{'display':'','stored':None,'native':None,'formula':None})
   assert raw['display']==r['source_display_raw'],(sid,r['source_sheet'],r['source_cell'],'display')
   assert raw['stored']==r['source_stored_value_raw'],(sid,r['source_sheet'],r['source_cell'],'stored')
   factverified+=1
  for r in rows:
   cell=original_data[r['source_sheet']][int(r['source_row']),int(r['source_column'])];display=cell['display'].strip();stored=cell['stored'];typed=Decimal(stored) if stored is not None and cell['native'] in {'float','percentage','currency','n'} else None
   if typed is not None and display in {'-','－','—','–','…','...','NA','N/A','無'}:status='source_display_typed_value_conflict_unresolved';assert r['value'] is None
   elif display in {'-','－','—','–','…','...','NA','N/A','無'}:status='source_marker';assert r['value'] is None
   else:status='reported_typed_numeric';assert typed is not None and Decimal(str(r['value']))==typed
   assert status==r['value_status'];counts[status]+=1;verified+=1
   sheet=r['source_sheet'];nrow=int(r['source_row']);ncol=int(r['source_column'])
   assert r['source_row_label_raw']==get(original_data,sheet,'A'+str(nrow)),(sid,sheet,r['source_cell'],'row label')
   if 'hualien' in sid:
    parent=get(original_data,sheet,'B8' if ncol<=5 else 'F8');sex=get(original_data,sheet,coord(9,ncol))
    assert r['metric_raw']==parent,(sid,sheet,r['source_cell'],'metric heading')
    assert r['source_column_path']==[parent,sex],(sid,sheet,r['source_cell'],'column path')
    assert '人次' in get(original_data,sheet,'A7') and '冊' in get(original_data,sheet,'A7')
    header=re.search(r'(\d+)年\s*(\d+)月',get(original_data,sheet,'A6'));label=re.fullmatch(r'(\d+)年(\d+)月',sheet.strip())
    assert header and label,(sid,sheet,get(original_data,sheet,'A6'))
    same=header.groups()==label.groups()
    if same:assert r['period_year']==int(header[1])+1911 and r['period_month']==int(header[2])
    else:assert r['period_year'] is None and r['period_month'] is None and r['period_status']=='source_sheet_name_header_period_conflict_unresolved'
  sheets=collections.defaultdict(list)
  for r in rows:sheets[r['source_sheet']].append(r)
  signatures=collections.defaultdict(list)
  for name,sheetrows in sheets.items():
   facts_sheet=[r for r in facts if r['source_sheet']==name];header=[(r['source_cell'],r['source_display_raw'],r['source_stored_value_raw']) for r in facts_sheet if r['source_cell_role'] in {'header_cell','row_label_cell','column_label_cell','necessary_note_cell','definition_reference_cell'}]
   # Structural signature deliberately uses exactly the selected statistical
   # row labels, printed multilevel column path and raw unit; period is excluded.
   structure=sorted({(r['source_row'],r['source_row_label_raw'],json.dumps(r['source_column_path'],ensure_ascii=False,sort_keys=True),r['unit_raw']) for r in sheetrows})
   h=hashlib.sha256(json.dumps(structure,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();signatures[h].append((name,sheetrows))
  for ordinal,(signature,members) in enumerate(sorted(signatures.items()),1):
   memberrows=[r for name,rr in members for r in rr];names=[name for name,rr in members];first=names[0];hualien='hualien' in sid;is114='114' in sid
   periods=sorted({(r.get('period_year'),r.get('period_month')) for r in memberrows if r.get('period_year') is not None});years=sorted({x[0] for x in periods});unresolved=[]
   if hualien:
    facts_sem={**dimension_facts(),'measure':'借閱人數 raw heading, but original A7 unit explicitly人次; separate borrowing冊數','unit':{'借閱人數':'人次','借閱冊數':'冊'},'collection_type':'圖書資訊 borrowing; no proof all formats/reporting completeness unchanged','stock_flow_ratio_financial':'monthly borrowing flow','period_resolution':'month only when original sheet name and A6 agree','population':'讀者身分 classification' if 'reader' in sid else '館藏地（室） classification','aggregation_role':'row總計 and sex總計 overlap components; do not add totals to components','age_sex_reader_classification':{'sex':['總計','男','女','不詳'],'row_categories_raw':sorted({r['source_row_label_raw'] for r in memberrows})},'facilities_are_not_identified_by_row_count':True,'metric_heading_and_unit_evidence':{'A7':get(original_data,first,'A7'),'B8':get(original_data,first,'B8'),'F8':get(original_data,first,'F8')}}
    status='published_panel_limited' if len(periods)>1 else 'source_series_only';scope='Same original workbook SHA + this exact header/row-label grid signature + exact row classification/metric/sex; compare only cells with matched period and reported typed value.'
    unresolved=['不得將reader與room兩種分類相加；來源未證明兩分類填報母體逐月完全相等。','borrow人數原題不等於去重人數；A7實印人次，保留兩者原字。','display - 和typed0矛盾維持null與原typed值，不能自動改0或缺值。','部分來源公式只保留cached value，未重新計算或認證公式正確。','新出現／更名館藏地是分類斷點，不能無證據接成設施實體。']
    notes=[{'locator':{'sheet':first,'cell':'A7'},'raw':get(original_data,first,'A7')}]
   else:
    facts_sem={**dimension_facts(),'measure':'five distinct collection/acquisition/borrowing/new-reader metrics','unit':{'館藏數量(冊)':'冊','新書入庫數量(冊)':'冊','借閱冊數(冊)':'冊','借閱人次(人)':'人 as printed;114 same-workbook definition explicitly event人次','讀者新增數(人)':'人'},'stock_flow_ratio_financial':'stock and annual flows remain separate','period_resolution':'explicit年度 in114, catalogue-title-year only in113','population':'six printed library/branch columns plus total, total not an extra facility','aggregation_role':'總計 overlaps component columns','age_sex_reader_classification':'sex/age not separately printed in these grids'}
    status='source_series_only';scope='Only original-version series;113 and114 attachments do not establish identical effective definitions or direct year comparison.';notes=[]
    if is114:
     for cell in ['A17','A24','A26']:
      assert get(original_data,'背景說明-圖書館概況',cell),cell
     assert '當年十二月底' in get(original_data,'背景說明-圖書館概況','A17');assert '一人一次' in get(original_data,'背景說明-圖書館概況','A24')
     facts_sem['same_workbook_definition_evidence']=[{'sheet':'背景說明-圖書館概況','cell':'A17','facts':'靜態為當年12月底，動態為當年1月至12月底；僅對這個114來源版本。'},{'sheet':'背景說明-圖書館概況','cell':'A24','facts':'借閱人次依全年借書或非書資料的一人一次計數，不是全年去重人數。'},{'sheet':'背景說明-圖書館概況','cell':'A26','facts':'借閱冊數為全年借出圖書或非書的冊次，一次借數冊計數冊次。'},{'sheet':'11014-03-01-2','cell':'A25','raw_short':get(original_data,'11014-03-01-2','A25').strip()}]
     facts_sem['normalized_unit_recommendation']={'metric_raw':'借閱人次(人)','printed_row_unit':'人','normalized_unit_candidate':'人次','basis':'same workbook A5人次(數) and explicit definition A24','status':'definition_qualified_event_count; retain raw row unit and allow root to decide reconciliation; never transfer to113'}
     unresolved=['原列借閱人次(人)與全表人次(數)及定義並列；不可只取其中一個字而隱藏原印差異。','背景定義對114版本可對應，不證明113來源當時相同。','讀者新增數不代表目前有效持證讀者或全年借閱去重人數。']
    else:unresolved=['附件本身無年度或統計標準時間，113只來自官方catalog題名，精確stock/flow時點未確認。','不能套用114工作簿背景定義到113；欄名相同不足證明填報一致。']
   blockers=collections.Counter(r['value_status'] for r in memberrows);conflict=sum(r['period_status']=='source_sheet_name_header_period_conflict_unresolved' for r in memberrows)
   groups_report.append({'source_id':sid,'grid_signature':signature,'sheets':names,'cells':len(memberrows),'period_conflict_cells':conflict,'value_status_counts':dict(blockers)})
   cards.append({'evidence_id':sid+'-grid-'+str(ordinal).zfill(2),'source_id':sid,'source_sha256':src['source_sha256'],'source_url':src['source_download_url'],'source_page_url':src['source_url'],'source_locator':{'kind':'workbook_grid','sheets':[{'sheet':name,'cells':sorted({r['source_cell'] for r in rr}), 'period_header_cell':'A6' if hualien else ('A4' if is114 else None)} for name,rr in members],'grid_signature':signature},'layer':'phase1_local_statistical_cells','source_table':get(original_data,first,'H3') if hualien else ('11014-03-01-2' if is114 else '工作表1'),'source_table_title':src['source_title'],'source_fields':{'row_headers_raw':sorted({r['source_row_label_raw'] for r in memberrows}),'column_paths_raw':sorted({json.dumps(r['source_column_path'],ensure_ascii=False) for r in memberrows}),'metric_units_raw':sorted({(r['metric_raw'],r['unit_raw']) for r in memberrows})},'data_years_present':years,'reviewed_original':{'sha_verified':True,'statistical_cells':len(memberrows),'all_matching_cells_original_XML_checked':True,'source_sheets_in_this_grid':len(members)},'semantic_facts':facts_sem,'original_notes_short':notes,'supported_comparison_scope':{'status':status,'scope':scope,'require_matching_grid_signature':signature,'excluded_value_statuses':['source_display_typed_value_conflict_unresolved','source_marker','blank_in_source'],'excluded_period_statuses':['source_sheet_name_header_period_conflict_unresolved'],'period_conflict_cells':conflict},'unresolved':unresolved,'review_method':'Entire related source XML cells read directly from original ZIP; stored/display values and statistical status compared for every cell; exact grid-header/row labels grouped without cross-file normalization.'})
   cards[-1]['observation_ids']=[r['observation_id'] for r in memberrows]
 return cards,{'source_files':len(sources),'source_cell_facts_XML_verified':factverified,'statistical_cells_XML_verified':verified,'value_status_counts':dict(counts),'grid_groups':groups_report}

def audit_programmes(root):
 meta=jread(root/'raw/ncl-2005-programmes/metadata.json');source=root/meta['source_local_path'];assert sha(source)==meta['source_sha256'];rows=readjsonl(root/'derived/ncl_2005_programmes.jsonl');quant=readjsonl(root/'derived/ncl_2005_programmes_long.jsonl');assert len(rows)==119 and len(quant)==123
 # The previous source-only independent review covers every number/label. This
 # new audit verifies the complete row/quantity relation and semantic guards.
 linked={q['observation_id']:q for q in quant};seen=[]
 for r in rows:
  assert r.get('data_year') is None
  for q in r['quantities']:
   original=linked[q['observation_id']];assert str(original['value_raw'])==str(q['value_raw']);assert str(original['value'])==str(q['value']);seen.append(q['observation_id'])
 assert len(seen)==len(set(seen))==len(quant)
 import pdfplumber
 with pdfplumber.open(source) as pdf:
  pages={n:pdf.pages[n-1].dedupe_chars(tolerance=.2) for n in [14,15,16,34]}
  for q in quant:
   box=q['source_cell_bbox'];box=json.loads(box) if isinstance(box,str) else box
   chars=[x for x in pages[int(q['source_pdf_page'])].chars if x['x0']>=box[0]-.3 and x['x1']<=box[2]+.3 and x['top']>=box[1]-.3 and x['bottom']<=box[3]+.3]
   raw=''.join(x['text'] for x in sorted(chars,key=lambda x:x['x0'])).strip()
   assert raw.replace(',','')==str(q['value_raw']).replace(',',''),(q['observation_id'],raw,q['value_raw'])
 cards=[]
 for table in meta['tables']:
  rr=[r for r in rows if int(r['source_table'])==table['table']];qq=[q for q in quant if int(q['source_table'])==table['table']]
  cards.append({'evidence_id':'phase2-ncl95-programme-table'+str(table['table']),'source_id':meta['source_id'],'source_sha256':meta['source_sha256'],'source_url':meta['source_download_url'],'source_page_url':meta['source_url'],'source_locator':{'table':table['table'],'pdf_pages':table['pdf_pages'],'printed_pages':table['printed_pages'],'programme_rows':[{'programme_id':r['programme_id'],'pdf_page':r['source_pdf_page'],'row':r['source_row'],'column':r['source_column'],'bbox':r['source_cell_bbox']} for r in rr]},'layer':'phase1_programme_rows_and_quantities','source_table':str(table['table']),'source_table_title':table['title'],'source_fields':table['column_headers_raw'],'data_years_present':[],'reviewed_original':{'sha_verified':True,'programme_rows':len(rr),'numeric_cells':len(qq),'all_numeric_glyph_spans_replayed':True,'prior_source_first_review':'research/ncl-2005-programmes-independent-review.json','new_check':'All row↔quantity original representations and null annual years checked; native numeric glyphs replayed; original PDFium images visually reread for headings and periods.','PDF_text_layer_limit':'Chinese headings absent from native PDF text extraction; source image review is distinct from machine glyph check.'},'semantic_facts':{**dimension_facts(),'measure':'specific named programme attendance/event/facility counts, not full-year library operations','unit':sorted({q['unit_raw'] for q in qq}),'stock_flow_ratio_financial':'programme counts','period_resolution':'programme window or explicitly printed month range; no synthesized full-year period','population':'named programme participants/facilities, 人 not evidence of unique people across events','aggregation_role':'printed summary rows overlap listed components; merged county slots recorded once','age_sex_reader_classification':'not present','report_reference_year_is_not_data_year':True,'source_edition_roc':95,'source_report_reference_year':2005,'period_status_counts':dict(collections.Counter(r['period_status'] for r in rr)),'component_checks':[x for x in meta['component_checks']] if table['table']==6 else [],'periods':[{'programme_id':r['programme_id'],'period_raw':r['period_raw'],'period_status':r['period_status'],'start_month_candidate':r['period_start_month_candidate'],'end_month_candidate':r['period_end_month_candidate']} for r in rr if table['table']==7]},'original_notes_short':['表6前文辦理窗與期程用字不完全一致，原表總計與分項加總差異保留。'] if table['table']==6 else ['第5列94年12月至95年5月；第6列95年4月至5月；其餘四列期間未知，不套成整年。'],'supported_comparison_scope':{'status':'source_series_only','scope':'Only same named programme and literal quantity; incompatible with annual canonical quantities, different programmes or inferred annual dates.'},'unresolved':['人數是否跨場去重未明示；不得稱全年服務人次或去重讀者。','2005為來源報告參照年；programme data_year始終null。','原縣市／館名不轉現行行政區；不以活動清單當設施名冊。'],'review_method':'Prior complete independent original-page review plus new full row/quantity and numeric glyph audit; original PDFium image headings/periods reread.'})
  cards[-1]['observation_ids']=[q['observation_id'] for q in qq]
  cards[-1]['programme_row_ids']=[r['programme_id'] for r in rr]
 return cards,{'programme_rows':len(rows),'numeric_quantity_cells':len(quant),'annual_years_all_null':True,'row_quantity_links_verified':len(seen),'no_cross_layer_aggregation':True}

def self_test():
 assert literal_month('10412')['year']==2015 and literal_month('11501')['month']==1
 for bad in ['105','11500','11513','1041','104120','１１５０１',' 11501','00012',None]:assert literal_month(bad) is None,bad
 assert literal_unit('借閱及續借冊數')=='冊' and literal_unit('取消預約人次')=='人次' and literal_unit('借閱人數') is None

def run(root,source_root):
 self_test();protected={p:{'sha256':sha(path_for(root,p)),'mtime_ns':path_for(root,p).stat().st_mtime_ns} for p in PROTECTED}
 canonical=[r for r in readjsonl(path_for(root,'data/combined/observations.jsonl')) if r.get('source_family')=='地方政府開放歷史表'];assert len(canonical)==14751
 a,ja=audit_json(root,canonical);b,wb=audit_workbooks(root,source_root);c,pr=audit_programmes(root)
 bindings={}
 for layer,expected in [('canonical_local_history',14751),('phase1_local_statistical_cells',18486),('phase1_programme_rows_and_quantities',123)]:
  ids=[oid for card in a+b+c if card['layer']==layer for oid in card['observation_ids']]
  assert len(ids)==len(set(ids))==expected,(layer,len(ids),len(set(ids)))
  bindings[layer]={'bound_ids':len(ids),'unique_ids':len(set(ids)),'exactly_once':True}
 assert sum(len(card.get('programme_row_ids',[])) for card in c)==119
 for p,state in protected.items():assert sha(path_for(root,p))==state['sha256'] and path_for(root,p).stat().st_mtime_ns==state['mtime_ns'],'Protected output changed '+p
 result={'schema_version':'phase2-local-evidence-1.0.0','dependencies':['Python3.12 standard library','pdfplumber'],'contract':'docs/phase2-contract.json','contract_sha256':sha(root/'docs/phase2-contract.json'),'script_sha256':sha(Path(__file__)),'status':'PASS','scope':'All released14751 local canonical records; all18486 phase1 statistical cells; programme119 rows/123 quantities. No source data mutation.','evidence_cards':a+b+c,'coverage':{'json':ja,'workbooks':wb,'programmes':pr,'evidence_cards':len(a+b+c),'observation_id_bindings':bindings},'global_rules':[{'id':'literal_roc5_month','only_field':'統計年月','pattern':'^[0-9]{5}$','month_range':[1,12],'roc_year_min':1,'output_resolution':'month','year_offset':1911,'never_infer':'annual total or exact event date from this code; invalid code unresolved'},{'id':'literal_source_field_unit','suffixes':{'冊數':'冊','人次':'人次'},'applies_only':'exact source-version field pointer, original units remain retained; no unique-person inference'},{'id':'protected_source_conflicts','block_comparison_on':['source_display_typed_value_conflict_unresolved','source_sheet_name_header_period_conflict_unresolved','source_marker','blank_in_source'],'no_repairs':True},{'id':'programme_nonannual','programme_data_year':None,'source_report_reference_year_is_not_data_year':True},{'id':'cross_source','default':'source_series_only or unresolved','never_auto_splice':True,'same_label_is_not_effective_date_evidence':True}],'protected_values':{'unchanged':True,'inputs':protected},'limits':['Evidence review of existing source versions, not a new exhaustive website search.','JSON and original XML facts establish literal units/periods; no certification of unchanged historic reporting rules, agency correctness or collection completeness.','Same-original published panels permit only exact matching metric/unit/classification/grid and resolvable periods; cross-file/year/agency continuity remains unconfirmed.','Programme original numeric/label review was the prior source-first independent review; this producer-side follow-up does not claim a fresh independent or human double review.','Full original files, PDF images/OCR, contact fields and deployment paths are not copied into these reports.']}
 return result

def markdown(d):
 c=d['coverage'];prom=c['json']['literal_unit_promotions_from_null'];return '''# 第二階段地方來源口徑證據

狀態：PASS。此報告只新增來源版本的語義證據，既有 canonical、來源格及 programme 數值／ID／缺值均未改動。

- 地方歷史：完整讀回 35 份既有官方 JSON、2,333 原列；逐筆核對去重後 14,751 canonical 觀測的來源 SHA、陣列位置與原值。中間表重複來源未冒算新增資料。
- 44 張卡直接綁定 observation_ids：地方14751、試算表18486、programme量化123，逐層恰一次；programme另綁119 row IDs。positive欄位規則另列精確IDs，採購冊數限5筆原觀測，不提升整份預算檔。
- 新竹：原欄明寫「冊數」「人次」，可在 phase2 另註冊／人次單位；來源單位 null 不被覆寫。14,400 筆的「統計年月」皆符合嚴格五碼及有效月份，可作 literal_period_code 月別解碼；這不證明跨年填報規則一致。
- 可由原欄字義提升的原 null 單位共 %s 筆（%s）。「借閱」「續借」「借閱及續借」各自保留；館藏地是來源分類，不是設施唯一識別；人次不是去重讀者。
- 臺中：年報、月報、分館借閱、購書經費與採購冊數各自成系列。原單位空欄維持未確認；購書經費字樣及萬字縮寫不自行補幣別。2015–2016資料庫類別與2017–2018不同，男／女分列也只限明印月份。
- 四工作簿：直接由原 ZIP/XML 覆核全部 33,705 格來源事實與 18,486 格統計。5,098 格 display「-」/typed0矛盾、1 格原字標記、176 格表頭／sheet期間矛盾全部保留，不轉0、不擇一期間。花蓮 reader／room 分類及 sex 總計重疊，不能跨格整表加總。
- 連江：113只得catalog題名年，不能套114定義。114原工作簿背景 A17 明訂靜態12月底、動態1至12月；A24／A26定義全年借閱人次與冊次。借閱人次列原印「(人)」與全表人次／同工作簿定義並列，證據與候選單位均保留，不靜默改原欄。
- Programme：完整覆核119列與123數量連結及原數字字形，data_year全null；表6是特定計畫，表7第5列為2005年12月至2006年5月、第6列為2006年4月至5月、四列期間未知，不能變全年營運。原總計與分項差異照留。

`published_panel_limited` 僅限同一原件 SHA、相同 grid type、原欄／單位／分類及可確認期間；其他檔案、欄名變更、行政界線或定義生效日未得證據時，限 source_series_only／unresolved。來源有發布不等於官方填報正確，也不聲稱人類雙校。

完整來源卡、逐來源定位、欄位規則、月份／分類清單、工作簿 grid 群及未解事項見 [phase2-local-evidence.json](phase2-local-evidence.json)。重播：`python scripts/phase2_local_source_audit.py --source-root <已restore原件目錄>`；亦可用相對 originals 或既有環境變數。原件與全文不入本報告。
'''%(sum(prom.values()),'、'.join(k+str(v) for k,v in sorted(prom.items())))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--source-root',type=Path);p.add_argument('--self-test',action='store_true');a=p.parse_args();self_test()
 source=a.source_root or Path(os.environ.get('TW_LIBRARY_PHASE1_SOURCE_ROOT',str(a.root/'raw/phase1_local_sources/originals')));d=run(a.root,source)
 stable_write(a.root/'research/phase2-local-evidence.json',d);stable_write(a.root/'research/phase2-local-evidence.md',markdown(d));print(json.dumps({'status':d['status'],'cards':len(d['evidence_cards']),'json':{k:v for k,v in d['coverage']['json'].items() if k!='json_circulation_arithmetic_mismatches'},'workbook_statistical_cells':d['coverage']['workbooks']['statistical_cells_XML_verified'],'programme':d['coverage']['programmes']},ensure_ascii=False))
if __name__=='__main__':main()
