#!/usr/bin/env python3
"""Extract four already-downloaded NCL tables; never modify older derived data.

Cell boundaries and row labels were checked against complete PDFium page renders.
No OCR digit guesses, blank-to-zero conversion, or hypothetical missing columns.
Requires pdfplumber. Run from any directory with the bundled Python runtime.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pdfplumber

BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'raw'/'ncl-historical'
COUNTIES=['臺北市','高雄市','臺中市','臺中縣','臺北縣','臺東縣','臺南市','臺南縣','宜蘭縣','花蓮縣','金門縣','南投縣','屏東縣','苗栗縣','桃園縣','高雄縣','基隆市','連江縣','雲林縣','新竹市','新竹縣','嘉義市','嘉義縣','彰化縣','澎湖縣']
INSTITUTIONS=['國立中央圖書館臺灣分館','國立臺中圖書館','臺灣省政府圖書館']
COUNT_COLUMNS=[
 ('national_main','國立圖書館／總館','國立','component'),
 ('national_branch','國立圖書館／分館','國立','component'),
 ('municipal_main','直轄市圖書館／總館','直轄市','component'),
 ('municipal_branch','直轄市圖書館／分館','直轄市','component'),
 ('county_main','縣市文化局圖書館／總館','縣市','component'),
 ('county_branch','縣市文化局圖書館／分館','縣市','component'),
 ('township_main','鄉鎮市區圖書館／總館','鄉鎮市區','component'),
 ('township_branch','鄉鎮市區圖書館／分館','鄉鎮市區','component'),
 ('other_provincial','其他／省政府圖書館','其他省設','component'),
 ('total_main','合計／總館','全部層級','published_total'),
 ('total_branch','合計／分館','全部層級','published_total'),
]
STAFF_COLUMNS=[
 ('professional_staff','人員／專業人員','人','component','stock_reference_date_not_explicit_in_table'),
 ('administrative_staff','人員／行政人員','人','component','stock_reference_date_not_explicit_in_table'),
 ('technical_staff','人員／技術人員','人','component','stock_reference_date_not_explicit_in_table'),
 ('temporary_staff','人員／臨時人員','人','component','stock_reference_date_not_explicit_in_table'),
 ('contract_staff','人員／約聘僱人員','人','component','stock_reference_date_not_explicit_in_table'),
 ('volunteers','人員／志工','人','component','stock_or_annual_person_count_unconfirmed'),
 ('student_staff','人員／工讀生','人','component','stock_reference_date_not_explicit_in_table'),
 ('other_staff','人員／其他','人','component','stock_reference_date_not_explicit_in_table'),
 ('all_staff','人員／合計','人','published_total','stock_reference_date_not_explicit_in_table'),
 ('physical_borrower_visits','圖書借閱／人次','人次','separate_flow','flow_calendar_year'),
 ('promotion_events','推廣活動／場次','場次','separate_flow','flow_calendar_year'),
 ('promotion_attendance','推廣活動／人次','人次','separate_flow','flow_calendar_year'),
]
SOURCES={
 98:dict(filename='yearbook-98-public-library.pdf',year=2008,title='中華民國九十八年圖書館年鑑：公共圖書館',publication_date='2009-12-01',url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565548575038748',download='https://www.ncl.edu.tw/files/file_pool/1/0Q083565548284341223/5c7f15c3-14f8-4b82-9c20-e88fc60ec73a.pdf'),
 99:dict(filename='yearbook-99-public-library.pdf',year=2009,title='中華民國九十九年圖書館年鑑：公共圖書館',publication_date='2011-06-01',url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565491338132165',download='https://www.ncl.edu.tw/files/file_pool/1/0Q083565512225393695/6d53fb99-39c2-4f24-8e27-8bee15671115.pdf'),
 100:dict(filename='yearbook-100-public-library.pdf',year=2010,title='中華民國一百年圖書館年鑑：公共圖書館',publication_date='2011-12-01',url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565466726779537',download='https://www.ncl.edu.tw/files/file_pool/1/0Q083565464178586012/3c355713-0489-4bdd-8c00-8431e1e9f5da.pdf'),
}
TABLES=[
 dict(id='ncl-gap-2008-t3-counts',edition=98,pdf_page=2,printed_page=78,table='3',kind='counts',title='全國公立公共圖書館統計表（97年）',ys=(158,525),xs=[93.18,126.83,158.19,190.54,222.91,252.16,281.62,316.98,352.34,421.07,453.43,481.93],source_note='資料來源：「公共圖書館統計系統」http://publibstat.lib.nctu.edu.tw/，上網日期：98.7.15。'),
 dict(id='ncl-gap-2008-t5-staff-services',edition=98,pdf_page=4,printed_page=80,table='5',kind='staff',title='全國各縣市暨鄉鎮圖書館人員及服務統計表（97年）',ys=(156,649),xs=[118.92,144.27,168.24,191.46,215.27,242.77,269.45,296.35,323.73,351.64,396.39,440.76,481.89],source_note='資料來源：「公共圖書館統計系統」http://publibstat.lib.nctu.edu.tw/，上網日期：98年7月15日。'),
 dict(id='ncl-gap-2009-t1-counts',edition=99,pdf_page=2,printed_page=74,table='1',kind='counts',title='全國公立公共圖書館統計表（98年）',ys=(137,523),xs=[100.63,153.07,184.98,217.56,258.94,299.06,335.91,370.35,434.41,461.41,490.394],source_note='資料來源：國家圖書館。「國家圖書館2009至2012中程發展策略計畫」。臺北市：該館，民98.4。'),
 dict(id='ncl-gap-2010-t1-counts',edition=100,pdf_page=2,printed_page=34,table='1',kind='counts',title='全國公立公共圖書館統計表（99年）',ys=(120,506),xs=[92.18,119.11,144.62,176.54,209.11,250.5,290.61,327.46,361.9,425.96,452.96,481.878],source_note='資料來源：公共圖書館統計系統。上網日期：100年5月15日，http://publibstat.lib.nctu.edu.tw/stat/showStat.aspx/。'),
]

def read_grid(page,spec):
    """Use individual positioned glyphs, not space-separated extracted words."""
    xs=spec['xs'];top,bottom=spec['ys']
    chars=[c for c in page.chars if c['text'].strip() and xs[0]<=(c['x0']+c['x1'])/2<xs[-1] and top<(c['top']+c['bottom'])/2<bottom]
    bands=[]
    for char in sorted(chars,key=lambda c:(c['top']+c['bottom'])/2):
        y=(char['top']+char['bottom'])/2
        if not bands or y-bands[-1][0]>2:bands.append([y,[char]])
        else:bands[-1][1].append(char)
    expected=26 if spec['kind']=='counts' else 29
    if len(bands)!=expected:raise ValueError((spec['id'],'row bands',len(bands),expected))
    grid=[]
    for y,cs in bands:
        values=[]
        for left,right in zip(xs,xs[1:]):
            cell=sorted([c for c in cs if left<=(c['x0']+c['x1'])/2<right],key=lambda c:c['x0'])
            raw=''.join(c['text'] for c in cell).strip()
            normalized=re.sub(r'[\s,]','',raw)
            status='blank' if not raw else ('reported' if re.fullmatch(r'\d+',normalized) else 'source_symbol')
            if status=='source_symbol' and raw not in ['-','—','…','...']:raise ValueError((spec['id'],raw,'unreviewed source symbol'))
            values.append((raw,str(int(normalized)) if status=='reported' else None,status))
        grid.append((y,values))
    return grid

def checks_for(spec,grid,columns,entities):
    checks=[]
    for col,column in enumerate(columns):
        observed=[int(values[col][1]) for _,values in grid[:-1] if values[col][1] is not None]
        published=grid[-1][1][col][1]
        if published is not None:
            actual=sum(observed)
            checks.append(dict(check='observed_entities_sum_to_national',metric=column[0],calculated=actual,published=int(published),passed=actual==int(published)))
    keyed={c[0]:i for i,c in enumerate(columns)}
    for row,(entity,(_,values)) in enumerate(zip(entities,grid),start=1):
        relations=[('total_main',[k for k in keyed if k.endswith('_main') and k!='total_main']+['other_provincial']),('total_branch',[k for k in keyed if k.endswith('_branch') and k!='total_branch'])] if spec['kind']=='counts' else [('all_staff',[x[0] for x in STAFF_COLUMNS[:8]])]
        for total,parts in relations:
            if total not in keyed:continue
            published=values[keyed[total]][1]
            if published is None:continue
            observed=[int(values[keyed[p]][1]) for p in parts if p in keyed and values[keyed[p]][1] is not None]
            actual=sum(observed)
            checks.append(dict(check='published_row_total_vs_explicit_components',entity=entity,source_row=row,metric=total,calculated=actual,published=int(published),passed=actual==int(published),blank_handling='only_reported_numeric_cells_summed; blanks_remain_null'))
    return checks

def main():
    allrows=[];metadata=[]
    for spec in TABLES:
        source=SOURCES[spec['edition']];path=RAW/source['filename']
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        with pdfplumber.open(path) as pdf:grid=read_grid(pdf.pages[spec['pdf_page']-1],spec)
        entities=COUNTIES+(['總計'] if spec['kind']=='counts' else INSTITUTIONS+['總計'])
        columns=COUNT_COLUMNS if spec['kind']=='counts' else STAFF_COLUMNS
        if spec['edition']==99:columns=[c for c in columns if c[0]!='national_branch']
        if len(columns)!=len(spec['xs'])-1:raise ValueError('columns do not match image-reviewed boundaries')
        retrieved=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()
        for row,(entity,(y,values)) in enumerate(zip(entities,grid),start=1):
            original_fields={c[1]:v[0] for c,v in zip(columns,values)}
            for col,(column,(raw,value,status)) in enumerate(zip(columns,values),start=2):
                is_count=spec['kind']=='counts'
                key,label=column[:2]
                metric_id='ncl_gap_count_table_'+key if is_count else 'ncl_gap_2008_t5_'+key
                unit='所' if is_count else column[2]
                temporal='stock_reference_date_not_explicit_in_table' if is_count else column[4]
                role=column[3]
                kind='national_total' if entity=='總計' else ('public_library_institution' if entity in INSTITUTIONS else 'county')
                scope='國立/直轄市/縣市/鄉鎮及省政府館按所在地×層級交叉列；合計與分項重疊' if is_count else '25舊縣市與3國立/省設館分列；全國總計與組成列重疊'
                allrows.append(dict(data_year=source['year'],entity_raw=entity,entity_contextual_name=entity,entity_kind=kind,geography_vintage=f'{source["year"]}原表25縣市',
                    national_libraries_scope='included_in_geographic_cross_tab' if is_count else ('separate_institution' if kind=='public_library_institution' else 'national_total' if kind=='national_total' else 'county_staff_services_separately_listed_from_national_institutions'),
                    metric_id=metric_id,metric_raw=label,value_raw=raw,value=value,value_status=status,unit=unit,unit_raw=None if is_count else unit,unit_basis='館數原表未另印單位；同章圖書館數量總述以所稱' if is_count else '原表表頭',temporal_kind=temporal,time_reference=f'原表民國{source["year"]-1911}年；精確人力/館數時點不由上網日代替' if not temporal.startswith('flow') else f'{source["year"]}年全年服務量',
                    institutional_level=column[2] if is_count else '人員及服務',aggregation_role=role,scope_note=scope,original_fields=original_fields,
                    source_id=spec['id'],source_url=source['url'],source_download_url=source['download'],source_sha256=digest,source_local_path=str(path.relative_to(BASE)),source_agency='國家圖書館',source_title=source['title'],source_retrieved_at=retrieved,
                    source_pdf_page=spec['pdf_page'],source_printed_page=spec['printed_page'],source_table=spec['table'],source_table_title=spec['title'],source_row=row,source_column=col,source_column_path=label,source_row_label_verification='transcribed_from_complete_PDFium_page_image',source_cell_bbox=[spec['xs'][col-2],round(y-6,3),spec['xs'][col-1],round(y+6,3)],source_cell_bbox_kind='positioned_glyph_band',
                    source_locator=f'PDF page {spec["pdf_page"]}; printed page {spec["printed_page"]}; table {spec["table"]}; data row {row}; physical column {col}',
                    source_note=spec['source_note'],extraction_status='positioned_pdf_glyphs_full_page_pdfium_reviewed',license_status='not_confirmed',publication_date=source['publication_date']))
        validations=checks_for(spec,grid,columns,entities)
        statuses=Counter(v[2] for _,vs in grid for v in vs)
        metadata.append(dict(table_id=spec['id'],completed=True,completion_scope='all_visible_data_cells_in_this_table_only',data_year=source['year'],edition_roc=spec['edition'],title=spec['title'],source_agency='國家圖書館',source_url=source['url'],source_download_url=source['download'],source_local_path=str(path.relative_to(BASE)),source_sha256=digest,source_retrieved_at=retrieved,pdf_page=spec['pdf_page'],printed_page=spec['printed_page'],source_table=spec['table'],data_rows=len(grid),numeric_columns=len(columns),data_cells=len(grid)*len(columns),value_status_counts=dict(statuses),source_row_names=entities,column_paths=[c[1] for c in columns],column_boundaries=spec['xs'],source_note=spec['source_note'],
            omitted_columns_in_source=['國立圖書館／分館：原表未刊此欄，不能補建為0或從合計倒推官方值'] if spec['edition']==99 else [],
            validation_checks=validations,source_discrepancies=[c for c in validations if not c['passed']],
            license_status='not_confirmed',redistribution_scope='derived_statistical_facts_with_attribution_only; original_PDF_and_images_private',visual_review='full_page_PDFium_render_headers_all_row_labels_and_source_note_checked_by_assistant',independent_review='pending_root_review'))
    (BASE/'derived').mkdir(exist_ok=True)
    out=BASE/'derived'/'ncl_gap_tables_long.csv'
    with out.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(allrows[0]));writer.writeheader()
        for row in allrows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    (BASE/'derived'/'ncl_gap_tables_long.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in allrows))
    doc=dict(schema_version='1.0.0',checked_at='2026-10-25',tables_completed=len(metadata),data_cells=len(allrows),tables=metadata,not_modified=['derived/ncl_historical_long.csv','derived/ncl_historical_rows.jsonl','scripts/fetch_ncl_historical.py'])
    (RAW/'gap-tables-metadata.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'completed_tables':len(metadata),'cells':len(allrows),'tables':[dict(id=m['table_id'],rows=m['data_rows'],columns=m['numeric_columns'],cells=m['data_cells'],statuses=m['value_status_counts'],source_discrepancies=m['source_discrepancies']) for m in metadata]},ensure_ascii=False))

if __name__=='__main__':main()
