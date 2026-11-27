#!/usr/bin/env python3
"""Register complete reviewed 114/early-yearbook extracts from pinned originals."""
import argparse
import csv
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
from pathlib import Path

import record_io
from build_nov2026_sources import COLUMNS, load_records, source_cards, write_json

ROOT = Path(__file__).resolve().parents[1]
BATCHES = {
    'dgbas_yearbook_114': {
        'document': 'dgbas-yearbook-114', 'file': 'raw/dgbas-yearbook-114/ch4.pdf',
        'extractor': 'extract_dgbas114_table422.py', 'output_flag': '--output-dir',
        'retrieved_at': '2026-11-27T17:03:47.945547+00:00',
        'method': 'Pinned PDF page 29. Exact whole-grid agreement of pdfplumber, PDFium and pypdf.',
    },
    'ncl_early_1985': {
        'document': 'ncl-ed2-public-libraries-1985', 'file': 'raw/ncl-early-1985/yearbook-02-current-status.pdf',
        'extractor': 'extract_ncl1985_public_libraries.py', 'output_flag': '--out',
        'retrieved_at': '2026-11-27T17:04:00.852866+00:00',
        'method': 'Pinned scanned PDF. Quantity, placement and scope checked against the adjacent original prose.',
    },
    'ncl_early_89': {
        'document': 'ncl-ed89-public-libraries', 'file': 'raw/ncl-early-89/yearbook-89-public-library.pdf',
        'extractor': 'extract_ncl89_public_libraries.py', 'output_flag': '--out',
        'retrieved_at': '2026-11-27T17:04:04.361853+00:00',
        'arguments': ('--ocr', 'raw/ncl-early-89/ocr-cell-readback.jsonl'),
        'method': 'Pinned scanned PDF. Full numeric grid image review with Apple Vision; independently image-read table 3-1 and visually rechecked all OCR mismatches.',
    },
}

CSV_FIELDS = (
    'observation_id', 'source_id', 'data_year', 'geography', 'geographic_scope',
    'indicator', 'value', 'raw_value', 'value_status', 'unit', 'unit_raw', 'unit_status',
    'source_url', 'source_sha256', 'source_locator', 'source_table', 'source_table_title',
    'source_row', 'source_column', 'source_pdf_page', 'source_printed_page', 'source_edition_roc',
    'source_download_url', 'source_local_path', 'source_retrieved_at', 'source_title', 'publication_date',
)


def build(batch):
    spec = BATCHES[batch]
    raw = (ROOT / spec['file']).parent
    with TemporaryDirectory(prefix='library-reviewed-tables-') as directory:
        out = Path(directory)
        subprocess.run([
            sys.executable, str(ROOT / 'scripts' / spec['extractor']), '--project', str(ROOT),
            '--source', str(ROOT / spec['file']), spec['output_flag'], str(out),
            '--retrieved-at', spec['retrieved_at'], *spec.get('arguments', ()),
        ], check=True)
        rows = load_records(out / 'observations.jsonl')
        if not rows or len(rows) != len({row['observation_id'] for row in rows}):
            raise ValueError('Empty extraction or duplicate observation IDs')
        if any(row['component_source_id'] != spec['document'] or set(row) - set(COLUMNS) for row in rows):
            raise ValueError('Unexpected source identity or canonical fields')
        rows = [{field: row.get(field) for field in COLUMNS} for row in rows]
        for row in rows:
            if isinstance(row['source_cell_bbox'], (list, dict)):
                row['source_cell_bbox'] = json.dumps(row['source_cell_bbox'], ensure_ascii=False, separators=(',', ':'))
        for name in ('documents.json', 'verification.json', 'source_cells.json', 'source_cells.jsonl'):
            path = out / name
            if path.is_file():
                (raw / name).write_bytes(path.read_bytes())
        write_json(raw / 'definition-evidence.json', source_cards(rows, spec['method']))
        record_io.write(ROOT, f'derived/{batch}_observations.jsonl', rows)
        with (ROOT / 'derived' / f'{batch}_long.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    **row,
                    'source_url': row['source_page_url'],
                    'source_download_url': row['source_url'].split('#', 1)[0],
                    'source_local_path': row['source_snapshot_path'],
                    'source_retrieved_at': row['retrieved_at'],
                    'source_title': row['source_edition'] or row['source_table_title'],
                })
    print(json.dumps({'batch': batch, 'observations': len(rows)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True, choices=BATCHES)
    build(parser.parse_args().batch)
