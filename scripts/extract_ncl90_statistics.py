#!/usr/bin/env python3
"""Build the NCL volume 90 statistical appendix public-library subset.

Grid locations and literal readings were transcribed from the original scans by
an AI. Apple Vision separately attempts the same cells. A mismatch or failure
is preserved as such rather than used to modify a source reading.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import pypdfium2
from PIL import Image, ImageOps

EXPECTED_SHA = "45433ab3b7ac5986febf6057865aa8243a155b3029775ece88d6c3741c373a9a"
EXPECTED_BYTES = 16634553
URL = "https://www.ncl.edu.tw/files/file_pool/1/0Q083566036013949105/73b4de2e-e2bc-4df5-83f6-d86d41be25e5.pdf"
CATALOGUE = "https://www.ncl.edu.tw/tw/XCProduct/Cont?SId=0Q083565818875133522&XsmSId=0Q035603820559491425&sq="
TITLE = "中華民國九十年圖書館年鑑"
SOURCE_ID = "ncl-ed90-statistics"
PERIOD = "民國89年"
DASHES = {"-", "－", "—", "–", "―", "−", "﹣", "─"}

# Reviewed source cells in 70%-scale screenshot coordinates; coordinates are
# converted back to original PDF coordinates for the source locator.
# Each observation keeps the containing physical cell even if split into
# primary quantity and parenthesized respondent count.
COUNT_ROWS = (
    ("國立", "4", 486, 523), ("省市立", "72", 523, 557),
    ("縣市立", "40", 557, 592), ("鄉（鎮、市、區）立", "364", 592, 626),
    ("社教館", "3", 626, 660), ("私立", "135", 660, 693),
    ("小計", "618", 693, 722),
)
BASIC_COLUMNS = (
    ("館藏圖書冊數", "冊", 271, 437), ("閱覽席位", "席位", 437, 604),
    ("借閱人次", "人次", 604, 772), ("借閱冊數", "冊", 772, 938),
)
BASIC_ROWS = (
    ("公立公共圖書館", 508, 547,
     (("20,031,156","467"), ("－",None), ("12,535,383","467"), ("24,188,338","467"))),
    ("私立公共圖書館", 547, 586,
     (("864,410","51"), ("6,536","60"), ("189,069","54"), ("665,228","54"))),
)
TITLES = {
    "151": "臺閩地區各類型圖書館數量統計表",
    "152": "臺閩地區各類型圖書館基本資料統計表",
    "153": "中華圖書資訊館際合作協會各類型會員數量統計表",
}
VISION = r'''
import Foundation
import Vision
import ImageIO
for file in CommandLine.arguments.dropFirst() {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["en-US", "zh-Hant"]
    request.usesLanguageCorrection = false
    request.minimumTextHeight = 0.005
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: file), options: [:])
    do {
        try handler.perform([request])
        let observations = (request.results ?? []).sorted {
            if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.2 {
                return $0.boundingBox.midY > $1.boundingBox.midY
            }
            return $0.boundingBox.minX < $1.boundingBox.minX
        }.compactMap { $0.topCandidates(1).first?.string }
        let output: [String:Any] = [
            "id": URL(fileURLWithPath:file).deletingPathExtension().lastPathComponent,
            "text": observations.joined(separator:" "), "revision": request.revision
        ]
        print(String(data:try JSONSerialization.data(withJSONObject:output,options:[.sortedKeys]),encoding:.utf8)!)
    } catch {
        let output: [String:Any] = [
            "id": URL(fileURLWithPath:file).deletingPathExtension().lastPathComponent,
            "text": "", "error": error.localizedDescription
        ]
        print(String(data:try JSONSerialization.data(withJSONObject:output,options:[.sortedKeys]),encoding:.utf8)!)
    }
}
'''


def physical_cells():
    for index, (label, raw, top, bottom) in enumerate(COUNT_ROWS, 1):
        yield "151", 5, 681, index, 1, label, None, "圖書館數量", None, raw, None, (403, top, 472, bottom)
    for index, (label, top, bottom, values) in enumerate(BASIC_ROWS, 2):
        for column, ((metric, unit, left, right), (raw, response)) in enumerate(zip(BASIC_COLUMNS, values), 1):
            yield "152", 6, 682, index, column, label, metric, metric, unit, raw, response, (left, top, right, bottom)
    yield "153", 11, 687, 1, 2, "數量", "公共", "公共類會員數量", None, "30", None, (270,385,368,415)


def source_box(box):
    return [round(z/.70,3) for z in box]


def visual_status(raw, response, candidates):
    expected = [raw.replace(",","")] + ([response] if response else [])
    if raw in DASHES:
        match = any(any(ch in DASHES for ch in c["text"]) and not re.search(r"\d",c["text"]) for c in candidates)
        detected = any(re.search(r"\d",c["text"]) for c in candidates)
    else:
        readings = [re.findall(r"[0-9]+", re.sub(r"(?<=\d)[,.，\s]+(?=\d{3}\b)","",c["text"]))
                    for c in candidates]
        match = expected in readings
        detected = any(readings)
    if match:
        return "vision_and_ai_visual_agree", True
    if detected:
        return "vision_disagrees_ai_visual_only", False
    return "vision_no_matching_text_ai_visual_only", False


def run_vision(pdf, targets):
    with TemporaryDirectory(prefix="ncl90-vision-") as temporary:
        folder = Path(temporary)
        swift = folder/"read.swift"
        swift.write_text(VISION)
        images = []
        pages = {n: pdf[n-1].render(scale=.70).to_pil() for n in (5,6,11)}
        for cell in targets:
            table,p,_,row,col,*_,box = cell
            l,t,r,b = box
            for variant in ("full","inner"):
                inset = 4 if variant=="inner" else 1
                im = pages[p].crop((l+inset,t+inset,r-inset,b-inset)).convert("L")
                im = ImageOps.autocontrast(im,cutoff=1)
                im = im.resize((im.width*4,im.height*4),Image.Resampling.LANCZOS)
                im = ImageOps.expand(im,border=18,fill=255)
                path = folder/f"{table}-{row}-{col}-{variant}.png"
                im.save(path)
                images.append(path)
        process = subprocess.run(["swift",str(swift),*[str(p) for p in images]],
                                 check=True,capture_output=True,text=True,timeout=120)
    return {record["id"]:record for record in map(json.loads,process.stdout.splitlines())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0,str(args.project/"scripts"))
    from build_discovered_20261028 import adapt
    body = args.source.read_bytes()
    if len(body)!=EXPECTED_BYTES or hashlib.sha256(body).hexdigest()!=EXPECTED_SHA:
        raise ValueError("Official scan bytes differ from the reviewed input.")
    document = {
        "candidate_id": SOURCE_ID, "source_sha256": EXPECTED_SHA,
        "title": TITLE+"：圖書館統計資料", "edition_raw": TITLE,
        "source_local_path": "raw/ncl-early-statistics/yearbook-90-statistics.pdf",
        "official_url": URL, "catalogue_url": CATALOGUE, "publication_date": "2002-01-01",
        "retrieved_at": "2026-11-27T15:38:57.311351+00:00", "source_bytes": len(body),
        "source_version_id": SOURCE_ID+"@sha256:"+EXPECTED_SHA,
        "rights_status": "published_statistical_facts_only_full_document_license_unconfirmed",
    }
    pdf = pypdfium2.PdfDocument(body)
    targets = list(physical_cells())
    try:
        assert len(pdf)==28 and all(not pdf[p-1].get_textpage().get_text_range().strip() for p in (5,6,11))
        ocr = run_vision(pdf, targets)
    finally:
        pdf.close()
    statuses = {}
    rows, cells = [], []
    columns = json.loads((args.project/"scripts/discovered_20261028_canonical_columns.json").read_text())["columns"]
    for table,p,printed,row,col,label,header,metric,unit,raw,response,box in targets:
        cell_id = f"{SOURCE_ID}/t{table}/p{p}/r{row}/c{col}"
        full_literal = raw+(f" （{response}）" if response else "")
        readings = [ocr[f"{table}-{row}-{col}-{variant}"] for variant in ("full","inner")]
        status,matched = visual_status(raw,response,readings)
        statuses[cell_id] = status
        notes = ["掃描原圖由AI逐格核讀；來源數字按原欄列及括弧分辨。"]
        if table=="151":
            notes.append("列屬公共圖書館區塊，原刊國家圖書館另列。小計含私立館。來源未單獨印明是否含分館。")
        elif table=="152":
            notes.append("填答館數不含分館，分館統計併入總館。館別公私立分列。")
            if raw in DASHES:
                notes.append("原格僅短橫，沒有括號填答數；短橫語義未明，保持原符號與空值。")
        else:
            notes.append("中華圖書資訊館際合作協會公共類會員。公私立、分館數及生效日未明。")
        values = [("primary", raw, unit)] + ([("responding_libraries",response,"館")] if response else [])
        for role, literal, actual_unit in values:
            responding = role=="responding_libraries"
            bbox = source_box(box)
            cell = {
                "cell_id": cell_id+"/"+role, "physical_cell_id":cell_id,
                "source_document_id":SOURCE_ID,"source_url":URL+f"#page={p}",
                "source_catalogue_url":CATALOGUE,"source_sha256":EXPECTED_SHA,
                "source_version_id":document["source_version_id"],"source_pdf_page":p,
                "source_printed_page":str(printed),"source_table":table,
                "source_table_title":f"{TITLES[table]}（{PERIOD}）","source_row":str(row),
                "source_column":str(col),"source_cell_bbox":bbox,
                "source_locator": (f"PDF page {p}; printed page {printed}; table {table}; "
                                   f"source row {row}; numeric column {col}; quantity {role}; bbox "
                                   + ",".join(map(str,bbox))),
                "row_label_raw":label,"entity_raw":label,"column_label_raw":"填答館數" if responding else header,
                "entity_kind":"cooperation_membership_public_category" if table=="153" else "published_public_library_type",
                "geography_vintage":"臺閩地區原刊館型分類，非縣市面板",
                "national_libraries_scope":"association_member_category_public_national_column_excluded" if table=="153" else "national_library_separately_listed_not_in_selected_public_subgroup",
                "data_year":2000,"period_raw":PERIOD,"period_status":"explicit_original_table_ROC_year_exact_dates_unconfirmed",
                "temporal_kind":"annual_source_reference_exact_period_unconfirmed",
                "population_scope":("臺閩地區原表公共圖書館區塊／"+label if table=="151" else label+"／"+metric if table=="152" else metric) + ("；該指標填答館數" if responding else ""),
                "metric_id":f"t{table}-c{col}-{role}","metric_raw":metric+("／填答館數" if responding else ""),
                "value":None if literal in DASHES else int(literal.replace(",","")),"value_raw":literal,
                "value_status":"source_marker" if literal in DASHES else "reported",
                "unit":actual_unit,"unit_raw":"填答館數" if responding else header if table=="152" else None,
                "unit_status":"literal_heading_填答館數_identifies_unit_館" if responding else "literal_column_label" if actual_unit else "literal_quantity_unit_unprinted",
                "aggregation_role":"responding_libraries_not_total_libraries" if responding else "published_subtotal" if table=="151" and row==7 else "source_type_quantity",
                "source_notes":notes,
                "quality_flags":["AI_visual_review_not_human_collation","exact_dates_unconfirmed",status]+(["printed_dash_meaning_unconfirmed"] if literal in DASHES else []),
                "independent_check":{"method":"AI original scan cell visual read and Apple Vision OCR","matched":matched,"ocr_result_status":status,"vision_attempts":readings,"human_review":False},
                "source_edition":TITLE,"source_edition_roc":90,
                "physical_source_context":{"complete_cell_literal":full_literal,"quantity_role":role,
                                           "source_printed_response_parenthesized":bool(response),"is_total_library_count":False if responding else None,
                                           "source_image_box_coordinate_origin":"top-left on actual original PDF page",
                                           "source_row_index_scope":"selected_public_subgroup" if table=="151" else "whole_table_data_rows"},
            }
            observation = adapt(cell,document)
            assert set(observation)<=set(columns)
            observation["value_parse_rule"] = "separate_literal_quantity_in_same_physical_cell; original_full_cell_and_response_role_in_source_time_reference"
            observation["unit_basis"] = "literal_column_label" if observation["unit"] else "no_independent_unit_printed; counting_object_in_caption_and_population"
            rows.append({field:observation.get(field) for field in columns})
            cells.append({**cell,"observation_id":observation["observation_id"],"source_id":observation["source_id"]})
    assert len(rows)==23 and len({r["observation_id"] for r in rows})==23
    assert len({c["physical_cell_id"] for c in cells})==16
    assert sum(r["value"] is None for r in rows)==1
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"documents.json").write_text(json.dumps({"documents":[document]},ensure_ascii=False,indent=2)+"\n")
    (args.out/"source_cells.json").write_text(json.dumps({"physical_cells":16,"numeric_positions":22,"formal_observations":23,"physical_ocr_status_counts":dict(Counter(statuses.values())),"cells":cells},ensure_ascii=False,indent=2)+"\n")
    with (args.out/"observations.jsonl").open("w") as stream:
        for observation in rows:
            stream.write(json.dumps(observation,ensure_ascii=False)+"\n")
    print(json.dumps({"physical_cells":16,"numeric_positions":22,"observations":23,"original_dash":1,"physical_ocr_status_counts":dict(Counter(statuses.values())),"unmatched":{k:v for k,v in statuses.items() if v!="vision_and_ai_visual_agree"}},ensure_ascii=False))

if __name__ == "__main__":
    main()
