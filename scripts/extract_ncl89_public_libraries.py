#!/usr/bin/env python3
"""Translate fully image-read NCL edition 89 statistical grids to source observations."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unicodedata

import pypdfium2

SOURCE_ID = "ncl-ed89-public-libraries"
SOURCE_SHA = "cd394d40fb89fb9e0624513adecc95b6642669ae21898a01168410f2a7cb040c"
SOURCE_URL = "https://www.ncl.edu.tw/files/file_pool/1/0Q083565690358881489/d5d8b3d1-b854-413a-935d-b14a780c3f2b.pdf"
CATALOGUE_URL = "https://www.ncl.edu.tw/librarianship-yearbook/0Q083565657469156923"
EDITION = "中華民國八十九年圖書館年鑑"
RETRIEVED_AT = "2026-11-27T17:04:04.361853+00:00"
SOURCE_PATH = "raw/ncl-early-89/yearbook-89-public-library.pdf"
FOOTNOTE_34 = "彰化市、南投市、臺東市三地設有文化中心，縣轄市不建館，以「未開放」計；另南投縣省政府圖書館列入省市級以上圖書館計。統計資料截至民國88年10月。"
FOOTNOTE_35 = "現住人口數為該縣市列入統計之鄉鎮市區圖書館86年底該鄉鎮市區人口數之合計。"
ANOMALY = "1,3118,247"
KNOWN_31_AGGREGATES = {"臺閩地區", "臺灣地區", "臺灣省", "金馬地區"}
TITLES = {
    "3-1": "臺閩地區公共圖書館地區分布概況",
    "3-4": "臺灣地區公共圖書館統計表",
    "3-5": "臺灣省各縣市鄉鎮市立圖書館館藏資料統計表",
    "3-6": "臺閩地區公共圖書館服務與資源使用統計表",
}
FIELDS_34 = (
    ("已開放部分", "省市級以上圖書館", "總館"),
    ("已開放部分", "省市級以上圖書館", "分館"),
    ("已開放部分", "縣市文化中心", "圖書館"),
    ("已開放部分", "縣市文化中心", "分館"),
    ("已開放部分", "鄉鎮市區圖書館", "本館"),
    ("已開放部分", "鄉鎮市區圖書館", "第二館分館"),
    ("已開放部分", "合計"),
    ("未開放部分", "省轄市區分館"),
    ("未開放部分", "鄉鎮市圖書館"),
    ("未開放部分", "合計"),
)
FIELDS_35 = (
    ("現住人口數", None, "人", "source_heading_counts_residents_in_people"),
    ("平均館藏資料／圖書資料（冊）", "冊", "冊", "literal_column_unit"),
    ("平均館藏資料／非書資料（件）", "件", "件", "literal_column_unit"),
    ("每人擁有館藏冊件數", "冊件", None, "combined_volume_item_original_heading_no_unified_unit"),
    ("排序", None, None, "ordinal_original_heading_no_unit"),
)
FIELDS_36 = (
    ("登計讀者人數（人）", "人", "registered_readers_survey_reference"),
    ("平均每月進館人數（人）", "人", "average_monthly_visitors_survey_reference"),
    ("年度開館日數（日）", "日", "annual_open_days_exact_period_unconfirmed"),
    ("圖書資料開架率（%）", "%", "shelf_percentage_survey_reference"),
    ("年度借閱人數（人）", "人", "annual_reported_people_exact_period_unconfirmed"),
    ("年度借閱冊數（冊）", "冊", "annual_reported_volumes_exact_period_unconfirmed"),
)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path):
    return json.loads(path.read_text())


def quantity(raw: str):
    if raw == "":
        return None, "source_blank"
    if raw == ANOMALY:
        return None, "source_marker"
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?", raw):
        raise ValueError(f"Unreviewed numeric literal: {raw!r}")
    return str(Decimal(raw.replace(",", ""))), "reported"


def semantics(table, row, column, role, labels):
    name = labels[0]
    result = {
        "entity_raw": name,
        "row_label_raw": name,
        "unit_raw": None,
        "data_month": None,
        "national_libraries_scope": "institutional_inclusion_preserved_as_original_not_independently_certified",
    }
    if table == "3-1":
        is_branch = role == "branches"
        result.update(
            entity_kind="historic_geographic_aggregate" if name in KNOWN_31_AGGREGATES else "historic_county_city_original",
            geography_vintage="民國86年臺閩地區原刊行政區，未轉為現行縣市",
            column_label_raw="數量",
            metric_raw="括弧所列分館數" if is_branch else "公共圖書館數量",
            unit="所",
            unit_raw="所",
            unit_status="literal_table_unit",
            data_year=1997,
            period_raw="依據國家圖書館於民國86年所進行的統計資料",
            period_status="adjacent_original_prose_roc_86_survey_exact_date_unconfirmed",
            temporal_kind="survey_reference_year_snapshot_exact_date_unconfirmed",
            population_scope="民國86年國家圖書館調查；臺閩地區公私立公共圖書館；地區及地區合計重疊",
            national_libraries_scope="original_public_library_survey_national_role_not_inferred",
            aggregation_role="source_separate_parenthesized_branch_quantity" if is_branch else
                ("published_overlapping_geographic_total" if name in KNOWN_31_AGGREGATES else "historic_geographic_quantity"),
            source_notes=["原表附註表示括弧內為分館數。沒有括弧的原格保留該狀態。",
                          "臺閩地區、臺灣地區、臺灣省和金馬地區與表內個別行政區重疊。"],
            source_heading_context=["地區", "數量"],
            source_original_region_block=(
                "原刊獨立列之臺北市／高雄市" if name in {"臺北市", "高雄市"} else
                "原刊金馬地區區塊" if name in {"金馬地區", "金門縣", "連江縣"} else
                "原刊區域合計" if name in KNOWN_31_AGGREGATES else "原刊臺灣省區塊"
            ),
            source_reported_disagreement=(
                "臺灣省原報398（51）。原刊縮排下21個省內細列主量相加408，已印分館數相加53。"
                if name == "臺灣省" else None
            ),
        )
    elif table == "3-4":
        heading = FIELDS_34[column - 1]
        result.update(
            entity_raw="臺灣地區" if name == "總計" else name,
            entity_kind="historic_geographic_aggregate" if name == "總計" else "historic_county_city_original",
            geography_vintage="民國88年10月臺灣地區原刊23縣市；金門、連江未列",
            column_label_raw="／".join(heading),
            metric_raw="／".join(heading) + "圖書館數量" if heading[-1] == "合計" else "／".join(heading),
            unit=None,
            unit_status="original_independent_unit_unprinted_counted_entity_clear",
            data_year=1999,
            data_month=10,
            period_raw="統計資料截至民國88年10月",
            period_status="literal_original_roc_88_month_10_cutoff_exact_day_unconfirmed",
            temporal_kind="snapshot_as_of_source_reported_month_exact_day_unconfirmed",
            population_scope="臺灣地區公共圖書館，依原表已開放／未開放與館類分列",
            national_libraries_scope="original_provincial_or_above_category_see_source_footnote",
            aggregation_role="published_region_total" if name=="總計" else
                ("published_open_status_subtotal" if heading[-1]=="合計" else "historic_geographic_quantity"),
            source_notes=[FOOTNOTE_34],
            source_reported_disagreement=(
                "原報已開放合計36，同列可見的已印分項加總38。原值照錄。"
                if name=="屏東縣" and column==7 else None
            ),
            source_heading_context=list(heading),
        )
    elif table == "3-5":
        metric, unit_raw, unit, unit_status = FIELDS_35[column - 1]
        year = 1997 if column == 1 else 1999 if column in (2, 3) else None
        period = (
            "原表註：86年底該鄉鎮市區人口數之合計" if column == 1 else
            "正文：88年國中圖的調查統計" if column in (2, 3) else
            "館藏參照88年調查；原表人口分母為86年底；比率／排序沒有單一年份"
        )
        result.update(
            entity_kind="survey_aggregate_for_listed_counties" if name == "合計／平均" else "historic_county_city_original",
            geography_vintage="臺灣省原刊列入調查的17縣市；列入調查館所服務地域",
            column_label_raw=metric,
            metric_raw=metric,
            unit=unit,
            unit_raw=unit_raw,
            unit_status=unit_status,
            data_year=year,
            collection_survey_year_context=1999,
            population_reference_year_context=1997,
            period_raw=period,
            period_status="literal_original_roc_86_year_end_resident_population" if column == 1 else
                ("adjacent_original_prose_roc_88_collection_survey_exact_date_unconfirmed" if year else
                 "catalogued_collection_survey_and_resident_denominator_reference_different_years"),
            temporal_kind="stock_year_end" if column==1 else
                ("survey_reference_year_collection_average_exact_period_unconfirmed" if year else
                 ("mixed_years_per_capita_ratio" if column==4 else "rank_based_on_mixed_years_per_capita_ratio")),
            population_scope="臺灣省17縣市列入調查之鄉鎮市立圖書館；人口依原表註列入之鄉鎮市區合計",
            national_libraries_scope="survey_township_city_public_libraries",
            aggregation_role=(
                "published_population_total" if column == 1 else
                "published_survey_average_or_ratio" if column in (2, 3, 4) else "unprinted_total_rank"
            ) if name == "合計／平均" else (
                "survey_geographic_population_denominator" if column == 1 else
                "published_geographic_collection_average" if column in (2, 3) else
                "published_per_capita_ratio" if column==4 else "published_ordinal_rank"
            ),
            source_notes=[FOOTNOTE_35,
                          "原表最後一列為「合計／平均」，人口欄作合計，館藏與每人欄維持刊載之平均或比率。"],
        )
    else:
        metric, unit, temporal = FIELDS_36[column - 1]
        role_label = labels[1]
        result.update(
            entity_raw="臺閩地區",
            row_label_raw=role_label,
            source_parent_row_label_raw=name,
            entity_kind="historic_library_type_aggregate",
            geography_vintage="原刊臺閩地區，縣市立與鄉鎮市立依原表館型分組",
            column_label_raw=metric,
            metric_raw="／".join((name, role_label, metric)),
            unit=unit,
            unit_raw=unit,
            unit_status="literal_column_unit",
            data_year=1997,
            period_raw="依據民國86年國家圖書館所做的調查",
            period_status="adjacent_original_prose_roc_86_survey_exact_statistical_dates_unconfirmed",
            temporal_kind=temporal,
            population_scope=f"臺閩地區{name}圖書館原調查；原表{role_label}列",
            national_libraries_scope="county_city_and_township_city_public_groups_separately",
            aggregation_role="published_type_total" if role_label=="總數" else "published_type_average",
            source_notes=["正文指向國家圖書館民國86年所做調查。各指標精確起訖與原始館數分母未明。",
                          "原刊總數、平均數及單位保留，未按總數／平均數反算。"],
        )
    return result


def visions(path):
    if not path:
        return None
    return {Path(row["file"]).stem:row for row in map(json.loads, path.read_text().splitlines())}


def ocr_readback(ocr, expected):
    if ocr is None:
        return {"status": "no_local_ocr_run_in_this_rebuild", "observed": []}
    text = [entry["text"] for entry in ocr["observations"]]
    visible = " ".join(unicodedata.normalize("NFKC", literal) for literal in text)
    seen = re.findall(r"\d[\d,]*(?:\.\d+)?", visible)
    digits = lambda token: token.replace(",", "")
    if expected == [""]:
        status = "vision_blank_agrees" if not text else "vision_blank_noise_reviewed_from_image"
    else:
        same = list(map(digits, expected)) == list(map(digits, seen))
        status = "vision_digit_agreement_image_checked" if same else "vision_difference_image_value_preserved"
    return {"status": status, "observed": text, "vision_revision": ocr["request_revision"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    home = Path(__file__).parent
    parser.add_argument("--grid", type=Path, default=home / "ncl89_grids.json")
    parser.add_argument("--coordinates", type=Path, default=home / "ncl89_coordinates.json")
    parser.add_argument("--ocr", type=Path)
    parser.add_argument("--retrieved-at", default=RETRIEVED_AT)
    opt = parser.parse_args()
    data, geometry = read_json(opt.grid), read_json(opt.coordinates)
    ocr = visions(opt.ocr)
    pdf_bytes = opt.source.read_bytes()
    if len(pdf_bytes) != 15337299 or sha256(pdf_bytes).hexdigest() != SOURCE_SHA:
        raise ValueError("Original PDF changed")
    pdf = pypdfium2.PdfDocument(pdf_bytes)
    if len(pdf) != 28:
        raise ValueError("Pinned PDF page count changed")
    sys.path.insert(0, str(opt.project / "scripts"))
    from build_discovered_20261028 import adapt
    document = {
        "candidate_id": SOURCE_ID,
        "source_sha256": SOURCE_SHA,
        "title": EDITION + "：公共圖書館章",
        "edition_raw": EDITION,
        "source_local_path": SOURCE_PATH,
        "official_url": SOURCE_URL,
        "catalogue_url": CATALOGUE_URL,
        "publication_date": "2000-12-01",
        "retrieved_at": opt.retrieved_at,
        "source_version_id": f"{SOURCE_ID}@sha256:{SOURCE_SHA}",
        "source_bytes": len(pdf_bytes),
        "rights_status": "public_statistical_facts_only_full_original_redistribution_not_confirmed",
    }
    schema = read_json(opt.project/"scripts/discovered_20261028_canonical_columns.json")["columns"]
    raw_cells, rows = [], []
    ocr_counts = Counter()
    table_counts = {}
    for table, spec in geometry.items():
        pdf_page = spec["pdf_page"]
        printed = spec["printed_page"]
        if pdf[pdf_page - 1].get_textpage().get_text_range().strip():
            raise ValueError("Expected an image-only original statistical table")
        page_width, page_height = pdf[pdf_page-1].get_size()
        px_width, px_height = spec["raster"]
        x_lines = spec["x"]
        original_count = len(raw_cells)
        canonical_count = len(rows)
        for i, row in enumerate(data[table]):
            idx = spec.get("printed_row_indices", list(range(1, len(data[table])+1)))[i]
            y_top, y_bottom = spec["ys"][i] if "ys" in spec else spec["y"][i:i+2]
            if table == "3-1":
                label, main, branch = row
                labels = [label]
                cells = [(main, branch)]
            elif table == "3-6":
                labels, cells = row[:2], row[2:]
            else:
                labels, cells = row[:1], row[1:]
            if len(cells) != len(x_lines) - 1:
                raise ValueError("Unexpected grid width")
            for col, literal in enumerate(cells, 1):
                px_box = [x_lines[col-1], y_top, x_lines[col], y_bottom]
                pdf_box = [round(value * scale, 3) for value, scale in
                           zip(px_box, (page_width/px_width, page_height/px_height)*2)]
                physical_id = f"{SOURCE_ID}/t{table}/p{pdf_page}/r{idx}/c{col}"
                stem = f"{table}-r{idx:02d}-c{col:02d}"
                if table == "3-1":
                    readings = [("main", literal[0])]
                    if literal[1] is not None:
                        readings.append(("branches", literal[1]))
                else:
                    readings = [("primary", literal)]
                image_probe = ocr_readback(ocr[stem] if ocr is not None else None, [r[1] for r in readings])
                ocr_counts[image_probe["status"]] += 1
                raw_cells.append({
                    "physical_cell_id": physical_id, "table": table, "source_pdf_page": pdf_page,
                    "source_printed_page": printed, "source_row": idx, "source_column": col,
                    "row_labels_raw": labels, "source_cell_bbox": pdf_box,
                    "bbox_basis": "top-left coordinates on pinned PDF page",
                    "raw_readings": {k: v for k, v in readings}, "optical_check": image_probe,
                    "original_pdf_crop_visual_reviewed_if_optical_disagreement": image_probe["status"] in (
                        "vision_difference_image_value_preserved", "vision_blank_noise_reviewed_from_image"),
                })
                for role, raw in readings:
                    cell_id = physical_id + ("/" + role if table=="3-1" else "")
                    locator = (f"PDF page {pdf_page}; printed page {printed}; table {table}; "
                               f"source row {idx}; numeric column {col}; quantity {role}; bbox "
                               + ",".join(map(str, pdf_box)))
                    val, val_status = quantity(raw)
                    meta = semantics(table, idx, col, role, labels)
                    flags = ["AI_image_grid_review_no_human_double_collation"]
                    if val_status == "source_blank":
                        flags.append("original_cell_blank_meaning_not_inferred")
                    if raw == ANOMALY:
                        flags.append("source_printed_digit_grouping_anomaly_no_scalar_interpretation")
                        meta["source_notes"].append("該格實印 1,3118,247，數字分組異常，原字串保存，正規數值留空。")
                    if table=="3-6" and raw=="14,294,751.83":
                        flags.append("fractional_reported_reader_total_preserved")
                    if table=="3-1":
                        meta["parenthetical_branch_count_printed"] = literal[1] is not None
                        meta["primary_and_separate_branch_amounts"] = list(literal)
                    cell = {
                        **meta,
                        "cell_id": cell_id, "physical_cell_id": physical_id,
                        "source_document_id": SOURCE_ID, "source_url": SOURCE_URL+f"#page={pdf_page}",
                        "source_edition": EDITION, "source_edition_roc": 89,
                        "source_sha256": SOURCE_SHA, "source_version_id": document["source_version_id"],
                        "source_pdf_page": pdf_page, "source_printed_page": str(printed),
                        "source_table": table, "source_table_title": TITLES[table],
                        "source_row": idx, "source_column": col, "source_cell_bbox": pdf_box,
                        "source_locator": locator, "row_index_basis": "visible table data grid, excluding column header; table 3-6 indexes include labelled group rows",
                        "value": val, "value_raw": raw, "value_status": val_status,
                        "metric_id": f"{table}-c{col}-{role}"+(f"-{labels[0]}-{labels[1]}" if table=="3-6" else ""),
                        "quality_flags": flags,
                        "independent_check": {
                            "method": "Fixed visual transcription from original PDF grid; local Vision OCR checked separately in source evidence",
                            "human_review": False, "human_double_collation_completed": False,
                        },
                    }
                    result = adapt(cell, document)
                    result["publication_year"] = 2000
                    if table=="3-6" and col==2:
                        result["periodicity_raw"] = "平均每月"
                    if table=="3-4":
                        result["periodicity_raw"] = "截至月份"
                    unknown = set(result) - set(schema)
                    if unknown:
                        raise ValueError(f"Unexpected canonical fields: {unknown}")
                    rows.append({field: result.get(field) for field in schema})
        table_counts[table] = {"physical_cells":len(raw_cells)-original_count,
                               "observations":len(rows)-canonical_count}
    assert table_counts == {
        "3-1":{"physical_cells":29,"observations":48},
        "3-4":{"physical_cells":240,"observations":240},
        "3-5":{"physical_cells":90,"observations":90},
        "3-6":{"physical_cells":24,"observations":24},
    }
    assert len(rows) == len({r["observation_id"] for r in rows}) == 402
    assert len(raw_cells) == len({r["physical_cell_id"] for r in raw_cells}) == 383
    anomalous = [r for r in rows if r["value_status"] == "source_marker"]
    assert len(anomalous)==1 and anomalous[0]["raw_value"]==ANOMALY
    issues = {
        table: [cell["physical_cell_id"] for cell in raw_cells
                if cell["table"]==table and cell["optical_check"]["status"] in (
                    "vision_difference_image_value_preserved", "vision_blank_noise_reviewed_from_image")]
        for table in TITLES
    }
    opt.out.mkdir(parents=True, exist_ok=True)
    write_json(opt.out/"documents.json", {"documents": [document]})
    write_json(opt.out/"source_cells.json", {
        "source_id": SOURCE_ID, "source_sha256": SOURCE_SHA,
        "cell_grid_counts": table_counts,
        "value_status_counts": dict(Counter(row["value_status"] for row in rows)),
        "historical_inventory": {
            "3-1": "29 geographic/aggregate rows; additional observations are printed parenthetical branch counts.",
            "3-4": "24 source geographic/aggregate rows × 10 columns including original blanks.",
            "3-5": "18 source rows × 5 columns. The population references 1997 year-end, holdings are 1999 survey context, ratios/ranks have mixed period.",
            "3-6": "4 numeric data rows × 6 columns. Printed group-label rows 1 and 4 are structural and excluded.",
        },
        "column_and_row_geometry": geometry,
        "ocr_status_counts": dict(ocr_counts), "ocr_disagreements_or_blank_noise": issues,
        "source_arithmetic_observations": {
            "3-1": "臺灣省原報398（51）。原刊縮排下21列主量相加408，已印分館數相加53。原報保留。",
            "3-4": "已開放縣市文化中心圖書館、鄉鎮市區第二館分館及已開放合計的列印分項上下合計有差。屏東縣原報合計36，該列已印分項加總38。差異悉數保留。",
            "3-5": "臺中縣現住人口數原印 1,3118,247，缺少可信的數字分組，原值保留，數值空白。",
            "3-6": "鄉鎮市立登計讀者人數總數實印14,294,751.83，原刊小數位保留。",
        },
        "verification_method": "Whole-grid AI reading from printed pages and separate Apple Vision cell OCR. All OCR mismatches were reviewed from the pinned PDF crop.",
        "human_sample_reading_completed": False, "human_double_collation_completed": False, "cells": raw_cells,
    })
    with (opt.out/"observations.jsonl").open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"))+"\n")
    print(json.dumps({
        "observations":len(rows),"physical_cells":len(raw_cells),
        "table_counts":table_counts,"value_status_counts":Counter(r["value_status"] for r in rows),
        "ocr_status_counts":ocr_counts,
        "reported_year_counts":Counter(str(r["data_year"]) for r in rows),
        "same_source_scope_comparison_only":True,
        "human_double_collation_completed":False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
