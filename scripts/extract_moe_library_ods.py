#!/usr/bin/env python3
"""Extract the MOE public-library workbook's displayed cells and official provenance."""

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SOURCE_URL = "https://stats.moe.gov.tw/files/time/library.ods"
DEFINITION_URL = (
    "https://www.stat.gov.tw/News_NoticeCalendar_Content_temp.aspx"
    "?MetaI_D=104&n=3717&year=2026"
)
SOURCE_SHA = "b84bb8cc4f05283aebf429bc6dc082232e3eaf432f510a60201a3e9e1709aa42"
RETRIEVED_AT = "2026-11-27T15:37:53.705149+00:00"
SOURCE_PATH = "raw/moe-library-ods/library.ods"
DOCUMENT_ID = "moe-library-ods"
NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
}
TABLE = "{" + NS["table"] + "}"
TEXT = "{" + NS["text"] + "}"
OFFICE = "{" + NS["office"] + "}"
SECTION_RE = re.compile(r"^(?:圖書及非書資料收藏數量|[一二三]、)")
FOOTER_RE = re.compile(r"^(?:資料來源|說明|製表年月)")
NUMBER_RE = re.compile(r"^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$")
DASHES = {"-", "－", "—", "–", "―", "─"}
CAPTURE_COLUMNS = 36
EXPLICIT_NULLS = {
    "value", "unit", "unit_raw", "period_start", "period_end",
    "source_pdf_page", "source_printed_page", "license_url",
}


def document_metadata(retrieved_at):
    return {
        "candidate_id": DOCUMENT_ID,
        "title": "教育部統計處《公立公共圖書館統計》歷年工作簿",
        "official_url": SOURCE_URL,
        "catalogue_url": DEFINITION_URL,
        "source_sha256": SOURCE_SHA,
        "source_local_path": SOURCE_PATH,
        "source_version_id": f"{DOCUMENT_ID}@sha256:{SOURCE_SHA}",
        "retrieved_at": retrieved_at,
        "publisher": "教育部統計處",
        "edition_raw": "教育部統計處 library.ods（原件屬性修改日 2026-06-23）",
        "source_bytes": 259186,
        "snapshot_distribution": "not_in_public_bundle",
        "rights_scope": "原表統計事實及必要表頭；工作簿原件未隨公開包提供",
    }


def element_text(e):
    """Preserve ODF typography, including explicit text:s run lengths."""
    parts = [e.text or ""]
    for child in e:
        if child.tag == TEXT + "s":
            parts.append(" " * int(child.get(TEXT + "c", "1")))
        elif child.tag == TEXT + "tab":
            parts.append("\t")
        elif child.tag == TEXT + "line-break":
            parts.append("\n")
        else:
            parts.append(element_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def displayed(e):
    if e is None:
        return ""
    return "\n".join(element_text(p) for p in e.findall("text:p", NS))


def configured(value):
    return unicodedata.normalize("NFKC", value).strip()


def clean_label(value):
    return re.sub(r"\s+", " ", value.strip())


def compact_header(value):
    return re.sub(r"\s+", "", value)


def col_letters(number):
    result = ""
    while number:
        number, digit = divmod(number - 1, 26)
        result = chr(ord("A") + digit) + result
    return result


def grid(sheet):
    result = {}
    row_number = 1
    for row in sheet.findall("table:table-row", NS):
        repetition = int(row.get(TABLE + "number-rows-repeated", "1"))
        values = {}
        column = 1
        for element in row:
            if element.tag not in {TABLE + "table-cell", TABLE + "covered-table-cell"}:
                continue
            column_repeat = int(element.get(TABLE + "number-columns-repeated", "1"))
            for index in range(column, min(column + column_repeat, CAPTURE_COLUMNS + 1)):
                values[index] = element
            column += column_repeat
            if column > CAPTURE_COLUMNS:
                break
        for index in range(row_number, min(row_number + repetition, 70)):
            result[index] = values
        row_number += repetition
        if row_number > 70:
            break
    return result


def parse_amount(element):
    visible = displayed(element)
    stored = element.get(OFFICE + "value")
    if not visible.strip():
        if stored is not None or element.get(TABLE + "formula"):
            raise ValueError("Numeric XML cell without a displayed value")
        return None, "source_blank", "empty_independent_cell"
    literal = configured(visible)
    if literal in DASHES:
        # The visible dash often masks stored numeric zero. Its semantics
        # are unspecified, so zero remains supplemental metadata only.
        if stored is not None and Decimal(stored) != 0:
            raise ValueError("A dash masks a nonzero stored value")
        return None, "source_marker", "dash_display_cached_zero" if stored is not None else "literal_dash"
    if not NUMBER_RE.fullmatch(literal):
        raise ValueError(f"Unreviewed source literal {visible!r}")
    amount = Decimal(literal.replace(",", ""))
    if stored is None:
        raise ValueError(f"Source text number has no stored numeric value {visible!r}")
    stored_amount = Decimal(stored)
    if amount != stored_amount:
        precision = abs(amount.as_tuple().exponent)
        increment = Decimal(1).scaleb(-precision)
        if stored_amount.quantize(increment, rounding=ROUND_HALF_UP) != amount:
            raise ValueError(f"Display/cache disagreement not explained by rounding {visible!r}, {stored}")
        return str(amount), "reported", "display_rounded_stored_number_preserved"
    return str(amount), "reported", "display_equals_stored_number"


def metric_description(raw_label, section, parent):
    normalized = configured(raw_label)
    unit_match = re.search(r"\(([^()]*)\)\s*$", normalized)
    unit_raw = None
    name = clean_label(raw_label)
    temporal = "annual_source_reference_exact_period_unconfirmed"
    if unit_match and unit_match.group(1) != "含東南亞文":
        unit_raw = unit_match.group(1).split(";")[0]
        name = clean_label(re.sub(r"[（(][^（）()]*[）)]\s*$", "", raw_label))
    if re.match(r"^(?:圖書館數\s*)?(總館|分館|區館)$", name):
        if not name.startswith("圖書館數"):
            name = "圖書館數 " + name
        temporal = "stock_year_end"
    elif re.search(r"\d+年底", normalized):
        temporal = "stock_year_end"
    elif name.startswith("全年"):
        temporal = "flow_calendar_year"
    elif section or SECTION_RE.match(normalized):
        temporal = "stock_year_end"
    if SECTION_RE.match(normalized):
        metric = name
    elif section:
        metric = f"{section}／{name}"
    else:
        metric = name
    if normalized in ("中文", "外文", "外文(含東南亞文)"):
        if parent is None:
            raise ValueError(f"No parent indicator for {raw_label!r}")
        metric = f"{section}／{parent[0]}／{name}"
        return metric, parent[1], "inherited_literal_parent_row_unit", temporal, name
    if name == "線上（自購或自行建置）資料庫":
        # Its row omits a separate unit. Do not project the subtotal's 項
        # upward into a heterogeneous set of other 種-denominated entries.
        unit_raw = None
    return metric, unit_raw, "literal_row_unit" if unit_raw else "unit_not_printed_on_measure_row", temporal, name


def qualified_columns(rows, header_row, by_county):
    region = displayed(rows[3][3])
    national = displayed(rows[3][2]).strip()
    if national != "國家圖書館" or "公立公共圖書館" not in compact_header(region):
        raise ValueError("Original top-level sheet labels changed")
    heads = {2: national}
    for idx in range(3, CAPTURE_COLUMNS + 1):
        variants = [displayed(rows[row].get(idx)) for row in range(3, header_row + 1)]
        for v in reversed(variants):
            label = v.strip()
            if idx == 3 and label in {"計", "總計"}:
                heads[idx] = v
                break
            if idx >= 4 and label:
                heads[idx] = v
                break
    if sorted(heads) != list(range(2, max(heads) + 1)):
        raise ValueError(f"Workbook headers skip columns: {heads}")
    if not by_county and compact_header(heads[4]) != "國立":
        raise ValueError("Establishment level heading no longer identifies national public libraries")
    return heads, region


def source_scope(column_index, header, by_county, region):
    group_label = compact_header(region)
    name = compact_header(header)
    if column_index == 2:
        return ("國家圖書館", "separately_reported_national_library",
                "institution_only", "國家圖書館單列",
                "國家圖書館單獨統計欄，與公立公共圖書館欄分開。")
    if column_index == 3:
        note = (
            "原表欄頭明示總計含國立公共資訊圖書館及國立臺灣圖書館，即使兩館也分列。"
            if "含國立公共資訊" in group_label else
            "公立公共圖書館原表總計。國家圖書館另列。")
        return ("公立公共圖書館" + ("縣市表總計" if by_county else "設立別總計"),
                "published_public_library_total", "published_total",
                "separate_national_library_column_excluded_from_public_subtotal", note)
    if by_county and re.fullmatch(r"[\u4e00-\u9fff]+[縣市]", name):
        return (name, "county_source_label", "source_county_quantity",
                "national_public_libraries_separately_labeled",
                "公立公共圖書館縣市欄，沿用當年原表行政區名稱與範圍。")
    if by_county:
        return (name, "separately_reported_library", "institution_only",
                "original_named_public_library_or_provincial_library",
                "縣市表另列館別，與縣市欄分開，可能包含於原表公立合計。")
    return (name, "published_public_library_establishment_type", "source_type_quantity",
            "national_public_libraries_by_establishment_class",
            f"公立公共圖書館按設立別。館類為{clean_label(header)}，沿用原表。")


def read_source(path):
    source_body = path.read_bytes()
    if hashlib.sha256(source_body).hexdigest() != SOURCE_SHA:
        raise ValueError("Official workbook changed. Review the new source version first.")
    with zipfile.ZipFile(path) as book:
        root = ET.fromstring(book.read("content.xml"))
    return root.findall("office:body/office:spreadsheet/table:table", NS)


def extract_sheet(sheet, document):
    rows = grid(sheet)
    sheet_name = sheet.get(TABLE + "name")
    match = re.fullmatch(r"(\d{2,3})(縣)?", sheet_name)
    if not match:
        raise ValueError(f"Unexpected workbook sheet {sheet_name!r}")
    roc_year, by_county = int(match.group(1)), bool(match.group(2))
    year = roc_year + 1911
    title = displayed(rows[1][1]).strip()
    period_header = displayed(rows[2][1]).strip()
    if not period_header.startswith(f"{roc_year}年"):
        raise ValueError(f"Worksheet year label is inconsistent: {sheet_name} {period_header}")
    header_rows = [
        idx for idx in range(3, 6)
        if displayed(rows[idx][3]).strip() in {"總計", "計"}
    ]
    if len(header_rows) != 1:
        raise ValueError(f"Cannot identify a unique bottom header row in {sheet_name!r}")
    header_row = header_rows[0]
    headers, region = qualified_columns(rows, header_row, by_county)
    note_row = next(idx for idx in sorted(rows) if displayed(rows[idx].get(1)).strip().startswith("資料來源"))
    notes = [
        clean_label(displayed(rows[idx].get(1))) for idx in range(note_row, min(note_row + 5, max(rows) + 1))
        if displayed(rows[idx].get(1)).strip()
    ]
    made = [
        (f"{col_letters(col)}{idx}", clean_label(displayed(rows[idx][col])))
        for idx in range(note_row, min(note_row + 5, max(rows) + 1))
        for col in range(2, CAPTURE_COLUMNS + 1)
        if "製表年月" in displayed(rows[idx].get(col))
    ]
    audit = []
    cells = []
    section = parent = None
    for idx in range(header_row + 1, note_row):
        row = rows[idx]
        raw_label = displayed(row.get(1))
        label = configured(raw_label)
        if not label or FOOTER_RE.match(label):
            raise ValueError(f"Unexpected unlabelled/nondata row {sheet_name}!A{idx}")
        metric, raw_unit, unit_basis, temporal, name = metric_description(raw_label, section, parent)
        section_row = bool(SECTION_RE.match(label))
        if section_row:
            section = name
            parent = None
        elif re.match(r"^[１２12](?:圖書|期刊)", name):
            parent = (name, raw_unit)
        for col in range(max(headers) + 1, CAPTURE_COLUMNS + 1):
            stray = row.get(col)
            if stray is not None and (displayed(stray).strip() or stray.get(OFFICE + "value")):
                audit.append({
                    "cell": f"{col_letters(col)}{idx}",
                    "display": displayed(stray),
                    "stored_value": stray.get(OFFICE + "value"),
                    "formula": stray.get(TABLE + "formula"),
                    "reason": "no printed lower or upper header identifying a statistical column",
                })
        for col, header in headers.items():
            e = row.get(col)
            position = f"{col_letters(col)}{idx}"
            if e is None or e.tag == TABLE + "covered-table-cell":
                audit.append({"cell": position, "reason": "missing or covered position, not an independent cell"})
                continue
            if int(e.get(TABLE + "number-columns-spanned", "1")) > 1 or int(e.get(TABLE + "number-rows-spanned", "1")) > 1:
                if displayed(e).strip() or e.get(OFFICE + "value"):
                    raise ValueError(f"Visible numeric cells may not be reproduced over multiple positions: {sheet_name}!{position}")
                audit.append({"cell": position, "reason": "blank merged cell anchor, not an independent statistic"})
                continue
            amount, value_status, amount_check = parse_amount(e)
            if section_row and value_status == "source_blank":
                continue
            geography, entity_kind, role, national_scope, population = source_scope(col, header, by_county, region)
            flags = []
            if amount_check == "dash_display_cached_zero":
                flags.append("ods_visible_dash_with_stored_zero")
            if amount_check == "display_rounded_stored_number_preserved":
                flags.append("ods_visible_rounded_value_and_exact_stored_value")
            budget_uncertain = roc_year >= 111 and col >= 3 and "全年購買圖書資料費" in metric
            if budget_uncertain:
                flags.append("printed_budget_unit_scale_conflict_unresolved")
            workbook = {
                "sheet": sheet_name,
                "cell": position,
                "row_label_cell": f"A{idx}",
                "top_header_cell": "B3" if col == 2 else "C3",
                "bottom_header_cell": f"{col_letters(col)}{header_row}",
                "original_display": displayed(e),
                "original_stored_value": e.get(OFFICE + "value"),
                "original_stored_value_type": e.get(OFFICE + "value-type"),
                "original_formula": e.get(TABLE + "formula"),
                "display_and_stored_value_status": amount_check,
                "workbook_footer_start": f"A{note_row}",
                "table_prepared_at_as_printed": made,
            }
            if col > 3 and by_county and not displayed(rows[header_row].get(col)).strip():
                header_locations = [idx for idx in range(3, header_row) if displayed(rows[idx].get(col)).strip()]
                workbook["bottom_header_cell"] = f"{col_letters(col)}{header_locations[-1]}"
            if col == 2:
                workbook["bottom_header_cell"] = "B3"
            period_raw = f"民國{roc_year}年全年" if temporal == "flow_calendar_year" else period_header
            grouping = "county" if by_county else "establishment"
            locator = f"ODS sheet {sheet_name}; {position}; row label A{idx}; column heading {workbook['bottom_header_cell']}"
            cells.append({
                "cell_id": f"{DOCUMENT_ID}/{sheet_name}/{position}",
                "source_document_id": DOCUMENT_ID,
                "source_url": SOURCE_URL,
                "source_catalogue_url": DEFINITION_URL,
                "source_sha256": SOURCE_SHA,
                "source_version_id": document["source_version_id"],
                "source_pdf_page": None,
                "source_printed_page": None,
                "source_table": grouping,
                "source_table_title": title,
                "source_row": str(idx),
                "source_column": col_letters(col),
                "source_locator": locator,
                "row_label_raw": raw_label,
                "column_label_raw": header,
                "entity_raw": geography,
                "entity_kind": entity_kind,
                "geography_vintage": f"民國{roc_year}年工作表原列口徑" if by_county else "原工作表設立別",
                "data_year": year,
                "period_raw": period_raw,
                "period_status": "literal_sheet_year_and_official_reference_period",
                "metric_id": hashlib.sha256(metric.encode()).hexdigest()[:12],
                "metric_raw": metric,
                "value": amount,
                "value_raw": displayed(e),
                "value_status": value_status,
                "unit": None if budget_uncertain else raw_unit,
                "unit_raw": raw_unit,
                "unit_status": "printed_budget_unit_scale_conflict_unresolved" if budget_uncertain else unit_basis,
                "temporal_kind": temporal,
                "population_scope": population,
                "national_libraries_scope": national_scope,
                "aggregation_role": role,
                "source_notes": [
                    f"教育部統計處原工作表{sheet_name}，設立別與縣市別各自保留。",
                    "畫面短橫與儲存零分開，年末存量與全年流量依官方統計定義。",
                    *(
                        ["原印萬元，但公立欄自111年起量值尺度突變，原數照錄，正規單位待核。"]
                        if budget_uncertain else []
                    ),
                ],
                "quality_flags": flags,
                "independent_check": {"method": "ODF displayed text and stored value/format reconciliation", "matched": True},
                "source_edition": document["edition_raw"],
                "source_table_year_context": period_header,
                "source_workbook_context": workbook,
                "subtotals_and_indicators_overlap": section_row,
            })
    result = {
        "sheet": sheet_name,
        "data_year": year,
        "grouping": "county" if by_county else "establishment",
        "title": title,
        "period_header_raw": period_header,
        "range": f"B{header_row + 1}:{col_letters(max(headers))}{note_row - 1}",
        "upper_header_raw": region,
        "column_labels": {col_letters(i): h for i, h in headers.items()},
        "county_columns": sum(
            source_scope(c, headers[c], by_county, region)[1] == "county_source_label"
            for c in headers
        ),
        "source_footer": notes,
        "table_prepared_at_as_printed": made,
        "observations": len(cells),
        "status_counts": dict(collections.Counter(c["value_status"] for c in cells)),
        "excluded_nondata_positions": audit,
    }
    return cells, result


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def compared_published_totals(cells):
    groups = collections.defaultdict(dict)
    for cell in cells:
        if cell["aggregation_role"] == "published_total":
            groups[(cell["data_year"], cell["metric_raw"])][cell["source_table"]] = cell
    disagreements = []
    for (year, metric), pair in sorted(groups.items()):
        if set(pair) != {"county", "establishment"}:
            continue
        county, establishment = pair["county"], pair["establishment"]
        if (county["value"], county["value_status"]) == (establishment["value"], establishment["value_status"]):
            continue
        disagreements.append({
            "data_year": year,
            "indicator": metric,
            "county_table": {"value_raw": county["value_raw"], "source_locator": county["source_locator"]},
            "establishment_table": {
                "value_raw": establishment["value_raw"], "source_locator": establishment["source_locator"],
            },
        })
    return disagreements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--retrieved-at", default=RETRIEVED_AT)
    args = parser.parse_args()
    root = args.project_root.resolve()
    source = args.source or root / SOURCE_PATH
    output = args.output_dir or root / "derived"
    document = document_metadata(args.retrieved_at)
    sys.path.insert(0, str(root / "scripts"))
    from build_discovered_20261028 import adapt

    cells, sheets = [], []
    for sheet in read_source(source):
        records, metadata = extract_sheet(sheet, document)
        cells.extend(records)
        sheets.append(metadata)
    expected_sheets = {"94"} | {str(y) + suffix for y in range(95, 115) for suffix in ("", "縣")}
    if {s["sheet"] for s in sheets} != expected_sheets or len(sheets) != 41:
        raise ValueError("The expected official sheet inventory differs from the workbook")
    if len(cells) != len({c["cell_id"] for c in cells}):
        raise ValueError("Workbook cell coordinates overlap")
    columns = json.loads((root / "scripts/discovered_20261028_canonical_columns.json").read_text())["columns"]
    canonical = []
    for cell in cells:
        item = adapt(cell, document)
        item["source_location_kind"] = "official_spreadsheet_cell"
        item["source_field"] = cell["metric_raw"]
        item["source_column_path"] = cell["column_label_raw"]
        item["value_parse_rule"] = "ods_visible_literal_number; stored_precision_and_dashes_separately_retained"
        item["unit_basis"] = cell["unit_status"]
        item["comparability"] = "original_statistical_workbook_only_groupings_and_original_geographies_kept_separate"
        if cell["temporal_kind"] == "flow_calendar_year":
            item["period_start"] = f"{cell['data_year']}-01-01"
            item["period_end"] = f"{cell['data_year']}-12-31"
            item["period_basis"] = "literal_full_year_row_and_official_statistical_definition"
        elif cell["temporal_kind"] == "stock_year_end":
            item["period_basis"] = "literal_year_end_or_official_static_indicator_definition"
        if set(item) - set(columns):
            raise ValueError(f"Canonical schema lacks {sorted(set(item) - set(columns))}")
        # The canonical workbook component stays below GitHub's single-file
        # limit, while the complete combined builder restores optional fields.
        canonical.append({
            column: item.get(column) for column in columns
            if item.get(column) is not None or column in EXPLICIT_NULLS
        })
    if len(canonical) != len({row["observation_id"] for row in canonical}):
        raise ValueError("Canonical observation identities are duplicated")
    summary = {
        "source": document,
        "source_header_meaning": "See official release calendar and exact original workbook headings; do not add the two groupings together.",
        "sheets": sheets,
        "sheet_count": len(sheets),
        "observations": len(cells),
        "status_counts": dict(collections.Counter(c["value_status"] for c in cells)),
        "display_validation": dict(collections.Counter(
            c["source_workbook_context"]["display_and_stored_value_status"] for c in cells
        )),
        "displayed_zero_values": sum(c["value"] is not None and Decimal(c["value"]) == 0 for c in cells),
        "formula_cells_with_source_cache": sum(bool(c["source_workbook_context"]["original_formula"]) for c in cells),
        "budget_unit_conflict_cells": sum("printed_budget_unit_scale_conflict_unresolved" in c["quality_flags"] for c in cells),
        "excluded_unheaded_or_covered": sum(len(s["excluded_nondata_positions"]) for s in sheets),
        "published_totals_differ_between_workbook_groupings": compared_published_totals(cells),
        "human_double_collation_completed": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "moe_cells.jsonl", cells)
    write_jsonl(output / "moe_canonical.jsonl", canonical)
    write_json(output / "moe_summary.json", summary)
    write_json(output / "moe_documents.json", {"documents": [document]})
    trace_columns = [
        "observation_id", "source_id", "source_sha256", "source_download_url",
        "source_url", "source_local_path", "source_retrieved_at", "source_title",
        "source_edition_roc", "publication_date", "data_year", "sheet", "cell",
        "metric_raw", "entity_raw", "value", "value_raw", "value_status",
        "unit", "unit_raw", "unit_status", "source_locator",
    ]
    trace = []
    for cell, row in zip(cells, canonical, strict=True):
        trace.append({
            **cell,
            "observation_id": row["observation_id"],
            "source_id": row["source_id"],
            "source_download_url": document["official_url"],
            "source_url": document["catalogue_url"],
            "source_local_path": document["source_local_path"],
            "source_retrieved_at": document["retrieved_at"],
            "source_title": document["title"],
            "source_edition_roc": None,
            "publication_date": None,
            "sheet": cell["source_workbook_context"]["sheet"],
            "cell": cell["source_workbook_context"]["cell"],
        })
    with (output / "moe_long.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=trace_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(trace)
    print(json.dumps({
        key: value for key, value in summary.items()
        if key not in {"sheets", "source", "published_totals_differ_between_workbook_groupings"}
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
