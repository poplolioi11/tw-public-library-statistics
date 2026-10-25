#!/usr/bin/env python3
"""Reproduce image-reviewed, coordinate-based NCL yearbook core tables.

101/102/103 editions cover reference years 2011/2012/2013. Uses only explicitly
linked official chapter PDFs retained privately. No PDF, HTML, image or narrative
text is licensed for redistribution by this extraction. Statistical facts only.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,unicodedata
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.request import Request,urlopen
import pdfplumber

BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'raw/ncl-additional'
DERIVED=BASE/'derived'
COUNTIES_2011=['新北市','臺北市','臺中市','臺南市','高雄市','宜蘭縣','桃園縣','新竹縣','苗栗縣','彰化縣','南投縣','雲林縣','嘉義縣','屏東縣','臺東縣','花蓮縣','澎湖縣','基隆市','新竹市','嘉義市','金門縣','連江縣']
COUNTY_SET=set(COUNTIES_2011)
NATIONAL_2011=['國立中央圖書館臺灣分館','國立臺中圖書館','臺灣省政府圖書館']
LEVELS=['國立級圖書館','直轄市級圖書館','縣市級圖書館','鄉鎮市區級圖書館','合計']
NUMBER=re.compile(r'^([0-9][0-9,]*(?:\.[0-9]+)?)([a-z*]*)$')
DOCUMENTS={}
PAGES={}
ROWS=[]
CELLS=[]
TABLES=[]
CHECKS=[]


def utc():return datetime.now(timezone.utc).isoformat()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def doc(edition,kind,offline):
    key=(edition,kind)
    if key in DOCUMENTS:return DOCUMENTS[key]
    metadata=RAW/f'yearbook-{edition}-{kind}.metadata.json'
    if not metadata.exists():raise FileNotFoundError('Official entry discovery metadata required: '+str(metadata))
    m=json.loads(metadata.read_text());path=RAW/f'yearbook-{edition}-{kind}.pdf'
    if not path.exists():
        if offline:raise FileNotFoundError(path)
        with urlopen(Request(m['source_download_url'],headers={'User-Agent':'Taiwan-public-library-statistics/source-linked-research'}),timeout=45) as response:b=response.read()
        if not b.startswith(b'%PDF'):raise ValueError('Official linked resource is not PDF')
        if hashlib.sha256(b).hexdigest()!=m['sha256']:raise ValueError('Source changed; requires new image review before accepting revision')
        path.write_bytes(b)
    if digest(path)!=m['sha256']:raise ValueError('Private original SHA mismatch: '+str(path))
    m.update(source_local_path=str(path.relative_to(BASE)),source_edition=str(edition),source_edition_roc=edition,license_status='not_confirmed',
             license_evidence='Official chapter is publicly downloadable; signed chapter full-text open licence has not been confirmed. PDFs retained privately; statistical facts only.',
             snapshot_distribution='not_in_public_bundle')
    DOCUMENTS[key]=m
    return m

def page(edition,kind,index,offline):
    key=(edition,kind,index)
    if key not in PAGES:
        m=doc(edition,kind,offline)
        pdf=pdfplumber.open(BASE/m['source_local_path'])
        PAGES[key]=(pdf,pdf.pages[index].dedupe_chars(tolerance=0.35))
    return PAGES[key][1]

def words(pg):return pg.extract_words(x_tolerance=1,y_tolerance=2,keep_blank_chars=False)
def center(w):return (w['top']+w['bottom'])/2

def cell_text(pg,bbox):
    x0,y0,x1,y1=bbox
    chars=[c for c in pg.chars if x0+0.2<=(c['x0']+c['x1'])/2<x1-0.2 and y0+0.1<=(c['top']+c['bottom'])/2<y1-0.1]
    if not chars:return ''
    lines=[]
    for c in sorted(chars,key=lambda c:(c['top'],c['x0'])):
        cy=(c['top']+c['bottom'])/2
        hit=next((line for line in lines if abs(line[0]-cy)<3.5),None)
        if hit is None:lines.append([cy,[c]])
        else:hit[1].append(c)
    return ' '.join(''.join(c['text'] for c in sorted(line[1],key=lambda c:c['x0'])) for line in sorted(lines,key=lambda x:x[0])).strip()

def numeric(raw):
    raw=raw.strip();token=unicodedata.normalize('NFKC',raw);token=re.sub(r'\s+','',token)
    if not token:return None,'blank_in_source',''
    if token in {'-','－','—','…','...','N/A','NA'}:return None,'not_available_in_source',''
    match=NUMBER.fullmatch(token)
    if not match:raise ValueError('Unexpected nonnumeric cell: '+repr(raw))
    return str(Decimal(match.group(1).replace(',',''))),'reported_decimal' if '.' in match.group(1) else 'reported',match.group(2)

def unit_contract(edition,kind,table,metric):
    key,label,unit,_=metric
    # Explicit unit text and normalized interpretive unit are separate. Never
    # call a contextual count unit a unit actually printed in this cell header.
    if table in {19,20,32,33,40,157,169,151,154}:
        return None,'依同章類型／數量文義推定；本表欄頭未另明印單位。館數以所、人力以人、席位以席標準化；不代表原表明印。'
    if table==31:return '所','原表列名明印「總館（所）／分館（所）／館外服務站（所）」'
    if table==34:
        match=re.search(r'（([^）]+)）',label)
        return (match.group(1),'原表列名括號明印單位') if match else (None,'原表上層小計／總計未明印統一單位；原分項使用冊、種、件，不能宣稱全為冊。')
    if table in {21,22}:
        match=re.search(r'（([^）]+)）',label)
        return (match.group(1),'原表欄頭括號明印；冊次及每人標準化解讀另保留原單位') if match else (None,'由原表欄頭文義推定')
    if table==35:
        if key=='books_per_capita':return '冊/件','原表「人均擁有圖書冊數（冊/件）」欄頭；原印斜線語義不改寫為單純冊。'
        return ('冊','原表「館藏圖書冊數」明示冊') if key=='book_holdings' else (None,'原表「人口數」文義推定為人；未另印括號單位。')
    if table==36:
        return None,'依原表圖書資料購置經費及人均購書費之文義；新臺幣元及元／人為標準化解讀，未宣稱原表明印。'
    if table==37:
        return None,'依欄頭人口數／外借冊數／借閱人次／每人平均借閱冊數文義；冊次為流量標準化單位，不冒充原印單位。'
    if table in {38,39}:return ('場次' if table==38 else '人次'),'原表標題明示統計量（場次／人次）。'
    if table in {170,152,155}:
        raw={'holdings':'冊、件','seats':'席','borrower_visits':'人次','loans':'冊'}[key]
        return raw,'原表基本統計欄頭明印括號單位；借閱冊次為流量標準化解讀。'
    return None,'單位尚待逐表認證；保留正規化文義解讀。'


def emit(edition,kind,pdfpage,printed,table,title,entity,metric,raw,bbox,row,column,*,year=None,scope=None,note='',offline=True):
    # metric=(stable table-local ID, original label, original unit, temporal kind)
    m=doc(edition,kind,offline);value,status,annotation=numeric(raw);reference_year=year or edition+1910
    raw_title=title.split('／公共圖書館')[0].split('／公立公共圖書館')[0]
    if table==170:raw_title=raw_title.replace('基本統計表','基本資料統計表')
    if table in {170,152,155} and metric[0]=='holdings':metric=(metric[0],('館藏量' if table==155 else '館藏圖書冊數')+'（冊、件）',metric[2],metric[3])
    entity_kind='county' if entity in COUNTY_SET else 'national_total' if entity in {'總計','全國','合計'} else 'public_library_institution' if entity in NATIONAL_2011 else 'library_level_or_ownership_class'
    if scope is None:
        scope='included_in_national_total' if entity_kind=='national_total' else 'separate_institution' if entity_kind=='public_library_institution' else 'table_specific_scope_not_fully_certified'
    if metric[3] in {'flow_calendar_year','annual_financial'}:start=f'{reference_year}-01-01';end=f'{reference_year}-12-31'
    else:start=None;end=None
    locator=f'PDF page {pdfpage}; printed page {printed}; table {table}; data row {row}; column {column}; bbox '+','.join(f'{v:.2f}' for v in bbox)
    unit_raw,unit_basis=unit_contract(edition,kind,table,metric)
    footnotes={
        19:'資料來源：公共圖書館統計系統。上網日期：101年7月15日。',
        20:'每位館員平均服務人口數＝（各縣市總人口數÷縣市內各層級公共圖書館編制內總館員數）。資料來源：公共圖書館統計系統、內政統計年報。上網日期：101年7月15日。',
        21:'平均每人擁書量＝（縣市內各層級公共圖書館總館藏量－含圖書資料、非書資料及電子資源÷各縣市總人口數）；平均每人購書經費＝（縣市內各層級公共圖書館圖書資料購置費加總÷各縣市總人口數）；平均每人借閱量＝（縣市內各層級公共圖書館總借閱冊數÷各縣市總人口數）。上網日期：101年7月15日。',
        22:'資料來源：公共圖書館統計系統。上網日期：101年7月15日。',
        31:'直轄市係指臺北市、新北市、臺中市、臺南市及高雄市。臺北市、新北市及高雄市，皆設有總館1所，分館及館外服務站若干所；臺中市統計總館計34所，係指其所轄行政區設置之區圖書館總館館數；臺南市統計總館計42所，除臺南市立圖書館總館外，包含各行政區所設置之館舍總館館數。',
    }.get(table)
    if table in {32,35,36,37,38,39,40}:footnotes='註：本表統計數據不含國立臺灣圖書館及國立公共資訊圖書館。'
    if table in {170,152,155}:footnotes='館藏包含圖書及非書資料，但不含電子書。公共圖書館統計不含私立公共圖書館。'
    if table==169:footnotes='公立公共圖書館數包括分館，資料來源：國立臺中圖書館，〈2011年度彙整結果〉。「公共圖書館統計系統」。網址：http://publibstat.ntl.gov.tw/index.php?do=statistic_2010（上網日期：101年11月13日）。臺灣省政府圖書館。'
    if table==170:footnotes='公立公共圖書館資料來源：國立臺中圖書館，〈2011年度彙整結果〉。「公共圖書館統計系統」。網址：http://publibstat.ntl.gov.tw/index.php?do=statistic_2010（上網日期：101年10月23日）。館藏圖書冊數含非書資料，公立公共圖書館部分不含電子書253,356種。'
    if table==154:footnotes='資料來源：國家圖書館「全國圖書館名錄」，檢自http://libstat.ncl.edu.tw/statFront/a_libcatalog/search_result.jsp?searchType=type&page=2&cityId=ALL&orgId='
    if table==155:footnotes='（1）館藏量包含圖書及非書資料，但不含電子書。（3）公立公共圖書館統計，檢自國立公共資訊圖書館「公共圖書館統計系統」2013年度彙整結果。'
    if table==151:footnotes='公共圖書館數，檢自國立公共資訊圖書館「公共圖書館統計系統」2012年度彙整結果，館數計入總館及分館（不含館外服務站）；私立公共圖書館數，則取自國家圖書館「全國圖書館名錄」私立公共圖書館子項。'
    aggregate_metric=metric[0] in {'compiled','formal_compiled','formal_subtotal','informal_subtotal','physical_materials','electronic','all_holdings','all_main','all_branch','all_outreach','subtotal'}
    role='derived_ratio' if metric[3]=='derived_ratio' else 'published_total' if entity_kind=='national_total' or aggregate_metric or entity=='公共圖書館（含私立）' else 'reported_component'
    record=dict(data_year=reference_year,entity_raw=entity,entity_contextual_name=entity,entity_kind=entity_kind,
        geography_vintage=f'{reference_year} original published geography; 桃園縣 retained; not reclassified to current boundaries',
        national_libraries_scope=scope,metric_id=f'table{table}_{metric[0]}',metric_raw=metric[1],value_raw=raw,value=value,
        unit=metric[2],temporal_kind=metric[3],source_id=m['source_id'],source_url=m['source_page_url'],
        source_download_url=m['source_download_url'],source_sha256=m['sha256'],source_local_path=m['source_local_path'],
        source_agency='國家圖書館',source_retrieved_at=m['source_retrieved_at'],source_pdf_page=pdfpage,
        source_printed_page=str(printed),source_table=str(table),source_row=row,source_column=column,source_locator=locator,
        raw_extracted_line=raw,extraction_status='image_reviewed_headers_and_footnotes_coordinate_cells',license_status='not_confirmed',
        publication_date={101:'2012-12',102:'2014-05',103:'2015-01-01'}.get(edition),publication_date_basis='copyright_page_month' if edition in {101,102} else 'official_entry_publication_date',value_status=status,source_edition=str(edition),source_edition_roc=edition,
        table_title_raw=raw_title,population_scope='公立公共圖書館；以各表原始母體與註腳為準',period_raw=f'{reference_year-1911}年（原表資料年）',
        period_start=start,period_end=end,notes=note,cell_annotation=annotation,cell_bbox=[round(v,3) for v in bbox],
        snapshot_distribution='not_in_public_bundle',unit_raw=unit_raw,unit_basis=unit_basis,aggregation_role=role,institutional_level=entity if entity_kind=='library_level_or_ownership_class' else metric[1].split('／')[0] if table==19 else '原表各級合計或明列機構',source_column_path=metric[1] if table not in {31,33,34,157} else entity if table in {31,33,34} else f'{reference_year-1911}年',source_cell_bbox=[round(v,3) for v in bbox],source_cell_bbox_kind='positioned_glyph_band_or_table_grid',source_version_id=f"{m['source_id']}:{m['sha256']}",source_title=f'中華民國{edition}年圖書館年鑑／'+('公共圖書館' if kind=='public-library' else '圖書館統計'),source_table_title=raw_title,source_data_year_raw=f'{reference_year-1911}年',scope_note=scope,time_reference=f'{reference_year}年全年' if start else f'原表民國{reference_year-1911}年；精確時點未逐表明示，不以出版日或上網日替代',quality_flags=[],source_footnotes_raw=footnotes,source_footnotes_status='selected_original_footnote_excerpts; whitespace_normalized; full_context_in_private_PDF' if footnotes else 'no_table_specific_transcription',source_original_access_date_raw='101年7月15日' if edition==101 and kind=='public-library' else '101年11月13日' if table==169 else '101年10月23日' if table==170 else None,original_fields={'entity':entity,'metric':metric[1],'value_raw':raw,'table_title':raw_title,'unit_raw':unit_raw})
    if role=='published_total':record['quality_flags'].append('published_total_overlaps_components')
    if edition==103 and table==33:record['quality_flags'].append('printed_title_differs_from_column_dimension')
    if table in {169,170}:record['quality_flags'].append('source_reference_year_url_mismatch')
    if 'including_private' in scope:record['population_scope']='公共圖書館（原表含私立）；不得當作公立公共館數'
    if 'private_ownership_only' in scope:record['population_scope']='私立公共圖書館類別總數；非單館資料；不可併入公立館統計'
    ROWS.append(record);CELLS.append({k:record[k] for k in ['data_year','source_id','source_sha256','source_pdf_page','source_table','source_row','source_column','entity_raw','metric_id','metric_raw','value_raw','value','value_status','cell_bbox']})
    return record

def table_info(edition,kind,number,title,pages,expected,description):
    before=len(ROWS)
    return {'edition_roc':edition,'document_kind':kind,'table':str(number),'title':title,'pdf_pages':pages,'expected_cells':expected,'row_start':before,'coverage':description}

def finish(info):
    rows=ROWS[info.pop('row_start'):]
    if len(rows)!=info['expected_cells']:raise ValueError(('Incomplete table',info,len(rows)))
    info.update(extracted_cells=len(rows),numeric_cells=sum(r['value'] is not None for r in rows),explicit_missing_cells=sum(r['value_status']=='not_available_in_source' for r in rows),blank_cells=sum(r['value_status']=='blank_in_source' for r in rows),zero_cells=sum(r['value'] is not None and Decimal(r['value'])==0 for r in rows),coverage_status='complete_selected_operational_table_or_explicit_public_library_subset')
    TABLES.append(info)

def numeric_words(pg,bbox):
    x0,y0,x1,y1=bbox
    return [w for w in words(pg) if x0<=(w['x0']+w['x1'])/2<x1 and y0<=center(w)<y1 and (NUMBER.fullmatch(w['text']) or w['text'] in {'-','…','N/A'})]

def matrix(edition,kind,pdfpage,printed,table,title,bbox,entities,metrics,*,row_oriented=True,scope=None,note='',year=None):
    pg=page(edition,kind,pdfpage-1,True);groups=[]
    for w in sorted(numeric_words(pg,bbox),key=lambda w:(center(w),w['x0'])):
        hit=next((g for g in groups if abs(g[0]-center(w))<2.3),None)
        if hit is None:groups.append([center(w),[w]])
        else:hit[1].append(w)
    expected_rows=len(entities) if row_oriented else len(metrics)
    expected_cols=len(metrics) if row_oriented else len(entities)
    if len(groups)!=expected_rows:raise ValueError(('Matrix row count',edition,table,len(groups),expected_rows))
    info=table_info(edition,kind,table,title,[pdfpage],expected_rows*expected_cols,'complete coordinate matrix')
    for i,(_,group) in enumerate(sorted(groups),1):
        group.sort(key=lambda w:w['x0'])
        if len(group)!=expected_cols:raise ValueError(('Matrix column count',edition,table,i,len(group),expected_cols))
        for j,w in enumerate(group,1):
            entity=entities[i-1] if row_oriented else entities[j-1];metric=metrics[j-1] if row_oriented else metrics[i-1]
            emit(edition,kind,pdfpage,printed,table,title,entity,metric,w['text'],(w['x0'],w['top'],w['x1'],w['bottom']),i,j+1,scope=scope,note=note,year=year)
    finish(info)

def county_table(edition,pdfpage,printed,table,title,bbox,metrics,*,split=True,note='',continuation=False):
    pg=page(edition,'public-library',pdfpage-1,True);x0,y0,x1,y1=bbox
    labels=[w for w in words(pg) if w['text'] in COUNTY_SET and x0<=w['x0']<x1 and y0<=center(w)<y1]
    info=None
    if not continuation:info=table_info(edition,'public-library',table,title,[pdfpage],22*len(metrics),'all 22 printed county rows; no current-boundary recoding')
    for w in sorted(labels,key=lambda w:(0 if not split or w['x0']<269 else 1,center(w))):
        right=269 if split and w['x0']<269 else x1
        candidates=numeric_words(pg,(w['x1']+0.8,center(w)-5.8,right,center(w)+5.8))
        candidates.sort(key=lambda n:n['x0'])
        if len(candidates)!=len(metrics):raise ValueError(('County numeric columns',edition,table,w['text'],[(v['text'],v['x0']) for v in candidates]))
        for j,(metric,n) in enumerate(zip(metrics,candidates),1):
            emit(edition,'public-library',pdfpage,printed,table,title,w['text'],metric,n['text'],(n['x0'],n['top'],n['x1'],n['bottom']),len({r['entity_raw'] for r in ROWS if r['source_id']==f'ncl-yearbook-{edition}-public-library' and r['source_table']==str(table)})+(0 if j>1 else 1),j+1,scope='excluded_from_county_metrics_per_table_footnote',note=note)
    if info:
        seen=[r['entity_raw'] for r in ROWS[-22*len(metrics):]]
        if set(seen)!=COUNTY_SET:raise ValueError(('County set mismatch',table,set(seen)))
        finish(info)
    return len(labels)

STOCK='annual_reference_year_stock_timing_unconfirmed'

def core_103():
    ed=103
    matrix(ed,'public-library',2,72,31,'全國公共圖書館數量統計－依圖書館級別（102年）',(175,136,483,179),LEVELS,
        [('main','總館（所）','所',STOCK),('branch','分館（所）','所',STOCK),('outreach','館外服務站（所）','所',STOCK)],row_oriented=False,
        note='表31註a：直轄市總館數依原行政區設置與各市定義；臺中34、臺南42不代表每市僅一總館。總館、分館、館外站分項保留，不能無條件與其他館數母體相接。')
    county_table(ed,2,72,32,'全國公共圖書館數量統計－依縣市別（102年）',(56,278,483,433),[('main','總館','所',STOCK),('branch','分館','所',STOCK),('outreach','館外服務站','所',STOCK)])
    staff=[('formal_compiled','正式人力／編制內人員'),('professional','正式人力／專業人員'),('administrative','正式人力／行政人員'),('technical','正式人力／技術人員'),('temporary','正式人力／臨時人員'),('contract','正式人力／約聘僱人員'),('formal_subtotal','正式人力／小計'),('student','非正式人力／工讀生'),('volunteer','非正式人力／志工'),('other','非正式人力／其他'),('informal_subtotal','非正式人力／小計')]
    matrix(ed,'public-library',2,72,33,'全國公共圖書館人力資源統計－依縣市別（102年）',(178,512,483,665),LEVELS,[(k,l,'人',STOCK) for k,l in staff],row_oriented=False,
        note='原表題寫「依縣市別」，實際數值欄為圖書館級別；按影像欄頭保留。專業／行政／技術為編制內人員分項，不可與編制內小計重複相加。')
    holdings=[('physical_materials','圖書資料','原表未列總量單位（混合冊／種／件）'),('books','圖書（冊）','冊'),('periodicals','期刊（種）','種'),('newspapers','報紙（種）','種'),('other_physical','其他（件）','件'),('nonbook','非書資料（件）','件'),('electronic','電子資源','原表未列總量單位'),('databases','資料庫（種）','種'),('ebooks','電子書（種）','種'),('all_holdings','總計','混合冊／種／件（原表總量）')]
    matrix(ed,'public-library',3,73,34,'全國公共圖書館館藏資源數量統計（102年）',(175,265,483,423),LEVELS,[(k,l,u,STOCK) for k,l,u in holdings],row_oriented=False,
        note='分項、上層小計與總計同時保存；異質單位不得視為全是冊。與統計章表155／157另保留版本及不同數值，不相互覆寫。')
    county_table(ed,3,73,35,'各縣市公共圖書館館藏圖書冊數及人均擁有圖書冊數（102年）',(56,495,483,636),[('population','人口數','人',STOCK),('book_holdings','館藏圖書冊數','冊',STOCK),('books_per_capita','人均擁有圖書冊數（冊／件）','冊／件／人（原表）','derived_ratio')])
    county_table(ed,4,74,36,'各縣市公共圖書館圖書資料購置經費及人均購書費（102年）',(56,305,483,446),[('population','人口數','人',STOCK),('acquisition_spending','圖書資料購置經費','新臺幣元','annual_financial'),('spending_per_capita','每人平均購書經費','新臺幣元／人','derived_ratio')])
    county_table(ed,5,75,37,'各縣市公共圖書館圖書資料使用情形（102年）',(56,141,483,532),[('population','人口數','人',STOCK),('loans','外借冊數','冊次（原表冊數）','flow_calendar_year'),('borrower_visits','借閱人次','人次','flow_calendar_year'),('loans_per_capita','每人平均借閱冊數','冊次／人','derived_ratio')],split=False)
    activities=[('reading','閱讀推廣活動'),('education_arts','社教藝文活動'),('local','地方特色活動'),('story','說故事'),('film','影片欣賞'),('other','其他'),('subtotal','小計')]
    county_table(ed,6,76,38,'各縣市公共圖書館推廣活動類型及辦理場次（102年）',(56,136,483,419),[(k,l,'場次','flow_calendar_year') for k,l in activities],split=False)
    info=table_info(ed,'public-library',39,'各縣市公共圖書館各類推廣活動參與人次（102年）',[6,7],22*7,'all 22 county rows; continuation page retained')
    n1=county_table(ed,6,76,39,info['title'],(56,501,483,653),[(k,l,'人次','flow_calendar_year') for k,l in activities],split=False,continuation=True)
    n2=county_table(ed,7,77,39,info['title'],(56,128,483,314),[(k,l,'人次','flow_calendar_year') for k,l in activities],split=False,continuation=True)
    if n1+n2!=22:raise ValueError('Incomplete activity attendance continuation')
    finish(info)
    county_table(ed,7,77,40,'各縣市公共圖書館閱覽席位設置情形（102年）',(56,497,483,666),[('seats','席位數','席',STOCK)],split=True)


def core_101():
    ed=101;entities=COUNTIES_2011+NATIONAL_2011+['總計']
    pg=page(ed,'public-library',3,True);table=pg.find_tables()[0]
    edges=sorted({round(x,4) for c in table.columns for x in (c.bbox[0],c.bbox[2])})
    if len(edges)!=18:raise ValueError(('Table19 columns changed',edges))
    metrics=[]
    for group,gid in [('國立圖書館','national'),('直轄市圖書館','municipal'),('縣市級圖書館','county'),('鄉鎮市圖書館','township')]:
        for label,k in [('總館','main'),('分館','branch'),('館外服務站','outreach')]:metrics.append((f'{gid}_{k}',f'{group}／{label}','所',STOCK))
    metrics += [('province_other','其他／省政府圖書館','所',STOCK),('all_main','合計／總館','所',STOCK),('all_branch','合計／分館','所',STOCK),('all_outreach','合計／館外服務站','所',STOCK)]
    labels=[w for w in words(pg) if w['text'] in COUNTY_SET|{'總計'} and w['x0']<91 and 322<center(w)<666]
    if len(labels)!=23 or {w['text'] for w in labels}!=COUNTY_SET|{'總計'}:raise ValueError('Table19 complete county labels not found')
    info=table_info(ed,'public-library',19,'全國公共圖書館館所統計（100年度）',[4],23*16,'all 22 counties plus total; all 16 numeric/blank cells per row')
    for i,w in enumerate(sorted(labels,key=center),1):
        for j,metric in enumerate(metrics,1):
            bbox=(edges[j],center(w)-6,edges[j+1],center(w)+6);raw=cell_text(pg,bbox)
            emit(ed,'public-library',4,54,19,info['title'],w['text'],metric,raw,bbox,i,j+1,
                 scope='geographic_distribution_by_explicit_national_local_level_columns',note='原表留白格，原因未確認；保留空白狀態，不補0；國立館按所在地另列於國立級欄。')
    finish(info)
    staff=[('compiled','編制內館員總計','人',STOCK),('professional','編制內專業人員','人',STOCK),('administrative','編制內行政人員','人',STOCK),('technical','編制內技術人員','人',STOCK),('temporary','臨時人員','人',STOCK),('contract','約聘僱人員','人',STOCK),('student','工讀生','人',STOCK),('volunteer','志工人數','人','stock_or_annual_not_fully_confirmed'),('other','其他','人',STOCK),('service_population_per_staff','館員平均服務人口數','人／編制內館員','derived_ratio')]
    finance=[('population','人口數（人）','人',STOCK),('mixed_holdings','館藏收藏量（冊）','冊（原表；含非書及電子資源混合）',STOCK),('acquisition_spending','全年購買圖書資料費（元）','新臺幣元','annual_financial'),('loans','全年圖書借閱量（冊）','冊次','flow_calendar_year'),('holdings_per_capita','平均每人擁書量（冊）','冊／人（原表混合館藏）','derived_ratio'),('spending_per_capita','平均每人購買經費（元）','新臺幣元／人','derived_ratio'),('loans_per_capita','每人借閱量（冊）','冊次／人','derived_ratio')]
    for pageidx,num,printed,defs,title in [(4,20,55,staff,'全國公共圖書館人力資源統計（100年度）'),(5,21,56,finance,'全國公共圖書館購買圖書資料經費及館藏數量統計表（100年度）')]:
        pg=page(ed,'public-library',pageidx,True);grid=pg.find_tables()[0]
        if len(grid.rows)!=27 or len(grid.columns)!=len(defs)+1:raise ValueError(('Core table grid changed',num))
        info=table_info(ed,'public-library',num,title,[pageidx+1],26*len(defs),'all 22 counties, 3 separately printed national/provincial institutions, and total; blanks/dashes retained')
        for i,(entity,rowbox) in enumerate(zip(entities,grid.rows[1:]),1):
            for j,(metric,colbox) in enumerate(zip(defs,grid.columns[1:]),1):
                bbox=(colbox.bbox[0],rowbox.bbox[1],colbox.bbox[2],rowbox.bbox[3]);raw=cell_text(pg,bbox)
                scope=None;note='編制內人員分項、上層小計與人均比率不可重複相加。'
                if entity in COUNTY_SET:
                    scope='separate_national_rows_not_added_to_printed_county_amounts'
                    if metric[3]=='derived_ratio':scope='county_ratio_formula_uses_all_levels_per_footnote; relation_to_separate_rows_not_certified'
                if num==21:note='原表*人均擁書量包含非書及電子資源；**購書費與***借閱量分母為縣市總人口。人均公式的全層級分子與另列國立館原量不可直接視為相同範圍。'
                emit(ed,'public-library',pageidx+1,printed,num,title,entity,metric,raw,bbox,i,j+1,scope=scope,note=note)
        finish(info)
    pg=page(ed,'public-library',6,True)
    labels=[w for w in words(pg) if w['text'] in set(entities) and w['x0']<159 and 132<center(w)<515]
    if len(labels)!=26:raise ValueError(('Table22 rows',len(labels)))
    metrics=[('seats','閱覽席位數（席）','席',STOCK),('computers','供讀者使用的電腦數（臺）','臺',STOCK),('promotion_events','全國推廣活動（場次）','場次','flow_calendar_year'),('promotion_attendance','全國推廣活動（人次）','人次','flow_calendar_year')]
    info=table_info(ed,'public-library',22,'全國公共圖書館服務統計表（100年度）',[7],26*4,'all 26 source entities')
    for i,w in enumerate(sorted(labels,key=center),1):
        ns=sorted(numeric_words(pg,(159,center(w)-6,483,center(w)+6)),key=lambda n:n['x0'])
        if len(ns)!=4:raise ValueError(('Table22 columns',w['text'],ns))
        for j,(metric,n) in enumerate(zip(metrics,ns),1):emit(ed,'public-library',7,57,22,info['title'],w['text'],metric,n['text'],(n['x0'],n['top'],n['x1'],n['bottom']),i,j+1,scope='included_in_national_total' if w['text']=='總計' else 'separate_institution' if w['text'] in NATIONAL_2011 else 'separate_national_rows_not_added_to_printed_county_amounts')
    finish(info)


def statistics_subsets():
    # Exact public-library groups only. Other library types and their totals are
    # intentionally outside this task. No school statistics are imported.
    settings=[(101,6,412,169,(55,125,483,223),7),(102,2,402,151,(55,357,483,455),7),(103,2,390,154,(280,149,483,256),6)]
    class_labels={101:['公共圖書館（含私立）','國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市立圖書館','其他公立公共圖書館','私立公共圖書館'],102:['公共圖書館（含私立）','國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市立圖書館','其他公立公共圖書館','私立公共圖書館'],103:['公共圖書館（含私立）','國立圖書館','直轄市立圖書館','縣市立圖書館','鄉鎮市立圖書館','私立公共圖書館']}
    for ed,pno,printed,num,bbox,n in settings:
        pg=page(ed,'statistics',pno-1,True);ns=sorted(numeric_words(pg,(430,bbox[1],483,bbox[3])),key=center)
        if len(ns)!=n:raise ValueError(('Type subset rows',ed,num,[(v['text'],center(v)) for v in ns]))
        info=table_info(ed,'statistics',num,f'我國各類型圖書館數量統計表（{ed-1}年）／公共圖書館完整類別組',[pno],n,'complete public-library ownership/level subset only; other library types intentionally excluded')
        for i,(label,w) in enumerate(zip(class_labels[ed],ns),1):
            scope='public_libraries_including_private' if i==1 else 'private_ownership_only' if label=='私立公共圖書館' else 'public_library_level_class_from_statistics_chapter'
            emit(ed,'statistics',pno,printed,num,info['title'],label,('library_count','圖書館數量','所',STOCK),w['text'],(w['x0'],w['top'],w['x1'],w['bottom']),i,2,scope=scope,
                 note='圖書館類型表的完整公共館類別組含私立；不能當公立總數或與公共館章館數硬接。101卷表169未獨立確認是否一致排除館外站；102卷表151註記計總館/分館、不含館外站；103卷表154來自全國圖書館名錄。')
        finish(info)
    basic=[('holdings','館藏量／館藏圖書冊數','冊、件（不含電子書）',STOCK),('seats','閱覽席位','席',STOCK),('borrower_visits','借閱人次','人次','flow_calendar_year'),('loans','借閱冊數','冊次','flow_calendar_year')]
    # bbox is the public-library row, verified in each page image.
    for ed,pno,printed,num,bbox in [(101,7,413,170,(145,279,483,290)),(102,3,403,152,(158,456,484,467)),(103,3,391,155,(170,169,483,183))]:
        pg=page(ed,'statistics',pno-1,True);ns=sorted(numeric_words(pg,bbox),key=lambda n:n['x0'])
        if len(ns)!=4:raise ValueError(('Public basic row',ed,num,[(w['text'],center(w)) for w in ns]))
        info=table_info(ed,'statistics',num,f'我國各類型圖書館基本統計表（{ed-1}年）／公立公共圖書館列',[pno],4,'all four public-library cells; other library types excluded')
        for j,(metric,w) in enumerate(zip(basic,ns),1):emit(ed,'statistics',pno,printed,num,info['title'],'全國',metric,w['text'],(w['x0'],w['top'],w['x1'],w['bottom']),2,j+1,scope='public_libraries_excluding_private_and_National_Central_Library_separate_type',
            note='原註館藏含圖書及非書，但不含電子書；2011年另排除電子書253,356種。不同章／表的原值保留，不以後表覆寫。')
        finish(info)
    # 103 edition table157 is a complete, explicitly historical public-library table.
    pg=page(103,'statistics',4,True);groups=[]
    # The original has a second, shifted PDF text layer from an embedded
    # illustration, including text outside the crop box. Use only the five
    # visible table baselines verified against PDFium rendering.
    visible_baselines=[427.9,440.8,453.6,466.4,479.3]
    ns=[w for w in numeric_words(pg,(145,422,483,486)) if min(abs(center(w)-v) for v in visible_baselines)<0.5]
    for w in sorted(ns,key=lambda w:(center(w),w['x0'])):
        hit=next((g for g in groups if abs(g[0]-center(w))<2.5),None)
        if hit is None:groups.append([center(w),[w]])
        else:hit[1].append(w)
    if len(groups)!=5 or any(len(g[1])!=5 for g in groups):raise ValueError(('Table157 matrix',[(y,[w['text'] for w in g]) for y,g in groups]))
    metrics=[('library_count','圖書館數量','所',STOCK)]+basic
    info=table_info(103,'statistics',157,'公共圖書館基本統計表（98年至102年）',[5],25,'complete 5-year × 5-metric public-library table; own publication version')
    for i,(_,g) in enumerate(sorted(groups),1):
        for j,w in enumerate(sorted(g,key=lambda n:n['x0']),1):emit(103,'statistics',5,393,157,info['title'],'全國',metrics[i-1],w['text'],(w['x0'],w['top'],w['x1'],w['bottom']),i,j+1,year=2008+j,scope='public_libraries; source historical series; same-year definition not independently harmonized',note='原表98–102年全國公共館序列；不與同卷其它型別館數或其他出版版合併去重。')
    finish(info)


def validate_and_write():
    keys=[]
    for r in ROWS:
        keys.append((r['source_id'],r['source_table'],r['source_row'],r['source_column'],r['data_year'],r['metric_id'],r['entity_raw']))
        if r['value'] is not None:
            parsed,_,_=numeric(r['value_raw'])
            if parsed!=r['value']:raise ValueError('Raw value mismatch')
    if len(set(keys))!=len(keys):raise ValueError('Duplicate source coordinate observation key')
    # Arithmetic checks describe discrepancies in the printed source and never
    # overwrite either reported totals or component observations.
    def check(check_name,target,components):
        if target['value'] is None or any(c['value'] is None for c in components):return
        total=Decimal(target['value']);parts=sum(Decimal(c['value']) for c in components)
        result={'check':check_name,'source_id':target['source_id'],'table':target['source_table'],'entity':target['entity_raw'],'metric_id':target['metric_id'],'reported':str(total),'sum_parts':str(parts),'matches':total==parts,'source_locator':target['source_locator'],'component_locators':[c['source_locator'] for c in components]}
        CHECKS.append(result)
        if total!=parts:target['quality_flags'].append('source_arithmetic_difference')
    groups=defaultdict(dict)
    for r in ROWS:groups[(r['source_id'],r['source_table'],r['entity_raw'])][r['metric_id'].split('_',1)[1]]=r
    for (sid,table,entity),g in groups.items():
        if sid=='ncl-yearbook-103-public-library' and table in {'38','39'}:
            check('printed_activity_subtotal',g['subtotal'],[g[k] for k in ['reading','education_arts','local','story','film','other']])
        if sid=='ncl-yearbook-101-public-library' and table=='20':
            check('compiled_staff_subclassification',g['compiled'],[g[k] for k in ['professional','administrative','technical']])
        if sid=='ncl-yearbook-103-public-library' and table=='33':
            check('compiled_staff_subclassification',g['formal_compiled'],[g[k] for k in ['professional','administrative','technical']])
            check('formal_staff_subtotal',g['formal_subtotal'],[g[k] for k in ['formal_compiled','temporary','contract']])
            check('informal_staff_subtotal',g['informal_subtotal'],[g[k] for k in ['student','volunteer','other']])
    for table in ['20','21','22']:
        gs=defaultdict(list)
        for r in ROWS:
            if r['source_id']=='ncl-yearbook-101-public-library' and r['source_table']==table and r['temporal_kind']!='derived_ratio':gs[r['metric_id']].append(r)
        for metric,g in gs.items():
            target=next(r for r in g if r['entity_raw']=='總計')
            check('printed_column_total_all_25_source_entities',target,[r for r in g if r is not target])
    for table in ['31','33','34']:
        gs=defaultdict(list)
        for r in ROWS:
            if r['source_id']=='ncl-yearbook-103-public-library' and r['source_table']==table:gs[r['metric_id']].append(r)
        for metric,g in gs.items():
            target=next(r for r in g if r['entity_raw']=='合計')
            check('printed_total_four_library_levels',target,[r for r in g if r is not target])
    image_facts=[
        (101,'public-library','20','臺南市','compiled',2011,'42.0'),
        (101,'public-library','20','總計','compiled',2011,'1248.0'),
        (101,'public-library','22','總計','promotion_events',2011,'77901'),
        (103,'public-library','31','直轄市級圖書館','main',2013,'79'),
        (103,'public-library','34','合計','all_holdings',2013,'39321176'),
        (101,'statistics','169','公共圖書館（含私立）','library_count',2011,'794'),
        (102,'statistics','151','公共圖書館（含私立）','library_count',2012,'633'),
        (103,'statistics','154','公共圖書館（含私立）','library_count',2013,'683'),
        (103,'statistics','157','全國','library_count',2009,'536'),
        (103,'statistics','157','全國','loans',2013,'65423579')]
    for edition,kind,table,entity,metric,year,expected in image_facts:
        hits=[r for r in ROWS if r['source_id']==f'ncl-yearbook-{edition}-{kind}' and r['source_table']==table and r['entity_raw']==entity and r['metric_id']==f'table{table}_{metric}' and r['data_year']==year]
        if len(hits)!=1 or Decimal(hits[0]['value'])!=Decimal(expected):raise ValueError(('Image checked reference cell mismatch',edition,table,entity,metric,expected,hits))
    CHECKS.append({'check':'image_anchored_regression_cells','cells_checked':len(image_facts),'matches':True})
    counts=Counter(r['source_id'] for r in ROWS)
    overview={'built_at':utc(),'long_rows':len(ROWS),'data_years':sorted({r['data_year'] for r in ROWS}),'source_ids':dict(counts),
        'value_status_counts':dict(Counter(r['value_status'] for r in ROWS)),'tables':TABLES,'checks':CHECKS,
        'all_selected_tables_complete':all(t['extracted_cells']==t['expected_cells'] for t in TABLES),
        'zero_cells':sum(r['value'] is not None and Decimal(r['value'])==0 for r in ROWS),
        'arithmetic_discrepancies':[c for c in CHECKS if not c['matches']],
        'input_pdf_paths':[m['source_local_path'] for m in DOCUMENTS.values()],
        'source_edition_publication_date_evidence':{'101':'Copyright page: 出版日期：中華民國101年12月 初版','102':'Copyright page: 出版日期：中華民國103年5月 初版 (edition102 is not publication year2013)','103':'Official entry visible 出版日期2015-01-01; DC.Date2015-01-01'},
        'intentional_exclusions':[
          {'scope':'all three full public-library chapters','reason':'Signed narrative, photographs, named construction/project outcomes, policy and training rosters are outside operational-core-table scope; not counted as missing data.'},
          {'scope':'102 edition public-library chapter','reason':'Reference year 2012 operational overview is narrative, not the same complete county core tables; not converted from ranked narrative facts into invented tables. Specific city training tables22/23 intentionally excluded.'},
          {'scope':'statistics chapters','reason':'All non-public-library types, school rows, national central library as a separate type, cross-type totals and duplicate chart graphics intentionally excluded. Public/private mixed ownership group remains explicitly classified, never treated as a public-only total.'}],
        'remaining_limits':['102 edition does not supply a full 22-county operational core table batch in the inspected public-library chapter; no claim all 2012 county indicators complete.','Blank source cells and explicit dashes are preserved separately and never zero-filled.','No cross-year geographic harmonization, no new full-text licence claim, no PDF redistribution.','Current publication is not an expert or human double-checked edition; page images, table headers, footnotes and cell geometry were reviewed by the agent.']}
    DERIVED.mkdir(exist_ok=True)
    out=DERIVED/'ncl_additional_years_long.csv'
    with out.open('w',newline='',encoding='utf-8') as stream:
        w=csv.DictWriter(stream,fieldnames=list(ROWS[0]));w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in ROWS)
    (DERIVED/'ncl_additional_years_long.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in ROWS))
    (RAW/'extraction-validation.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2)+'\n')
    (RAW/'extracted-operational-cells.json').write_text(json.dumps(CELLS,ensure_ascii=False,indent=2)+'\n')
    for (edition,kind),m in DOCUMENTS.items():
        selected=[t for t in TABLES if t['edition_roc']==edition and t['document_kind']==kind]
        m.update(selected_table_metadata=selected,source_cells=sum(t['extracted_cells'] for t in selected),numeric_cells=sum(t['numeric_cells'] for t in selected),blank_cells=sum(t['blank_cells'] for t in selected),explicit_missing_cells=sum(t['explicit_missing_cells'] for t in selected),intentional_exclusion=overview['intentional_exclusions'],incremental_update_policy='Only exact official observed URLs are used. Missing identical-SHA originals may be restored; changed SHA requires new image review and explicit table-spec revision; never silently replace source version.')
    (RAW/'documents.json').write_text(json.dumps(list(DOCUMENTS.values()),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:overview[k] for k in ['long_rows','data_years','source_ids','value_status_counts','all_selected_tables_complete']},ensure_ascii=False))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--offline',action='store_true',help='require existing reviewed originals; default only retrieves missing exact linked originals')
    args=ap.parse_args();RAW.mkdir(parents=True,exist_ok=True)
    for edition in [101,102,103]:
        for kind in ['public-library','statistics','toc']+(['copyright'] if edition in {101,102} else []):doc(edition,kind,args.offline)
    core_103();core_101();statistics_subsets();validate_and_write()

if __name__=='__main__':main()
