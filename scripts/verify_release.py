#!/usr/bin/env python3
"""Independent, offline source verification. Does not import acquisition/extraction code.

JSON observations are checked exhaustively against raw snapshots. Historical PDF
cells below are fixed expectations independently read from rendered pages on
2026-10-25; they are samples, not a full transcription review.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import html
import json
import math
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = [f"Bacol{n:05d}" for n in range(282, 292)]
PDF_SHA = {
    2008: "780f72e99bec13702fc706f0e86b7c90cc19b370dc0048e1ef92a261766f4c28",
    2009: "a0b93a4c5f78e6f57e39a5605c3ff78c6e046f513b274df6652a363b67cfb52b",
    2010: "e2117dfa3bd89e8b4727542c360d836046915d798c04517a6c0a2ac3e5cb4ba8",
}
# Values read from PDFium page images, not generated from extracted CSV/JSON.
# year, entity_raw, metric_id, expected numeric string, PDF page, table, data row
PDF_SAMPLES = [
    (2009, "臺北市", "volunteers", "1394", 4, 3, 1),
    (2009, "臺北市", "student_staff", "33", 4, 3, 1),
    (2009, "國立中央圖書館", "volunteers", "409", 4, 3, 26),
    (2009, "國立中央圖書館", "student_staff", "0", 4, 3, 26),
    (2009, "國立中央圖書館", "all_staff", "495", 4, 3, 26),
    (2009, "總計", "volunteers", "8996", 4, 3, 29),
    (2009, "總計", "student_staff", "197", 4, 3, 29),
    (2009, "總計", "all_staff", "12958", 4, 3, 29),
    (2010, "臺北市", "student_staff", "36", 4, 4, 1),
    (2010, "臺北市", "volunteers", "1412", 4, 4, 1),
    (2010, "國立中央圖書館臺灣分館", "student_staff", "0", 4, 4, 26),
    (2010, "國立中央圖書館臺灣分館", "volunteers", "367", 4, 4, 26),
    (2010, "國立中央圖書館臺灣分館", "all_staff", "444", 4, 4, 26),
    (2010, "總計", "student_staff", "324", 4, 4, 29),
    (2010, "總計", "volunteers", "8941", 4, 4, 29),
    (2010, "總計", "all_staff", "12998", 4, 4, 29),
    (2009, "國立中央圖書館", "holdings_mixed", "1528469", 3, 2, 26),
    (2009, "國立中央圖書館", "acquisition_spending", "39870245", 3, 2, 26),
    (2009, "國立中央圖書館", "physical_loans", "1235390", 3, 2, 26),
    (2008, "國立中央圖書館臺灣分館", "holdings_mixed", "1471274", 3, 4, 26),
    (2008, "國立中央圖書館臺灣分館", "acquisition_spending", "16231567", 3, 4, 26),
    (2008, "國立中央圖書館臺灣分館", "physical_loans", "946172", 3, 4, 26),
    (2008, "臺北市", "population", "2622923", 3, 4, 1),
    (2008, "臺北市", "holdings_mixed", "5437454", 3, 4, 1),
    (2008, "臺北市", "physical_loans", "9218877", 3, 4, 1),
    (2010, "國立中央圖書館臺灣分館", "holdings_mixed", "1577652", 3, 3, 26),
    (2010, "國立中央圖書館臺灣分館", "acquisition_spending", "23734466", 3, 3, 26),
    (2010, "國立中央圖書館臺灣分館", "physical_loans", "1208376", 3, 3, 26),
]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def jsonfile(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def typed_equal(a, b):
    return type(a) is type(b) and a == b


def escape_pointer(token):
    return str(token).replace("~", "~0").replace("/", "~1")


def resolve_pointer(document, pointer):
    if not pointer.startswith("/"):
        raise ValueError("JSON Pointer must start with /")
    value = document
    for token in pointer.split("/")[1:]:
        if re.search(r"~(?![01])", token):
            raise ValueError("Invalid JSON Pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("Invalid array index")
            value = value[int(token)]
        else:
            value = value[token]
    return value


def independent_parse(raw):
    """Independent decimal-based oracle; no call into library_pipeline."""
    if raw is None:
        return None, "source_null"
    if type(raw) is bool:
        return None, "unparsed"
    if type(raw) in (int, float):
        if isinstance(raw, float) and not math.isfinite(raw):
            raise ValueError("Non-finite number")
        return raw, "reported"
    text = str(raw).strip()
    if text == "":
        return None, "source_blank"
    if text in {"-", "—", "–", "…", "...", "N/A", "NA"}:
        return None, "source_marker"
    text = text.translate(str.maketrans({",": "", "，": ""}))
    if re.fullmatch(r"-?[0-9]+", text):
        return int(Decimal(text)), "reported"
    if re.fullmatch(r"-?[0-9]+\.[0-9]+", text):
        return str(Decimal(text)), "reported_decimal"
    return None, "unparsed"


def local_value(raw, unit):
    value, status = independent_parse(raw)
    if status != "unparsed":
        return value, status, unit or None
    text = str(raw).replace(",", "").strip()
    if re.fullmatch(r"[0-9]+冊", text):
        return int(text[:-1]), "reported", unit or "冊"
    magnitude = re.fullmatch(r"([0-9]+)萬\s*([0-9]{0,4})", text)
    if magnitude:
        return int(magnitude[1]) * 10000 + int(magnitude[2] or 0), "reported", unit or None
    return value, status, unit or None


def reference_year(period):
    text = str(period).strip()
    if re.fullmatch(r"[0-9]{5}", text):
        if not 1 <= int(text[3:]) <= 12:
            raise ValueError("Invalid ROC year-month")
        return int(text[:3]) + 1911
    if re.fullmatch(r"[0-9]{2,3}", text):
        return int(text) + 1911
    if re.fullmatch(r"(?:19|20)[0-9]{2}", text):
        return int(text)
    if re.match(r"(?:19|20)[0-9]{2}-", text):
        return dt.datetime.fromisoformat(text).year
    raise ValueError("Unverified period syntax: " + text)


class Verification:
    def __init__(self, root):
        self.root = root
        self.failures = []
        self.checks = 0
        self.result = {}

    def check(self, condition, code, detail):
        self.checks += 1
        if not condition:
            self.failures.append({"code": code, "detail": detail})

    def core(self):
        manifest = jsonfile(self.root / "data/source_manifest.json")["sources"]
        rows = [json.loads(line) for line in
                (self.root / "data/observations.jsonl").read_text().splitlines() if line]
        required_charts = {f"public-chart-{year}-{topic}"
                           for year in range(2011, 2026) for topic in TOPICS}
        charts = {sid for sid, src in manifest.items()
                  if src["kind"] == "public_national_chart"}
        self.check(charts == required_charts, "chart_grid", {
            "missing": sorted(required_charts - charts), "extra": sorted(charts - required_charts)})
        sources = {sid: src for sid, src in manifest.items()
                   if src["kind"] in {"public_national_chart", "licensed_api"}}
        self.check({sid for sid, src in sources.items() if src["kind"] == "licensed_api"}
                   == {"ogdl-api-2023"}, "licensed_source_range", list(sources))
        expected, documents, placeholders = {}, {}, []
        api_dimensions = {}
        for sid, src in sources.items():
            raw = (self.root / src["snapshot_path"]).read_bytes()
            self.check(digest(raw) == src["sha256"], "raw_sha", sid)
            document = json.loads(raw.decode("utf-8-sig"))
            documents[sid] = document
            self.check(isinstance(document, list) and bool(document), "source_array", sid)
            if src["kind"] == "licensed_api":
                self.check(len(document) == 26, "api_row_count", len(document))
                for i, row in enumerate(document):
                    fields = [key for key in row if key != "縣市別"]
                    self.check(len(fields) == 86, "api_field_count", {"row": i, "count": len(fields)})
                    self.check(str(row.get("縣市別", "")).startswith("2023-"), "api_year", row.get("縣市別"))
                    for field in fields:
                        pointer = f"/{i}/{escape_pointer(field)}"
                        expected[(sid, pointer)] = row[field]
                        api_dimensions[(sid, pointer)] = (row["縣市別"].split("-", 1)[1], field)
            else:
                year, topic = src["year"], src["topic"]
                request = src["body"]
                self.check(sid == f"public-chart-{year}-{topic}", "chart_identity", sid)
                self.check(request.get("Years") == str(year) and request.get("Topic") == topic
                           and request.get("SelectCity") == ["-1"]
                           and request.get("SelectLevel") == [], "chart_request", sid)
                for i, row in enumerate(document):
                    for field, value in row.items():
                        if not field.startswith("ItemAmount"):
                            continue
                        pointer = f"/{i}/{escape_pointer(field)}"
                        suffix = field[len("ItemAmount"):]
                        label = row.get("ItemName") if not suffix else row.get("legendName" + suffix)
                        if label is None or label == "":
                            placeholders.append({"source_id": sid, "source_locator": pointer,
                                                 "raw_value": value, "field": field})
                        else:
                            expected[(sid, pointer)] = value
        seen, ids, families, statuses = collections.Counter(), [], collections.defaultdict(set), collections.Counter()
        family_rows = collections.Counter()
        for row in rows:
            sid, pointer = row["source_id"], row["source_locator"]
            key = (sid, pointer)
            seen[key] += 1
            ids.append(row["observation_id"])
            self.check(sid in sources, "unknown_source", sid)
            if sid not in sources:
                continue
            source = sources[sid]
            family_rows[source["kind"]] += 1
            families[row["series_id"]].add(source["kind"])
            self.check(key in expected, "unexpected_observation", key)
            for field, source_field in [("source_snapshot_path", "snapshot_path"),
                                        ("source_sha256", "sha256"), ("source_url", "url"),
                                        ("source_method", "method"), ("retrieved_at", "retrieved_at")]:
                self.check(row.get(field) == source.get(source_field), "source_lineage", {"key": key, "field": field})
            try:
                rawvalue = resolve_pointer(documents[sid], pointer)
                self.check(typed_equal(rawvalue, row["raw_value"]), "raw_value", key)
                value, status = independent_parse(rawvalue)
                self.check(typed_equal(value, row["value"]), "parsed_value", key)
                self.check(status == row["value_status"], "value_status", key)
                statuses[status] += 1
                if status == "source_null":
                    self.check(row["value"] is None and row.get("zero_interpretation") is None,
                               "null_not_zero", key)
                if value == 0:
                    self.check(bool(row.get("zero_interpretation")), "zero_uncertainty", key)
            except (ValueError, KeyError, IndexError, TypeError) as error:
                self.check(False, "pointer_or_parse", {"key": key, "error": str(error)})
            self.check(row["data_year"] == source["year"], "data_year", key)
            self.check(row.get("comparability") == "not_certified_across_years_or_source_families",
                       "cross_family_comparability", key)
            if source["kind"] == "public_national_chart":
                self.check(row["geography"] == "全國" and row["geographic_scope"] == "national_total",
                           "chart_geography", key)
                self.check(row["series_id"].startswith("chart-" + source["topic"] + "-"), "series_family", key)
                raw_row = documents[sid][int(pointer.split("/")[1])]
                amount_key = pointer.split("/")[-1]
                suffix = amount_key[len("ItemAmount"):]
                label = raw_row.get("ItemName") if not suffix else raw_row.get("legendName" + suffix)
                self.check(isinstance(label, str) and row["source_field"] == label
                           and row["indicator"].endswith("｜" + label),
                           "chart_label", key)
                self.check(isinstance(label, str) and row["series_id"] == "chart-" + source["topic"] + "-" + digest(label.encode())[:10],
                           "chart_series_identity", key)
                if source["topic"] in {"Bacol00282", "Bacol00283", "Bacol00287", "Bacol00288"}:
                    self.check(raw_row["ItemName"] == "全國", "raw_national_scope", key)
                if source["topic"] == "Bacol00286":
                    self.check(row["unit"] == "間", "area_count_unit", key)
                if source["topic"] == "Bacol00288":
                    self.check(row["unit"] is None, "heterogeneous_unit", key)
                if source["topic"] == "Bacol00291":
                    unit = "台" if label == "巡迴車" else "個" if label in {"社群網站", "館外服務站"} else "所"
                    self.check(row["unit"] == unit, "institution_count_unit", key)
                self.check(row["license_status"] == "publicly_published_statistical_facts", "chart_rights", key)
                try:
                    self.check(json.loads(row["source_request"]) == source["body"], "request_lineage", key)
                except (ValueError, TypeError):
                    self.check(False, "request_lineage", key)
            else:
                geo, field = api_dimensions.get(key, (None, None))
                scope = ("national_total" if geo == "全國" else
                         "county_excluding_national_alternative" if geo and "(不含國立館)" in geo else
                         "county_default_includes_national_where_applicable")
                self.check(row["geography"] == geo and row["geographic_scope"] == scope
                           and row["source_field"] == field, "api_dimensions", key)
                self.check(row["series_id"].startswith("api-") and row["license_status"]
                           == "OGDL-1.0_explicit_link_2023", "api_family_rights", key)
        actual = set(seen)
        self.check(actual == set(expected), "source_cell_completeness", {
            "missing": sorted(set(expected) - actual), "extra": sorted(actual - set(expected))})
        self.check(all(count == 1 for count in seen.values()), "duplicate_source_cells",
                   [key for key, count in seen.items() if count != 1])
        self.check(len(ids) == len(set(ids)), "duplicate_observation_ids", len(ids) - len(set(ids)))
        self.check(all(len(kinds) == 1 for kinds in families.values()), "mixed_source_series",
                   [series for series, kinds in families.items() if len(kinds) != 1])
        self.check(len(rows) == 3091, "core_record_count", len(rows))
        self.check(family_rows == {"licensed_api": 2236, "public_national_chart": 855}, "family_counts", dict(family_rows))
        self.result["core"] = {
            "status": "pass" if not self.failures else "fail", "records_checked": len(rows),
            "sources_checked": len(sources), "chart_grid": {"years": list(range(2011, 2026)),
            "topics": TOPICS, "expected_sources": 150, "present_sources": len(charts)},
            "api_2023": {"raw_rows": 26, "value_fields_per_row": 86, "expected_values": 2236},
            "family_counts": dict(family_rows), "value_status_counts": dict(statuses),
            "excluded_no_legend_cells": len(placeholders),
            "excluded_third_placeholder_cells": sum(p["field"] == "ItemAmount3" for p in placeholders),
            "all_raw_and_parsed_values_checked": True,
            "cross_family_rule": "Separate series; no cross-family totals or sums are calculated.",
            "inputs": {"observations_sha256": digest((self.root / "data/observations.jsonl").read_bytes()),
                       "manifest_sha256": digest((self.root / "data/source_manifest.json").read_bytes())},
        }

    def historical(self):
        before = len(self.failures)
        documents = jsonfile(self.root / "raw/ncl-historical/documents.json")
        documents = {doc["id"]: doc for doc in documents}
        with (self.root / "derived/ncl_historical_long.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        by_key = collections.defaultdict(list)
        for source_id, document in documents.items():
            raw = (self.root / document["local_path"]).read_bytes()
            year = document["data_year"]
            self.check(digest(raw) == document["sha256"] == PDF_SHA[year], "historical_pdf_sha", source_id)
        for row in rows:
            key = (int(row["data_year"]), row["entity_raw"], row["metric_id"])
            by_key[key].append(row)
            document = documents[row["source_id"]]
            self.check(row["source_sha256"] == document["sha256"], "historical_lineage", key)
            self.check(int(row["data_year"]) == document["data_year"]
                       and row["source_url"] == document["url"]
                       and row["source_download_url"] == document["download_url"],
                       "historical_document_identity", key)
            self.check(Decimal(row["value_raw"].replace(",", "")) == Decimal(row["value"]),
                       "historical_number_parse", key)
            self.check(row["license_status"] == "not_confirmed", "historical_rights_boundary", key)
            national_names = {"國立中央圖書館", "國立中央圖書館臺灣分館", "國立臺中圖書館", "臺灣省政府圖書館"}
            if row["entity_raw"] in national_names:
                self.check(row["entity_kind"] == "public_library_institution"
                           and row["national_libraries_scope"] == "separate_institution",
                           "historical_institution_scope", key)
            elif row["entity_raw"] == "總計":
                self.check(row["entity_kind"] == "national_total"
                           and row["national_libraries_scope"] == "included_in_national_total",
                           "historical_total_scope", key)
            else:
                self.check(row["entity_kind"] == "county"
                           and row["national_libraries_scope"] == "excluded_from_county_metrics",
                           "historical_county_scope", key)
        self.check(collections.Counter(int(row["data_year"]) for row in rows)
                   == {2008: 191, 2009: 539, 2010: 539}, "historical_row_counts", len(rows))
        self.check(all(len(value) == 1 for value in by_key.values()), "historical_duplicate_cells", "year/entity/metric")
        sample_results = []
        for year, entity, metric, expected, page, table, ordinal in PDF_SAMPLES:
            matches = by_key[(year, entity, metric)]
            result = {"data_year": year, "entity_raw": entity, "metric_id": metric,
                      "expected_value_from_page_image": expected, "pdf_page": page,
                      "table": table, "data_row": ordinal, "observed_values": [r["value"] for r in matches]}
            valid = len(matches) == 1 and Decimal(matches[0]["value"]) == Decimal(expected)
            if valid:
                locator = matches[0]["source_locator"]
                valid = all(part in locator for part in [f"PDF page {page};", f"table {table};", f"data row {ordinal}"])
            self.check(valid, "historical_visual_sample", result)
            result["status"] = "pass" if valid else "fail"
            sample_results.append(result)
        missing_cells = []
        for year in (2008, 2009, 2010):
            entities = [("國立中央圖書館" if year == 2009 else "國立中央圖書館臺灣分館"),
                        "國立臺中圖書館", "臺灣省政府圖書館"]
            for entity in entities:
                for metric in ("population", "holdings_per_capita", "acquisition_spending_per_capita", "loans_per_capita"):
                    key = (year, entity, metric)
                    self.check(not by_key[key], "pdf_blank_not_zero", key)
                    missing_cells.append({"data_year": year, "entity": entity, "metric": metric,
                                          "expected": "absent_blank_not_zero"})
        for metric in ("holdings_mixed", "volunteers", "student_staff"):
            for row in by_key[(2009, "國立中央圖書館", metric)]:
                self.check(row["entity_contextual_name"] == "國立中央圖書館臺灣分館"
                           and row["entity_kind"] == "public_library_institution"
                           and row["national_libraries_scope"] == "separate_institution",
                           "national_library_raw_context", metric)
        self.result["historical_ncl"] = {
            "status": "pass" if len(self.failures) == before else "fail",
            "lineage_and_numeric_parse_rows_checked": len(rows),
            "pdf_documents_hash_checked": len(documents),
            "visual_review_date": "2026-10-25", "visual_review_method": "Independent page-image reading using PDFium; fixed expectations in verify_release.py, no extraction program imported.",
            "visual_pages_checked": ["2008 PDF page 3 (printed 79)", "2009 PDF pages 3–4 (printed 75–76)", "2010 PDF pages 3–4 (printed 35–36)"],
            "visual_sample_cells": len(sample_results), "samples": sample_results,
            "national_institution_blank_cells_checked": len(missing_cells),
            "staff_header_order": {"2009": "志工 precedes 工讀生", "2010": "工讀生 precedes 志工"},
            "national_library_scope_note": "Footnotes exclude the three separately listed national/provincial libraries from relevant county figures; national total overlaps all constituent rows.",
            "not_full_pdf_transcription_review": True,
            "inputs": {"csv_sha256": digest((self.root / "derived/ncl_historical_long.csv").read_bytes()),
                       "pdf_sha256": {str(year): value for year, value in PDF_SHA.items()}},
        }

    def components(self):
        """All adapter rows vs derived; all local derived cells vs original JSON."""
        before = len(self.failures)
        rows = [json.loads(line) for line in
                (self.root / "data/component_records.jsonl").read_text().splitlines() if line]
        with (self.root / "derived/local_historical_long.csv").open(encoding="utf-8-sig", newline="") as stream:
            local = list(csv.DictReader(stream))
        metadata = {}
        for path in (self.root / "raw/official-local").glob("catalog-*/resource-*.metadata.json"):
            meta = jsonfile(path)
            if meta.get("source_sha256") and meta.get("raw_path"):
                metadata[(meta["source_download_url"], meta["source_sha256"])] = meta
        raw_documents, raw_expected, blank_raw_rows = {}, set(), 0
        dimensions = {"統計年月", "館藏地", "機關代碼", "縣市別代碼", "郵遞區號", "館別", "年度", "新竹市代碼", "更新日期"}
        for key in {key for key, meta in metadata.items() if meta.get("status") == "downloaded"}:
            meta = metadata[key]
            raw = (self.root / meta["raw_path"]).read_bytes()
            self.check(digest(raw) == meta["source_sha256"], "local_raw_sha", meta["raw_path"])
            self.check(meta["format"] == "json", "local_supported_format", meta["raw_path"])
            document = json.loads(raw.decode("utf-8-sig"))
            raw_documents[key] = document
            catalogue = jsonfile(self.root / "raw/official-local" / ("catalog-" + meta["dataset_id"]) / "catalog-record.json")
            page = (self.root / catalogue["catalog_path"]).read_bytes()
            self.check(digest(page) == catalogue["catalog_sha256"], "local_catalogue_sha", meta["dataset_id"])
            text = page.decode("utf-8-sig")
            datasets = []
            for block in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', text, re.S):
                data = json.loads(block)
                datasets.extend(data if isinstance(data, list) else [data])
            dataset = next(d for d in datasets if d.get("@type") == "Dataset")
            self.check(dataset.get("license") == "https://data.gov.tw/license"
                       and "政府資料開放授權條款" in html.unescape(text), "local_actual_licence_evidence", meta["dataset_id"])
            self.check(key[0] in {d.get("contentUrl") for d in dataset.get("distribution", [])},
                       "local_resource_catalogue_link", key[0])
            for index, raw_row in enumerate(document):
                if "數值" in raw_row:
                    if any(str(raw_row.get(k, "")).strip() for k in ("項目", "欄位名稱", "數值", "資料時間日期")):
                        raw_expected.add((key, index, "數值"))
                    else:
                        blank_raw_rows += 1
                else:
                    raw_expected.update((key, index, field) for field in raw_row if field not in dimensions)
        seen_cells = collections.Counter()
        by_record = {row["record_id"]: row for row in local}
        canonical_local = {row["source_record_id"]: row for row in rows if row.get("source_family") == "地方政府開放歷史表"}
        dropped = 0
        conflicts = collections.defaultdict(set)
        retained_conflicts = collections.defaultdict(set)
        dedup_fields = ("county", "period_effective", "periodicity_raw", "facility_raw", "geography_code_raw",
                        "district_code_raw", "metric_group_raw", "metric_raw", "unit_raw", "value_raw")
        for source in local:
            key = (source["source_download_url"], source["source_sha256"])
            index_match = re.fullmatch(r"JSON array\[([0-9]+)\]", source["source_locator"])
            self.check(bool(index_match), "local_locator", source["record_id"])
            if not index_match:
                continue
            index = int(index_match[1])
            original = raw_documents[key][index]
            self.check(json.loads(source["original_fields"]) == original, "local_original_fields", source["record_id"]) if "original_fields" in source else None
            field = "數值" if "數值" in original else source["metric_raw"]
            seen_cells[(key, index, field)] += 1
            self.check(field in original and str(original[field]) == source["value_raw"], "local_raw_cell", source["record_id"])
            period = str(original.get("資料時間日期") or original.get("統計年月") or original.get("年度") or "")
            self.check(source["period_raw"] == period, "local_raw_period", source["record_id"])
            facility = original.get("館藏地") or original.get("館別") or ""
            self.check(source["facility_raw"] == facility, "local_raw_facility", source["record_id"])
            if source["period_effective_basis"] == "observation_field":
                self.check(source["period_effective"] == period, "local_effective_period", source["record_id"])
            else:
                meta = metadata[key]
                catalogue = jsonfile(self.root / "raw/official-local" / ("catalog-" + meta["dataset_id"]) / "catalog-record.json")
                text = (self.root / catalogue["catalog_path"]).read_text()
                blocks = [block for block in re.findall(r'<li class="resource-item"[^>]*>.*?</li>', text, re.S)
                          if source["source_download_url"] in html.unescape(block)]
                title = " ".join(html.unescape(re.sub("<[^>]+>", " ", " ".join(blocks))).split())
                self.check(bool(title) and source["period_effective"] in title,
                           "local_title_period_evidence", source["record_id"])
            semantics = tuple(source[k] for k in dedup_fields[:-1])
            conflicts[semantics].add(source["value_raw"])
            if source["duplicate_of"]:
                dropped += 1
                previous = by_record.get(source["duplicate_of"])
                self.check(previous is not None and not previous["duplicate_of"]
                           and all(source[k] == previous[k] for k in dedup_fields), "local_safe_dedup", source["record_id"])
                self.check(source["record_id"] not in canonical_local, "duplicate_not_exported", source["record_id"])
                continue
            retained_conflicts[semantics].add(source["value_raw"])
            target = canonical_local.get(source["record_id"])
            self.check(target is not None, "local_adapter_missing", source["record_id"])
            if not target:
                continue
            for out, src in (("raw_value", "value_raw"), ("source_url", "source_download_url"),
                             ("source_sha256", "source_sha256"), ("source_page_url", "source_url"),
                             ("period_raw", "period_raw"), ("period_effective", "period_effective"),
                             ("periodicity_raw", "periodicity_raw"), ("geography", "county")):
                self.check(target[out] == source[src], "local_adapter_field", {"record": source["record_id"], "field": out})
            self.check(target["source_snapshot_path"] == metadata[key]["raw_path"], "local_adapter_snapshot", source["record_id"])
            self.check(target["data_year"] == reference_year(source["period_effective"]), "local_reference_year", source["record_id"])
            self.check(target["period_start"] is None and target["period_end"] is None,
                       "local_not_annualized", source["record_id"])
            self.check(target["facility"] == (facility or None)
                       and target["geographic_scope"] == ("municipal_library_institution" if facility else "county_official_table"),
                       "local_institution_scope", source["record_id"])
            value, status, unit = local_value(source["value_raw"], source["unit_raw"])
            self.check(typed_equal(target["value"], value) and target["value_status"] == status
                       and target["unit"] == unit, "local_value_and_unit", source["record_id"])
            self.check(bool(target.get("value_parse_rule")), "local_parse_rule_retained", source["record_id"])
        self.check(set(seen_cells) == raw_expected and all(count == 1 for count in seen_cells.values()),
                   "local_complete_raw_cells", {"expected": len(raw_expected), "seen": len(seen_cells),
                   "missing": len(raw_expected - set(seen_cells)), "extra": len(set(seen_cells) - raw_expected)})
        self.check(conflicts == retained_conflicts, "local_conflicting_values_preserved", "all value sets per semantic key")
        self.check(len(canonical_local) == len(local) - dropped, "local_adapter_count", len(canonical_local))
        historical_targets = {(row["source_id"], row["data_year"], row["geography"], row["source_field"]): row
                              for row in rows if row["source_id"].startswith(("ncl-yearbook-", "dgbas-social-indicators-"))}
        expected_historical, source_files = set(), {}
        missing_statuses = 0
        for filename in ("ncl_historical_long.csv", "dgbas_historical_long.csv"):
            with (self.root / "derived" / filename).open(encoding="utf-8-sig", newline="") as stream:
                for source in csv.DictReader(stream):
                    key = (source["source_id"], int(source["data_year"]), source["entity_raw"], source["metric_raw"])
                    expected_historical.add(key)
                    target = historical_targets.get(key)
                    self.check(target is not None, "historical_adapter_missing", key)
                    if not target:
                        continue
                    source_files[source["source_local_path"]] = source["source_sha256"]
                    self.check(target["raw_value"] == source["value_raw"]
                               and target["source_snapshot_path"] == source["source_local_path"]
                               and target["source_sha256"] == source["source_sha256"]
                               and target["source_locator"] == source["source_locator"] + "; column " + source["source_column"],
                               "historical_adapter_lineage", key)
                    value, status = independent_parse(source["value"])
                    if source.get("value_status") == "not_available_in_source":
                        value, status = None, "not_available_in_source"
                        missing_statuses += 1
                    self.check(typed_equal(target["value"], value) and target["value_status"] == status,
                               "historical_adapter_value", key)
                    self.check(target["geographic_scope"] == source["entity_kind"]
                               and target["temporal_kind"] == source["temporal_kind"], "historical_adapter_scope", key)
                    unit = None if "混合" in source["unit"] else source["unit"]
                    self.check(target["unit"] == unit, "historical_adapter_unit", key)
                    if source["source_id"].startswith("dgbas"):
                        self.check(target["license_status"] == source["license_code"]
                                   and target["license_url"] == source["license_url"], "dgbas_adapter_licence", key)
        self.check(set(historical_targets) == expected_historical, "historical_adapter_complete", len(expected_historical))
        for path, expected in source_files.items():
            self.check(digest((self.root / path).read_bytes()) == expected, "historical_adapter_raw_sha", path)
        county_extra = sum(row["source_id"] == "dgbas-county-library-Z091101a029" for row in rows)
        self.check(len(rows) == len(canonical_local) + len(expected_historical) + county_extra, "component_total", len(rows))
        self.result["components"] = {
            "status": "pass" if len(self.failures) == before else "fail", "canonical_records_checked": len(rows),
            "local_raw_documents_checked": len(raw_documents), "local_raw_cells_and_derived_rows_checked": len(local),
            "blank_non_observation_raw_rows_excluded": blank_raw_rows,
            "local_canonical_records_checked": len(canonical_local), "exact_duplicate_rows_excluded": dropped,
            "conflicting_value_groups": sum(len(values) > 1 for values in conflicts.values()),
            "historical_adapter_records_checked": len(expected_historical),
            "explicit_missing_source_markers_retained": missing_statuses,
            "pdf_raw_files_hash_checked": len(source_files),
            "local_verification_level": "All original JSON cells and complete original objects vs derived; every nonduplicate adapter record vs derived and raw.",
            "historical_verification_level": "Every adapter record vs derived and PDF source hashes; NCL visual sample scope reported separately. DGBAS PDF content not independently transcribed in this adapter review.",
            "inputs": {"components_sha256": digest((self.root / "data/component_records.jsonl").read_bytes()),
                       "local_derived_sha256": digest((self.root / "derived/local_historical_long.csv").read_bytes())},
        }

    def county_table(self):
        before = len(self.failures)
        metadata = jsonfile(self.root / "raw/segis-history/metadata.json")
        raw = (self.root / metadata["source_raw_path"]).read_bytes()
        self.check(digest(raw) == metadata["source_sha256"], "county_table_sha", metadata["source_raw_path"])
        text = raw.decode("utf-8-sig")
        table = re.search(r"<table[^>]*id=['\"]dataTable['\"].*?</table>", text, re.S).group(0)
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
        names = {}
        cells = {}
        for row_no, body in enumerate(rows, start=1):
            for column, (tag, attributes, value) in enumerate(re.findall(r"<(td|th)([^>]*)>(.*?)</\1>", body, re.S), start=1):
                attrs = dict(re.findall(r"([a-z]+)=['\"]([^'\"]*)['\"]", attributes))
                value = html.unescape(re.sub("<[^>]+>", "", value)).strip()
                if tag == "th" and attrs.get("type") == "area":
                    names[attrs["value"]] = value
                if "fvalue" in attrs.get("class", "").split():
                    key = (int(attrs["date"]), attrs["area"])
                    self.check(key not in cells and attrs["effect"] == "Z091101a029", "county_raw_duplicate", key)
                    cells[key] = (value, row_no, column)
        expected = {(year, area) for year in range(1998, 2026) for area in names}
        self.check(len(names) == 23 and set(cells) == expected, "county_full_raw_grid", len(cells))
        self.check(names == metadata["geographies"], "county_header_mapping", names)
        with (self.root / "derived/dgbas_county_historical_long.csv").open(encoding="utf-8-sig", newline="") as stream:
            derived = list(csv.DictReader(stream))
        seen, reported, missing = set(), 0, 0
        canonical = [json.loads(line) for line in (self.root / "data/component_records.jsonl").read_text().splitlines() if line]
        canonical = [row for row in canonical if row["source_id"] == metadata["source_id"]]
        mapped = {}
        for target in canonical:
            match = re.search(r"\[area='([^']+)'\]", target["source_locator"])
            area = target.get("area_code_raw") or (match[1] if match else None)
            mapped[(target["data_year"], area)] = target
        for source in derived:
            key = (int(source["data_year"]), source["area_code_raw"])
            self.check(key not in seen and key in cells, "county_derived_duplicate", key)
            seen.add(key)
            original, row_no, column = cells[key]
            value, status = (None, "not_available_in_source") if original == "-" else (int(original.replace(",", "")), "reported")
            reported += status == "reported"
            missing += status == "not_available_in_source"
            self.check(source["value_raw"] == original and source["value_status"] == status
                       and (source["value"] == "" if value is None else int(source["value"]) == value), "county_raw_numeric_value", key)
            self.check(source["entity_raw"] == names[key[1]] and source["unit"] == "所"
                       and int(source["source_table_row"]) == row_no and int(source["source_table_column"]) == column,
                       "county_raw_cell_dimensions", key)
            self.check(source["source_sha256"] == metadata["source_sha256"]
                       and source["source_local_path"] == metadata["source_raw_path"]
                       and source["source_method"] == "POST"
                       and json.loads(source["source_request"]) == metadata["source_request"], "county_source_lineage", key)
            self.check("包含國家圖書館" in source["population_scope"]
                       and "改制後縣市別" in source["geography_vintage"]
                       and source["period_start"] == "" and source["period_end"] == "", "county_scope_preserved", key)
            self.check((key[0] <= 2005) == (status == "not_available_in_source"), "county_effective_coverage", key)
            if canonical:
                target = mapped.get(key)
                self.check(target is not None, "county_adapter_missing", key)
                if target:
                    self.check(target["geography"] == source["entity_raw"]
                               and typed_equal(target["value"], value) and target["raw_value"] == original
                               and target["value_status"] == status and target["unit"] == "所", "county_adapter_value", key)
                    self.check(target["source_sha256"] == source["source_sha256"]
                               and target["source_snapshot_path"] == source["source_local_path"]
                               and target["source_locator"] == source["source_locator"], "county_adapter_lineage", key)
        self.check(seen == expected and len(derived) == 644 and reported == 460 and missing == 184,
                   "county_derived_complete_grid", {"derived": len(derived), "reported": reported, "missing": missing})
        if canonical:
            self.check(set(mapped) == expected and len(canonical) == 644, "county_adapter_complete_grid", len(canonical))
        self.result["dgbas_county_table"] = {
            "status": "pass" if len(self.failures) == before else "fail", "raw_cells_checked": len(cells),
            "derived_cells_checked": len(derived), "canonical_records_checked": len(canonical),
            "canonical_mapping_status": ("verified" if len(self.failures) == before else "failed") if canonical else "not_yet_integrated",
            "reported_cells": reported, "explicit_missing_cells": missing,
            "selected_reference_years": [1998, 2025], "reported_reference_years": [2006, 2025],
            "geographies_including_total": len(names), "source_sha256": metadata["source_sha256"],
            "scope": "Official post-reform 22 counties plus national total; includes National Central Library, NLPI and NTL. Not merged with other count series.",
            "licence_scope_inference": metadata["license_scope_inference"],
        }

    def report(self, directory):
        report = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "status": "pass" if not self.failures else "fail", "assertions": self.checks,
                  "scope": "3091 core source cells exhaustively checked; NCL lineage/number parsing all rows, PDF page-image samples only; component coverage as individually reported.",
                  "independent_of_pipeline_and_extractors": True, "network_used": False,
                  **self.result, "failures": self.failures,
                  "limitations": ["Chart response JSON does not itself contain a validated reference year; year follows the saved official UI request.",
                                  "A returned zero is not proof of true zero or historical collection of that indicator.",
                                  "Source values matching snapshots do not prove the official source itself has no mistakes.",
                                  "PDF visual checks are targeted samples, not a full transcription review.",
                                  "No source families or overlapping national/county/institution scopes are summed.",
                                  "DGBAS PDF cell content is checked against derived extraction only, not independently transcribed here."]}
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "source-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        core, historical = self.result.get("core", {}), self.result.get("historical_ncl", {})
        lines = ["# 正式資料來源獨立回查", "", f"檢查時間：{report['checked_at']}。結果：**{report['status']}**，共 {self.checks:,} 個斷言、{len(self.failures)} 項失敗。", "",
                 "本驗收腳本不匯入主管線或 PDF 抽取程式，也不發出網路請求。", "",
                 "## 全量回查範圍", "",
                 f"核心資料 {core.get('records_checked', 0):,} 筆逐筆比對原檔 SHA-256、JSON Pointer、原始值及獨立數值解析；檢查來源網址、請求、年分、地理口徑及來源家族。",
                 "2011–2025 年 × 10 個主題的 150 份全國圖表完整列舉；2023 API 的 26 列 × 86 值欄應有 2,236 筆，與 855 筆圖表分開保留。",
                 f"沒有有效 legend 的數值欄排除 {core.get('excluded_no_legend_cells', 0)} 格，其中第三欄 placeholder {core.get('excluded_third_placeholder_cells', 0)} 格；其餘有效欄位沒有遺漏或重複。", "",
                 "## 歷史 PDF 抽查", "",
                 f"國圖歷史表 {historical.get('lineage_and_numeric_parse_rows_checked', 0):,} 筆檢查來源雜湊與數值解析；3 份 PDF 綁定固定雜湊。另獨立視讀 5 頁，使用固定期望值抽查 {len(PDF_SAMPLES)} 格，以及 36 個國立館留白格沒有變成 0。這不是全文校對。",
                 "2009 年表3是「志工→工讀生」：臺北市 1,394／33；國立中央圖書館 409／0。2010 年表4改為「工讀生→志工」：臺北市 36／1,412。原始國立中央圖書館名稱與推定對應臺灣分館名稱分欄保存。", "",
                 "| 年度 | 原始列名 | 指標 | PDF 視讀值 | 結果 |", "|---|---|---|---:|---|"]
        lines += [f"| {r['data_year']} | {r['entity_raw']} | {r['metric_id']} | {r['expected_value_from_page_image']} | {r['status']} |" for r in historical.get("samples", [])]
        components = self.result.get("components")
        if components:
            lines += ["", "## 整併元件全量回查", "",
                      f"共 {components['canonical_records_checked']:,} 筆元件。地方 {components['local_raw_documents_checked']} 份原始 JSON，逐格核對 {components['local_raw_cells_and_derived_rows_checked']:,} 筆 derived 資料的原值與完整原始欄位；其 {components['local_canonical_records_checked']:,} 筆保留資料逐筆核對整併映射。",
                      f"排除的 {components['exact_duplicate_rows_excluded']:,} 筆均與保留列的原始值、期間、單位、館別及地理代碼相同；保留每個語意群組的所有異值。現批異值群組 {components['conflicting_value_groups']} 組，不能據此推論其他來源也沒有差異。",
                      "民國年與民國年月分別轉換參考年，但保留原年月、週期、館別，沒有填成年初／年底年度總值。館別有值時維持機構範圍，不改成縣市總量。萬與冊後綴有明確轉換規則，未在原欄寫元時不猜貨幣單位。",
                      f"歷史元件 {components['historical_adapter_records_checked']:,} 筆與 derived、PDF 雜湊回查；{components['explicit_missing_source_markers_retained']} 個來源未提供符號保持缺值。主計總處開放授權代碼與原授權網址保留。主計總處 PDF 內容本次沒有獨立全文轉錄比對。"]
        combined = self.result.get("combined")
        if combined:
            lines += ["", f"最終整併 JSONL {combined['records_checked']:,} 筆，與核心及元件的 ID 集合完全相同；每筆所有原有欄位及值型別均保留，沒有整併後遺漏、重複或覆寫。"]
        county = self.result.get("dgbas_county_table")
        if county:
            lines += ["", "## 主計總處縣市館數整包", "",
                      f"Z091101a029 原始 HTML {county['raw_cells_checked']} 格與長表逐格核對，原年份×縣市完整。2006–2025 年 460 格有值；1998–2005 年 184 格官方原示「-」，保留為缺值。",
                      f"包含總計與22縣市，採官方改制後縣市範圍且包含國家圖書館。整併已回查 {county['canonical_records_checked']} 筆，狀態 {county['canonical_mapping_status']}；不與其他館數序列合併。授權證據為主計總處母站廣泛宣告，套用到查詢子站的範圍推論已另標。"]
        lines += ["", "## 解讀界線", "",
                  "公開圖表的回應內沒有年分欄；年分是原始公開年度請求的年分，不能誤稱與 API 一樣有回應內年度驗證。來源回傳 0 仍可能涉及未蒐集或系統補零。",
                  "不同來源家族與全國／縣市／國立館重疊口徑沒有相加；匹配官方原檔不代表官方原資料沒有錯。歷史 PDF 授權未確認的狀態保持不變。",
                  "各層驗收範圍與輸入雜湊見 source-verification.json；元件映射回查不等於所有歷史 PDF 全文校對。"]
        if self.failures:
            lines += ["", "## 失敗", "", "```json", json.dumps(self.failures, ensure_ascii=False, indent=2), "```"]
        (directory / "source-verification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return report

    def combined(self):
        before = len(self.failures)
        expected = [json.loads(line) for name in ("data/observations.jsonl", "data/component_records.jsonl")
                    for line in (self.root / name).read_text().splitlines() if line]
        path = self.root / "data/combined/observations.jsonl"
        actual = [json.loads(line) for line in path.read_text().splitlines() if line]
        targets = {row["observation_id"]: row for row in actual}
        self.check(len(targets) == len(actual) == len(expected), "combined_counts_unique", len(actual))
        self.check(set(targets) == {row["observation_id"] for row in expected}, "combined_record_set", len(targets))
        for source in expected:
            target = targets.get(source["observation_id"], {})
            differences = [field for field, value in source.items() if not typed_equal(value, target.get(field))]
            self.check(not differences, "combined_field_mapping", {
                "observation_id": source["observation_id"], "different_fields": differences})
        self.result["combined"] = {"status": "pass" if len(self.failures) == before else "fail",
                                   "records_checked": len(actual), "all_original_fields_preserved": True,
                                   "snapshot_sha256": digest(path.read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reports", type=Path, default=None)
    parser.add_argument("--core-only", action="store_true", help="skip component adapter records")
    args = parser.parse_args()
    verification = Verification(args.root)
    try:
        verification.core()
        verification.historical()
        if not args.core_only and (args.root / "data/component_records.jsonl").exists():
            verification.components()
            if (args.root / "derived/dgbas_county_historical_long.csv").exists():
                verification.county_table()
            if (args.root / "data/combined/observations.jsonl").exists():
                verification.combined()
    except Exception as error:
        verification.check(False, "verification_exception", {"type": type(error).__name__, "error": str(error)})
    report = verification.report(args.reports or args.root / "research")
    print(json.dumps({"status": report["status"], "assertions": report["assertions"],
                      "failures": len(report["failures"])}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
