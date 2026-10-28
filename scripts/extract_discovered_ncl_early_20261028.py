#!/usr/bin/env python3
"""Reproduce complete reviewed 2001–2004 NCL original statistical tables.

Only the specified statistical cells, necessary labels and source coordinates
are exported. Original PDFs and complete authored prose are not redistributed.
Supply exact official originals with --source-root; source hashes are pinned by
the reviewed discovery register. No acquisition, canonical merge or publishing.
"""
from __future__ import annotations
import argparse, collections, decimal, hashlib, json, re, subprocess
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
# Portable public statistical provenance; no private acquisition paths or caches.
PINNED_SOURCE_DOCUMENTS = {'ncl-ed91-public-libraries': {'candidate_id': 'ncl-ed91-public-libraries', 'official_url': 'https://www.ncl.edu.tw/files/file_pool/1/0Q083566106366221617/6e5a9913-4bf0-436e-9fbb-b91b148ca1b7.pdf', 'catalogue_url': 'https://www.ncl.edu.tw/librarianship-yearbook/0Q083566087370545104', 'source_sha256': '6b58c1f4432c77bb0fcbea94c2dc0373f1d5f163e080a203b01d74e29b9b0ff4', 'source_bytes': 49620616, 'source_version_id': 'ncl-ed91-public-libraries@sha256:6b58c1f4432c77bb0fcbea94c2dc0373f1d5f163e080a203b01d74e29b9b0ff4', 'retrieved_at': '2026-10-28T09:35:53.164539+00:00', 'edition_raw': '91年卷'}, 'ncl-ed92-public-libraries': {'candidate_id': 'ncl-ed92-public-libraries', 'official_url': 'https://www.ncl.edu.tw/files/file_pool/1/0Q083565618826372741/0b1bbc3b-6596-4602-bddc-c0d604ed6785.pdf', 'catalogue_url': 'https://www.ncl.edu.tw/librarianship-yearbook/0Q083565619396807101', 'source_sha256': '5e05eba958bd1bb569cc01c8a62138dcfbd40b5ad263908d233e21df1324ce06', 'source_bytes': 1129868, 'source_version_id': 'ncl-ed92-public-libraries@sha256:5e05eba958bd1bb569cc01c8a62138dcfbd40b5ad263908d233e21df1324ce06', 'retrieved_at': '2026-10-28T09:35:08.518125+00:00', 'edition_raw': '92年卷'}, 'ncl-ed93-public-libraries': {'candidate_id': 'ncl-ed93-public-libraries', 'official_url': 'https://www.ncl.edu.tw/files/file_pool/1/0Q083565599956839186/5932209a-a4a1-47aa-9247-0242fcd9167d.pdf', 'catalogue_url': 'https://www.ncl.edu.tw/librarianship-yearbook/0Q083565582148900528', 'source_sha256': 'c50226224241648bd3965e4aa89732583b3b15b99275ab401cf41badc0246057', 'source_bytes': 173078, 'source_version_id': 'ncl-ed93-public-libraries@sha256:c50226224241648bd3965e4aa89732583b3b15b99275ab401cf41badc0246057', 'retrieved_at': '2026-10-28T09:35:05.374349+00:00', 'edition_raw': '93年卷'}, 'ncl-ed94-public-libraries': {'candidate_id': 'ncl-ed94-public-libraries', 'official_url': 'https://www.ncl.edu.tw/files/file_pool/1/0Q083565582274153586/52feab5e-f333-4195-9e74-4ee3f8f9bd96.pdf', 'catalogue_url': 'https://www.ncl.edu.tw/librarianship-yearbook/0Q083565585645073973', 'source_sha256': '6a33073693212a20a74f9b3cb190e926ca4dfb6f6af988ef0357a2339c253417', 'source_bytes': 1574971, 'source_version_id': 'ncl-ed94-public-libraries@sha256:6a33073693212a20a74f9b3cb190e926ca4dfb6f6af988ef0357a2339c253417', 'retrieved_at': '2026-10-28T09:35:05.081655+00:00', 'edition_raw': '94年卷'}}
COUNTIES = ['臺北縣','桃園縣','新竹縣','苗栗縣','臺中縣','彰化縣','南投縣','雲林縣','嘉義縣','臺南縣','高雄縣','屏東縣','宜蘭縣','花蓮縣','臺東縣','澎湖縣','基隆市','新竹市','臺中市','嘉義市','臺南市','金門縣','連江縣']
INSTITUTIONS = ['國立中央圖書館臺灣分館','國立臺中圖書館','臺北市立圖書館','高雄市立圖書館','高雄市中正文化中心']

def col(key, label, unit, temporal='annual_source_reference_exact_period_unconfirmed', role='source_measure'):
    return {'metric_id':key,'metric_raw':label,'unit':unit,'unit_raw':unit,'temporal_kind':temporal,'aggregation_role':role}

MONEY=col('acquisition_spending','購書經費','元','annual_financial')
HOLD=col('holdings_total','館藏總數','冊','stock_year_end')
POP=col('population','人口數','人','stock_year_end')
HOLDPC=col('holdings_per_capita','每人擁有館藏冊數','冊/人','stock_year_end','derived_ratio')
MONEYPC=col('spending_per_capita','平均每人購書費','元/人','annual_financial','derived_ratio')
STAFF=[col('staff_'+key,'人力／'+label,'人') for key,label in [('formal','正式'),('temporary','臨時'),('contract','約聘僱'),('student','工讀生'),('volunteer','志工')]]
SERVICES=[col('reader_services','讀者服務','人次','flow_calendar_year'),col('promotion_events','推廣服務','場次','flow_calendar_year'),col('reference_enquiries','參考諮詢','人次','flow_calendar_year'),col('township_guidance','輔導鄉鎮（市）','次數','flow_calendar_year')]

def sha(b):return hashlib.sha256(b).hexdigest()
def stable(obj):return (json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def clean_cids(text):
    # Explicit glyph mappings for punctuation verified in the 92-edition image.
    return text.replace('(cid:286)','(').replace('(cid:287)',')')
def numeric_token(text):
    raw=clean_cids(text)
    raw=re.sub(r'\(cid:\d+\)','',raw)
    return re.sub(r'[\s,]','',raw)
def parse(raw):
    value=numeric_token(raw)
    if not raw.strip():return None,'source_blank'
    if re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?',value):return format(decimal.Decimal(value),'f'),'reported'
    annotated=re.fullmatch(r'([0-9,]+)\s*[（(](圖書|期刊)[）)]',re.sub(r'\s','',raw))
    if annotated:return str(int(annotated[1].replace(',',''))),'reported'
    return None,'source_marker'

def text_box(page, box):
    left,top,right,bottom=box
    chars=[c for c in page.chars if c['text'].strip() and left<=(c['x0']+c['x1'])/2<right and top<=(c['top']+c['bottom'])/2<bottom]
    lines=[]
    for char in sorted(chars,key=lambda c:(c['top']+c['bottom'])/2):
        y=(char['top']+char['bottom'])/2
        line=next((x for x in lines if abs(x[0]-y)<2),None)
        if line is None:line=[y,[]];lines.append(line)
        line[1].append(char)
    return '\n'.join(''.join(c['text'] for c in sorted(cs,key=lambda c:c['x0'])) for _,cs in lines)

class Extractor:
    def __init__(self,root,source_root):
        self.root=root;self.source_root=source_root;self.records=[];self.tables=[];self.documents=[]
        register=root/'docs/source-discovery-20261028.json'
        self.registry={r['candidate_id']:r for r in json.loads(register.read_text())['candidates']} if register.exists() else PINNED_SOURCE_DOCUMENTS
    def open(self,edition):
        self.edition=edition;self.sid=f'ncl-ed{edition}-public-libraries';self.spec=self.registry[self.sid]
        path=self.source_root/(self.sid+'.pdf');body=path.read_bytes()
        if sha(body)!=self.spec['source_sha256'] or len(body)!=self.spec['source_bytes']:raise ValueError('Original version differs: '+self.sid)
        self.pdf=pdfplumber.open(path);self.ind=pdfium.PdfDocument(path)
        document={k:self.spec[k] for k in ('candidate_id','official_url','catalogue_url','source_sha256','source_bytes','source_version_id','retrieved_at','edition_raw')}
        document['original_PDF_embedded_dates']={k:v for k,v in self.pdf.metadata.items() if k in ('CreationDate','ModDate')}
        document['embedded_dates_are_not_data_year']=True
        self.documents.append(document)
    def close(self):self.pdf.close();self.ind.close()
    def emit(self,page_number,table,title,row,colnum,entity,column,box,year,*,raw_override=None,unit_override=None,notes=None,flags=None,merged=None,period_raw=None,components=None):
        page=self.pdf.pages[page_number-1];raw=clean_cids(text_box(page,box));value,status=parse(raw)
        other_page=self.ind[page_number-1]
        try:
            tp=other_page.get_textpage();left,top,right,bottom=box
            other=tp.get_text_bounded(left=left+.05,right=right-.05,bottom=page.height-bottom+.05,top=page.height-top-.05).strip();tp.close()
        finally:other_page.close()
        token1=numeric_token(raw);token2=numeric_token(other)
        # Chinese is unavailable in the CMap of several originals. Numeric/blank
        # checks compare literal ASCII numeric tokens; labels are image-reviewed.
        digits1=re.findall(r'-?[0-9]+(?:\.[0-9]+)?',token1);digits2=re.findall(r'-?[0-9]+(?:\.[0-9]+)?',token2)
        if digits1!=digits2:raise ValueError(('PDF numeric engines disagree',self.sid,table,row,colnum,raw,other,box))
        if raw_override is not None:
            if re.findall(r'[0-9]+(?:\.[0-9]+)?',numeric_token(raw_override))!=re.findall(r'[0-9]+(?:\.[0-9]+)?',token1):raise ValueError('Image-label override changes source numeric tokens')
            raw=raw_override;value,status=parse(raw)
        unit=column['unit'];unit_raw=column['unit_raw'];unit_status='printed_column_heading' if unit else 'printed_heading_counting_basis_unresolved'
        temporal=column['temporal_kind']
        if unit_override:
            unit,unit_raw,unit_status,temporal=unit_override
        quality=list(flags or [])
        if status=='source_blank':quality.append('source_blank_reason_unconfirmed')
        if value=='0':quality.append('source_reported_zero_not_certified_true_zero')
        if merged:quality.append('original_merged_cell_recorded_once')
        display_raw=raw
        # A unit-bearing quantity is literal, not a zero or a missing token.
        if raw_override=='每週80人次':value='80';status='reported'
        oid=f'{self.sid}/{table}/{page_number}/{row}/{colnum}'
        printed_page={91:70,92:94,93:107,94:73}[self.edition]+page_number
        r={'cell_id':'cell-'+sha(oid.encode())[:24],'source_document_id':self.sid,'source_url':self.spec['official_url']+'#page='+str(page_number),'source_sha256':self.spec['source_sha256'],'source_version_id':self.spec['source_version_id'],'source_retrieved_at':self.spec['retrieved_at'],'source_catalogue_url':self.spec['catalogue_url'],'source_edition_roc':self.edition,'source_pdf_page':page_number,'source_printed_page':str(printed_page),'source_table':str(table),'source_table_title':title,'source_row':str(row),'source_column':str(colnum),'source_locator':f'PDF page {page_number}; printed page {printed_page}; table {table}; source row {row}; numeric column {colnum}; bbox '+','.join(f'{x:.3f}' for x in box),'source_cell_bbox':[round(x,4) for x in box],'row_label_raw':entity,'column_label_raw':column['metric_raw'],'entity_raw':entity,'entity_kind':'county' if entity in COUNTIES else 'public_library_institution','data_year':year,'period_raw':period_raw or (str(year-1911)+'年' if year is not None else None),'period_status':'explicit_original_table_ROC_year' if year is not None else 'shared_source_years_not_single_year','metric_id':column['metric_id'],'metric_raw':column['metric_raw'],'value_raw':display_raw,'value':value,'value_status':status,'unit':unit,'unit_raw':unit_raw,'unit_status':unit_status,'temporal_kind':temporal,'population_scope':'原表列明之國立／直轄市立公共館' if entity not in COUNTIES else '原表當年各縣市文化局／縣市立及鄉鎮市圖書館，依表題及註腳分開','national_libraries_scope':'national_institutions_separate_from_county_rows' if entity in COUNTIES else 'explicit_institution_or_shared_municipal_scope','geography_vintage':f'{year}原表行政區，未重編今日22縣市' if year is not None else '原表行政區，未重編今日22縣市','aggregation_role':'shared_merged_source_cell' if merged else column['aggregation_role'],'source_notes':list(notes or []),'quality_flags':quality,'independent_check':{'method':'positioned_pdfminer_vs_PDFium_cell_numeric_tokens','matched':True,'pdfminer_raw':text_box(page,box),'pdfium_raw':other,'numeric_tokens':digits1,'label_review':'specified_original_page_images_checked; no full-prose export'},'license_status':'published_statistical_facts_document_license_unconfirmed'}
        if merged:r['merged_cell_scope']=merged
        if components:r['value_components']=components
        self.records.append(r)
    def grid(self,pn,table,title,entities,xs,ys,columns,year,*,row_offset=0,notes=None,overrides=None):
        if len(xs)!=len(columns)+1 or len(ys)!=len(entities)+1:raise ValueError('Grid dimensions')
        before=len(self.records)
        for ri,entity in enumerate(entities):
            for ci,column in enumerate(columns):
                kwargs=(overrides or {}).get((ri,ci),{})
                self.emit(pn,table,title,ri+1+row_offset,ci+1,entity,column,[xs[ci],ys[ri],xs[ci+1],ys[ri+1]],year,notes=notes,**kwargs)
        self.tables.append({'source_document_id':self.sid,'table':str(table),'pdf_page':pn,'title':title,'data_rows':len(entities),'numeric_columns':len(columns),'physical_cells_emitted':len(self.records)-before,'expected_grid_slots':len(entities)*len(columns),'scope_complete_for_this_page_grid':True,'source_notes':list(notes or [])})

def evenly(start,step,n):return [round(start+i*step,5) for i in range(n+1)]

def extract93(e):
    e.open(93)
    try:
        title='國立暨直轄市立公共圖書館經費、館藏與資源使用統計表（民國92年）'
        cols=[MONEY,HOLD,col('borrower_visits','圖書借閱人次','人次','flow_calendar_year'),col('loans','圖書借閱冊數','冊','flow_calendar_year'),*STAFF]
        xs=[155.88,204.12,252.12,300.38,348.38,375.12,401.88,428.38,455.12,481.88]
        ys=[539.12,572.25,588.88,605.62]
        notes=['高雄包括高雄市立圖書館及高雄市立中正文化中心管理處；前四數量欄為兩機構共享合併格，只記一次。','購書經費、館藏總數、借閱人次及借閱冊數資料來源為教育部統計處。']
        e.grid(2,'16',title,INSTITUTIONS[:3],xs,ys,cols,2003,notes=notes)
        start=len(e.records)
        for ci,column in enumerate(cols[:4]):
            e.emit(2,'16',title,'4–5',ci+1,'高雄市立圖書館及高雄市中正文化中心',column,[xs[ci],605.62,xs[ci+1],638.88],2003,merged={'row_labels':INSTITUTIONS[3:],'rows':[4,5]},notes=notes)
        for ri,entity in enumerate(INSTITUTIONS[3:]):
            for ci,column in enumerate(cols[4:],4):e.emit(2,'16',title,ri+4,ci+1,entity,column,[xs[ci],605.62+ri*16.63,xs[ci+1],605.62+(ri+1)*16.63],2003,notes=notes)
        e.tables[-1].update(data_rows=5,expected_grid_slots=45,physical_cells_emitted=41,merged_covered_slots=4,scope_complete_for_this_page_grid=True)
        e.grid(3,'17','臺閩地區各縣（市）暨鄉鎮（市）立圖書館館藏資料及購書經費統計表（民國92年）',COUNTIES,[92.88,192.12,291.38,390.62,435.88,481.38],evenly(205.88,16.65,23),[POP,HOLD,MONEY,HOLDPC,MONEYPC],2003,notes=['館藏總數及購書經費含縣市立及鄉鎮立圖書館。','資料來源：教育部統計處。'])
        title='臺閩地區各縣市文化局人力、讀者服務、推廣服務、參考諮詢與輔導鄉鎮（市）概況統計表（民國92年）'
        e.grid(5,'19',title,COUNTIES[:16],[92.88,125.12,157.62,189.88,222.12,254.38,311.12,367.88,424.62,481.38],evenly(405.88,16.65,16),[*STAFF,*SERVICES],2003,notes=['文化局人力與各縣市服務母體保留原表，不自認全縣所有館員數；空白不補零。'])
        e.grid(6,'19',title+'（續）',COUNTIES[16:],[93.5,125.88,158.12,190.38,222.88,255.0,311.88,368.38,425.12,481.88],evenly(222.38,16.65,7),[*STAFF,*SERVICES],2003,row_offset=16,notes=['與PDF5同表續頁；空白不補零。'])
    finally:e.close()

def extract94(e):
    e.open(94)
    try:
        cols=[MONEY,HOLD,col('borrower_visits','圖書借閱人次','人次','flow_calendar_year'),col('reference_enquiries','參考諮詢','人次','flow_calendar_year'),col('township_guidance','輔導鄉鎮','次數','flow_calendar_year'),*STAFF]
        over={(4,9):{'raw_override':'每週80人次','unit_override':('人次/週','每週80人次（表頭人力為人）','explicit_printed_cell_unit_overrides_shared_heading','source_reported_weekly_quantity'),'flags':['weekly_person_visits_not_volunteer_headcount_or_annual_total']}}
        e.grid(2,'7','國立暨直轄市立公共圖書館經費、館藏與資源使用統計表（民國93年）',INSTITUTIONS[:4]+['高雄市政府文化局'],[116.72,164.68,212.63,260.6,308.55,356.5,377.46,399.71,429.73,459.01,482.54],[432.79,482.19,517.88,549.08,599.1,649.13],cols,2004,overrides=over,notes=['資料來源為教育部統計處及國立中央圖書館臺灣分館。','高雄包括高雄市立圖書館及高雄市政府文化局；機構列保留不合併。'])
        e.grid(3,'8','臺閩地區各縣市暨鄉鎮市立圖書館館藏資料及購書經費統計表（民國93年）',COUNTIES,[123.08,194.59,269.46,343.97,413.85,481.89],evenly(206.93,16.652,23),[POP,HOLD,MONEY,HOLDPC,MONEYPC],2004,notes=['資料來源：國立中央圖書館臺灣分館。','基隆市館藏數與92年同，原註93年購書經費全數支援區圖書館；是來源沿用原報，不是整理者補值。'])
        staff_total=col('staff_total','人員／合計','人','stock_year_end','published_total')
        staff=[{**x,'metric_raw':x['metric_raw'].replace('人力','人員')} for x in STAFF]
        e.grid(4,'9','臺閩地區各縣市立圖書館人員、讀者及推廣服務、參考諮詢與輔導概況統計表（民國93年）',COUNTIES,[101.71,132.43,164.43,195.57,226.0,256.21,289.14,337.05,387.56,436.44,482.47],evenly(206.93,16.652,23),[*staff,staff_total,*SERVICES],2004,notes=['資料來源：國立中央圖書館臺灣分館。','人員合計與分項重疊，不整表相加；原刊留白及零值分開。'])
    finally:e.close()

COUNTS_ROWS=['臺北市','高雄市','基隆市','臺北縣','桃園縣','新竹縣','新竹市','苗栗縣','臺中縣','臺中市','南投縣','彰化縣','雲林縣','嘉義縣','嘉義市','臺南縣','臺南市','高雄縣','屏東縣','臺東縣','花蓮縣','宜蘭縣','澎湖縣','金門縣','連江縣','總計']
COUNT_COLUMNS=[col('opened_national_main','已開放／國立圖書館總館','館','stock_year_end'),col('opened_provincial_city_main','已開放／省市圖書館總館','館','stock_year_end'),col('opened_provincial_city_branch','已開放／省市圖書館分館','館','stock_year_end'),col('opened_county_main','已開放／縣市文化局圖書館','館','stock_year_end'),col('opened_county_branch','已開放／縣市文化局分館','館','stock_year_end'),col('opened_township_main','已開放／鄉鎮市區圖書館本館','館','stock_year_end'),col('opened_township_second_branch','已開放／鄉鎮市區第二館分館','館','stock_year_end'),col('opened_total','已開放／合計','館','stock_year_end','published_total'),col('not_opened_township','未開放／鄉鎮市圖書館','館','stock_year_end'),col('not_opened_city_district_branch','未開放／省轄市區分館','館','stock_year_end'),col('not_opened_total','未開放／合計','館','stock_year_end','published_total')]

def repair_count_scope(e,start,year):
    for r in e.records[start:]:
        r['population_scope']='臺閩地區原列國立、省市、縣市及鄉鎮市區公共圖書館；已開放與未開放分列'
        r['national_libraries_scope']='original_table_has_explicit_national_and_municipal_columns'
        r['entity_kind']='published_geographic_total' if r['entity_raw']=='總計' else 'county'
        if r['entity_raw']=='總計':r['aggregation_role']='published_total'
        r['source_notes'].append('已開放、未開放合計及底列總計與分項重疊，不能整表相加。')

def extract92(e):
    e.open(92)
    try:
        title='臺閩地區公共圖書館統計表（民國91年）'
        start=len(e.records)
        e.grid(3,'5',title,COUNTS_ROWS[:9],[136.13,171.89,207.13,242.37,277.61,312.85,348.09,383.33,418.57,453.81,489.06,524.47],evenly(567.23,17.008,9),COUNT_COLUMNS,2002,notes=['原章截至民國91年12月底；已開放總計504館、未開放12館為原表。'])
        e.grid(4,'5',title+'（續）',COUNTS_ROWS[9:],[135.71,171.47,206.71,241.95,277.19,312.43,347.67,382.91,418.15,453.39,488.63,524.05],evenly(297.94,17.008,17),COUNT_COLUMNS,2002,row_offset=9,notes=['PDF3同表完整續頁；總計列是來源刊載。'])
        repair_count_scope(e,start,2002)
        title='國立暨直轄市立公共圖書館經費、館藏與資源使用統計表（民國91年）'
        cols=[MONEY,col('library_count_with_parenthetical','圖書館數','館','stock_year_end'),{**HOLD,'metric_raw':'總館藏數'},col('borrower_visits','圖書借閱人次（表頭單位：人）','人','flow_calendar_year'),col('loans','圖書借閱冊數','冊','flow_calendar_year')]
        e.grid(5,'6',title,INSTITUTIONS[:4],[198.49,258.34,305.0,377.06,450.76,524.47],evenly(229.93,17.008,4),cols,2002,notes=['原註截至民國91年12月底之資料。','高雄包括高雄市立圖書館及高雄市立中正文化中心管理處。','館數的括號原值保留，不在單一總館數欄拆算；人次欄表頭單位為人，保留不改為人次。','館數括號字形超出欄線，文字擷取邊界延至相鄰空隙以免切斷括號數值。'])
        title='臺灣省各縣市鄉鎮市立圖書館館藏資料統計表（民國91年）'
        hold={**HOLD,'metric_raw':'館藏總數（含非書資料）'}
        e.grid(5,'7',title,COUNTIES[:21],[170.14,303.36,406.24,524.47],evenly(363.15,17.008,21),[POP,hold,HOLDPC],2002,notes=['人口數、館藏數均為各縣市民國91年12月資料。','館藏總數表頭明列含非書資料，不視為純圖書冊數；原表21縣市，無金門、連江列。'])
        entities=['臺北縣','桃園縣','新竹市','臺中縣','臺南縣','高雄縣','屏東縣','花蓮縣','澎湖縣','金門縣','連江縣','總計']
        title='縣市文化局（中心）圖書館統計比較表（民國90年及91年）'
        xs=[135.89,170.14,204.39,238.64,272.89,307.15,341.4,375.65,409.9,444.15,478.41,512.66,546.92]
        ys=[247.0,281.015,315.03,366.055,417.08,451.095,485.11,519.125,553.14,587.155,621.17,655.185,691.22]
        metrics=[HOLD,STAFF[0],STAFF[1],STAFF[2],STAFF[3],STAFF[4]]
        before=len(e.records)
        for ri in range(12):
            metric=metrics[ri//2];year=2001+ri%2
            for ci,entity in enumerate(entities):
                override={}
                if ri in (2,3) and ci==0:override['raw_override']='5(1)'
                if ri in (2,3) and ci==4:override['raw_override']=('5' if ri==2 else '4')+'（以工代職1位）'
                if ri in (6,7) and ci==10:override['raw_override']='各1人'
                e.emit(6,'8',title,ri+1,ci+1,entity,metric,[xs[ci],ys[ri],xs[ci+1],ys[ri+1]],year,notes=['原表僅列本次填送之11縣市文化局（中心）；總計格原刊留白，不能當完整全臺面板。','正式人員括號與以工代職註記保留，未把多數字字串硬轉單一值。'],**override)
                e.records[-1]['population_scope']='原表填送之縣市文化局（中心）圖書館；非各縣市所有公共館'
                if entity=='總計':e.records[-1]['entity_kind']='published_geographic_total';e.records[-1]['aggregation_role']='published_total'
        e.tables.append({'source_document_id':e.sid,'table':'8','pdf_page':6,'title':title,'metric_year_rows':12,'entity_columns':12,'physical_cells_emitted':len(e.records)-before,'expected_grid_slots':144,'scope_complete_for_this_page_grid':True})
        xs=[129.22,163.47,197.72,231.97,266.23,300.48,334.73,368.98,403.23,437.49,471.74,505.99,540.25]
        before=len(e.records)
        common_notes=['表8續頁；以民國92年8月15日截稿前填送縣市彙列，填送截止日不是數值年度。','經費圖書／期刊分列與合併原格依來源逐格保留，不複製合併格。']
        # Four counties print book and periodical amounts separately. All other
        # columns have one physical cell spanning both subrows, not two values.
        for yi,year in enumerate([2001,2002]):
            top=248.1+yi*102.17;mid=top+51.035;bottom=top+102.17
            for ci,entity in enumerate(entities):
                detailed=ci in (0,4,5,10)
                parts=[('books','圖書',top,mid),('periodicals','期刊',mid,bottom)] if detailed else [('books_and_periodicals','圖書期刊',top,bottom)]
                for pi,(key,label,y0,y1) in enumerate(parts):
                    column=col('spending_'+key,'經費／'+label,'元','annual_financial')
                    box=[xs[ci],y0,xs[ci+1],y1]
                    override={}
                    if detailed:
                        tokens=re.findall(r'[0-9][0-9,]*',re.sub(r'\(cid:\d+\)','',text_box(e.pdf.pages[6],box)))
                        if len(tokens)!=1:raise ValueError(('Unexpected split expense cell',entity,year,tokens))
                        override['raw_override']=tokens[0]+'（'+label+'）'
                    e.emit(7,'8',title+'（續）','expense-'+str(yi+1)+'-'+key,ci+1,entity,column,box,year,notes=common_notes,merged=None if detailed else {'subcolumns':['圖書','期刊'],'scope':'原表圖書期刊合併經費格'},**override)
                    e.records[-1]['population_scope']='原表填送之縣市文化局（中心）圖書館；非各縣市所有公共館'
                    if entity=='總計':e.records[-1]['entity_kind']='published_geographic_total';e.records[-1]['aggregation_role']='published_total'
        for ri in range(8):
            column=SERVICES[ri//2];year=2001+ri%2;y0=452.44+ri*34.0;y1=452.44+(ri+1)*34.0
            for ci,entity in enumerate(entities):
                override={}
                if ri==4 and ci==0:override['raw_override']='未統計'
                if ri in (6,7) and ci==7:override['raw_override']='隨時輔導\n無法計次'
                if ri in (6,7) and ci==10:override['raw_override']='每鄉各2'
                e.emit(7,'8',title+'（續）','service-'+str(ri+1),ci+1,entity,column,[xs[ci],y0,xs[ci+1],y1],year,notes=common_notes,**override)
                e.records[-1]['population_scope']='原表填送之縣市文化局（中心）圖書館；非各縣市所有公共館'
                if entity=='總計':e.records[-1]['entity_kind']='published_geographic_total';e.records[-1]['aggregation_role']='published_total'
        e.tables.append({'source_document_id':e.sid,'table':'8','pdf_page':7,'title':title+'（續）','expense_years':2,'expense_physical_cells_per_year':16,'service_year_rows':8,'entity_columns':12,'physical_cells_emitted':len(e.records)-before,'expected_physical_cells':128,'scope_complete_for_this_page_grid':True,'note':'依每縣市實際分列／合併的經費格記錄，不補成相同欄數。'})
    finally:e.close()

# These are source-image review references, not generated values or imputation.
# At runtime each nonblank value must be supported by actual OCR of the pinned
# source, except the one specifically documented independent image readback.
SCAN91_COUNTS = """2 1 49 _ _ _ _ 52 _ _ _
_ 2 17 _ _ _ _ 19 _ _ _
_ _ _ 1 _ 5 _ 6 _ _ _
_ _ _ 1 _ 29 36 66 _ 1 1
_ _ _ 1 _ 13 5 19 _ _ _
_ _ _ 1 _ 13 _ 14 _ _ _
_ _ _ 1 1 _ _ 2 3 _ 3
_ _ _ 1 _ 18 1 20 _ _ _
_ _ _ 1 _ 21 4 26 _ _ _
1 1 1 1 _ 8 2 14 _ _ _
_ 1 _ 1 _ 12 _ 14 _ 1 1
_ _ _ 1 _ 25 1 27 _ 1 1
_ _ _ 1 _ 20 _ 21 _ _ _
_ _ _ 1 _ 18 _ 19 _ _ _
_ _ _ 1 2 _ _ 3 2 _ 2
_ _ _ 1 _ 31 1 33 _ _ _
_ _ _ 2 7 _ _ 9 1 _ 1
_ _ _ 1 1 27 7 36 _ _ _
_ _ _ 1 1 32 2 36 _ 1 1
_ _ _ 1 _ 15 _ 16 _ 1 1
_ _ _ 1 _ 13 _ 14 _ _ _
_ _ _ 1 _ 12 1 14 _ _ _
_ _ _ 1 _ 5 _ 6 _ 1 1
_ _ _ 1 _ 4 _ 5 _ _ _
_ _ _ 1 1 3 _ 5 _ _ _
3 5 67 24 13 324 60 496 6 6 12"""
SCAN91_OTHER_REVIEW = {'91-4-12-1-1': '11,117,065', '91-4-12-1-2': '1', '91-4-12-1-3': '920,512', '91-4-12-1-4': '450,758', '91-4-12-1-5': '676,137', '91-4-12-2-1': '8,500,000', '91-4-12-2-2': '1 ( 1)', '91-4-12-2-3': '606,000', '91-4-12-2-4': '826,447', '91-4-12-2-5': '1,118,441', '91-4-12-3-1': '44,627,900', '91-4-12-3-2': '1 (49)', '91-4-12-3-3': '3,535,874', '91-4-12-3-4': '1,671,561', '91-4-12-3-5': '5,905,058', '91-4-12-4-1': '11,880,000', '91-4-12-4-2': '2 (17)', '91-4-12-4-3': '1,050,000', '91-4-12-4-4': '1,000,797', '91-4-12-4-5': '2,670,333', '91-4-13-1-1': '3,610,252', '91-4-13-1-2': '2,018,535', '91-4-13-1-3': '0.56', '91-4-13-2-1': '1,762,963', '91-4-13-2-2': '240,239', '91-4-13-2-3': '0.14', '91-4-13-3-1': '446,300', '91-4-13-3-2': '136,276', '91-4-13-3-3': '0.31', '91-4-13-4-1': '560,640', '91-4-13-4-2': '560,623', '91-4-13-4-3': '1.00', '91-4-13-5-1': '1,502,274', '91-4-13-5-2': '165,444', '91-4-13-5-3': '0.11', '91-4-13-6-1': '1,313,994', '91-4-13-6-2': '129,258', '91-4-13-6-3': '0.10', '91-4-13-7-1': '541,818', '91-4-13-7-2': '82,943', '91-4-13-7-3': '0.15', '91-4-13-8-1': '743,562', '91-4-13-8-2': '79,755', '91-4-13-8-3': '0.11', '91-4-13-9-1': '565,365', '91-4-13-9-2': '539,870', '91-4-13-9-3': '0.96', '91-4-13-10-1': '1,107,397', '91-4-13-10-2': '977,324', '91-4-13-10-3': '0.88', '91-4-13-11-1': '1,236,958', '91-4-13-11-2': '1,066,764', '91-4-13-11-3': '0.86', '91-4-13-12-1': '909,364', '91-4-13-12-2': '884,390', '91-4-13-12-3': '0.97', '91-4-13-13-1': '465,799', '91-4-13-13-2': '176,065', '91-4-13-13-3': '0.38', '91-4-13-14-1': '353,139', '91-4-13-14-2': '150,614', '91-4-13-14-3': '0.43', '91-4-13-15-1': '244,612', '91-4-13-15-2': '144,416', '91-4-13-15-3': '0.59', '91-4-13-16-1': '92,268', '91-4-13-16-2': '103,654', '91-4-13-16-3': '1.12', '91-4-13-17-1': '390,966', '91-4-13-17-2': '195,701', '91-4-13-17-3': '0.50', '91-4-13-18-1': '373,296', '91-4-13-18-2': '176,116', '91-4-13-18-3': '0.47', '91-5-13-19-1': '983,694', '91-5-13-19-2': '257,019', '91-5-13-19-3': '0.26', '91-5-13-20-1': '267,993', '91-5-13-20-2': '169,596', '91-5-13-20-3': '0.64', '91-5-13-21-1': '740,846', '91-5-13-21-2': '473,893', '91-5-13-21-3': '0.64'}
VISION_SWIFT = 'import Foundation\nimport Vision\nimport ImageIO\n\nfor file in CommandLine.arguments.dropFirst() {\n    let url = URL(fileURLWithPath: file)\n    let request = VNRecognizeTextRequest()\n    request.recognitionLevel = .accurate\n    request.recognitionLanguages = ["en-US"]\n    request.usesLanguageCorrection = false\n    request.minimumTextHeight = 0.002\n    let handler = VNImageRequestHandler(url: url, options: [:])\n    try handler.perform([request])\n    let observations = (request.results ?? []).map { observation -> [String:Any] in\n        let candidate = observation.topCandidates(1).first!\n        let box = observation.boundingBox\n        return ["text":candidate.string,"confidence":candidate.confidence,"bbox":[box.minX,1-box.maxY,box.maxX,1-box.minY]]\n    }\n    let response: [String:Any] = ["file":url.lastPathComponent,"engine":"Apple Vision VNRecognizeTextRequest accurate zh-Hant en-US","request_revision":request.revision,"observations":observations]\n    let result = try JSONSerialization.data(withJSONObject: response, options: [.sortedKeys])\n    print(String(data:result,encoding:.utf8)!)\n}\n'


def scan91_geometry():
    specs=[]
    def add(pn,table,entities,xs,ys,offset=0,panel=None):
        for ri,entity in enumerate(entities):
            for ci in range(len(xs)-1):
                specs.append({'key':f'91-{pn}-{table}-{ri+1+offset}-{ci+1}','pdf_page':pn,'table':table,'row':ri+1+offset,'column':ci+1,'entity':entity,'normalized_bbox':[xs[ci],ys[ri],xs[ci+1],ys[ri+1]],'panel':panel})
    add(3,'11',COUNTS_ROWS[:22],[.1354,.2202,.276,.3333,.4189,.4747,.5305,.6161,.6734,.7574,.8415,.8966],evenly(.474,(.9388-.474)/22,22))
    add(4,'11',COUNTS_ROWS[22:],[.1895,.274,.332,.388,.4735,.5295,.5854,.670,.727,.8113,.895,.949],evenly(.2518,(.3367-.2518)/4,4),22)
    add(4,'12',INSTITUTIONS[:4],[.303,.416,.529,.670,.811,.949],evenly(.474,.02125,4))
    add(4,'13',COUNTIES[:9],[.1895,.3028,.4161,.5295],evenly(.7358,(.928-.7358)/9,9),panel='left')
    add(4,'13',COUNTIES[9:18],[.6135,.7275,.8405,.949],evenly(.7358,(.928-.7358)/9,9),9,panel='right')
    add(5,'13',COUNTIES[18:20],[.1374,.2502,.3645,.4765],[.219,.23985,.2607],18,panel='left continuation')
    add(5,'13',COUNTIES[20:21],[.562,.675,.788,.900],[.219,.2607],20,panel='right continuation; physical cell spans two left-panel rows')
    return specs

def scan91_ocr(e,specs):
    """Perform fresh local Vision OCR; never require pre-existing OCR caches."""
    from PIL import Image,ImageOps,ImageDraw,ImageFont
    audit=e.root/'tmp/formal-ingest-20261028/ncl-early'
    audit.mkdir(parents=True,exist_ok=True)
    swift=audit/'vision_cells.swift';swift.write_text(VISION_SWIFT)
    originals={};images={}
    for pn in (3,4,5):
        page=e.ind[pn-1]
        try:im=page.render(scale=2.4).to_pil().convert('RGB')
        finally:page.close()
        im.save(audit/f'ed91-p{pn}-ocr.png');images[pn]=im
    # An external synthetic caption fixes short-line orientation when possible.
    # It is outside the source crop, excluded by its output coordinates, and is
    # never treated as source text. It does not supply any source digits.
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',28)
    files=[]
    for spec in specs:
        im=images[spec['pdf_page']];w,h=im.size;b=spec['normalized_bbox']
        px=[round(b[0]*w)+4,round(b[1]*h)+4,round(b[2]*w)-4,round(b[3]*h)-4]
        original=im.crop(px);crop=ImageOps.expand(original,border=24,fill='white')
        filename=spec['key']+'.png';crop.save(audit/filename);files.append(audit/filename)
        originals[spec['key']]={'crop_png_sha256':sha((audit/filename).read_bytes()),'pixel_bbox':px,'source_render_scale':2.4}
        canvas=Image.new('RGB',(max(500,crop.width+20),crop.height+160),'white')
        draw=ImageDraw.Draw(canvas);draw.text((24,24),'LIBRARY STATISTICS',font=font,fill='black');canvas.paste(crop,((canvas.width-crop.width)//2,120))
        filename='caption-'+filename;canvas.save(audit/filename);files.append(audit/filename)
    regions=[(3,[.1354,.474,.8966,.9388]),(4,[.1895,.2518,.949,.3367]),(4,[.303,.474,.949,.559]),(4,[.1895,.7358,.5295,.928]),(4,[.6135,.7358,.949,.928]),(5,[.1374,.219,.4765,.2607]),(5,[.562,.219,.900,.2607])]
    for i,(pn,b) in enumerate(regions):
        im=images[pn];w,h=im.size;px=[round(b[0]*w),round(b[1]*h),round(b[2]*w),round(b[3]*h)]
        region=im.crop(px);file=audit/f'region91-{i}.png';region.save(file);files.append(file)
    process=subprocess.run(['/usr/bin/swift',str(swift),*[str(p) for p in files]],text=True,capture_output=True,check=True,timeout=600)
    (audit/'vision-current-run.private.jsonl').write_text(process.stdout)
    responses={r['file']:r for line in process.stdout.splitlines() for r in [json.loads(line)]}
    candidates=collections.defaultdict(list)
    for spec in specs:
        for prefix,kind in [('', 'source_cell_crop'),('caption-','source_cell_crop_with_excluded_orientation_caption')]:
            response=responses[prefix+spec['key']+'.png']
            observations=[r for r in response['observations'] if prefix=='' or r['bbox'][1]>.35]
            raw='\n'.join(r['text'] for r in observations)
            candidates[spec['key']].append({'crop_kind':kind,'raw':raw,'confidence':min((r['confidence'] for r in observations),default=None),'request_revision':response['request_revision']})
        for i,(pn,b) in enumerate(regions):
            if pn!=spec['pdf_page']:continue
            sb=spec['normalized_bbox'];cx=(sb[0]+sb[2])/2;cy=(sb[1]+sb[3])/2
            if not (b[0]<=cx<=b[2] and b[1]<=cy<=b[3]):continue
            response=responses[f'region91-{i}.png'];observations=[]
            for row in response['observations']:
                rb=row['bbox'];x=b[0]+((rb[0]+rb[2])/2)*(b[2]-b[0]);y=b[1]+((rb[1]+rb[3])/2)*(b[3]-b[1])
                if sb[0]<=x<sb[2] and sb[1]<=y<sb[3]:observations.append(row)
            raw='\n'.join(r['text'] for r in observations)
            candidates[spec['key']].append({'crop_kind':'source_table_region','raw':raw,'confidence':min((r['confidence'] for r in observations),default=None),'request_revision':response['request_revision']})
    (audit/'scan91-review-index.private.json').write_bytes(stable({'source_sha256':e.spec['source_sha256'],'specs':specs,'source_image_crops':originals,'ocr_candidates':candidates,'review_reference_scope':'Specified original statistical cells only; Codex source-image review, not human transcription or independent OCR engines.'}))
    return candidates,originals

def scan_normalize(raw):
    return re.sub(r'\s|,','',raw).replace('（','(').replace('）',')')

def extract91(e):
    e.open(91)
    try:
        specs=scan91_geometry();candidates,originals=scan91_ocr(e,specs)
        count_ref=[r.split() for r in SCAN91_COUNTS.splitlines()]
        if len(count_ref)!=26 or any(len(r)!=11 for r in count_ref):raise ValueError('Scan review reference dimensions')
        counts_columns=[{**c,'metric_raw':c['metric_raw'].replace('省市圖書館','省市級圖書館').replace('文化局','文化中心')} for c in COUNT_COLUMNS[:8]+[COUNT_COLUMNS[9],COUNT_COLUMNS[8],COUNT_COLUMNS[10]]]
        table12=[MONEY,col('library_count_with_parenthetical','圖書館數','館','stock_year_end'),{**HOLD,'metric_raw':'總館藏數'},col('borrower_visits','圖書借閱人次（表頭單位：人）','人','flow_calendar_year'),col('loans','圖書借閱冊數','冊','flow_calendar_year')]
        table13=[POP,{**HOLD,'metric_raw':'館藏總數（含非書資料）'},HOLDPC]
        titles={'11':'臺閩地區公共圖書館統計表（民國90年）','12':'國立暨直轄市立公共圖書館經費、館藏與資源使用統計表（民國90年）','13':'臺灣省各縣市鄉鎮市立圖書館館藏資料統計表（民國90年）'}
        groups=collections.defaultdict(list);start=len(e.records)
        for spec in specs:
            table=spec['table'];row=spec['row'];ci=spec['column'];entity=spec['entity'];pn=spec['pdf_page'];key=spec['key']
            expected=count_ref[row-1][ci-1] if table=='11' else SCAN91_OTHER_REVIEW[key]
            if expected=='_':expected=''
            observed=candidates[key];matched=[r for r in observed if scan_normalize(r['raw'])==scan_normalize(expected)]
            manual_gap=key=='91-3-11-10-4'
            # The parent agent independently viewed this original crop after the
            # actual OCR runs consistently omitted its clearly printed digit 1.
            # Preserve this exceptional route instead of claiming OCR success.
            if not matched and not manual_gap:raise ValueError(('Fresh scan OCR differs from reviewed source literal',key,expected,observed))
            raw=matched[0]['raw'] if matched else expected
            if not expected:raw=''
            metric=(counts_columns if table=='11' else table12 if table=='12' else table13)[ci-1]
            page=e.pdf.pages[pn-1];nb=spec['normalized_bbox'];box=[nb[0]*page.width,nb[1]*page.height,nb[2]*page.width,nb[3]*page.height]
            notes=['原件為掃描影像，無內嵌文字層；以本機Apple Vision實際OCR並逐格對照原表影像。','各種裁格的Vision輸出是同一引擎，不當成獨立辨識引擎或人工複核。']
            if table=='11':notes+=['原章截至民國90年12月，已開放與未開放分列；空白不是零。','臺中市縣市文化中心圖書館原格1有OCR漏字，由主代理另行原圖讀回核定。']
            if table=='12':notes+=['統計資料截至民國90年12月；高雄含市立圖書館及中正文化中心管理處。','原表註3明列圓括弧內數字代表分館數；保留複合格原值，不複製成兩筆實際格。','借閱人次欄表頭單位為人，原樣保留。']
            if table=='13':notes+=['人口數及館藏總數為各縣市民國90年12月資料。','含非書資料，保留原館藏母體；原表21縣市，不含金門、連江。','PDF4左右兩欄18縣市，PDF5續表補臺中市、嘉義市、臺南市。']
            e.emit(pn,table,titles[table],row,ci,entity,metric,box,2001,notes=notes)
            r=e.records[-1];value,status=parse(raw)
            r.update(value_raw=raw,value=value,value_status=status)
            r['quality_flags']=['scanned_original_no_embedded_text','same_Vision_engine_variants_not_independent_OCR','Codex_image_review_not_human_review']
            if not expected:r['quality_flags'].append('source_blank_image_grid_reviewed_reason_unconfirmed')
            if len({scan_normalize(x['raw']) for x in observed if x['raw']})>1:r['quality_flags'].append('OCR_variant_disagreement_resolved_against_original_image')
            if manual_gap:r['quality_flags']+=['OCR_omitted_printed_glyph','second_agent_original_crop_readback_confirmed_1']
            if key=='91-4-11-26-7':r['quality_flags']+=['cell_OCR_180_degree_60_as_09_table_region_OCR_60_original_image_review','second_agent_original_crop_readback_confirmed_60']
            r['independent_check']={'method':'actual_local_Apple_Vision_OCR_plus_Codex_original_image_cell_review','matched':True,'independent_text_engines':False,'human_review':False,'OCR_supported_selected_literal':bool(matched),'source_image_crop_sha256':originals[key]['crop_png_sha256'],'source_render_scale':2.4,'OCR_candidates':observed,'source_image_review':{'reviewer':'Codex child agent; specified original table grids viewed','reviewed_literal':expected,'source_pinned_SHA':e.spec['source_sha256'],'independent_parent_agent_readback':'2026-10-28 original crop digit 1 confirmed through view_image' if manual_gap else None},'limitations':['OCR is not original truth; image review is AI-assisted, not a human transcription.','Repeated OCR variants do not constitute independent engines.']}
            if key=='91-4-11-26-7':r['independent_check']['source_image_review']['independent_parent_agent_readback']='2026-10-28 parent independently viewed original crop through view_image and confirmed 60, not 09; cell and table OCR differences preserved'
            if table=='11':
                r['population_scope']='臺閩地區國立、省市級、縣市文化中心及鄉鎮市區公共館，依原表欄別分開'
                r['national_libraries_scope']='original_table_has_explicit_national_and_municipal_columns';r['entity_kind']='county' if entity!='總計' else 'published_geographic_total'
                if entity=='總計':r['aggregation_role']='published_total'
                r['source_notes'].append('合計及底列總計與分項重疊，不能整表相加。')
            if table=='12':r['row_label_raw']=['央圖臺灣分館','臺中圖書館','臺北','高雄'][row-1]
            if table=='13':r['source_panel']=spec['panel'];r['population_scope']='原表臺灣省21縣市暨鄉鎮市立圖書館；含非書資料'
            groups[table,pn].append(r)
        for (table,pn),rows in groups.items():
            e.tables.append({'source_document_id':e.sid,'table':table,'pdf_page':pn,'title':titles[table],'source_rows':sorted(set(r['source_row'] for r in rows),key=int),'numeric_columns':11 if table=='11' else 5 if table=='12' else 3,'physical_cells_emitted':len(rows),'expected_physical_cells':len(rows),'scope_complete_for_this_page_grid':True,'OCR_method':'local Apple Vision accurate en-US; source cell, orientation-caption cell and source-table-region variants','image_review_method':'Codex viewed original table page grids; exceptional digit1 independently reread by parent agent','human_image_review':False})
        # Reconcile the source's published column totals using only actual
        # reported source values. This is a diagnostic, never a fill rule.
        for ci in range(1,12):
            values=[r['value'] for r in e.records[start:] if r['source_table']=='11' and int(r['source_column'])==ci and r['entity_raw']!='總計' and r['value_status']=='reported']
            total=next(r['value'] for r in e.records[start:] if r['source_table']=='11' and int(r['source_column'])==ci and r['entity_raw']=='總計')
            observed_sum=sum(decimal.Decimal(v) for v in values)
            if observed_sum!=decimal.Decimal(total):raise ValueError(('Scanned source published total discrepancy',ci,str(observed_sum),total))
            next(t for t in e.tables if t['source_document_id']==e.sid and t['table']=='11' and t['pdf_page']==4).setdefault('table11_reported_value_sum_diagnostics',[]).append({'column':ci,'reported_cells':len(values),'reported_value_sum':str(observed_sum),'published_total':total,'matched':True,'source_blanks_not_filled':True})
    finally:e.close()


def extract(root,source_root,editions):
    e=Extractor(root,source_root)
    functions={91:extract91,92:extract92,93:extract93,94:extract94}
    for edition in editions:
        if edition not in functions:raise ValueError('Edition not yet implemented: '+str(edition))
        functions[edition](e)
    ids=[r['cell_id'] for r in e.records]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate source-cell IDs')
    output=root/'derived/discovered_ncl_early_20261028_cells.jsonl'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(b''.join(stable(r) for r in e.records))
    metadata={'schema_version':'1.0.0','role':'reviewed_original_statistical_cells_for_canonical_adaptation','source_documents':e.documents,'completed_editions':editions,'tables':e.tables,'source_cells':len(e.records),'statuses':dict(collections.Counter(r['value_status'] for r in e.records)),'units':dict(collections.Counter(str(r['unit']) for r in e.records)),'independent_pdf_engine_checks':sum(r['independent_check']['method']=='positioned_pdfminer_vs_PDFium_cell_numeric_tokens' and r['independent_check']['matched'] for r in e.records),'numeric_values_invented':False,'unknowns_imputed':False,'cross_source_aggregation_permitted':False,'full_originals_or_authored_prose_distributed':False,'outputs':{'cells':{'path':str(output.relative_to(root)),'sha256':sha(output.read_bytes())}},'intentionally_excluded':['93卷表18私立公共圖書館統計，不納入本公立館批次。','各卷非指定表之署名論述、照片及計畫敘事未包含。'],'pending':[f'{edition}卷本次未選入執行；不表示官方無資料。' for edition in [91,92,93,94] if edition not in editions], 'scanned_cells_reviewed':sum(r['source_edition_roc']==91 for r in e.records), 'OCR_runtime_dependencies':['macOS Apple Vision framework; /usr/bin/swift','Python pdfplumber, pypdfium2 and Pillow'], 'human_review_claimed':False}
    (root/'derived/discovered_ncl_early_20261028_metadata.json').write_bytes(stable(metadata))
    return metadata

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--editions',nargs='+',type=int,default=[91,92,93,94]);a=p.parse_args()
    report=extract(a.root.resolve(),a.source_root.resolve(),a.editions);print(json.dumps({k:report[k] for k in ('completed_editions','source_cells','statuses','independent_pdf_engine_checks')},ensure_ascii=False))

if __name__=='__main__':main()
