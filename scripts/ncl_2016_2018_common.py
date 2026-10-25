#!/usr/bin/env python3
"""Reviewed coordinate producer for NCL editions106–108 (data2016–2018).
Dependencies: Python3.12 stdlib and pdfplumber. PDFium is used only for the
private image-review evidence, not by this deterministic offline extractor.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, io, json, re, unicodedata
from decimal import Decimal
from pathlib import Path
from urllib.request import Request,urlopen
import pdfplumber
BASE=Path(__file__).resolve().parents[1]
COUNTIES=['臺北市','新北市','桃園市','臺中市','臺南市','高雄市','基隆市','新竹縣','新竹市','苗栗縣','南投縣','彰化縣','雲林縣','嘉義縣','嘉義市','屏東縣','宜蘭縣','花蓮縣','臺東縣','澎湖縣','金門縣','連江縣']
STOCK='stock_reference_year_exact_date_not_stated';FLOW='flow_calendar_year';RATIO='derived_ratio'
NUM=re.compile(r'^[0-9][0-9,]*(?:\.[0-9]+)?\*?$')
PUBDATES={2016:'2018-06-01',2017:'2019-06-01',2018:'2020-09-01'}
ACCESS={2016:'106年5月4日',2017:'107年6月14日',2018:'108年5月30日'}
MONTHS={2016:'106年7月',2017:'107年8月',2018:'108年8月'}
PRINTED={2016:{'public-library':80,'statistics':430},2017:{'public-library':88,'statistics':400},2018:{'public-library':74,'statistics':378}}
LICENSE_URL='https://www.ncl.edu.tw/open-government-declaration'
LICENSE_EVIDENCE='官方開放宣告二（三）明列「出版品」及專人專案撰文等須經原權利人同意；未確認本章全文開放授權。僅重整公開統計事實，完整PDF、影像、HTML與周邊署名正文不列公開分發。'
def sha(b):return hashlib.sha256(b).hexdigest()
def stable_write(path,body):
 body=body.encode('utf-8') if isinstance(body,str) else body
 if path.exists() and path.read_bytes()==body:return
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(body);tmp.replace(path)
def metric(key,label,unit=None,raw=None,basis=None,temporal=STOCK):
 return dict(key=key,label=label,unit=unit,unit_raw=raw,unit_basis=basis or ('原表欄列頭明印單位' if raw else '依同章統計文義推定；原表本欄未另印單位' if unit else '原表未印可統一計算單位'),temporal=temporal)
def cy(w):return (w['top']+w['bottom'])/2

def parse(raw):
 token=re.sub(r'\s+','',unicodedata.normalize('NFKC',raw));ann='*' if token.endswith('*') else ''
 token=token.removesuffix('*')
 if not token:return None,'blank_in_source',ann
 if token=='無':return None,'source_marker',ann
 if token in {'-','--','—','…','...','NA','N/A'}:return None,'not_available_in_source',ann
 if not NUM.fullmatch(token):raise ValueError('Unparsed source cell '+repr(raw))
 return str(Decimal(token.replace(',',''))),'reported_decimal' if '.' in token else 'reported',ann

class Producer:
 def __init__(self,year,offline):
  self.year=year;self.ed=year-1910;self.raw=BASE/f'raw/ncl-{year}';self.rows=[];self.tables=[];self.docs={};self.pdfs={};self.quality=[]
  # Validate all dependencies before any generated output is written.
  for kind in ['public-library','statistics','copyright']:
   m=json.loads((self.raw/f'yearbook-{self.ed}-{kind}.metadata.json').read_text());path=BASE/m['source_local_path']
   if not path.exists():
    if offline:raise FileNotFoundError(str(path)+'; existing outputs retained')
    with urlopen(Request(m['source_download_url'],headers={'User-Agent':'Taiwan-public-library-statistics/source-linked-research'}),timeout=45) as response:b=response.read()
    if not b.startswith(b'%PDF') or sha(b)!=m['sha256']:raise ValueError('Observed source changed; a new version and image review are required; existing outputs retained')
    stable_write(path,b)
   if sha(path.read_bytes())!=m['sha256']:raise ValueError('Original SHA differs from reviewed source: '+str(path))
   self.docs[kind]=m;self.pdfs[kind]=pdfplumber.open(path)
 def page(self,kind,n):return self.pdfs[kind].pages[n-1].dedupe_chars(tolerance=.3)
 def text(self,pg,b):
  x0,y0,x1,y1=b
  return ''.join(c['text'] for c in sorted([c for c in pg.chars if x0<=(c['x0']+c['x1'])/2<x1 and y0<=(c['top']+c['bottom'])/2<y1],key=lambda c:c['x0'])).strip().replace('\uf098','*')
 def footnote(self,kind,pno,b):
  p=self.page(kind,pno);x0,y0,x1,y1=b
  return '\n'.join(l['text'] for l in p.crop((x0,y0,x1,y1)).extract_text_lines(x_tolerance=1,y_tolerance=2)).strip().replace('\uf098','*')
 def emit(self,kind,pno,table,title,entity,m,raw,bbox,row,col,year=None,note='',footnote=None,role=None,extra=None):
  yr=year or self.year;doc=self.docs[kind];v,status,ann=parse(raw);key=m['key'];temporal=m['temporal'];label=m['label'];scope=''
  county=entity in COUNTIES
  ek='county' if county else 'national_total' if entity in {'合計','小計','全國'} else 'named_national_public_library' if entity in {'國資圖','國臺圖'} else 'library_level_or_ownership_class'
  if county:scope='excluded_from_county_metrics' if kind=='public-library' else 'not_stated'
  elif entity in {'國立圖書館','國立級圖書館','國資圖','國臺圖'}:scope='separate_national_public_library_level'
  elif entity=='私立圖書館':scope='private_ownership_only'
  elif entity=='公共圖書館':scope='public_libraries_including_private'
  elif kind=='statistics' and '完整公共館子群' in title:scope='public_library_group_scope_and_facility_count_definition_specific_to_source'
  elif kind=='public-library' and ek=='national_total' and ('本表不含' in (footnote or '') or title.startswith('縣市')):scope='excluded_from_county_published_total'
  elif kind=='public-library' and title.startswith('全國') and ek=='national_total':scope='public_libraries_including_two_national_public_libraries_excluding_National_Central_Library'
  elif kind=='public-library' and ek=='library_level_or_ownership_class':scope='excluded_from_non_national_level_components'
  else:scope='see_table_specific_source_note'
  if role is None:role='derived_ratio' if temporal==RATIO else 'published_total' if ek=='national_total' or key in {'formal_subtotal','informal_subtotal','physical_subtotal','electronic_subtotal','all_holdings','all_facilities','subtotal','operating_total'} or entity=='公共圖書館' else 'reported_component'
  flags=['published_total_overlaps_components'] if role=='published_total' else []
  notes=[note] if note else []
  if ',' in raw and not re.fullmatch(r'[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?\*?',raw):flags.append('source_nonstandard_digit_grouping');notes.append('原刊分節逗點不規則；僅移除逗點解析全部原印數字，不補位、不改字。')
  if ann:flags.append('source_footnote_marker_retained');notes.append('原圖星號保留；此PDF內嵌字型私用碼U+F098依PDFium可見星號轉為*，數字不變。')
  if raw=='無':flags.append('source_marker_semantics_unconfirmed');notes.append('原表明印「無」，語義未進一步確認；value留空並保留source_marker，不改0或推定不適用。')
  if key in {'physical_subtotal','electronic_subtotal','all_holdings'}:notes.append('原表混合冊、種、件或未明示統一單位；總計不可視為純圖書冊數。')
  if key=='all_facilities':flags.append('includes_reading_rooms_and_outreach_not_library_main_branch_count');notes.append('本格含閱覽室及館外服務站；不可直接當總館、分館、區館數。')
  start,end=(f'{yr}-01-01',f'{yr}-12-31') if temporal in {FLOW,'annual_financial'} else (None,None)
  bbox=[round(x,3) for x in bbox];printed=PRINTED[self.year][kind]+pno
  r=dict(data_year=yr,entity_raw=entity,entity_contextual_name=entity,entity_kind=ek,geography_vintage=f'{yr}年原刊縣市標籤；未跨行政區界線重編',national_libraries_scope=scope,
   metric_id=f'table{table}_{key}',metric_raw=label,value_raw=raw,value=v,value_status=status,unit=m['unit'],unit_raw=m['unit_raw'],unit_basis=m['unit_basis'],unit_status='printed_unit' if m['unit_raw'] else 'contextual_unit_inference' if m['unit'] else 'no_uniform_unit_reported',temporal_kind=temporal,
   source_id=doc['source_id'],source_url=doc['source_page_url'],source_download_url=doc['source_download_url'],source_sha256=doc['sha256'],source_local_path=doc['source_local_path'],source_agency='國家圖書館',source_retrieved_at=doc['source_retrieved_at'],source_pdf_page=pno,source_printed_page=str(printed),source_table=str(table),source_row=row,source_column=col,
   source_locator=f'PDF page {pno}; printed page {printed}; table {table}; data row {row}; column {col}; bbox '+','.join(f'{x:.3f}' for x in bbox),source_location_kind='table_cell',source_cell_bbox=bbox,source_cell_bbox_kind='reviewed_numeric_row_band_and_column_boundaries',
   raw_extracted_line=raw,extraction_status='PDFium_reviewed_headers_footnotes_and_native_coordinate_cells',license_status='not_confirmed',license_url=LICENSE_URL,
   publication_date=PUBDATES[self.year],publication_date_basis=f'官方入口明列日期；版權頁確認民國{self.ed+1}年'+('6月' if self.year<2018 else '9月'),source_edition=str(self.ed),source_edition_roc=self.ed,source_table_title=title,table_title_raw=title,source_title=f'中華民國{self.ed}年圖書館年鑑／'+('公共圖書館' if kind=='public-library' else '圖書館統計'),
   population_scope='公立公共圖書館；統計章館數完整公共館子群含私立，另依欄列與註腳分開',period_raw=f'{yr-1911}年（原表資料年）',period_start=start,period_end=end,notes='；'.join(notes),cell_annotation=ann,
   snapshot_distribution='not_in_public_bundle',aggregation_role=role,institutional_level=entity if ek=='library_level_or_ownership_class' else '原表各層級合計',source_column_path=entity if extra and extra.get('transposed') else label,source_version_id=doc['source_id']+':'+doc['sha256'],source_data_year_raw=f'{yr-1911}年',
   scope_note=scope,time_reference=f'{yr}年全年' if start else f'原表民國{yr-1911}年；精確時點未明示，不以卷號或出版日補日期',quality_flags=flags,source_footnotes_raw=footnote,source_footnotes_status='relevant_original_table_note' if footnote else 'no_table_specific_note_printed',source_original_access_date_raw=('106年10月13日' if self.year==2016 and table in {24,25} else ACCESS[self.year]) if kind=='public-library' else None,source_data_obtained_date_raw=MONTHS[self.year] if kind=='statistics' else None,
   observation_identity_suffix=f'pdf{pno}:row{row}:col{col}',entity_label_status='printed_source_label_retained',interpretation_basis='按原刊欄列、數值、資料年與註腳保存，不修補原刊矛盾或以計算結果覆寫。',parse_rule='strip_original_thousands_separators_preserve_all_digits_and_separate_footnote_marker',original_fields={'entity':entity,'metric':label,'value_raw':raw,'unit_raw':m['unit_raw'],'table_title':title})
  if extra:
   r.update({k:v for k,v in extra.items() if k!='transposed'})
  self.rows.append(r)
 def matrix(self,table,title,pno,region,ncols,metrics,kind='public-library',entities=None,transpose=False,row_offset=0,year_columns=None,footnote=None,note='',expected_rows=None,col_offset=2,role=None,extra=None):
  pg=self.page(kind,pno);x0,y0,x1,y1=region;ww=pg.extract_words(x_tolerance=1,y_tolerance=2)
  for w in ww:w['text']=w['text'].replace('\uf098','*')
  tokens=[w for w in ww if x0<=w['x0']<x1 and y0<cy(w)<y1 and (NUM.fullmatch(w['text']) or w['text'] in {'無','-','--','—','…'})]
  groups=[]
  for w in sorted(tokens,key=lambda w:(cy(w),w['x0'])):
   g=next((g for g in groups if abs(g['y']-cy(w))<1.8),None)
   if g is None:groups.append({'y':cy(w),'words':[w]})
   else:g['words'].append(w)
  groups.sort(key=lambda g:g['y'])
  if expected_rows is not None and len(groups)!=expected_rows:raise ValueError(('row count',self.year,table,pno,len(groups),expected_rows,[(g['y'],len(g['words'])) for g in groups]))
  for g in groups:
   g['words'].sort(key=lambda w:w['x0'])
   if len(g['words'])!=ncols:raise ValueError(('column count',self.year,table,pno,g['y'],[w['text'] for w in g['words']],ncols))
  if transpose:
   if len(metrics)!=len(groups) or len(entities)!=ncols:raise ValueError('metric/level grid mismatch')
  else:
   if len(metrics)!=ncols:raise ValueError('metric grid mismatch')
   if entities is not None and len(entities)!=len(groups):raise ValueError(('entity grid mismatch',table,len(entities),len(groups)))
  # Full rows determine nonoverlapping column bounds. Every token must then
  # roundtrip from original deduplicated PDF characters within its cell.
  boundaries=[x0]+[(max(g['words'][j]['x1'] for g in groups)+min(g['words'][j+1]['x0'] for g in groups))/2 for j in range(ncols-1)]+[x1]
  for j in range(ncols-1):
   if max(g['words'][j]['x1'] for g in groups)>min(g['words'][j+1]['x0'] for g in groups):raise ValueError(('overlap column',table,j))
  for i,g in enumerate(groups):
   y=g['y'];entity=entities[i] if entities is not None and not transpose else None
   if not transpose and entity is None:
    entity=re.sub(r'\s+','',self.text(pg,(280 if x0>280 else 50,y-5.7,x0,y+5.7)))
    if entity not in COUNTIES+['合計','小計','國資圖','國臺圖']:raise ValueError(('unrecognized printed entity',table,pno,i,repr(entity)))
   for j,w in enumerate(g['words']):
    b=(boundaries[j],y-5.7,boundaries[j+1],y+5.7);raw=self.text(pg,b)
    if re.sub(r'\s+','',raw)!=w['text']:raise ValueError(('character roundtrip',table,pno,i,j,raw,w['text']))
    m=metrics[i] if transpose else metrics[j];e=entities[j] if transpose else entity
    self.emit(kind,pno,table,title,e,m,raw,b,i+1+row_offset,j+col_offset,year=year_columns[j] if year_columns else None,note=note,footnote=footnote,role=role,extra=dict(extra or {},transposed=transpose))
  return [g['y'] for g in groups]
 def table(self,table,title,kind,pages,expected,scope):
  rr=[r for r in self.rows if r['source_table']==str(table) and r['source_id']==self.docs[kind]['source_id']]
  if len(rr)!=expected:raise ValueError(('table incomplete',table,len(rr),expected))
  counties=[r['entity_raw'] for r in rr if r['entity_kind']=='county']
  if counties and set(counties)!=set(COUNTIES):raise ValueError(('County set differs from22original labels',self.year,table,sorted(set(counties))))
  self.tables.append(dict(table=table,title=title,document_kind=kind,pdf_pages=pages,expected_cells=expected,extracted_cells=len(rr),reference_years=sorted({r['data_year'] for r in rr}),scope=scope,county_labels=sorted(set(counties)),status_counts=dict(collections.Counter(r['value_status'] for r in rr))))
 def validate(self):
  keys=[(r['source_id'],r['source_table'],r['source_pdf_page'],r['source_row'],r['source_column']) for r in self.rows]
  if len(keys)!=len(set(keys)):raise ValueError('Duplicate original cell positions')
  for r in self.rows:
   v,s,a=parse(r['value_raw'])
   if (v,s,a)!=(r['value'],r['value_status'],r['cell_annotation']):raise ValueError('parse mismatch')
   if r['value'] is None and r['value_raw']=='0':raise ValueError('zero/null conflated')
   if not all(r[k] for k in ['source_url','source_download_url','source_sha256','source_locator','source_version_id']):raise ValueError('Missing provenance')
  # Validate printed sums, preserving every inconsistency instead of repairing.
  for t in self.tables:
   rr=[r for r in self.rows if r['source_table']==str(t['table']) and r['source_id']==self.docs[t['document_kind']]['source_id']]
   # County component totals only for additive metrics, never ratio columns.
   for mid in sorted({r['metric_id'] for r in rr if r['entity_kind']=='county' and r['temporal_kind']!=RATIO}):
    components=[r for r in rr if r['metric_id']==mid and r['entity_kind'] in {'county','named_national_public_library'} and r['value'] is not None]
    totals=[r for r in rr if r['metric_id']==mid and r['entity_kind']=='national_total' and r['value'] is not None]
    for total in totals:
     if len({r['entity_raw'] for r in components if r['entity_kind']=='county'})!=22:continue
     actual=sum(Decimal(r['value']) for r in components);reported=Decimal(total['value'])
     if actual!=reported:self.issue(total,'source_total_differs_from_component_sum',{'component_sum':str(actual),'printed_total':str(reported),'difference_printed_minus_components':str(reported-actual)})
   # Transposed grid published totals across levels, only same metric/year.
   if any(r['source_column_path']==r['entity_raw'] for r in rr):
    for mid in sorted({r['metric_id'] for r in rr}):
     rs=[r for r in rr if r['metric_id']==mid];tt=[r for r in rs if r['entity_raw']=='合計'];cc=[r for r in rs if r['entity_raw']!='合計']
     if len(tt)==1 and cc and all(r['value'] is not None for r in rs):
      s=sum(Decimal(r['value']) for r in cc);v=Decimal(tt[0]['value'])
      if s!=v:self.issue(tt[0],'source_total_differs_from_component_sum',{'component_sum':str(s),'printed_total':str(v),'difference_printed_minus_components':str(v-s)})
  # Activity subtotals and ordinary annual budget rows can be checked by row.
  for t in self.tables:
   rr=[r for r in self.rows if r['source_table']==str(t['table']) and r['source_id']==self.docs[t['document_kind']]['source_id']]
   for rowkey in sorted({(r['source_pdf_page'],r['source_row']) for r in rr}):
    rs=[r for r in rr if (r['source_pdf_page'],r['source_row'])==rowkey]
    totals=[r for r in rs if r['metric_id'].endswith('_subtotal') or r['metric_id'].endswith('_operating_total')]
    if len(totals)!=1 or len(rs) not in {3,7}:continue
    trow=totals[0];cc=[r for r in rs if r is not trow]
    if trow['value'] is not None and all(r['value'] is not None for r in cc):
     s=sum(Decimal(r['value']) for r in cc);v=Decimal(trow['value'])
     if s!=v:self.issue(trow,'source_row_total_differs_from_components',{'component_sum':str(s),'printed_total':str(v),'difference_printed_minus_components':str(v-s)})
 def issue(self,row,flag,detail):
  if flag not in row['quality_flags']:row['quality_flags'].append(flag)
  row['notes']+='；原印總計與本表可加總分項不一致，原值保留，未以計算值覆寫。'
  self.quality.append(dict(source_id=row['source_id'],source_table=row['source_table'],source_row=row['source_row'],source_column=row['source_column'],entity_raw=row['entity_raw'],metric_raw=row['metric_raw'],source_locator=row['source_locator'],flag=flag,**detail))
 def write(self,exclusions):
  self.validate();names=list(dict.fromkeys(k for r in self.rows for k in r))
  buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=names);w.writeheader()
  for r in self.rows:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else '' if v is None else v for k,v in r.items()})
  csvpath=BASE/f'derived/ncl_{self.year}_long.csv';jsonpath=BASE/f'derived/ncl_{self.year}_long.jsonl'
  cb=buf.getvalue().encode();jb=('\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in self.rows)+'\n').encode()
  meta=dict(schema_version='ncl_core_coordinate_cells_v1',data_year=self.year,source_edition_roc=self.ed,publication_date=PUBDATES[self.year],records=len(self.rows),numeric_cells=sum(r['value'] is not None for r in self.rows),status_counts=dict(collections.Counter(r['value_status'] for r in self.rows)),documents=self.docs,tables=self.tables,intentional_exclusions=exclusions,
   rights=dict(license_status='not_confirmed',license_url=LICENSE_URL,license_evidence=LICENSE_EVIDENCE,public_distribution='Derived statistical facts only; complete PDF, images, full text and surrounding signed prose remain private.'),quality_issues=self.quality,
   scope_limitations=['完整性僅及下列指定營運核心表與統計章公共館子群，不是整冊所有表。','全國歷年表為同卷重刊版本，不能冒稱22縣市歷年核心原量全齊。','原印留白或無字未推定不適用；缺值未補0；原報0原樣保存。','縣市表與全國分層表母體、數值版本或電子書範圍可能不同，須依source_id、source_table與口徑挑選，不能直接相加。'],
   dependencies=['Python3.12 standard library','pdfplumber','scripts/ncl_2016_2018_common.py',f'scripts/extract_ncl_{self.year}.py'],image_review='All included table pages rendered with pypdfium2 and visually reviewed for headers, county labels, units and footnotes. Private images under corresponding raw directory.',outputs=[dict(path=str(csvpath.relative_to(BASE)),sha256=sha(cb),bytes=len(cb)),dict(path=str(jsonpath.relative_to(BASE)),sha256=sha(jb),bytes=len(jb))])
  stable_write(csvpath,cb);stable_write(jsonpath,jb);stable_write(self.raw/'extraction-metadata.json',json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({'data_year':self.year,'edition':self.ed,'records':len(self.rows),'status_counts':meta['status_counts'],'tables':len(self.tables),'quality_issues':len(self.quality)},ensure_ascii=False))

# Shared metric descriptions are source headings, not invented broader measures.
def common_metrics():
 population=metric('population','人口數','人')
 counts=[metric('main','總館（所）','所','所'),metric('branch','分館（所）','所','所'),metric('district','區館（所）','所','所'),metric('reading_room','閱覽室（所）','所','所'),metric('outreach','館外服務站（所）','所','所'),metric('all_facilities','合計','所',basis='原表總館、分館、區館、閱覽室及館外服務站合計，非僅圖書館總分區館數')]
 staff=[metric(k,l,'人',basis='同章人力資源段明示人數；此欄本身未另印人') for k,l in [('formal_compiled','正式人力／編制內人員'),('contract','正式人力／約聘僱人員'),('temporary','正式人力／臨時人員'),('formal_subtotal','正式人力／小計'),('student','非正式人力／工讀生'),('volunteer','非正式人力／志工'),('other','非正式人力／其他'),('informal_subtotal','非正式人力／小計')]]
 holdings=[metric('books','圖書資料／圖書（冊）','冊','冊'),metric('periodicals','圖書資料／期刊（種）','種','種'),metric('newspapers','圖書資料／報紙（種）','種','種'),metric('other_physical','圖書資料／其他（件）','件','件'),metric('physical_subtotal','圖書資料／小計'),metric('nonbook','非書資料（件）','件','件'),metric('databases','電子資源／資料庫（種）','種','種'),metric('ebooks','電子資源／電子書（種）','種','種'),metric('electronic_subtotal','電子資源／小計'),metric('all_holdings','總計')]
 spending=[population,metric('acquisition_spending','圖書資料購置經費','新臺幣元',basis='同章購置經費正文明述新臺幣及元；表頭未另印貨幣單位',temporal='annual_financial'),metric('spending_per_capita','每人平均購書經費','新臺幣元／人',basis='同章每人平均購書經費正文明述元；欄頭未另印',temporal=RATIO)]
 county_holdings=[population,metric('holdings','館藏圖書資源數量',None,basis='欄頭未印統一單位；同章館藏資源包含冊、件、種，不將館藏量改稱純圖書冊數'),metric('holdings_per_capita','每人平均擁有書量',None,basis='原表未另印單位；每人平均比率，未統一異質館藏的計量單位',temporal=RATIO)]
 loans=[population,metric('loans','借閱冊數','冊次',basis='原欄借閱冊數，按全年借閱流量正規化冊次',temporal=FLOW),metric('borrower_visits','借閱人次','人次','人次',temporal=FLOW),metric('loans_per_capita','每人平均借閱冊數','冊次／人',basis='原欄每人平均借閱冊數，按年度流量正規化',temporal=RATIO)]
 activities=[('reading','閱讀推廣活動'),('education_arts','社教藝文活動'),('local','地方特色活動'),('story','說故事'),('film','影片欣賞'),('other','其他'),('subtotal','小計')]
 immigrant=[metric('immigrant_population','新住民人口數','人'),metric('immigrant_books','圖書（冊）','冊','冊'),metric('immigrant_periodicals','期刊（種）','種','種'),metric('immigrant_activity_events','活動（場次）','場次','場次',temporal=FLOW),metric('immigrant_activity_attendance','活動（人次）','人次','人次',temporal=FLOW)]
 budget=[metric('current_expenditure','經常門','新臺幣元',basis='同章年度營運總經費正文明述元；幣別沿同章經費的新臺幣語境推定，原表未另印幣別',temporal='annual_financial'),metric('capital_expenditure','資本門','新臺幣元',basis='同章年度營運總經費正文明述元；幣別沿同章經費的新臺幣語境推定，原表未另印幣別',temporal='annual_financial'),metric('operating_total','營運總經費','新臺幣元',basis='同章年度營運總經費正文明述元；幣別沿同章經費的新臺幣語境推定，原表未另印幣別',temporal='annual_financial')]
 basics=[metric('holdings','館藏量（冊、件）','冊、件','冊、件'),metric('loans','借閱冊數','冊次',basis='年度借閱冊數按流量正規化冊次',temporal=FLOW),metric('borrower_visits','借閱人次','人次','人次',temporal=FLOW),metric('seats','閱覽席位','席',basis='閱覽席位按席位數推定；原表未另印席')]
 return dict(population=population,counts=counts,staff=staff,holdings=holdings,spending=spending,county_holdings=county_holdings,loans=loans,activities=activities,immigrant=immigrant,budget=budget,basics=basics)

def add_stats(p):
 year=p.year;ed=p.ed;c=common_metrics();base={2016:168,2017:212,2018:191}[year]
 if year==2016:
  title='我國各類型圖書館數量統計表（105年）／完整公共館子群'
  fn=p.footnote('statistics',3,(56,245,483,262))
  levels=['國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市立圖書館']
  metrics=[c['counts'][i] for i in [0,1,3,4,5]]
  p.matrix(base,title,2,(160,423,483,485),5,metrics,kind='statistics',entities=levels,expected_rows=4,row_offset=1,footnote=fn,note='此卷公共館類型合計包含閱覽室、館外服務站；另列私立圖書館80，總計1,218，不等同公立總分館530。')
  pg=p.page('statistics',2)
  for row,y,entity in [(1,413.1,'公共圖書館'),(6,491.9,'私立圖書館')]:
   # Exact baselines reviewed against the printed table and numeric token geometry.
   ww=[w for w in pg.extract_words(x_tolerance=1,y_tolerance=2) if abs(cy(w)-y)<3 and w['x0']>380 and NUM.fullmatch(w['text'])]
   if len(ww)!=1:raise ValueError(('stats2016 onecell',row,y,ww))
   w=ww[0];b=(w['x0']-2,cy(w)-5.7,w['x1']+2,cy(w)+5.7)
   p.emit('statistics',2,base,title,entity,(metric('library_count','私立圖書館數量','所',basis='同頁正文數量明示所；私立列未細分設施類型') if entity=='私立圖書館' else c['counts'][-1]),p.text(pg,b),b,row,7 if entity=='公共圖書館' else 6,footnote=fn,note='原表公共館組總計含私立且含閱覽室及館外服務站；私立列未細分設施種類，不假定其內部設施構成。')
  p.table(base,title,'statistics',[2],22,'complete public-library group: four ownership levels × main/branch/reading room/outreach/total; private and public-group total')
 else:
  title=f'我國各類型圖書館數量統計表（{year-1911}年）／完整公共館子群'
  labels=['公共圖書館','國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市立圖書館','直轄市山地原住民區立圖書館','私立圖書館']
  # Group total is in its separate last column, so these scalar cells have
  # explicitly reviewed disjoint regions rather than invented blank cells.
  pg=p.page('statistics',2);ww=pg.extract_words(x_tolerance=1,y_tolerance=2)
  ys=[379,397,415,433,451,469,487] if year==2017 else [156,174,193,211,229,256,274]
  # Baselines are obtained from the exact source values, and constrained to the
  # visibly reviewed public-library group, not by trying endpoint variants.
  actual=[w for w in ww if (w['x0']>320 if year==2017 else w['x0']>400) and (370<cy(w)<490 if year==2017 else 145<cy(w)<280) and NUM.fullmatch(w['text'])]
  actual.sort(key=cy)
  if len(actual)!=7:raise ValueError(('publiccountstatsrows',year,[(cy(w),w['text']) for w in actual]))
  fn=p.footnote('statistics',3,(56,276,483,309)) if year==2017 else p.footnote('statistics',2,(280,601,483,651))
  for i,(entity,w) in enumerate(zip(labels,actual),1):
   b=(w['x0']-2,cy(w)-5.7,w['x1']+2,cy(w)+5.7)
   p.emit('statistics',2,base,title,entity,metric('library_count','圖書館數量','所',basis='同頁各類型數量正文明述所；表頭未另印'),p.text(pg,b),b,i,3 if i==1 else 2,footnote=fn,note='完整公共館分類組包含私立；國家圖書館為另一類型，未混入公立公共館。')
  p.table(base,title,'statistics',[2],7,'complete public-library group including private; other library types intentionally excluded')
 title=f'我國各類型圖書館基本統計表（{year-1911}年）／公立公共圖書館列'
 fn=p.footnote('statistics',3,(56,452,483,531)) if year==2016 else p.footnote('statistics',3,(56,598,483,668)) if year==2017 else p.footnote('statistics',3,(56,279,483,338))
 yregion={2016:(350,373),2017:(475,495),2018:(157,177)}[year]
 p.matrix(base+1,title,3,(160,yregion[0],483,yregion[1]),4,c['basics'],kind='statistics',entities=['全國'],expected_rows=1,row_offset=1,footnote=fn,note='原註公立公共館館藏含圖書資料、非書資料及電子書，與其他表或歷年版本不強併。')
 p.table(base+1,title,'statistics',[3],4,'entire public-library row only; excludes separate National Central Library and other library types')
 histnum={2016:171,2017:215,2018:194}[year]
 title=f'公立公共圖書館基本統計表（{year-1915}年至{year-1911}年）'
 fn=p.footnote('statistics',4,(56,396,483,426)) if year==2016 else p.footnote('statistics',4,(56,598,483,659)) if year==2017 else p.footnote('statistics',4,(56,313,483,348))
 ys={2016:(315,394),2017:(499,596),2018:(230,309)}[year]
 hist=[metric('library_count','圖書館數量','所')]+c['basics']
 note='本卷重刊五年全國序列，保留出版版本；不是縣市歷年表。'
 if year==2016:note+='105年原表館數1,138與同卷含閱覽室／館外站設施總量相同；107卷表215另明示修訂為536，原版不覆寫。'
 if year==2017:note+='原註105年館數原著錄1,138，依公共圖書館統計系統更新數值為536；帶星號格原樣保留。'
 p.matrix(histnum,title,4,(125,ys[0],483,ys[1]),5,hist,kind='statistics',entities=['全國']*5,transpose=True,year_columns=list(range(year-4,year+1)),expected_rows=5,footnote=fn,note=note)
 p.table(histnum,title,'statistics',[4],25,'complete five-year national public-library table; preserve edition-specific revisions and definition uncertainty')
