#!/usr/bin/env python3
"""Read the 39 annual cells in the NCL 2025 reading report's Table 1."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from lxml import html

TITLE = '近3年臺灣民眾公共圖書館使用情形分析'
REPORT_URL = 'https://www.ncl.edu.tw/tw/books/0Q112333768515788432'
REPORT_PDF = ('https://www.ncl.edu.tw/files/file_pool/1/0Q120145388038649336/'
              'df66cab6-10d6-4502-9fbb-6a8db59a339c.pdf')
REPORT_PDF_SHA256 = 'ad221212e57e12b5b8458455b765956b684f5bcd1808a1f8e83b33f0e8846288'
ONLINE_TABLE_URL = 'https://reading.ncl.edu.tw/web/front/page.do?pageId=74'
REPORT_SCOPE = '國立臺灣圖書館、國立公共資訊圖書館及22縣市公共圖書館；原表含國立圖書館數據'
EXPECTED_METRICS = (
    ('進館總人次', 'visits', '萬人次', 'published_total'),
    ('借閱總人次', 'loans-all-visits', '萬人次', 'published_total'),
    ('圖書借閱總人次', 'loans-books-visits', '萬人次', 'component'),
    ('買斷型電子書借閱總人次', 'loans-purchased-ebooks-visits', '萬人次', 'component'),
    ('租用型電子書借閱總人次', 'loans-rented-ebooks-visits', '萬人次', 'component'),
    ('計次型電子書借閱總人次', 'loans-pay-per-use-ebooks-visits', '萬人次', 'component'),
    ('借閱總冊數', 'loans-all-volumes', '萬冊', 'published_total'),
    ('圖書借閱總冊數', 'loans-books-volumes', '萬冊', 'component'),
    ('買斷型電子書借閱總冊數', 'loans-purchased-ebooks-volumes', '萬冊', 'component'),
    ('租用型電子書借閱總冊數', 'loans-rented-ebooks-volumes', '萬冊', 'component'),
    ('計次型電子書借閱總冊數', 'loans-pay-per-use-ebooks-volumes', '萬冊', 'component'),
    ('累計辦證數', 'cards-cumulative', '萬張', 'published_total'),
    ('網站資源使用次數', 'website-resource-use', '萬次', 'published_total'),
)
RAW_INTEGER = re.compile(r'(?:\d{1,3}(?:,\d{3})+|\d+)\Z')


def text(element):
    return ' '.join(element.text_content().split())


def read_table(source_bytes):
    document = html.fromstring(source_bytes)
    if '114年臺灣閱讀風貌年度報告' not in document.text_content():
        raise ValueError('Expected title of the official 2025 reading report')
    table_parents = document.xpath('//p[normalize-space(.)=$title]/parent::*', title=TITLE)
    if len(table_parents) != 1:
        raise ValueError('Expected one section heading for the official three-year table')
    section = table_parents[0]
    tables = section.xpath('./table')
    if len(tables) != 1:
        raise ValueError('Expected one table after the section heading')
    table = tables[0]
    unit_matches = [text(p) for p in section.xpath('./p') if '單位：萬，含國立圖書館數據' in text(p)]
    if len(unit_matches) != 1:
        raise ValueError('Original unit / inclusion note missing')
    rows = [row.xpath('./th|./td') for row in table.xpath('./thead/tr|./tbody/tr|./tr')]
    if len(rows) != 14:
        raise ValueError(f'Expected 13 indicators and one header, got {len(rows)} rows')
    headers = [text(cell) for cell in rows[0]]
    annual_headers = ['指標項目', '112年', '113年', '114年']
    if headers[:4] != annual_headers or headers[4] != '近2年 相較' or rows[0][4].get('colspan') != '2':
        raise ValueError(f'Changed year/comparison headers: {headers}')

    source_hash = hashlib.sha256(source_bytes).hexdigest()
    records = []
    comparison_cells = []
    for row_number, (row, (label, indicator, unit, role)) in enumerate(zip(rows[1:], EXPECTED_METRICS), 2):
        if len(row) not in (4, 6) or text(row[0]) != label:
            raise ValueError(f'Unexpected data row at DOM row {row_number}: {[text(c) for c in row]}')
        for column, (year, cell) in enumerate(zip(range(2023, 2026), row[1:4]), 2):
            literal = text(cell)
            if not RAW_INTEGER.fullmatch(literal) or cell.get('rowspan') or cell.get('colspan'):
                raise ValueError(f'Unexpected annual cell at DOM row {row_number}, column {column}: {literal}')
            records.append({
                'data_year': year,
                'source_edition_roc': 114,
                'source_title': '114年臺灣閱讀風貌年度報告',
                'source_publication_date': '2026-04-23',
                'source_publication_date_evidence': REPORT_URL,
                'online_table_publish_date': None,
                'source_url': ONLINE_TABLE_URL,
                'source_sha256': source_hash,
                'source_locator': f'HTML Table 1; DOM row {row_number}; cell {column}; {label} / {headers[column-1]}',
                'source_table': '1',
                'source_table_title': TITLE,
                'source_row': row_number,
                'source_field': headers[column-1],
                'source_column': column,
                'source_metric_label': label,
                'indicator': indicator,
                'unit': unit,
                'unit_raw': '萬',
                'unit_basis': '原表註以萬為量級，依原指標名稱及編輯說明辨識量詞',
                'raw_value': literal,
                'value': int(literal.replace(',', '')),
                'value_status': 'reported',
                'precision_scope': '原表萬位數，保留原刊精度',
                'aggregation_role': role,
                'geography': '全國',
                'population_scope': REPORT_SCOPE,
                'population_scope_evidence': f'{REPORT_PDF}#page=5',
                'crosscheck_pdf_page': 12,
                'crosscheck_printed_page': 13,
            })
        if len(row) == 6:
            spans = [int(cell.get('rowspan', '1')) for cell in row[4:]]
            expected_span = 3 if row_number in (5, 10) else 1
            if spans != [expected_span, expected_span]:
                raise ValueError(f'Changed year comparison grouping at DOM row {row_number}: {spans}')
            comparison_cells.append({
                'source_row': row_number,
                'rowspan': expected_span,
                'source_labels': [text(next_row[0]) for next_row in rows[row_number-1:row_number-1+expected_span]],
                'change_as_printed': text(row[4]),
                'rate_as_printed': text(row[5]),
            })
    if [cell['source_row'] for cell in comparison_cells] != [2, 3, 4, 5, 8, 9, 10, 13, 14]:
        raise ValueError('Published comparison cells missing or unexpectedly repeated')
    return records, comparison_cells


def verify_pdf(filename, rows):
    import logging

    from pypdf import PdfReader

    if hashlib.sha256(filename.read_bytes()).hexdigest() != REPORT_PDF_SHA256:
        raise ValueError('Report PDF official snapshot SHA-256 mismatch')
    logging.getLogger('pypdf').setLevel(logging.CRITICAL)
    report = PdfReader(filename)
    if len(report.pages) != 94:
        raise ValueError('Official report requires 94 PDF pages')
    methodology = re.sub(r'\s+', '', report.pages[4].extract_text(extraction_mode='layout'))
    for evidence in ('國立臺灣圖書館、國立公共資訊圖書館、22縣市公共圖書館', '114年1月1日至12月31日', '114年12月31日止之總數量'):
        if evidence not in methodology:
            raise ValueError(f'Methodology scope not found in PDF page 5: {evidence}')
    text_layer = report.pages[11].extract_text(extraction_mode='layout')
    lines = text_layer.splitlines()
    labels = ('進館總人次', '借閱總人次', '圖書借閱總人次', '買斷型電子書', '租用型電子書', '計次型電子書',
              '借閱總冊數', '圖書借閱總冊數', '買斷型電子書', '租用型電子書', '計次型電子書', '累計辦證數', '網站資源使用次數')
    data_lines = [line.strip() for line in lines if any(line.strip().startswith(label) for label in labels)
                  and re.search(r'\d', line)]
    if len(data_lines) != len(labels):
        raise ValueError(f'Expected 13 corresponding PDF rows, got {len(data_lines)}')
    for index, (label, line) in enumerate(zip(labels, data_lines)):
        values = re.findall(r'(?<!\d)\d+(?:,\d{3})*', line)[:3]
        if not line.startswith(label) or values != [row['raw_value'] for row in rows[index*3:index*3+3]]:
            raise ValueError(f'HTML/PDF mismatch for row {index+1}: {label} {values}')
    return {'method': 'pypdf layout layer of pinned official PDF', 'rows': 13, 'matching_cells': 39,
            'pdf_page': 12, 'printed_page': 13, 'pdf_sha256': REPORT_PDF_SHA256}


def read_pdf_table(filename):
    import pdfplumber

    source_bytes = filename.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != REPORT_PDF_SHA256:
        raise ValueError('Report PDF official snapshot SHA-256 mismatch')
    with pdfplumber.open(filename) as document:
        page = document.pages[11]
        words = page.extract_words(x_tolerance=2, y_tolerance=2)
    # Each annual value is right-aligned at one fixed column boundary. The
    # comparison columns start farther to the right, outside these ranges.
    column_boundaries = (206.95, 266.47, 326.00)
    annual_columns = []
    for boundary in column_boundaries:
        cells = [word for word in words if 260 < word['top'] < 650
                 and abs(word['x1'] - boundary) < 0.5 and RAW_INTEGER.fullmatch(word['text'])]
        cells.sort(key=lambda word: word['top'])
        if len(cells) != len(EXPECTED_METRICS):
            raise ValueError(f'Unexpected row count at PDF column boundary {boundary}: {len(cells)}')
        annual_columns.append(cells)
    records = []
    for row_index, (label, indicator, unit, role) in enumerate(EXPECTED_METRICS):
        cells = [column[row_index] for column in annual_columns]
        if max(cell['top'] for cell in cells) - min(cell['top'] for cell in cells) > 0.5:
            raise ValueError(f'PDF row {row_index + 1} values do not share a baseline')
        for column, (year, cell) in enumerate(zip(range(2023, 2026), cells), 2):
            literal = cell['text']
            box = tuple(round(cell[key], 3) for key in ('x0', 'top', 'x1', 'bottom'))
            records.append({
                'data_year': year,
                'source_edition_roc': 114,
                'source_title': '114年臺灣閱讀風貌年度報告',
                'source_publication_date': '2026-04-23',
                'source_publication_date_evidence': REPORT_URL,
                'source_url': f'{REPORT_PDF}#page=12',
                'source_page_url': REPORT_URL,
                'source_sha256': source_hash,
                'source_locator': f'PDF page 12; printed page 13; table 1; data row {row_index+1}; column {column}; bbox {",".join(f"{value:.3f}" for value in box)}',
                'source_table': '1',
                'source_table_title': TITLE,
                'source_pdf_page': 12,
                'source_printed_page': 13,
                'source_row': row_index + 1,
                'source_field': f'{year - 1911}年',
                'source_column': column,
                'source_bbox': box,
                'source_metric_label': label,
                'indicator': indicator,
                'unit': unit,
                'unit_raw': '萬',
                'unit_basis': '原表註以萬為量級，依原指標名稱及編輯說明辨識量詞',
                'raw_value': literal,
                'value': int(literal.replace(',', '')),
                'value_status': 'reported',
                'precision_scope': '原表萬位數，保留原刊精度',
                'aggregation_role': role,
                'geography': '全國',
                'population_scope': REPORT_SCOPE,
                'population_scope_evidence': f'{REPORT_PDF}#page=5',
                'source_retrieval_of_underlying_statistics': '2026-03-10',
            })
    verification = verify_pdf(filename, records)
    verification['primary_extractor'] = 'pdfplumber word coordinates and fixed source column boundaries'
    return records, verification, len(source_bytes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Official HTML snapshot (optional for PDF canonical output)')
    parser.add_argument('--pdf', type=Path)
    parser.add_argument('--canonical-pdf', action='store_true', help='Use pinned PDF as the canonical source; optionally cross-check HTML')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jsonl', type=Path)
    args = parser.parse_args()
    if args.canonical_pdf and not args.pdf:
        parser.error('--canonical-pdf requires --pdf')
    if not args.canonical_pdf and not args.source:
        parser.error('HTML mode requires --source')
    html_bytes = args.source.read_bytes() if args.source else None
    html_records, comparison_cells = read_table(html_bytes) if html_bytes else (None, None)
    if args.canonical_pdf:
        records, verification, source_size = read_pdf_table(args.pdf)
        if html_records:
            keys = ('data_year', 'source_metric_label', 'raw_value', 'unit')
            if any(tuple(a[k] for k in keys) != tuple(b[k] for k in keys) for a, b in zip(records, html_records)):
                raise ValueError('Official HTML and PDF canonical records disagree')
    else:
        records = html_records
        verification = verify_pdf(args.pdf, records) if args.pdf else None
        source_size = len(html_bytes)
    result = {
        'source_url': records[0]['source_url'].split('#')[0],
        'source_sha256': records[0]['source_sha256'],
        'source_bytes': source_size,
        'row_count': 13,
        'annual_cell_count': len(records),
        'publication_date': '2026-04-23',
        'publication_date_evidence': REPORT_URL,
        'html_page_date': None,
        'report_pdf_url': REPORT_PDF,
        'report_pdf_scope_evidence': '編輯說明（PDF第5頁、印頁6），2025年統計資料取得日為2026-03-10',
        'report_pdf_verification': verification,
        'html_crosscheck': {'url': ONLINE_TABLE_URL, 'sha256': hashlib.sha256(html_bytes).hexdigest(),
                            'matching_cells': len(html_records)} if args.canonical_pdf and html_records else None,
        'rights': {
            'scope': '統計事實，標示來源。保留原發布頁與原件連結，以觀測值長表發布；原PDF、HTML、插圖及文章保留於原發布網站。',
            'status': 'statistical_facts_only; source_document_reuse_license_unconfirmed',
            'evidence': 'https://www.tipo.gov.tw/tw/copyright/692-33512.html',
        },
        'notes': {
            'annual_precision': '原表「萬」；加總差異不倒推或更正。',
            'period_2025': '報告編輯說明資料年期間為2025全年或累計至年底；細項日期須依指標分辨。',
            'earlier_periods': '2023及2024照表頭標年度；本次未核較早年度的原申報期初／期末。',
            'excluded_year_comparison_columns': '另存原格，不視為單年度水準；電子書類別的同比合併格保留一次。',
        },
        'year_comparison_cells_excluded_from_annual_records': comparison_cells,
        'records': records,
    }
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.jsonl:
        args.jsonl.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in records), encoding='utf-8')
    print(json.dumps({'source_bytes': source_size, 'source_sha256': result['source_sha256'],
                      'annual_cells': len(records), 'pdf_crosscheck': verification,
                      'html_crosscheck': result['html_crosscheck']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
