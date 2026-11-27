#!/usr/bin/env python3
"""Extract the complete public-library subsets from the pinned NCL 92/93 volumes."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pdfplumber
import pypdfium2

VOLUMES = {
    92: {
        "sha": "681cace80653b4fb85e5cfb2c6f952152816f54b54ad40f76f9630720364f93e",
        "url": "https://www.ncl.edu.tw/files/file_pool/1/0Q083565623997260739/ecaa1d7a-1133-4661-a1f1-385f50cac5fd.pdf",
        "catalogue": "https://www.ncl.edu.tw/librarianship-yearbook/0Q083565619396807101",
        "retrieved_at": "2026-10-28T09:35:06.139082+00:00",
        "bytes": 629928, "pages": 14, "title": "中華民國九十二年圖書館年鑑",
        "counts": ("166", 6, 564, (260, 289), (290, 304.5, 318.5, 332.5, 347, 361, 375, 390),
                   ("國立", "省市立", "縣市立", "鄉(鎮、市、區)立", "社教館", "私立", "小計")),
        "basic": ("167", 7, 565, (164, 269, 354, 439, 524),
                  ((300, 316, 333), (333, 350, 366))),
        "member": ("168", 12, 570, (201, 232, 226, 246)),
    },
    93: {
        "sha": "df50b5a3d7b2bbe88b2cc15f2a021630ec3123a5a6fd480241884f72e80194f7",
        "url": "https://www.ncl.edu.tw/files/file_pool/1/0Q083565614859888130/c8cdaafe-3720-43ba-8c67-8113c96873c1.pdf",
        "catalogue": "https://www.ncl.edu.tw/librarianship-yearbook/0Q083565582148900528",
        "retrieved_at": "2026-10-28T09:35:05.805332+00:00",
        "bytes": 1883323, "pages": 12, "title": "中華民國九十三年圖書館年鑑",
        "counts": ("176", 5, 448, (215, 249), (222, 236, 252, 267, 283, 298, 314, 330),
                   ("國立", "直轄市立", "縣市立", "鄉(鎮、市、區)立", "社教館", "私立", "小計")),
        "basic": ("177", 6, 449, (143, 226, 311, 396, 481),
                  ((257, 273, 288), (290, 307, 322))),
        "member": ("178", 11, 454, (153, 191, 182, 207)),
    },
}

TITLES = {
    "counts": "臺閩地區各類型圖書館數量統計表",
    "basic": "臺閩地區各類型圖書館基本資料統計表",
    "member": "中華圖書資訊館際合作協會各類型會員數量統計表",
}
METRICS = (("館藏圖書冊數", "冊"), ("閱覽席位", "席位"),
           ("借閱人次", "人次"), ("借閱冊數", "冊"))
NUMBER = re.compile(r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)")


def read_one(page, other_page, box):
    left, top, right, bottom = box
    text = page.within_bbox(box).extract_text() or ""
    text_page = other_page.get_textpage()
    try:
        alternate = text_page.get_text_bounded(
            left=left, right=right, bottom=page.height-bottom, top=page.height-top
        ).strip()
    finally:
        text_page.close()
    def parse(raw):
        raw = re.sub(r"\(cid:[0-9]+\)", "", raw)
        found = NUMBER.findall(raw)
        if len(found) != 1:
            raise ValueError((box, "exactly one integer required", raw))
        return found[0], int(found[0].replace(",", ""))
    numeral, value = parse(text)
    _, other_value = parse(alternate)
    if value != other_value:
        raise ValueError((box, "PDF engines disagree", text, alternate))
    return numeral, value, {"method": "positioned_pdfplumber_vs_PDFium_numeric_tokens",
                             "matched": True, "pdfplumber_raw": text,
                             "pdfium_raw": alternate, "human_review": False}


def extract(edition, source):
    spec = VOLUMES[edition]
    body = source.read_bytes()
    if len(body) != spec["bytes"] or hashlib.sha256(body).hexdigest() != spec["sha"]:
        raise ValueError(f"Original bytes differ for edition {edition}.")
    pdf = pypdfium2.PdfDocument(body)
    source_document_id = f"ncl-ed{edition}-statistics"
    period = f"民國{edition-1}年"
    document = {"candidate_id": source_document_id, "source_sha256": spec["sha"],
                "title": spec["title"] + "：圖書館統計章", "edition_raw": spec["title"],
                "source_local_path": f"raw/ncl-early-statistics/yearbook-{edition}-statistics.pdf",
                "official_url": spec["url"], "catalogue_url": spec["catalogue"],
                "retrieved_at": spec["retrieved_at"], "source_bytes": spec["bytes"],
                "source_version_id": source_document_id+"@sha256:"+spec["sha"],
                "rights_status": "published_statistical_facts_only_full_document_license_unconfirmed"}
    cells = []
    try:
        with pdfplumber.open(source) as doc:
            assert len(pdf) == len(doc.pages) == spec["pages"]
            def emit(kind, table, p, printed, row, column, row_label, column_label,
                     metric, population, notes, measurements):
                page = doc.pages[p-1]
                other = pdf[p-1]
                try:
                    tokens = [(role, box, unit, read_one(page, other, box))
                              for role, box, unit in measurements]
                finally:
                    other.close()
                physical_id = f"{source_document_id}/t{table}/p{p}/r{row}/c{column}"
                full_text = tokens[0][3][0]
                if len(tokens) == 2:
                    full_text += "\n（"+tokens[1][3][0]+"）"
                for role, bbox, unit, (numeral, value, check) in tokens:
                    response = role == "responding_libraries"
                    suffix = "；僅此指標填答館數，不含分館，分館資料併入總館"
                    cells.append({
                        "cell_id": physical_id+"/"+role, "physical_cell_id": physical_id,
                        "source_document_id": source_document_id,
                        "source_url": spec["url"]+f"#page={p}", "source_catalogue_url": spec["catalogue"],
                        "source_sha256": spec["sha"], "source_version_id": document["source_version_id"],
                        "source_pdf_page": p, "source_printed_page": str(printed),
                        "source_table": table, "source_table_title": f"{TITLES[kind]}（{period}）",
                        "source_row": str(row), "source_column": str(column), "source_cell_bbox": bbox,
                        "source_locator": (f"PDF page {p}; printed page {printed}; table {table}; "
                                           f"source row {row}; numeric column {column}; quantity {role}; bbox "
                                           + ",".join(map(str,bbox))),
                        "row_label_raw": row_label, "entity_raw": row_label,
                        "column_label_raw": "填答館數" if response else column_label,
                        "entity_kind": ("cooperation_membership_public_category" if kind=="member"
                                        else "published_public_library_type"),
                        "geography_vintage": "臺閩地區原刊館型分類，非縣市面板",
                        "national_libraries_scope": ("association_member_category_public_national_column_excluded"
                                                     if kind=="member" else
                                                     "national_library_separately_listed_not_in_selected_public_subgroup"),
                        "data_year": edition+1910, "period_raw": period,
                        "period_status": "explicit_original_table_ROC_year_exact_dates_unconfirmed",
                        "temporal_kind": "annual_source_reference_exact_period_unconfirmed",
                        "population_scope": population+(suffix if response else ""),
                        "metric_id": f"t{table}-c{column}-{role}",
                        "metric_raw": metric+("／填答館數" if response else ""),
                        "value": value, "value_raw": numeral, "value_status": "reported",
                        "unit": unit, "unit_raw": "填答館數" if response else (column_label if kind=="basic" else None),
                        "unit_status": ("literal_heading_填答館數_identifies_unit_館" if response else
                                        "literal_column_label" if unit else "literal_quantity_unit_unprinted"),
                        "aggregation_role": ("responding_libraries_not_total_libraries" if response else
                                             "published_subtotal" if kind=="counts" and row==7 else
                                             "source_type_quantity"),
                        "source_notes": list(notes),
                        "quality_flags":["AI_visual_review_not_human_collation", "exact_dates_unconfirmed"],
                        "independent_check": check,
                        "source_edition": spec["title"], "source_edition_roc": edition,
                        "physical_source_context": {"complete_cell_literal": full_text,
                                                    "quantity_role": role,
                                                    "source_printed_response_parenthesized": len(tokens)==2,
                                                    "is_total_library_count": False if response else None,
                                                    "raw_values_before_normalization": [t[3][0] for t in tokens],
                                                    "labels_review": "AI original PDF page visual check; not human collation",
                                                    "source_row_index_scope": ("selected_public_subgroup" if kind=="counts"
                                                                               else "whole_table_data_rows")},
                    })
            table,p,printed,(left,right),ys,labels = spec["counts"]
            for i,label in enumerate(labels,1):
                notes = ["公共圖書館區塊含公立與私立，國家圖書館另列；小計為原刊所印。"]
                if edition == 92:
                    notes.append("此表註明大學圖書館不含分館；未直接說明本公共館數分館口徑。")
                else:
                    notes.append("原表註明除大專校院外其餘館型均包含分館。")
                    notes.append("本頁頁眉誤印九十二年卷；卷別依官方目錄及統計章，資料年依表176。")
                emit("counts",table,p,printed,i,1,label,None,"圖書館數量",
                     "臺閩地區原表公共圖書館區塊／"+label, notes,
                     [("primary",(left,ys[i-1],right,ys[i]),None)])
            table,p,printed,xs,ys = spec["basic"]
            for row,(label,(top,split,bottom)) in enumerate(zip(("公立公共圖書館","私立公共圖書館"),ys),2):
                for col,(metric,unit) in enumerate(METRICS,1):
                    notes = ["原格含主值與括號填答館數；填答館數非總館數，原註分館資料併總館。"]
                    notes.append("資料來源為教育部統計處。" if row==2 else "資料來源為國家圖書館。")
                    emit("basic",table,p,printed,row,col,label,metric,metric,label+"／"+metric,notes,
                         [("primary",(xs[col-1],top,xs[col],split),unit),
                          ("responding_libraries",(xs[col-1],split,xs[col],bottom),"館")])
            table,p,printed,bbox = spec["member"]
            emit("member",table,p,printed,1,2,"數量","公共","公共類會員數量",
                 "中華圖書資訊館際合作協會公共類會員",
                 ["此為協會會員，不能當完整公共館總量。公私立、分館和生效日未明。"],
                 [("primary",bbox,None)])
    finally:
        pdf.close()
    assert len(cells)==24 and len({c["physical_cell_id"] for c in cells})==16
    assert len({c["cell_id"] for c in cells})==24
    return document,cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source92", type=Path, required=True)
    parser.add_argument("--source93", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0,str(args.project/"scripts"))
    from build_discovered_20261028 import adapt
    documents, cells, rows = [], [], []
    columns = json.loads((args.project/"scripts/discovered_20261028_canonical_columns.json").read_text())["columns"]
    for edition,source in [(92,args.source92),(93,args.source93)]:
        document,batch = extract(edition,source)
        documents.append(document)
        for cell in batch:
            row = adapt(cell,document)
            assert set(row) <= set(columns)
            row["value_parse_rule"] = "separate_literal_quantity_in_same_physical_cell; original_full_cell_and_response_role_in_source_time_reference"
            row["unit_basis"] = "literal_column_label" if row["unit"] else "no_independent_unit_printed; counting_object_in_caption_and_population"
            rows.append({field:row.get(field) for field in columns})
            cells.append({**cell,"observation_id":row["observation_id"],"source_id":row["source_id"]})
    assert len(rows)==48 and len({r["observation_id"] for r in rows})==48
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"documents.json").write_text(json.dumps({"documents":documents},ensure_ascii=False,indent=2)+"\n")
    (args.out/"source_cells.json").write_text(json.dumps({"physical_cells":32,"numeric_positions":48,"cells":cells},ensure_ascii=False,indent=2)+"\n")
    with (args.out/"observations.jsonl").open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row,ensure_ascii=False)+"\n")
    print(json.dumps({"observations":48,"physical_cells":32,"years":[2002,2003],
                      "source_units_unprinted":16,"human_double_collation_completed":False}))
if __name__ == "__main__":
    main()
