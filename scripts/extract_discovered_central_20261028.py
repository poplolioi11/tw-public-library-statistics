#!/usr/bin/env python3
"""Reproduce four reviewed documents: full NTPC/Tainan tables, DGBAS4-22, MOE社3.

Only statistical cells, necessary original labels and provenance are exported.
No network requests, imputation, cross-source aggregation or original PDF export.
"""
import argparse, collections, decimal, hashlib, json, re, tempfile
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]


def stable(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def parse(raw):
    s = re.sub(r'[\s,]', '', raw)
    if not s:
        return None, 'source_blank'
    if s in ('-', '--', '…', '...'):
        return None, 'source_marker'
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', s):
        raise ValueError('Unreviewed numerical token: ' + repr(raw))
    return format(decimal.Decimal(s), 'f'), 'reported'


def base(document, table, row, column, label, metric, raw, value, status,
         year, unit, temporal, entity, entity_kind, page=None, printed=None):
    sid = document['candidate_id']
    identity = f'{sid}/{table}/{page}/{row}/{column}'
    return {
        'cell_id': 'cell-' + hashlib.sha256(identity.encode()).hexdigest()[:24],
        'source_document_id': sid, 'source_url': document['official_url'] + ('#page=' + str(page) if page else ''),
        'source_sha256': document['source_sha256'], 'source_version_id': document['source_version_id'],
        'source_retrieved_at': document['retrieved_at'], 'source_pdf_page': page,
        'source_printed_page': printed, 'source_table': table, 'source_table_title': table,
        'source_row': str(row), 'source_column': str(column),
        'source_locator': f'PDF page {page}; printed page {printed}; table {table}; row {row} ({label}); column {column} ({metric})',
        'row_label_raw': label, 'column_label_raw': metric, 'entity_raw': entity,
        'entity_kind': entity_kind, 'data_year': year, 'period_raw': label,
        'period_status': 'explicit_original_year' if year is not None else 'original_row_year_not_explicit',
        'metric_id': 'field_' + hashlib.sha256(metric.encode()).hexdigest()[:14], 'metric_raw': metric,
        'value_raw': raw, 'value': value, 'value_status': status, 'unit': unit,
        'unit_raw': unit, 'unit_status': 'printed_heading' if unit else 'source_unit_unconfirmed',
        'temporal_kind': temporal, 'population_scope': document['scope'],
        'national_libraries_scope': 'not_independently_certified',
        'geography_vintage': '原刊地名與當年分類；未自行轉換界線',
        'aggregation_role': 'source_measure', 'source_notes': list(document['cautions']),
        'quality_flags': [], 'independent_check': {},
    }


def probes(root, source_root, documents):
    from probe_library_source_tables import extract
    with tempfile.TemporaryDirectory(prefix='library-pinned-probes-') as tmp:
        result = extract(Path(tmp), source_root)
    rows = []
    for original in result['records']:
        sid = original['source_id']; doc = documents[sid]; loc = original['source_locator']
        metric = loc['column_label_raw']; year = original['data_year']; table = loc['table']
        ratio = '%' == original['unit'] or '每人' in metric or '變動率' in metric
        ranking = '排名' in metric
        temporal = 'source_ratio_period' if ratio else 'source_ranking' if ranking else 'annual_source_reference'
        if sid.startswith('ntpc'):
            temporal = 'stock_year_end' if metric == '藏書冊數' else 'annual_source_reference'
            entity_kind = 'county_official_table' if year is not None else 'municipal_district_in_source_table'
        else:
            entity_kind = 'national_total' if original['geography_raw'] == '全國' else 'regional_subtotal' if original['geography_raw'] == '六都地區' else 'county_official_table'
        row = base(doc, table, loc['row_ordinal'], loc['column_ordinal'], original['source_row_label_raw'], metric,
                   original['raw_value_pdfminer'], original['value'],
                   'source_marker' if original['value'] is None else 'reported', year, original['unit'], temporal,
                   original['geography_raw'], entity_kind, loc['pdf_page'], loc['printed_page'])
        row['source_table_title'] = '新北市立圖書館借閱概況' if sid.startswith('ntpc') else '104年全國圖書館概況' if table == '1' else '臺南市歷年圖書館概況'
        row['population_scope'] = '原刊新北市立圖書館系統；年度與行政區另列，辦證計數及館藏範圍須依原表註記，不與其他母體拼接。' if sid.startswith('ntpc') else '原刊公共圖書館統計；全國、六都小計、縣市及臺南歷年分列；分館是否納入館數未另確認，不與其他來源館數拼接。'
        row['period_status'] = original['period_status']
        row['source_table_year_context'] = original['source_table_year_context']
        row['source_cell_bbox'] = loc['bbox_pdfplumber']
        row['source_locator'] += '; bbox ' + ','.join(format(x, '.4f') for x in loc['bbox_pdfplumber'])
        row['unit_status'] = original['unit_status']
        row['independent_check'] = {'method': 'pdfplumber_vs_PDFium_pinned_complete_table', 'matched': True,
                                    'pdfminer_raw': original['raw_value_pdfminer'], 'pdfium_raw': original['raw_value_pdfium']}
        if original['period_status'] == 'multi_year_change_not_single_year':
            row['temporal_kind'] = 'multi_year_change_ratio' if ratio else 'multi_year_absolute_change'
            row['aggregation_role'] = 'multi_year_change_not_annual_stock_or_flow'
            row['quality_flags'].append('multi_year_change_not_single_year')
        elif ranking:
            row['aggregation_role'] = 'published_rank_not_business_quantity'
        elif row['entity_kind'] in ('national_total', 'regional_subtotal'):
            row['aggregation_role'] = 'published_total' if row['entity_kind'] == 'national_total' else 'published_subtotal'
        if sid.startswith('ntpc') and metric == '藏書冊數':
            row['collection_segment'] = 'excludes_nonbook_2006_2009' if year is not None and year < 2010 else 'includes_books_electronic_nonbook_since2010' if year is not None else 'district_period_unresolved'
        rows.append(row)
    return rows


def dgbas(source_root, documents):
    doc = documents['dgbas-yearbook-113']; path = source_root/'dgbas-yearbook-113.pdf'
    metrics = [('總館', '所'), ('分館', '所'), ('區館', '所'), ('圖書', '千冊'), ('期刊', '種'), ('電子資源', '種'), ('全年圖書資訊借閱人次', '千人次'), ('全年圖書資訊借閱冊數', '千冊')]
    entities = ['國家圖書館', '公立公共圖書館', '新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市', '宜蘭縣', '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義縣', '屏東縣', '臺東縣', '花蓮縣', '澎湖縣', '基隆市', '新竹市', '嘉義市', '金門縣', '連江縣']
    bounds = [154, 191, 242, 284, 336, 383, 438, 495, 548]
    rows = []
    with pdfplumber.open(path) as pdf, pdfium.PdfDocument(path) as independent:
        page = pdf.pages[119]; words = page.extract_words(x_tolerance=1, y_tolerance=1)
        labels = [w for w in words if w['x1'] < 150 and 135 < w['top'] < 700 and (re.fullmatch(r'\d+年', w['text']) or w['text'] in entities)]
        labels.sort(key=lambda w: w['top'])
        assert len(labels) == 39, [x['text'] for x in labels]
        assert [x['text'] for x in labels[15:]] == entities
        tp = independent[119].get_textpage()
        for ri, label in enumerate(labels, 1):
            annual = re.fullmatch(r'(\d+)年', label['text']); year = int(annual.group(1))+1911 if annual else None
            geo = '全國' if annual else label['text']; kind = 'national_total' if annual else 'public_library_institution' if label['text'] == '國家圖書館' else 'national_public_library_subtotal' if label['text'] == '公立公共圖書館' else 'county_official_table'
            for ci, (metric, unit) in enumerate(metrics, 1):
                cell = [w for w in words if abs(w['top']-label['top']) < 1 and bounds[ci-1] <= w['x0'] and w['x1'] <= bounds[ci]]
                assert cell, (ri, ci)
                raw = ' '.join(w['text'] for w in sorted(cell, key=lambda w: w['x0']))
                value, status = parse(raw)
                box = [min(w['x0'] for w in cell), min(w['top'] for w in cell), max(w['x1'] for w in cell), max(w['bottom'] for w in cell)]
                other = tp.get_text_bounded(left=box[0]-.3, bottom=page.height-box[3]-.3, right=box[2]+.3, top=page.height-box[1]+.3).strip()
                assert parse(other) == (value, status), (raw, other)
                row = base(doc, '4-22', ri, ci, label['text'], metric, raw, value, status, year, unit,
                           'flow_calendar_year' if ci >= 7 else 'stock_year_end', geo, kind, 120, '105')
                row['source_table_title'] = '公立公共圖書館概況'
                row['source_table_year_context'] = 2024
                row['population_scope'] = '年度全國總列含國家圖書館及公立公共圖書館；機關別國家圖書館、公立公共館小計及縣市另列，不整表相加。'
                row['national_libraries_scope'] = 'annual_total_includes_NCL_public_subtotal_includes_NLPI_NTL_per_source_note'
                row['aggregation_role'] = 'published_total' if annual else 'published_subtotal' if kind == 'national_public_library_subtotal' else 'source_component'
                row['source_cell_bbox'] = box
                row['source_locator'] += '; bbox ' + ','.join(format(x, '.4f') for x in box)
                row['independent_check'] = {'method': 'pdfplumber_vs_PDFium_positioned_cell', 'matched': True, 'pdfminer_raw': raw, 'pdfium_raw': other}
                if not annual:
                    row['period_status'] = 'institution_rows_after_last_annual_row_year_not_repeated'
                    row['source_notes'].append('機關別列位於113年年度列後，保留2024表脈絡；未把未逐列印出的年份當成明列資料年。')
                rows.append(row)
        tp.close()
    assert len(rows) == 312
    return rows


def moe(source_root, documents):
    # xlrd is an acquisition/reproduction dependency, not needed to read exports.
    import xlrd
    doc = documents['moe-16years-T403']; book = xlrd.open_workbook(source_root/'moe-16years-T403.xls'); sheet = book.sheet_by_name('社3')
    assert sheet.nrows == 22 and sheet.ncols == 4
    assert [int(sheet.cell_value(i, 0)) for i in range(4, 20)] == list(range(83, 99))
    assert '含國家圖書館' in sheet.cell_value(20, 0)
    rows = []
    for i in range(4, 20):
        roc = int(sheet.cell_value(i, 0)); year = roc + 1911
        for ci, (metric, unit) in enumerate([('圖書館數', '所'), ('藏書冊數', '千冊'), ('圖書借閱人數', '千人次')], 1):
            cell = sheet.cell(i, ci); assert cell.ctype == xlrd.XL_CELL_NUMBER
            raw = format(decimal.Decimal(str(cell.value)), 'f'); value = format(decimal.Decimal(raw).normalize(), 'f')
            row = base(doc, '社3', i+1, ci+1, str(roc), metric, raw, value, 'reported', year, unit,
                       'annual_source_reference' if ci == 3 else 'year_end_reference', '全國', 'national_total')
            row['source_table_title'] = '（三）公立公共圖書館數及圖書借閱人數'
            row['source_locator'] = f'XLS worksheet 社3; cell {chr(65+ci)}{i+1}; heading row4; notes rows21–22'
            row['unit_raw'] = str(sheet.cell_value(3, ci))
            row['population_scope'] = '本表資料含國家圖書館（原表註1）。'
            row['national_libraries_scope'] = 'includes_National_Central_Library_per_original_note'
            row['source_notes'] += [str(sheet.cell_value(20, 0)), str(sheet.cell_value(21, 0)), '與既有全國表年份重疊，保留不同出版來源，不作新增業務量相加。']
            row['aggregation_role'] = 'published_total'
            row['source_stored_value_raw'] = repr(cell.value)
            row['source_display_status'] = 'BIFF_numeric_cell_format_not_rendered'
            row['independent_check'] = {'method': 'xlrd_BIFF_numeric_cell_and_explicit_sheet_header_year_note_check', 'matched': True, 'second_independent_spreadsheet_engine': False}
            rows.append(row)
    assert len(rows) == 48
    return rows


def extract(root, source_root):
    documents = {x['candidate_id']: x for x in json.loads((root/'raw/discovered-20261028/documents.json').read_text())['documents']}
    selected = ['ntpc-cultural-2015', 'tainan-bulletin-10505', 'dgbas-yearbook-113', 'moe-16years-T403']
    for sid in selected:
        path = source_root/(sid+('.xls' if sid == 'moe-16years-T403' else '.pdf'))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == documents[sid]['source_sha256'], sid
    rows = probes(root, source_root, documents) + dgbas(source_root, documents) + moe(source_root, documents)
    assert len({r['cell_id'] for r in rows}) == len(rows) == 756
    root.joinpath('derived/discovered_central_20261028_cells.jsonl').write_text(''.join(stable(r)+'\n' for r in rows))
    meta = {'schema_version': '1.0.0', 'full_selected_tables': True, 'source_cells': len(rows),
            'source_counts': dict(collections.Counter(r['source_document_id'] for r in rows)),
            'null_cells': sum(r['value'] is None for r in rows), 'unresolved_year_cells': sum(r['data_year'] is None for r in rows),
            'no_imputation': True, 'no_cross_source_aggregation': True, 'no_full_originals_distributed': True,
            'tables': [{'document': 'ntpc-cultural-2015', 'table': '6-2', 'source_cells': 156}, {'document': 'tainan-bulletin-10505', 'table': '1+2', 'source_cells': 240}, {'document': 'dgbas-yearbook-113', 'table': '4-22', 'source_cells': 312}, {'document': 'moe-16years-T403', 'table': '社3', 'source_cells': 48}]}
    root.joinpath('derived/discovered_central_20261028_metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n')
    return meta


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', type=Path, default=ROOT); p.add_argument('--source-root', type=Path)
    a = p.parse_args(); root = a.root.resolve(); print(json.dumps(extract(root, a.source_root.resolve() if a.source_root else root/'raw/discovered-20261028'), ensure_ascii=False))
