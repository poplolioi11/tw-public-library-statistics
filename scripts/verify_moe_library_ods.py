#!/usr/bin/env python3
"""Cross-check MOE extract with an independent DOM reader and all three files."""

import argparse
import collections
import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.dom import Node, minidom

NS_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"


def dom_text(node):
    if node.nodeType == Node.TEXT_NODE:
        return node.data
    if node.namespaceURI == NS_TEXT:
        if node.localName == "s":
            return " " * int(node.getAttributeNS(NS_TEXT, "c") or "1")
        if node.localName == "tab":
            return "\t"
        if node.localName == "line-break":
            return "\n"
    return "".join(dom_text(child) for child in node.childNodes)


def worksheet_display(element):
    return "\n".join(dom_text(paragraph) for paragraph in element.childNodes
                     if paragraph.namespaceURI == NS_TEXT and paragraph.localName == "p")


def column_number(letters):
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter) - ord("A") + 1
    return result


def source_rows(workbook, wanted):
    positions = {}
    for name, target_row_col in wanted.items():
        sheet = workbook[name]
        current_row = 1
        for row in sheet.getElementsByTagNameNS(NS_TABLE, "table-row"):
            repeats = int(row.getAttributeNS(NS_TABLE, "number-rows-repeated") or 1)
            selected = sorted(number for number in target_row_col if current_row <= number < current_row + repeats)
            if selected:
                cells = [cell for cell in row.childNodes if cell.namespaceURI == NS_TABLE
                         and cell.localName in {"table-cell", "covered-table-cell"}]
                current_column = 1
                for cell in cells:
                    column_repeats = int(cell.getAttributeNS(NS_TABLE, "number-columns-repeated") or 1)
                    for number in selected:
                        for column, text in target_row_col[number].items():
                            if current_column <= column < current_column + column_repeats:
                                positions[(name, text)] = cell
                    current_column += column_repeats
            current_row += repeats
    return positions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    folder = args.output_dir
    summary = json.loads((folder / "moe_summary.json").read_text())
    source_sha = hashlib.sha256(args.source.read_bytes()).hexdigest()
    assert source_sha == summary["source"]["source_sha256"]
    with zipfile.ZipFile(args.source) as container:
        original = minidom.parseString(container.read("content.xml"))
    workbook = {
        node.getAttributeNS(NS_TABLE, "name"): node
        for node in original.getElementsByTagNameNS(NS_TABLE, "table")
    }
    cells = [json.loads(line) for line in (folder / "moe_cells.jsonl").open()]
    required = collections.defaultdict(lambda: collections.defaultdict(dict))
    for cell in cells:
        coords = cell["source_workbook_context"]
        letter, row = re.fullmatch(r"([A-Z]+)([1-9]\d*)", coords["cell"]).groups()
        required[coords["sheet"]][int(row)][column_number(letter)] = coords["cell"]
    positions = source_rows(workbook, required)
    assert len(cells) == len(positions) == summary["observations"]
    kinds = collections.Counter()
    with (folder / "moe_canonical.jsonl").open() as canonical, (folder / "moe_long.csv").open(
        encoding="utf-8-sig", newline=""
    ) as csv_stream:
        for cell, line, trace in zip(cells, canonical, csv.DictReader(csv_stream), strict=True):
            coords = cell["source_workbook_context"]
            e = positions[coords["sheet"], coords["cell"]]
            row = json.loads(line)
            original_display = worksheet_display(e)
            assert e.localName == "table-cell"
            assert original_display == row["raw_value"] == trace["value_raw"] == cell["value_raw"]
            assert (e.getAttributeNS(NS_OFFICE, "value") or None) == coords["original_stored_value"]
            assert (e.getAttributeNS(NS_TABLE, "formula") or None) == coords["original_formula"]
            assert cell["source_sha256"] == row["source_sha256"] == trace["source_sha256"] == source_sha
            assert cell["source_locator"] == row["source_locator"] == trace["source_locator"]
            assert row["value_status"] == trace["value_status"] == cell["value_status"]
            assert row["observation_id"] == trace["observation_id"]
            kinds[row["value_status"]] += 1
            if row["value_status"] == "reported":
                formatted = Decimal(unicodedata.normalize("NFKC", original_display).strip().replace(",", ""))
                assert formatted == Decimal(str(row["value"])) == Decimal(trace["value"]) == Decimal(cell["value"])
                stored = Decimal(coords["original_stored_value"])
                assert stored.quantize(Decimal(1).scaleb(formatted.as_tuple().exponent), rounding=ROUND_HALF_UP) == formatted
            elif row["value_status"] == "source_marker":
                assert original_display.strip() == "-" and row["value"] is None and not trace["value"]
            elif row["value_status"] == "source_blank":
                assert not original_display and row["value"] is None and not trace["value"]
            else:
                raise AssertionError("Unknown source value status")
    assert dict(kinds) == summary["status_counts"]
    sheets = {entry["sheet"]: entry for entry in summary["sheets"]}
    assert len(sheets) == len(workbook) == 41
    assert len(sheets["101縣"]["column_labels"]) == 27 and sheets["101縣"]["county_columns"] == 22
    assert len(sheets["114縣"]["column_labels"]) == 26 and sheets["114縣"]["county_columns"] == 22
    probes = {
        ("101縣", "C11"): ("54436793", "冊"),
        ("101", "C11"): ("62904803", "冊"),
        ("114縣", "C13"): ("131780931", "冊"),
        ("114", "C12"): ("131780931", "冊"),
        ("114縣", "C11"): ("856346547", None),
    }
    observed = {
        (c["source_workbook_context"]["sheet"], c["source_workbook_context"]["cell"]): (c["value"], c["unit"])
        for c in cells
    }
    assert all(observed[key] == value for key, value in probes.items())
    print(json.dumps({"source_sha256": source_sha, "all_cells_verified": len(cells),
                      "recognised_worksheets": len(sheets), "counts": kinds}, ensure_ascii=False))


if __name__ == "__main__":
    main()
