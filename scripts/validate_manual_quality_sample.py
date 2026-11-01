#!/usr/bin/env python3
"""Verify transport, deterministic selection and blank reference status, not accuracy."""
import argparse, collections, csv, json, sys
from pathlib import Path
from pypdf import PdfReader
import prepare_manual_quality_sample as m

def main():
    p = argparse.ArgumentParser(); p.add_argument('--private', type=Path, required=True)
    p.add_argument('--public', type=Path, required=True); p.add_argument('--package', type=Path, required=True)
    a = p.parse_args(); sys.path.insert(0, str(a.public/'scripts')); import record_io
    rows = list(record_io.rows(a.private)); public = list(record_io.rows(a.public))
    sources = {r['source_sha256']: (a.private/r['source_snapshot_path']).resolve() for r in rows}
    reader = a.package/'reader'; freeze = json.loads((a.package/'freeze.json').read_text())
    manifest = json.loads((reader/'sample-manifest.json').read_text()); index = json.loads((reader/'source-index.json').read_text())
    assert [(r['stratum'],r['observation_id']) for r in manifest] == m.select(public)[1]
    assert m.file_sha(reader/'sample-manifest.json') == freeze['reader_manifest_sha256']
    assert m.file_sha(a.package/'evaluator_DO_NOT_GIVE_TO_READER/database-comparator.json') == freeze['comparator_sha256']
    assert not any(set(r) & set(m.ANSWER_FIELDS) for r in manifest)
    assert len(manifest) == len({r['sample_id'] for r in manifest}) == 120
    actual = collections.Counter(r['stratum'] for r in manifest)
    assert actual == {s:n for s,(_,n) in m.SIZES.items()}
    with (reader/'independent-readings.csv').open(encoding='utf-8-sig',newline='') as f: readings=list(csv.DictReader(f))
    assert [r['sample_id'] for r in readings] == [r['sample_id'] for r in manifest]
    assert all(v == '' for r in readings for k,v in r.items() if k != 'sample_id')
    assert freeze['human_readings_completed'] == 0 and freeze['accuracy_estimate'] is None
    docs={}; copied_pages=0
    for s in index:
        original=sources[s['source_sha256']]; attachment=reader/s['attachment']
        assert m.file_sha(original)==s['source_sha256']
        assert m.file_sha(attachment)==s['attachment_sha256']
        if s['original_pdf_pages_in_attachment_order']:
            src=PdfReader(original); dst=PdfReader(attachment); docs[s['attachment']]=dst
            pages=s['original_pdf_pages_in_attachment_order']; assert len(pages)==len(dst.pages)
            for i,n in enumerate(pages):
                assert m.sha(src.pages[n-1].get_contents().get_data())==m.sha(dst.pages[i].get_contents().get_data())
                copied_pages+=1
        else: assert attachment.read_bytes()==original.read_bytes()
    text_checks=[]
    for b in manifest:
        assert (reader/b['attachment']).is_file()
        if b['stratum']=='B_text_pdf':
            text=docs[b['attachment']].pages[b['attachment_page']-1].extract_text() or ''
            text_checks.append({'sample_id':b['sample_id'],'characters':len(text),'text_layer_present':bool(text.strip())})
    result={'passed':True,'fixed_seed_sample_reproduced':True,'sample_n':len(manifest),'strata':dict(actual),
            'original_source_versions_rehashed':len(index),'copied_pdf_content_streams_matched':copied_pages,
            'B_sample_pages_with_text_layer':sum(x['text_layer_present'] for x in text_checks),
            'database_answers_absent_from_reader_manifest':True,'all_human_fields_blank':True,
            'human_readings_completed':0,'accuracy_estimate':None,
            'limits':['字元層存在不等於文字解碼或讀格正確；B5pc-H等字碼的工具警告不影響原PDF頁保留。',
                      'PDF欄頭與註腳可能超出選頁，核讀者須按URL回原件全文；不確定不可猜。',
                      '這些是原件身分、傳輸與隔離檢查，未完成人工核讀或雙校。']}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
