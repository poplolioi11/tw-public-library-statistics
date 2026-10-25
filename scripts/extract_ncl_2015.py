#!/usr/bin/env python3
"""Coordinate extraction of the reviewed 105-edition public-library core tables.

The reference year is 104/2015, verified in chapter text and table titles;
the actual publication date is 2017-08. Full PDF/HTML snapshots remain private.
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
RAW = BASE / 'raw/ncl-2015'
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
    m = json.loads((RAW / f'yearbook-105-{kind}.metadata.json').read_text())
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
        publication_date='2017-08-01', publication_date_basis='official_entry_visible_publication_date; copyright page confirms106年8月',
        source_data_year_evidence='公共館章首明示呈現104年發展，表9–18題名104年；原統計系統讀取日105年10月13日。統計編例明示104年統計、資料取得105年7月。')
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
    # differences must not reorder digits within a single numeric line.
    return ''.join(c['text'] for c in sorted(chars, key=lambda c:c['x0'])).strip()


def cells_at(pg, y, bounds):
    return [(text_in(pg,(x0,y-5.7,x1,y+5.7)), (x0,y-5.7,x1,y+5.7)) for x0,x1 in zip(bounds,bounds[1:])]


def footnote(table):
    if table == 9: return '（1）直轄市係指臺北市、新北市、桃園市、臺中市、臺南市與高雄市。（2）館外服務站係指在圖書館外，定期提供使用者特定服務項目的據點；不包含圖書巡迴車及圖書館外的電腦連線場所。'
    if table == 10: return '（1）本表不含國立臺灣圖書館及國立公共資訊圖書館統計數據。（2）直轄市總館部分，臺中市總館35所為所轄各行政區圖書館總館；另臺南市總館43所為臺南市立圖書館及各區公所所轄之區圖書館總館館數。'
    if table in {11,14,15,16,17,18}: return '本表不含國立臺灣圖書館及國立公共資訊圖書館統計數據。'
    if table == 143: return '資料整理自國家圖書館「全國圖書館調查統計系統」http://libstat.ncl.edu.tw/statFront/'
    if table == 144: return '（1）國家圖書館及公立公共圖書館館藏量，包含圖書、非書資料及電子書。（3）公立公共圖書館統計，檢自國立公共資訊圖書館「公共圖書館統計系統」2015年度彙整結果。'
    if table == 146: return '資料整理自近五年《中華民國圖書館年鑑》之「圖書館統計」專題。'
    return None


def emit(kind, pno, printed, table, title, entity, metric, raw, bbox, row, col, year=2015, note='', role=None):
    # metric: id, literal heading (with hierarchy), normalized unit, raw printed
    # unit, unit basis, temporal kind. Descriptions never become units.
    m = DOCS[kind]; key,label,unit,unit_raw,unit_basis,temporal = metric
    unit_candidate=unit if table==17 else None
    unit_status='source_heading_conflict_unresolved' if table==17 else 'printed_unit' if unit_raw else 'contextual_unit_inference' if unit else 'no_uniform_unit_reported'
    if table==17: unit=None
    parsed,status = value(raw)
    entity_kind = 'county' if entity in COUNTIES else 'national_total' if entity in {'全國','合計'} else 'library_level_or_ownership_class'
    uncertain_alignment = table in {10,11,14,15,16,17,18} and 3<=row<=7
    duplicate_label = table in {15,18} and row in {21,22}
    if uncertain_alignment: entity_kind='county_source_label_uncertain'
    if duplicate_label: entity_kind='county_source_label_duplicate_unresolved'
    scope = ('excluded_from_county_published_total' if table in {10,11,14,15,16,17,18} and entity=='合計' else
        'excluded_from_county_metrics' if entity in COUNTIES else
        'public_libraries_including_private' if table==143 and entity=='公共圖書館（含私立）' else
        'private_ownership_only' if table==143 and entity=='私立圖書館' else
        'separate_national_public_library_level' if entity in {'國立級圖書館','國立圖書館'} else
        'excluded_from_non_national_level_components' if entity_kind=='library_level_or_ownership_class' else
        'included_in_published_national_total' if entity=='合計' else
        'public_libraries_including_two_national_public_libraries_excluding_National_Central_Library')
    if role is None: role = 'derived_ratio' if temporal==RATIO else 'published_total' if entity_kind=='national_total' or key in {'formal_subtotal','informal_subtotal','physical_subtotal','electronic_subtotal','all_holdings','all_facilities','subtotal'} or entity=='公共圖書館（含私立）' else 'reported_component'
    start,end = (f'{year}-01-01',f'{year}-12-31') if temporal in {FLOW,'annual_financial'} else (None,None)
    locator = f'PDF page {pno}; printed page {printed}; table {table}; data row {row}; column {col}; bbox ' + ','.join(f'{v:.2f}' for v in bbox)
    notes = [note] if note else []
    flags = ['published_total_overlaps_components'] if role=='published_total' else []
    interpretation_basis='按原刊數值、欄列與明印資料年保存，未自行改原值或重配縣市。'
    label_status='printed_source_label_retained'
    if table in {16,17}: notes.append('欄序依PDFium原件影像：閱讀推廣、說故事、社教藝文、地方特色、影片欣賞、其他、小計；不可按extract_text多行欄頭輸出順序配數字。')
    if uncertain_alignment:
        notes.append('原刊縣市資料列3–7疑似與名稱錯列：表10註腳稱臺中總館35、臺南43，但數值印於臺南35、高雄43列；同卷數張核心表標籤亦有相應疑義。此處照原印列名及原值保存，未將數值改配桃園／臺中／臺南／高雄／基隆。')
        flags.append('source_geography_label_alignment_suspect_unreassigned');label_status='source_label_alignment_suspect_unreassigned'
    if duplicate_label:
        notes.append('本表末兩個縣市資料列原件均印金門縣（第21及22列），未印連江縣。保留兩列及各自來源座標，不猜改第22列為連江。')
        flags.append('duplicate_printed_geography_label');label_status='duplicate_printed_geography_label_unresolved'
    if table==9 and key=='all_facilities':
        notes.append('本列加總總館、分館、閱覽室及館外服務站，合計1,219不是公立圖書館總分館536所。');flags.append('includes_reading_rooms_and_outreach_not_library_main_branch_count')
    if table==13 and key in {'physical_subtotal','electronic_subtotal','all_holdings'}:
        notes.append('原表跨冊、種、件小計／總計原值保留，未給統一計算單位。')
    if table==13 and key=='nonbook':
        notes.append('原件非書資料行五個數值全部與上一圖書資料小計相同（總計43,293,799），但同頁／前頁正文稱非書1,594,608件；保留原印行，不用正文或總計反算覆寫。')
        flags.append('source_nonbook_row_duplicates_physical_subtotal')
    if table==17:
        interpretation_basis='原表題名印「辦理場次」，但印62頁（PDF4）敘述各縣市推廣活動共90,643場、參與17,151,036人並指表16/17；表17合計17,151,036與人次相符。正文支持人次候選，惟原題單位衝突未解，unit留空；原題及原印場次保留。'
        notes.append(interpretation_basis);flags.append('source_title_unit_conflict')
    if ',' in raw and not re.fullmatch(r'[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?',raw):
        notes.append('原刊數字分節逗點不規則；只移除分節逗點解析，保留全部數字與原始字串，不移位或補數字。');flags.append('source_nonstandard_digit_grouping')
    if entity=='桃園縣': notes.append('2015原刊仍印桃園縣，而本卷表9註腳印桃園市；保留原名與疑義，不重分類。');flags.append('source_historical_geography_name_retained')
    r=dict(data_year=year,entity_raw=entity,entity_contextual_name=entity,entity_kind=entity_kind,
        geography_vintage=f'{year} original published geography; 桃園縣 retained where printed',national_libraries_scope=scope,
        metric_id=f'table{table}_{key}',metric_raw=label,value_raw=raw,value=parsed,unit=unit,unit_raw=unit_raw,unit_basis=unit_basis,
        unit_status=unit_status,unit_interpretation_candidate=unit_candidate,
        temporal_kind=temporal,value_status=status,source_id=m['source_id'],source_url=m['source_page_url'],source_download_url=m['source_download_url'],
        source_sha256=m['sha256'],source_local_path=m['source_local_path'],source_agency='國家圖書館',source_retrieved_at=m['source_retrieved_at'],
        source_pdf_page=pno,source_printed_page=str(printed),source_table=str(table),source_row=row,source_column=col,source_locator=locator,
        raw_extracted_line=raw,extraction_status='PDFium_reviewed_headers_and_footnotes_coordinate_cells',license_status='not_confirmed',license_url=m['license_url'],
        publication_date='2017-08-01',publication_date_basis=m['publication_date_basis'],source_edition='105',source_edition_roc=105,
        table_title_raw=title.split('／')[0],source_table_title=title.split('／')[0],source_selection_title=title,source_title='中華民國105年圖書館年鑑／'+('公共圖書館' if kind=='public-library' else '圖書館統計'),
        population_scope='公立公共圖書館；表143公共館組含私立，按各表註腳分開',period_raw=f'{year-1911}年（原表明列資料年）',
        period_start=start,period_end=end,notes='；'.join(notes),cell_annotation='',cell_bbox=[round(v,3) for v in bbox],
        source_cell_bbox=[round(v,3) for v in bbox],source_cell_bbox_kind='reviewed_numeric_row_band_and_column_bounds',
        snapshot_distribution='not_in_public_bundle',aggregation_role=role,institutional_level=entity if entity_kind=='library_level_or_ownership_class' else '原表各層級合計',
        source_column_path=entity if table in {9,12,13} else label,source_version_id=m['source_id']+':'+m['sha256'],source_data_year_raw=f'{year-1911}年',
        scope_note=scope,time_reference=f'{year}年全年' if start else f'原表民國{year-1911}年；未明示精確時點，不以卷號、出版日、上網日補日期',
        quality_flags=flags,source_footnotes_raw=footnote(table),source_footnotes_status='table_specific_relevant_original_excerpts_whitespace_normalized' if footnote(table) else 'no_table_specific_note_printed',
        source_original_access_date_raw='105年10月13日' if kind=='public-library' else None,
        source_data_obtained_date_raw='105年7月（統計章編例）' if kind=='statistics' else None,
        observation_identity_suffix='row:'+str(row),entity_label_status=label_status,interpretation_basis=interpretation_basis,
        parse_rule='strip_original_thousands_separators_preserve_all_digits',
        original_fields={'entity':entity,'metric':label,'value_raw':raw,'table_title':title.split('／')[0],'unit_raw':unit_raw,'source_data_row':row})
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
        for j,(entity,(raw,bbox)) in enumerate(zip(LEVELS,cells),2): emit('public-library',pno,58+pno,table,title,entity,m,raw,bbox,i,j)
    record_table(table,title,'public-library',[pno],len(metrics)*5,'entire numeric grid; four public-library levels and published total')


def county_grid(table,pno,title,y0,y1,metrics,bounds,split=False,label_x=(0,115)):
    pg=page('public-library',pno)
    expected=COUNTIES+['合計']
    if table in {15,18}: expected=COUNTIES[:-1]+['金門縣','合計']
    labels=[w for w in words(pg) if w['text'] in set(expected) and y0<cy(w)<y1 and (label_x[0]<=w['x0']<label_x[1] or split and 280<w['x0']<330)]
    labels.sort(key=lambda w:(w['x0']>280,cy(w)))
    if [w['text'] for w in labels] != expected: raise ValueError(('Printed county data rows changed',table,[w['text'] for w in labels],expected))
    for i,w in enumerate(labels,1):
        b=bounds[1] if split and w['x0']>280 else bounds[0] if split else bounds
        for j,(m,(raw,bbox)) in enumerate(zip(metrics,cells_at(pg,cy(w)+.15,b)),2):
            emit('public-library',pno,58+pno,table,title,w['text'],m,raw,bbox,i,j,note='原表分左右續表，資料列依左表後右表的順序編號，包含原刊合計列。' if split else '')
    record_table(table,title,'public-library',[pno],23*len(metrics),'all 22 printed county-position rows plus published total; source labels are not corrected or reassigned; excludes two national public libraries by printed note')


def extract():
    counts=[metric('main','總館（所）','所','所'),metric('branch','分館（所）','所','所'),metric('reading_room','閱覽室（所）','所','所'),metric('outreach','館外服務站（所）','所','所'),metric('all_facilities','合計','所',basis='原表四種設施相加；含閱覽室及館外服務站，非總館加分館數')]
    level_grid(9,1,'全國公共圖書館數量統計―依圖書館隸屬層級（104年）',[595.3,609.2,623.2,637.2,651.1],[180,238,300,363,425,483],counts)
    county_grid(10,2,'全國公共圖書館數量統計―依縣市別（104年）',140,460,[metric(k,l,'所',basis='同章表9相同設施欄明印所，表10本身未另印') for k,l,*_ in counts[:4]],[340,370,405,437,483],label_x=(280,333))
    population=metric('population','人口數','人')
    spending=[population,metric('acquisition_spending','圖書資料購置經費','新臺幣元',basis='同章印60頁年度統計明述新臺幣及元，表11欄頭未印貨幣單位',temporal='annual_financial'),metric('spending_per_capita','每人平均購書經費','新臺幣元／人',basis='同章印60頁明述每人平均分配購書經費及元，表11欄頭未印貨幣單位',temporal=RATIO)]
    county_grid(11,3,'全國公共圖書館圖書資料購置經費及人均購書經費分析（104年）',155,475,spending,[104,154.5,215,259])
    staff=[metric(k,l,'人',basis='同章印60頁人力資源段明示人員人數；表12欄頭未另印人') for k,l in [('formal_compiled','正式人力／編制內人員'),('contract','正式人力／約聘雇人員'),('temporary','正式人力／臨時人員'),('formal_subtotal','正式人力／小計'),('student','非正式人力／工讀生'),('volunteer','非正式人力／志工'),('other','非正式人力／其他'),('informal_subtotal','非正式人力／小計')]]
    level_grid(12,3,'全國公共圖書館人力資源統計（104年）',[578.5,592.5,606.5,620.9,648.4,662.4,676.3,690.8],[195,250,311,372,432,483],staff)
    holdings=[metric('books','圖書資料／圖書（冊）','冊','冊'),metric('periodicals','圖書資料／期刊（種）','種','種'),metric('newspapers','圖書資料／報紙（種）','種','種'),metric('other_physical','圖書資料／其他（件）','件','件'),metric('physical_subtotal','圖書資料／小計',None,basis='原表混合冊、種、件小計，未印統一單位'),metric('nonbook','非書資料／非書資料（件）','件','件'),metric('databases','電子資源／資料庫（種）','種','種'),metric('ebooks','電子資源／電子書（種）','種','種'),metric('electronic_subtotal','電子資源／小計',None,basis='原表小計未另印單位，不將描述充作單位'),metric('all_holdings','總計',None,basis='原表總計混合冊、種、件，不設統一計算單位')]
    level_grid(13,4,'全國公共圖書館館藏資源數量統計（104年）',[501.5,517.1,532.8,548.5,564.6,595.5,626.9,642.6,658.6,674.3],[174,235,298,360.5,423,483],holdings)
    county_grid(14,5,'全國公共圖書館館藏資源數量及人均擁有圖書量分析（104年）',157,310,[population,metric('book_holdings','館藏圖書冊數','冊','冊'),metric('books_per_capita','人均擁有圖書冊數（冊/件）','冊/件','冊/件',basis='照原印斜線單位保存；人均比值，不改寫斜線含義',temporal=RATIO)],[[104,158,215,255],[325,379,440,483]],True)
    county_grid(15,5,'全國公共圖書館圖書資料使用情形（104年）',390,685,[population,metric('loans','借閱冊數','冊次',basis='原表冊數，按年度外借流量正規化冊次',temporal=FLOW),metric('borrower_visits','借閱人次','人次','人次',temporal=FLOW),metric('loans_per_capita','每人平均借閱冊數','冊次／人',basis='原表每人平均借閱冊數，按年度流量正規化',temporal=RATIO)],[145,218,305,395,483])
    activity=[('reading','閱讀推廣活動'),('story','說故事'),('education_arts','社教藝文活動'),('local','地方特色活動'),('film','影片欣賞'),('other','其他'),('subtotal','小計')]
    county_grid(16,6,'全國公共圖書館推廣活動類型及辦理場次（104年）',368,664,[metric(k,l,'場次','場次',temporal=FLOW) for k,l in activity],[110,166,219,272,325,379,432,483])
    county_grid(17,7,'全國公共圖書館推廣活動類型及辦理場次（104年）',142,498,[metric(k,l,'人次','場次',basis='原題印場次；印62頁正文與表17總量17,151,036支持參與人次候選，但原題衝突未解。unit留空、原題不覆寫，另存candidate及interpretation_basis',temporal=FLOW) for k,l in activity],[110,175,219,272,335,388,429,483])
    county_grid(18,8,'全國公共圖書館提供新住民各類服務情形（104年）',130,487,[metric('immigrant_population','新住民人口數','人'),metric('immigrant_books','圖書（冊）','冊','冊'),metric('immigrant_periodicals','期刊（種）','種','種'),metric('immigrant_activity_events','活動（場次）','場次','場次',temporal=FLOW),metric('immigrant_activity_attendance','活動（人次）','人次','人次',temporal=FLOW)],[120,185,255,326,397,468])
    pg=page('statistics',2)
    labels=['公共圖書館（含私立）','國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市立圖書館','私立圖書館']
    for i,(y,entity) in enumerate(zip([157.6,176.1,194.6,213.1,231.6,250.2],labels),1):
        bounds=[440,483] if i==1 else [395,435]
        raw,bbox=cells_at(pg,y,bounds)[0]
        emit('statistics',2,348,143,'我國各類型圖書館數量統計表（104年）／公共圖書館完整類別組',entity,metric('library_count','圖書館數量','所',basis='同頁正文各類型數量明示所；表頭未另印'),raw,bbox,i,3 if i==1 else 2,note='公共館組含私立80所，合計616；不可當公立536所。國家圖書館為另一類型，不納本子表。')
    record_table(143,'我國各類型圖書館數量統計表（104年）／公共圖書館完整類別組','statistics',[2],6,'complete public-library subtype, including private; other library types excluded')
    basics=[metric('holdings','館藏量（冊、件）','冊、件','冊、件'),metric('loans','借閱冊數（冊）','冊次','冊',temporal=FLOW),metric('borrower_visits','借閱人次（人次）','人次','人次',temporal=FLOW),metric('seats','閱覽席位（席）','席','席')]
    pg=page('statistics',3)
    for j,(m,(raw,bbox)) in enumerate(zip(basics,cells_at(pg,167.2,[190,263,337,418,483])),2):
        emit('statistics',3,349,144,'我國各類型圖書館基本統計表（104年）／公立公共圖書館列','全國',m,raw,bbox,2,j,note='本表明示公立公共館館藏含圖書、非書及電子書；不與排除電子書版本硬併。')
    record_table(144,'我國各類型圖書館基本統計表（104年）／公立公共圖書館列','statistics',[3],4,'entire public-library row only; excludes separate National Central Library type')
    historical=[metric('library_count','圖書館數量','所')]+basics
    pg=page('statistics',5)
    for i,(m,y) in enumerate(zip(historical,[397.5,416.3,435.1,448,460.8]),1):
        for j,(raw,bbox) in enumerate(cells_at(pg,y,[130,203,275,347,419,483]),2):
            emit('statistics',5,351,146,'公立公共圖書館基本統計表（100年至104年）','全國',m,raw,bbox,i,j,year=2009+j,note='本卷重刊2011–2015五年序列；原註近五年年鑑統計，未逐年重證舊年電子書口徑，不套104年表144註腳至全部五年。')
    record_table(146,'公立公共圖書館基本統計表（100年至104年）','statistics',[5],25,'complete five-year public-library table; retain this publication version and historical definition uncertainty')


def validate():
    if len(ROWS)!=909: raise ValueError(('Total source positions',len(ROWS)))
    keys=[(r['source_id'],r['source_table'],r['source_row'],r['source_column']) for r in ROWS]
    if len(keys)!=len(set(keys)): raise ValueError('Duplicate source coordinate')
    token_checks=0; word_cache={}
    for r in ROWS:
        kind='public-library' if r['source_id'].endswith('public-library') else 'statistics'
        key=(kind,r['source_pdf_page'])
        if key not in word_cache: word_cache[key]=words(page(*key))
        x0,y0,x1,y1=r['source_cell_bbox']
        tokens=[w for w in word_cache[key] if x0 <= (w['x0']+w['x1'])/2 < x1 and y0 <= cy(w) < y1 and N.fullmatch(w['text'])]
        if len(tokens)!=1 or tokens[0]['text']!=r['value_raw'] or tokens[0]['x0']<x0 or tokens[0]['x1']>x1:
            raise ValueError(('Separate numeric word-token crosscheck failed',r['source_locator'],r['value_raw'],tokens))
        if r['observation_identity_suffix']!='row:'+str(r['source_row']): raise ValueError('Missing row identity suffix')
        if r['source_table']=='17' and not (r['unit'] is None and r['unit_raw']=='場次' and r['unit_status']=='source_heading_conflict_unresolved' and r['unit_interpretation_candidate']=='人次'):
            raise ValueError('Unresolved source title-unit conflict was promoted to an accepted unit')
        token_checks+=1
    fixed={(9,1,6):309,(9,2,6):227,(9,3,6):455,(9,4,6):228,(9,5,6):1219,
        (10,3,2):2,(10,4,2):35,(10,5,2):43,(10,23,2):307,(10,23,3):224,
        (11,6,3):74044257,(11,23,2):23492074,(11,23,3):545123438,
        (12,1,6):1234,(12,6,6):10777,(12,8,6):12171,
        (13,5,6):43293799,(13,6,6):43293799,(13,10,6):45211354,
        (14,23,3):42146109,(15,21,2):132799,(15,22,2):12547,(15,23,3):66151791,
        (143,1,3):616,(143,6,2):80,(144,2,2):45211354,(144,2,5):93237}
    for table,vals in [(16,[4881,2713,3646,0,2338,2345,15923]),(17,[797043,39404,105644,0,65359,131343,1138793])]:
        for c,v in enumerate(vals,2): fixed[(table,1,c)]=v
    for c,v in enumerate([10092638,526273,4042953,1323012,339830,826330,17151036],2):fixed[(17,23,c)]=v
    for c,v in enumerate([46,0,0,0,0],2):fixed[(18,22,c)]=v
    history=[[519,521,534,530,536],[34778039,37254822,39368510,42627572,45211354],[57348294,62904803,65423579,64910820,69223451],[15964060,17888352,17995110,18023310,20369651],[80470,83025,86042,88744,93237]]
    for row,vs in enumerate(history,1):
        for col,v in enumerate(vs,2): fixed[(146,row,col)]=v
    for (t,row,col),v in fixed.items():
        matches=[r for r in ROWS if r['source_table']==str(t) and r['source_row']==row and r['source_column']==col]
        if len(matches)!=1 or Decimal(matches[0]['value'])!=Decimal(v): raise ValueError(('Image anchor failed',t,row,col,v,matches))
    # Both original金門 labels and all row-based identities must survive.
    for table in [15,18]:
        for row in [21,22]:
            group=[r for r in ROWS if r['source_table']==str(table) and r['source_row']==row]
            if not group or any(r['entity_raw']!='金門縣' or 'duplicate_printed_geography_label' not in r['quality_flags'] for r in group):raise ValueError('Printed duplicate county label was corrected or collapsed')
        if any(r['entity_raw']=='連江縣' for r in ROWS if r['source_table']==str(table)):raise ValueError('Unprinted連江 label invented')
    checks=[]
    def arithmetic(name,target,parts):
        if target['value'] is None or any(r['value'] is None for r in parts):return
        total=Decimal(target['value']);summed=sum(Decimal(r['value']) for r in parts)
        c=dict(check=name,table=target['source_table'],entity=target['entity_raw'],source_row=target['source_row'],metric_id=target['metric_id'],reported=str(total),sum_components=str(summed),matches=total==summed,source_locator=target['source_locator']);checks.append(c)
        if total!=summed:target['quality_flags'].append('source_arithmetic_difference')
    for t in [9,12,13]:
        metrics={r['metric_id'] for r in ROWS if r['source_table']==str(t)}
        for metricid in sorted(metrics):
            g=[r for r in ROWS if r['source_table']==str(t) and r['metric_id']==metricid]
            arithmetic('published_four_level_total',next(r for r in g if r['entity_raw']=='合計'),[r for r in g if r['entity_raw']!='合計'])
    for t in [16,17]:
        for source_row in range(1,24):
            g=[r for r in ROWS if r['source_table']==str(t) and r['source_row']==source_row]
            arithmetic('printed_activity_row_subtotal',next(r for r in g if r['metric_id'].endswith('_subtotal')),[r for r in g if not r['metric_id'].endswith('_subtotal')])
    for t in [10,11,14,15,16,17,18]:
        metrics=sorted({r['metric_id'] for r in ROWS if r['source_table']==str(t) and r['temporal_kind']!=RATIO})
        for metricid in metrics:
            g=[r for r in ROWS if r['source_table']==str(t) and r['metric_id']==metricid]
            arithmetic('printed_total_all_22_source_positions_not_reassigned',next(r for r in g if r['source_row']==23),[r for r in g if r['source_row']!=23])
    for entity in LEVELS:
        g={r['metric_id'].split('_',1)[1]:r for r in ROWS if r['source_table']=='13' and r['entity_raw']==entity}
        arithmetic('printed_holdings_total_vs_printed_subtotals',g['all_holdings'],[g[k] for k in ['physical_subtotal','nonbook','electronic_subtotal']])
    inventory=[]
    for t in [10,11,14,15,16,17,18]:
        g=[r for r in ROWS if r['source_table']==str(t) and r['source_column']==2]
        labels=[r['entity_raw'] for r in g if r['source_row']!=23]
        inventory.append(dict(table=t,printed_county_position_rows=len(labels),unique_county_labels=len(set(labels)),
            printed_labels=labels,duplicates={k:v for k,v in collections.Counter(labels).items() if v>1},
            labels_not_printed_from_original_22_list=sorted(set(COUNTIES)-set(labels)),
            unresolved_alignment_rows=[r['source_row'] for r in g if r['entity_label_status']=='source_label_alignment_suspect_unreassigned']))
    report=dict(reference_year=2015,edition_roc=105,publication_date='2017-08-01',long_rows=len(ROWS),
        source_ids=dict(collections.Counter(r['source_id'] for r in ROWS)),value_status_counts=dict(collections.Counter(r['value_status'] for r in ROWS)),
        zero_cells=sum(r['value'] is not None and Decimal(r['value'])==0 for r in ROWS),all_selected_tables_complete=True,
        table_count=len(TABLES),tables=TABLES,image_anchor_cells_checked=len(fixed),independent_word_token_cells_checked=token_checks,
        identity_suffix_rows_checked=len(ROWS),printed_county_label_inventory=inventory,quality_flag_counts=dict(collections.Counter(f for r in ROWS for f in r['quality_flags'])),
        arithmetic_checks=checks,arithmetic_discrepancies=[c for c in checks if not c['matches']],
        images_reviewed=['public-library PDF pages1–8','statistics PDF pages2,3,5'],
        independent_review_limit='Producer image review of full selected table structure, headers and notes with fixed literal source anchors; separate word-token checks cover all909 positions. Not an independent human full-cell double collation.',
        intentional_exclusions=['Public-library table19 construction/equipment subsidy plan and all subsequent local policy, construction, training/narrative examples and photographs.','Statistics chapter other library families, National Central Library separate type, school tables, publication industry and graphs duplicating selected tables.'],
        rights=dict(license_status='not_confirmed',license_url='https://www.ncl.edu.tw/open-government-declaration',full_originals_distribution='not_in_public_bundle',statistical_facts_only=True),
        source_caveats=['Tables15/18 print two金門縣 rows and no連江縣 label; both rows and original coordinates preserved with row identity suffix, no inferred correction.','Printed county-position rows3–7 in tables10/11/14/15/16/17/18 have internal label-alignment concerns; values remain assigned only to their printed labels and flagged uncertain.','Table17 original title says場次 while narrative and17151036total support參與人次 only as a candidate; unit remainsnull, conflict unresolved, original title/rawunit retained.','Table13 nonbook row duplicates physical subtotal across all five columns, contrary to narrative1594608; no invented corrected row.','Table11基隆 acquisition原印7,4044,257, exact digit-preserving parse74044257; nonstandard comma grouping flagged.','Table9 all-facilities total1219 includes reading rooms/outreach; public-library main+branch count is536.','Table143 includes private80, so616 is not public-only536.','Table144 holdings includes ebooks; historical table146 does not independently certify every older-year definition.','桃園縣 preserved as printed; table9 note says桃園市. No geographic harmonization or silent reassignment.'])
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
    for kind in ['public-library','statistics']: document(kind,args.offline)
    extract();report=validate()
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=list(ROWS[0]));writer.writeheader()
    for r in ROWS:writer.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    OUT.mkdir(exist_ok=True)
    # All extraction and validation complete before either final output changes.
    stable_write(OUT/'ncl_2015_long.csv',out.getvalue())
    stable_write(OUT/'ncl_2015_long.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in ROWS))
    stable_write(RAW/'extraction-validation.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for kind,m in DOCS.items():
        m.update(selected_table_metadata=[t for t in TABLES if t['document_kind']==kind],source_cells=sum(r['source_id']==m['source_id'] for r in ROWS))
    stable_write(RAW/'documents.json',json.dumps(list(DOCS.values()),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['long_rows','table_count','source_ids','value_status_counts','image_anchor_cells_checked','all_selected_tables_complete']},ensure_ascii=False))


if __name__=='__main__': main()
