#!/usr/bin/env python3
"""Isolated contract tests for run_update.run_extension_groups.

Only stdlib is used. Every input, output and state file lives in TemporaryDirectory;
extractor calls are mocked and no actual extraction or network operation occurs.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TARGET = Path(__file__).with_name("run_update.py")
GROUPS = {
    "ncl_gap": {
        "script": "extract_ncl_gap_tables.py",
        "args": (),
        "inputs": (
            "raw/ncl-historical/yearbook-98-public-library.pdf",
            "raw/ncl-historical/yearbook-99-public-library.pdf",
            "raw/ncl-historical/yearbook-100-public-library.pdf",
        ),
        "outputs": (
            "derived/ncl_gap_tables_long.csv",
            "derived/ncl_gap_tables_long.jsonl",
            "raw/ncl-historical/gap-tables-metadata.json",
        ),
    },
    "ncl_earlier": {
        "script": "extract_ncl_earlier_years.py",
        "args": (),
        "inputs": (
            "raw/ncl-earlier/yearbook-96-public-library.pdf",
            "raw/ncl-earlier/yearbook-97-public-library.pdf",
            "raw/ncl-earlier/yearbook-96-download.json",
            "raw/ncl-earlier/yearbook-97-download.json",
            "raw/ncl-earlier/table-specifications.json",
        ),
        "outputs": (
            "derived/ncl_earlier_years_long.csv",
            "derived/ncl_earlier_years_long.jsonl",
            "raw/ncl-earlier/metadata.json",
        ),
    },
    "ncl_additional": {
        "script": "extract_ncl_additional_years.py",
        "args": ("--offline",),
        "inputs": (
            "raw/ncl-additional/yearbook-101-public-library.pdf",
            "raw/ncl-additional/yearbook-103-public-library.pdf",
            "raw/ncl-additional/yearbook-101-statistics.pdf",
            "raw/ncl-additional/yearbook-102-statistics.pdf",
            "raw/ncl-additional/yearbook-103-statistics.pdf",
            "raw/ncl-additional/yearbook-101-public-library.metadata.json",
            "raw/ncl-additional/yearbook-103-public-library.metadata.json",
            "raw/ncl-additional/yearbook-101-statistics.metadata.json",
            "raw/ncl-additional/yearbook-102-statistics.metadata.json",
            "raw/ncl-additional/yearbook-103-statistics.metadata.json",
        ),
        "outputs": (
            "derived/ncl_additional_years_long.csv",
            "derived/ncl_additional_years_long.jsonl",
            "raw/ncl-additional/extracted-operational-cells.json",
            "raw/ncl-additional/documents.json",
            "raw/ncl-additional/extraction-validation.json",
        ),
    },
}


class UpdateGroupsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="library-update-groups-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        self.calls = []
        self.generation = 0
        spec = importlib.util.spec_from_file_location("isolated_run_update", TARGET)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.root_patch = mock.patch.object(self.module, "ROOT", self.root)
        self.call_patch = mock.patch.object(self.module, "call", side_effect=self.fake_call)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.mock_call = self.call_patch.start()
        self.addCleanup(self.call_patch.stop)
        for key, group in GROUPS.items():
            self.write("scripts/" + group["script"], "# synthetic extractor\n")
            for source in group["inputs"]:
                self.write(source, "synthetic source " + key + ": " + source + "\n")

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def fake_call(self, script, *args):
        self.calls.append((script, args))
        self.generation += 1
        matches = [(key, value) for key, value in GROUPS.items() if value["script"] == script]
        self.assertEqual(len(matches), 1, "unexpected extractor was invoked")
        key, group = matches[0]
        self.assertEqual(args, group["args"])
        for output in group["outputs"]:
            self.write(output, json.dumps({"group": key, "generation": self.generation}) + "\n")

    def run_groups(self):
        self.calls.clear()
        self.mock_call.reset_mock()
        self.module.run_extension_groups()
        return [script for script, _ in self.calls]

    def seed(self):
        self.run_groups()
        self.calls.clear()
        self.mock_call.reset_mock()

    def protected_files(self):
        files = [self.root / output for group in GROUPS.values() for output in group["outputs"]]
        files += list((self.root / "data").glob("*_extraction_state.json"))
        return {str(path.relative_to(self.root)): path.read_bytes() for path in files}

    def assert_missing_input_fails_without_call_or_output_change(self, missing):
        self.seed()
        before = self.protected_files()
        for relative in missing:
            (self.root / relative).unlink()
        failure = None
        try:
            self.module.run_extension_groups()
        except FileNotFoundError as exc:
            failure = exc
        self.assertIsNotNone(
            failure,
            "Missing reviewed source did not fail before extraction; calls=" + repr(self.calls),
        )
        self.assertEqual(self.calls, [], "must detect missing reviewed input before invoking an extractor")
        self.assertEqual(self.protected_files(), before, "missing input changed an existing output or state")

    def inventory_group(self, key, status="source_reviewed"):
        group = GROUPS[key]
        return {"id": key, "review_status": status, "script": group["script"], "args": list(group["args"]),
                "inputs": list(group["inputs"]), "outputs": list(group["outputs"]),
                "derived_csv": group["outputs"][0], "raw_directories": []}

    def test_reviewed_inventory_selects_only_its_registered_cohort(self):
        self.write("data/reviewed_historical_cohorts.json", json.dumps({"schema_version": "1.0.0", "cohorts": [self.inventory_group("ncl_earlier")]}))
        self.assertEqual(self.run_groups(), [GROUPS["ncl_earlier"]["script"]])
        self.assertEqual(self.run_groups(), [])
        self.write("raw/ncl-earlier/table-specifications.json", "changed reviewed coordinates")
        self.assertEqual(self.run_groups(), [GROUPS["ncl_earlier"]["script"]])

    def test_catalogue_only_inventory_entry_cannot_trigger_extraction(self):
        self.write("data/reviewed_historical_cohorts.json", json.dumps({"schema_version": "1.0.0", "cohorts": [self.inventory_group("ncl_earlier", "catalogue_only")]}))
        self.assertEqual(self.run_groups(), [])
        self.assertEqual(list((self.root / "data").glob("*_extraction_state.json")), [])

    def test_first_run_builds_exactly_three_groups(self):
        self.assertEqual(self.run_groups(), [group["script"] for group in GROUPS.values()])
        self.assertEqual(len(list((self.root / "data").glob("*_extraction_state.json"))), 3)
        self.assertTrue(all((self.root / output).exists() for group in GROUPS.values() for output in group["outputs"]))

    def test_identical_second_run_rebuilds_nothing(self):
        self.seed()
        before = self.protected_files()
        self.assertEqual(self.run_groups(), [])
        self.assertEqual(self.protected_files(), before)

    def test_changed_earlier_table_spec_rebuilds_only_earlier(self):
        self.seed()
        self.write("raw/ncl-earlier/table-specifications.json", "changed reviewed table spec\n")
        self.assertEqual(self.run_groups(), [GROUPS["ncl_earlier"]["script"]])
        self.assertEqual(self.run_groups(), [], "state should become current after the selective rebuild")

    def test_deleted_output_rebuilds_only_its_group(self):
        for key, group in GROUPS.items():
            for output in group["outputs"]:
                with self.subTest(group=key, output=output):
                    self.seed()
                    (self.root / output).unlink()
                    self.assertEqual(self.run_groups(), [group["script"]])
                    self.assertEqual(self.run_groups(), [])

    def test_missing_all_gap_sources_fails_and_preserves_outputs(self):
        self.assert_missing_input_fails_without_call_or_output_change(GROUPS["ncl_gap"]["inputs"])

    def test_missing_one_required_gap_pdf_fails_and_preserves_outputs(self):
        self.assert_missing_input_fails_without_call_or_output_change(
            ["raw/ncl-historical/yearbook-99-public-library.pdf"]
        )

    def test_missing_required_earlier_table_spec_fails_and_preserves_outputs(self):
        self.assert_missing_input_fails_without_call_or_output_change(
            ["raw/ncl-earlier/table-specifications.json"]
        )

    def test_missing_previously_reviewed_earlier_pdf_fails_and_preserves_outputs(self):
        self.assert_missing_input_fails_without_call_or_output_change(
            ["raw/ncl-earlier/yearbook-96-public-library.pdf"]
        )

    def test_missing_previously_reviewed_additional_pdf_fails_and_preserves_outputs(self):
        self.assert_missing_input_fails_without_call_or_output_change(
            ["raw/ncl-additional/yearbook-102-statistics.pdf"]
        )

    def test_changed_extractor_rebuilds_only_its_group(self):
        self.seed()
        self.write("scripts/" + GROUPS["ncl_additional"]["script"], "# revised synthetic extractor\n")
        self.assertEqual(self.run_groups(), [GROUPS["ncl_additional"]["script"]])

    def test_extractor_overwrites_then_raises_restores_outputs_and_state(self):
        for key, group in GROUPS.items():
            with self.subTest(group=key):
                self.seed()
                before = self.protected_files()
                self.write(group["inputs"][0], "changed input to trigger extraction\n")

                def fail_after_write(script, *args):
                    self.fake_call(script, *args)
                    raise RuntimeError("synthetic extractor failure after output writes")

                self.mock_call.side_effect = fail_after_write
                try:
                    with self.assertRaisesRegex(RuntimeError, "synthetic extractor failure"):
                        self.module.run_extension_groups()
                finally:
                    self.mock_call.side_effect = self.fake_call
                self.assertEqual(self.calls, [(group["script"], group["args"])])
                self.assertEqual(self.protected_files(), before, "partial output writes or state survived rollback")

    def test_extractor_returns_with_missing_output_restores_outputs_and_state(self):
        for key, group in GROUPS.items():
            for omitted in group["outputs"]:
                with self.subTest(group=key, omitted=omitted):
                    self.seed()
                    before = self.protected_files()
                    self.write(group["inputs"][0], "changed input for omitted output: " + omitted + "\n")

                    def return_without_one_output(script, *args):
                        self.fake_call(script, *args)
                        (self.root / omitted).unlink()

                    self.mock_call.side_effect = return_without_one_output
                    try:
                        with self.assertRaisesRegex(FileNotFoundError, "did not produce every reviewed output"):
                            self.module.run_extension_groups()
                    finally:
                        self.mock_call.side_effect = self.fake_call
                    self.assertEqual(self.calls, [(group["script"], group["args"])])
                    self.assertEqual(self.protected_files(), before, "missing output failure changed old outputs or state")


if __name__ == "__main__":
    unittest.main(verbosity=2)
