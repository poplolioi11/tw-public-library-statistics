#!/usr/bin/env python3
"""Coordinate extraction of the reviewed 104-edition public-library core tables.

The reference year is 103/2014, verified in chapter text and table titles;
the actual publication date is 2016-07. Full PDF/HTML snapshots remain private.
Only this producer's files are written. Existing originals are hash-checked;
missing originals can be restored from their observed official attachment URLs.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, io, json, re, unicodedata
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen
import pdfplumber

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / 'raw/ncl-2014'
OUT = BASE / 'derived'
COUNTIES = ['臺北市','新北市','臺中市','臺南市','高雄市','基隆市','桃園縣','新竹縣','新竹市','苗栗縣','南投縣','彰化縣','雲林縣','嘉義縣','嘉義市','屏東縣','宜蘭縣','花蓮縣','臺東縣','澎湖縣','金門縣','連江縣']
LEVELS = ['國立級圖書館','直轄市級圖書館','縣市級圖書館','鄉鎮市區級圖書館','合計']
STOCK = 'stock_reference_year_exact_date_not_stated'
FLOW = 'flow_calendar_year'
RATIO = 'derived_ratio'
N = re.compile(r'^[0-9][0-9,]*(?:\.[0-9]+)?$')
DOCS, PDFS, ROWS, TABLES = {}, {}, [], []


def sha(data): return hashlib.sha256(data).hexdigest()


def stable_write(path, body):
    body = body.encode('utf-8') if isinstance(body, str) else body
    if path.exists() and path.read_bytes() == body: return
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(body)
    temporary.replace(path)


def document(kind, offline):
    if kind in DOCS: return DOCS[kind]
    m = json.loads((RAW / f'yearbook-104-{kind}.metadata.json').read_text())
    path = BASE / m['source_local_path']
    if not path.exists():
        if offline: raise FileNotFoundError(path)
        with urlopen(Request(m['source_download_url'], headers={'User-Agent':'Taiwan-public-library-statistics/source-linked-research'}), timeout=45) as response:
            body = response.read()
        if not body.startswith(b'%PDF') or sha(body) != m['sha256']:
            raise ValueError('Attachment changed: new version and image review required; old outputs retained')
        stable_write(path, body)
    if sha(path.read_bytes()) != m['sha256']: raise ValueError('Original PDF SHA differs from reviewed version')
    m.update(license_url='https://www.ncl.edu.tw/open-government-declaration',
        license_evidence='官方開放宣告二（三）明列「出版品」及專人專案撰文等須經原權利人同意；未確認本章全文開放授權。只整理統計事實，不重散布完整PDF、HTML或影像。',
        publication_date='2016-07-01', publication_date_basis='official_entry_visible_publication_date; copyright page confirms105年7月',
        source_data_year_evidence='公共館章首明示呈現103年發展，表14–23題名103年；統計編例明示103年統計、資料取得104年7月。')
    DOCS[kind] = m
    PDFS[kind] = pdfplumber.open(path)
    return m


def page(kind, n): return PDFS[kind].pages[n-1].dedupe_chars(tolerance=.3)
def cy(w): return (w['top'] + w['bottom']) / 2
def words(pg): return pg.extract_words(x_tolerance=1, y_tolerance=2)


def value(raw):
    token = re.sub(r'\s+', '', unicodedata.normalize('NFKC', raw))
    if not token: return None, 'blank_in_source'
    if token in {'-','--','—','…','...','NA','N/A'}: return None, 'not_available_in_source'
    if not N.fullmatch(token): raise ValueError('Unparsed nonnumeric source cell: ' + repr(raw))
    return str(Decimal(token.replace(',',''))), 'reported_decimal' if '.' in token else 'reported'


def text_in(pg, bbox):
    x0,y0,x1,y1 = bbox
    chars = [c for c in pg.chars if x0 <= (c['x0']+c['x1'])/2 < x1 and y0 <= (c['top']+c['bottom'])/2 < y1]
    # Every selected value cell is one numeric line. Slight glyph-baseline
    # differences must not reorder digits (the source's金門159 has this case).
    return ''.join(c['text'] for c in sorted(chars, key=lambda c:c['x0'])).strip()


def cells_at(pg, y, bounds):
    return [(text_in(pg,(x0,y-5.7,x1,y+5.7)), (x0,y-5.7,x1,y+5.7)) for x0,x1 in zip(bounds,bounds[1:])]


def footnote(table):
    if table == 14: return '（1）直轄市係指臺北市、新北市、臺中市、臺南市與高雄市。（2）數據資料整理自國立公共資訊圖書館「公共圖書館統計系統」2014年度彙整成果。'
    if table == 15: return '（1）本表不含國立臺灣圖書館及國立公共資訊圖書館統計數據。（2）直轄市總館部分臺中市總館35所為所轄各行政區圖書總館；另臺南市總館42所為臺南市立圖書館以及各區公所所轄之總館館數。（3）數據資料整理自國立公共資訊圖書館「公共圖書館統計系統」2014年度彙整成果。'
    if table in {16,19,20,21,22,23}: return '（1）本表不含國立臺灣圖書館及國立公共資訊圖書館統計數據。（2）數據資料整理自國立公共資訊圖書館「公共圖書館統計系統」2014年度彙整成果。'
    if table == 18: return '數據資料整理自國立公共資訊圖書館「公共圖書館統計系統」2014年度彙整成果。'
    if table == 199: return '資料整理自國家圖書館「全國圖書館調查統計系統」http://libstat.ncl.edu.tw/statFront/'
    if table == 200: return '（1）國家圖書館及公立公共圖書館館藏量，包含圖書、非書資料及電子書。（3）公立公共圖書館統計，檢自國立公共資訊圖書館「公共圖書館統計系統」2014年度彙整結果。'
    if table == 202: return '資料整理自近五年《中華民國圖書館年鑑》之「圖書館統計」專題。'
    return None


def emit(kind, pno, printed, table, title, entity, metric, raw, bbox, row, col, year=2014, note='', role=None):
    # metric: id, literal heading (with hierarchy), normalized unit, raw printed
    # unit, unit basis, temporal kind. Descriptions never become units.
    m = DOCS[kind]; key,label,unit,unit_raw,unit_basis,temporal = metric
    parsed,status = value(raw)
    entity_kind = 'county' if entity in COUNTIES else 'national_total' if entity in {'全國','合計'} else 'library_level_or_ownership_class'
    scope = ('excluded_from_county_metrics' if entity_kind=='county' else
        'public_libraries_including_private' if table==199 and entity=='公共圖書館（含私立）' else
        'private_ownership_only' if table==199 and entity=='私立圖書館' else
        'separate_national_public_library_level' if entity in {'國立級圖書館','國立圖書館'} else
        'excluded_from_non_national_level_components' if entity_kind=='library_level_or_ownership_class' else
        'included_in_published_national_total' if entity=='合計' else
        'public_libraries_including_two_national_public_libraries_excluding_National_Central_Library')
    if role is None: role = 'derived_ratio' if temporal==RATIO else 'published_total' if entity_kind=='national_total' or key in {'formal_subtotal','informal_subtotal','physical_subtotal','electronic_subtotal','all_holdings','subtotal'} or entity=='公共圖書館（含私立）' else 'reported_component'
    start,end = (f'{year}-01-01',f'{year}-12-31') if temporal in {FLOW,'annual_financial'} else (None,None)
    locator = f'PDF page {pno}; printed page {printed}; table {table}; data row {row}; column {col}; bbox ' + ','.join(f'{v:.2f}' for v in bbox)
    notes = [note] if note else []
    flags = ['published_total_overlaps_components'] if role=='published_total' else []
    if table in {21,22}: notes.append('欄序依PDFium原件影像：閱讀推廣、說故事、社教藝文、地方特色、影片欣賞、其他、小計；不可按extract_text多行欄頭輸出順序配數字。')
    if table==16 and entity=='基隆市' and key=='population':
        notes.append('原件實印4603498，與本卷表19/20基隆人口373,077不一致；忠實保留原值，未改成推測正值。');flags.append('source_internal_population_difference')
    if table==18 and key in {'physical_subtotal','electronic_subtotal','all_holdings'}:
        notes.append('原表跨冊、種、件的小計／總計原值保留，未給統一計算單位；圖書資料小計不含另列非書資料，總計另納非書及電子資源。')
    if entity=='桃園縣': notes.append('原表縣名為桃園縣，保留2014原刊地理名稱，不重分類為現行名稱。')
    r=dict(data_year=year,entity_raw=entity,entity_contextual_name=entity,entity_kind=entity_kind,
        geography_vintage=f'{year} original published geography; 桃園縣 retained where printed',national_libraries_scope=scope,
        metric_id=f'table{table}_{key}',metric_raw=label,value_raw=raw,value=parsed,unit=unit,unit_raw=unit_raw,unit_basis=unit_basis,
        temporal_kind=temporal,value_status=status,source_id=m['source_id'],source_url=m['source_page_url'],source_download_url=m['source_download_url'],
        source_sha256=m['sha256'],source_local_path=m['source_local_path'],source_agency='國家圖書館',source_retrieved_at=m['source_retrieved_at'],
        source_pdf_page=pno,source_printed_page=str(printed),source_table=str(table),source_row=row,source_column=col,source_locator=locator,
        raw_extracted_line=raw,extraction_status='PDFium_reviewed_headers_and_footnotes_coordinate_cells',license_status='not_confirmed',license_url=m['license_url'],
        publication_date='2016-07-01',publication_date_basis=m['publication_date_basis'],source_edition='104',source_edition_roc=104,
        table_title_raw=title,source_table_title=title,source_title='中華民國104年圖書館年鑑／'+('公共圖書館' if kind=='public-library' else '圖書館統計'),
        population_scope='公立公共圖書館；表199公共館組含私立，按各表註腳分開',period_raw=f'{year-1911}年（原表明列資料年）',
        period_start=start,period_end=end,notes='；'.join(notes),cell_annotation='',cell_bbox=[round(v,3) for v in bbox],
        source_cell_bbox=[round(v,3) for v in bbox],source_cell_bbox_kind='reviewed_numeric_row_band_and_column_bounds',
        snapshot_distribution='not_in_public_bundle',aggregation_role=role,institutional_level=entity if entity_kind=='library_level_or_ownership_class' else '原表各層級合計',
        source_column_path=entity if table in {14,17,18} else label,source_version_id=m['source_id']+':'+m['sha256'],source_data_year_raw=f'{year-1911}年',
        scope_note=scope,time_reference=f'{year}年全年' if start else f'原表民國{year-1911}年；未明示精確時點，不以卷號、出版日、上網日補日期',
        quality_flags=flags,source_footnotes_raw=footnote(table),source_footnotes_status='table_specific_relevant_original_excerpts_whitespace_normalized' if footnote(table) else 'no_table_specific_note_printed',
        source_original_access_date_raw=None,original_fields={'entity':entity,'metric':label,'value_raw':raw,'table_title':title,'unit_raw':unit_raw})
    ROWS.append(r)


def metric(key,label,unit,raw=None,basis=None,temporal=STOCK):
    return (key,label,unit,raw,basis or ('原表標題／欄列頭明印單位' if raw else '依同章文義推定，未宣稱欄頭明印單位'),temporal)


def record_table(table,title,kind,pages,expected,scope):
    records = [r for r in ROWS if r['source_table']==str(table) and r['source_id']==DOCS[kind]['source_id']]
    if len(records)!=expected: raise ValueError(('Incomplete table',table,len(records),expected))
    TABLES.append(dict(table=table,title=title,document_kind=kind,pdf_pages=pages,expected_cells=expected,extracted_cells=len(records),
        reference_years=sorted({r['data_year'] for r in records}),scope=scope,status_counts=dict(collections.Counter(r['value_status'] for r in records))))


def level_grid(table,pno,title,ys,bounds,metrics):
    pg=page('public-library',pno)
    for i,(y,m) in enumerate(zip(ys,metrics),1):
        cells=cells_at(pg,y,bounds)
        for j,(entity,(raw,bbox)) in enumerate(zip(LEVELS,cells),2): emit('public-library',pno,54+pno,table,title,entity,m,raw,bbox,i,j)
    record_table(table,title,'public-library',[pno],len(metrics)*5,'entire numeric grid; four public-library levels and published total')


def county_grid(table,pno,title,y0,y1,metrics,bounds,split=False):
    pg=page('public-library',pno)
    labels=[w for w in words(pg) if w['text'] in COUNTIES and y0<cy(w)<y1 and (w['x0']<115 or split and 280<w['x0']<330)]
    labels.sort(key=lambda w:(w['x0']>280,cy(w)))
    if [w['text'] for w in labels] != COUNTIES: raise ValueError(('County rows changed',table,[w['text'] for w in labels]))
    for i,w in enumerate(labels,1):
        b=bounds[1] if split and w['x0']>280 else bounds[0] if split else bounds
        for j,(m,(raw,bbox)) in enumerate(zip(metrics,cells_at(pg,cy(w)+.15,b)),2):
            emit('public-library',pno,54+pno,table,title,w['text'],m,raw,bbox,i,j,note='原表分左右續表，資料列依左表後右表的縣市順序編號。' if split else '')
    record_table(table,title,'public-library',[pno],22*len(metrics),'all 22 original county rows; excludes two national public libraries by printed note')


def extract():
    count=[metric('main','總館（所）','所','所'),metric('branch','分館（所）','所','所'),metric('outreach','館外服務站（所）','所','所')]
    level_grid(14,1,'全國公共圖書館數量統計－依圖書館級別（103年）',[620.8,634.7,648.7],[180,238,300,363,425,483],count)
    county_grid(15,2,'全國公共圖書館數量統計－依縣市別（103年）',205,370,[metric(k,l,'所',basis='同章表14相同總館／分館／館外服務站列明印所；表15本身未另印') for k,l,*_ in count],[[110,153,211,255],[338,382,436,483]],True)
    population=metric('population','人口數','人')
    spending=[population,metric('acquisition_spending','圖書資料購置經費','新臺幣元',basis='同章印55頁年度統計明述新臺幣及元，表16欄頭本身未印貨幣單位',temporal='annual_financial'),metric('spending_per_capita','每人平均購書經費','新臺幣元／人',basis='同章印55–56頁明述每人平均分配購書經費及元，表16欄頭本身未印貨幣單位',temporal=RATIO)]
    county_grid(16,2,'全國公共圖書館圖書資料購置經費及人均購書經費分析（103年）',490,655,spending,[[105,152.1,210,259],[333,383,440,483]],True)
    staff=[metric(k,l,'人',basis='同章印57頁人力資源段明示各類人員人數；表17欄頭未另印人') for k,l in [('formal_compiled','正式人力／編制內人員'),('contract','正式人力／約聘雇人員'),('temporary','正式人力／臨時人員'),('formal_subtotal','正式人力／小計'),('student','非正式人力／工讀生'),('volunteer','非正式人力／志工'),('other','非正式人力／其他'),('informal_subtotal','非正式人力／小計')]]
    level_grid(17,3,'全國公共圖書館人力資源統計（103年）',[559.7,573.6,587.6,602,629.5,643.5,657.4,671.4],[195,250,311,372,432,483],staff)
    holdings=[metric('books','圖書資料／圖書（冊）','冊','冊'),metric('periodicals','圖書資料／期刊（種）','種','種'),metric('newspapers','圖書資料／報紙（種）','種','種'),metric('other_physical','圖書資料／其他（件）','件','件'),metric('nonbook','非書資料（件）','件','件'),metric('physical_subtotal','圖書資料／小計',None,basis='原表小計未印統一單位；分項冊、種、件不可混為冊'),metric('databases','電子資源／資料庫（種）','種','種'),metric('ebooks','電子資源／電子書（種）','種','種'),metric('electronic_subtotal','電子資源／小計',None,basis='原表小計未另印單位，不將描述充作單位'),metric('all_holdings','總計',None,basis='原表總計混合冊、種、件，保留數值但不設統一計算單位')]
    level_grid(18,4,'全國公共圖書館館藏資源數量統計（103年）',[501.1,516.8,532.4,548.1,563.8,579.9,610.8,626.5,642.5,658.2],[174,234,297,359.5,422,483],holdings)
    county_grid(19,5,'全國公共圖書館館藏資源數量及人均擁有圖書量分析（103年）',157,310,[population,metric('book_holdings','館藏圖書冊數','冊','冊'),metric('books_per_capita','人均擁有圖書冊數（冊/件）','冊/件','冊/件',basis='照原印斜線單位保存；是人均比值，未改寫斜線含義',temporal=RATIO)],[[108,158,214,255],[335,385,440,483]],True)
    county_grid(20,5,'全國公共圖書館圖書資料使用情形（103年）',388,670,[population,metric('loans','借閱冊數','冊次',basis='原表冊數，按年度外借流量正規化冊次',temporal=FLOW),metric('borrower_visits','借閱人次','人次','人次',temporal=FLOW),metric('loans_per_capita','每人平均借閱冊數','冊次／人',basis='原表每人平均借閱冊數，按年度流量正規化；非獨立人數',temporal=RATIO)],[145,218,305,395,483])
    activity=[('reading','閱讀推廣活動'),('story','說故事'),('education_arts','社教藝文活動'),('local','地方特色活動'),('film','影片欣賞'),('other','其他'),('subtotal','小計')]
    county_grid(21,6,'全國公共圖書館推廣活動類型及辦理場次（103年）',373,657,[metric(k,l,'場次','場次',temporal=FLOW) for k,l in activity],[110,166,219,272,325,379,432,483])
    county_grid(22,7,'各縣市公共圖書館各類推廣活動參與人次（103年）',142,483,[metric(k,l,'人次','人次',temporal=FLOW) for k,l in activity],[110,175,219,282,335,388,433,483])
    county_grid(23,8,'全國公共圖書館提供新住民各類服務情形（103年）',130,471,[metric('immigrant_population','新住民人口數','人'),metric('immigrant_books','圖書（冊）','冊','冊'),metric('immigrant_periodicals','期刊（種）','種','種'),metric('immigrant_activity_events','活動（場次）','場次','場次',temporal=FLOW),metric('immigrant_activity_attendance','活動（人次）','人次','人次',temporal=FLOW)],[120,185,255,326,397,468])
    pg=page('statistics',2)
    labels=['公共圖書館（含私立）','國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市立圖書館','私立圖書館']
    for i,(y,entity) in enumerate(zip([157.6,176.1,194.6,213.1,231.6,250.2],labels),1):
        bounds=[450,483] if i==1 else [400,445]
        raw,bbox=cells_at(pg,y,bounds)[0]
        emit('statistics',2,302,199,'我國各類型圖書館數量統計表（103年）／公共圖書館完整類別組',entity,metric('library_count','圖書館數量','所',basis='同頁正文各類型數量明示所；表頭未另印'),raw,bbox,i,3 if i==1 else 2,note='公共館組含私立117所，合計647；不可當作公立530所或與表14混加。國家圖書館是另一類型，未納本子表。')
    record_table(199,'我國各類型圖書館數量統計表（103年）／公共圖書館完整類別組','statistics',[2],6,'complete public-library subtype only, including private; other library types excluded')
    basics=[metric('holdings','館藏量（冊、件）','冊、件','冊、件'),metric('loans','借閱冊數（冊）','冊次','冊',temporal=FLOW),metric('borrower_visits','借閱人次（人次）','人次','人次',temporal=FLOW),metric('seats','閱覽席位（席）','席','席')]
    pg=page('statistics',3)
    for j,(m,(raw,bbox)) in enumerate(zip(basics,cells_at(pg,167.2,[200,278,352,430,483])),2):
        emit('statistics',3,303,200,'我國各類型圖書館基本統計表（103年）／公立公共圖書館列','全國',m,raw,bbox,2,j,note='本表註腳明示公立公共館館藏包括圖書、非書及電子書，和前卷不含電子書的口徑不可硬併。')
    record_table(200,'我國各類型圖書館基本統計表（103年）／公立公共圖書館列','statistics',[3],4,'entire public-library row only; national central library separately classified and excluded')
    historical=[metric('library_count','圖書館數量','所')]+basics
    pg=page('statistics',5)
    for i,(m,y) in enumerate(zip(historical,[406.7,419.5,432.3,445.2,458.0]),1):
        for j,(raw,bbox) in enumerate(cells_at(pg,y,[130,203,275,347,419,483]),2):
            emit('statistics',5,305,202,'公立公共圖書館基本統計表（99年至103年）','全國',m,raw,bbox,i,j,year=2008+j,note='本卷重刊2010–2014五年序列；原註僅近五年年鑑統計，歷年館藏含電子書口徑未逐年重證，不套用103年表200註腳至全部五年。')
    record_table(202,'公立公共圖書館基本統計表（99年至103年）','statistics',[5],25,'complete five-year public-library table; retain publication version and historical definition uncertainty')


def validate():
    if len(ROWS)!=844: raise ValueError(('Total source positions',len(ROWS)))
    keys=[(r['source_id'],r['source_table'],r['source_row'],r['source_column']) for r in ROWS]
    if len(keys)!=len(set(keys)): raise ValueError('Duplicate source coordinate')
    # A separate word-token segmentation catches clipping and glyph-order
    # mistakes in the cell-based extractor. Table16 has touching population /
    # spending tokens, so compare whole numeric-row glyph coverage there.
    token_checks=0; row_glyph_checks=0; word_cache={}
    for r in ROWS:
        if r['source_table']=='16': continue
        kind='public-library' if r['source_id'].endswith('public-library') else 'statistics'
        key=(kind,r['source_pdf_page'])
        if key not in word_cache: word_cache[key]=words(page(*key))
        x0,y0,x1,y1=r['source_cell_bbox']
        tokens=[w for w in word_cache[key] if x0 <= (w['x0']+w['x1'])/2 < x1 and y0 <= cy(w) < y1 and N.fullmatch(w['text'])]
        if len(tokens)!=1 or tokens[0]['text']!=r['value_raw'] or tokens[0]['x0']<x0 or tokens[0]['x1']>x1:
            raise ValueError(('Independent numeric token crosscheck failed',r['source_locator'],r['value_raw'],tokens))
        token_checks+=1
    for entity in COUNTIES:
        cells=sorted([r for r in ROWS if r['source_table']=='16' and r['entity_raw']==entity],key=lambda r:r['source_column'])
        pg=page('public-library',2); x0,y0,_,y1=cells[0]['source_cell_bbox'];x1=cells[-1]['source_cell_bbox'][2]
        glyphs=[c for c in pg.chars if x0<=(c['x0']+c['x1'])/2<x1 and y0<=(c['top']+c['bottom'])/2<y1 and re.fullmatch('[0-9,.]',c['text'])]
        if ''.join(c['text'] for c in sorted(glyphs,key=lambda c:c['x0'])) != ''.join(r['value_raw'] for r in cells):
            raise ValueError(('Table16 uncovered or duplicate numeric glyph',entity))
        row_glyph_checks+=1
    # Literal values read from the PDFium originals, entered independently of
    # word extraction, cover the fragile column order and printed anomalies.
    fixed={
        (14,'合計','main',2014):'316',(14,'合計','branch',2014):'214',(14,'合計','outreach',2014):'214',
        (16,'基隆市','population',2014):'4603498',(16,'臺北市','acquisition_spending',2014):'103291228',
        (16,'連江縣','spending_per_capita',2014):'100.95',
        (17,'合計','formal_compiled',2014):'1218',(17,'合計','volunteer',2014):'10008',
        (18,'合計','all_holdings',2014):'42627572',(19,'基隆市','population',2014):'373077',
        (20,'臺北市','loans',2014):'12792546',
        (199,'公共圖書館（含私立）','library_count',2014):'647',(199,'私立圖書館','library_count',2014):'117',
        (200,'全國','holdings',2014):'42627572',(200,'全國','seats',2014):'88744',
        (23,'金門縣','immigrant_books',2014):'159',
    }
    for t,vals in [(21,[5882,2975,3254,0,2135,352,14598]),(22,[745777,42869,82524,0,58409,46120,975699])]:
        for key,v in zip(['reading','story','education_arts','local','film','other','subtotal'],vals): fixed[(t,'臺北市',key,2014)]=str(v)
    for key,v in zip(['immigrant_population','immigrant_books','immigrant_periodicals','immigrant_activity_events','immigrant_activity_attendance'],[34,0,0,0,0]): fixed[(23,'連江縣',key,2014)]=str(v)
    for key,vals in [('library_count',[536,519,521,534,530]),('holdings',[32842875,34778039,37254822,39368510,42627572]),('loans',[53980017,57348294,62904803,65423579,64910820]),('borrower_visits',[15000966,15964060,17888352,17995110,18023310]),('seats',[80060,80470,83025,86042,88744])]:
        for yr,v in zip(range(2010,2015),vals): fixed[(202,'全國',key,yr)]=str(v)
    for (t,e,k,y),v in fixed.items():
        matches=[r for r in ROWS if r['source_table']==str(t) and r['entity_raw']==e and r['metric_id']==f'table{t}_{k}' and r['data_year']==y]
        if len(matches)!=1 or Decimal(matches[0]['value'])!=Decimal(v): raise ValueError(('Image anchor failed',t,e,k,y,v,matches))
    checks=[]
    def arithmetic(name,target,parts):
        if target['value'] is None or any(r['value'] is None for r in parts):return
        total=Decimal(target['value']);summed=sum(Decimal(r['value']) for r in parts)
        c=dict(check=name,table=target['source_table'],entity=target['entity_raw'],metric_id=target['metric_id'],reported=str(total),sum_components=str(summed),matches=total==summed,source_locator=target['source_locator']);checks.append(c)
        if total!=summed:target['quality_flags'].append('source_arithmetic_difference')
    for t in [14,17,18]:
        metrics={r['metric_id'] for r in ROWS if r['source_table']==str(t)}
        for metricid in sorted(metrics):
            g=[r for r in ROWS if r['source_table']==str(t) and r['metric_id']==metricid]
            arithmetic('published_four_level_total',next(r for r in g if r['entity_raw']=='合計'),[r for r in g if r['entity_raw']!='合計'])
    for t in [21,22]:
        for entity in COUNTIES:
            g=[r for r in ROWS if r['source_table']==str(t) and r['entity_raw']==entity]
            arithmetic('printed_activity_subtotal',next(r for r in g if r['metric_id'].endswith('_subtotal')),[r for r in g if not r['metric_id'].endswith('_subtotal')])
    report=dict(reference_year=2014,edition_roc=104,publication_date='2016-07-01',long_rows=len(ROWS),
        source_ids=dict(collections.Counter(r['source_id'] for r in ROWS)),value_status_counts=dict(collections.Counter(r['value_status'] for r in ROWS)),
        zero_cells=sum(r['value'] is not None and Decimal(r['value'])==0 for r in ROWS),all_selected_tables_complete=True,
        table_count=len(TABLES),tables=TABLES,image_anchor_cells_checked=len(fixed),
        independent_word_token_cells_checked=token_checks,table16_whole_numeric_row_glyph_checks=row_glyph_checks,arithmetic_checks=checks,
        arithmetic_discrepancies=[c for c in checks if not c['matches']],
        images_reviewed=['public-library PDF pages1–8','statistics PDF pages2,3,5'],
        independent_review_limit='Producer image review of full table structure, headers and notes plus60 fixed source anchors; separate word-token or whole-row glyph checks cover all844 positions. Not an independent human full-cell double collation.',
        intentional_exclusions=['Public-library table24 construction/equipment subsidy plan; all subsequent local policy, construction, training and narrative examples; photographs.','Statistics chapter other library families, National Central Library separate type, school tables, publication industry and graphs duplicating selected tables.'],
        rights=dict(license_status='not_confirmed',license_url='https://www.ncl.edu.tw/open-government-declaration',full_originals_distribution='not_in_public_bundle',statistical_facts_only=True),
        source_caveats=['Table16 printed基隆人口4603498 differs from tables19/20 population373,077. No correction made.','Activities21/22 multi-line extracted text heading order is misleading; visual column order is authoritative.','Table199 includes private libraries; table14 and table202 public-only counts remain distinct.','Table200 holdings explicitly includes ebooks; historical table202 does not independently certify every older-year definition.','桃園縣 preserved as printed; no cross-year geography harmonization.'])
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
    for kind in ['public-library','statistics']: document(kind,args.offline)
    extract();report=validate()
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(ROWS[0]));writer.writeheader()
    for r in ROWS:writer.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    OUT.mkdir(exist_ok=True)
    # All extraction and validation complete before either final output changes.
    stable_write(OUT/'ncl_2014_long.csv',out.getvalue())
    stable_write(OUT/'ncl_2014_long.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in ROWS))
    stable_write(RAW/'extraction-validation.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for kind,m in DOCS.items():
        m.update(selected_table_metadata=[t for t in TABLES if t['document_kind']==kind],source_cells=sum(r['source_id']==m['source_id'] for r in ROWS))
    stable_write(RAW/'documents.json',json.dumps(list(DOCS.values()),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['long_rows','table_count','source_ids','value_status_counts','image_anchor_cells_checked','all_selected_tables_complete']},ensure_ascii=False))


if __name__=='__main__': main()
