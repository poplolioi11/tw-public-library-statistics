#!/usr/bin/env python3
"""Offline, standard-library validation of the public distribution.

Checks agreement of the three canonical formats and packaged evidence. Missing
originals explicitly marked not_in_public_bundle are not full-source verification.
No requests are sent and no data are rewritten. Run --self-test for offline fixtures.
"""
from __future__ import annotations

import gzip
import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
import tempfile
import unicodedata
import unittest
import record_io
from source_literal_review import reviewed_non_scalar_literal
from urllib.parse import urlparse

HEX64 = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_NAME = "PUBLICATION_MANIFEST.json"
PUBLICATION_ONLY_FIELDS = {"snapshot_distribution", "public_evidence_path", "public_evidence_sha256", "public_projection_policy"}
CONTACT_PARTS = ("行動電話", "市話", "電子郵件", "電子信箱", "聯絡電話", "聯絡人", "聯絡資訊", "聯絡方式", "手機號", "傳真")
CONTACT_ENGLISH = {"email", "emailaddress", "tel", "telephone", "phone", "phonenumber", "mobile", "mobilenumber", "mobilephone", "fax", "contact", "contactname", "contactperson", "contactemail", "contactphone", "authorphone"}
SOURCE_MARKERS = {"無", "未新增", "未統計", "-", "--", "—", "–", "…", "...", "N/A", "NA", "n/a"}
NOT_APPLICABLE_MARKERS = {"N/A", "NA", "n/a", "不適用"}
NULL_STATUSES = {"source_blank", "source_null", "source_marker", "not_available_in_source", "not_applicable"}


class ValidationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"Cannot read JSON {path.name}: {type(error).__name__}") from error


def normalized_hash(value, label: str) -> str:
    require(isinstance(value, str), f"{label}: missing SHA-256")
    value = value.removeprefix("sha256:")
    require(bool(HEX64.fullmatch(value)), f"{label}: invalid SHA-256")
    return value


def relative_file(root: Path, value, label: str) -> tuple[str, Path]:
    require(isinstance(value, str) and bool(value.strip()), f"{label}: empty path")
    text = value.replace("\\", "/")
    rel = PurePosixPath(text)
    require(not rel.is_absolute() and ".." not in rel.parts and not re.match(r"^[A-Za-z]:", text), f"{label}: path must remain inside repository")
    actual = (root / str(rel)).resolve()
    require(actual.is_relative_to(root), f"{label}: symlink leaves repository")
    return str(rel), actual


def ignored_manifest_path(value: str) -> bool:
    parts = PurePosixPath(value.replace("\\", "/")).parts
    return parts == (MANIFEST_NAME,) or ".git" in parts or "__pycache__" in parts or value.endswith(".pyc")


def contact_key(key: str) -> bool:
    normalized = unicodedata.normalize("NFKC", key).lower()
    compact = re.sub(r"[\s_\-.:/()（）]+", "", normalized)
    if compact in {"電話", "手機"} or any(part in compact for part in CONTACT_PARTS):
        return True
    return compact in CONTACT_ENGLISH or compact.endswith(("contactemail", "contactphone", "contactperson", "authorphone", "officephone"))


def check_projection_keys(value, label: str, depth: int = 0) -> None:
    require(depth < 100, f"{label}: excessive JSON nesting")
    if isinstance(value, dict):
        for key, child in value.items():
            require(not contact_key(str(key)), f"{label}: unrelated contact key {key!r}")
            check_projection_keys(child, f"{label}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_projection_keys(child, f"{label}[{index}]", depth + 1)
    elif isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        # Also inspect a serialized original_fields object. Never match or remove
        # digit patterns in ordinary values, RIDs, URLs, hashes or identifiers.
        try:
            child = json.loads(value)
        except (ValueError, RecursionError):
            return
        if isinstance(child, (dict, list)):
            check_projection_keys(child, f"{label}<JSON>", depth + 1)


def csv_cell(value) -> str:
    return "" if value is None else str(value)


def sqlite_cell(value, declaration: str):
    if value is None:
        return None
    require(not isinstance(value, (dict, list)), "SQLite canonical format cannot represent a nested JSON cell")
    if "INT" in declaration.upper():
        require(isinstance(value, int) and not isinstance(value, bool), "Integer SQLite column differs from canonical JSON type")
        return value
    if "REAL" in declaration.upper():
        require(isinstance(value, (int, float)) and not isinstance(value, bool), "Real SQLite column differs from canonical JSON type")
        return float(value)
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        require(math.isfinite(value), "Non-finite JSON number")
        # Match SQLite's conversion for a bound floating value in a TEXT column.
        with sqlite3.connect(":memory:") as connection:
            return connection.execute("SELECT CAST(? AS TEXT)", (value,)).fetchone()[0]
    return str(value)


def is_reported_zero(value) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        return Decimal(str(value)) == 0
    except (InvalidOperation, ValueError):
        return False


def validate_value_semantics(record: dict, identifier: str) -> None:
    """Validate missingness against the original representation, never its label alone."""
    value, raw, status = record["value"], record["raw_value"], record.get("value_status")
    text = raw.strip() if isinstance(raw, str) else None
    if text in {"無", "未新增", "未統計"}:
        require(value is None and status == "source_marker", f"{identifier}: literal source text must retain source_marker, not zero or a claimed missingness reason")
    if value is None:
        require(status in NULL_STATUSES, f"{identifier}: null has unsupported source status {status!r}")
        if status == "source_blank":
            require(isinstance(raw, str) and text == "", f"{identifier}: source_blank requires an empty original string")
        elif status == "source_null":
            require(raw is None, f"{identifier}: source_null requires original JSON null")
        elif status == "not_applicable":
            require(text in NOT_APPLICABLE_MARKERS, f"{identifier}: not_applicable requires an explicit original applicability marker")
        else:
            reviewed=status=='source_marker' and reviewed_non_scalar_literal(record)
            require(text in SOURCE_MARKERS or reviewed, f"{identifier}: missing/marker status requires a recognized original symbol or an exact reviewed non-scalar source cell, not an unparsed number or text")
    else:
        require(status not in NULL_STATUSES, f"{identifier}: a null source status cannot carry a reported value")
        require(raw is not None and text != "" and text not in SOURCE_MARKERS | NOT_APPLICABLE_MARKERS,
                f"{identifier}: reported value contradicts an originally empty/null/marked cell")


def manifest_entries(manifest: dict) -> list[tuple[str, str]]:
    files = manifest.get("files", manifest.get("file_hashes"))
    require(isinstance(files, (dict, list)), "Manifest needs files mapping or [{path, sha256}] list")
    entries = []
    if isinstance(files, dict):
        for path, item in files.items():
            digest = item.get("sha256", item.get("hash")) if isinstance(item, dict) else item
            entries.append((path, digest))
    else:
        for item in files:
            require(isinstance(item, dict), "Manifest file entry must be an object")
            entries.append((item.get("path"), item.get("sha256", item.get("hash"))))
    require(bool(entries), "Manifest file inventory is empty")
    return entries


def statistical_fingerprint(records: list[dict]) -> str:
    projected = [{key: value for key, value in record.items() if key not in PUBLICATION_ONLY_FIELDS} for record in records]
    payload = json.dumps(projected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate(root: Path, allow_no_manifest: bool = False) -> dict:
    root = root.resolve()
    combined = root / "data/combined"
    summary = read_json(combined / "summary.json")
    expected_count = summary.get("records")
    expected_missing = summary.get("missing_cells")
    require(isinstance(expected_count, int) and not isinstance(expected_count, bool), "summary.records must be an integer")
    require(isinstance(expected_missing, int) and not isinstance(expected_missing, bool), "summary.missing_cells must be an integer; do not infer or hardcode it")
    require(0 <= expected_missing <= expected_count, "Invalid summary count range")

    rows = {}
    columns = set()
    relative = summary.get("canonical_jsonl_path") or "data/combined/observations.jsonl"
    require(relative in {"data/combined/observations.jsonl", "data/combined/observations.jsonl.gz"}, "Unrecognized canonical JSONL transport path")
    _, path = relative_file(root, relative, "canonical JSONL")
    opener = gzip.open if path.suffix == ".gz" else open
    uncompressed_digest = hashlib.sha256()
    try:
        with opener(path, "rb") as raw_stream:
            for block in iter(lambda: raw_stream.read(1024 * 1024), b""):
                uncompressed_digest.update(block)
    except (OSError, EOFError) as error:
        raise ValidationError("Cannot read complete canonical JSONL transport") from error
    logical_sha256 = uncompressed_digest.hexdigest()
    if summary.get("canonical_uncompressed_sha256"):
        require(logical_sha256 == summary["canonical_uncompressed_sha256"], "Uncompressed canonical SHA mismatch")
    try:
        with opener(path, "rt", encoding="utf-8-sig") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                require(isinstance(record, dict), f"JSONL line {line_number} is not an object")
                identifier = record.get("observation_id")
                require(isinstance(identifier, str) and bool(identifier.strip()), f"JSONL line {line_number}: empty observation_id")
                require(identifier not in rows, f"Duplicate JSONL observation_id: {identifier}")
                require("value" in record and "raw_value" in record, f"{identifier}: value/raw_value absent")
                require("data_year" in record and (record["data_year"] is None or type(record["data_year"]) is int),
                        f"{identifier}: data_year must be a confirmed integer year or null, without coercion")
                for field in ("source_id", "source_locator", "source_url"):
                    require(isinstance(record.get(field), str) and bool(record[field].strip()), f"{identifier}: empty {field}")
                parsed = urlparse(record["source_url"])
                require(parsed.scheme in ("http", "https") and bool(parsed.netloc), f"{identifier}: invalid source URL")
                normalized_hash(record.get("source_sha256"), f"{identifier}.source_sha256")
                rows[identifier] = record
                columns.update(record)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"Cannot read canonical JSONL: {type(error).__name__}") from error
    require(len(rows) == expected_count, "JSONL count differs from summary.records")
    missing_count = sum(row["value"] is None for row in rows.values())
    zero_count = sum(is_reported_zero(row["value"]) for row in rows.values())
    require(missing_count == expected_missing, "JSONL null count differs from summary.missing_cells")
    unresolved_period_records = sum(row["data_year"] is None for row in rows.values())
    reference_years = sorted({row["data_year"] for row in rows.values() if type(row["data_year"]) is int})
    require(type(summary.get("unresolved_period_records", 0)) is int and summary.get("unresolved_period_records", 0) == unresolved_period_records,
            "Unresolved period count differs from summary; null years must not be discarded or replaced by zero")
    if "reference_years" in summary or unresolved_period_records:
        require(isinstance(summary.get("reference_years"), list) and all(type(year) is int for year in summary["reference_years"])
                and summary["reference_years"] == reference_years, "summary.reference_years must contain confirmed integer years only")
    for identifier, record in rows.items():
        validate_value_semantics(record, identifier)

    csv_path = record_io.path_for(root, "data/combined/observations.csv")
    with record_io.open_text(root, "data/combined/observations.csv", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames or []
        require(len(header) == len(set(header)) and set(header) == columns, "CSV field set differs from JSONL")
        seen = set()
        for record in reader:
            identifier = record.get("observation_id")
            require(identifier in rows, "CSV has an unknown observation_id")
            require(identifier not in seen, f"Duplicate CSV observation_id: {identifier}")
            seen.add(identifier)
            require(None not in record, f"{identifier}: malformed CSV row")
            for field in header:
                require(record[field] == csv_cell(rows[identifier].get(field)), f"{identifier}: CSV differs at {field}")
        require(seen == set(rows), "CSV row set differs from JSONL")

    db_path = record_io.path_for(root, "data/combined/library_statistics.sqlite")
    require(db_path.is_file(), "Canonical SQLite file missing")
    with record_io.materialized_file(root, "data/combined/library_statistics.sqlite") as materialized:
        with sqlite3.connect(materialized.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            connection.execute("PRAGMA query_only=ON")
            require(connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity check failed")
            declarations = {row[1]: row[2] for row in connection.execute("PRAGMA table_info(observations)")}
            require(set(declarations) == columns, "SQLite field set differs from JSONL")
            connection.row_factory = sqlite3.Row
            seen = set()
            for sqlite_row in connection.execute("SELECT * FROM observations"):
                identifier = sqlite_row["observation_id"]
                require(identifier in rows, "SQLite has an unknown observation_id")
                require(identifier not in seen, f"Duplicate SQLite observation_id: {identifier}")
                seen.add(identifier)
                for field, declaration in declarations.items():
                    require(sqlite_row[field] == sqlite_cell(rows[identifier].get(field), declaration), f"{identifier}: SQLite differs at {field}")
            require(seen == set(rows), "SQLite row set differs from JSONL")

    hash_cache = {}
    def file_hash(actual: Path) -> str:
        if actual not in hash_cache:
            require(actual.is_file(), f"Missing packaged file: {actual.relative_to(root)}")
            digest = hashlib.sha256()
            with actual.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            hash_cache[actual] = digest.hexdigest()
        return hash_cache[actual]

    original_files = set()
    omitted_originals = set()
    evidence_files = set()
    for identifier, record in rows.items():
        original_sha = normalized_hash(record["source_sha256"], f"{identifier}.source_sha256")
        original_path = record.get("source_snapshot_path")
        if original_path:
            rel, actual = relative_file(root, original_path, f"{identifier}.source_snapshot_path")
            if actual.is_file():
                require(file_hash(actual) == original_sha, f"{identifier}: original source hash mismatch; projection hash must not replace source_sha256")
                original_files.add(rel)
            else:
                require(record.get("snapshot_distribution") == "not_in_public_bundle", f"{identifier}: original missing without not_in_public_bundle marker")
                omitted_originals.add((record["source_id"], original_sha))
        elif record.get("snapshot_distribution") == "not_in_public_bundle":
            omitted_originals.add((record["source_id"], original_sha))
        else:
            raise ValidationError(f"{identifier}: no source snapshot or explicit omission marker")
        evidence_path = record.get("public_evidence_path")
        if evidence_path:
            rel, actual = relative_file(root, evidence_path, f"{identifier}.public_evidence_path")
            digest = file_hash(actual)
            if record.get("public_evidence_sha256"):
                require(digest == normalized_hash(record["public_evidence_sha256"], f"{identifier}.public_evidence_sha256"), f"{identifier}: public evidence hash mismatch")
            if PurePosixPath(rel).parts[:2] == ("raw", "public-projections"):
                require(original_sha != digest, f"{identifier}: source_sha256 equals a transformed projection hash; keep the original source hash separately")
            evidence_files.add(rel)
        elif record.get("public_evidence_sha256"):
            raise ValidationError(f"{identifier}: public_evidence_sha256 has no evidence path")

    projection_count = 0
    projection_dir = root / "raw/public-projections"
    if projection_dir.exists():
        for candidate in sorted(projection_dir.glob("*.json")):
            rel, actual = relative_file(root, str(candidate.relative_to(root)), "public projection")
            check_projection_keys(read_json(actual), rel)
            projection_count += 1

    integrity = read_json(root / "docs/publication-integrity.json")
    require(integrity.get("records") == expected_count and integrity.get("missing_cells") == expected_missing, "Publication-integrity counts differ from summary")
    public_fingerprint = statistical_fingerprint(list(rows.values()))
    require(public_fingerprint == normalized_hash(integrity.get("public_statistical_content_sha256"), "public statistical fingerprint"), "Public statistical fingerprint mismatch")
    historical_fingerprint = normalized_hash(integrity.get("original_statistical_content_sha256"), "historical original statistical fingerprint")
    require(historical_fingerprint == public_fingerprint, "Published statistical content differs from the recorded original fingerprint")
    require(integrity.get("statistical_and_source_fields_unchanged") is True, "Publication does not declare statistical/source fields unchanged")

    manifest_path = root / MANIFEST_NAME
    manifest_present = manifest_path.is_file()
    require(manifest_present or allow_no_manifest, "PUBLICATION_MANIFEST.json missing; --allow-no-manifest is for preflight only")
    manifest_files = set()
    ignored_entries = 0
    manifest = read_json(manifest_path) if manifest_present else None
    if manifest_present:
        require(isinstance(manifest, dict), "Publication manifest must be an object")
    for filename, digest in manifest_entries(manifest) if manifest_present else []:
        require(isinstance(filename, str), "Manifest file path must be text")
        if ignored_manifest_path(filename):
            ignored_entries += 1
            continue
        rel, actual = relative_file(root, filename, "manifest entry")
        require(rel not in manifest_files, f"Duplicate manifest file: {rel}")
        require(file_hash(actual) == normalized_hash(digest, f"manifest {rel}"), f"Manifest file hash mismatch: {rel}")
        manifest_files.add(rel)
    require(bool(manifest_files) or not manifest_present, "No eligible manifest files were checked")
    for required in (relative, csv_path.relative_to(root).as_posix(), db_path.relative_to(root).as_posix(), "data/combined/summary.json"):
        require(required in manifest_files or not manifest_present, f"Manifest does not inventory canonical file: {required}")
    for evidence in evidence_files:
        require(evidence in manifest_files or not manifest_present, f"Manifest does not inventory public evidence: {evidence}")

    if manifest_present and manifest.get("canonical_sha256"):
        require(logical_sha256 == manifest["canonical_sha256"], "Manifest logical canonical SHA mismatch")
    partition_count = 0
    partition_index = root / "data/by_year/index.json"
    if partition_index.exists():
        index = read_json(partition_index)
        require(index.get("canonical_path") == relative, "Annual index points at a different canonical transport")
        require(type(index.get("unresolved_period_records", 0)) is int and index.get("unresolved_period_records", 0) == unresolved_period_records,
                "Annual index unresolved period count differs from canonical")
        union = hashlib.sha256(); total = 0; years = []
        for partition in index["partitions"]:
            year = partition.get("data_year")
            require("data_year" in partition and (year is None or type(year) is int), "Annual partition needs an integer year or an explicit null period")
            if year is None:
                require(partition["path"] == "data/by_year/unresolved_period.jsonl", "Unresolved periods require their own unresolved_period.jsonl partition")
            rel, actual = relative_file(root, partition["path"], "annual partition")
            require(rel in manifest_files or not manifest_present, "Annual partition not inventoried")
            content = actual.read_bytes()
            require(hashlib.sha256(content).hexdigest() == partition["sha256"], "Annual partition hash mismatch")
            entries = [json.loads(line) for line in content.splitlines() if line.strip()]
            require(len(entries) == partition["records"] and all(type(row.get("data_year")) is type(year) and row.get("data_year") == year for row in entries), "Annual partition rows/year mismatch")
            union.update(content); total += len(entries); years.append(partition["data_year"])
        require(years == sorted(set(years), key=lambda year: (year is None, year)), "Annual partitions duplicate or out of order")
        require(total == len(rows) == index["records"] and union.hexdigest() == logical_sha256, "Annual partition union differs from decompressed canonical")
        partition_count = len(years)

    if isinstance(summary.get("source_families"), dict):
        counts = {}
        for row in rows.values():
            family = row.get("source_family")
            counts[family] = counts.get(family, 0) + 1
        require(counts == summary["source_families"], "Source-family counts differ from summary")
    return {"records": len(rows), "canonical_jsonl_path": relative, "canonical_csv_path": csv_path.relative_to(root).as_posix(), "canonical_sqlite_path": db_path.relative_to(root).as_posix(), "canonical_uncompressed_sha256": logical_sha256, "annual_partition_union_checked": partition_count, "unresolved_period_records": unresolved_period_records, "missing_cells": missing_count, "reported_zero_cells": zero_count,
            "null_status_counts": {status: sum(row["value"] is None and row.get("value_status") == status for row in rows.values()) for status in sorted(NULL_STATUSES)},
            "formats": "JSONL/CSV/SQLite content agrees", "original_files_hash_checked": len(original_files),
            "omitted_source_versions_not_full_source_verified": len(omitted_originals),
            "public_evidence_files_hash_checked": len(evidence_files), "projection_files_contact_keys_checked": projection_count,
            "manifest_file_hashes_checked": len(manifest_files), "ignored_manifest_entries": ignored_entries,
            "public_statistical_fingerprint_recomputed": public_fingerprint,
            "manifest_checked": manifest_present, "publication_validation_complete": manifest_present,
            "verification_scope": "Canonical agreement, recomputed public statistical fingerprint, and packaged-file integrity only. The original fingerprint is a historical recorded claim, not fresh original-document verification. Omitted originals were not fully reverified; reported zero is not certification of true zero. Without a manifest this is preflight only."}


def self_test() -> bool:
    class Fixtures(unittest.TestCase):
        def setUp(self):
            self.temp = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp.cleanup)
            self.root = Path(self.temp.name)
            combined = self.root / "data/combined"
            combined.mkdir(parents=True)
            evidence = self.root / "raw/public-projections/source.json"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(json.dumps({"RID": "0912345678", "value": 0, "source_sha256": "a" * 64}))
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            base = {"source_id": "fixture-source", "source_family": "fixture", "source_url": "https://example.gov.tw/data?rid=0912345678",
                    "source_sha256": "a" * 64, "source_locator": "array[0]", "source_snapshot_path": "raw/omitted-original.json",
                    "snapshot_distribution": "not_in_public_bundle", "public_evidence_path": "raw/public-projections/source.json",
                    "public_evidence_sha256": digest, "license_scope_inference": True, "data_year": 2025}
            self.rows = [{**base, "observation_id": "zero", "value": 0, "raw_value": "0", "value_status": "reported"},
                         {**base, "observation_id": "null", "value": None, "raw_value": "-", "value_status": "not_available_in_source"}]
            (combined / "summary.json").write_text(json.dumps({"records": 2, "missing_cells": 1, "source_families": {"fixture": 2}}))
            (combined / "observations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in self.rows))
            with (combined / "observations.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
                writer.writeheader(); writer.writerows(self.rows)
            with sqlite3.connect(combined / "library_statistics.sqlite") as connection:
                columns = list(self.rows[0])
                connection.execute("CREATE TABLE observations (" + ",".join('"' + name + '" ' + ("INTEGER" if name == "data_year" else "TEXT") for name in columns) + ")")
                connection.executemany("INSERT INTO observations VALUES (" + ",".join("?" for _ in columns) + ")", [[row[name] for name in columns] for row in self.rows])
            (self.root / "docs").mkdir()
            fingerprint = statistical_fingerprint(self.rows)
            (self.root / "docs/publication-integrity.json").write_text(json.dumps({"records": 2, "missing_cells": 1,
                "original_statistical_content_sha256": fingerprint, "public_statistical_content_sha256": fingerprint,
                "statistical_and_source_fields_unchanged": True}))
            self.write_manifest()

        def write_manifest(self):
            files = {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in self.root.rglob("*") if path.is_file() and path.name != MANIFEST_NAME}
            (self.root / MANIFEST_NAME).write_text(json.dumps({"files": files}))

        def rewrite_canonical(self):
            combined = self.root / "data/combined"
            (combined / "observations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in self.rows))
            columns = list(self.rows[0])
            with (combined / "observations.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader(); writer.writerows(self.rows)
            with sqlite3.connect(combined / "library_statistics.sqlite") as connection:
                connection.execute("DELETE FROM observations")
                connection.executemany("INSERT INTO observations VALUES (" + ",".join("?" for _ in columns) + ")", [[row[name] for name in columns] for row in self.rows])
            self.write_manifest()

        def compressed_fixture(self):
            combined=self.root/"data/combined";plain=combined/"observations.jsonl";content=plain.read_bytes()
            (combined/"observations.jsonl.gz").write_bytes(gzip.compress(content,mtime=0));plain.unlink()
            summary=read_json(combined/"summary.json");summary.update(canonical_jsonl_path="data/combined/observations.jsonl.gz",canonical_uncompressed_sha256=hashlib.sha256(content).hexdigest());(combined/"summary.json").write_text(json.dumps(summary))
            directory=self.root/"data/by_year";directory.mkdir()
            (directory/"2025.jsonl").write_bytes(content)
            (directory/"index.json").write_text(json.dumps({"canonical_path":"data/combined/observations.jsonl.gz","records":2,"partitions":[{"data_year":2025,"path":"data/by_year/2025.jsonl","records":2,"sha256":hashlib.sha256(content).hexdigest()}]}))
            self.write_manifest()
            return content

        def test_gzip_master_and_plain_annual_union_match_original_bytes(self):
            content=self.compressed_fixture();report=validate(self.root)
            self.assertEqual(report["canonical_uncompressed_sha256"],hashlib.sha256(content).hexdigest())
            self.assertEqual(report["annual_partition_union_checked"],1)
            self.assertEqual(report["canonical_jsonl_path"],"data/combined/observations.jsonl.gz")

        def test_truncated_gzip_does_not_pass_as_partial_data(self):
            self.compressed_fixture();p=self.root/"data/combined/observations.jsonl.gz";p.write_bytes(p.read_bytes()[:-5]);self.write_manifest()
            with self.assertRaisesRegex(ValidationError,"complete canonical"):validate(self.root)

        def test_wrong_decompressed_sha_is_rejected(self):
            self.compressed_fixture();p=self.root/"data/combined/summary.json";summary=read_json(p);summary["canonical_uncompressed_sha256"]="b"*64;p.write_text(json.dumps(summary));self.write_manifest()
            with self.assertRaisesRegex(ValidationError,"Uncompressed canonical SHA"):validate(self.root)

        def test_rehashed_annual_partition_cannot_drop_an_observation(self):
            self.compressed_fixture();p=self.root/"data/by_year/2025.jsonl";p.write_bytes(p.read_bytes().splitlines(keepends=True)[0]);index=read_json(p.parent/"index.json");index["partitions"][0].update(records=1,sha256=hashlib.sha256(p.read_bytes()).hexdigest());(p.parent/"index.json").write_text(json.dumps(index));self.write_manifest()
            with self.assertRaisesRegex(ValidationError,"partition union"):validate(self.root)

        def test_literal_absence_text_retains_its_own_unresolved_state(self):
            for raw in ("無","未新增","未統計"):
                validate_value_semantics({"value":None,"raw_value":raw,"value_status":"source_marker"},"fixture")
                with self.assertRaises(ValidationError):validate_value_semantics({"value":None,"raw_value":raw,"value_status":"not_available_in_source"},"fixture")

        def test_formats_zero_null_omission_and_rid(self):
            report = validate(self.root)
            self.assertEqual(report["reported_zero_cells"], 1)
            self.assertEqual(report["missing_cells"], 1)
            self.assertEqual(report["original_files_hash_checked"], 0)
            self.assertEqual(report["omitted_source_versions_not_full_source_verified"], 1)

        def test_csv_cannot_turn_zero_into_empty(self):
            path = self.root / "data/combined/observations.csv"
            with path.open(newline="") as stream:
                reader = csv.DictReader(stream); fields = reader.fieldnames; rows = list(reader)
            rows[0]["value"] = ""
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
            with self.assertRaisesRegex(ValidationError, "CSV differs at value"):
                validate(self.root)
            self.rewrite_canonical()
            with sqlite3.connect(self.root / "data/combined/library_statistics.sqlite") as connection:
                connection.execute("UPDATE observations SET value='0' WHERE observation_id='null'")
            with self.assertRaisesRegex(ValidationError, "SQLite differs at value"):
                validate(self.root)

        def test_nested_contact_key_is_rejected_without_phone_regex(self):
            path = self.root / "raw/public-projections/source.json"
            path.write_text(json.dumps({"original_fields": json.dumps({"電子郵件": "fixture"})}))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            for row in self.rows: row["public_evidence_sha256"] = digest
            self.rewrite_canonical()
            with self.assertRaisesRegex(ValidationError, "unrelated contact key"):
                validate(self.root)

        def test_projection_hash_cannot_replace_original_hash(self):
            for row in self.rows: row["source_sha256"] = row["public_evidence_sha256"]
            self.rewrite_canonical()
            with self.assertRaisesRegex(ValidationError, "source_sha256 equals a transformed projection hash"):
                validate(self.root)

        def test_manifest_hash_tampering_is_rejected(self):
            manifest_path = self.root / MANIFEST_NAME
            manifest = read_json(manifest_path)
            manifest["files"]["data/combined/summary.json"] = "b" * 64
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValidationError, "Manifest file hash mismatch"):
                validate(self.root)

        def test_null_statuses_require_matching_original_representations(self):
            cases = [("source_blank", ""), ("source_blank", "  "), ("source_null", None),
                     ("source_marker", "—"), ("not_available_in_source", "…"),
                     ("not_applicable", "N/A"), ("not_applicable", "不適用")]
            for status, raw in cases:
                with self.subTest(status=status, raw=raw):
                    validate_value_semantics({"value": None, "raw_value": raw, "value_status": status}, "fixture")

        def test_numbers_or_unparsed_text_cannot_be_relabelled_as_missing(self):
            for status in NULL_STATUSES:
                for raw in ("0", "123", "1,234", "12.3", "約百人", 0, 123):
                    with self.subTest(status=status, raw=raw), self.assertRaises(ValidationError):
                        validate_value_semantics({"value": None, "raw_value": raw, "value_status": status}, "fixture")
            for status, raw in [("source_blank", None), ("source_null", ""),
                                ("not_available_in_source", ""), ("not_applicable", "-")]:
                with self.subTest(status=status, raw=raw), self.assertRaises(ValidationError):
                    validate_value_semantics({"value": None, "raw_value": raw, "value_status": status}, "fixture")

        def test_nonnull_value_cannot_have_a_null_status_or_raw_marker(self):
            for value, raw, status in [(0, "-", "reported"), (0, "", "reported"),
                                       (0, None, "reported"), (1, "1", "source_blank")]:
                with self.subTest(value=value, raw=raw, status=status), self.assertRaises(ValidationError):
                    validate_value_semantics({"value": value, "raw_value": raw, "value_status": status}, "fixture")

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    return result.wasSuccessful()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true", help="run isolated offline fixtures instead of validating a distribution")
    parser.add_argument("--allow-no-manifest", action="store_true", help="preflight only; do not claim full publication validation without the final manifest")
    args = parser.parse_args()
    if args.self_test:
        return 0 if self_test() else 1
    try:
        report = validate(args.root, allow_no_manifest=args.allow_no_manifest)
    except (ValidationError, OSError, EOFError, sqlite3.Error, ValueError) as error:
        print(f"PUBLICATION VALIDATION FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
