"""離線回歸：真資料不寫入，所有下載均以 fixture 取代。"""
import contextlib
import datetime as dt
import inspect
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import library_pipeline as pipeline


class FixtureResponse:
    def __init__(self, raw, url="https://example.gov.tw/data", headers=None):
        self.raw = raw
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}

    def read(self, *args):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def chart_spec(topic="Bacol00282", year=2023):
    return {
        "source_id": f"public-chart-{year}-{topic}",
        "url": pipeline.CHART_URL,
        "method": "POST",
        "body": {"Years": str(year), "Topic": topic,
                 "SelectLevel": [], "SelectCity": ["-1"]},
        "kind": "public_national_chart", "year": year, "topic": topic,
    }


def api_spec():
    return {"source_id": "ogdl-api-2023", "kind": "licensed_api", "year": 2023,
            "method": "GET", "body": None,
            "url": pipeline.BASE + "/api/API/ConsolidationData?Year=2023"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def resolve_pointer(document, pointer):
    result = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        result = result[int(token)] if isinstance(result, list) else result[token]
    return result


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(pipeline, "ROOT", self.root).start()
        pipeline.dump(self.root / "research/definitions.json", {"fields": []})
        # A test that accidentally falls through to the network fails immediately.
        patch.object(pipeline.urllib.request, "urlopen",
                     side_effect=AssertionError("離線測試禁止真實網路請求")).start()
        patch.object(pipeline.time, "sleep").start()

    def add_snapshot(self, spec, data):
        raw = encoded(data)
        relative = f"raw/snapshots/{spec['source_id']}/{pipeline.sha(raw)}.json"
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {**spec, "sha256": pipeline.sha(raw), "snapshot_path": relative,
                "retrieved_at": "2026-10-25T00:00:00+00:00"}

    def build(self, entries, definitions=()):
        pipeline.dump(self.root / "data/source_manifest.json",
                      {"sources": {x["source_id"]: x for x in entries}})
        pipeline.dump(self.root / "research/definitions.json", {"fields": list(definitions)})
        with contextlib.redirect_stdout(io.StringIO()):
            summary = pipeline.normalize()
        rows = [json.loads(line) for line in
                (self.root / "data/observations.jsonl").read_text().splitlines()]
        return summary, rows

    def acquire_fixture(self, spec, raw=None, error=None):
        kwargs = {"force": True} if "force" in inspect.signature(pipeline.acquire).parameters else {}
        with patch.object(pipeline, "specs", return_value=[spec]), \
                patch.object(pipeline.urllib.request, "urlopen",
                             side_effect=error if error else None,
                             return_value=FixtureResponse(raw or b"", spec["url"])), \
                contextlib.redirect_stdout(io.StringIO()):
            return pipeline.acquire([spec["year"]], **kwargs)

    def history(self):
        path = self.root / "data/source_history.jsonl"
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def test_response_rejects_wrong_year_empty_error_and_wrong_scope(self):
        with self.assertRaises(ValueError):
            pipeline.validate_response(api_spec(), encoded([{"縣市別": "2024-全國"}]))
        for invalid in ([], {"isSuccess": False}, [{"error": "access denied"}]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                pipeline.validate_response(chart_spec(), encoded(invalid))
        with self.assertRaises(ValueError):
            pipeline.validate_response(chart_spec(), encoded([
                {"ItemName": "臺北市", "ItemAmount1": 1, "legendName1": "圖書"}]))

    def test_catalog_http200_error_page_is_not_license_evidence(self):
        spec = {"source_id": "catalog-6425", "kind": "metadata"}
        fake = ("<html><title>Sign in</title><body>Access denied " + "x" * 200
                + "</body></html>").encode()
        with self.assertRaises(ValueError):
            pipeline.validate_response(spec, fake)

    def test_zero_null_blank_marker_and_precision_are_distinct(self):
        cases = [(0, (0, "reported")), ("0", (0, "reported")),
                 (None, (None, "source_null")), ("", (None, "source_blank")),
                 ("—", (None, "source_marker")), ("bad", (None, "unparsed")),
                 (True, (None, "unparsed")), ("1,234", (1234, "reported")),
                 ("12.30", ("12.30", "reported_decimal"))]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(pipeline.parse_number(raw), expected)

    def test_placeholder_column_is_skipped_but_real_zero_and_null_are_kept(self):
        data = [{"ItemName": "全國", "ItemAmount1": 0, "legendName1": "圖書",
                 "ItemAmount2": None, "legendName2": "電子書",
                 "ItemAmount3": 0, "legendName3": None}]
        _, rows = self.build([self.add_snapshot(chart_spec(), data)])
        self.assertEqual(len(rows), 2)
        by_field = {r["source_field"]: r for r in rows}
        self.assertEqual((by_field["圖書"]["value"], by_field["圖書"]["value_status"]),
                         (0, "reported"))
        self.assertIsNone(by_field["電子書"]["value"])
        self.assertEqual(by_field["電子書"]["value_status"], "source_null")
        self.assertIsNone(by_field["電子書"]["zero_interpretation"])
        self.assertIn("unconfirmed", by_field["圖書"]["zero_interpretation"])
        for row in rows:
            self.assertEqual(resolve_pointer(data, row["source_locator"]), row["raw_value"])

    def test_area_distribution_counts_and_heterogeneous_units_are_preserved(self):
        source = chart_spec("Bacol00286")
        area = [{"ItemName": "1000-5000平方公尺", "ItemAmount": 223,
                 "legendName": "圖書館總面積(間數)"}]
        _, rows = self.build([self.add_snapshot(source, area)])
        self.assertEqual(rows[0]["unit"], "間")
        self.assertEqual(rows[0]["value"], 223)
        self.assertEqual(rows[0]["source_field"], "1000-5000平方公尺")
        self.assertEqual(pipeline.chart_definition("Bacol00291", "巡迴車")["unit"], "台")
        self.assertEqual(pipeline.chart_definition("Bacol00291", "館外服務站")["unit"], "個")
        self.assertIsNone(pipeline.chart_definition("Bacol00288", "電子資源")["unit"])

    def test_json_pointer_escapes_api_key_and_county_alternatives_remain_distinct(self):
        key = "藏書/服務~數"
        data = [{"縣市別": "2023-" + name, key: value}
                for name, value in [("全國", "1,234"), ("新北市", "100"),
                                    ("新北市(不含國立館)", None)]]
        definition = {"raw_name": key, "group": "fixture", "unit": None,
                      "temporal_kind": "stock_year_end", "notes": []}
        _, rows = self.build([self.add_snapshot(api_spec(), data)], [definition])
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({r["observation_id"] for r in rows}), 3)
        self.assertEqual({r["geographic_scope"] for r in rows}, {
            "national_total", "county_default_includes_national_where_applicable",
            "county_excluding_national_alternative"})
        for row in rows:
            self.assertIn("~1", row["source_locator"])
            self.assertIn("~0", row["source_locator"])
            self.assertEqual(resolve_pointer(data, row["source_locator"]), row["raw_value"])
            self.assertEqual(row["data_year"], 2023)

    def test_chart_and_api_are_separate_series_not_merged_duplicate_facts(self):
        field = "全年圖書資訊借閱人次"
        definition = {"raw_name": field, "group": "fixture", "unit": "人次",
                      "temporal_kind": "flow_calendar_year", "notes": []}
        api = self.add_snapshot(api_spec(), [{"縣市別": "2023-全國", field: "10"}])
        chart = self.add_snapshot(chart_spec(), [
            {"ItemName": "全國", "ItemAmount1": 10, "legendName1": "圖書"}])
        _, rows = self.build([api, chart], [definition])
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r["series_id"] for r in rows}), 2)
        self.assertTrue(all(r["comparability"].startswith("not_certified") for r in rows))

    def test_snapshot_hash_failure_does_not_replace_existing_output(self):
        entry = self.add_snapshot(chart_spec(), [{"ItemName": "全國", "ItemAmount": 1}])
        entry["sha256"] = "0" * 64
        pipeline.dump(self.root / "data/source_manifest.json", {"sources": {entry["source_id"]: entry}})
        previous = self.root / "data/observations.jsonl"
        previous.write_text("previous approved output\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            pipeline.normalize()
        self.assertEqual(previous.read_text(), "previous approved output\n")

    def test_incremental_build_reparses_only_changed_source(self):
        a_spec, b_spec = chart_spec(year=2022), chart_spec(year=2023)
        old = [{"ItemName": "全國", "ItemAmount1": 1, "legendName1": "圖書"}]
        a, b = self.add_snapshot(a_spec, old), self.add_snapshot(b_spec, old)
        first, rows = self.build([a, b])
        self.assertEqual((first["reparsed_sources"], first["reused_normalized_sources"]), (2, 0))
        untouched = next(r for r in rows if r["source_id"] == a["source_id"])
        second, same_rows = self.build([a, b])
        self.assertEqual((second["reparsed_sources"], second["reused_normalized_sources"]), (0, 2))
        self.assertEqual(rows, same_rows)
        revised = self.add_snapshot(b_spec, [{"ItemName": "全國", "ItemAmount1": 2,
                                             "legendName1": "圖書"}])
        third, revised_rows = self.build([a, revised])
        self.assertEqual((third["reparsed_sources"], third["reused_normalized_sources"]), (1, 1))
        self.assertEqual(next(r for r in revised_rows if r["source_id"] == a["source_id"]), untouched)
        self.assertEqual(next(r for r in revised_rows if r["source_id"] == b["source_id"])["value"], 2)
        indicators = pipeline.load(self.root / "data/indicators.json", [])
        self.assertEqual(indicators[0]["observed_years"], [2022, 2023])

    def test_cached_source_still_requires_original_snapshot_integrity(self):
        entry = self.add_snapshot(chart_spec(), [{"ItemName": "全國", "ItemAmount1": 1,
                                                  "legendName1": "圖書"}])
        self.build([entry])
        previous = (self.root / "data/observations.jsonl").read_bytes()
        snapshot = self.root / entry["snapshot_path"]
        snapshot.write_bytes(b"tampered source")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            pipeline.normalize()
        self.assertEqual((self.root / "data/observations.jsonl").read_bytes(), previous)
        snapshot.unlink()
        with self.assertRaises(FileNotFoundError):
            pipeline.normalize()
        self.assertEqual((self.root / "data/observations.jsonl").read_bytes(), previous)

    def test_due_intervals_distinguish_metadata_recent_old_and_licensed_sources(self):
        specs = [chart_spec(year=2025), chart_spec(year=2024), chart_spec(year=2011),
                 api_spec(), {"source_id": "catalog-6425", "kind": "metadata", "year": None}]
        intervals = [14, 14, 365, 90, 7]
        current = dt.datetime.now(dt.timezone.utc)
        recent = {spec["source_id"]: {"last_checked_at":
                  (current - dt.timedelta(days=days - 1)).isoformat()}
                  for spec, days in zip(specs, intervals)}
        pipeline.dump(self.root / "data/source_manifest.json", {"sources": recent})
        self.assertEqual(pipeline.due_sources(specs), [])
        self.assertEqual(set(pipeline.due_sources(specs, force=True)), set(recent))
        expired = {spec["source_id"]: {"last_checked_at":
                   (current - dt.timedelta(days=days + 1)).isoformat()}
                   for spec, days in zip(specs, intervals)}
        pipeline.dump(self.root / "data/source_manifest.json", {"sources": expired})
        self.assertEqual(set(pipeline.due_sources(specs)), set(expired))

    def test_missing_original_is_due_even_before_its_normal_check_interval(self):
        specs = [chart_spec(year=2011), api_spec(),
                 {"source_id": "catalog-6425", "kind": "metadata", "year": None}]
        sources = {spec["source_id"]: {"last_checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "snapshot_path": "raw/omitted-" + spec["source_id"] + ".json"} for spec in specs}
        pipeline.dump(self.root / "data/source_manifest.json", {"sources": sources})
        self.assertEqual(set(pipeline.due_sources(specs)), set(sources))
        for source in sources.values():
            path = self.root / source["snapshot_path"]
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"restored fixture")
        self.assertEqual(pipeline.due_sources(specs), [])

    def test_missing_or_corrupt_body_sends_no_conditionals_and_cannot_accept_304(self):
        spec = chart_spec()
        raw = encoded([{"ItemName": "全國", "ItemAmount1": 1, "legendName1": "圖書"}])
        old = {**spec, "sha256": pipeline.sha(raw), "snapshot_path": "raw/omitted.json",
               "retrieved_at": "2026-10-25T00:00:00+00:00", "etag": '"fixture-etag"',
               "last_modified": "Sun, 25 Oct 2026 00:00:00 GMT"}
        for state in ("missing", "corrupt"):
            if state == "corrupt":
                path = self.root / old["snapshot_path"]
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b"not the verified body")
            seen = []
            def respond(request, **kwargs):
                seen.append({key.lower(): value for key, value in request.header_items()})
                return FixtureResponse(raw, spec["url"])
            with self.subTest(state=state), patch.object(pipeline.urllib.request, "urlopen", side_effect=respond):
                latest, _ = pipeline.fetch_one(spec, old)
                self.assertTrue((self.root / latest["snapshot_path"]).exists())
                self.assertNotIn("if-none-match", seen[0])
                self.assertNotIn("if-modified-since", seen[0])
            with self.subTest(state=state, response=304), \
                    patch.object(pipeline.urllib.request, "urlopen",
                                 side_effect=HTTPError(spec["url"], 304, "Not Modified", {}, None)), \
                    self.assertRaisesRegex(ValueError, "without a verified local body"):
                pipeline.fetch_one(spec, old)

    def test_fresh_acquisition_and_a_b_a_history_preserve_every_revision(self):
        spec = chart_spec()
        bodies = [encoded([{"ItemName": "全國", "ItemAmount1": n, "legendName1": "圖書"}])
                  for n in (1, 2, 1)]
        for body in bodies:
            self.assertEqual(self.acquire_fixture(spec, body), [])
        events = self.history()
        self.assertEqual([e["sha256"] for e in events], [pipeline.sha(x) for x in bodies])
        self.assertEqual([e["previous_sha256"] for e in events],
                         [None, pipeline.sha(bodies[0]), pipeline.sha(bodies[1])])
        self.assertEqual(len(list((self.root / "raw/snapshots" / spec["source_id"]).glob("*.json"))), 2)

    def test_failure_keeps_old_source_and_304_does_not_create_revision(self):
        spec = chart_spec()
        body = encoded([{"ItemName": "全國", "ItemAmount1": 1, "legendName1": "圖書"}])
        self.assertEqual(self.acquire_fixture(spec, body), [])
        before = pipeline.load(self.root / "data/source_manifest.json", {})["sources"][spec["source_id"]]
        errors = self.acquire_fixture(spec, encoded({"isSuccess": False}))
        self.assertEqual(len(errors), 1)
        after = pipeline.load(self.root / "data/source_manifest.json", {})["sources"][spec["source_id"]]
        self.assertEqual(after, before)
        self.assertEqual(len(self.history()), 1)
        self.assertEqual(self.acquire_fixture(spec, error=HTTPError(spec["url"], 304, "Not Modified", {}, None)), [])
        latest = pipeline.load(self.root / "data/source_manifest.json", {})["sources"][spec["source_id"]]
        self.assertEqual(latest["sha256"], before["sha256"])
        self.assertTrue((self.root / latest["snapshot_path"]).exists())
        self.assertEqual(len(self.history()), 1)

    def test_interruption_after_manifest_write_does_not_lose_history_event(self):
        spec = chart_spec()
        a = encoded([{"ItemName": "全國", "ItemAmount1": 1, "legendName1": "圖書"}])
        b = encoded([{"ItemName": "全國", "ItemAmount1": 2, "legendName1": "圖書"}])
        self.assertEqual(self.acquire_fixture(spec, a), [])
        original_dump = pipeline.dump

        def stop_after_manifest(path, value):
            original_dump(path, value)
            if path.name == "source_manifest.json":
                raise KeyboardInterrupt("fixture process interruption")

        with patch.object(pipeline, "dump", side_effect=stop_after_manifest), \
                self.assertRaises(KeyboardInterrupt):
            self.acquire_fixture(spec, b)
        latest = pipeline.load(self.root / "data/source_manifest.json", {})["sources"][spec["source_id"]]
        self.assertEqual(latest["sha256"], pipeline.sha(b))
        self.assertEqual(self.history()[-1]["sha256"], latest["sha256"])


if __name__ == "__main__":
    unittest.main()
