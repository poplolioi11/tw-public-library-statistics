#!/usr/bin/env python3
"""Owned, offline coordinate extraction for NCL 109–111 editions.

Inputs are the reviewed per-edition table-specifications.json and source PDFs
with immutable source-download metadata. No UI, networking or shared outputs.
PDFium is the second text engine for all selected value-cell checks.
"""
from __future__ import annotations
import collections,csv,hashlib,io,json,re,unicodedata
from decimal import Decimal
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium
BASE=Path(__file__).resolve().parents[1]
N=re.compile(r'^\d[\d,]*(?:\.\d+)?$')
STOCK='stock_reference_year_exact_date_not_stated';FLOW='flow_calendar_year';RATIO='derived_ratio'

def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,b):
 b=b.encode() if isinstance(b,str) else b
 if p.exists() and p.read_bytes()==b:return
 p.parent.mkdir(exist_ok=True,parents=True);q=p.with_suffix(p.suffix+'.tmp');q.write_bytes(b);q.replace(p)
def metric(k,l,u=None,ur=None,t=STOCK):return dict(id=k,label=l,unit=u,unit_raw=ur,temporal=t)
COUNTS=[metric('main','總館','所'),metric('branch','分館','所'),metric('district','區館','所'),metric('reading_room','閱覽室','所'),metric('outreach','館外服務站','處'),metric('all_facilities','合計',None)]
POP=metric('population','人口數','人')
SPENDING=[POP,metric('acquisition_expense','圖書資料購置經費','新臺幣元',t='annual_financial'),metric('acquisition_per_capita','每人平均購書經費','新臺幣元／人',t=RATIO)]
STAFF=[POP,metric('compiled_staff','編制內館員數(B)','人'),metric('professional_staff','編制內專業人員數(C)','人'),metric('volunteers','志工人數(D)','人'),metric('population_per_compiled_staff','編制內人員服務人口數(A/B)','人／人',t=RATIO),metric('population_per_professional_staff','編制內專業人員服務人口數(A/C)','人／人',t=RATIO),metric('volunteers_per_10000','每萬人擁有志工數(D/A*10,000)','人／萬人',t=RATIO)]
STAFFLEVEL=[metric(k,l,'人') for k,l in [('compiled','正式人力／編制內人員'),('contract','正式人力／約聘僱人員'),('temporary','正式人力／臨時人員'),('formal_subtotal','正式人力／小計'),('student','非正式人力／工讀生'),('volunteer','非正式人力／志工'),('other','非正式人力／其他'),('informal_subtotal','非正式人力／小計')]]
HOLD=[metric('books','圖書資料／圖書（冊）','冊','冊'),metric('periodicals','圖書資料／期刊（種）','種','種'),metric('newspapers','圖書資料／報紙（種）','種','種'),metric('other','圖書資料／其他（件）','件','件'),metric('physical_subtotal','圖書資料／小計'),metric('nonbook','非書資料（件）','件','件'),metric('database','電子資源／資料庫（種）','種','種'),metric('ebook','電子資源／電子書（種）','種','種'),metric('electronic_subtotal','電子資源／小計'),metric('all_holdings','總計')]
HOLDCOUNTY=[POP,metric('holdings','館藏圖書資源數量',None),metric('holdings_per_capita','每人平均擁有量',None,t=RATIO)]
USAGE=[POP,metric('loans','借閱冊數','冊次',t=FLOW),metric('borrower_visits','借閱人次','人次','人次',FLOW),metric('loans_per_capita','每人平均借閱冊數','冊次／人',t=RATIO)]
ACTIVITY=[('reading','閱讀推廣活動'),('education_arts','社教藝文活動'),('local','地方特色活動'),('story','說故事'),('film','影片欣賞'),('other','其他'),('subtotal','小計')]
IMMIGRANTS=[metric('immigrant_population','新住民人口數','人'),metric('books','圖書（冊）','冊','冊'),metric('periodicals','期刊（種）','種','種'),metric('events','活動（場次）','場次','場次',FLOW),metric('attendance','活動（人次）','人次','人次',FLOW)]
BUDGET=[metric('current','經常門（元）','新臺幣元','元','annual_financial'),metric('capital','資本門（元）','新臺幣元','元','annual_financial'),metric('total_budget','營運總經費（元）','新臺幣元','元','annual_financial')]
ACQUISITION=[metric('print_total','紙本圖書／合計（冊）','冊','冊',FLOW),metric('print_chinese','紙本圖書／中文（冊）','冊','冊',FLOW),metric('print_foreign','紙本圖書／外文（冊）','冊','冊',FLOW),metric('periodicals','期刊（種）','種','種',FLOW),metric('audiovisual','視聽資料（件）','件','件',FLOW),metric('ebooks','電子書（種）','種','種',FLOW)]
BASIC=[metric('holdings','館藏量（冊、件）','冊、件','冊、件'),metric('loans','借閱冊數','冊次',t=FLOW),metric('borrower_visits','借閱人次','人次',t=FLOW),metric('seats','閱覽席位','席')]
TITLES={'level_count':'全國公共圖書館數量統計―依圖書館隸屬層級','county_count':'全國公共圖書館數量統計―依縣市別','spending':'全國公共圖書館圖書資料購置經費及人均購書經費','staff_level':'全國公共圖書館人力資源統計','staff':'直轄市、縣市公共圖書館人力資源統計','holdings_level':'全國公共圖書館館藏資源數量統計','holdings_county':'直轄市、縣市公共圖書館館藏資源數量及人均擁有圖書量','usage':'直轄市、縣市公共圖書館圖書資料使用情形','events':'直轄市、縣市公共圖書館推廣活動類型及辦理場次','attendance':'直轄市、縣市公共圖書館推廣活動類型及參與人次','immigrants':'全國公共圖書館提供新住民各類服務情形','budget':'全國公共圖書館年度營運經費','acquisition':'全國公共圖書館採編服務館藏新增情形','stats_types':'我國各類型圖書館數量統計表／公共圖書館完整子群','stats_basic':'我國各類型圖書館基本統計表／公立公共圖書館完整列','stats_historical':'公立公共圖書館基本統計表'}

def get_metrics(typ,year):
 if typ=='level_count':return [dict(m,unit_raw='所' if i<4 else '處' if i==4 else None) for i,m in enumerate(COUNTS)]
 if typ=='county_count':return COUNTS
 if typ=='spending':return SPENDING
 if typ=='staff':
  a=[dict(m) for m in STAFF];a[0]['label']='服務轄區人口數(A)';a[2]['label']='編制內專業人員(C)';return a
 if typ=='staff_level':return STAFFLEVEL
 if typ=='holdings_level':return HOLD
 if typ=='holdings_county':return HOLDCOUNTY
 if typ=='usage':return USAGE
 if typ in ['events','attendance']:return [metric(k,l,'場次' if typ=='events' else '人次','場次' if typ=='events' else '人次',t=FLOW) for k,l in ACTIVITY]
 if typ=='immigrants':return IMMIGRANTS
 if typ=='budget':return BUDGET
 if typ=='acquisition':return ACQUISITION[:5 if year==2021 else 6]
 if typ=='stats_basic':return BASIC
 if typ=='stats_historical':
  a=[metric('library_count','圖書館數量','所')]+BASIC[:3]
  a[1]=metric('holdings','館藏量')
  if year==2021:
   a[2]=metric('loans','圖書借閱冊數','冊次',t=FLOW);a[3]=metric('borrower_visits','圖書借閱人次','人次',t=FLOW)
   a += [metric('ebook_loans','電子書借閱冊數','冊次',t=FLOW),metric('ebook_borrower_visits','電子書借閱人次','人次',t=FLOW)]
  return a+[BASIC[3]]
 if typ=='stats_types':return [metric('library_count','圖書館數量','所')]
 raise ValueError(typ)

def text_cell(pg,bbox):
 x0,y0,x1,y1=bbox;cc=[c for c in pg.chars if x0<=(c['x0']+c['x1'])/2<x1 and y0<=(c['top']+c['bottom'])/2<y1]
 lines=[]
 for c in sorted(cc,key=lambda c:((c['top']+c['bottom'])/2,c['x0'])):
  y=(c['top']+c['bottom'])/2
  line=next((l for l in lines if abs(l[0]-y)<2),None)
  if line is None:line=[y,[]];lines.append(line)
  line[1].append(c)
 return '\n'.join(''.join(c['text'] for c in sorted(z,key=lambda c:c['x0'])) for y,z in sorted(lines)).strip()

def compact(s):return re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
def parse(raw):
 t=compact(raw)
 if not t:return None,'blank_in_source','source_blank_preserved'
 if t in {'無','未新增'}:return None,'source_marker','source_marker_preserved_semantics_not_resolved'
 if t in {'-','—','--','…','...','NA','N/A'}:return None,'not_available_in_source','source_marker_preserved'
 if not N.fullmatch(t):raise ValueError(('Unparsed source field',repr(raw)))
 return str(Decimal(t.replace(',',''))),'reported_decimal' if '.' in t else 'reported','strip_original_thousands_separators_preserve_all_digits'

def run(year):
 rawdir=BASE/f'raw/ncl-{year}';cfg=json.loads((rawdir/'table-specifications.json').read_text());edition=cfg['edition']
 for evidence_kind in ['public-library','statistics','copyright','editing','toc']:
  em=json.loads((rawdir/f'yearbook-{edition}-{evidence_kind}.metadata.json').read_text())
  ep=BASE/em['source_local_path']
  if sha(ep.read_bytes())!=em['sha256']:raise ValueError('Original bibliographic evidence changed; review required')
 cm=json.loads((rawdir/'catalog.metadata.json').read_text())
 if cm['source_edition_roc']!=edition or cm['publication_date_on_entry']!=cfg['publication_entry_date']:
  raise ValueError('Reviewed catalogue date/edition differs; review required')
 catalogue_html=rawdir/'catalog.html'
 if catalogue_html.exists() and sha(catalogue_html.read_bytes())!=cm['sha256']:raise ValueError('Private catalogue snapshot changed; review required')
 catalogue_links={item['url'] for item in cm['pdf_links']}
 docs={};pdfs={};pdfiumdocs={};pgcache={};tp_cache={}
 for kind in ['public-library','statistics']:
  m=json.loads((rawdir/f'yearbook-{edition}-{kind}.metadata.json').read_text());p=BASE/m['source_local_path']
  if m['source_download_url'] not in catalogue_links:raise ValueError('Source attachment is absent from the reviewed catalogue projection')
  if sha(p.read_bytes())!=m['sha256']:raise ValueError('Original PDF hash changed; review required')
  docs[kind]=m;pdfs[kind]=pdfplumber.open(p);pdfiumdocs[kind]=pdfium.PdfDocument(p)
 def page(k,p):
  if (k,p) not in pgcache:pgcache[k,p]=pdfs[k].pages[p-1].dedupe_chars(tolerance=.3)
  return pgcache[k,p]
 rows=[];review=[];allchecks=[]
 for tab in cfg['tables']:
  typ=tab['type'];table=tab['table'];kind=tab.get('kind','public-library');m=docs[kind];metrics=get_metrics(typ,year)
  title=tab.get('title_raw',TITLES[typ]+f'（{year-1911}年）')
  if typ=='stats_historical':title=TITLES[typ]+f'（{year-1915}年至{year-1911}年）'
  before=len(rows)
  for segment in tab['segments']:
   p=segment['pdf_page'];pg=page(kind,p);bounds=segment['bounds'];ys=segment['ys']
   for j,y in enumerate(ys):
    row=segment['row_start']+j
    # Level tables store metrics on rows, institutional classes on columns.
    if typ in {'level_count','staff_level','holdings_level'}:fields=[(z,metrics[row-1],col) for col,z in enumerate(cfg['levels'],2)]
    elif typ=='stats_historical':fields=[('全國',metrics[j],col) for col in range(2,7)]
    else:fields=[(segment['entities'][j],met,col) for col,met in enumerate(metrics,2)]
    for idx,(entity,met,col) in enumerate(fields):
     byear=year;lo,hi=bounds[idx],bounds[idx+1];ylo,yhi=y-6.6,y+6.6
     if typ=='stats_historical':byear=year-4+idx
     if typ=='stats_types':lo,hi=(435,483) if j==0 else (395,435);col=3 if j==0 else 2
     special_magnitude=year==2020 and typ=='acquisition' and entity=='臺北市' and met['id']=='audiovisual'
     scoped=year==2020 and typ=='acquisition' and entity=='臺東縣' and met['id']=='ebooks'
     if special_magnitude or scoped:ylo,yhi=y-14,y+14
     bbox=[lo,ylo,hi,yhi];raw=text_cell(pg,bbox);rawglyph=raw;flags=[];notes=[]
     if any(unicodedata.category(c)=='Cc' and c!='\n' for c in raw):
      raw=''.join(c for c in raw if unicodedata.category(c)!='Cc' or c=='\n');flags.append('zero_width_PDF_control_glyph_omitted_from_visible_raw_preserved_in_original_fields')
     if '(cid:' in raw:
      # Only two selected 111-edition value cells use the missing Chinese cmap.
      if raw=='(cid:3602)' and year==2021 and typ=='staff' and ((entity=='嘉義市' and met['id']=='population_per_professional_staff') or (entity=='連江縣' and met['id'] in {'population_per_compiled_staff','population_per_professional_staff'})):
       raw='無';flags.append('Chinese_marker_transcribed_from_PDFium_image_due_missing_ToUnicode')
      else:raise ValueError(('Unreviewed CID value',year,table,row,col,raw))
     if special_magnitude:
      if compact(raw)!='2萬9,225':raise ValueError(('Magnitude source changed',raw))
      val,status,rule='29225','reported','literal_ten_thousand_magnitude';flags.append('source_numeric_magnitude_multiline')
     elif scoped:
      if compact(raw)!='分區資源中心新增80':raise ValueError(('Scoped source changed',raw))
      val,status,rule='80','reported','literal_scoped_quantity';flags.append('scoped_source_component_not_county_total')
     else:val,status,rule=parse(raw)
     if status=='source_marker':notes.append('原印文字標記照錄；語義未釐清，不推定0、缺失或無人。')
     if typ=='staff' and year==2021 and entity=='連江縣' and met['id'] in {'compiled_staff','population_per_compiled_staff'}:
      flags.append('source_positive_staff_count_but_service_population_marked_無');notes.append('本表連江原印編制內館員1人，但A/B原印無；不以除法自行修補。')
     if typ=='staff' and year==2021 and met['id']=='population':flags.append('source_population_matches_prior_year_differs_same_year_spending_table');notes.append('原表題明列110年，但人口與本卷表9不同、與前卷109年人口相同；保留原表年與數字，不改填2020。')
     if ',' in raw and N.fullmatch(compact(raw)) and not re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?',compact(raw)):flags.append('source_nonstandard_digit_grouping')
     role='published_total' if entity in {'全國','合計','小計','公共圖書館','公立公共圖書館'} or met['id'] in {'all_facilities','formal_subtotal','informal_subtotal','physical_subtotal','electronic_subtotal','all_holdings','subtotal','total_budget','print_total'} else 'derived_ratio' if met['temporal']==RATIO else 'reported_component'
     if role=='published_total':flags.append('published_total_overlaps_components')
     if typ in {'level_count','county_count'} and met['id']=='all_facilities':notes.append('含閱覽室及館外服務站，不能作公立公共館總分館所數。');flags.append('includes_reading_rooms_and_outreach_not_library_main_branch_count')
     if typ=='holdings_level' and met['unit'] is None:notes.append('跨冊、種、件之原刊小計／總計；未給統一計量單位，不自行換算。')
     county=entity in cfg['counties'];lev=typ in {'level_count','staff_level','holdings_level','stats_types'}
     ek='county' if county else 'national_total' if entity in {'全國','合計','小計','公立公共圖書館'} else 'library_level_or_ownership_class'
     if scoped:ek='county_scoped_component_not_full_total';notes.append('原格僅明示分區資源中心新增80種；不是臺東全縣完整電子書新增總量。')
     scope='本表縣市館統計，不含國立二館' if county or (entity in {'合計','小計'} and typ not in {'budget','level_count','staff_level','holdings_level'}) else '全國公立公共圖書館，含國立公共資訊圖書館及國立臺灣圖書館、排除國家圖書館另一類型'
     if typ=='county_count':scope='各縣市公共館及館外服務設施；不含國立二館；直轄市山地原住民區館計入直轄市'
     if typ=='stats_types':scope='完整公共圖書館類型含私立；國家圖書館另列不含於本組；依原國立／直轄市／縣市／鄉鎮市／山地原住民／私立子群'
     if typ=='stats_historical':scope='公立公共館全國歷史重刊版本；保留本卷數據，不與其他版本覆寫'
     if typ=='stats_basic':scope='公立公共圖書館完整列；原註館藏包括圖書、非書及電子書；其他圖書館類型排除'
     if typ=='acquisition':scope='國資圖、國臺圖及22縣市館藏新增服務原列；總計、中文、外文重疊不能相加'
     if scoped:scope='僅臺東縣分區資源中心新增電子書種數；非全縣完整新增總量'
     offset=cfg['public_printed_offset' if kind=='public-library' else 'statistics_printed_offset'];printed=p+offset
     foot='直轄市山地原住民區立圖書館館數計入直轄市立圖書館。' if typ=='county_count' else ('資料整理自國家圖書館「全國圖書館'+('調查' if year<2021 else '')+'統計系統」收錄之圖書館名錄；公立公共圖書館數量則取自國立公共資訊圖書館之「公共圖書館統計系統」。') if typ=='stats_types' else ('國家圖書館及公立公共圖書館館藏量，包含'+('圖書資料' if year==2021 else '圖書')+'、非書資料及電子書。') if typ=='stats_basic' else f'資料整理自{edition}年各縣市填報於國立公共資訊圖書館「公共圖書館統計系統」之數據。' if typ=='stats_historical' else ''
     unitbasis='原表題名／欄列頭明示單位' if met['unit_raw'] else '依原指標／同章文義標準化；原欄頭未另明示' if met['unit'] else '原表未列統一單位；混合量或比值不自行補單位'
     temporal=met['temporal'];start,end=(f'{byear}-01-01',f'{byear}-12-31') if temporal in {FLOW,'annual_financial'} else (None,None)
     locator=f'PDF page {p}; printed page {printed}; table {table}; data row {row}; column {col}; bbox '+','.join(f'{v:.2f}' for v in bbox)
     r=dict(data_year=byear,entity_raw=entity,entity_contextual_name=entity,entity_kind=ek,geography_vintage=f'{year} original source labels',national_libraries_scope=scope,
       metric_id=f'table{table}_{met["id"]}',metric_raw=met['label'],value_raw=raw,value=val,unit=met['unit'],unit_raw=met['unit_raw'],unit_basis=unitbasis,unit_status='printed_unit' if met['unit_raw'] else 'contextual_unit_inference' if met['unit'] else 'no_uniform_unit_reported',unit_interpretation_candidate=None,
       temporal_kind=temporal,value_status=status,source_id=m['source_id'],source_url=m['source_page_url'],source_download_url=m['source_download_url'],source_sha256=m['sha256'],source_local_path=m['source_local_path'],source_agency='國家圖書館',source_retrieved_at=m['source_retrieved_at'],source_pdf_page=p,source_printed_page=str(printed),source_table=str(table),source_row=row,source_column=col,source_locator=locator,raw_extracted_line=rawglyph,extraction_status='PDFium_image_headers_rows_reviewed_coordinate_glyphs_plus_second_engine_tokens',license_status='not_confirmed',license_url='https://www.ncl.edu.tw/open-government-declaration',publication_date=cfg['publication_entry_date'],publication_date_basis='official_catalog_entry_date; copyright_publication_month separately retained',copyright_publication_month=cfg['copyright_publication_month'],source_edition=str(edition),source_edition_roc=edition,table_title_raw=title,source_table_title=title,source_selection_title=title,source_title=f'中華民國{edition}年圖書館年鑑／'+('公共圖書館' if kind=='public-library' else '圖書館統計'),population_scope=scope,period_raw=f'{byear-1911}年（原表資料年）',period_start=start,period_end=end,notes='；'.join(notes),cell_annotation=raw if scoped else '',cell_bbox=[round(x,3) for x in bbox],source_cell_bbox=[round(x,3) for x in bbox],source_cell_bbox_kind='reviewed_numeric_row_band_and_column_bounds',snapshot_distribution='not_in_public_bundle',aggregation_role=role,institutional_level=entity if lev else '原表各層級合計',source_column_path=entity if typ in {'level_count','staff_level','holdings_level'} else str(byear-1911)+'年' if typ=='stats_historical' else met['label'],source_version_id=m['source_id']+':'+m['sha256'],source_data_year_raw=f'{byear-1911}年',scope_note=scope,time_reference=f'{byear}年全年' if start else f'原表{byear-1911}年；未明示精確存量日',quality_flags=flags,source_footnotes_raw=foot or None,source_footnotes_status='relevant_original_note_excerpt_whitespace_normalized' if foot else 'no_table_specific_note_printed',source_original_access_date_raw=None,source_data_obtained_date_raw=({2019:'109年8月',2020:'110年12月',2021:'111年12月'}[year]+'（統計章編例）') if kind=='statistics' else None,observation_identity_suffix='row:'+str(row),entity_label_status='printed_source_label_retained',interpretation_basis='原刊欄列及原值保留；不更換疑似錯值、不把文字標記當0。',parse_rule=rule,value_parse_rule=rule,value_qualifier='scoped_source_component' if scoped else None,source_location_kind='table_numeric_magnitude' if special_magnitude else 'table_scoped_quantity' if scoped else 'table_cell',original_fields=dict(entity=entity,metric=met['label'],value_raw=raw,raw_glyphs=rawglyph,table_title=title,source_data_row=row))
     if typ=='stats_historical' and met['id']=='holdings':
      r['unit_status']='source_unit_unconfirmed_or_not_printed'
      r['unit_basis']='本五年表原列只印館藏量，未列計量單位；不沿用單年基本表的冊、件或認定跨年口徑相同。'
      r['quality_flags'].append('historical_holdings_unit_not_printed_no_cross_table_imputation')
      r['notes']+='；'+r['unit_basis']
     if typ=='stats_basic':r['entity_contextual_name']='全國'
     r['source_original_physical_column']=col+1 if year==2021 and typ=='acquisition' else None
     if r['source_original_physical_column'] is not None:
      r['source_locator']+='; original physical column '+str(r['source_original_physical_column'])+' (source_column is the data-column convention excluding the serial-number column)'
     if typ=='stats_historical':
      r['entity_label_status']='contextual_national_aggregate_inferred'
      r['notes']+='；全國為依表題及公立公共館母體所作地理context，原五年表沒有印出全國地理列名。'
     rows.append(r)
     # A separate PDFium text engine reads the identical physical cell; no CSV input.
     if (kind,p) not in tp_cache:tp_cache[kind,p]=pdfiumdocs[kind][p-1].get_textpage()
     pheight=pg.height
     second=tp_cache[kind,p].get_text_bounded(left=lo,bottom=pheight-yhi,right=hi,top=pheight-ylo)
     digits=lambda s:''.join(re.findall(r'[0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?',s))
     # Chinese PDFium text is CID codepoints in111; compare only actual numeric-font glyphs.
     expected_digits=digits(re.sub(r'\(cid:[0-9]+\)','',rawglyph))
     if digits(second)!=expected_digits:raise ValueError(('Second engine numeric mismatch',year,table,row,col,rawglyph,repr(second),expected_digits,digits(second)))
     word_tokens=[w for w in pg.extract_words(x_tolerance=1,y_tolerance=2) if lo <= (w['x0']+w['x1'])/2 < hi and ylo <= (w['top']+w['bottom'])/2 < yhi and N.fullmatch(''.join(c for c in w['text'] if unicodedata.category(c)!='Cc'))]
     if status in {'reported','reported_decimal'} and not special_magnitude and not scoped:
      if len(word_tokens)!=1 or ''.join(c for c in word_tokens[0]['text'] if unicodedata.category(c)!='Cc')!=raw or word_tokens[0]['x0']<lo-.05 or word_tokens[0]['x1']>hi+.05:
       raise ValueError(('Independent word-token containment failure',year,table,row,col,raw,word_tokens,bbox))
     allchecks.append(dict(source_table=table,source_pdf_page=p,source_row=row,source_column=col,numeric_token_match=True,word_token_containment_checked=status in {'reported','reported_decimal'} and not special_magnitude and not scoped,blank_in_both=(not rawglyph and not second.strip()),second_engine='PDFium',first_engine='pdfplumber_character_grid'))
  count=len(rows)-before
  if count!=tab['expected_cells']:raise ValueError(('Incomplete table',year,table,count,tab['expected_cells']))
  review.append(dict(source_table=table,type=typ,pages=[s['pdf_page'] for s in tab['segments']],expected_cells=count,extracted_cells=count,status_counts=dict(collections.Counter(r['value_status'] for r in rows[before:])),complete=True))
 arithmetic=[]
 for tab in cfg['tables']:
  tt=tab['type'];rr=[r for r in rows if r['source_table']==str(tab['table']) and (r['source_id'].endswith('statistics') if tt.startswith('stats_') else r['source_id'].endswith('public-library'))]
  group=collections.defaultdict(list)
  for r in rr:group[r['source_row']].append(r)
  for rownum,rs in group.items():
   rs.sort(key=lambda r:r['source_column'])
   if tt in {'events','attendance','county_count','level_count','staff_level','holdings_level'}:parts,total=rs[:-1],rs[-1]
   elif tt=='budget':parts,total=rs[:2],rs[2]
   elif tt=='acquisition':parts,total=rs[1:3],rs[0]
   else:continue
   if any(r['value'] is None for r in parts+[total]):continue
   calc=sum(Decimal(r['value']) for r in parts);pub=Decimal(total['value']);ok=calc==pub
   arithmetic.append(dict(table=tab['table'],source_row=rownum,entity=total['entity_raw'],rule='printed_components_vs_printed_total',computed=str(calc),published=str(pub),matches=ok,interpretation='source diagnostic only; mixed-unit holdings not standardized'))
   if not ok:
    for r in rs:r['quality_flags'].append('source_published_components_total_discrepancy_preserved');r['notes']+='；原刊同列分項與合計算術不一致；保留原數字，未反算更正。'
 if len(rows)!=cfg['selected_cells']:raise ValueError('Total mismatch')
 keys=[(r['source_id'],r['source_table'],r['source_row'],r['source_column']) for r in rows]
 if len(keys)!=len(set(keys)):raise ValueError('Source cell collision')
 out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader()
 for r in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()})
 evidence_inputs={str(p.relative_to(BASE)):sha(p.read_bytes()) for p in sorted(rawdir.glob('yearbook-*')) if p.suffix=='.pdf' or p.name.endswith('.metadata.json')}
 evidence_inputs[str((rawdir/'catalog.html').relative_to(BASE))]=cm['sha256']
 evidence_inputs[str((rawdir/'catalog.metadata.json').relative_to(BASE))]=sha((rawdir/'catalog.metadata.json').read_bytes())
 evidence_inputs[str((rawdir/'table-specifications.json').relative_to(BASE))]=sha((rawdir/'table-specifications.json').read_bytes())
 csvbytes=out.getvalue();jsonbytes=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
 report=dict(input_evidence_sha256=evidence_inputs,data_year=year,source_edition_roc=edition,long_rows=len(rows),table_count=len(review),all_selected_tables_complete=True,tables=review,second_engine_cell_checks=len(allchecks),second_engine_numeric_mismatches=0,value_status_counts=dict(collections.Counter(r['value_status'] for r in rows)),quality_flag_counts=dict(collections.Counter(f for r in rows for f in r['quality_flags'])),arithmetic_checks=arithmetic,arithmetic_discrepancies=[a for a in arithmetic if not a['matches']],copyright_publication_month=cfg['copyright_publication_month'],publication_entry_date=cfg['publication_entry_date'],publication_date_difference=(cfg['copyright_publication_month']!=cfg['publication_entry_date'][:7]),csv_sha256=sha(csvbytes.encode()),jsonl_sha256=sha(jsonbytes.encode()),verification_limits='Producer reviewed PDFium images of all selected headers, row labels, units and terminal rows; all selected value positions crosschecked with PDFium numeric tokens against pdfplumber coordinate glyphs. This is not an independent human full-cell double collation. Chinese111edition has no ToUnicode; literal labels/無 mapped from source images, not guessed from CID strings.',intentional_exclusions=['Engineering/construction/equipment project case tables, local stories, awards, TopN reading performance, named people, book rankings and photographs.','Statistics chapter non-public-library families and duplicate charts.'],rights=dict(license_status='not_confirmed',license_url='https://www.ncl.edu.tw/open-government-declaration',full_originals_distribution='not_in_public_bundle',statistical_facts_only=True),dependencies=['scripts/ncl_modern_2019_2021_common.py',f'scripts/extract_ncl_{year}.py',f'raw/ncl-{year}/table-specifications.json',f'raw/ncl-{year}/yearbook-{edition}-public-library.pdf',f'raw/ncl-{year}/yearbook-{edition}-public-library.metadata.json',f'raw/ncl-{year}/yearbook-{edition}-statistics.pdf',f'raw/ncl-{year}/yearbook-{edition}-statistics.metadata.json'])
 report['dependencies']+=list(evidence_inputs)
 report['dependencies']=list(dict.fromkeys(report['dependencies']))
 write(BASE/f'derived/ncl_{year}_long.csv',csvbytes);write(BASE/f'derived/ncl_{year}_long.jsonl',jsonbytes)
 write(rawdir/'extraction-validation.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 write(rawdir/'token-checks.private.json',json.dumps(allchecks,ensure_ascii=False,indent=2)+'\n')
 for k,m in docs.items():m.update(selected_table_metadata=[t for t in review if ('statistics' if t['type'].startswith('stats_') else 'public-library')==k],source_cells=sum(r['source_id']==m['source_id'] for r in rows),license_url=report['rights']['license_url'],license_evidence='官方開放宣告二（三）明列出版品及專人專案撰文等須經原權利人同意；未確認本章全文開放授權。僅整理統計事實，不重散布完整PDF／影像。',publication_entry_date=cfg['publication_entry_date'],copyright_publication_month=cfg['copyright_publication_month'])
 write(rawdir/'documents.json',json.dumps(list(docs.values()),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['data_year','long_rows','table_count','value_status_counts','second_engine_cell_checks','csv_sha256']},ensure_ascii=False))
 return report
