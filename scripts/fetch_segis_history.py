#!/usr/bin/env python3
"""SEGIS target alternative: complete anonymous DGBAS county-library table.

Only follow the observed public form chain StateFile_ZWeb -> Varval -> ShowQuery.
No authentication, inferred private endpoint or browser/UI operation.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import http.cookiejar
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw/segis-history"
BASE = "https://winstacity.dgbas.gov.tw/DgbasWeb/ZWeb/"
ENTRY = BASE + "StateFile_ZWeb.aspx?Type=table"
INDICATOR = "Z091101a029"
LICENCE = "https://www.stat.gov.tw/cp.aspx?n=3164"
DEFINITION = "公立公共圖書館館數（包含國家圖書館、國立公共資訊圖書館及國立臺灣圖書館）。"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def semantic_digest(records, names, years, definition):
    payload = {"indicator": INDICATOR, "definition": definition,
               "names": names, "selected_years": sorted(years),
               "values": sorted((int(row["data_year"]), row["area_code_raw"], row["value_raw"]) for row in records)}
    return sha(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def definition_text(text):
    match = re.search(r"<p id=['\"]descP['\"]>(.*?)(?:</p>|<p>|</div>)", text, re.S)
    if not match:
        raise ValueError("Official indicator notes locator changed; review required")
    return " ".join(html.unescape(re.sub("<[^>]+>", " ", match[1])).split())


def log_check(event):
    with (RAW / "source-checks.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def hidden(text):
    values = {}
    for tag in re.findall(r"<input[^>]*>", text):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', tag))
        if attrs.get("type") == "hidden" and attrs.get("name"):
            values[attrs["name"]] = html.unescape(attrs.get("value", ""))
    return values


def choices(text):
    selects = re.findall(r"<select[^>]*>.*?</select>", text, re.S)
    dates = re.findall(r"<option value=['\"]([^'\"]+)", selects[1])
    menu = re.search(r"<div[^>]+id=['\"]menu['\"].*?</div>", text, re.S).group(0)
    places = re.findall(r"<a[^>]*target=['\"]([^'\"]+)['\"]", menu)
    if not dates or not places:
        raise ValueError("Public year/place selector missing")
    return dates, places


def acquisition():
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    events = []

    def request(name, url, data=None, referer=ENTRY):
        payload = urllib.parse.urlencode(data).encode() if data is not None else None
        headers = {"User-Agent": "Taiwan-public-library-statistics/0.1 public-data research", "Referer": referer}
        if payload is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        with opener.open(urllib.request.Request(url, data=payload, headers=headers), timeout=30) as response:
            raw = response.read()
            final = response.url
        snapshot = RAW / (name + "-" + sha(raw) + ".html")
        if not snapshot.exists():
            snapshot.write_bytes(raw)
        (RAW / (name + ".html")).write_bytes(raw)
        events.append({"url": url, "method": "POST" if payload else "GET", "response_url": final,
                       "sha256": sha(raw), "path": str(snapshot.relative_to(ROOT)),
                       "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat()})
        return raw.decode("utf-8-sig")

    catalogue = request("dgbas-table", ENTRY)
    if DEFINITION not in catalogue or 'value="Y967"' not in catalogue:
        raise ValueError("Expected public indicator/definition absent; requires review")
    selection = hidden(catalogue)
    area = selection["ctl00$ContentPlaceHolder1$hfArea"]
    selection.update(UID="Y967", Type=area, Area=area)
    selection["ctl00$ContentPlaceHolder1$Go"] = "完成挑選"
    varval = request("dgbas-varval", BASE + "Varval.aspx", selection)
    dates, places = choices(varval)
    public = {"axX": "[Measures]", "axY": "[Date];[Place]", "axDate": "','".join(dates),
              "axArea": ";".join(places), "axCode": ";".join(places), "axEffect": "967",
              "axCycle": "Y年", "axSubjectNo": "公立公共圖書館個數(所)"}
    query = hidden(varval)
    query.update(public)
    query["ctl00$ContentPlaceHolder1$btnGoon"] = "繼續"
    request("dgbas-showquery", BASE + "ShowQuery.aspx?Z=", query, BASE + "Varval.aspx")
    save_json(RAW / "dgbas-query-request.json", {"url": BASE + "ShowQuery.aspx?Z=",
              "public_selection": public, "retrieved_at": events[-1]["retrieved_at"],
              "transient_viewstate": "Use fresh hidden fields from saved public form; no login required."})
    save_json(RAW / "dgbas-request-history.json", events)


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.depth = 0
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            if attrs.get("id") == "dataTable":
                self.active, self.depth = True, 1
            elif self.active:
                self.depth += 1
        if not self.active:
            return
        if tag == "tr":
            self.row = []
        if tag in {"td", "th"}:
            self.cell = {"tag": tag, "attributes": attrs, "text": ""}

    def handle_data(self, data):
        if self.active and self.cell is not None:
            self.cell["text"] += data

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag in {"td", "th"} and self.cell is not None:
            self.cell["text"] = self.cell["text"].strip()
            self.row.append(self.cell)
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "table":
            self.depth -= 1
            if not self.depth:
                self.active = False


def build():
    metadata_path = RAW / "metadata.json"
    previous = json.loads(metadata_path.read_text()) if metadata_path.exists() else None
    path = RAW / "dgbas-showquery.html"
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    if DEFINITION not in text:
        raise ValueError("Definition missing in returned data")
    current_notes = definition_text(text)
    previous_source_valid = False
    if previous:
        previous_path = ROOT / previous["source_raw_path"]
        previous_raw = previous_path.read_bytes() if previous_path.is_file() else None
        previous_source_valid = previous_raw is not None and sha(previous_raw) == previous["source_sha256"]
        previous_notes = (definition_text(previous_raw.decode("utf-8-sig")) if previous_source_valid
                          else previous.get("source_definition_text"))
        if previous_notes is not None and previous_notes != current_notes:
            raise ValueError("Official indicator notes/definition changed; saved for review, previous CSV preserved")
    snapshot = RAW / ("dgbas-showquery-" + sha(raw) + ".html")
    if not snapshot.exists():
        snapshot.write_bytes(raw)
    request = json.loads((RAW / "dgbas-query-request.json").read_text())
    dates, places = choices((RAW / "dgbas-varval.html").read_text(encoding="utf-8-sig"))
    years = [int(value[:4]) for value in dates]
    table = Table()
    table.feed(text)
    names = {cell["attributes"]["value"]: cell["text"] for cell in table.rows[0]
             if cell["attributes"].get("type") == "area"}
    if set(names) != set(places):
        raise ValueError("Geographic selector and result header differ")
    records, cell_ledger, seen = [], [], set()
    public_parameters = json.dumps(request["public_selection"], ensure_ascii=False, separators=(",", ":"))
    for row_index, row in enumerate(table.rows, start=1):
        for column_index, cell in enumerate(row, start=1):
            attrs, original = cell["attributes"], cell["text"]
            if "fvalue" not in attrs.get("class", "").split():
                continue
            key = (int(attrs["date"]), attrs["area"])
            if key in seen or attrs["effect"] != INDICATOR:
                raise ValueError("Duplicate cell or unexpected indicator")
            seen.add(key)
            if original == "-":
                value, status = None, "not_available_in_source"
            elif re.fullmatch(r"[0-9,]+", original):
                value, status = int(original.replace(",", "")), "reported"
            else:
                raise ValueError("Unparsed official cell " + repr(original))
            locator = f"HTML #dataTable; tr {row_index}; column {column_index}; td.fvalue[effect='{INDICATOR}'][date='{key[0]}'][area='{key[1]}']"
            records.append({"data_year": key[0], "entity_raw": names[key[1]], "entity_kind": "national_total" if names[key[1]] == "總計" else "county",
                "area_code_raw": key[1], "geography_vintage": "官方查詢『改制後縣市別』；歷史值依官方重編範圍，未自行合併",
                "metric_id": INDICATOR, "metric_raw": "公立公共圖書館個數(所)", "value_raw": original,
                "value": value, "value_status": status, "unit": "所", "temporal_kind": "annual_reference_year_stock_timing_unconfirmed",
                "period_raw": str(key[0]), "period_start": None, "period_end": None,
                "population_scope": DEFINITION, "national_libraries_scope": "includes_National_Central_Library_NLPI_and_NTL_per_official_definition",
                "source_id": "dgbas-county-library-Z091101a029", "source_agency": "行政院主計總處；指標資料來源：教育部",
                "source_url": ENTRY, "source_download_url": request["url"], "source_method": "POST",
                "source_request": public_parameters, "source_sha256": sha(raw), "source_local_path": str(snapshot.relative_to(ROOT)),
                "source_retrieved_at": request["retrieved_at"], "source_locator": locator,
                "source_table_row": row_index, "source_table_column": column_index,
                "license_status": "OGDL-1.0_site_declaration", "license_url": LICENCE,
                "license_scope_note": "主計總處母站廣泛網站宣告；查詢子站未另列條款。只整理官方統計事實，未納標誌或第三方作品。",
                "license_scope_inference": True, "extraction_status": "complete_public_HTML_table_cells_verified_against_all_public_selectors",
                "comparability": "not_certified_against_NLPI_or_other_library_count_series"})
            cell_ledger.append({"row": row_index, "column": column_index, **cell})
    expected = {(year, place) for year in years for place in places}
    if seen != expected:
        raise ValueError(f"Incomplete public table: {len(seen)} vs {len(expected)} cells")
    directory = ROOT / "derived"
    directory.mkdir(exist_ok=True)
    output = directory / "dgbas_county_historical_long.csv"
    fingerprint = semantic_digest(records, names, years, current_notes)
    previous_fingerprint = previous.get("semantic_sha256") if previous and previous.get("semantic_version") == 2 else None
    if previous and previous_source_valid and not previous_fingerprint and output.exists():
        with output.open(encoding="utf-8-sig", newline="") as stream:
            old_records = list(csv.DictReader(stream))
        previous_fingerprint = semantic_digest(old_records, previous["geographies"], previous["selected_years"], previous_notes)
    if previous and previous_source_valid and previous_fingerprint == fingerprint and output.exists():
        if previous.get("derived_sha256") and sha(output.read_bytes()) != previous["derived_sha256"]:
            raise ValueError("Previous derived CSV integrity mismatch; manual review required")
        # ViewState/layout and check time may change; immutable observation provenance stays fixed.
        previous.update(semantic_sha256=fingerprint, semantic_version=2, source_definition_text=current_notes,
                        derived_sha256=sha(output.read_bytes()),
                        last_checked_at=request["retrieved_at"], last_check_status="success",
                        last_response_sha256=sha(raw), last_response_path=str(snapshot.relative_to(ROOT)))
        log_check({"checked_at": request["retrieved_at"], "event": "unchanged_semantic_content",
                   "semantic_sha256": fingerprint, "response_sha256": sha(raw)})
        save_json(metadata_path, previous)
        print(json.dumps({"status": "unchanged_semantic_content", "records": len(records)}, ensure_ascii=False))
        return
    # Validate the licence reference before replacing any published derived output.
    licence_file = ROOT / "raw/ncl-historical/dgbas-open-data-declaration.html"
    licence_text = licence_file.read_text()
    if "政府資料開放授權條款-第1版" not in licence_text:
        raise ValueError("Saved DGBAS site licence evidence absent")
    if previous and output.exists():
        versions = RAW / "versions"
        versions.mkdir(exist_ok=True)
        old_csv = output.read_bytes()
        archive = versions / ("long-" + sha(old_csv) + ".csv")
        if not archive.exists():
            archive.write_bytes(old_csv)
        save_json(versions / ("metadata-" + sha(json.dumps(previous, sort_keys=True).encode()) + ".json"), previous)
    temporary_output = output.with_suffix(".csv.tmp")
    with temporary_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with (RAW / "dgbas_county_original_table.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["資料年"] + [names[place] for place in places])
        values = {(row["data_year"], row["area_code_raw"]): row["value_raw"] for row in records}
        for year in years:
            writer.writerow([year] + [values[(year, place)] for place in places])
    save_json(RAW / "dgbas_county_original_cells.json", cell_ledger)
    year_counts = {str(year): dict(collections.Counter(row["value_status"] for row in records if row["data_year"] == year)) for year in years}
    licence_copy = RAW / ("licence-" + sha(licence_file.read_bytes()) + ".html")
    if not licence_copy.exists():
        licence_copy.write_bytes(licence_file.read_bytes())
    metadata = {"source_id": records[0]["source_id"], "complete_selected_grid": True,
                "selected_years": years, "geographies": names, "records": len(records),
                "reported_cells": sum(row["value_status"] == "reported" for row in records),
                "missing_marker_cells": sum(row["value_status"] != "reported" for row in records),
                "semantic_sha256": fingerprint, "derived_sha256": sha(temporary_output.read_bytes()),
                "semantic_version": 2, "source_definition_text": current_notes,
                "first_observed_at": request["retrieved_at"], "last_checked_at": request["retrieved_at"],
                "last_check_status": "success",
                "year_status_counts": year_counts, "source_sha256": sha(raw),
                "source_raw_path": str(snapshot.relative_to(ROOT)), "source_format": "official HTML dataTable",
                "export_provenance": "Site CSV export is generated client-side. Original HTML retained; original_table.csv and cells.json are complete local serializations of its cells, not independent official downloads.",
                "source_url": ENTRY, "source_query_url": request["url"], "source_method": "POST",
                "source_request": request["public_selection"], "definition": DEFINITION,
                "license_status": records[0]["license_status"], "license_url": LICENCE,
                "license_evidence_file": str(licence_copy.relative_to(ROOT)),
                "license_evidence": "行政院主計總處網站上刊載之所有資料與素材，其得受著作權保護之範圍，採政府資料開放授權條款-第1版發布",
                "license_scope_inference": True, "caveats": ["1998–2005 cells are explicitly '-' and remain missing, never zero.",
                    "2006–2025 is the complete reported 20-year × 22 counties plus national total grid.",
                    "Official post-reform geography is retained even for pre-2010 reference years.",
                    "Definition includes National Central Library; do not merge or add to NLPI public-library count series.",
                    "The broad DGBAS parent-site licence is evidence; no separate query-subdomain licence was located."]}
    log_check({"checked_at": request["retrieved_at"], "event": "revised" if previous else "new",
               "previous_semantic_sha256": previous_fingerprint, "semantic_sha256": fingerprint,
               "response_sha256": sha(raw)})
    temporary_output.replace(output)
    save_json(metadata_path, metadata)
    print(json.dumps({key: metadata[key] for key in ["records", "reported_cells", "missing_marker_cells"]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="only parse saved official responses")
    parser.add_argument("--refresh", action="store_true", help="repeat the observed anonymous public form query; preserve old data on failure")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if args.offline and args.refresh:
        parser.error("--offline and --refresh are mutually exclusive")
    try:
        if args.refresh or (not args.offline and not (RAW / "dgbas-showquery.html").exists()):
            acquisition()
        build()
    except Exception as error:
        metadata_path = RAW / "metadata.json"
        if metadata_path.exists():
            previous = json.loads(metadata_path.read_text())
            previous.update(last_check_status="failed", last_failed_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                            last_error={"type": type(error).__name__, "message": str(error)})
            save_json(metadata_path, previous)
        raise


if __name__ == "__main__":
    main()
