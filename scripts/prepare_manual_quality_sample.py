#!/usr/bin/env python3
"""Prepare a version-pinned private source-reading audit; never creates human truth.

Selection reads IDs and source-format fields only. Database values are written
exclusively to a separate evaluator directory, never the reader packet.
"""
import argparse, collections, csv, hashlib, io, json, platform, random, subprocess
from pathlib import Path
from pypdf import PdfReader, PdfWriter

COMMIT = '4c4e656d94598627c364a49beb967ec437dff037'
LOGICAL_SHA = '12d1f08b656bca6d01ca611aa045917289d0c534f1776141a7b486f5ed329322'
SCAN_SHA = '6b58c1f4432c77bb0fcbea94c2dc0373f1d5f163e080a203b01d74e29b9b0ff4'
SEED = 20261030
SIZES = {'A_scan91': (369, 60), 'B_text_pdf': (39342, 40), 'C_structured': (18534, 20)}
LOCATOR_FIELDS = ('source_url', 'source_page_url', 'source_sha256', 'source_locator',
                  'source_pdf_page', 'source_printed_page', 'source_table',
                  'source_row', 'source_column', 'source_field')
READ_FIELDS = ('reader_id', 'read_at', 'access_status', 'literal_reading', 'cell_kind',
               'unit_as_printed', 'unit_interpretation', 'period_as_printed',
               'period_interpretation', 'geography_as_printed', 'population_as_printed',
               'context_locator', 'uncertainty', 'notes')
ANSWER_FIELDS = ('value', 'raw_value', 'value_status', 'unit', 'unit_raw', 'unit_status',
                 'data_year', 'period_start', 'period_end', 'temporal_kind',
                 'period_basis', 'population_scope', 'geography', 'definition_status')

def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()
def encoded(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def dump(p, obj): p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def csv_write(p, fields, rows):
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
def classify(r):
    if r.get('component_source_id') == 'ncl-ed91-public-libraries':
        assert r['source_sha256'] == SCAN_SHA and r.get('source_pdf_page')
        return 'A_scan91'
    return 'B_text_pdf' if r.get('source_pdf_page') is not None else 'C_structured'

def select(rows):
    frames = {s: [] for s in SIZES}
    for r in rows: frames[classify(r)].append(r['observation_id'])
    result = []
    for s, (N, n) in SIZES.items():
        frame = sorted(frames[s]); assert len(frame) == N and len(set(frame)) == N
        # Independent deterministic streams; algorithm/version are pinned in manifest.
        rng = random.Random(f'{SEED}/{s}')
        selected = sorted(rng.sample(frame, n))
        result.extend((s, oid) for oid in selected)
    return frames, result

def main():
    p = argparse.ArgumentParser(); p.add_argument('--private', type=Path, required=True)
    p.add_argument('--public', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); import sys
    sys.path.insert(0, str(a.public / 'scripts')); import record_io
    git_before = subprocess.check_output(['git', 'status', '--porcelain'], cwd=a.public, text=True)
    assert not git_before, 'Public checkout must remain clean'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.public, text=True).strip() == COMMIT
    assert record_io.logical_sha(a.public) == LOGICAL_SHA
    public = list(record_io.rows(a.public)); private = list(record_io.rows(a.private))
    assert len(public) == len(private) == 58245
    by_id = {r['observation_id']: r for r in public}; originals = {r['observation_id']: r for r in private}
    assert len(by_id) == len(originals) == 58245
    for oid, r in by_id.items():
        for k in ANSWER_FIELDS + LOCATOR_FIELDS: assert r.get(k) == originals[oid].get(k), (oid, k)
    frames, sample = select(public); assert sample == select(list(reversed(public)))[1]
    assert len(sample) == len({oid for _, oid in sample}) == 120
    out = a.output; out.mkdir(parents=True, exist_ok=False)
    reader = out / 'reader'; reader.mkdir(); (reader / 'sources').mkdir()
    evaluator = out / 'evaluator_DO_NOT_GIVE_TO_READER'; evaluator.mkdir()
    dump(evaluator / 'sampling-frame.json', {s: sorted(ids) for s, ids in frames.items()})
    blind = []; key = []; source_log = []; attached = {}
    for i, (s, oid) in enumerate(sample, 1):
        r, original = by_id[oid], originals[oid]; sid = f'Q{i:03d}'
        b = {'sample_id': sid, 'stratum': s, 'observation_id': oid}
        b.update({k: r.get(k) for k in LOCATOR_FIELDS})
        path = (a.private / original['source_snapshot_path']).resolve(); h = r['source_sha256']
        if h not in attached:
            assert path.is_file() and file_sha(path) == h, f'Original source changed: {oid}'
            attached[h] = {'path': path, 'rows': []}
        attached[h]['rows'].append(b)
        key.append({'sample_id': sid, 'observation_id': oid, 'canonical_row_sha256': sha(encoded(r)),
                    'database_comparator_NOT_HUMAN_TRUTH': {k: r.get(k) for k in ANSWER_FIELDS}})
        blind.append(b)
    for h, item in attached.items():
        path, items = item['path'], item['rows']
        if path.suffix.lower() == '.pdf':
            doc = PdfReader(path); pages = set()
            for b in items:
                n = int(b['source_pdf_page']); assert 1 <= n <= len(doc.pages)
                # Adjacent context is a convenience, not a claim of a complete table.
                pages.update(range(max(1, n - 1), min(len(doc.pages), n + 1) + 1))
            pages = sorted(pages); writer = PdfWriter()
            for n in pages: writer.add_page(doc.pages[n - 1])
            rel = f'sources/{h[:20]}-source-pages.pdf'
            with (reader / rel).open('wb') as f: writer.write(f)
            for b in items:
                b.update(attachment=rel, attachment_page=pages.index(int(b['source_pdf_page'])) + 1,
                         attachment_status='original_pdf_pages_derivative_not_database_render')
            kind = '原件選頁；頁面順序映射另存，非完整原檔，SHA另算'
        else:
            rel = f'sources/{h[:20]}{path.suffix.lower()}'
            (reader / rel).write_bytes(path.read_bytes())
            for b in items: b.update(attachment=rel, attachment_page=None, attachment_status='original_bytes_verified')
            pages = None; kind = '完整原始結構檔，可能含其他官方欄位；私人核讀用途，非公開附件'
        source_log.append({'source_sha256': h, 'attachment': rel, 'attachment_sha256': file_sha(reader / rel),
                           'attachment_bytes': (reader / rel).stat().st_size,
                           'original_pdf_pages_in_attachment_order': pages, 'kind': kind})
    dump(reader / 'source-index.json', source_log)
    dump(reader / 'sample-manifest.json', blind)
    csv_write(reader / 'sample-manifest.csv', list(blind[0]), blind)
    readings = [{'sample_id': b['sample_id'], **{k: '' for k in READ_FIELDS}} for b in blind]
    csv_write(reader / 'independent-readings.csv', ['sample_id', *READ_FIELDS], readings)
    dump(evaluator / 'database-comparator.json', key)
    dump(evaluator / 'selected-database-rows.json', [by_id[oid] for _, oid in sample])
    frame_digest = sha(encoded({s: sorted(ids) for s, ids in frames.items()}))
    manifest = {'schema_version': '1.0.0', 'created_date_taipei': '2026-10-30', 'dataset_version': '0.9.1',
                'public_commit': COMMIT, 'canonical_logical_sha256': LOGICAL_SHA, 'seed': SEED,
                'algorithm': 'CPython random.Random(str(seed)+"/"+stratum).sample(sorted(observation_ids), n); selected IDs sorted',
                'python': platform.python_version(), 'frame_sha256': frame_digest,
                'sampling_unit': 'fixed-version observation record, not document or unique physical cell',
                'strata': {s: {'population_N': N, 'sample_n': n} for s, (N,n) in SIZES.items()},
                'sample_n': len(sample), 'source_versions_in_sample': len(attached),
                'reader_manifest_sha256': file_sha(reader / 'sample-manifest.json'),
                'comparator_sha256': file_sha(evaluator / 'database-comparator.json'),
                'human_reader_assigned': False, 'human_readings_completed': 0,
                'human_double_collation_completed': False, 'accuracy_estimate': None,
                'replacement_policy': 'never replace inaccessible, ambiguous, blank, marker or zero cells',
                'new_source_methods_benchmark_included': False,
                'fresh_official_url_availability_tested': False,
                'original_hash_identity_is_not_cell_accuracy': True}
    dump(out / 'freeze.json', manifest)
    instructions = '''# v0.9.1 既有資料品質抽樣：盲讀包

這是固定版本資料庫的品質抽查，不是新來源方法比較，也不是人工雙校完成證明。
讀者尚未指定，目前人工讀值 0 筆。請先保留這份凍結清單，再開始核讀。

1. 用 sample-manifest.csv 找 sample_id、官方原件 URL、原件 SHA、頁表列欄與附件。
2. PDF 附件是原件選頁，attachment_page 是附件頁碼；source_pdf_page 是完整原檔頁碼。必要時回官方全文查續頁、欄頭、註腳與母體，沒有證據填「未知」。選頁不是完整原檔；original SHA 與附件 SHA 分開記在 source-index.json。
3. 結構檔是核過原件 SHA 的官方原始版本，不是從資料庫重繪的答案。按 source_locator 找原欄位；URL 有時為 POST 服務入口，僅點網址可能不能重現舊回應，請使用凍結原件與 SHA。
4. 只填 independent-readings.csv。literal_reading 保留實際看到的字串；空白請填 cell_kind=blank，符號 marker，數字 numeric，模糊 unreadable，無法取得 retrieval_failed。access_status 記 readable / unreadable / retrieval_failed。0、空白、符號不同，不推算或補零。
5. 單位、期間、母體與地理用原文記錄；明示無法確定時填 unknown，不用資料庫口徑替原表解答。context_locator 寫支持判讀的欄頭／頁碼／註腳。
6. 不查看 evaluator_DO_NOT_GIVE_TO_READER 中的資料庫比對鍵，不向 AI 索取標準答案。自己或其他讀者若已看過資料庫的同格答案，在 notes 記錄可能的揭盲。
7. 不可換掉困難樣本。不能判讀也要保留同一 sample_id。完成讀值後另存新檔，不覆寫本包的空白範本或凍結清單。

單人與資料庫不一致僅是「不一致」，需要原件裁決才能稱資料庫錯誤。作者抽樣核對不等於獨立人工雙校。原先的 OCR/AI 判讀不能變成人類參考答案。

三層分別是 369 抽60、39,342 抽40、18,534 抽20。不要把120筆直接合併算全庫錯誤率。不能判讀的比例另報，不能算成正確，也不能悄悄縮小完整樣本。未全部核完時不給整層母體推論。

這份包僅供私人核讀，包含官方原件；不能直接拿去公開發布。未改授權，也未新增 DOI、寄信或投稿。
'''
    (reader / '先讀這份.md').write_text(instructions, encoding='utf-8')
    assert all(not v for row in readings for k,v in row.items() if k != 'sample_id')
    assert not (set(blind[0]) & set(ANSWER_FIELDS)), 'Blind manifest contains database answers'
    assert not list(reader.rglob('*comparator*'))
    assert all((reader / b['attachment']).is_file() for b in blind)
    assert git_before == subprocess.check_output(['git','status','--porcelain'], cwd=a.public, text=True)
    checks = {'passed': True, 'exhaustive_disjoint_frame': True, 'row_order_invariant_selection': True,
              'sample_counts_correct': True, 'unique_sample_ids': True, 'originals_sha_verified': len(attached),
              'reader_has_no_database_answer_fields': True, 'all_human_fields_blank': True,
              'all_120_have_source_attachment': True, 'public_checkout_unchanged': True,
              'human_validation_not_performed': True}
    dump(out / 'machine-checks.json', checks)
    print(json.dumps({'freeze': manifest, 'checks': checks},ensure_ascii=False))

if __name__ == '__main__': main()
