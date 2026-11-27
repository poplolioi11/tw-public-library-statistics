#!/usr/bin/env python3
"""Read all eight observations in the NCL 1985 table 1 public-library subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pypdfium2

SOURCE_ID = "ncl-ed2-public-libraries-1985"
EXPECTED_SHA256 = "9c9e17f88d0706d2f46738952a797e6c66e6ed5b46f0ad51c64f50cfd58f023a"
EXPECTED_BYTES = 11292745
SOURCE_URL = "https://www.ncl.edu.tw/files/file_pool/1/0Q083566619294348883/23cf6dc8-4e92-4917-b2c2-ef1812a69771.pdf"
CATALOGUE_URL = "https://www.ncl.edu.tw/librarianship-yearbook/0Q083566602665258360"
EDITION = "第二次中華民國圖書館年鑑"
TABLE_TITLE = "臺閩地區各類型圖書館統計表（74年12月）"
AREA_NOTE = "本表包括臺灣地區及金馬地區圖書館。"
FACILITY_NOTE = "** 另設50所分館及14所民衆閱覽室未併入統計"
TABULAR_CREDIT = "民國74年12月國立中央圖書館統計。"
# Values are readings from the pinned source image, checked again by Vision at
# their source coordinates and against the separately typeset facing-page prose.
ROWS = (
    (1, "省市立", "type_count", "4", (0.245, 0.275), r"省市立圖書館4所"),
    (2, "縣市立", "type_count", "21", (0.279, 0.296), r"縣市立圖書館及縣市立文化中心21所"),
    (2, "縣市立", "additional_branches", "50", (0.296, 0.307), r"另設50個分館"),
    (2, "縣市立", "additional_reading_rooms", "14", (0.308, 0.326), r"14個民[衆眾]閱覽室"),
    (3, "鄉鎭市立", "type_count", "236", (0.331, 0.353), r"鄉[鎮鎭]圖書館236所"),
    (4, "社教館", "type_count", "6", (0.371, 0.393), r"社會教育館6所"),
    (5, "私立", "type_count", "69", (0.412, 0.434), r"私立圖書館69所"),
    (6, "小計", "published_subtotal", "336", (0.454, 0.476), r"公共圖書館336所"),
)
METRICS = {
    "type_count": "圖書館數量",
    "published_subtotal": "圖書館數量",
    "additional_branches": "另設分館數量",
    "additional_reading_rooms": "另設民眾閱覽室數量",
}
VISION = r'''
import Foundation
import Vision
for file in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: file)
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hant", "en-US"]
    request.usesLanguageCorrection = false
    request.minimumTextHeight = 0.004
    try VNImageRequestHandler(url: url, options: [:]).perform([request])
    let spans: [[String: Any]] = (request.results ?? []).compactMap { observation in
        guard let reading = observation.topCandidates(1).first else { return nil }
        let b = observation.boundingBox
        return ["text": reading.string, "box": [b.minX, 1-b.maxY, b.maxX, 1-b.minY]]
    }
    let item: [String: Any] = ["id": url.deletingPathExtension().lastPathComponent,
                              "revision": request.revision, "spans": spans]
    print(String(decoding: try JSONSerialization.data(withJSONObject: item, options: [.sortedKeys]), as: UTF8.self))
}
'''


def pinned_source(source):
    body = source.read_bytes()
    if len(body) != EXPECTED_BYTES or hashlib.sha256(body).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Official yearbook source differs from the reviewed bytes.")
    return body


def vision_pages(body):
    with TemporaryDirectory(prefix="ncl1985-review-") as raw_temp:
        folder = Path(raw_temp)
        swift = folder / "recognize.swift"
        swift.write_text(VISION, encoding="utf-8")
        sizes = {}
        with pypdfium2.PdfDocument(body) as pdf:
            if len(pdf) != 21:
                raise ValueError("Original PDF page count differs.")
            for number in (4, 5):
                page = pdf[number - 1]
                sizes[number] = page.get_size()
                if page.get_textpage().get_text_range().strip():
                    raise ValueError("A text layer was found in an expected scan-only page.")
                page.render(scale=2.2).to_pil().save(folder / f"{number}.png")
        result = subprocess.run(
            ["swift", str(swift), str(folder / "4.png"), str(folder / "5.png")],
            check=True, capture_output=True, text=True, timeout=120,
        )
    return {int(rec["id"]): rec for rec in map(json.loads, result.stdout.splitlines())}, sizes


def pdf_box(span, page_size):
    width, height = page_size
    return [round(n * scale, 3) for n, scale in zip(span["box"], (width, height, width, height))]


def detect_count(spans, literal, y_bounds):
    def within(item):
        left, top, right, bottom = item["box"]
        return 0.405 < (left + right) / 2 < 0.48 and y_bounds[0] <= (top + bottom) / 2 < y_bounds[1]

    located = [span for span in spans if within(span) and re.findall(r"[0-9]+", span["text"])]
    if len(located) != 1 or re.findall(r"[0-9]+", located[0]["text"]) != [literal]:
        raise ValueError(f"The pinned scan OCR did not substantiate {literal!r} in {y_bounds}: {located!r}")
    return located[0]


def prose_evidence(spans, pattern):
    lines = sorted((item for item in spans if 0.36 < item["box"][1] < 0.435),
                   key=lambda item: item["box"][1])
    passage = re.sub(r"\s+", "", "".join(item["text"] for item in lines))
    match = re.search(pattern, passage)
    if not match:
        raise ValueError(f"The separately typeset body on PDF page 4 did not corroborate {pattern!r}.")
    return match.group()


def build_cells(document, pages, sizes):
    table_page = pages[5]
    texts = [span["text"].replace(" ", "") for span in table_page["spans"]]
    if not any(f"表1：{TABLE_TITLE}" == line for line in texts):
        raise ValueError("Period and table title failed the original OCR anchor.")
    if not any(AREA_NOTE in line for line in texts):
        raise ValueError("Geographic scope note failed the original OCR anchor.")
    if not any("50所分館及14所" in line and "未併入統計" in line for line in texts):
        raise ValueError("County accessory-count note failed the original OCR anchor.")
    if not any(TABULAR_CREDIT in line for line in texts):
        raise ValueError("Source credit failed the original OCR anchor.")
    cells = []
    for row, label, role, literal, y_bounds, context_pattern in ROWS:
        raw = detect_count(table_page["spans"], literal, y_bounds)
        literal_prose = prose_evidence(pages[4]["spans"], context_pattern)
        bbox = pdf_box(raw, sizes[5])
        cell_id = f"{SOURCE_ID}/t1/p5/public-r{row}/c2"
        accessory = role.startswith("additional_")
        notes = [AREA_NOTE, "原表公共圖書館區塊含私立，國家圖書館另列。"]
        if row in (2, 6):
            notes.append(FACILITY_NOTE)
        cell = {
            "cell_id": f"{cell_id}/{role}",
            "physical_cell_id": cell_id,
            "source_document_id": SOURCE_ID,
            "source_url": f"{SOURCE_URL}#page=5",
            "source_sha256": EXPECTED_SHA256,
            "source_version_id": document["source_version_id"],
            "source_pdf_page": 5,
            "source_printed_page": "30",
            "source_table": "1",
            "source_table_title": TABLE_TITLE,
            "source_row": str(row),
            "source_column": "2",
            "source_cell_bbox": bbox,
            "source_locator": (f"PDF page 5; printed page 30; table 1; public-library subgroup data row {row}; "
                               f"physical column 2; quantity {role}; top-left PDF units bbox "
                               + ",".join(map(str, bbox))),
            "row_label_raw": label,
            "entity_raw": "臺閩地區",
            "entity_kind": "published_taiwan_kinmen_matsu_library_type_or_subtotal",
            "column_label_raw": "數量",
            "geography_vintage": "1985年原表臺閩地區，依備註含臺灣及金馬",
            "national_libraries_scope": "national_library_separately_listed_excluded_from_public_library_subgroup",
            "population_scope": f"臺灣及金馬地區公共圖書館／{label}"
                                + (f"／{METRICS[role]}，未併入原館數" if accessory else ""),
            "data_year": 1985,
            "data_month": 12,
            "period_raw": "74年12月",
            "period_status": "original_table_explicit_ROC_year_month_exact_day_unreported",
            "temporal_kind": "stock_reference_month_exact_day_unreported",
            "metric_id": f"t1-public-r{row}-{role}",
            "metric_raw": METRICS[role],
            "value": int(literal),
            "value_raw": literal,
            "value_status": "reported",
            "unit": "所",
            "unit_raw": "所" if accessory else None,
            "unit_status": "explicit_table_note_counting_unit" if accessory else "pinned_facing_page_prose_counting_unit",
            "aggregation_role": role if not accessory else role + "_excluded_from_published_subtotal",
            "source_notes": notes,
            "quality_flags": ["AI_source_image_review", "OCR_and_corresponding_original_prose_agree",
                              "human_collation_not_completed"],
            "source_edition": EDITION,
            "physical_source_context": {
                "whole_cell_reading": "21**\n(50)\n[14]" if row == 2 else literal,
                "quantity_role": role,
                "parenthetical_notation": "(50)" if role == "additional_branches"
                                           else "[14]" if role == "additional_reading_rooms" else None,
                "source_row_index_scope": "selected public-library subgroup",
                "top_left_origin_pdf_page_size": list(sizes[5]),
                "source_credit": TABULAR_CREDIT,
                "do_not_add_to_printed_subtotal": accessory,
                "separately_listed_national_library_row_outside_subgroup": True,
            },
            "independent_check": {
                "method": "AI original scan read; Apple Vision numeric at original location; separately typeset facing-page prose cross-check",
                "vision_revision": table_page["revision"],
                "vision_table_raw": raw["text"],
                "vision_prose_corroboration": literal_prose,
                "prose_pdf_page": 4,
                "prose_printed_page": "29",
                "prose_url": f"{SOURCE_URL}#page=4",
                "same_publication": True,
                "matched": True,
                "human_review": False,
            },
        }
        cells.append(cell)
    return cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--retrieved-at", default="2026-11-27T17:04:00.852866+00:00")
    parser.add_argument("--source-local-path", default="raw/ncl-early-1985/yearbook-02-current-status.pdf")
    args = parser.parse_args()
    sys.path.insert(0, str(args.project / "scripts"))
    from build_discovered_20261028 import adapt

    document = {
        "candidate_id": SOURCE_ID,
        "title": EDITION + "：圖書館事業現況調查分析",
        "edition_raw": EDITION,
        "official_url": SOURCE_URL,
        "catalogue_url": CATALOGUE_URL,
        "source_sha256": EXPECTED_SHA256,
        "source_bytes": EXPECTED_BYTES,
        "source_version_id": SOURCE_ID + "@sha256:" + EXPECTED_SHA256,
        "source_local_path": args.source_local_path,
        "retrieved_at": args.retrieved_at,
        "publication_date": "1988-12-01",
        "rights_status": "published_statistical_facts_only_full_document_license_unconfirmed",
        "recheck_interval_days": 365,
    }
    pages, sizes = vision_pages(pinned_source(args.source))
    cells = build_cells(document, pages, sizes)
    columns = json.loads((args.project / "scripts/discovered_20261028_canonical_columns.json").read_text())["columns"]
    canonical = []
    for cell in cells:
        row = adapt(cell, document)
        role = cell["physical_source_context"]["quantity_role"]
        row["facility"] = cell["row_label_raw"].replace("鎭", "鎮")
        row["source_row_hierarchy_raw"] = "公共圖書館／" + cell["row_label_raw"]
        row["source_original_table_row"] = str(int(cell["source_row"]) + 1)
        row["source_original_physical_column"] = "2"
        row["periodicity_raw"] = None
        row["publication_year"] = 1988
        row["publication_date"] = document["publication_date"]
        row["publication_date_basis"] = "official_yearbook_catalogue"
        row["value_parse_rule"] = "separate_literal_quantities_at_one_physical_cell; source annotation retains the complete physical reading"
        row["source_cell_annotation"] = cell["physical_source_context"]["whole_cell_reading"]
        row["source_parenthetical_raw"] = cell["physical_source_context"]["parenthetical_notation"]
        row["source_footnotes_raw"] = AREA_NOTE + ("\n" + FACILITY_NOTE if cell["source_row"] in {"2", "6"} else "")
        row["source_footnotes_status"] = "read_from_pinned_original_table"
        row["source_data_year_raw"] = "74年12月"
        row["unit_basis"] = "table_note_**" if role.startswith("additional_") else "facing_page_PDF4_print29_explicit_unit_所"
        if set(row) - set(columns):
            raise ValueError("Source adapter produced unrecognized canonical fields.")
        canonical.append({field: row.get(field) for field in columns})
        cell["observation_id"] = row["observation_id"]
        cell["source_id"] = row["source_id"]
    count_roles = {c["row_label_raw"]: c["value"] for c in cells if c["aggregation_role"] == "type_count"}
    subtotal = next(c["value"] for c in cells if c["aggregation_role"] == "published_subtotal")
    assert len(canonical) == len({r["observation_id"] for r in canonical}) == 8
    assert len({c["physical_cell_id"] for c in cells}) == 6
    assert sum(count_roles.values()) == subtotal == 336
    output = {
        "source_scope": "PDF5／印頁30表1公共圖書館區塊，6個實體格、8個原報數量",
        "original_bibliographic_credit": TABULAR_CREDIT,
        "whole_source_pdf_pages": 21,
        "unique_physical_cells": 6,
        "canonical_observations": 8,
        "numeric_table_and_facing_page_ocr_checked": 8,
        "exclusions": [
            "國家圖書館及其他館型的獨立列在指定公共館子群以外。",
            "沒有由主館、另設分館與閱覽室重算含附屬設施的新總數。",
        ],
        "printed_subtotal": subtotal,
        "category_sum_only_for_acceptance": sum(count_roles.values()),
        "human_double_collation_completed": False,
        "cells": cells,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "source_cells.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "documents.json").write_text(json.dumps({"documents": [document]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "observations.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in canonical), encoding="utf-8")
    print(json.dumps({k: v for k, v in output.items() if k != "cells"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
