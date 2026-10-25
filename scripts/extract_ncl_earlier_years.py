#!/usr/bin/env python3
"""Complete NCL 96/97-edition core operating-statistics tables, offline.

Original PDFs stay private. Uses table-specific, PDFium-reviewed positioned
glyphs; does not import or change previously delivered extractors or data.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import pdfplumber

BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'raw'/'ncl-earlier'
SOURCES={
 97:dict(title='中華民國九十七年圖書館年鑑：公共圖書館',publication_date='2008-12-01',url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565555623845321',accessed_raw='97年5月30日',accessed_date='2008-05-30',printed_start=35,pages=49),
 96:dict(title='中華民國九十六年圖書館年鑑：公共圖書館',publication_date='2007-12-01',url='https://www.ncl.edu.tw/librarianship-yearbook/0Q083565568411570887',accessed_raw='96年5月31日',accessed_date='2007-05-31',printed_start=27,pages=38),
}

def read_grid(page,spec):
    xs=spec['xs'];top,bottom=spec['ys']
    chars=[c for c in page.chars if c['text'].strip() and xs[0]<=(c['x0']+c['x1'])/2<xs[-1] and top<(c['top']+c['bottom'])/2<bottom]
    bands=[]
    for char in sorted(chars,key=lambda c:(c['top']+c['bottom'])/2):
        y=(char['top']+char['bottom'])/2
        if not bands or y-bands[-1][0]>2:bands.append([y,[char]])
        else:bands[-1][1].append(char)
    if len(bands)!=len(spec['rows']):raise ValueError((spec['id'],'row count',len(bands),len(spec['rows'])))
    if len(xs)!=len(spec['columns'])+1:raise ValueError((spec['id'],'column boundaries'))
    grid=[]
    for y,cs in bands:
        cells=[]
        for left,right in zip(xs,xs[1:]):
            cell=sorted([c for c in cs if left<=(c['x0']+c['x1'])/2<right],key=lambda c:c['x0'])
            raw=''.join(c['text'] for c in cell).strip()
            normalized=re.sub(r'[\s,]','',raw)
            status='blank' if not raw else ('numeric' if re.fullmatch(r'-?\d+(?:\.\d+)?',normalized) else 'marker')
            if status=='marker' and raw not in ['-','—','…','...']:raise ValueError((spec['id'],raw,'unreviewed symbol'))
            cells.append((raw,str(Decimal(normalized)) if status=='numeric' else None,status))
        grid.append((y,cells))
    return grid

def validate(spec,grid):
    checks=[];columns=spec['columns'];keyed={c['key']:i for i,c in enumerate(columns)}
    if spec['column_total_last_row']:
        for col,c in enumerate(columns):
            if c['aggregation_role']=='derived_ratio':continue
            published=grid[-1][1][col][1]
            if published is None:continue
            actual=sum(Decimal(cells[col][1]) for _,cells in grid[:-1] if cells[col][1] is not None)
            checks.append(dict(check='published_column_total_vs_explicit_entities',metric=c['key'],calculated=str(actual),published=published,passed=actual==Decimal(published),source_row=len(grid),source_column=col+2))
    for row,(entity,(_,cells)) in enumerate(zip(spec['rows'],grid),start=1):
        for total,parts in spec['row_relations']:
            pub=cells[keyed[total]][1]
            if pub is None:continue
            actual=sum(Decimal(cells[keyed[p]][1]) for p in parts if cells[keyed[p]][1] is not None)
            checks.append(dict(check='published_row_total_vs_explicit_components',entity=entity,metric=total,calculated=str(actual),published=pub,passed=actual==Decimal(pub),source_row=row,source_column=keyed[total]+2,blank_handling='sum_only_reported_numbers; original_blanks_remain_null'))
        if 'population' in keyed and cells[keyed['population']][1] is not None:
            denominator=Decimal(cells[keyed['population']][1])
            for num,ratio in [('holdings_mixed','holdings_per_capita'),('acquisition_spending','spending_per_capita'),('physical_loans','loans_per_capita')]:
                if num not in keyed or ratio not in keyed:continue
                a,b=cells[keyed[num]][1],cells[keyed[ratio]][1]
                if a is None or b is None or denominator==0:continue
                calculated=(Decimal(a)/denominator).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                checks.append(dict(check='printed_ratio_vs_recalculation',entity=entity,metric=ratio,calculated=str(calculated),published=b,passed=abs(calculated-Decimal(b))<=Decimal('.01'),source_row=row,source_column=keyed[ratio]+2))
    return checks

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--editions',nargs='+',type=int,default=[97,96]);args=parser.parse_args()
    specs=json.loads((RAW/'table-specifications.json').read_text())
    allrows=[];metadata=[];source_metadata=[]
    for edition in args.editions:
        source=SOURCES[edition]
        download=json.loads((RAW/f'yearbook-{edition}-download.json').read_text())
        path=RAW/f'yearbook-{edition}-public-library.pdf';digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=download['sha256']:raise ValueError('PDF differs from verified download metadata')
        source_metadata.append(dict(**download,source_url=source['url'],source_title=source['title'],publication_date=source['publication_date'],source_publication_edition_roc=edition,original_reported_access_date_raw=source['accessed_raw'],original_reported_access_date=source['accessed_date']))
        with pdfplumber.open(path) as pdf:
            for spec in [s for s in specs if s['source_edition_roc']==edition]:
                grid=read_grid(pdf.pages[spec['pdf_page']-1],spec)
                checks=validate(spec,grid)
                discrepancies=[c for c in checks if not c['passed']]
                year=spec['data_year'];is_counts='count_cross_tab' in spec['kind']
                for row,(entity,(y,cells)) in enumerate(zip(spec['rows'],grid),start=1):
                    original_fields={c['raw_label']:v[0] for c,v in zip(spec['columns'],cells)}
                    if entity=='總計':kind='national_total'
                    elif entity=='合計':kind='geographic_subgroup_total'
                    elif entity.startswith('國立') or entity in ['臺灣省政府圖書館','臺北市立圖書館','高雄市立圖書館','高雄市政府文化局中正文化中心']:kind='public_library_institution'
                    else:kind='county'
                    for col,(c,(raw,value,status)) in enumerate(zip(spec['columns'],cells),start=2):
                        flags=[]
                        if status=='blank':flags.append('source_blank')
                        elif status=='marker':flags.append('source_marker_unquantified')
                        if c['aggregation_role']=='published_total':flags.append('published_total_overlaps_components')
                        if kind in ['national_total','geographic_subgroup_total']:flags.append('published_total_overlaps_entity_rows')
                        if any(d['source_row']==row and d['source_column']==col for d in discrepancies):flags.append('official_value_differs_from_recalculation; preserved_unchanged')
                        if c['key']=='holdings_mixed' and value is not None and Decimal(value)==0:flags.append('official_zero_meaning_unconfirmed; not_replaced_by_missing')
                        if edition==96 and spec['table']=='1':flags.append('branch_reading_room_second_library_categories_not_equivalent_to_next_edition_branch_only')
                        if edition==96 and spec['table'] in ['3','4'] and (entity in ['臺北市','高雄市','臺北市立圖書館','高雄市立圖書館','高雄市政府文化局中正文化中心']):flags.append('municipal_institution_geographic_cross_table_overlap_do_not_sum')
                        allrows.append(dict(data_year=year,source_data_year_raw=f'{year-1911}年',source_edition_roc=edition,entity_raw=entity,entity_contextual_name=entity,entity_kind=kind,geography_vintage=f'{year}原表行政區；保留原列順序',
                            national_libraries_scope=spec['national_libraries_scope'],metric_id=spec['id'].replace('-','_')+'_'+c['key'],metric_raw=c['raw_label'],value_raw=raw,value=value,value_status=status,unit=c['unit'],unit_raw=c['unit_raw'],unit_basis=c['unit_basis'],temporal_kind=c['temporal_kind'],time_reference=f'{year}年全年' if c['temporal_kind'] in ['flow_calendar_year','annual_financial'] else f'{year}年12月底，依同章總述' if c['temporal_kind']=='stock_year_end' else f'原表{year}年；精確時點未另明示，不以上網日替代',
                            institutional_level=spec['kind'],aggregation_role=c['aggregation_role'],scope_note=spec['national_libraries_scope'],quality_flags=flags,original_fields=original_fields,
                            source_id=spec['id'],source_url=source['url'],source_download_url=download['source_download_url'],source_sha256=digest,source_local_path=str(path.relative_to(BASE)),source_agency='國家圖書館',source_title=source['title'],source_retrieved_at=download['source_retrieved_at'],source_pdf_page=spec['pdf_page'],source_printed_page=spec['printed_page'],source_table=spec['table'],source_table_title=spec['title'],source_row=row,source_column=col,source_column_path=c['raw_label'],source_row_label_verification='complete_PDFium_page_checked; table_specific_order',source_cell_bbox=[spec['xs'][col-2],round(y-6,3),spec['xs'][col-1],round(y+6,3)],source_cell_bbox_kind='positioned_glyph_band',source_locator=f'PDF page {spec["pdf_page"]}; printed page {spec["printed_page"]}; table {spec["table"]}; data row {row}; physical column {col}',
                            source_note=' '.join(spec['footnotes_raw']),source_footnotes_raw=spec['footnotes_raw'],source_original_access_date_raw=source['accessed_raw'],source_original_access_date=source['accessed_date'],extraction_status='positioned_PDF_glyphs_all_table_headers_rows_and_notes_PDFium_checked',license_status='not_confirmed',publication_date=source['publication_date']))
                metadata.append(dict(source_id=spec['id'],completed=True,completion_scope='all_printed_data_cells_of_specified_core_table',source_edition_roc=edition,data_year=year,pdf_page=spec['pdf_page'],printed_page=spec['printed_page'],table=spec['table'],title=spec['title'],data_rows=len(grid),numeric_columns=len(spec['columns']),source_cells=len(grid)*len(spec['columns']),value_status_counts=dict(Counter(v[2] for _,vs in grid for v in vs)),row_labels=spec['rows'],column_specifications=spec['columns'],column_boundaries=spec['xs'],scope_note=spec['national_libraries_scope'],scope_caveats=spec['scope_caveats'],source_footnotes_raw=spec['footnotes_raw'],source_url=source['url'],source_download_url=download['source_download_url'],source_sha256=digest,checks=checks,source_discrepancies=discrepancies,independent_review='pending_root_review'))
    outdir=BASE/'derived';outdir.mkdir(exist_ok=True)
    with (outdir/'ncl_earlier_years_long.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(allrows[0]));writer.writeheader()
        for row in allrows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    (outdir/'ncl_earlier_years_long.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in allrows))
    doc=dict(schema_version='1.0.0',checked_at='2026-10-25',completed_editions_roc=args.editions,source_cells=len(allrows),sources=source_metadata,tables=metadata,intentional_exclusion=['整冊及整章敘述文字、照片與圖像不公開。','特定閱讀空間改造、工程建設計畫成果表及個案不納入本批。','96卷表6臺中市便民措施清單、表7彰化增加開館服務時間個別措施表不屬本批全臺年度核心統計；未宣稱全章所有表均入庫。'],redistribution_scope='statistical_values_necessary_notes_and_source_locators_only; complete_authored_PDF_private')
    (RAW/'metadata.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'completed_editions_roc':args.editions,'tables':len(metadata),'cells':len(allrows),'statuses':dict(Counter(r['value_status'] for r in allrows)),'details':[dict(id=m['source_id'],rows=m['data_rows'],columns=m['numeric_columns'],cells=m['source_cells'],discrepancies=m['source_discrepancies']) for m in metadata]},ensure_ascii=False))

if __name__=='__main__':main()
