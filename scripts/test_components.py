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
import verify_release as verifier


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

    def additional_ncl(self, raw="", value="", status="blank", temporal="stock_reference_date_not_explicit_in_table"):
        return {"data_year": "2008", "source_id": "ncl-gap-fixture", "metric_id": "national_main",
                "entity_raw": "臺北市", "entity_kind": "county", "metric_raw": "國立圖書館／總館",
                "source_column_path": "國立圖書館／總館", "value_raw": raw, "value": value,
                "value_status": status, "unit": "所", "unit_raw": "", "unit_basis": "原表未印單位，依上下文推定館數",
                "temporal_kind": temporal, "source_download_url": "https://example.gov.tw/a.pdf",
                "source_pdf_page": "2", "source_printed_page": "78", "source_table": "3",
                "source_row": "1", "source_column": "2", "source_url": "https://example.gov.tw/a",
                "source_locator": "PDF page 2; table 3; data row 1; physical column 2",
                "source_sha256": self.sha, "source_local_path": "raw/fixture.json", "source_retrieved_at": "2026-10-25",
                "extraction_status": "fixture", "institutional_level": "國立", "aggregation_role": "component",
                "source_cell_bbox": "[1,2,3,4]", "national_libraries_scope": "included_in_geographic_cross_tab"}

    def test_additional_ncl_blank_zero_and_uncertain_stock_date_stay_distinct(self):
        blank = self.additional_ncl()
        zero = self.additional_ncl("0", "0", "reported")
        rows = adapter.adapt_additional_ncl_rows([blank, zero])
        self.assertEqual((rows[0]["value"], rows[0]["value_status"], rows[0]["raw_value"]), (None, "source_blank", ""))
        self.assertIsNone(rows[0]["zero_interpretation"])
        self.assertEqual((rows[1]["value"], rows[1]["value_status"]), (0, "reported"))
        self.assertTrue(rows[1]["zero_interpretation"])
        self.assertTrue(all(row["period_start"] is None and row["period_end"] is None for row in rows))

    def test_additional_ncl_preserves_bbox_levels_roles_and_source_version(self):
        source = self.additional_ncl("123", "123", "reported", "flow_calendar_year")
        source["aggregation_role"] = "published_total"
        row = adapter.adapt_additional_ncl_rows([source])[0]
        self.assertEqual(row["source_cell_bbox"], source["source_cell_bbox"])
        self.assertEqual(row["institutional_level"], "國立")
        self.assertEqual(row["aggregation_role"], "published_total")
        self.assertEqual(row["source_version_id"], source["source_id"] + "@sha256:" + self.sha)
        self.assertEqual((row["period_start"], row["period_end"]), ("2008-01-01", "2008-12-31"))
        self.assertEqual(row.get("unit_basis"), source["unit_basis"])

    def test_additional_ncl_marker_cannot_erase_numeric_raw_or_normalized_value(self):
        for source in [self.additional_ncl("123", "", "missing"),
                       self.additional_ncl("-", "123", "source_marker"),
                       self.additional_ncl("", "0", "blank")]:
            with self.subTest(source=source["value_status"]), self.assertRaises(ValueError):
                adapter.adapt_additional_ncl_rows([source])
        row = adapter.adapt_additional_ncl_rows([self.additional_ncl("…", "", "missing")])[0]
        self.assertEqual((row["value"], row["value_status"], row["raw_value"]), (None, "not_available_in_source", "…"))

    def test_independent_ncl_oracle_rejects_inconsistent_blank_and_numeric_states(self):
        for source in [self.additional_ncl("123", "", "missing"),
                       self.additional_ncl("-", "1", "missing"),
                       self.additional_ncl("", 0, "blank"),
                       self.additional_ncl("12", "13", "reported")]:
            with self.subTest(source=source["value_status"]), self.assertRaises(ValueError):
                verifier.ncl_source_value(source)
        self.assertEqual(verifier.ncl_source_value(self.additional_ncl("1,234", "1234", "reported")), (1234, "reported"))

    def test_additional_ncl_period_contract_uses_only_explicit_year_end_stock_basis(self):
        for kind, reference, expected in [
                ("flow_calendar_year", "全年借閱量", ("2008-01-01", "2008-12-31")),
                ("annual_financial", "原表全年購書經費", ("2008-01-01", "2008-12-31")),
                ("stock_year_end", "同章明示截至2008年12月底", (None, "2008-12-31")),
                ("stock_reference_date_not_explicit_in_table", "原表年度，具體日期未知", (None, None))]:
            source = self.additional_ncl("1", "1", "reported", kind)
            source["time_reference"] = reference
            with self.subTest(kind=kind):
                self.assertEqual(verifier.ncl_period_from_source(source), expected)
                record = adapter.adapt_additional_ncl_rows([source])[0]
                self.assertEqual((record["period_start"], record["period_end"]), expected)
        source = self.additional_ncl("1", "1", "reported", "stock_year_end")
        with self.assertRaisesRegex(ValueError, "no explicit chapter/table timing basis"):
            verifier.ncl_period_from_source(source)

    def test_additional_ncl_unprinted_unit_description_is_not_a_calculation_unit(self):
        source = self.additional_ncl("123", "123", "reported")
        source["unit"] = "原表未列總量單位"
        source["unit_raw"] = "原表未列總量單位"
        record = adapter.adapt_additional_ncl_rows([source])[0]
        self.assertIsNone(record["unit"])
        self.assertEqual(record["unit_raw"], source["unit_raw"])
        self.assertIn(source["unit"], record["notes"])

    def test_independent_annotated_number_contract_is_bound_to_the_reviewed_cell(self):
        source = self.additional_ncl("79a", "79", "reported")
        source.update(source_id="ncl-yearbook-103-public-library", source_table="31", source_row="1", source_column="3",
                      source_sha256="32172e27133b43e11839136cf0a2280050140b8f4633348e3d8c0bf06ddd5951", cell_annotation="a")
        self.assertEqual(verifier.ncl_source_value(source), (79, "reported"))
        self.assertEqual(adapter.adapt_additional_ncl_rows([source])[0]["source_cell_annotation"], "a")
        for change in [{"value_raw": "79b"}, {"source_row": "2"}, {"cell_annotation": ""}, {"source_sha256": "b" * 64}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                verifier.ncl_source_value({**source, **change})
        self.assertEqual(verifier.ncl_source_value(self.additional_ncl("", "", "blank_in_source")), (None, "source_blank"))
        revised=self.additional_ncl('536*','536','reported')
        revised.update(source_id='ncl-yearbook-107-statistics',source_table='215',source_row='1',source_column='5',
                       source_sha256='2dcdd3f4a1e5ac2014ff79d13dd83e5274fc1d99885650f99450303c350c4f3b',cell_annotation='*')
        self.assertEqual(verifier.ncl_source_value(revised),(536,'reported'))
        with self.assertRaises(ValueError):verifier.ncl_source_value({**revised,'source_column':'6'})


    def test_prose_magnitude_and_printed_approximation_remain_traceable(self):
        source = self.additional_ncl("4億8,794萬7,482", "487947482", "reported_prose")
        source["source_location_kind"] = "prose_numeric_span"
        self.assertEqual(verifier.ncl_source_value(source), (487947482, "reported"))
        with self.assertRaises(ValueError):
            verifier.ncl_source_value({**source, "value": "487947483"})
        approximate = self.additional_ncl("約20.93", "20.93", "reported_prose")
        approximate.update(value_qualifier="approximate_as_printed", source_location_kind="prose_numeric_span")
        self.assertEqual(verifier.ncl_source_value(approximate), ("20.93", "reported_decimal"))
        with self.assertRaises(ValueError):
            verifier.ncl_source_value({**approximate, "value_qualifier": ""})

    def test_percent_points_require_a_percent_unit(self):
        source = self.additional_ncl("0.85%", "0.85", "reported")
        source["unit"] = "%"
        self.assertEqual(verifier.ncl_source_value(source), ("0.85", "reported_decimal"))
        with self.assertRaises(ValueError):
            verifier.ncl_source_value({**source, "unit": "人"})

    def test_literal_textual_source_states_are_not_zero_or_generic_missing(self):
        for raw in ("無", "未新增"):
            source = self.additional_ncl(raw, "", "source_marker")
            record = adapter.adapt_additional_ncl_rows([source])[0]
            self.assertEqual((record["value"],record["raw_value"],record["value_status"]),(None,raw,"source_marker"))
            self.assertEqual(verifier.ncl_source_value(source),(None,"source_marker"))
            with self.assertRaises(ValueError):adapter.adapt_additional_ncl_rows([{**source,"value":"0"}])
            with self.assertRaises(ValueError):verifier.ncl_source_value({**source,"value":"0"})

    def test_scoped_literal_cannot_become_a_full_county_total(self):
        source = self.additional_ncl("分區資源中心新\n增80", "80", "reported")
        source.update(source_id="ncl-yearbook-110-public-library", source_table="24", source_row="21", source_column="7",
                      source_sha256="4d95c7af8993461b0395b331e2d60a221e1eaeac80bf7def28a86ee6fb2009cf",
                      entity_raw="臺東縣", entity_kind="county_scoped_component_not_full_total",
                      population_scope="僅臺東縣分區資源中心新增電子書種數；非全縣完整新增總量",
                      value_parse_rule="literal_scoped_quantity", value_qualifier="scoped_source_component")
        self.assertEqual(verifier.ncl_source_value(source), (80, "reported"))
        for change in ({"source_row":"20"}, {"source_sha256":"b"*64}, {"value":"81"},
                       {"entity_kind":"county"}, {"population_scope":"全縣"}, {"value_raw":"新增80"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                verifier.ncl_source_value({**source, **change})

    def test_explicit_source_subperiod_survives_adaptation(self):
        source = self.additional_ncl("10", "10", "reported")
        source.update(temporal_kind="annual_financial", period_start="2013-09-01", period_end="2013-12-31",
                      period_raw="原表分期9/1–12/31", source_subrow_label_raw="行政法人（9/1–12/31）")
        row = adapter.adapt_additional_ncl_rows([source])[0]
        self.assertEqual(row["period_start"], "2013-09-01")
        self.assertEqual(row["period_end"], "2013-12-31")
        self.assertEqual(row["source_subrow_label_raw"], source["source_subrow_label_raw"])
        source["source_period_interpretation_status"]="printed_extra_slash_unresolved_candidate_dates"
        row=adapter.adapt_additional_ncl_rows([source])[0]
        self.assertIsNone(row["period_start"])
        self.assertIsNone(row["period_end"])
        self.assertEqual((row["period_start_candidate"],row["period_end_candidate"]),("2013-09-01","2013-12-31"))

    def test_conflicting_printed_unit_stays_unknown_with_separate_candidate(self):
        source = self.additional_ncl("10", "10", "reported")
        source.update(unit="人次", unit_raw="場次", unit_status="source_heading_conflict_unresolved", unit_interpretation_candidate="人次")
        row = adapter.adapt_additional_ncl_rows([source])[0]
        self.assertIsNone(row["unit"])
        self.assertEqual(row["unit_raw"], "場次")
        self.assertEqual(row["unit_status"], "source_heading_conflict_unresolved")
        self.assertEqual(row["unit_interpretation_candidate"], "人次")

    def test_duplicate_printed_county_labels_keep_two_physical_records(self):
        first = self.additional_ncl("10", "10", "reported")
        first.update(entity_raw="金門縣", entity_kind="county_source_label_duplicate_unresolved", observation_identity_suffix="row:21")
        second = {**first, "value_raw": "20", "value": "20", "source_row": "22", "observation_identity_suffix": "row:22"}
        records = adapter.adapt_additional_ncl_rows([first, second])
        self.assertEqual([r["geography"] for r in records], ["金門縣", "金門縣"])
        self.assertNotEqual(records[0]["observation_id"], records[1]["observation_id"])
        self.assertEqual([r["value"] for r in records], [10, 20])
        self.assertTrue(all(r["geographic_scope"] == "county_source_label_duplicate_unresolved" for r in records))


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
