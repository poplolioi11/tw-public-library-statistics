#!/usr/bin/env python3
"""Download and extract verified historical public-library tables, with lineage.

Requires pypdf. Does not combine historical and present county boundaries.
Run with the bundled Python runtime documented in research/ncl-historical-verification.md.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen
from pypdf import PdfReader

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / 'raw' / 'ncl-historical'
DERIVED = BASE / 'derived'
COUNTIES = ['臺北市','高雄市','臺中市','臺中縣','臺北縣','臺東縣','臺南市','臺南縣','宜蘭縣','花蓮縣','金門縣','南投縣','屏東縣','苗栗縣','桃園縣','高雄縣','基隆市','連江縣','雲林縣','新竹市','新竹縣','嘉義市','嘉義縣','彰化縣','澎湖縣']
ENTITIES = COUNTIES + ['國立中央圖書館臺灣分館','國立臺中圖書館','臺灣省政府圖書館','總計']
SOURCES = [
    dict(id='ncl-yearbook-100-public', filename='yearbook-100-public-library.pdf', data_year=2010,
         url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565466726779537',
         download_url='https://www.ncl.edu.tw/files/file_pool/1/0Q083565464178586012/3c355713-0489-4bdd-8c00-8431e1e9f5da.pdf',
         publication_date='2011-12-01', title='中華民國一百年圖書館年鑑：公共圖書館'),
    dict(id='ncl-yearbook-99-public', filename='yearbook-99-public-library.pdf', data_year=2009,
         url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565491338132165',
         download_url='https://www.ncl.edu.tw/files/file_pool/1/0Q083565512225393695/6d53fb99-39c2-4f24-8e27-8bee15671115.pdf',
         publication_date='2011-06-01', title='中華民國九十九年圖書館年鑑：公共圖書館'),
    dict(id='ncl-yearbook-98-public', filename='yearbook-98-public-library.pdf', data_year=2008,
         url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565548575038748',
         download_url='https://www.ncl.edu.tw/files/file_pool/1/0Q083565548284341223/5c7f15c3-14f8-4b82-9c20-e88fc60ec73a.pdf',
         publication_date='2009-12-01', title='中華民國九十八年圖書館年鑑：公共圖書館'),
]
TABLE3 = [
    ('population','人口數（A）','人','stock_year_end'),
    ('holdings_mixed','圖書及非書資料收藏數量（冊）（B）','冊（原表；正文為冊、件、種混合）','stock_year_end'),
    ('acquisition_spending','全年購買圖書資料費（元）（C）','新臺幣元','annual_financial'),
    ('physical_loans','全年圖書資訊借閱冊數（D）','冊次','flow_calendar_year'),
    ('holdings_per_capita','每人擁有館藏冊書（B/A）','冊／人（原表混合館藏量）','derived_ratio'),
    ('acquisition_spending_per_capita','平均每人購買經費（C/A）','新臺幣元／人','derived_ratio'),
    ('loans_per_capita','平均每人外借冊數（D/A）','冊次／人','derived_ratio'),
]
TABLE4 = [
    ('professional_staff','專業人員','人','stock_year_end'),
    ('administrative_staff','行政人員','人','stock_year_end'),
    ('technical_staff','技術人員','人','stock_year_end'),
    ('temporary_staff','臨時人員','人','stock_year_end'),
    ('contract_staff','約聘僱人員','人','stock_year_end'),
    ('student_staff','工讀生','人','stock_year_end'),
    ('volunteers','志工','人','stock_or_annual_not_fully_confirmed'),
    ('other_staff','其他','人','stock_year_end'),
    ('all_staff','合計','人','stock_year_end'),
    ('physical_borrower_visits','圖書資訊（人次）','人次','flow_calendar_year'),
    ('promotion_events','推廣活動（場次）','場次','flow_calendar_year'),
    ('promotion_attendance','推廣活動（人次）','人次','flow_calendar_year'),
]
NUM = re.compile(r'(?<![\d.])[0-9][\d,]*(?:\.[0-9]+)?')

def numeric_lines(text, valid_lengths):
    result=[]
    lines=text.splitlines()
    consumed=set()
    for i,line in enumerate(lines):
        if i in consumed: continue
        numbers=NUM.findall(line)
        if 12 in valid_lengths and len(numbers)==10 and i+1<len(lines) and len(NUM.findall(lines[i+1]))==2:
            line+=' '+lines[i+1]
            numbers=NUM.findall(line)
            consumed.add(i+1)
        if len(numbers) in valid_lengths:
            # Excludes headings, references and multi-digit publication dates.
            first=Decimal(numbers[0].replace(',',''))
            if len(numbers)==3 and first < 100000:
                continue
            result.append((line,numbers))
    return result

def get_source(source, offline=False):
    RAW.mkdir(parents=True,exist_ok=True)
    path=RAW/source['filename']
    if not path.exists():
        if offline: raise FileNotFoundError(path)
        with urlopen(source['download_url'],timeout=60) as response:
            body=response.read()
        if not body.startswith(b'%PDF'): raise ValueError('Not a PDF: '+source['download_url'])
        path.write_bytes(body)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    return path,digest

def extract_historical(source,path,digest):
    pdf=PdfReader(path)
    result=[]
    year=source['data_year']
    specs=[('3',2,35,TABLE3),('4',3,36,TABLE4)]
    if year==2009:
        # 2009 header places volunteers BEFORE student staff; 2010 reverses them.
        staff_2009=TABLE4[:5]+[TABLE4[6],TABLE4[5]]+TABLE4[7:]
        specs=[('2',2,75,TABLE3),('3',3,76,staff_2009)]
    if year==2008:
        # This PDF lacks Chinese text mapping, but complete numeric rows are intact.
        # All 29 entity labels/order and the exclusion footnote were checked in page image.
        specs=[('4',2,79,TABLE3)]
    for table, pageindex, printedpage, definitions in specs:
        rawtext=pdf.pages[pageindex].extract_text() or ''
        is_financial=definitions==TABLE3
        pairs=numeric_lines(rawtext,{3,7} if is_financial else {12})
        if len(pairs)!=29: raise ValueError(f'table {table}: expected 29 complete rows, got {len(pairs)}')
        for ordinal, (entity,(rawline,numbers)) in enumerate(zip(ENTITIES,pairs),start=1):
            if is_financial and 26<=ordinal<=28:
                assert len(numbers)==3
                numbers=[None]+numbers+[None,None,None]
            if len(numbers)!=len(definitions): raise ValueError((table,entity,numbers))
            for column,((metric,label,unit,temporal),value) in enumerate(zip(definitions,numbers),start=1):
                if value is None: continue  # blank cells remain absent, never zero
                kind='national_total' if entity=='總計' else ('public_library_institution' if ordinal>=26 else 'county')
                entity_label='國立中央圖書館' if year==2009 and ordinal==26 else entity
                result.append(dict(data_year=year,entity_raw=entity_label,entity_contextual_name=entity,entity_kind=kind,geography_vintage=f'{year} pre-five-municipality table labels',
                    national_libraries_scope='included_in_national_total' if kind=='national_total' else ('separate_institution' if kind=='public_library_institution' else 'excluded_from_county_metrics'),
                    metric_id=metric,metric_raw=label,value_raw=value,value=str(Decimal(value.replace(',',''))),unit=unit,temporal_kind=temporal,
                    source_id=source['id'],source_url=source['url'],source_download_url=source['download_url'],source_sha256=digest,
                    source_local_path=str(path.relative_to(BASE)),source_agency='國家圖書館',source_retrieved_at=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),
                    source_pdf_page=pageindex+1,source_printed_page=printedpage,source_table=table,source_row=ordinal,source_column=column+1,
                    source_locator=f'PDF page {pageindex+1}; printed page {printedpage}; table {table}; data row {ordinal}',
                    raw_extracted_line=rawline,extraction_status='programmatic_text_with_table_header_and_footnote_image_checked',
                    license_status='not_confirmed',publication_date=source['publication_date']))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
    DERIVED.mkdir(parents=True,exist_ok=True)
    rows=[];documents=[]
    for source in SOURCES:
        path,digest=get_source(source,args.offline)
        extracted=[]
        if source['data_year'] in [2008,2009,2010]: extracted=extract_historical(source,path,digest)
        documents.append(dict(**source,local_path=str(path.relative_to(BASE)),sha256=digest,bytes=path.stat().st_size,
            source_retrieved_at=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),
            license_status='not_confirmed',license_url=None,license_evidence='官方可下載；尚未核得此署名專章開放授權，原檔僅本機研究留存。',
            extracted_long_rows=len(extracted),extraction_status={2010:'complete_tables_3_4',2009:'complete_tables_2_3',2008:'complete_table_4'}[source['data_year']],
            metadata_checked_at='2026-10-25'))
        rows.extend(extracted)
    out=DERIVED/'ncl_historical_long.csv'
    with out.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (RAW/'documents.json').write_text(json.dumps(documents,ensure_ascii=False,indent=2)+'\n')
    (DERIVED/'ncl_historical_rows.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    print(json.dumps({'long_rows':len(rows),'data_years':sorted({x['data_year'] for x in rows}),'csv':str(out)},ensure_ascii=False))

if __name__=='__main__': main()
