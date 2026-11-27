#!/usr/bin/env python3
"""Rebuild selected November source cohorts using hash-pinned official originals."""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

import record_io
from build_discovered_20261028 import adapt

ROOT = Path(__file__).resolve().parents[1]
NCL_EARLY = ROOT / "raw/ncl-early-statistics"
MOE = ROOT / "raw/moe-library-ods"
READING = ROOT / "raw/ncl-reading-2025"
COLUMNS = json.loads((ROOT / "scripts/discovered_20261028_canonical_columns.json").read_text())["columns"]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def command(script, *args):
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)], check=True)


def load_records(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def source_cards(rows, method):
    groups = defaultdict(list)
    for row in rows:
        groups[row["source_id"], row["source_sha256"], row["source_table"]].append(row)
    cards = []
    for (source_id, sha, table), members in sorted(groups.items()):
        first = members[0]
        urls = sorted({r["source_url"] for r in members})
        years = sorted({r["data_year"] for r in members if r["data_year"] is not None})
        pages = sorted({r["source_pdf_page"] for r in members if r["source_pdf_page"] is not None})
        identifier = hashlib.sha256(f"{source_id}|{sha}|{table}".encode()).hexdigest()[:24]
        cards.append({
            "evidence_id": "p2-nov2026-" + identifier,
            "layer": "canonical",
            "source_id": source_id,
            "source_sha256": sha,
            "source_url": urls[0],
            "source_urls": urls,
            "source_locator": {"table": table, "pdf_pages": pages, "raw_locator_examples": [r["source_locator"] for r in members[:3]]},
            "source_table": table,
            "source_table_title": first["source_table_title"],
            "source_fields": sorted({r["source_field"] for r in members if r["source_field"]}),
            "indicators": sorted({r["indicator"] for r in members}),
            "series_ids": sorted({r["series_id"] for r in members}),
            "data_years_present": years,
            "unresolved_period_records": sum(r["data_year"] is None for r in members),
            "reviewed_original": True,
            "review_method": method,
            "semantic_facts": {
                "retained_units": sorted({r["unit"] for r in members if r["unit"]}),
                "population_scopes": sorted({r["population_scope"] for r in members}),
                "cross_source_equivalence_confirmed": False,
            },
            "supported_comparison_scope": {
                "status": "source_series_only",
                "data_years": years,
                "positive_scope": "Retain original rows. No cross-source equivalence or new cross-year chart certified.",
            },
            "field_policies": [],
            "observation_ids": sorted(r["observation_id"] for r in members),
            "human_review_completed": False,
            "human_double_collation_completed": False,
        })
    return {"schema_version": "1.0.0", "source_cards": cards}


def reading_observations(records, document):
    for row in records:
        year = row["data_year"]
        metric = row["indicator"]
        point_in_time = metric == "cards-cumulative"
        cell = {
            "cell_id": f'ncl-reading-2025-report/t1/r{row["source_row"]}/c{row["source_column"]}',
            "source_document_id": document["candidate_id"],
            "source_url": document["official_url"] + "#page=12",
            "source_sha256": document["source_sha256"],
            "source_version_id": document["candidate_id"] + "@sha256:" + document["source_sha256"],
            "source_pdf_page": 12,
            "source_printed_page": "13",
            "source_locator": row["source_locator"],
            "source_cell_bbox": row["source_bbox"],
            "source_table": "1",
            "source_table_title": row["source_table_title"],
            "source_row": row["source_row"],
            "source_column": row["source_column"],
            "row_label_raw": row["source_metric_label"],
            "column_label_raw": f"{year-1911}年",
            "entity_raw": "全國",
            "entity_kind": "national_total",
            "geography_vintage": "原刊當年22縣市與另列國立公共館",
            "data_year": year,
            "period_raw": f"{year-1911}年",
            "period_status": "report_methodology_2025_confirmed" if year == 2025 else "original_year_exact_dates_unconfirmed",
            "metric_id": metric,
            "metric_raw": row["source_metric_label"],
            "value": row["value"],
            "value_raw": row["raw_value"],
            "value_status": "reported",
            "unit": row["unit"],
            "unit_raw": "萬",
            "unit_status": "original_scale_and_indicator_counting_unit",
            "temporal_kind": ("stock_year_end" if point_in_time else "flow_calendar_year") if year == 2025 else "annual_source_reference_exact_period_unconfirmed",
            "population_scope": row["population_scope"],
            "national_libraries_scope": "two_national_public_library_systems_included",
            "aggregation_role": row["aggregation_role"],
            "source_notes": ["原表以萬為量級，照刊載精度保存。電子書分類及總計各有原口徑。"],
            "source_edition": document["title"],
            "source_edition_roc": 114,
            "independent_check": {"method": "All 39 pinned PDF annual cells matched the official web table during source review.", "human_review": False},
        }
        mapped = adapt(cell, document)
        mapped["source_family"] = "國家圖書館閱讀報告統計事實"
        mapped["publication_year"] = 2026
        mapped["publication_date"] = "2026-04-23"
        mapped["publication_date_basis"] = "official_catalogue"
        mapped["unit_basis"] = row["unit_basis"]
        if year == 2025 and not point_in_time:
            mapped["period_start"], mapped["period_end"] = "2025-01-01", "2025-12-31"
        yield mapped


def build(batch):
    with TemporaryDirectory(prefix="library-nov-review-") as directory:
        output = Path(directory)
        if batch == "ncl_early_statistics":
            raw = NCL_EARLY
            command("extract_ncl_early_statistics.py", "--project", ROOT,
                    "--source92", raw / "yearbook-92-statistics.pdf",
                    "--source93", raw / "yearbook-93-statistics.pdf", "--out", output)
            rows = load_records(output / "observations.jsonl")
            command("extract_ncl90_statistics.py", "--project", ROOT,
                    "--source", raw / "yearbook-90-statistics.pdf", "--out", output / "edition90")
            rows.extend(load_records(output / "edition90/observations.jsonl"))
            documents = json.loads((output / "documents.json").read_text())
            documents["documents"].extend(json.loads((output / "edition90/documents.json").read_text())["documents"])
            write_json(output / "documents.json", documents)
            batch_files = {"documents.json": "documents.json", "source_cells.json": "source-cells.json",
                           "edition90/source_cells.json": "edition90-source-cells.json"}
            method = "Pinned PDFs. 92/93 text engines and AI image check; 90 AI image reading and Apple Vision OCR."
        elif batch == "moe_library_ods":
            raw = MOE
            command("extract_moe_library_ods.py", "--project-root", ROOT,
                    "--source", raw / "library.ods", "--output-dir", output,
                    "--retrieved-at", "2026-11-27T15:37:53.705149+00:00")
            rows = load_records(output / "moe_canonical.jsonl")
            batch_files = {"moe_documents.json": "documents.json", "moe_summary.json": "extraction-metadata.json"}
            method = "Pinned original ODS. OpenDocument XML expanded physical cell positions and displayed/cache value checks."
        elif batch == "ncl_reading_2025":
            raw = READING
            command("extract_ncl_reading_2025.py", "--canonical-pdf", "--pdf", raw / "report.pdf",
                    "--out", output / "report.json", "--jsonl", output / "reading.jsonl")
            report = json.loads((output / "report.json").read_text())
            document = {
                "candidate_id": "ncl-reading-2025-report",
                "title": "114年臺灣閱讀風貌年度報告",
                "official_url": "https://www.ncl.edu.tw/files/file_pool/1/0Q120145388038649336/df66cab6-10d6-4502-9fbb-6a8db59a339c.pdf",
                "catalogue_url": "https://www.ncl.edu.tw/tw/books/0Q112333768515788432",
                "source_local_path": "raw/ncl-reading-2025/report.pdf",
                "source_sha256": "ad221212e57e12b5b8458455b765956b684f5bcd1808a1f8e83b33f0e8846288",
                "retrieved_at": "2026-11-27T15:39:53+00:00",
                "publication_date": "2026-04-23",
            }
            rows = list(reading_observations(load_records(output / "reading.jsonl"), document))
            write_json(output / "documents.json", {"documents": [document]})
            write_json(output / "extraction-metadata.json", {
                **{k: v for k, v in report.items() if k != "records"},
                "official_web_table_crosscheck": {
                    "url": "https://reading.ncl.edu.tw/web/front/page.do?pageId=74",
                    "sha256": "ab38731a11db53c0d329e4ff472004f8e7e40009503cd69b041c9c065336d1ef",
                    "matching_annual_cells": 39,
                },
            })
            batch_files = {"documents.json": "documents.json", "extraction-metadata.json": "extraction-metadata.json"}
            method = "Pinned PDF Table 1 extraction, all 39 annual cells checked against the separate official web table."
        else:
            raise ValueError(f"Unsupported batch: {batch}")

        if not rows or len(rows) != len({r["observation_id"] for r in rows}):
            raise ValueError("Empty batch or duplicate observations")
        if any(set(row) - set(COLUMNS) for row in rows):
            raise ValueError("Unexpected canonical fields")
        rows = [{column: row.get(column) for column in COLUMNS} for row in rows]
        for row in rows:
            if isinstance(row["source_cell_bbox"], (dict, list)):
                row["source_cell_bbox"] = json.dumps(
                    row["source_cell_bbox"], ensure_ascii=False, separators=(",", ":")
                )
        for source, name in batch_files.items():
            (raw / name).write_bytes((output / source).read_bytes())
        write_json(raw / "definition-evidence.json", source_cards(rows, method))
        record_io.write(ROOT, f"derived/{batch}_observations.jsonl", rows)
        fields = (
            "observation_id", "source_id", "data_year", "geography", "geographic_scope",
            "indicator", "value", "raw_value", "value_status", "unit", "unit_raw", "unit_status",
            "source_url", "source_sha256", "source_locator", "source_table", "source_table_title",
            "source_row", "source_column", "source_pdf_page", "source_printed_page", "source_edition_roc",
            "source_download_url", "source_local_path", "source_retrieved_at", "source_title", "publication_date",
        )
        with (ROOT / "derived" / f"{batch}_long.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    **row,
                    "source_url": row["source_page_url"],
                    "source_download_url": row["source_url"].split("#", 1)[0],
                    "source_local_path": row["source_snapshot_path"],
                    "source_retrieved_at": row["retrieved_at"],
                    "source_title": row["source_edition"] or row["source_table_title"],
                })
    print(json.dumps({"batch": batch, "records": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, choices=("ncl_early_statistics", "moe_library_ods", "ncl_reading_2025"))
    build(parser.parse_args().batch)
