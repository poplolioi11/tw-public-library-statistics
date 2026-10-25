"""Small isolated regressions for semantic component adaptation; no real data writes."""
import contextlib
import csv
import hashlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import adapt_components as adapter
import fetch_segis_history as county_fetch


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.addCleanup(patch.stopall)
        patch.object(adapter, "ROOT", self.root).start()
        (self.root / "data").mkdir()
        (self.root / "derived").mkdir()
        self.raw = self.root / "raw/fixture.json"
        self.raw.parent.mkdir()
        self.raw.write_bytes(b'[{"fixture":true}]')
        self.sha = hashlib.sha256(self.raw.read_bytes()).hexdigest()

    def write_rows(self, name, rows):
        if not rows:
            return
        with (self.root / "derived" / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def local(self, period="11201", value="10", record="first", url="https://example.gov.tw/a"):
        return {"county": "新竹市", "source_id": "local-fixture", "source_title": "借閱量",
                "source_url": "https://data.gov.tw/dataset/fixture", "source_download_url": url,
                "source_sha256": self.sha, "source_retrieved_at": "2026-10-25T00:00:00+00:00",
                "source_locator": "JSON array[0]", "period_raw": period,
                "period_effective": period, "period_effective_basis": "observation_field",
                "periodicity_raw": "月", "facility_raw": "某分館", "geography_code_raw": "10018",
                "district_code_raw": "", "metric_group_raw": "", "metric_raw": "借閱冊數",
                "unit_raw": "", "value_raw": value, "duplicate_of": "", "record_id": record,
                "license_url": "https://data.gov.tw/license"}

    def raw_metadata(self, urls):
        folder = self.root / "raw/official-local/catalog-fixture"
        folder.mkdir(parents=True)
        for index, url in enumerate(urls):
            (folder / f"resource-{index}.metadata.json").write_text(json.dumps({
                "source_download_url": url, "source_sha256": self.sha, "raw_path": "raw/fixture.json"}))

    def run_adapter(self):
        with contextlib.redirect_stdout(io.StringIO()):
            adapter.main()
        return [json.loads(line) for line in
                (self.root / "data/component_records.jsonl").read_text().splitlines()]

    def test_roc_and_month_year_extraction(self):
        for period, expected in [("11201", 2023), ("10412", 2015), ("105", 2016),
                                 ("2018-01-01T00:00:00", 2018), ("2020", 2020), ("民國99年", 2010)]:
            with self.subTest(period=period):
                self.assertEqual(adapter.period_year(period), expected)

    def test_explicit_magnitude_and_book_suffix_without_inferred_currency(self):
        cases = [("5,407萬", (54070000, "reported", None)),
                 ("5,155萬 2,415", (51552415, "reported", None)),
                 ("251,609冊", (251609, "reported", "冊")),
                 ("5萬10000", (None, "unparsed", None)),
                 ("約5萬", (None, "unparsed", None))]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                actual = adapter.parse_local_value(raw, None)
                self.assertEqual(actual[:3], expected)
                self.assertTrue(actual[3])

    def test_months_stay_separate_and_facility_is_not_county_total(self):
        january, february = self.local(), self.local("11202", "20", "second")
        self.write_rows("local_historical_long.csv", [january, february])
        self.raw_metadata([january["source_download_url"]])
        rows = self.run_adapter()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["data_year"] for row in rows}, {2023})
        self.assertEqual({row["period_effective"] for row in rows}, {"11201", "11202"})
        self.assertEqual(len({row["observation_id"] for row in rows}), 2)
        self.assertTrue(all(row["period_start"] is None and row["period_end"] is None for row in rows))
        self.assertTrue(all(row["geographic_scope"] == "municipal_library_institution"
                            and row["facility"] == "某分館" for row in rows))

    def test_duplicate_exclusion_preserves_conflicting_value_from_other_resource(self):
        first = self.local()
        duplicate = {**first, "record_id": "duplicate", "duplicate_of": "first"}
        different = self.local(value="11", record="different", url="https://example.gov.tw/b")
        self.write_rows("local_historical_long.csv", [first, duplicate, different])
        self.raw_metadata([first["source_download_url"], different["source_download_url"]])
        rows = self.run_adapter()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["value"] for row in rows}, {10, 11})
        self.assertEqual({row["source_record_id"] for row in rows}, {"first", "different"})

    def test_ambiguous_same_resource_identity_fails_without_export(self):
        first, different = self.local(), self.local(value="11", record="different")
        self.write_rows("local_historical_long.csv", [first, different])
        self.raw_metadata([first["source_download_url"]])
        with self.assertRaisesRegex(ValueError, "collision"):
            self.run_adapter()
        self.assertFalse((self.root / "data/component_records.jsonl").exists())

    def test_dgbas_open_licence_and_explicit_missing_marker_are_preserved(self):
        row = {"data_year": "1991", "source_id": "dgbas-social-indicators-fixture",
               "entity_raw": "全國", "entity_kind": "national_total", "metric_id": "fixture",
               "metric_raw": "圖書館利用率", "value": "", "value_raw": "…",
               "value_status": "not_available_in_source", "unit": "百分比",
               "temporal_kind": "derived_ratio", "publication_date": "",
               "source_download_url": "https://example.gov.tw/a.pdf", "source_pdf_page": "1",
               "source_url": "https://example.gov.tw/a.pdf", "source_locator": "PDF page 1",
               "source_column": "1", "source_sha256": self.sha,
               "source_local_path": "raw/fixture.json", "source_retrieved_at": "2026-10-25",
               "license_status": "verified_open", "license_code": "OGDL-1.0_site_declaration",
               "license_url": "https://www.stat.gov.tw/cp.aspx?n=3164",
               "extraction_status": "fixture", "source_printed_page": "122",
               "source_table": "公立公共圖書館", "source_row": "18", "source_edition": "2005"}
        self.write_rows("dgbas_historical_long.csv", [row])
        result = self.run_adapter()[0]
        self.assertEqual(result["license_status"], "OGDL-1.0_site_declaration")
        self.assertEqual(result["license_url"], row["license_url"])
        self.assertIsNone(result["value"])
        self.assertEqual(result["raw_value"], "…")
        self.assertEqual(result["value_status"], "not_available_in_source")
        self.assertIsNone(result["zero_interpretation"])


class CountyRefreshTests(unittest.TestCase):
    """Self-contained table fixture; no real source file or network is required."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patch.stopall)
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw/segis-history"
        self.raw.mkdir(parents=True)
        table = "<table id='dataTable'><tr><th>&nbsp;</th><th type='area' value='05'>總計</th><th type='area' value='0502'>新北市</th></tr>"
        table += "<tr><td type='effect' value='Z091101a029'>公立公共圖書館個數(所)</td><td></td><td></td></tr>"
        for year, values in [(1998, ["-", "-"]), (2006, ["100", "10"])]:
            table += f"<tr><td type='date' value='{year}'>{year}</td>"
            for area, value in zip(["05", "0502"], values):
                table += f"<td class='text-right fvalue' effect='Z091101a029' date='{year}' area='{area}'>{value}</td>"
            table += "</tr>"
        table += "</table><p id='descP'>定義：" + county_fetch.DEFINITION + "<br>資料來源：教育部<p>"
        source_bytes = table.encode()
        source_sha = hashlib.sha256(source_bytes).hexdigest()
        (self.raw / "dgbas-showquery.html").write_bytes(source_bytes)
        source_path = "raw/segis-history/snapshot-" + source_sha + ".html"
        (self.root / source_path).write_bytes(source_bytes)
        self.metadata = {"source_sha256": source_sha, "source_raw_path": source_path,
                         "definition": county_fetch.DEFINITION, "selected_years": [1998, 2006],
                         "geographies": {"05": "總計", "0502": "新北市"}}
        (self.raw / "metadata.json").write_text(json.dumps(self.metadata))
        (self.raw / "dgbas-varval.html").write_text("<select><option value='967'>指標</option></select><select>"
            "<option value='1998/01/01'>1998</option><option value='2006/01/01'>2006</option></select>"
            "<div id='menu'><a target='05'>總計</a><a target='0502'>新北市</a></div>")
        (self.raw / "dgbas-query-request.json").write_text(json.dumps({"url": county_fetch.BASE + "ShowQuery.aspx?Z=",
            "public_selection": {"axEffect": "967"}, "retrieved_at": "2026-10-25T00:00:00+00:00"}))
        self.output = self.root / "derived/dgbas_county_historical_long.csv"
        self.output.parent.mkdir()
        with self.output.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["data_year", "area_code_raw", "value_raw", "source_sha256"])
            writer.writeheader()
            for year, values in [(1998, ["-", "-"]), (2006, ["100", "10"])]:
                for area, value in zip(["05", "0502"], values):
                    writer.writerow({"data_year": year, "area_code_raw": area, "value_raw": value, "source_sha256": source_sha})
        self.original_csv = self.output.read_bytes()
        licence = self.root / "raw/ncl-historical/dgbas-open-data-declaration.html"
        licence.parent.mkdir()
        licence.write_text("fixture：政府資料開放授權條款-第1版")
        patch.object(county_fetch, "ROOT", self.root).start()
        patch.object(county_fetch, "RAW", self.raw).start()
        patch.object(county_fetch.urllib.request, "build_opener",
                     side_effect=AssertionError("離線測試禁止真實網路請求")).start()

    def test_viewstate_or_layout_only_change_keeps_original_observation_provenance(self):
        current = self.raw / "dgbas-showquery.html"
        current.write_bytes(current.read_bytes() + b"\n<!-- changed transient ViewState/layout -->")
        request_path = self.raw / "dgbas-query-request.json"
        request = json.loads(request_path.read_text())
        request["retrieved_at"] = "2026-11-01T00:00:00+00:00"
        request_path.write_text(json.dumps(request))
        with contextlib.redirect_stdout(io.StringIO()):
            county_fetch.build()
        latest = json.loads((self.raw / "metadata.json").read_text())
        self.assertEqual(self.output.read_bytes(), self.original_csv)
        self.assertEqual(latest["source_sha256"], self.metadata["source_sha256"])
        self.assertEqual(latest["source_raw_path"], self.metadata["source_raw_path"])
        self.assertEqual(latest["last_checked_at"], request["retrieved_at"])
        self.assertNotEqual(latest["last_response_sha256"], latest["source_sha256"])

    def test_incomplete_response_does_not_replace_previous_csv(self):
        current = self.raw / "dgbas-showquery.html"
        current.write_text(re.sub(r"<td class='text-right fvalue'[^>]*>.*?</td>", "",
                                  current.read_text(), count=1))
        with self.assertRaisesRegex(ValueError, "Incomplete public table"):
            county_fetch.build()
        self.assertEqual(self.output.read_bytes(), self.original_csv)

    def test_definition_change_requires_review_and_keeps_previous_csv(self):
        current = self.raw / "dgbas-showquery.html"
        current.write_text(current.read_text().replace(county_fetch.DEFINITION,
                                                       county_fetch.DEFINITION + "新增母體說明"))
        with self.assertRaisesRegex(ValueError, "notes/definition changed"):
            county_fetch.build()
        self.assertEqual(self.output.read_bytes(), self.original_csv)

    def test_network_failure_keeps_previous_csv_and_records_failed_check(self):
        with patch.object(county_fetch, "acquisition", side_effect=OSError("fixture connection failed")), \
                patch("sys.argv", ["fetch_segis_history.py", "--refresh"]), \
                self.assertRaises(OSError):
            county_fetch.main()
        latest = json.loads((self.raw / "metadata.json").read_text())
        self.assertEqual(self.output.read_bytes(), self.original_csv)
        self.assertEqual(latest["source_sha256"], self.metadata["source_sha256"])
        self.assertEqual(latest["last_check_status"], "failed")

    def assert_rebuild_without_previous_raw(self, corrupt=False):
        previous_raw = self.root / self.metadata["source_raw_path"]
        if corrupt:
            previous_raw.write_bytes(b"corrupt old source")
        else:
            previous_raw.unlink()
        current = self.raw / "dgbas-showquery.html"
        current.write_bytes(current.read_bytes() + b"\n<!-- new independently downloaded response -->")
        new_sha = hashlib.sha256(current.read_bytes()).hexdigest()
        request_path = self.raw / "dgbas-query-request.json"
        request = json.loads(request_path.read_text())
        request["retrieved_at"] = "2026-11-02T00:00:00+00:00"
        request_path.write_text(json.dumps(request))
        with contextlib.redirect_stdout(io.StringIO()):
            county_fetch.build()
        latest = json.loads((self.raw / "metadata.json").read_text())
        self.assertEqual(latest["source_sha256"], new_sha)
        self.assertNotEqual(latest["source_sha256"], self.metadata["source_sha256"])
        self.assertTrue((self.root / latest["source_raw_path"]).exists())
        with self.output.open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["source_sha256"] for row in rows}, {new_sha})
        self.assertEqual({row["source_retrieved_at"] for row in rows}, {request["retrieved_at"]})

    def test_missing_previous_html_rebuilds_new_provenance_from_current_response(self):
        self.assert_rebuild_without_previous_raw()

    def test_corrupt_previous_html_cannot_hit_semantic_cache(self):
        self.assert_rebuild_without_previous_raw(corrupt=True)


if __name__ == "__main__":
    unittest.main()
