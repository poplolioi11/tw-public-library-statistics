#!/usr/bin/env python3
"""Verify phase-one source projections offline; never infer source statistics."""
import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COUNTS = {
    'programme_rows': 119,
    'programme_quantities': 123,
    'local_original_cells': 33705,
    'local_statistical_cells': 18486,
}


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def clean(row):
    return {key: value for key, value in row.items() if key != 'original_fields'}


def ident(value):
    return '"' + value.replace('"', '""') + '"'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError('Expected a project-relative file path')
    return path


def compare_rows(rows, fields, csvrows, sqlfields, sqlrows, require, table):
    """A sparse JSON object contributes to a table-wide union, not a row schema.

    Missing JSON keys map to CSV empty fields and SQLite NULL. Explicit empty
    strings still map to SQLite empty strings, retaining their distinction from
    NULL. original_fields is checked CSV-versus-JSONL only, because SQLite is an
    explicitly documented projection that omits that duplicate private field.
    """
    union = set().union(*(row.keys() for row in rows)) if rows else set()
    sqlunion = union - {'original_fields'}
    require(len(fields) == len(set(fields)), 'Duplicate CSV columns: ' + table)
    require(set(fields) == union, 'CSV union columns differ: ' + table)
    require(len(sqlfields) == len(set(sqlfields)), 'Duplicate SQLite columns: ' + table)
    require(set(sqlfields) == sqlunion, 'SQLite union columns differ: ' + table)
    require(len(rows) == len(csvrows) == len(sqlrows), 'Format row counts differ: ' + table)
    missing_keys = 0
    for index, (raw, crow, srow) in enumerate(zip(rows, csvrows, sqlrows, strict=True), 1):
        require(None not in crow and set(crow) == union,
                'CSV malformed row: ' + table + ':' + str(index))
        require(set(srow) == sqlunion, 'SQLite row schema differs: ' + table)
        for key in union:
            value = raw.get(key)  # An absent key has exactly the NULL contract.
            missing_keys += key not in raw
            label = table + ':' + str(index) + ':' + key
            if isinstance(value, bool):
                # csv.DictWriter emits Python True/False; JSON encoders emit
                # true/false. Both retain Boolean meaning, unlike 1 or 0.
                require(crow[key] in (str(value), stable(value)),
                        'CSV boolean value differs: ' + label)
                if key != 'original_fields':
                    require(srow[key] == stable(value), 'SQLite boolean value differs: ' + label)
            elif isinstance(value, (dict, list)):
                try:
                    parsed = json.loads(crow[key])
                except (TypeError, ValueError) as exc:
                    raise ValueError('CSV structured value is not JSON: ' + label) from exc
                require(stable(parsed) == stable(value), 'CSV structured value differs: ' + label)
                if key != 'original_fields':
                    try:
                        parsed = json.loads(srow[key])
                    except (TypeError, ValueError) as exc:
                        raise ValueError('SQLite structured value is not JSON: ' + label) from exc
                    require(stable(parsed) == stable(value), 'SQLite structured value differs: ' + label)
            else:
                require(crow[key] == ('' if value is None else str(value)),
                        'CSV source value differs: ' + label)
                if key != 'original_fields':
                    require(srow[key] == (None if value is None else str(value)),
                            'SQLite source value differs: ' + label)
    return {'union_columns': len(union), 'sqlite_columns': len(sqlunion),
            'absent_json_keys_checked_as_null': missing_keys}


def validate(root, allow_private_fields=False):
    manifest_path = root / 'docs/phase1-supplements.json'
    manifest = json.loads(manifest_path.read_text())
    checks = 0
    hashes = {'docs/phase1-supplements.json': digest(manifest_path)}

    def require(ok, reason):
        nonlocal checks
        checks += 1
        if not ok:
            raise ValueError(reason)

    require(manifest['dataset_version'] == (root / 'VERSION').read_text().strip(),
            'Supplement version differs')
    require(len(manifest['tables']) == len(EXPECTED_COUNTS)
            and {spec['table'] for spec in manifest['tables']} == set(EXPECTED_COUNTS),
            'Supplement table list differs')
    dbpath = local_path(root, manifest['sqlite'])
    hashes[manifest['sqlite']] = digest(dbpath)
    con = sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    datasets, table_reports = {}, {}
    try:
        require(con.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'SQLite integrity check failed')
        actual_tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        require(actual_tables == set(EXPECTED_COUNTS), 'Unexpected SQLite table list')
        for spec in manifest['tables']:
            table = spec['table']
            path = local_path(root, spec['jsonl'])
            body = path.read_text()
            require(all(line.strip() for line in body.splitlines()), 'Blank JSONL row: ' + table)
            rows = [json.loads(line) for line in body.splitlines()]
            require(all(isinstance(row, dict) for row in rows), 'Non-object JSONL row: ' + table)
            datasets[table] = rows
            if not allow_private_fields:
                require(not any('original_fields' in row for row in rows),
                        'Private whole-row duplicate in published JSONL')
            hashes[spec['jsonl']] = digest(path)
            if allow_private_fields:
                require(hashes[spec['jsonl']] == spec['private_producer_jsonl_sha256'],
                        'Private producer JSONL hash differs: ' + table)
            # Public hashes may differ after removing original_fields. Record
            # actual distributed hashes without misusing a private producer hash.
            csvpath = local_path(root, spec['csv'])
            hashes[spec['csv']] = digest(csvpath)
            with csvpath.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                fields, csvrows = reader.fieldnames or [], list(reader)
            if not allow_private_fields:
                require('original_fields' not in fields, 'Private whole-row duplicate in published CSV')
            sqlfields = [row[1] for row in con.execute('PRAGMA table_info(' + ident(table) + ')')]
            sqlrows = [dict(row) for row in con.execute('SELECT * FROM ' + ident(table) + ' ORDER BY rowid')]
            require(len(rows) == spec['records'] == EXPECTED_COUNTS[table],
                    'Supplement source-scope count differs: ' + table)
            table_reports[table] = compare_rows(rows, fields, csvrows, sqlfields, sqlrows, require, table)
            table_reports[table]['records'] = len(rows)
            if table.startswith('programme'):
                require(all(row.get('data_year') is None for row in rows),
                        'Programme silently assigned to calendar year')
    finally:
        con.close()

    local = datasets['local_statistical_cells']
    require(len({row['observation_id'] for row in local}) == len(local),
            'Duplicate statistical source-cell identity')
    unresolved = [row for row in local if row['value_status'] == 'source_display_typed_value_conflict_unresolved']
    require(len(unresolved) == 5098, 'Reviewed display/typed conflict count differs')
    require(all(row['value'] is None and row['value_raw'].strip() == '-'
                and str(row.get('source_typed_numeric_value')) == '0' for row in unresolved),
            'Display dash/typed zero conflict changed representation or final value')
    conflicts = [row for row in local if row['period_status'] == 'source_sheet_name_header_period_conflict_unresolved']
    require(len(conflicts) == 176, 'Reviewed period-conflict cell count differs')
    require(all(row['period_year'] is None and row['period_month'] is None for row in conflicts),
            'Conflicting sheet/header date silently chosen')
    require(sum(row['value_status'] == 'source_marker' for row in local) == 1,
            'Reviewed literal source marker count differs')
    facts = datasets['local_original_cells']
    factmap = {(row['source_id'], row['source_sheet'], row['source_cell']): row for row in facts}
    require(len(factmap) == len(facts), 'Duplicate original source-cell coordinates')
    for row in local:
        key = (row['source_id'], row['source_sheet'], row['source_cell'])
        require(key in factmap, 'Statistical cell absent from original-cell table')
        fact = factmap[key]
        for field, value in fact.items():
            require(field in row and stable(row[field]) == stable(value),
                    'Statistical/original source-cell value differs: ' + field)

    partition_path = root / 'docs/phase1-source-cell-partitions.json'
    hashes['docs/phase1-source-cell-partitions.json'] = digest(partition_path)
    part = json.loads(partition_path.read_text())
    parent_spec = next(spec for spec in manifest['tables'] if spec['table'] == 'local_statistical_cells')
    require(part['parent_jsonl'] == parent_spec['jsonl'] and part['records'] == len(local),
            'Partition parent metadata differs')
    groups = defaultdict(list)
    for row in local:
        groups[(row['source_id'], row['source_sheet'])].append(clean(row))
    entries = part['partitions']
    require(len({entry['path'] for entry in entries}) == len(entries), 'Duplicate partition file paths')
    require(len({(entry['source_id'], entry['source_sheet']) for entry in entries}) == len(entries)
            and {(entry['source_id'], entry['source_sheet']) for entry in entries} == set(groups),
            'Partition source-sheet coverage differs')
    allrows = []
    for entry in entries:
        path = local_path(root, entry['path'])
        body = path.read_bytes()
        sha = hashlib.sha256(body).hexdigest()
        require(sha == entry['sha256'], 'Partition hash differs')
        hashes[entry['path']] = sha
        data = [json.loads(line) for line in body.decode().splitlines()]
        require(len(data) == entry['records'], 'Partition count differs')
        key = (entry['source_id'], entry['source_sheet'])
        require(all((row['source_id'], row['source_sheet']) == key for row in data),
                'Partition source-sheet label differs')
        require([stable(row) for row in data] == [stable(row) for row in groups[key]],
                'Partition source-sheet rows or order differ')
        require(dict(Counter(row['period_status'] for row in data)) == entry['period_status_counts'],
                'Partition period-status counts differ')
        allrows.extend(data)
    require(sorted(stable(row) for row in allrows) == sorted(stable(clean(row)) for row in local),
            'Source-sheet partition multiset differs from parent data')

    result = {'status': 'pass', 'dataset_version': manifest['dataset_version'],
              'assertions': checks, **{table: len(rows) for table, rows in datasets.items()},
              'unresolved_display_typed': len(unresolved), 'unresolved_period_cells': len(conflicts),
              'partitions': len(entries), 'tables': table_reports, 'file_sha256': hashes,
              'formats': 'CSV/JSONL/SQLite agree for every union-schema field; source-sheet partition rows, order, multiset and SHA agree',
              'scope': 'Format/projection verification; does not replace original-workbook/PDF source review or certify official reporting accuracy.',
              'private_producer_sha_policy': 'Private mode verifies producer JSONL SHA; public projection records its own distributed SHA without conflating it with the private producer SHA.'}
    reference = root / 'research/phase1-local-independent-review.json'
    if reference.exists():
        review = json.loads(reference.read_text())
        reviewed_hashes = review.get('comparison', {}).get('final_file_sha256', {})
        matches = {path: hashes.get(path) == sha for path, sha in reviewed_hashes.items()}
        if allow_private_fields:
            require(len(matches) == 4 and all(matches.values()),
                    'Local source files changed after independent original-XML review')
        result['assertions'] = checks
        result['independent_original_xml_review_reference'] = {
            'path': str(reference.relative_to(root)), 'sha256': digest(reference),
            'reported_result': review.get('result'), 'seen_initial': review.get('seen_initial'),
            'source_cell_checks': review.get('comparison', {}).get('checks'),
            'reviewed_file_sha256_matches': matches,
            'reference_only_not_rerun_originals': True,
        }
    return result


def self_test():
    """Isolated regressions for sparse union/NULL and structured-value semantics."""
    import unittest

    def require(ok, reason):
        if not ok:
            raise ValueError(reason)

    class UnionTests(unittest.TestCase):
        def fixture(self):
            rows = [{'id': 'a', 'optional': 'x'}, {'id': 'b'}, {'id': 'c', 'optional': None}]
            crows = [{'id': 'a', 'optional': 'x'}, {'id': 'b', 'optional': ''}, {'id': 'c', 'optional': ''}]
            con = sqlite3.connect(':memory:')
            con.row_factory = sqlite3.Row
            con.execute('CREATE TABLE facts (id TEXT, optional TEXT)')
            con.executemany('INSERT INTO facts VALUES (?,?)', [('a', 'x'), ('b', None), ('c', None)])
            sqlrows = [dict(row) for row in con.execute('SELECT * FROM facts ORDER BY rowid')]
            con.close()
            return rows, ['id', 'optional'], crows, ['id', 'optional'], sqlrows

        def test_sparse_union_is_complete_and_missing_is_null(self):
            report = compare_rows(*self.fixture(), require, 'facts')
            self.assertEqual(report['absent_json_keys_checked_as_null'], 1)

        def test_missing_key_cannot_become_sql_empty_string(self):
            args = list(self.fixture()); args[4][1]['optional'] = ''
            with self.assertRaisesRegex(ValueError, 'SQLite source value differs'):
                compare_rows(*args, require, 'facts')

        def test_explicit_empty_string_is_not_sql_null(self):
            args = list(self.fixture()); args[0][0]['optional'] = ''; args[2][0]['optional'] = ''; args[4][0]['optional'] = None
            with self.assertRaisesRegex(ValueError, 'SQLite source value differs'):
                compare_rows(*args, require, 'facts')

        def test_unexpected_sql_column_is_rejected(self):
            args = list(self.fixture()); args[3].append('extra')
            with self.assertRaisesRegex(ValueError, 'SQLite union columns differ'):
                compare_rows(*args, require, 'facts')

        def test_csv_sparse_column_must_still_exist(self):
            args = list(self.fixture()); args[1].remove('optional')
            with self.assertRaisesRegex(ValueError, 'CSV union columns differ'):
                compare_rows(*args, require, 'facts')

        def test_bool_is_not_numeric_one(self):
            with self.assertRaisesRegex(ValueError, 'CSV boolean value differs'):
                compare_rows([{'flag': True}], ['flag'], [{'flag': '1'}], ['flag'], [{'flag': 'true'}], require, 'facts')

        def test_python_csv_bool_and_json_bool_preserve_same_value(self):
            compare_rows([{'flag': False}], ['flag'], [{'flag': 'False'}], ['flag'], [{'flag': 'false'}], require, 'facts')

        def test_private_duplicate_compares_csv_but_is_omitted_from_sql(self):
            report = compare_rows([{'id': 'a', 'original_fields': {'cell': 0}}], ['id', 'original_fields'],
                                  [{'id': 'a', 'original_fields': '{"cell":0}'}], ['id'], [{'id': 'a'}], require, 'facts')
            self.assertEqual(report['sqlite_columns'], 1)

        def test_builder_noop_preserves_all_bytes_and_mtimes(self):
            import contextlib
            import io
            import runpy
            import tempfile

            namespace = runpy.run_path(str(ROOT / 'scripts/build_phase1_supplements.py'))
            build = namespace['main']
            with tempfile.TemporaryDirectory(prefix='phase1-noop-test-') as temporary:
                root = Path(temporary)
                (root / 'derived').mkdir()
                (root / 'docs').mkdir()
                (root / 'VERSION').write_text('isolated-fixture\n')
                fixtures = {
                    'ncl_2005_programmes': [{'id': 'a', 'data_year': None}, {'id': 'b', 'optional': 'x', 'data_year': None}],
                    'ncl_2005_programmes_long': [{'id': 'q', 'data_year': None, 'original_fields': {'original': 0}}],
                    'phase1_local_sources_cells': [{'source_id': 'fixture', 'source_sheet': '113年6月', 'source_cell': 'B10'}],
                    'phase1_local_sources_long': [{'source_id': 'fixture', 'source_sheet': '113年6月', 'source_cell': 'B10', 'period_status': 'unresolved'}],
                }
                for name, rows in fixtures.items():
                    (root / 'derived' / (name + '.jsonl')).write_text(''.join(stable(row) + '\n' for row in rows))
                build.__globals__['ROOT'] = root

                def snapshot():
                    return {str(path.relative_to(root)): (digest(path), path.stat().st_mtime_ns)
                            for path in root.rglob('*') if path.is_file()}

                with contextlib.redirect_stdout(io.StringIO()):
                    build()
                first = snapshot()
                with contextlib.redirect_stdout(io.StringIO()):
                    build()
                self.assertEqual(first, snapshot())

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(UnionTests))
    if not result.wasSuccessful():
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--allow-private-fields', action='store_true')
    parser.add_argument('--report', help='Write deterministic verification JSON at a root-relative path')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    root = args.root.resolve()
    result = validate(root, args.allow_private_fields)
    if args.report:
        path = local_path(root, args.report)
        body = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
        if not path.exists() or path.read_bytes() != body:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
