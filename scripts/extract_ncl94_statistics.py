#!/usr/bin/env python3
"""Read 16 complete public-library physical cells from a pinned NCL PDF.

Bounded source extraction; neither a human reference nor a quality certification.
Labels and table scope were read from all original page images by an AI.
Numerical values below are obtained from two independently executed PDF engines.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium

SHA = '2db33efbce20154623b6ba7398e2cfa40af8116578264889d380ab41520c44cf'
URL = 'https://www.ncl.edu.tw/files/file_pool/1/0Q083565587711082557/9135e4ba-4fe3-440c-9a51-50ac088a552e.pdf'
CATALOGUE = 'https://www.ncl.edu.tw/librarianship-yearbook/0Q083565585645073973'


def digest(body):
    return hashlib.sha256(body).hexdigest()


def original_box_text(page, box):
    left, top, right, bottom = box
    chars = [c for c in page.chars
             if c['text'].strip() and left <= (c['x0']+c['x1'])/2 < right
             and top <= (c['top']+c['bottom'])/2 < bottom]
    lines = []
    for char in sorted(chars, key=lambda c: (c['top']+c['bottom'])/2):
        y = (char['top']+char['bottom'])/2
        line = next((line for line in lines if abs(line[0]-y) < 2), None)
        if line is None:
            line = [y, []]
            lines.append(line)
        line[1].append(char)
    return '\n'.join(''.join(c['text'] for c in sorted(cs, key=lambda c:c['x0']))
                     for _, cs in lines)


def tokens(raw):
    # Unmapped CID numbers identify glyphs; they are never numerical data.
    clean = re.sub(r'\(cid:\d+\)', '', raw)
    clean = clean.replace(',', '')
    return re.findall(r'(?<!\d)-?\d+(?:\.\d+)?', clean)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    body = args.source.read_bytes()
    if len(body) != 279122 or digest(body) != SHA:
        raise ValueError('Original bytes differ; review is required, no output written.')
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    result = []
    with pdfplumber.open(args.source) as document:
        other_document = pdfium.PdfDocument(args.source)
        try:
            if len(document.pages) != 12 or len(other_document) != 12:
                raise ValueError('Original page count differs.')

            def emit(table, page_number, printed_page, row, column, row_label,
                     column_label, box, unit, population, *, count_box=None,
                     unit_status='literal_quantity_unit_unprinted', notes=()):
                page = document.pages[page_number-1]
                original = original_box_text(page, box)
                other_page = other_document[page_number-1]
                try:
                    other_text = other_page.get_textpage()
                    try:
                        left, top, right, bottom = box
                        alternate = other_text.get_text_bounded(
                            left=left+.03, right=right-.03,
                            bottom=page.height-bottom+.03,
                            top=page.height-top-.03).strip()
                    finally:
                        other_text.close()
                finally:
                    other_page.close()
                a, b = tokens(original), tokens(alternate)
                wanted = 2 if count_box else 1
                if a != b or len(a) != wanted:
                    raise ValueError((table,row,column,'PDF numeric engines disagree',original,alternate,a,b))
                if any(not re.fullmatch(r'\d+', x) for x in a):
                    raise ValueError('Noninteger original token requires review.')
                main_value = int(a[0])
                parenthesized = int(a[1]) if count_box else None
                record = {
                    'cell_id': f'ncl-ed94-statistics/t{table}/p{page_number}/r{row}/c{column}',
                    'source_document_id': 'ncl-ed94-statistics',
                    'source_version_id': 'ncl-ed94-statistics@sha256:'+SHA,
                    'source_sha256': SHA, 'source_url': URL+'#page='+str(page_number),
                    'source_catalogue_url': CATALOGUE,
                    'source_pdf_page': page_number, 'source_printed_page': str(printed_page),
                    'source_table': str(table), 'source_row': str(row),
                    'source_column': str(column), 'source_row_label_raw':row_label,
                    'source_column_label_raw': column_label if str(table)!='145' else None,
                    'source_column_context':column_label,
                    'source_column_label_status':'literal_header' if str(table)!='145' else 'quantity_context_from_table_title_no_separate_header',
                    'source_row_index_scope':'selected_public_subgroup' if str(table)=='145' else 'whole_table_data_rows',
                    'source_bbox_points_top_origin': list(box),
                    'source_locator':f'PDF {page_number}; printed {printed_page}; table {table}; row {row}; column {column}; bbox '+','.join(map(str,box)),
                    'source_raw_pdfminer': original, 'source_raw_pdfium': alternate,
                    'value_raw': original,
                    'raw_transcription_method':'native_pdfminer_complete_numeric_cell_text',
                    'value': main_value, 'value_status':'reported',
                    'unit':unit, 'unit_raw':column_label if str(table)=='146' else None, 'unit_status':unit_status,
                    'period_raw':'民國93年', 'data_year':93+1911,
                    'period_basis':'literal_original_table_title',
                    'period_start':None, 'period_end':None,
                    'exact_period_unknown':True,
                    'population_scope':population,
                    'parenthesized_responding_libraries':None,
                    'source_edition_raw':'中華民國九十四年圖書館年鑑',
                    'cross_source_panel_permission':False,
                    'human_review_completed':False, 'human_double_collation_completed':False,
                    'labels_review':'AI visual read of full original table pages; not human collation',
                    'numeric_check':{'method':'positioned_pdfminer_vs_PDFium_numeric_tokens',
                                     'pdfminer_tokens':a,'pdfium_tokens':b,'matched':True},
                    'notes':list(notes),
                }
                if count_box:
                    response_raw = original_box_text(page, count_box)
                    if tokens(response_raw) != [a[1]]:
                        raise ValueError('Parenthesized response does not match full cell token.')
                    # Both PDF engines omit the rendered parentheses in this CMap.
                    # Only punctuation is restored from AI visual inspection; digits
                    # and commas remain the independently extracted source strings.
                    numeral_strings=re.findall(r'\d[\d,]*(?:\.\d+)?', original)
                    if len(numeral_strings)!=2:
                        raise ValueError('Cannot preserve the two literal source numeral strings.')
                    record['value_raw']=numeral_strings[0]+'\n（'+numeral_strings[1]+'）'
                    record['raw_transcription_method']='native_numbers_and_commas; parentheses_visually_read_by_AI_due_to_missing_CMap_glyphs'
                    record['parenthesized_responding_libraries'] = {
                        'value':parenthesized, 'raw_pdfminer':response_raw,
                        'source_bbox_points_top_origin':list(count_box),
                        'indicator_raw':'填答館數', 'unit':'館', 'unit_raw':'填答館數',
                        'unit_status':'literal_heading_填答館數_identifies_unit_館',
                        'is_total_library_count':False,
                        'population_scope':'原指標填答館數；原註不含分館，分館資料併總館',
                    }
                result.append(record)

            rows = ['國立','直轄市立','縣市立','鄉鎮、市、區立','社教館','私立','小計']
            ys = [238.0+i*15.59 for i in range(8)]
            for i,label in enumerate(rows,1):
                emit('145',5,440,i,1,'公共圖書館／'+label,'數量',
                     (220.0,ys[i-1],250.0,ys[i]),None,
                     '表145公共圖書館區塊／'+label+'；國家圖書館另列排除',
                     notes=('原註其他館型數含分館（大學圖書館例外）；此公共館子群含分館。',
                            '原列及小計分列，不能全部相加。'))

            xs=[142.302,227.328,312.355,397.381,482.47]
            public_rows=[('公立公共圖書館',256.54,289.85),('私立公共圖書館',289.85,323.16)]
            columns=[('館藏圖書冊數','冊'),('閱覽席位','席位'),('借閱人次','人次'),('借閱冊數','冊')]
            for row,(label,top,bottom) in enumerate(public_rows,2):
                for col,(heading,unit) in enumerate(columns,1):
                    box=(xs[col-1],top,xs[col],bottom)
                    count_box=(xs[col-1],top+16.65,xs[col],bottom)
                    emit('146',6,441,row,col,label,heading,box,unit,
                         '表146／'+label+'／'+heading+'之原報值；填答館數另為附屬量',
                         count_box=count_box,
                         unit_status='literal_column_label' if unit else 'printed_label_counting_unit_unresolved',
                         notes=('原格含主值與括號填答館數；保留同一physical cell完整原字串，不拆作兩個原格。',
                                '填答館數不含分館，分館統計資料併入總館；不能把括號當總館數。',
                                '國家圖書館另列，其專屬非書資料／網路人次註腳不自行套用本列。'))

            emit('147',11,446,1,2,'數量','公共',
                 (147.746,173.92,185.67,190.93),None,
                 '中華圖書資訊館際合作協會公共類會員；不是全臺公共館數或借閱量',
                 notes=('來源明印中華圖書資訊館際合作協會；國立及其他會員類型不與公共相加。',
                        '公私立、分館、生效日未明，保留未知。'))
        finally:
            other_document.close()
    if len(result)!=16 or len({x['cell_id'] for x in result})!=16:
        raise ValueError('Incomplete or duplicated physical cell batch.')
    numeric_count=sum(1+bool(x['parenthesized_responding_libraries']) for x in result)
    if numeric_count!=24:
        raise ValueError('Incomplete main/parenthesized numerical positions.')
    report={
        'schema_version':'1.0.0', 'role':'complete_source_subset_not_human_reference',
        'source_sha256':SHA,'source_bytes':len(body),'source_pdf_pages':12,
        'physical_cells':len(result),'numeric_positions':numeric_count,
        'physical_cell_count_by_table':{t:sum(x['source_table']==t for x in result) for t in ['145','146','147']},
        'original_row_scope_complete_for_selected_public_subsets':True,
        'numeric_engine_checks_all_matched':all(x['numeric_check']['matched'] for x in result),
        'human_review_completed':False,'human_double_collation_completed':False,
        'full_original_distributed':False,'public_publication_performed':False,
        'missing_values_imputed':False,'cross_source_comparability_certified':False,
        'source_arithmetic_check':{'table145_category_sum':sum(x['value'] for x in result if x['source_table']=='145' and x['source_row']!='7'),'table145_subtotal':next(x['value'] for x in result if x['source_table']=='145' and x['source_row']=='7'),'not_a_source_accuracy_proof':True},
        'cells':result,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['physical_cells','numeric_positions','physical_cell_count_by_table','numeric_engine_checks_all_matched']},ensure_ascii=False))


if __name__=='__main__':
    main()
