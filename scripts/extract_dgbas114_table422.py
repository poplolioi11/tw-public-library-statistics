#!/usr/bin/env python3
"""Reproduce the 312 published positions in DGBAS Yearbook 114, Table 4-22."""
import argparse
import hashlib
from collections import Counter
from importlib.metadata import version
import json
from pathlib import Path
import re
import sys

import pdfplumber
import pypdfium2 as pdfium
from pypdf import PdfReader

SOURCE_ID = 'dgbas-yearbook-114'
URL = 'https://ws.dgbas.gov.tw/001/Upload/463/relfile/11160/229649/ch4.pdf'
CATALOGUE = 'https://ebook.dgbas.gov.tw/News_Content_Ebook.aspx?n=4480&s=236722'
SHA256 = 'dabbb914ad186f8e59af661271ba0adca12a09bb3b4c36f1f4d07903f7d5fe51'
SOURCE_BYTES = 2657979
PAGE, PRINTED_PAGE = 29, '105'
TABLE = '4-22'
TITLE = '國家圖書館及公立公共圖書館概況'
STATISTICS = (
    ('總館', '所'), ('分館', '所'), ('區館', '所'), ('圖書', '千冊'), ('期刊', '種'),
    ('電子資源', '種'), ('全年圖書資訊借閱人次', '千人次'), ('全年圖書資訊借閱冊數', '千冊'),
)
ANNUAL_LABELS = tuple(f'{roc}年' for roc in range(100, 115))
INSTITUTION_LABELS = (
    '國家圖書館', '公立公共圖書館', '新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市',
    '宜蘭縣', '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義縣', '屏東縣',
    '臺東縣', '花蓮縣', '澎湖縣', '基隆市', '新竹市', '嘉義市', '金門縣', '連江縣',
)
LABELS = ANNUAL_LABELS + INSTITUTION_LABELS
BOUNDS = (154, 191, 242, 284, 336, 383, 438, 495, 548)
METHOD = 'pdfplumber_positioned_words_vs_PDFium_fixed_column_regions_vs_pypdf_layout'
SCOPE = {
    'national_total': '原刊年度全國總列含國家圖書館及公立公共圖書館。年底存量與全年借閱分欄。',
    'public_library_institution': '原刊另列國家圖書館。此列與公立公共圖書館小計分開保存。',
    'national_public_library_subtotal': '原刊公立公共圖書館合計含國立公共資訊圖書館及國立臺灣圖書館，國家圖書館另列。',
    'county_official_table': '原刊公立公共圖書館分縣市列，保留當時行政區與原欄口徑。',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def clean(raw):
    return re.sub(r'\s+', '', raw)


def jsonfile(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def jsonl(path, records):
    with path.open('w', encoding='utf-8') as stream:
        for row in records:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')


def layout_rows(source):
    """Extract the original row/column reading order using the pypdf layout engine."""
    table_lines = PdfReader(source).pages[PAGE - 1].extract_text(extraction_mode='layout').splitlines()
    rows = []
    for line in table_lines:
        fields = re.split(r'\s{2,}', line.strip())
        if fields and clean(fields[0]) in LABELS:
            label = clean(fields[0])
            require(len(fields) == 9, f'pypdf layout row does not have eight columns: {fields!r}')
            rows.append((label, fields[1:]))
    require(tuple(label for label, _ in rows) == LABELS, 'pypdf layout row inventory or order differs')
    return dict(rows)


def entity(label, row):
    if row <= len(ANNUAL_LABELS):
        return '全國', 'national_total', int(label.removesuffix('年')) + 1911
    if label == '國家圖書館':
        return label, 'public_library_institution', None
    if label == '公立公共圖書館':
        return label, 'national_public_library_subtotal', None
    return label, 'county_official_table', None


def page_headings(page):
    header = page.crop((0, 0, page.width, 138)).extract_text(x_tolerance=1, y_tolerance=1)
    compact = clean(header)
    require('表4-22' + TITLE in compact, 'Original table title differs')
    require(PRINTED_PAGE in compact, 'Original printed page was not found')
    require('年底及機關別' in compact, 'Missing original common row header')
    units = re.findall(r'\(([^()]+)\)', compact)
    require(units == [unit for _, unit in STATISTICS], 'Original printed column units differ')
    require(all(fragment in compact for fragment in ('總館', '分館', '區館', '圖書', '期刊', '電子資源', '全年圖書資訊', '借閱人次', '借閱冊數')),
            'Original column headings differ')


def extract(source, document, project):
    sys.path.insert(0, str(project / 'scripts'))
    from build_discovered_20261028 import adapt
    from extract_discovered_central_20261028 import base, parse

    alternate = layout_rows(source)
    cells = []
    with pdfplumber.open(source) as original, pdfium.PdfDocument(source) as independent:
        require(len(original.pages) == len(independent) == 36, 'Original chapter page count differs')
        page = original.pages[PAGE - 1]
        page_headings(page)
        words = page.extract_words(x_tolerance=1, y_tolerance=1)
        labels = sorted(
            (w for w in words if w['x1'] < BOUNDS[0] and 135 < w['top'] < 700 and w['text'] in LABELS),
            key=lambda w: w['top'],
        )
        require(tuple(word['text'] for word in labels) == LABELS, 'Official table row inventory or order differs')
        footnote = page.crop((0, labels[-1]['bottom'] + 1, page.width, page.height)).extract_text(
            x_tolerance=1, y_tolerance=1
        )
        require(all(s in clean(footnote) for s in (
            '公立公共圖書館含國立公共資訊圖書館及國立臺灣圖書館', '資料來源：國家圖書館、國立公共資訊圖書館'
        )), 'Original statistical scope note differs')
        text_page = independent[PAGE - 1].get_textpage()
        try:
            for row, word in enumerate(labels, 1):
                label = word['text']
                geography, kind, year = entity(label, row)
                for column, (metric, unit) in enumerate(STATISTICS, 1):
                    left, right = BOUNDS[column - 1:column + 1]
                    tokens = sorted(
                        (token for token in words if abs(token['top'] - word['top']) < 1
                         and left <= token['x0'] and token['x1'] <= right),
                        key=lambda token: token['x0'],
                    )
                    raw = ' '.join(token['text'] for token in tokens)
                    other = text_page.get_text_bounded(
                        left=left, right=right, bottom=page.height-word['bottom']-1, top=page.height-word['top']+1
                    ).strip()
                    layout = alternate[label][column - 1]
                    value, status = parse(raw)
                    require(clean(raw) == clean(other) == clean(layout)
                            and parse(other) == parse(layout) == (value, status),
                            f'{label}, {metric}: {raw!r} != {other!r} != {layout!r}')
                    box = [
                        round(min(t['x0'] for t in tokens), 4), round(min(t['top'] for t in tokens), 4),
                        round(max(t['x1'] for t in tokens), 4), round(max(t['bottom'] for t in tokens), 4),
                    ]
                    cell = base(document, TABLE, row, column, label, metric, raw, value, status,
                                year, unit, 'flow_calendar_year' if column >= 7 else 'stock_year_end',
                                geography, kind, PAGE, PRINTED_PAGE)
                    cell['source_locator'] += '; bbox ' + ','.join(f'{coordinate:.4f}' for coordinate in box)
                    cell.update(
                        source_table_title=TITLE, source_cell_bbox=box,
                        source_edition=document['edition_raw'], source_edition_roc=114,
                        source_table_year_context=2025,
                        source_year_label_raw=label if year is not None else None,
                        source_period_header_raw='年底及機關別',
                        source_publication_month=document['publication_month'],
                        source_coverage_note_raw=' '.join(footnote.splitlines()),
                        population_scope=SCOPE[kind],
                        national_libraries_scope='annual_total_includes_NCL_public_subtotal_includes_NLPI_NTL_per_source_note',
                        aggregation_role={
                            'national_total': 'published_total',
                            'national_public_library_subtotal': 'published_subtotal',
                        }.get(kind, 'source_component'),
                        independent_check={'method': METHOD, 'matched': True,
                                           'pdfplumber_raw': raw, 'pdfium_raw': other, 'pypdf_layout_raw': layout},
                    )
                    if year is None:
                        cell['period_raw'] = None
                        cell['period_status'] = 'institution_rows_after_last_annual_row_year_not_repeated'
                        cell['source_notes'].append('機關與縣市分列位於114年之後。另記2025版面脈絡，個別列的原刊年度未重印。')
                    cells.append(cell)
        finally:
            text_page.close()

    require(len(cells) == 312 and len({c['cell_id'] for c in cells}) == 312, 'Table 4-22 must contain 312 unique positions')
    summary = {key: sum(cell[key] is None for cell in cells) for key in ('data_year', 'value')}
    require(summary['data_year'] == 192, 'Expected 24 subrows of eight cells without repeated years')
    require(all((cell['value'] is None) == (cell['value_status'] != 'reported') for cell in cells),
            'A source marker or blank was interpreted as a value')
    probes = {(cell['row_label_raw'], cell['column_label_raw']): cell['value'] for cell in cells}
    require(probes['114年', '全年圖書資訊借閱冊數'] == '131895'
            and probes['公立公共圖書館', '全年圖書資訊借閱冊數'] == '131781'
            and probes['公立公共圖書館', '全年圖書資訊借閱人次'] == '45119',
            '2025 national and public subtotal anchors differ')
    canonical = [dict(adapt(cell, document), publication_year=2026) for cell in cells]
    return cells, canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True, help='Private project root containing canonical code')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--retrieved-at', required=True, help='ISO 8601 time from the original download receipt')
    options = parser.parse_args()
    body = options.source.read_bytes()
    require(len(body) == SOURCE_BYTES and hashlib.sha256(body).hexdigest() == SHA256,
            'Official original differs from pinned Table 4-22 review')
    document = {
        'candidate_id': SOURCE_ID, 'title': '中華民國統計年鑑114年版第四章表4-22',
        'edition_raw': '中華民國統計年鑑114年版', 'publication_month': '2026-09',
        'official_url': URL, 'catalogue_url': CATALOGUE, 'source_sha256': SHA256,
        'source_version_id': f'{SOURCE_ID}@sha256:{SHA256}', 'source_bytes': SOURCE_BYTES,
        'source_local_path': 'raw/dgbas-yearbook-114/ch4.pdf', 'retrieved_at': options.retrieved_at,
        'rights_status': 'published_statistical_facts_only_full_document_not_redistributed',
        'scope': '第四章表4-22之整表39列、8欄。保留各地域及機關之原載分類及單位。',
        'cautions': ['保留原刊總列與小計，各列依來源口徑使用。短橫與留白維持缺值。'],
    }
    cells, rows = extract(options.source, document, options.project)
    dest = options.output_dir
    dest.mkdir(parents=True, exist_ok=True)
    jsonfile(dest / 'documents.json', {'documents': [document]})
    jsonl(dest / 'source_cells.jsonl', cells)
    jsonl(dest / 'observations.jsonl', rows)
    receipt = {
        'source_id': SOURCE_ID, 'source_url': URL + '#page=29', 'source_sha256': SHA256,
        'pdf_page': PAGE, 'printed_page': PRINTED_PAGE, 'table': TABLE, 'table_title': TITLE,
        'source_rows': len(LABELS), 'statistical_columns': len(STATISTICS),
        'complete_grid_positions_checked': len(cells), 'positions_matched_in_three_readers': len(cells),
        'annual_rows_printed_years': [2011, 2025], 'year_label_null_observations': 192,
        'source_table_year_context': 2025, 'source_status_counts': dict(Counter(c['value_status'] for c in cells)),
        'scope': 'Original cell literals, numbering, units and note checked with fixed original SHA and three PDF text readers.',
        'libraries': {lib: version(lib) for lib in ('pdfplumber', 'pypdfium2', 'pypdf')},
        'independent_human_double_collation_completed': False,
    }
    jsonfile(dest / 'verification.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
