#!/usr/bin/env python3
"""Coordinate extraction of the complete reviewed NCL95/2005 core cohort.

Only statistical facts and short necessary table notes are emitted. Source
PDFs, entry HTML, source images and full extracted text remain private. The
native PDF contains numeric text but outlines many Chinese glyphs: all labels
and the two printed 未統計 markers below were transcribed from PDFium images.
No other year's data or geography is substituted. Dependencies: stdlib and
pdfplumber. pypdfium2/Pillow are required only for private image evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / 'raw/ncl-2005'
YEAR, EDITION = 2005, 95
LICENSE_URL = 'https://www.ncl.edu.tw/open-government-declaration'
SOURCE_SYSTEM = 'http://publibstat.lib.nctu.edu.tw/'
FLOW, STOCK, RATIO = 'flow_calendar_year', 'stock_year_end', 'derived_ratio'
NUMBER = re.compile(r'^\d[\d,]*(?:\.\d+)?$')
COUNTIES = ['臺北縣', '宜蘭縣', '桃園縣', '新竹縣', '苗栗縣', '臺中縣',
            '彰化縣', '南投縣', '雲林縣', '嘉義縣', '臺南縣', '高雄縣',
            '屏東縣', '臺東縣', '花蓮縣', '澎湖縣', '基隆市', '新竹市',
            '臺中市', '嘉義市', '臺南市', '金門縣', '連江縣']
NATIONAL = ['國立中央圖書館臺灣分館', '國立臺中圖書館']
NATIONAL_MUNICIPAL = NATIONAL + ['臺北市立圖書館', '高雄市立圖書館',
                               '高雄市政府文化局中正文化中心']
PROSE_REFERENCE_NOTE = ('表1至表4依原章說明為截至94年12月公共館資料；'
                        '國立館與直轄市另列，縣市表列原23個非直轄市縣市；'
                        '不跨改制重編為現行22縣市。')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def stable_write(path, body):
    body = body.encode('utf-8') if isinstance(body, str) else body
    if path.exists() and path.read_bytes() == body:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(body)
    tmp.replace(path)
    return True


def metric(key, label, unit=None, unit_raw=None, temporal=STOCK,
           basis=None, unit_status=None, role=None):
    return dict(key=key, label=label, unit=unit, unit_raw=unit_raw,
                temporal=temporal,
                basis=basis or ('原表欄頭明印單位' if unit_raw else
                                '原表數量文義推定，未另明印單位'),
                unit_status=unit_status or ('printed_unit' if unit_raw else
                                            'contextual_unit_inference' if unit else
                                            'source_unit_unconfirmed_or_not_printed'),
                role=role)


def parse(raw):
    if raw == '未統計':
        return None, 'source_marker'
    if raw == '':
        return None, 'blank_in_source'
    if not NUMBER.fullmatch(raw):
        raise ValueError('Unparsed original cell: ' + repr(raw))
    return str(Decimal(raw.replace(',', ''))), ('reported_decimal' if '.' in raw else 'reported')


class Producer:
    def __init__(self, offline=False, base=BASE):
        import pdfplumber
        self.base = Path(base)
        self.raw = self.base / 'raw/ncl-2005'
        self.rows, self.tables, self.quality = [], [], []
        self.docs, self.pdfs, self.token_audit = {}, {}, []
        # Validate every required source before modifying any output. No partial
        # replacement occurs if a required file is missing/changed.
        for kind in ('public-library', 'statistics'):
            mp = self.raw / f'yearbook-95-{kind}.metadata.json'
            meta = json.loads(mp.read_text())
            path = self.base / meta['source_local_path']
            if not path.exists():
                if offline:
                    raise FileNotFoundError(str(path) + '; prior outputs retained')
                with urlopen(Request(meta['source_download_url'], headers={
                        'User-Agent': 'Taiwan-public-library-statistics/source-linked-research'}), timeout=45) as response:
                    body = response.read()
                if not body.startswith(b'%PDF') or sha(body) != meta['sha256']:
                    raise ValueError('Source version changed: image review required; prior outputs retained')
                stable_write(path, body)
            if sha(path.read_bytes()) != meta['sha256']:
                raise ValueError('Reviewed source SHA mismatch; prior outputs retained: ' + str(path))
            self.docs[kind] = meta
        # Inputs are now validated; open sources for deterministic extraction.
        for kind, meta in self.docs.items():
            self.pdfs[kind] = pdfplumber.open(self.base / meta['source_local_path'])

    def close(self):
        for pdf in self.pdfs.values():
            pdf.close()

    def page(self, kind, pno):
        return self.pdfs[kind].pages[pno - 1].dedupe_chars(tolerance=.2)

    @staticmethod
    def numeric_text(page, bbox):
        x0, top, x1, bottom = bbox
        chars = [c for c in page.chars
                 if x0 <= (c['x0'] + c['x1']) / 2 < x1
                 and top <= (c['top'] + c['bottom']) / 2 < bottom]
        return ''.join(c['text'] for c in sorted(chars, key=lambda c: c['x0'])).strip()

    def emit(self, kind, pno, table, title, row, col, entity, m, raw, bbox,
             *, footnote=None, note='', row_label=None, parent=None,
             role=None, extra=None):
        doc = self.docs[kind]
        value, status = parse(raw)
        county = entity in COUNTIES
        if county:
            ek, context, label_status = 'county', entity, 'printed_source_label_retained'
            scope = 'county_and_township_public_libraries_excluding_separately_listed_national_and_two_municipal_libraries'
        elif entity in NATIONAL:
            ek, context, label_status = 'named_national_public_library', entity, 'printed_source_label_retained'
            scope = 'separately_listed_national_public_library_not_National_Central_Library'
        elif entity in NATIONAL_MUNICIPAL:
            ek, context, label_status = 'named_municipal_public_library', entity, 'printed_source_label_retained'
            scope = 'separate_named_municipal_institution'
        elif entity == '合計':
            ek, context, label_status = 'national_total', '原表23縣市合計', 'printed_source_label_retained'
            scope = 'published_total_of_the_23_original_county_rows_not_all_Taiwan_public_libraries'
        elif table == 107:
            ek, context, label_status = 'library_level_or_ownership_class', entity, 'printed_source_label_retained'
            scope = 'private_ownership_only' if entity == '私立' else 'public_library_group_scope_as_printed_including_private_in_subtotal'
        elif table == 5:
            ek, context, label_status = 'national_total', '全國', 'table_title_scope_not_printed_geography_row'
            scope = 'private_public_library_survey_partial_responses_not_entire_private_library_population'
        else:
            ek, context, label_status = 'national_total', '全國', 'printed_source_label_retained'
            scope = 'public_ownership_only' if entity == '公立公共圖書館' else 'private_ownership_only_partial_responses'
        ownership = ('private' if entity in {'私立', '私立公共圖書館'} else
                     'mixed_public_and_private' if table == 107 and entity == '小計' else
                     'not_stated' if table == 107 and entity == '社教館' else 'public')
        if table == 107 and entity == '小計':
            ek = 'national_total'
        role = role or m.get('role') or ('derived_ratio' if m['temporal'] == RATIO else
                                        'published_total' if entity in {'合計', '小計'} or m['key'] == 'staff_total' else 'reported_component')
        flags = ['published_total_overlaps_components'] if role == 'published_total' else []
        if table in {5, 108}:
            flags.append('response_sample_sizes_differ_by_metric_do_not_treat_as_total_library_count')
        if status == 'source_marker':
            flags.append('source_printed_not_statistically_counted_marker')
            note += '；原刊明印「未統計」，value留空，不改0、不推算。'
        printed = (18 if kind == 'public-library' else 244) + pno
        bbox = [round(v, 3) for v in bbox]
        period_start, period_end = ((f'{YEAR}-01-01', f'{YEAR}-12-31')
                                    if m['temporal'] in {FLOW, 'annual_financial'} else
                                    (None, f'{YEAR}-12-31') if table in {1, 2, 3, 4} and m['temporal'] == STOCK else
                                    (None, None))
        r = dict(
            data_year=YEAR, entity_raw=entity, entity_contextual_name=context, entity_kind=ek,
            entity_label_status=label_status, source_row_label_raw=row_label if row_label is not None else entity,
            source_parent_row_label_raw=parent, ownership_scope=ownership,
            geography_vintage='民國94年原25縣市界線；23個非直轄市縣市列於表3–4，臺北市、高雄市館另列；未跨界線重編',
            national_libraries_scope=scope, metric_id=f'table{table}_{m["key"]}', metric_raw=m['label'],
            value_raw=raw, value=value, value_status=status, unit=m['unit'], unit_raw=m['unit_raw'],
            unit_basis=m['basis'], unit_status=m['unit_status'], temporal_kind=m['temporal'],
            source_id=doc['source_id'], source_url=doc['source_page_url'],
            source_download_url=doc['source_download_url'], source_sha256=doc['sha256'],
            source_local_path=doc['source_local_path'], source_agency='國家圖書館',
            source_retrieved_at=doc['source_retrieved_at'], source_pdf_page=pno,
            source_printed_page=str(printed), source_table=str(table), source_row=row, source_column=col,
            source_locator=f'PDF page {pno}; printed page {printed}; table {table}; data row {row}; column {col}; bbox ' + ','.join(f'{v:.3f}' for v in bbox),
            source_location_kind='table_cell', source_cell_bbox=bbox,
            source_cell_bbox_kind='reviewed_numeric_row_band_and_printed_column_boundaries',
            raw_extracted_line=raw, extraction_status='PDFium_reviewed_headers_labels_footnotes_and_native_coordinate_numeric_cells',
            license_status='not_confirmed', license_url=LICENSE_URL,
            publication_date=doc['publication_date'], publication_date_basis=doc['publication_date_basis'],
            source_edition='95', source_edition_roc=95, source_table_title=title, table_title_raw=title,
            source_title='中華民國九十五年圖書館年鑑／' + ('公共圖書館' if kind == 'public-library' else '圖書館統計'),
            population_scope=scope, period_raw='民國94年', source_data_year_raw='民國94年',
            period_start=period_start, period_end=period_end,
            notes=note.strip('；'), cell_annotation='', snapshot_distribution='not_in_public_bundle',
            aggregation_role=role, institutional_level=entity if table == 107 else None,
            source_column_path=m['label'], source_version_id=doc['source_id'] + ':' + doc['sha256'],
            scope_note=scope,
            time_reference='原表題明印民國94年；表1至4章內明示截至94年12月底；私立填答調查為95年2月，這是調查時間，非私立館stock時點；出版日另列，不互相替代。',
            quality_flags=flags, source_footnotes_raw=footnote,
            source_footnotes_status='relevant_original_table_note' if footnote else 'no_table_specific_note_printed',
            observation_identity_suffix=f'pdf{pno}:row{row}:col{col}',
            interpretation_basis='按原刊標籤、數字、單位、年度與必要註腳保存；原印缺值不補0，數值矛盾不修補。',
            parse_rule='remove_original_thousands_separators_only_preserve_numeric_glyphs_and_exact_source_marker',
            original_fields={'entity': entity, 'source_row_label_raw': row_label if row_label is not None else entity,
                             'parent_row_label_raw': parent, 'metric': m['label'], 'value_raw': raw,
                             'unit_raw': m['unit_raw'], 'table_title': title})
        if extra:
            r.update(extra)
        self.rows.append(r)

    def grid(self, kind, pno, table, title, entities, metrics, boundaries,
             row_centres, *, row_offset=0, footnote=None, note='', markers=None,
             row_labels=None, extra=None):
        page = self.page(kind, pno)
        assert len(boundaries) == len(metrics) + 1
        assert len(entities) == len(row_centres)
        accepted = []
        words = page.extract_words(x_tolerance=1, y_tolerance=2)
        for i, (entity, y) in enumerate(zip(entities, row_centres)):
            for j, m in enumerate(metrics):
                box = (boundaries[j], y - 5.6, boundaries[j + 1], y + 5.6)
                raw = self.numeric_text(page, box)
                matches = [w for w in words if box[0] <= (w['x0'] + w['x1']) / 2 < box[2]
                           and box[1] <= (w['top'] + w['bottom']) / 2 < box[3]]
                position = (i + 1 + row_offset, j + 2)
                if markers and position in markers:
                    if raw or matches:
                        raise ValueError('Source marker box unexpectedly contains native text')
                    raw = markers[position]
                    token_source = 'image_verified_Chinese_outline_marker_missing_from_native_text'
                else:
                    if len(matches) != 1 or matches[0]['text'] != raw:
                        raise ValueError(('Word/char grid roundtrip failed', table, pno, position, raw, matches))
                    token_source = 'native_numeric_word_and_deduplicated_character_roundtrip'
                    accepted.append((matches[0]['x0'], matches[0]['top'], raw))
                self.emit(kind, pno, table, title, *position, entity, m, raw, box,
                          footnote=footnote, note=note,
                          row_label=row_labels[i] if row_labels else None, extra=extra)
                self.token_audit.append(dict(source_id=self.docs[kind]['source_id'], table=table,
                                             pdf_page=pno, row=position[0], column=position[1],
                                             raw=raw, bbox=[round(v, 3) for v in box], method=token_source))
        # Every native number in the full reviewed rectangular row bands must
        # be consumed exactly once; a missing whole metric cannot silently pass.
        all_tokens = [(w['x0'], w['top'], w['text']) for w in words
                      if boundaries[0] <= (w['x0'] + w['x1']) / 2 < boundaries[-1]
                      and any(y - 5.6 <= (w['top'] + w['bottom']) / 2 < y + 5.6 for y in row_centres)
                      and NUMBER.fullmatch(w['text'])]
        if Counter(accepted) != Counter(all_tokens):
            raise ValueError(('Unconsumed/duplicate numeric token in grid', table, pno))

    def table(self, kind, number, title, pages, expected, scope):
        rows = [r for r in self.rows if r['source_id'] == self.docs[kind]['source_id']
                and r['source_table'] == str(number)]
        if len(rows) != expected:
            raise ValueError(('Incomplete table grid', number, len(rows), expected))
        if number in {3, 4} and {r['entity_raw'] for r in rows if r['entity_kind'] == 'county'} != set(COUNTIES):
            raise ValueError('Original 23 county names missing/changed')
        self.tables.append(dict(document_kind=kind, table=number, title=title, pdf_pages=pages,
                                expected_cells=expected, extracted_cells=len(rows), data_years=[2005],
                                scope=scope, numeric_cells=sum(r['value'] is not None for r in rows),
                                status_counts=dict(Counter(r['value_status'] for r in rows))))

    def issue(self, r, flag, **detail):
        if flag not in r['quality_flags']:
            r['quality_flags'].append(flag)
        r['notes'] += '；原印可加總分項與總計不一致，保留全部原值，不以計算值改刊。'
        self.quality.append(dict(source_id=r['source_id'], source_table=r['source_table'],
                                 source_row=r['source_row'], source_column=r['source_column'],
                                 entity_raw=r['entity_raw'], metric_raw=r['metric_raw'], flag=flag,
                                 source_locator=r['source_locator'], **detail))

    def validate(self):
        if len(self.rows) != 494:
            raise ValueError(('Unexpected cohort cell count', len(self.rows)))
        keys = [(r['source_id'], r['source_table'], r['source_pdf_page'], r['source_row'], r['source_column']) for r in self.rows]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate source cell position')
        for r in self.rows:
            if parse(r['value_raw']) != (r['value'], r['value_status']):
                raise ValueError('Numeric normalization is not reproducible')
            if r['value_raw'] == '0' and r['value'] != '0':
                raise ValueError('Printed zero lost')
            if not all(r[k] for k in ('source_url', 'source_download_url', 'source_sha256', 'source_locator', 'source_version_id')):
                raise ValueError('Missing provenance')
        # Additive subtotal tests are source-quality diagnostics, never repairs.
        for mid in sorted({r['metric_id'] for r in self.rows if r['source_table'] == '4'}):
            rr = [r for r in self.rows if r['metric_id'] == mid]
            components = [r for r in rr if r['entity_kind'] == 'county']
            total = next(r for r in rr if r['entity_raw'] == '合計')
            if all(r['value'] is not None for r in components):
                s = sum(Decimal(r['value']) for r in components)
                if s != Decimal(total['value']):
                    self.issue(total, 'source_total_differs_from_component_sum', component_sum=str(s),
                               printed_total=total['value'], difference_printed_minus_components=str(Decimal(total['value']) - s))
        for entity in COUNTIES + ['合計']:
            rr = [r for r in self.rows if r['source_table'] == '4' and r['entity_raw'] == entity]
            total = next(r for r in rr if r['metric_id'] == 'table4_staff_total')
            staff = [r for r in rr if r['metric_id'] in {f'table4_staff_{k}' for k in ('formal', 'temporary', 'contract', 'student', 'volunteer', 'other')}]
            s = sum(Decimal(r['value']) for r in staff)
            if s != Decimal(total['value']):
                self.issue(total, 'source_row_total_differs_from_components', component_sum=str(s), printed_total=total['value'])
        group = [r for r in self.rows if r['source_table'] == '107']
        total = next(r for r in group if r['entity_raw'] == '小計')
        s = sum(Decimal(r['value']) for r in group if r is not total)
        if s != Decimal(total['value']):
            self.issue(total, 'source_total_differs_from_component_sum', component_sum=str(s), printed_total=total['value'])
        # Source versions are intentionally not harmonized. These are direct
        # conflicts between printed public/private tables, not bad extraction.
        for metric_key, description in [('holdings', '私立館館藏總數不同'), ('loans_responding_libraries', '私立借閱冊數填答館數不同')]:
            rs = [r for r in self.rows if r['entity_raw'] == '私立公共圖書館' and
                  r['metric_id'] in {f'table5_{metric_key}', f'table108_{metric_key}'}]
            if len(rs) == 2 and rs[0]['value'] != rs[1]['value']:
                for r in rs:
                    r['quality_flags'].append('source_same_edition_private_public_library_table_disagreement_unresolved')
                    r['notes'] += '；同卷公共館章與統計章' + description + '，原指標名／口徑不必然相同，保留各自版本，不強接或推定哪一個為正確。'
                self.quality.append(dict(flag='source_same_edition_private_public_library_table_disagreement_unresolved',
                                         metric=metric_key, cells=[dict(source_id=r['source_id'], table=r['source_table'],
                                                                       locator=r['source_locator'], raw=r['value_raw']) for r in rs]))

    def write(self):
        self.validate()
        fields = list(dict.fromkeys(k for r in self.rows for k in r))
        buf = io.StringIO(newline='')
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        for r in self.rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v, (dict, list))
                             else '' if v is None else v for k, v in r.items()})
        csvbody = buf.getvalue().encode('utf-8')
        jsonbody = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in self.rows).encode('utf-8')
        # CSV and JSONL must agree before any final write.
        parsed = list(csv.DictReader(io.StringIO(csvbody.decode())))
        for a, b in zip(parsed, self.rows):
            for key in fields:
                expected = (json.dumps(b.get(key), ensure_ascii=False, separators=(',', ':'))
                            if isinstance(b.get(key), (dict, list)) else '' if b.get(key) is None else str(b[key]))
                if a[key] != expected:
                    raise ValueError(('CSV/JSONL content mismatch', key))
        output_paths = [self.base / 'derived/ncl_2005_long.csv', self.base / 'derived/ncl_2005_long.jsonl']
        meta = dict(schema_version='ncl_core_coordinate_cells_v1', data_year=2005,
                    source_edition_roc=95, publication_date='2006-11-01', records=len(self.rows),
                    numeric_cells=sum(r['value'] is not None for r in self.rows),
                    zero_cells=sum(r['value'] is not None and Decimal(r['value']) == 0 for r in self.rows),
                    status_counts=dict(Counter(r['value_status'] for r in self.rows)),
                    documents=self.docs, tables=self.tables, quality_issues=self.quality,
                    intentional_exclusions=[
                        {'document_kind': 'public-library', 'table': '6 (including continued panels)', 'pdf_pages': [14, 15, 16], 'title': '公共圖書館辦理「推廣閱讀活動」及「示範觀摩館」一覽表', 'reason': 'intentional_exclusion: named program-specific library activities and professional observation visits; not whole-year core operating totals. Earlier preliminary construction-table classification was corrected after full original-page review.'},
                        {'document_kind': 'public-library', 'table': '7', 'pdf_pages': [34], 'title': '全國閱讀運動活動內容、場次及參加人數一覽表', 'reason': 'intentional_exclusion: selected reading-campaign activities, including printed periods spanning 94年12月至95年5月; not a complete calendar-2005 public-library operating table.'},
                        {'document_kind': 'statistics', 'figures': '9–24', 'reason': 'intentional_exclusion: original titles cover university, senior-high, junior-high and elementary libraries, not the public-library subgroup.'},
                        {'document_kind': 'statistics', 'figures': '25–28', 'reason': 'intentional_exclusion: interlibrary cooperation and publishing/ISBN/CIP aggregate statistics, not public-library operational subgroup.'},
                        {'reason': 'Other institutions, individuals, awards, named cases, photographs and surrounding signed prose are not emitted. Completeness is limited to the seven inventoried source-table groups.'}],
                    scope_limitations=[
                        '完整性僅及表1–5及表107/108公共館所選子群，非整冊全文或所有館類。',
                        '原23個非直轄市縣市列與兩直轄市、兩國立公共館分表；不重編現行22縣市，不把23縣市合計稱全臺總量。',
                        '私立公共館調查母體121館，實際各欄填答館數不同；填答數不是總館數。',
                        '單位原印人次與括號人有別者保留兩原字，normalized unit未定，不推成去重人數或累計人次。',
                        '未統計與原報0分離；未補值、未由比率反推原量。',
                        '公共館章與統計章私立館館藏／填答館數有原刊差異，未互相覆寫。'],
                    rights=dict(license_status='not_confirmed', license_url=LICENSE_URL,
                                license_evidence='NCL open-government declaration excludes publications and specially authored/commissioned texts. Chapter full-text redistribution is not established; derived statistical facts only.',
                                snapshot_distribution='not_in_public_bundle', private_materials='PDFs, source images, HTML, full extracted text and reviewer private evidence are not public distributions.'),
                    dependencies=['Python3.12 standard library', 'pdfplumber', 'scripts/extract_ncl_2005.py'],
                    numeric_audit=dict(native_numeric_cells=len(self.token_audit) - 2, image_only_marker_cells=2,
                                       native_word_char_roundtrip=True, full_numeric_token_conservation=True,
                                       unique_source_positions=True, csv_jsonl_all_fields_equal=True),
                    outputs=[dict(path=str(p.relative_to(self.base)), sha256=sha(b), bytes=len(b))
                             for p, b in zip(output_paths, (csvbody, jsonbody))])
        meta['known_not_ingested'] = [dict(x, status='known_source_outside_this_annual_core_cohort')
                                      for x in meta['intentional_exclusions']
                                      if x.get('document_kind') == 'public-library']
        stable_write(output_paths[0], csvbody)
        stable_write(output_paths[1], jsonbody)
        stable_write(self.raw / 'extraction-metadata.json', json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
        stable_write(self.raw / 'cell-token-audit.private.json', json.dumps(self.token_audit, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: meta[k] for k in ('data_year', 'records', 'numeric_cells', 'zero_cells', 'status_counts')}, ensure_ascii=False))


def extract(p):
    common = dict(note=PROSE_REFERENCE_NOTE, footnote='資料來源：「公共圖書館統計系統」' + SOURCE_SYSTEM)
    # Original names are read from the PDFium source images, retaining their
    # wrapped parent hierarchy but removing linebreaks only.
    m = [metric('acquisition_spending', '購書經費（元）', '元', '元', 'annual_financial'),
         metric('holdings', '館藏冊數（冊）', '冊', '冊'),
         metric('borrower_visits', '圖書借閱（人次）', '人次', '人次', FLOW),
         metric('loans', '圖書借閱（冊數）', '冊', '冊數', FLOW),
         metric('promotion_events', '推廣服務（場次）', '場次', '場次', FLOW),
         metric('reference_inquiries', '參考諮詢（人次）', '人次', '人次', FLOW)]
    title = '國立暨直轄市立公共圖書館購書經費、館藏與資源使用統計表（民國94年）'
    p.grid('public-library', 1, 1, title, NATIONAL_MUNICIPAL, m,
           [141.84, 199.01, 255.70, 312.39, 369.09, 425.78, 482.48],
           [499.8, 524.5, 541.1, 566.4, 607.8], **common)
    p.table('public-library', 1, title, [1], 30, 'five separate national/municipal institutions × six metrics; no total row')

    staff = [metric('staff_' + k, '人員（人）／' + label, '人', '人') for k, label in
             [('formal', '正式'), ('temporary', '臨時'), ('contract', '約聘僱'),
              ('student', '工讀生'), ('volunteer', '志工'), ('other', '其他')]]
    title = '國立暨直轄市立公共圖書館人員統計表（民國94年）'
    p.grid('public-library', 2, 2, title, NATIONAL_MUNICIPAL, staff,
           [141.28, 198.45, 255.14, 311.84, 368.53, 425.22, 482],
           [149.7, 174.3, 191, 217.3, 257.6], **common)
    p.table('public-library', 2, title, [2], 30, 'five national/municipal institutions × six original staffing categories')

    county = [metric('population', '人口數（人）', '人', '人'),
              metric('holdings', '館藏總數（冊）', '冊', '冊'),
              metric('acquisition_spending', '購書經費（元）', '元', '元', 'annual_financial'),
              metric('holdings_per_capita', '每人擁有館藏冊數（冊）', '冊／人', '冊', RATIO,
                     basis='原欄頭明印每人及冊；normalized unit依每人比率文義表示冊／人。'),
              metric('spending_per_capita', '平均每人購書經費（元）', '元／人', '元', RATIO,
                     basis='原欄頭明印平均每人及元；normalized unit依每人比率文義表示元／人。')]
    title = '臺閩地區各縣市暨鄉鎮市立圖書館館藏資料及購書經費統計表（民國94年）'
    p.grid('public-library', 2, 3, title, COUNTIES[:20], county,
           [102.18, 159.21, 224.91, 291.61, 387.30, 482],
           [354.6 + 16.65 * i for i in range(20)], **common)
    p.grid('public-library', 3, 3, title, COUNTIES[20:], county,
           [102.72, 159.75, 225.44, 292.15, 387.85, 482.48],
           [138.2, 154.9, 171.6], row_offset=20, **common)
    p.table('public-library', 3, title, [2, 3], 115, 'all 23 original nonmunicipal county/city rows × five metrics; continuation included; no printed total')

    use = [metric('borrower_visits', '圖書借閱（人次）', '人次', '人次', FLOW),
           metric('loans', '圖書借閱（冊數）', '冊', '冊數', FLOW),
           metric('visits', '進館人次', '人次', '人次', FLOW),
           metric('promotion_events', '推廣服務（場次）', '場次', '場次', FLOW),
           metric('reference_inquiries', '參考諮詢（人次）', '人次', '人次', FLOW)]
    total = metric('staff_total', '人員（人）／合計', '人', '人', role='published_total')
    title = '臺閩地區各縣市暨鄉鎮市立圖書館人員及服務統計（民國94年）'
    p.grid('public-library', 3, 4, title, COUNTIES + ['合計'], staff + [total] + use,
           [93.73, 116.11, 138.71, 168.02, 196.74, 219.64, 241.85,
            266.26, 307.56, 352.86, 397.16, 438.46, 482.48],
           [265.2 + 16.65 * i for i in range(24)],
           markers={(11, 11): '未統計', (11, 13): '未統計'},
           note=PROSE_REFERENCE_NOTE,
           footnote='資料來源：1. 人員、圖書借閱、推廣服務數據採自「公共圖書館統計系統」' + SOURCE_SYSTEM + '；2. 進館人次及參考諮詢數據為各單位提報。')
    p.table('public-library', 4, title, [3], 288, '23 original county/city rows plus printed total × twelve staffing/service metrics; two printed 未統計 markers retained')

    base = [metric('holdings', '館藏總數（冊）', '冊', '冊'),
            metric('seats', '閱覽席位（席）', '席', '席'),
            metric('borrower_visits', '圖書借閱人次（人）', None, '人', FLOW,
                   basis='原欄名人次但括號人；不擅定去重人數或累計人次，normalized unit留空。',
                   unit_status='source_heading_counting_basis_unresolved'),
            metric('loans', '圖書借閱冊數（冊）', '冊', '冊', FLOW)]
    title = '臺閩地區私立公共圖書館調查統計表（民國94年）'
    private_note = ('資料來源：國家圖書館95年2月問卷調查121所私立公共圖書館。'
                    '說明：本表括弧內數字代表填答館數。')
    p.grid('public-library', 4, 5, title, ['私立公共圖書館'], base,
           [140.97, 226.91, 311.95, 396.99, 482.48], [137.6],
           row_labels=['94'], footnote=private_note,
           note='私立公共館獨立母體；原行名是年度94，私立公共館範圍取自原表題，不是印刷地理列名。',
           extra={'source_original_survey_date_raw': '95年2月', 'source_survey_population_libraries': 121})
    responses = [metric(x['key'] + '_responding_libraries', x['label'],
                        '館', '館', temporal='survey_response_count', role='response_sample_size') for x in base]
    p.grid('public-library', 4, 5, title, ['私立公共圖書館'], responses,
           [140.97, 226.91, 311.95, 396.99, 482.48], [154.3], row_offset=1,
           row_labels=['94'], footnote=private_note,
           note='原同列各指標括號內填答館數，按獨立response_sample_size保存；不是總館數。',
           extra={'source_original_survey_date_raw': '95年2月', 'source_survey_population_libraries': 121,
                  'source_subrow_label_raw': '填答館數',
                  'source_subrow_label_status': 'description_from_printed_footnote_not_a_separate_row_heading',
                  'source_response_notation_kind': 'parenthesized_count_with_館_outlined_glyph'})
    p.table('public-library', 5, title, [4], 8, 'complete private public-library annual row: four metrics plus each metric response-library count')

    title = '臺閩地區各類型圖書館數量統計表（民國94年）／公共圖書館完整子群'
    labels = ['國立', '直轄市立', '縣市立', '鄉（鎮、市、區）立', '社教館', '私立', '小計']
    count = metric('library_count', '圖書館數量', '所', basis='原表題為圖書館數量，未另明印所；依館數文義推定。')
    p.grid('statistics', 4, 107, title, labels, [count], [218, 245],
           [200.7, 216.2, 231.8, 263.0, 278.6, 294.2, 309.8],
           footnote='說明：本統計表除大學圖書館外，其餘各類型圖書館數均包含分館。',
           note='公共圖書館分類組包含國立、直轄市立、縣市立、鄉鎮市區立、社教館及私立；國家圖書館另屬其他列，不混入本組。')
    english = ['National', 'Provincial／Municipal', 'County／City', 'Township／City／District',
               'Social Edu.Institutes', 'Private', 'Sub-total:']
    for r, label_en in zip(p.rows[-7:], english):
        r['source_parent_row_label_raw'] = '公共圖書館'
        r['source_parent_row_label_english_raw'] = 'Public Library'
        r['source_row_label_english_raw'] = label_en
        r['original_fields']['parent_row_label_raw'] = '公共圖書館'
        r['original_fields']['row_label_english_raw'] = label_en
    p.table('statistics', 107, title, [4], 7, 'all six original public-library ownership/level rows and their printed subtotal; includes private and branch libraries')

    title = '臺閩地區各類型圖書館基本資料統計表（民國94年）／公立與私立公共圖書館列'
    # This table says 館藏圖書冊數, not table5's 館藏總數; no claim
    # that these are harmonized totals or that other resource types are included.
    statbase = [metric('holdings', '館藏圖書冊數（冊）', '冊', '冊'),
                metric('seats', '閱覽席位（席）', '席', '席'),
                metric('borrower_visits', '借閱人次（人）', None, '人', FLOW,
                       basis='原欄名人次但括號人；計數口徑未釐清，不推定去重人數或累計人次。',
                       unit_status='source_heading_counting_basis_unresolved'),
                metric('loans', '借閱冊數（冊）', '冊', '冊', FLOW)]
    fn = ('資料來源：公立公共圖書館—「公共圖書館統計系統」' + SOURCE_SYSTEM + '；'
          '私立公共圖書館、專門圖書館—國家圖書館提供。'
          '說明：填答館數不含分館，分館的統計資料併入總館統計。')
    for row_index, entity, y in [(2, '公立公共圖書館', 207.2), (3, '私立公共圖書館', 240.5)]:
        p.grid('statistics', 5, 108, title, [entity], statbase,
               [142.34, 227.37, 312.40, 397.43, 482.48], [y],
               row_offset=(row_index - 1) * 2, footnote=fn,
               note='原印公共館類型行名保留；全國是推定範圍context。填答館數另列，分館併總館統計，不是圖書館總數。',
               extra={'source_original_table_row': row_index, 'source_subrow_label_raw': '資料數量'})
        resp = [metric(x['key'] + '_responding_libraries', x['label'],
                       '館', '館', temporal='survey_response_count',
                       basis='左上原欄頭明列數量（館）／填答館數；各值以括號表示填答館數。',
                       role='response_sample_size') for x in statbase]
        p.grid('statistics', 5, 108, title, [entity], resp,
               [142.34, 227.37, 312.40, 397.43, 482.48], [y + 16.65],
               row_offset=(row_index - 1) * 2 + 1, footnote=fn,
               note='同一館類列括號內各指標填答館數，獨立response_sample_size，未當作總館數。',
               extra={'source_original_table_row': row_index, 'source_subrow_label_raw': '填答館數',
                      'source_subrow_label_status': 'printed_diagonal_header_for_parenthetical_response_count',
                      'source_response_notation_kind': 'parenthesized_response_count'})
    p.table('statistics', 108, title, [5], 16, 'complete public/private public-library rows: four operational quantities plus four response-library counts per row')
    for r in p.rows:
        if r['source_table'] in {'1', '2'}:
            r['institutional_level'] = '國立' if r['entity_raw'] in NATIONAL else '直轄市立'
            r['source_row_hierarchy_raw'] = [r['institutional_level']] + (['高雄市'] if r['entity_raw'].startswith('高雄') else []) + [r['entity_raw']]
        if r['source_table'] in {'5', '108'}:
            r['source_row_indexing'] = 'quantity_and_parenthetical_response_lines_numbered_separately; physical_original_table_row_stored_separately'
            r['source_original_table_row'] = r.get('source_original_table_row', 1)
            response = r['aggregation_role'] == 'response_sample_size'
            r['source_subrow_sequence'] = 2 if response else 1
            if response:
                r['source_parenthetical_raw'] = '（' + r['value_raw'] + ('館）' if r['source_table'] == '5' else '）')
                r['original_fields']['parenthetical_response_raw'] = r['source_parenthetical_raw']
        if r['metric_id'] in {'table1_holdings', 'table3_holdings', 'table3_holdings_per_capita'}:
            r['unit'] = None
            r['unit_status'] = 'source_heading_body_counting_unit_conflict_unresolved'
            r['unit_basis'] = '原欄頭明印冊；同章PDF4／印22館藏說明以冊（件、種）及圖書、期刊、非書等混合資料計量。未證可統一為純冊數；normalized unit留空，原欄頭不改。'
            r['quality_flags'].append('source_heading_body_counting_unit_conflict_unresolved')
            r['notes'] += '；原館藏欄頭冊與同章冊（件、種）混合計量敘述未統一，不當作純圖書冊數；每人館藏比率不另反算。'
            r['source_unit_context_locator'] = 'public-library PDF page4; printed page22; section二 圖書資料收藏數量'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Require reviewed private source PDFs; never replace prior outputs on missing/changed input')
    args = parser.parse_args()
    producer = Producer(offline=args.offline)
    try:
        extract(producer)
        producer.write()
    finally:
        producer.close()


if __name__ == '__main__':
    main()
