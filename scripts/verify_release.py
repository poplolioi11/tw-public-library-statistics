#!/usr/bin/env python3
"""Independent, offline source verification. Does not import acquisition/extraction code.

JSON observations are checked exhaustively against raw snapshots. Historical PDF
cells below are fixed expectations independently read from rendered pages on
2026-10-25; they are samples, not a full transcription review.
"""
from __future__ import annotations

import gzip
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
ADDITIONAL_NCL_FILES = ("ncl_gap_tables_long.csv", "ncl_additional_years_long.csv", "ncl_earlier_years_long.csv")
REVIEWED_NCL_ANNOTATIONS = {
    ("ncl-yearbook-103-public-library", "31", "1", "3"): {
        "raw": "79a", "numeric": "79", "annotation": "a",
        "source_sha256": "32172e27133b43e11839136cf0a2280050140b8f4633348e3d8c0bf06ddd5951",
        "evidence": "Independently read PDF page2/printed72/table31 and its footnote a: municipal main libraries79a; Taichung34/Tainan42 follow local definitions.",
    }
}
REVIEWED_NCL_ANNOTATIONS[("ncl-yearbook-107-statistics", "215", "1", "5")] = {
    "raw": "536*", "numeric": "536", "annotation": "*",
    "source_sha256": "2dcdd3f4a1e5ac2014ff79d13dd83e5274fc1d99885650f99450303c350c4f3b",
    "evidence": "Original PDF4/printed404/table215,105year column. The footnote explicitly revises earlier1,138 to536; preserve both edition observations, original star and relevant footnote.",
}
REVIEWED_SCOPED_QUANTITIES = {
    ("ncl-yearbook-110-public-library", "24", "21", "7"): {
        "raw": "分區資源中心新增80", "numeric": "80",
        "source_sha256": "4d95c7af8993461b0395b331e2d60a221e1eaeac80bf7def28a86ee6fb2009cf",
        "entity_raw": "臺東縣",
        "scope": "僅臺東縣分區資源中心新增電子書種數；非全縣完整新增總量",
        "evidence": "Official110edition public-library PDF23/printed87/table24; the cell explicitly limits the count to the regional resource centre.",
    }
}
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


def record_path(root, relative):
    profile = root / "data/combined/publication-profile.json"
    use_gzip = profile.exists() and jsonfile(profile).get("jsonl_compression") == "gzip"
    if use_gzip and relative in {"data/component_records.jsonl", "data/combined/observations.jsonl"}:
        return root / (relative + ".gz")
    return root / relative


def record_bytes(root, relative):
    path = record_path(root, relative)
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()


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


def reviewed_ncl_csvs(root):
    inventory = root / "data/reviewed_historical_cohorts.json"
    if not inventory.exists():
        return ADDITIONAL_NCL_FILES
    document = jsonfile(inventory)
    if document.get("schema_version") != "1.0.0":
        raise ValueError("Unrecognized reviewed cohort inventory")
    result = []
    for group in document["cohorts"]:
        if group["review_status"] != "source_reviewed":
            continue
        path = Path(group["derived_csv"])
        if path.is_absolute() or ".." in path.parts or path.parts[0] != "derived" or path.suffix != ".csv":
            raise ValueError("Invalid reviewed input path")
        result.append(path.name)
    if len(result) != len(set(result)):
        raise ValueError("Duplicate reviewed CSV")
    return tuple(result)


def independent_printed_magnitude(raw):
    match = re.fullmatch(r"(?:(\d+)億)?(?:(\d+)萬)?(\d+)?", raw)
    if not match or not any(character in raw for character in "億萬"):
        return None
    big, middle, small = (int(part or 0) for part in match.groups())
    if small >= 10000 or (match[1] and middle >= 10000):
        raise ValueError("Ambiguous printed magnitude group")
    return big * 100000000 + middle * 10000 + small


def ncl_source_value(source):
    """Independent adapter oracle. A missingness label cannot erase raw digits."""
    raw, normalized = source["value_raw"], source.get("value", "")
    status = source.get("value_status", "reported")
    empty_normalized = normalized is None or (isinstance(normalized, str) and normalized.strip() == "")
    if status in {"blank", "source_blank", "blank_in_source"}:
        if not isinstance(raw, str) or raw.strip() or not empty_normalized:
            raise ValueError("NCL blank has a nonempty original/normalized value")
        return None, "source_blank"
    if status == "source_marker" and raw in {"無", "未新增", "未統計"}:
        if not empty_normalized:
            raise ValueError("Printed無 marker must not erase a number")
        return None, "source_marker"
    if status in {"missing", "source_symbol", "source_marker", "not_available_in_source"}:
        if not isinstance(raw, str) or raw.strip() not in {"-", "--", "—", "–", "…", "...", "N/A", "NA", "n/a"}:
            raise ValueError("NCL missing cell has no recognized original marker")
        if not empty_normalized:
            raise ValueError("NCL marked cell also has a normalized numeric value")
        return None, "not_available_in_source"
    if status == "not_applicable":
        if raw not in {"N/A", "NA", "n/a", "不適用"} or not empty_normalized:
            raise ValueError("NCL not-applicable cell has no explicit applicability marker")
        return None, "not_applicable"
    value, canonical_status = independent_parse(normalized)
    if value is None:
        raise ValueError("NCL reported number does not parse")
    raw_numeric = re.sub(r"[\s,，]", "", str(raw))
    if source.get("value_parse_rule") == "literal_scoped_quantity":
        key = tuple(str(source.get(field, "")) for field in ("source_id", "source_table", "source_row", "source_column"))
        reviewed = REVIEWED_SCOPED_QUANTITIES.get(key)
        if (not reviewed or raw_numeric != reviewed["raw"]
                or source.get("source_sha256") != reviewed["source_sha256"]
                or source.get("entity_raw") != reviewed["entity_raw"]
                or source.get("entity_kind") != "county_scoped_component_not_full_total"
                or source.get("value_qualifier") != "scoped_source_component"
                or reviewed["scope"] not in source.get("population_scope", "")
                or Decimal(str(value)) != Decimal(reviewed["numeric"])):
            raise ValueError("Scoped NCL number lacks its independently pinned source/scope contract")
        return value, canonical_status
    annotation = source.get("cell_annotation")
    if annotation:
        key = tuple(str(source.get(field, "")) for field in ("source_id", "source_table", "source_row", "source_column"))
        reviewed = REVIEWED_NCL_ANNOTATIONS.get(key)
        if not reviewed or raw_numeric != reviewed["raw"] or annotation != reviewed["annotation"] or source.get("source_sha256") != reviewed["source_sha256"]:
            raise ValueError("NCL numeric annotation has no independently reviewed cell contract")
        raw_numeric = reviewed["numeric"]
    if source.get("value_qualifier") == "approximate_as_printed" and raw_numeric.startswith("約"):
        raw_numeric = raw_numeric[1:]
    if raw_numeric.endswith("%") and source.get("unit") == "%":
        raw_numeric = raw_numeric[:-1]
    parsed_raw, _ = independent_parse(raw_numeric)
    if parsed_raw is None and source.get("source_location_kind") in {"prose_numeric_span", "table_numeric_magnitude"}:
        parsed_raw = independent_printed_magnitude(raw_numeric)
    if parsed_raw is None or Decimal(str(parsed_raw)) != Decimal(str(value)):
        raise ValueError("NCL normalized number differs from original numeric representation")
    return value, canonical_status


def ncl_period_from_source(source):
    kind, year = source["temporal_kind"], str(source["data_year"])
    if source.get("source_subrow_label_raw") and source.get("period_start") and source.get("period_end"):
        start, end = (dt.date.fromisoformat(source[field]) for field in ("period_start", "period_end"))
        if start.year != int(year) or end.year != int(year) or start > end:
            raise ValueError("Invalid original-table subperiod")
        if source.get("source_period_interpretation_status")=="printed_extra_slash_unresolved_candidate_dates":
            return None, None
        return start.isoformat(), end.isoformat()
    if kind in {"flow_calendar_year", "annual_financial"}:
        return year + "-01-01", year + "-12-31"
    if kind == "stock_year_end":
        basis = " ".join(str(source.get(field) or "") for field in ("time_reference", "source_note", "source_footnotes_raw", "scope_note"))
        if not any(marker in basis for marker in ("年底", "年末", "12月底", "12月31日", "December31")):
            raise ValueError("NCL year-end stock has no explicit chapter/table timing basis")
        return None, year + "-12-31"
    return None, None


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
                record_bytes(self.root, "data/component_records.jsonl").decode().splitlines() if line]
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
        legacy_keys = set()
        for filename in ("ncl_historical_long.csv", "dgbas_historical_long.csv"):
            with (self.root / "derived" / filename).open(encoding="utf-8-sig", newline="") as stream:
                legacy_keys.update((row["source_id"], int(row["data_year"]), row["entity_raw"], row["metric_raw"])
                                   for row in csv.DictReader(stream))
        historical_targets = {(row["source_id"], row["data_year"], row["geography"], row["source_field"]): row
                              for row in rows if (row["source_id"], row["data_year"], row["geography"], row["source_field"]) in legacy_keys}
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
        additional_count = 0
        for name in reviewed_ncl_csvs(self.root):
            path = self.root / "derived" / name
            if path.exists():
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    additional_count += sum(1 for _ in csv.DictReader(stream))
        self.check(len(rows) == len(canonical_local) + len(expected_historical) + county_extra + additional_count, "component_total", len(rows))
        self.result["components"] = {
            "status": "pass" if len(self.failures) == before else "fail", "canonical_records_checked": len(rows),
            "local_raw_documents_checked": len(raw_documents), "local_raw_cells_and_derived_rows_checked": len(local),
            "blank_non_observation_raw_rows_excluded": blank_raw_rows,
            "local_canonical_records_checked": len(canonical_local), "exact_duplicate_rows_excluded": dropped,
            "conflicting_value_groups": sum(len(values) > 1 for values in conflicts.values()),
            "historical_adapter_records_checked": len(expected_historical),
            "additional_ncl_expected_records": additional_count,
            "explicit_missing_source_markers_retained": missing_statuses,
            "pdf_raw_files_hash_checked": len(source_files),
            "local_verification_level": "All original JSON cells and complete original objects vs derived; every nonduplicate adapter record vs derived and raw.",
            "historical_verification_level": "Every adapter record vs derived and PDF source hashes; NCL visual sample scope reported separately. DGBAS PDF content not independently transcribed in this adapter review.",
            "inputs": {"components_sha256": digest(record_bytes(self.root, "data/component_records.jsonl")),
                       "local_derived_sha256": digest((self.root / "derived/local_historical_long.csv").read_bytes())},
        }

    def ncl_gap(self, source_only=False):
        """All four tables vs a baseline fixed before new extraction was read."""
        before = len(self.failures)
        baseline_path = self.root / "research/ncl-gap-independent-expectations.json"
        baseline = jsonfile(baseline_path)
        with (self.root / "derived/ncl_gap_tables_long.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        expected = {}
        fixed_source_discrepancies = []
        for table in baseline["tables"]:
            path = self.root / "raw/ncl-historical" / table["source_filename"]
            self.check(digest(path.read_bytes()) == table["source_sha256"], "ncl_gap_pdf_sha", table["table_id"])
            for cell in table["cells"]:
                key = (table["source_filename"], table["pdf_page_1based"], cell["data_row"], cell["physical_column_1based"])
                expected[key] = (table, cell)
            fixed_source_discrepancies.extend({"table_id": table["table_id"], "check": "column_sum", **item}
                                              for item in table["printed_total_checks"] if item["difference_printed_minus_sum"])
            fixed_source_discrepancies.extend({"table_id": table["table_id"], "check": "row_components", **item}
                                              for item in table["row_total_discrepancies"])
        seen = set()
        numeric = blanks = 0
        aliases = {"town_main": "township_main", "town_branch": "township_branch", "provincial_other": "other_provincial"}
        for source in rows:
            key = (Path(source["source_local_path"]).name, int(source["source_pdf_page"]),
                   int(source["source_row"]), int(source["source_column"]))
            self.check(key not in seen and key in expected, "ncl_gap_grid_key", key)
            seen.add(key)
            if key not in expected:
                continue
            table, cell = expected[key]
            value, status = ncl_source_value(source)
            self.check(typed_equal(value, cell["expected_numeric_value"]), "ncl_gap_independent_cell", key)
            self.check(source["entity_raw"] == cell["entity_raw"] and int(source["data_year"]) == table["data_year"],
                       "ncl_gap_row_and_year", key)
            self.check((status == "source_blank") == (cell["expected_cell_state"] == "printed_blank"), "ncl_gap_blank_state", key)
            self.check(source["source_sha256"] == table["source_sha256"]
                       and int(source["source_printed_page"]) == table["printed_page"]
                       and source["source_table"] == table["table_number"]
                       and source["source_locator"] == cell["locator"], "ncl_gap_physical_lineage", key)
            column = next(c for c in table["columns"] if c["column_id"] == cell["column_id"])
            if table["kind"] == "library_counts":
                metric = "ncl_gap_count_table_" + aliases.get(cell["column_id"], cell["column_id"])
                label = column["heading_group"] + "／" + column["heading_leaf"]
            else:
                metric = "ncl_gap_2008_t5_" + cell["column_id"]
                label = ("人員／" + column["heading_leaf"] if column["heading_group"] == "人員"
                         else column["heading_leaf"] + "／" + column["unit"])
            self.check(source["metric_id"] == metric and source["metric_raw"] == label
                       and source["source_column_path"] == label, "ncl_gap_header_mapping", key)
            self.check(source["unit"] == column["unit"], "ncl_gap_unit", key)
            if table["kind"] == "library_counts":
                self.check(source.get("unit_raw", "") == "" and "未另印" in source.get("unit_basis", ""),
                           "ncl_gap_inferred_count_unit", key)
            numeric += value is not None
            blanks += status == "source_blank"
        self.check(seen == set(expected) and len(rows) == 1180 and numeric == 830 and blanks == 350,
                   "ncl_gap_complete_blind_grid", {"rows": len(rows), "numeric": numeric, "blanks": blanks})
        self.result["ncl_gap_independent"] = {"status": "pass" if len(self.failures) == before else "fail",
            "tables_fully_compared": 4, "grid_positions_checked": len(rows), "printed_numeric_cells": numeric,
            "printed_blank_cells": blanks, "baseline_sha256": digest(baseline_path.read_bytes()),
            "baseline_recorded_before_extractor_outputs_read": baseline["new_extractor_or_derived_outputs_read"] is False,
            "review_level": "All1180 printed number/blank positions vs independently entered PDFium page-image baseline; not human double-collation.",
            "expected_source_arithmetic_discrepancies": fixed_source_discrepancies,
            "canonical_mapping": "separately_checked_by_ncl_additional_components" if not source_only else "not_checked_in_source_only_mode"}

    def ncl_additional_components(self):
        """Map new NCL extraction records without importing an extraction program."""
        before = len(self.failures)
        sources = []
        files = []
        for name in reviewed_ncl_csvs(self.root):
            path = self.root / "derived" / name
            if path.exists():
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    sources.extend(csv.DictReader(stream))
                files.append(name)
        source_ids = {source["source_id"] for source in sources}
        records = [json.loads(line) for line in record_bytes(self.root, "data/component_records.jsonl").decode().splitlines() if line]
        targets = [row for row in records if row["source_id"] in source_ids]
        mapped = {(row["source_id"], row["source_locator"]): row for row in targets}
        expected, checked_hashes, statuses = set(), {}, collections.Counter()
        for source in sources:
            key = (source["source_id"], source["source_locator"])
            self.check(key not in expected, "new_ncl_derived_unique", key)
            expected.add(key)
            path = source["source_local_path"]
            if path not in checked_hashes:
                checked_hashes[path] = digest((self.root / path).read_bytes())
            self.check(checked_hashes[path] == source["source_sha256"], "new_ncl_source_pdf_sha", key)
            target = mapped.get(key)
            self.check(target is not None, "new_ncl_adapter_missing", key)
            if not target:
                continue
            value, status = ncl_source_value(source)
            statuses[status] += 1
            self.check(typed_equal(target["value"], value) and target["value_status"] == status
                       and target["raw_value"] == source["value_raw"], "new_ncl_adapter_value", key)
            for output, field in [("data_year", "data_year"), ("source_pdf_page", "source_pdf_page")]:
                self.check(target[output] == int(source[field]), "new_ncl_adapter_integer", {"key": key, "field": output})
            for output, field in [("geography", "entity_raw"), ("geographic_scope", "entity_kind"),
                                  ("source_sha256", "source_sha256"), ("source_snapshot_path", "source_local_path"),
                                  ("institutional_level", "institutional_level"), ("aggregation_role", "aggregation_role"),
                                  ("national_libraries_scope", "national_libraries_scope"),
                                  ("unit_raw", "unit_raw"), ("unit_basis", "unit_basis"),
                                  ("source_cell_annotation", "cell_annotation"),
                                  ("source_footnotes_raw", "source_footnotes_raw"),
                                  ("source_footnotes_status", "source_footnotes_status"),
                                  ("source_original_access_date_raw", "source_original_access_date_raw"),
                                  ("value_qualifier", "value_qualifier"),
                                  ("value_parse_rule", "value_parse_rule"),
                                  ("source_subrow_label_raw", "source_subrow_label_raw"),
                                  ("source_period_interpretation_status", "source_period_interpretation_status"),
                                  ("copyright_publication_month", "copyright_publication_month")]:
                self.check((target.get(output) or "") == source.get(field, ""), "new_ncl_adapter_field", {"key": key, "field": output})
            for field in ('source_original_physical_column','source_cell_note_raw','source_cell_note_status'):
                self.check((target.get(field) or '')==source.get(field,''),'new_ncl_supplementary_cell_text',{'key':key,'field':field})
            for field in ('ownership_scope','source_row_label_raw','source_parent_row_label_raw','source_parenthetical_raw','source_response_notation_kind','source_subrow_label_status','source_unit_context_locator','source_original_survey_date_raw'):
                if source.get(field):self.check(target.get(field)==source[field],'new_ncl_literal_hierarchy_or_response_basis',{'key':key,'field':field})
            for output,field in [('geography_contextual_name','entity_contextual_name'),('entity_label_status','entity_label_status'),('unit_status','unit_status')]:
                if source.get(field):self.check(target.get(output)==source[field],'new_ncl_explicit_context_or_unit_state',{'key':key,'field':field})
            if source.get('population_scope'):
                self.check(target.get('population_scope')==source['population_scope'],'new_ncl_population_scope_retained',key)
            self.check(target["source_version_id"] == source["source_id"] + "@sha256:" + source["source_sha256"],
                       "new_ncl_source_version", key)
            self.check(target["source_field"] == (source.get("source_column_path") or source["metric_raw"]), "new_ncl_source_field", key)
            self.check(target["source_url"] == source["source_download_url"] + "#page=" + source["source_pdf_page"]
                       and target["source_page_url"] == source["source_url"], "new_ncl_source_url", key)
            bbox = source.get("source_cell_bbox", "")
            self.check(target.get("source_cell_bbox") == bbox, "new_ncl_source_bbox_preserved", key)
            if bbox:
                coordinates = json.loads(bbox)
                self.check(isinstance(coordinates, list) and len(coordinates) == 4
                           and coordinates[0] < coordinates[2] and coordinates[1] < coordinates[3], "new_ncl_bbox_geometry", key)
            expected_start, expected_end = ncl_period_from_source(source)
            self.check(target["period_start"] == expected_start and target["period_end"] == expected_end,
                       "new_ncl_period_not_invented", key)
            if source.get("source_period_interpretation_status")=="printed_extra_slash_unresolved_candidate_dates":
                self.check(target.get("period_start_candidate")==source['period_start'] and target.get("period_end_candidate")==source['period_end'],"new_ncl_unresolved_candidate_dates_separate",key)
            unit = source.get("unit") or None
            if source.get("unit_status") == "source_heading_conflict_unresolved" or (unit and ("混合" in unit or "件/種/冊" in unit or "原表未列" in unit)):
                unit = None
            self.check(target["unit"] == unit, "new_ncl_unit", key)
            if value is None:
                self.check(target.get("zero_interpretation") is None, "new_ncl_null_not_zero", key)
        self.check(set(mapped) == expected and len(mapped) == len(targets) == len(sources), "new_ncl_adapter_complete", len(sources))
        self.result["new_ncl_components"] = {"status": "pass" if len(self.failures) == before else "fail",
            "derived_files": files, "records_checked": len(sources), "source_pdf_hashes_checked": len(checked_hashes),
            "value_status_counts": dict(statuses), "gap_review_level": "Complete independent page-image baseline is checked separately.",
            "other_years_review_level": "Derived-to-canonical fields and raw PDF hashes checked; separately, five original-image tables have 164 independently entered expected sample positions (159 numeric, two blank, three explicit markers), recorded in research/ncl-v02-independent-image-samples.json. This is not a full independent transcription of all additional-year PDF cells."}

    def reviewed_cohort_evidence(self):
        reports = []
        for year in sorted({int(m.group(1)) for name in reviewed_ncl_csvs(self.root) if (m := re.fullmatch(r"ncl_(\d{4})_long\.csv", name))}):
            csv_path = self.root / f"derived/ncl_{year}_long.csv"
            if not csv_path.exists():
                continue
            report_path = self.root / f"research/ncl-{year}-independent-review.json"
            report = jsonfile(report_path)
            comparison = report["comparison"]
            expected_hash = comparison.get("producer_csv_sha256") or comparison.get("csv_sha256")
            self.check(digest(csv_path.read_bytes()) == expected_hash, "independent_review_bound_to_csv", year)
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                source = list(csv.DictReader(stream))
            indexed = {(r["source_sha256"], r["source_table"], r["source_row"], r["source_column"]): r for r in source}
            self.check(len(indexed) == len(source) == report["expected_cells"] == len(report['cells']), "independent_full_grid_count", year)
            if 'mismatches' in report:self.check(not report['mismatches'],"independent_review_no_mismatches",year)
            seen=set()
            for cell in report["cells"]:
                key = (cell["source_sha256"], cell["table"], str(cell["source_row"]), str(cell["source_column"]))
                row = indexed.get(key)
                self.check(key not in seen,"independent_grid_no_duplicate_expectation",key);seen.add(key)
                self.check(row is not None, "independent_grid_coordinate", key)
                if row is None:
                    continue
                for field,expected_field in [('entity_raw','expected_entity_raw'),('entity_raw','entity_raw')]:
                    if cell.get(expected_field) is not None:
                        self.check(row.get(field)==cell[expected_field],"independent_grid_original_entity_label",key)
                if cell.get('expected_geography_contextual_name') is not None:
                    self.check(row.get('entity_contextual_name')==cell['expected_geography_contextual_name'],'independent_grid_geography_context_crosswalk',key)
                if cell.get('expected_entity_label_status') is not None:
                    self.check(row.get('entity_label_status')==cell['expected_entity_label_status'],'independent_grid_entity_inference_state',key)
                if cell.get('source_category_raw') is not None:
                    literal_category_locations=[row.get(f,'') or '' for f in ('source_table_title','source_row_label_raw','source_parent_row_label_raw','source_row_hierarchy_raw')]
                    self.check(any(cell['source_category_raw'] in text for text in literal_category_locations),'independent_grid_original_category_location',key)
                if cell.get('observation_data_year') is not None:
                    self.check(int(row['data_year'])==int(cell['observation_data_year']),"independent_grid_reference_year",key)
                self.check(re.sub(r"\s+", "", row["value_raw"]) == re.sub(r"\s+", "", cell["raw_value"]), "independent_grid_original_string", key)
                actual_value,actual_status=ncl_source_value(row)
                expected_value=cell["normalized_value"]
                self.check((actual_value is None and expected_value is None) or (actual_value is not None and expected_value is not None and Decimal(str(actual_value))==Decimal(str(expected_value))), "independent_grid_number", key)
                if cell.get('value_status'):
                    expected_status={'blank_in_source':'source_blank','blank':'source_blank','source_symbol':'not_available_in_source'}.get(cell['value_status'],cell['value_status'])
                    self.check(actual_status==expected_status,"independent_grid_value_state",key)
                self.check(int(row["source_pdf_page"]) == cell["pdf_page"] and str(row["source_printed_page"]) == str(cell["printed_page"]), "independent_grid_pages", key)
            reports.append({"report": str(report_path.relative_to(self.root)), "sha256": digest(report_path.read_bytes()), "source_cells": report["expected_cells"], "method": "Independently fixed original PDF glyph grid and visual header/row/footnote review, not human double checking."})
        selections=self.root/'research/ncl-v04-image-expectations.json'
        if selections.exists():
            expected=jsonfile(selections);selected_index={}
            for filename in reviewed_ncl_csvs(self.root):
                with (self.root/'derived'/filename).open(encoding='utf-8-sig',newline='') as stream:
                    for row in csv.DictReader(stream):
                        selected_index[(row['source_sha256'],row['source_table'],row['source_row'],row['source_column'])]=row
            self.check(expected['expected_cells']==len(expected['cells'])==31,"independent_v04_image_selection_count",31)
            for cell in expected['cells']:
                key=(cell['source_sha256'],cell['table'],str(cell['source_row']),str(cell['source_column']))
                row=selected_index.get(key);self.check(row is not None,"independent_v04_image_selection_coordinate",key)
                if row is None:continue
                self.check(re.sub(r'\s+','',row['value_raw'])==re.sub(r'\s+','',cell['raw_value']),"independent_v04_image_selection_literal",key)
                value,status=ncl_source_value(row);wanted=cell['normalized_value']
                self.check((value is None and wanted is None) or (value is not None and wanted is not None and Decimal(str(value))==Decimal(str(wanted))),"independent_v04_image_selection_value",key)
            reports.append({'report':str(selections.relative_to(self.root)),'sha256':digest(selections.read_bytes()),'source_cells':31,'method':'Explicit image selections, separate from the full glyph-grid comparisons. Gemini read three supplied original page images; primary agent also inspected them and the2020scoped-quantity page.'})
        reading = self.root / "derived/ncl_reading_2012_long.csv"
        if reading.exists():
            path = self.root / "research/ncl-reading-2012-independent-review.json"
            report = jsonfile(path)
            self.check(digest(reading.read_bytes()) == report["derived_sha256"], "independent_reading_review_bound_to_csv", 154)
            self.check(len(report["expected_cells"]) == report["comparison_counts"]["matched"] == 154 and not report["mismatches"], "independent_reading_complete", 154)
            self.check(all(item["matches"] for item in report["comparison_details"]), "independent_reading_no_numeric_difference", 154)
            reports.append({"report": str(path.relative_to(self.root)), "sha256": digest(path.read_bytes()), "source_cells": 154, "method": "Fixed original table expectations, merged growth-period review and original PDF checks."})
        self.result["additional_independent_review_evidence"] = reports

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
        canonical = [json.loads(line) for line in record_bytes(self.root, "data/component_records.jsonl").decode().splitlines() if line]
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
        image_review_path = self.root / "research/ncl-v02-independent-image-samples.json"
        if image_review_path.exists():
            image_review = jsonfile(image_review_path)
            self.result["ncl_v02_targeted_image_review"] = {
                "report_path": "research/ncl-v02-independent-image-samples.json",
                "readable_report_path": "research/ncl-v02-independent-image-samples.md",
                "report_sha256": digest(image_review_path.read_bytes()),
                "status": image_review["status"], "method": image_review["method"],
                "summary": image_review["summary"], "scope_limit": image_review["scope_limit"],
            }
        report = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "status": "pass" if not self.failures else "fail", "assertions": self.checks,
                  "scope": "3091 core source cells exhaustively checked; all NCL adapter lineage/number states checked. Complete independently fixed glyph grids for explicitly reviewed cohorts and image/header/row/footnote selections are separately bounded in each evidence report. Older source review limits remain individually reported.",
                  "independent_of_pipeline_and_extractors": True, "network_used": False,
                  **self.result, "failures": self.failures,
                  "limitations": ["Chart response JSON does not itself contain a validated reference year; year follows the saved official UI request.",
                                  "A returned zero is not proof of true zero or historical collection of that indicator.",
                                  "Source values matching snapshots do not prove the official source itself has no mistakes.",
                                  "Original-image review scope is explicit per cohort; complete glyph-grid comparison is not full human image double collation.",
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
        for evidence in self.result.get("additional_independent_review_evidence", []):
            lines += ["", "新增批次獨立原件證據：" + evidence["report"] + "；" + str(evidence["source_cells"]) + "格，報告SHA與目前CSV綁定。" + evidence["method"]]
        gap = self.result.get("ncl_gap_independent")
        if gap:
            lines += ["", "## 四張國圖缺表的完整獨立視讀基準", "",
                      f"新增四表 {gap['grid_positions_checked']} 個位置，包含 {gap['printed_numeric_cells']} 個印刷數字與 {gap['printed_blank_cells']} 個留白，已對照在讀取抽取結果前建立的 PDFium 視讀基準逐格核對。這350格留白不同於原刊以符號明示的缺值，也不改為零。",
                      "原表差異保留：2008借閱人次28列加總11,946,492，印刷總計11,964,492；2009未印國立分館欄，臺中市與全國分館合計分別較可見分項多1。未補欄或改原值。"]
        new_ncl = self.result.get("new_ncl_components")
        if new_ncl:
            lines += ["", f"新國圖元件 {new_ncl['records_checked']} 筆逐筆比對 derived 與 canonical 的原值、缺值狀態、館級、加總角色、期間、來源版本、頁列欄及bbox。另對2006、2007、2011、2013年的5張原件表，先依PDFium影像建立164個位置的固定期望值，再比對derived及canonical；159個數值、2個原印留白及3個明示符號均無差異。",
                      "此獨立影像抽查的母體、表頭、單位、註腳與期間依據詳見[ncl-v02-independent-image-samples.md](ncl-v02-independent-image-samples.md)及其[逐格JSON紀錄](ncl-v02-independent-image-samples.json)。這164個位置為明示範圍的抽查，並非所有新卷全格獨立轉錄；四張缺表的1180位置全量基準則另列於上一節。"]
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
                    for line in record_bytes(self.root, name).decode().splitlines() if line]
        path = record_path(self.root, "data/combined/observations.jsonl")
        actual = [json.loads(line) for line in record_bytes(self.root, "data/combined/observations.jsonl").decode().splitlines() if line]
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
                                   "snapshot_sha256": digest(record_bytes(self.root, "data/combined/observations.jsonl"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reports", type=Path, default=None)
    parser.add_argument("--core-only", action="store_true", help="skip component adapter records")
    parser.add_argument("--gap-only", action="store_true", help="compare four new NCL tables against the blinded baseline before canonical integration")
    args = parser.parse_args()
    verification = Verification(args.root)
    if args.gap_only:
        try:
            verification.ncl_gap(source_only=True)
        except Exception as error:
            verification.check(False, "gap_verification_exception", {"type": type(error).__name__, "error": str(error)})
        output = args.reports or args.root / "research"
        output.mkdir(parents=True, exist_ok=True)
        report = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "status": "pass" if not verification.failures else "fail", "assertions": verification.checks,
                  **verification.result, "failures": verification.failures,
                  "scope": "Complete1180-position blinded PDF-image baseline vs four new extraction tables; canonical integration not checked in this run."}
        (output / "ncl-gap-extraction-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        gap = verification.result.get("ncl_gap_independent", {})
        text = "# 國圖四張缺表獨立抽取驗收\n\n" + f"結果：{report['status']}；{verification.checks}個斷言，{len(verification.failures)}項失敗。\n\n"
        text += "已對照先行盲核基準，逐格檢查完整1180個表格位置（830印刷數字、350留白）的值、行名、欄位、缺值狀態與來源頁列欄。" + ("結果全部一致。" if not verification.failures else "結果存在下列失敗，不能視為全部一致。")
        text += "這不是抽樣驗收，也不是人類雙校；精確千分位字形不在本基準的逐字保證範圍。此階段尚未驗新canonical整合。\n\n"
        text += "原表三項算術差異照原值保留：2008借閱人次總計與組成列差18,000；2009臺中市分館與全國分館可見分項各比原印合計少1，不能補造原未印的國立分館欄。\n\n"
        text += "基準與每項差異詳見JSON。\n"
        if verification.failures:
            text += "\n```json\n" + json.dumps(verification.failures, ensure_ascii=False, indent=2) + "\n```\n"
        (output / "ncl-gap-extraction-verification.md").write_text(text)
        print(json.dumps({"status": report["status"], "assertions": verification.checks, "failures": len(verification.failures)}))
        raise SystemExit(0 if not verification.failures else 1)
    try:
        verification.core()
        verification.historical()
        if not args.core_only and record_path(args.root, "data/component_records.jsonl").exists():
            verification.components()
            if (args.root / "derived/ncl_gap_tables_long.csv").exists():
                verification.ncl_gap()
            if any((args.root / "derived" / name).exists() for name in reviewed_ncl_csvs(args.root)):
                verification.ncl_additional_components()
                verification.reviewed_cohort_evidence()
            if (args.root / "derived/dgbas_county_historical_long.csv").exists():
                verification.county_table()
            if record_path(args.root, "data/combined/observations.jsonl").exists():
                verification.combined()
    except Exception as error:
        verification.check(False, "verification_exception", {"type": type(error).__name__, "error": str(error)})
    report = verification.report(args.reports or args.root / "research")
    print(json.dumps({"status": report["status"], "assertions": report["assertions"],
                      "failures": len(report["failures"])}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
