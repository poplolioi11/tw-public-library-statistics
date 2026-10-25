#!/usr/bin/env python3
"""Offline extraction of all five aggregate tables in NCL's 101 reading report.

No county observations, book-title rankings, named readers, awards or authored
prose are imported. Full PDF stays private. Coordinates were checked in PDFium.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pdfplumber

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "raw/ncl-2012"
PDF = RAW / "ncl-reading-101.pdf"
EXPECTED_SHA = "f25798e2fe96dcde51a0ed818edb395f986c2b427f8b39349d4edbe62dabacc4"
CLASSES = ["總類", "哲學", "宗教", "自然科學", "應用科學", "社會科學", "中國史地", "世界史地", "語言文學", "藝術", "小計"]
AGE_LABELS = ["學齡前／0-6歲", "學童／7-12歲", "青少年／13-18歲", "青年／19-30歲", "青壯年／31-50歲", "壯年／51-60歲", "銀髮族／61歲以上", "小計", "百分比"]
AGE_KEYS = ["age0_6", "age7_12", "age13_18", "age19_30", "age31_50", "age51_60", "age61plus", "all_ages", "book_class_share"]
SEX_LABELS = ["女性", "男性", "合計"]
SEX_KEYS = ["female", "male", "all_sexes"]


def raw_in_bbox(page, bbox):
    x0, top, x1, bottom = bbox
    chars = [c for c in page.chars if x0 <= (c["x0"] + c["x1"]) / 2 < x1 and top <= (c["top"] + c["bottom"]) / 2 < bottom]
    return "".join(c["text"] for c in sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"]))).strip()


def normalize(raw):
    if not raw:
        return None, "blank"
    text = re.sub(r"[\s,%]", "", raw)
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        raise ValueError("Unreviewed source token: " + repr(raw))
    return str(Decimal(text)), "numeric"


def main():
    digest = hashlib.sha256(PDF.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError("Original reading report changed; review again before extracting")
    source = json.loads((RAW / "ncl-reading-101.metadata.json").read_text())
    rows, tables, checks = [], [], []

    def add(table, title, page, row, column, path, raw, bbox, metric, label, year=2012, unit="冊", unit_raw="借閱冊數", temporal="flow_calendar_year", book_class=None, age=None, sex=None, role="component", row_label=None, span=None):
        value, status = normalize(raw)
        flags = ["independent_reading_report_version_not_yearbook_series", "county_breakdown_not_published_in_these_tables"]
        if status == "blank":
            flags.append("source_blank")
        if role in ["published_total", "published_subtotal"]:
            flags.append("published_total_overlaps_components")
        records = dict(
            data_year=year, source_data_year_raw="100年至101年（合併格）" if temporal == "derived_growth_rate" else f"{year - 1911}年", source_edition=None, source_edition_roc=None,
            source_family="國家圖書館閱讀報告統計事實", source_edition_title="臺灣101年閱讀習慣調查結果記者會暨表揚典禮活動手冊",
            entity_raw="全國", entity_contextual_name="全國", entity_kind="national_total", geography_vintage="全國；未出版縣市分列",
            population_scope="本報告彙整全國22縣市公共圖書館與國立臺灣圖書館、國立公共資訊圖書館資料；各表缺漏與對齊方式未另說明",
            national_libraries_scope="two_national_public_libraries_named_in_report; not_yearbook_scope_certified",
            book_class_raw=book_class, age_group_raw=age, sex_raw=sex,
            metric_id=metric, metric_raw=label, value_raw=raw, value=value, value_status=status,
            unit=unit, unit_raw=unit_raw, unit_basis="依原表欄頭或同頁單位；百分比保留百分數，不轉為0至1比例",
            temporal_kind=temporal, time_reference=f"{year}年全年" if temporal == "flow_calendar_year" else "2011至2012變動率" if temporal == "derived_growth_rate" else "2012年累積數，精確截點未另明示" if temporal.startswith("stock_") else "2012年度表內分布百分比",
            institutional_level="national_aggregate_reading_report", aggregation_role=role,
            scope_note="閱讀報告獨立版本；非年鑑、非NLPI縣市包；無22縣市分列，不用全國值推估各縣市",
            quality_flags=flags, original_fields={"row_label_raw": row_label, "column_path": path, "cell_raw": raw},
            source_id=f"ncl-reading-2012-t{table}", source_url=source["source_page_url"], source_download_url=source["source_download_url"],
            source_sha256=digest, source_local_path="raw/ncl-2012/ncl-reading-101.pdf", source_agency="國家圖書館",
            source_title=source["title"], source_retrieved_at=source["source_retrieved_at"],
            source_pdf_page=page, source_printed_page=page - 6, source_table=f"unlabelled-{table}", source_table_title=title,
            source_row=row, source_row_label_raw=row_label, source_column=column, source_column_span=span,
            source_column_path=path, source_cell_bbox=list(bbox), source_cell_bbox_kind="source_table_cell" if page == 16 else "reviewed_positioned_glyph_region_for_single_source_cell",
            source_locator=f"PDF page {page}; printed page {page - 6}; unnumbered table {table}; data row {row}; physical column {column}" + (f" spanning {span}" if span else ""),
            source_note="報告前言明示102年發布101年度統計；表一、二另列100年比較。本報告與年鑑口徑未確認一致，原值保留。",
            source_footnotes_raw=[], source_original_access_date_raw=None, source_original_access_date=None,
            extraction_status="all_five_aggregate_source_tables_PDFium_reviewed_positioned_glyphs", license_status="not_confirmed",
            publication_date="2013-02-25", publication_date_basis="report_release_event_on_handbook_PDF3; official_gallery_date_2013-02-27",
            source_gallery_publication_date="2013-02-27", collection_year=2013, collection_year_basis="PDF8前言明示今（102）年進行101年度統計",
        )
        # source_edition is a title, never a library-yearbook ROC volume number.
        records["source_edition"] = records["source_edition_title"]
        rows.append(records)
        return records

    with pdfplumber.open(PDF) as doc:
        if len(doc.pages) != 71:
            raise ValueError("Unexpected page count")
        page = doc.pages[13]
        # Growth rows are genuinely merged across both year columns: one source
        # value each, with a physical span; no imaginary blank cell is generated.
        for table, title, count_key, count_unit, counts_y, growth_y in [
            (1, "全國借閱圖書冊數", "physical_loans", "冊", (393, 417), (420, 443)),
            (2, "全國借閱圖書人次", "borrower_visits", "人次", (604, 628), (630, 654)),
        ]:
            count_row_label = "冊數" if table == 1 else "人次"
            for col, year, x0, x1 in [(2, 2011, 235, 347), (3, 2012, 347, 463)]:
                bbox = (x0, *counts_y[:1], x1, counts_y[1])
                add(table, title, 14, 1, col, f"年度／{year - 1911}年／{count_row_label}", raw_in_bbox(page, bbox), bbox, f"reading_t{table}_{count_key}", title, year, count_unit, count_unit, row_label=count_row_label)
            bbox = (235, growth_y[0], 463, growth_y[1])
            add(table, title, 14, 2, 2, "100年至101年／成長率（合併欄）", raw_in_bbox(page, bbox), bbox, f"reading_t{table}_{count_key}_growth_2011_2012", title + "／成長率", unit="%", unit_raw="成長率／%", temporal="derived_growth_rate", role="derived_ratio", row_label="成長率", span=[2, 3])
            tables.append(dict(table=table, title=title, pdf_page=14, printed_page=8, source_cells=3, years=[2011, 2012], merged_growth_cell=True))

        page = doc.pages[14]
        service_cols = [
            ("entry_visits", "進館／總人次", "人次", "進館總人次", "flow_calendar_year"),
            ("website_queries", "圖書館網站／查詢次數", "次", "查詢次數", "flow_calendar_year"),
            ("new_cards", "新增／辦證數", "張", None, "flow_calendar_year"),
            ("cumulative_cards", "累積／辦證數", "張", None, "stock_reference_date_not_explicit_in_table"),
        ]
        bounds = [173.8, 256.9, 340, 423.1, 505.7]
        for i, (key, label, unit, unit_raw, temporal) in enumerate(service_cols):
            bbox = (bounds[i], 279, bounds[i + 1], 314.5)
            add(3, "臺灣民眾101年利用圖書館服務統計", 15, 1, i + 2, label, raw_in_bbox(page, bbox), bbox, "reading_t3_" + key, label.replace("／", ""), unit=unit, unit_raw=unit_raw, temporal=temporal, row_label="使用統計")
        tables.append(dict(table=3, title="臺灣民眾101年利用圖書館服務統計", pdf_page=15, printed_page=9, source_cells=4, years=[2012]))

        page = doc.pages[15]
        found = page.find_tables()
        if len(found) != 2:
            raise ValueError("Expected exactly two demographic tables")
        for table, found_table, title, dimension_labels, dimension_keys in [
            (4, found[0], "各年齡層讀者借閱圖書類別分析表", AGE_LABELS, AGE_KEYS),
            (5, found[1], "不同性別讀者借閱圖書類別分析", SEX_LABELS, SEX_KEYS),
        ]:
            extracted = found_table.extract()
            data = extracted[2:]
            expected_width = len(dimension_labels) + 1
            if len(data) != 12 or any(len(r) != expected_width for r in data):
                raise ValueError("Unexpected demographic grid shape")
            if [re.sub(r"\s", "", r[0] or "") for r in data[:11]] != CLASSES:
                raise ValueError("Book classification order differs from reviewed PDF")
            if table == 4 and data[-1][0] != "百分比":
                raise ValueError("Age table share-row label changed")
            if table == 5 and data[-1][0] != "":
                raise ValueError("Sex table unlabeled share row changed")
            for ri, extracted_row in enumerate(data):
                row_label = extracted_row[0]
                class_label = CLASSES[ri] if ri < 10 else None
                class_key = f"class{ri}" if ri < 10 else "all_classes" if ri == 10 else "age_share" if table == 4 else "sex_share"
                for ci, (dimension, dim_key) in enumerate(zip(dimension_labels, dimension_keys)):
                    bbox = found_table.rows[ri + 2].cells[ci + 1]
                    raw = raw_in_bbox(page, bbox)
                    is_share = ri == 11 or (table == 4 and ci == 8)
                    role = "derived_ratio" if is_share else "published_subtotal" if ri == 10 or ci == len(dimension_labels) - (2 if table == 4 else 1) else "component"
                    add(table, title, 16, ri + 1, ci + 2, "借閱冊數／" + dimension, raw, bbox,
                        f"reading_t{table}_{class_key}_{dim_key}" + ("_share" if is_share else "_loans"),
                        "借閱圖書" + ("百分比" if is_share else "冊數") + "／" + (row_label or "百分比（原列名空白）") + "／" + dimension,
                        unit="%" if is_share else "冊", unit_raw="%" if is_share else "借閱冊數", temporal="derived_ratio" if is_share else "flow_calendar_year",
                        book_class=class_label, age=dimension if table == 4 and ci < 7 else None, sex=dimension if table == 5 and ci < 2 else None, role=role, row_label=row_label)
            tables.append(dict(table=table, title=title, pdf_page=16, printed_page=10, data_rows=12, data_columns=len(dimension_labels), source_cells=12 * len(dimension_labels), years=[2012]))

    # Check source arithmetic without altering any published value.
    for table, count_columns in [(4, 7), (5, 2)]:
        grid = {(r["source_row"], r["source_column"]): r for r in rows if r["source_id"] == f"ncl-reading-2012-t{table}"}
        for ri in range(1, 12):
            parts = [Decimal(grid[(ri, ci)]["value"]) for ci in range(2, count_columns + 2)]
            total = grid[(ri, count_columns + 2)]
            actual = sum(parts)
            checks.append(dict(check="published_row_total_vs_components", source_id=total["source_id"], source_row=ri, source_column=total["source_column"], calculated=str(actual), published=total["value"], passed=actual == Decimal(total["value"])))
        for ci in range(2, count_columns + 3):
            total = grid[(11, ci)]
            actual = sum(Decimal(grid[(ri, ci)]["value"]) for ri in range(1, 11))
            checks.append(dict(check="published_column_total_vs_classes", source_id=total["source_id"], source_row=11, source_column=ci, calculated=str(actual), published=total["value"], passed=actual == Decimal(total["value"])))
    for row in rows:
        if any(not c["passed"] and c["source_id"] == row["source_id"] and c["source_row"] == row["source_row"] and c["source_column"] == row["source_column"] for c in checks):
            row["quality_flags"].append("official_total_differs_from_component_sum; preserved_unchanged")
    if len(rows) != 154 or len({(r["source_id"], r["metric_id"], r["data_year"]) for r in rows}) != 154:
        raise ValueError("Unexpected or non-unique full source grid")
    if Counter(r["value_status"] for r in rows) != {"numeric": 153, "blank": 1}:
        raise ValueError("Reviewed blank/numeric inventory changed")
    out = BASE / "derived"
    with (out / "ncl_reading_2012_long.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    (out / "ncl_reading_2012_long.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    metadata = dict(checked_at="2026-10-25", completed=True, completion_scope="all_data_cells_of_five_national_aggregate_tables_PDF14_to16", source_family="國家圖書館閱讀報告統計事實", source_document=source, source_sha256=digest, source_cells=len(rows), numeric_cells=153, blank_cells=1,
        years=[2011, 2012], county_observations=0, county_coverage="does_not_fill_2012_22_county_core_gap", tables=tables, source_arithmetic_checks=checks, source_discrepancies=[c for c in checks if not c["passed"]],
        independent_review="pending_root_review", publication_date="2013-02-25", publication_date_basis="release_event_PDF3", source_gallery_publication_date="2013-02-27", source_edition_roc=None,
        limitations=["年齡表與性別表的同類別合計不同，未提供對齊說明；各自保留，不自行調和。", "百分比、合計、小計及分項重疊，不可將全部格相加。", "原報告8頁成長率跨兩年度欄合併，只計一格，不製造不存在的空白。", "累積辦證精確截點未另明示，不用記者會日期代替。", "本批未取得22縣市原始營運量表。"],
        intentional_exclusion=["書名與出版社榜單", "借閱楷模及其他個人資料", "得獎與評鑑", "工程個案", "表格之外的整篇著作文字"], license_status="not_confirmed", snapshot_distribution="original_PDF_private; statistical_facts_only")
    (RAW / "reading-extraction-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(cells=len(rows), statuses=dict(Counter(r["value_status"] for r in rows)), tables=len(tables), checks=len(checks), discrepancies=metadata["source_discrepancies"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
