#!/usr/bin/env python3
"""Extract the complete public-library block (1996–2011) of DGBAS 2011.

Input is the official four-page cultural/leisure PDF, not search snippets.
Requires pdfplumber. The current server omits an intermediate certificate;
see research/ncl-historical-verification.md for verified download provenance.
"""
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pdfplumber

BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'raw'/'ncl-historical'
FILE=RAW/'dgbas-social-indicators-2011-cultural.pdf'
SOURCE='https://ws.dgbas.gov.tw/public/attachment/211231530971.pdf'
SOURCES=[
    dict(edition=2011,filename='dgbas-social-indicators-2011-cultural.pdf',url=SOURCE,pdf_first_index=0,printed_first=122,year_start=1996,year_end=2011,metric_map={17:17,18:18,32:32,33:33,34:34}),
    dict(edition=2008,filename='dgbas-social-indicators-2008.pdf',url='https://ws.dgbas.gov.tw/001/Upload/466/ebook/ebook_88839/pdf/full.pdf',pdf_first_index=131,printed_first=124,year_start=1993,year_end=2008,metric_map={17:17,18:18,32:32,33:33,34:34}),
    dict(edition=2005,filename='dgbas-social-indicators-2005.pdf',url='https://ws.dgbas.gov.tw/public/data/331311404571.pdf',pdf_first_index=105,printed_first=122,year_start=1991,year_end=2005,metric_map={16:17,30:32,31:33,32:34}),
]
METRICS={
  17:('dgbas_readers_thousand','圖書借閱人數','千人次','flow_calendar_year'),
  18:('dgbas_library_use_percentage','圖書館利用率','百分比','derived_ratio'),
  32:('dgbas_library_count','家數','家','stock_year_end_not_explicitly_verified'),
  33:('dgbas_libraries_per_100000','每10萬人圖書館數','家／10萬人','derived_ratio'),
  34:('dgbas_book_stock_thousand','藏書冊數','千冊','stock_year_end_not_explicitly_verified'),
}

def extract_source(source):
    file=RAW/source['filename']
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    retrieved=datetime.fromtimestamp(file.stat().st_mtime,timezone.utc).isoformat()
    rows=[]
    with pdfplumber.open(file) as pdf:
        for relative_page in range(4):
            pageindex=source['pdf_first_index']+relative_page
            page=pdf.pages[pageindex]
            words=page.extract_words()
            year_words=sorted([w for w in words if re.fullmatch(r'(19|20)\d{2}',w['text']) and 60<w['top']<80],key=lambda w:w['x0'])
            years=[int(w['text']) for w in year_words]
            start=source['year_start'];end=source['year_end']
            assert years==(list(range(start,start+9)) if relative_page%2==0 else list(range(start+9,end+1))),years
            metrics=[k for k,v in source['metric_map'].items() if (v in [17,18])==(relative_page<2)]
            # A pair of facing pages shares row baselines. The English labels merge
            # ordinal 17/18 into the following word, so locate the exact Chinese row.
            reference=pdf.pages[pageindex-(relative_page%2)]
            reference_words=reference.extract_words()
            for ordinal in metrics:
                marker=next(w for w in reference_words if re.match(r'^'+str(ordinal)+r'(?!\d)',w['text']) and w['x0']<40)
                for col,(year,head) in enumerate(zip(years,year_words),start=1):
                    center=(head['x0']+head['x1'])/2
                    step=(year_words[1]['x0']-year_words[0]['x0'])
                    # Values align to year-header right edge. The final English
                    # stock cell abuts '1,000 volumes', so never crop to mid-gap.
                    crop=page.crop((center-step/2,marker['top']-1,head['x1']+0.4,marker['bottom']+1))
                    value_raw=(crop.extract_text(x_tolerance=1) or '').strip()
                    numeric=re.sub(r'\s+','',value_raw)
                    missing=numeric in ['…','...','-','—']
                    if not missing and not re.fullmatch(r'\d+(?:\.\d+)?',numeric):raise ValueError((pageindex+1,ordinal,year,value_raw))
                    canonical=source['metric_map'][ordinal]
                    metric,label,unit,temporal=METRICS[canonical]
                    caveats=[]
                    if canonical in [32,33] and year in [1998,1999]:
                        caveats.append('1998年、1999年臺灣省公共圖書館不含分館（原註⑨）。')
                    if canonical in [17,18] and year<=1999:
                        caveats.append('原中文註⑤：1999以前，圖書館借閱人數之定義為閱覽人數；英文註的敘述方向與中文不一致，未擅自調整。')
                    caveats.append('主計總處跨年彙整與國圖年鑑可能為不同修訂版；原值分開保存。')
                    rows.append(dict(data_year=year,entity_raw='全國',entity_kind='national_total',geography_vintage='官方表臺灣地區範圍；各年國立館納入細節未逐年確認',
                        metric_id=metric,metric_raw=label,value_raw=value_raw,value=None if missing else str(Decimal(numeric)),value_status='not_available_in_source' if missing else 'reported',unit=unit,temporal_kind=temporal,
                        source_id=f'dgbas-social-indicators-{source["edition"]}',source_url=source['url'],source_download_url=source['url'],source_edition=source['edition'],
                        source_local_path=str(file.relative_to(BASE)),source_agency='行政院主計總處' if source['edition']==2011 else '行政院主計處',source_sha256=digest,source_retrieved_at=retrieved,
                        source_pdf_page=pageindex+1,source_printed_page=source['printed_first']+relative_page,source_table='文化與休閒／公立公共圖書館',source_row=ordinal,source_column=col,
                        source_locator=f'PDF page {pageindex+1}; printed page {source["printed_first"]+relative_page}; public libraries row {ordinal}; year {year}; year-column {col}',
                        caveats=' '.join(caveats),extraction_status='programmatic_coordinate_cells_with_year_and_metric_validation',license_status='verified_open',license_code='OGDL-1.0_site_declaration',license_url='https://www.stat.gov.tw/cp.aspx?n=3164',publication_date=''))
    assert len(rows)==len(source['metric_map'])*(source['year_end']-source['year_start']+1)
    return rows

def main():
    rows=[];documents=[]
    for source in SOURCES:
        extracted=extract_source(source);rows.extend(extracted)
        file=RAW/source['filename']
        documents.append(dict(source_id=f'dgbas-social-indicators-{source["edition"]}',title=f'社會指標統計年報{source["edition"]}：文化與休閒',source_agency='行政院主計總處' if source['edition']==2011 else '行政院主計處',url=source['url'],download_url=source['url'],
            local_path=str(file.relative_to(BASE)),sha256=extracted[0]['source_sha256'],bytes=file.stat().st_size,source_retrieved_at=extracted[0]['source_retrieved_at'],
            extracted_pdf_pages=list(range(source['pdf_first_index']+1,source['pdf_first_index']+5)),printed_pages=f'{source["printed_first"]}–{source["printed_first"]+3}',
            data_year_min=source['year_start'],data_year_max=source['year_end'],complete_public_library_metrics=list(source['metric_map']),long_rows=len(extracted),
            license_status='verified_open',license_code='OGDL-1.0_site_declaration',license_url='https://www.stat.gov.tw/cp.aspx?n=3164',
            license_evidence='主計總處政府網站資料開放宣告：網站上刊載之所有資料與素材，採政府資料開放授權條款-第1版發布；另有特別聲明之第三方著作除外。',
            license_evidence_file='raw/ncl-historical/dgbas-open-data-declaration.html',license_scope='本次擷取的官方公立公共圖書館統計表；未將報告其他第三方文章或圖像納入。',
            excluded_content='僅擷取公立公共圖書館；其他文化休閒與學校資料未匯入。'))
    DERIVED=BASE/'derived';DERIVED.mkdir(exist_ok=True)
    with (DERIVED/'dgbas_historical_long.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (DERIVED/'dgbas_historical_rows.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    (RAW/'dgbas-documents.json').write_text(json.dumps(documents,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'long_rows':len(rows),'data_year_min':min(x['data_year'] for x in rows),'data_year_max':max(x['data_year'] for x in rows),'editions':[s['edition'] for s in SOURCES]},ensure_ascii=False))

if __name__=='__main__':main()
