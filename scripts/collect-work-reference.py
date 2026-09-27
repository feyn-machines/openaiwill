#!/usr/bin/env python3
"""Collect versioned work reference data locally; never publish or score it.

Uses only the Python standard library. Raw archives and normalized records live
under ignored root data/. The public manifest contains provenance and counts.
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
from html import unescape
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "31.0"
ONET = "https://www.onetcenter.org"
ONLINE = "https://www.onetonline.org"
ISIC_URL = "https://unstats.un.org/unsd/classifications/Econ/Download/In%20Text/ISIC_Rev_5_english_structure.csv"
ISIC_NOTES_URL = "https://unstats.un.org/unsd/classifications/Econ/Download/In%20Text/ISIC5_Exp_Notes_11Mar2024.xlsx"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def table(data):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def source_options(html):
    options = re.findall(r'<option[^>]*value="(\d+)"[^>]*>(.*?)</option>', html, re.S)
    return [(code, unescape(re.sub(r"<[^>]+>", "", label)).strip()) for code, label in options if code != "0"]


def isic_notes(data):
    """Read the seven columns of the official single-sheet explanatory workbook."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        strings = ET.fromstring(book.read("xl/sharedStrings.xml"))
        shared = ["".join(si.itertext()) for si in strings]
        sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        result = {}
        for row in sheet.findall("s:sheetData/s:row", ns)[1:]:
            values = {}
            for cell in row.findall("s:c", ns):
                value = cell.find("s:v", ns)
                if value is None:
                    continue
                text = shared[int(value.text)] if cell.get("t") == "s" else value.text
                values[re.sub(r"\d+", "", cell.get("r"))] = text.replace("_x000D_", "\n")
            full_code = values["A"]
            code = full_code[1:] if len(full_code) > 1 else full_code
            if code in result:
                raise ValueError(f"Duplicate ISIC explanatory code: {code}")
            result[code] = {"source_title": values["C"], "introductory_text_en": values.get("D"),
                            "includes_en": values.get("E"), "includes_also_en": values.get("F"),
                            "excludes_en": values.get("G")}
        return result


class Archive:
    def __init__(self, base, offline):
        self.base = base
        self.raw = base / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.manifest_file = base / "download-manifest.json"
        self.records = json.loads(self.manifest_file.read_text()) if self.manifest_file.exists() else []
        self.offline = offline

    def fetch(self, name, url):
        path = self.raw / name
        saved = next((r for r in reversed(self.records) if r["file"] == name and r.get("success")), None)
        if saved and path.exists():
            data = path.read_bytes()
            if sha(data) != saved["sha256"]:
                raise ValueError(f"Saved source checksum mismatch: {name}")
            if saved["requested_url"] != url:
                raise ValueError(f"Saved source URL mismatch: {name}")
            return data
        if self.offline:
            raise FileNotFoundError(f"Missing archived source: {name}")
        record = {"file": name, "requested_url": url, "retrieved_at": utc_now()}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; openaiwill-Research/1.0)"})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
                record.update(url=response.url, content_type=response.headers.get("Content-Type"), status=response.status)
            if name.endswith((".zip", ".xlsx")) and not data.startswith(b"PK"):
                raise ValueError(f"Expected ZIP container: {name}")
            if name.endswith(".csv") and b"<html" in data[:500].lower():
                raise ValueError(f"Expected CSV, got HTML: {name}")
            path.write_bytes(data)
            record.update(success=True, bytes=len(data), sha256=sha(data))
            print(f"Downloaded {name}: {len(data):,} bytes", flush=True)
        except Exception as exc:
            record.update(success=False, error=str(exc))
            raise
        finally:
            self.records.append(record)
            write_json(self.manifest_file, self.records)
        return data


def require(condition, message, checks):
    if not condition:
        raise ValueError(message)
    checks.append({"name": message, "status": "passed"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", default="2026-09-12")
    parser.add_argument("--offline", action="store_true", help="Rebuild only from hash-checked archived files")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.batch):
        parser.error("--batch must use YYYY-MM-DD")
    base = ROOT / "data/reference/work-taxonomy" / args.batch
    archive = Archive(base, args.offline)
    checks = []
    payload = archive.fetch("onet_31_0_csv.zip", ONET + "/dl_files/database/db_31_0_csv.zip")
    archive.fetch("onet_database.html", ONET + "/database.html")
    archive.fetch("onet_license.html", ONET + "/license_db.html")
    archive.fetch("onet_online_license.html", ONLINE + "/help/license")
    archive.fetch("onet_industry_help.html", ONLINE + "/help/online/browse_ind")
    archive.fetch("onet_external_sources.html", ONLINE + "/help/online/datasources")
    industry_html = archive.fetch("onet_industries.html", ONLINE + "/find/industry").decode()
    family_html = archive.fetch("onet_families.html", ONLINE + "/find/family").decode()
    for name in ("task_statements", "occupation_data", "gwas_to_iwas_to_dwas", "tasks_to_dwas"):
        archive.fetch(f"dictionary_{name}.html", f"{ONET}/dictionary/{VERSION}/csv/{name}.html")

    # Read every CSV in the complete archive, checking CRC and row structure.
    tables = {}
    inventory = []
    with zipfile.ZipFile(io.BytesIO(payload)) as zipped:
        require(zipped.testzip() is None, "archive_crc_valid", checks)
        for member in zipped.namelist():
            if not member.endswith(".csv"):
                continue
            data = zipped.read(member)
            rows = table(data)
            require(all(None not in row and all(v is not None for v in row.values()) for row in rows), f"csv_structure:{Path(member).name}", checks)
            name = Path(member).stem
            tables[name] = rows
            inventory.append({"file": member, "rows": len(rows), "sha256": sha(data), "bytes": len(data)})
    occupations = tables["occupation_data"]
    tasks = tables["task_statements"]
    activity_paths = tables["gwas_to_iwas_to_dwas"]
    activity_links = tables["tasks_to_dwas"]
    require(len(occupations) == 1016, "occupation_rows_equal_31_0_release", checks)
    require(len(tasks) == 18838, "task_rows_equal_31_0_dictionary", checks)
    require(len(activity_paths) == 2087, "dwa_rows_equal_31_0_dictionary", checks)
    occupation_by_id = {r["O*NET-SOC Code"]: r for r in occupations}
    task_by_id = {r["Task ID"]: r for r in tasks}
    require(len(occupation_by_id) == len(occupations), "occupation_ids_unique", checks)
    require(len(task_by_id) == len(tasks), "task_ids_unique", checks)
    require(all(r["O*NET-SOC Code"] in occupation_by_id for r in tasks), "task_occupation_refs_exist", checks)
    require(all(r["Title"] == occupation_by_id[r["O*NET-SOC Code"]]["Title"] for r in tasks), "task_occupation_titles_match", checks)

    # Task ratings carry the in-occupation workload signal. Relevance is the share of
    # incumbents who perform the task; importance is a 1-5 rating; frequency is a
    # distribution over seven categories. Incumbents Responding is a sample size, not a weight.
    ratings = tables["task_ratings"]
    require(all(r["Task ID"] in task_by_id for r in ratings), "rating_task_refs_exist", checks)
    require(all(r["O*NET-SOC Code"] == task_by_id[r["Task ID"]]["O*NET-SOC Code"] for r in ratings), "rating_occupation_matches_task", checks)
    require({r["Scale ID"] for r in ratings} == {"IM", "RT", "FT"}, "rating_scales_known", checks)
    importance, relevance, frequency = {}, {}, {}
    for row in ratings:
        value = float(row["Data Value"])
        if row["Scale ID"] == "FT":
            frequency.setdefault(row["Task ID"], {})[row["Category"]] = value
        else:
            target = importance if row["Scale ID"] == "IM" else relevance
            target[row["Task ID"]] = {"value": value, "n": int(row["N"]) if row["N"] else None,
                                      "suppress": row["Recommend Suppress"] == "Y"}
    require(len(importance) == len(relevance) == len(frequency) == 18420, "rated_task_rows_equal_31_0_release", checks)
    require(set(importance) == set(relevance) == set(frequency), "rating_scales_cover_same_tasks", checks)
    require(all(sorted(map(int, v)) == list(range(1, 8)) for v in frequency.values()), "frequency_has_seven_categories", checks)
    require(all(abs(sum(v.values()) - 100) <= 1 for v in frequency.values()), "frequency_distribution_sums_to_100", checks)
    require(all(1 <= v["value"] <= 5 for v in importance.values()), "importance_within_scale", checks)
    require(all(0 <= v["value"] <= 100 for v in relevance.values()), "relevance_within_percentage", checks)
    require(len(set(task_by_id) - set(importance)) == 418, "unrated_tasks_retained_not_dropped", checks)

    families = [{"id": f"onet-family:{code}", "source_code": code, "label_en": label,
                 "source_url": ONLINE + "/find/family", "kind": "occupational_family"}
                for code, label in source_options(family_html)]
    family_ids = {r["source_code"] for r in families}
    require(len(families) == 23, "all_23_job_families_collected", checks)
    require(all(code[:2] in family_ids for code in occupation_by_id), "occupation_family_refs_exist", checks)

    activities = {}
    for row in activity_paths:
        parent_id = None
        for level in ("GWA", "IWA", "DWA"):
            code = row[f"{level} Element ID"]
            item = {"id": f"onet-activity:{code}", "source_id": code, "kind": level,
                    "label_en": row[f"{level} Element Name"], "parent_id": parent_id}
            if code in activities:
                require(activities[code] == item, f"activity_parent_consistent:{code}", checks)
            activities[code] = item
            parent_id = item["id"]
    dwa_ids = {k for k, v in activities.items() if v["kind"] == "DWA"}
    require(all(r["Task ID"] in task_by_id and r["DWA Element ID"] in dwa_ids for r in activity_links), "task_activity_refs_exist", checks)
    require(all(r["O*NET-SOC Code"] == task_by_id[r["Task ID"]]["O*NET-SOC Code"] for r in activity_links), "activity_link_occupation_matches_task", checks)
    require(len({(r["Task ID"], r["DWA Element ID"]) for r in activity_links}) == len(activity_links), "task_activity_edges_unique", checks)
    require({r["Task ID"] for r in activity_links} == set(task_by_id), "every_source_task_has_activity_link", checks)

    industry_options = source_options(industry_html)
    require(len(industry_options) == 20, "all_20_industry_options_present", checks)
    industries, industry_links, unresolved_industry_rows = [], [], []
    for code, label in industry_options:
        page_url = ONLINE + "/find/industry?i=" + code
        html = archive.fetch(f"industry_{code}.html", page_url).decode()
        matches = re.findall(r'<a[^>]*href="([^\"]+\.csv\?[^\"]+)"', html)
        require(len(matches) == 1, f"one_csv_export_for_industry:{code}", checks)
        export_url = urllib.parse.urljoin(ONLINE, unescape(matches[0]))
        parsed_url = urllib.parse.urlparse(export_url)
        require(parsed_url.hostname == "www.onetonline.org" and urllib.parse.parse_qs(parsed_url.query).get("i") == [code], f"industry_export_matches_selected_source:{code}", checks)
        rows = table(archive.fetch(f"industry_{code}.csv", export_url))
        require(bool(rows) and all({"Code", "Occupation", "Employed by this Industry"} <= row.keys() for row in rows), f"industry_export_schema:{code}", checks)
        industries.append({"id": f"onet-industry:{code}", "source_code": code, "label_en": label,
                           "kind": "onet_online_industry_group", "source_url": page_url,
                           "export_url": export_url, "source_row_count": len(rows),
                           "inclusion_rule": "at_least_10_percent_of_occupation_employed_in_industry",
                           "snapshot_batch": args.batch})
        for row_number, row in enumerate(rows, 2):
            if row["Code"] not in occupation_by_id:
                unresolved_industry_rows.append({"industry_id": f"onet-industry:{code}", "source_url": export_url,
                                                "source_row_number": row_number, "source_row": row,
                                                "reason": "source_code_missing" if not row["Code"] else "source_code_absent_from_onet_31_0",
                                                "occupation_id": None})
                continue
            share = row["Employed by this Industry"].removesuffix("%")
            require(share.isdigit() and 10 <= int(share) <= 100, f"industry_share_valid:{code}:{row['Code']}", checks)
            industry_links.append({"industry_id": f"onet-industry:{code}", "occupation_id": f"onet-occupation:{row['Code']}",
                                   "source_occupation_title": row["Occupation"], "occupation_employment_share_percent": int(share),
                                   "share_denominator": "workers_in_this_occupation_not_workers_in_this_industry",
                                   "source_url": export_url,
                                   "is_world_weight": False, "suboccupation_share_may_be_parent_soc_aggregate": True})
    require(len({(r["industry_id"], r["occupation_id"]) for r in industry_links}) == len(industry_links), "industry_occupation_edges_unique", checks)
    require(len(industry_links) + len(unresolved_industry_rows) == sum(r["source_row_count"] for r in industries), "every_industry_source_row_accounted_for", checks)

    # ISIC Rev.5 is a separate economic-activity taxonomy, not a task mapping.
    isic_data = archive.fetch("isic_rev5.csv", ISIC_URL)
    isic_rows = list(csv.DictReader(io.StringIO(isic_data.decode("cp1252"))))
    isic = []
    section = None
    for row in isic_rows:
        code = row["ISIC Rev 5 Code"]
        if code.isalpha():
            section = code
            parent = None
            kind = "section"
        elif len(code) == 2:
            parent, kind = section, "division"
        else:
            parent, kind = code[:-1], {3: "group", 4: "class"}[len(code)]
        isic.append({"id": f"isic5:{code}", "source_code": code, "label_en": row["ISIC Rev 5 Title"],
                     "kind": kind, "parent_id": f"isic5:{parent}" if parent else None})
    isic_ids = {r["id"] for r in isic}
    require(len(isic_ids) == len(isic), "isic_codes_unique", checks)
    require(all(r["parent_id"] is None or r["parent_id"] in isic_ids for r in isic), "isic_parent_refs_exist", checks)
    notes = isic_notes(archive.fetch("isic_rev5_explanatory_notes.xlsx", ISIC_NOTES_URL))
    require(set(notes) == {r["source_code"] for r in isic}, "isic_notes_cover_all_structure_codes", checks)
    require(all(notes[r["source_code"]]["source_title"].strip() == r["label_en"].strip() for r in isic), "isic_notes_titles_match_structure", checks)
    for row in isic:
        row.update({key: value for key, value in notes[row["source_code"]].items() if key != "source_title"})

    task_counts = {}
    for row in tasks:
        code = row["O*NET-SOC Code"]
        task_counts[code] = task_counts.get(code, 0) + 1
    normalized = {
        "job-families": families,
        "occupations": [{"id": f"onet-occupation:{r['O*NET-SOC Code']}", "source_code": r["O*NET-SOC Code"],
                          "family_id": f"onet-family:{r['O*NET-SOC Code'][:2]}", "label_en": r["Title"],
                          "description_en": r["Description"], "source_version": VERSION,
                          "source_task_count": task_counts.get(r["O*NET-SOC Code"], 0),
                          "source_url": ONLINE + "/link/summary/" + r["O*NET-SOC Code"]} for r in occupations],
        "tasks": [{"id": f"onet-task:{r['Task ID']}", "source_task_id": r["Task ID"],
                   "occupation_id": f"onet-occupation:{r['O*NET-SOC Code']}", "statement_en": r["Task"],
                   "task_type": r["Task Type"] or None, "incumbents_responding": int(r["Incumbents Responding"]) if r["Incumbents Responding"] else None,
                   "importance": importance.get(r["Task ID"]), "relevance": relevance.get(r["Task ID"]),
                   "frequency": frequency.get(r["Task ID"]),
                   "source_updated_month": r["Date"], "domain_source": r["Domain Source"], "source_version": VERSION,
                   "record_kind": "source_work_task_not_validated_delivery_scenario"} for r in tasks],
        "work-activities": list(activities.values()),
        "task-activity-links": [{"task_id": f"onet-task:{r['Task ID']}", "activity_id": f"onet-activity:{r['DWA Element ID']}",
                                 "source_updated_month": r["Date"], "domain_source": r["Domain Source"]} for r in activity_links],
        "industries": industries,
        "industry-occupation-links": industry_links,
        "industry-unresolved-rows": unresolved_industry_rows,
        "isic-rev5": isic,
    }
    outputs = []
    for name, records in normalized.items():
        path = base / "normalized" / f"{name}.json"
        write_json(path, records)
        outputs.append({"file": str(path.relative_to(ROOT)), "rows": len(records), "sha256": sha(path.read_bytes())})
    write_json(base / "onet-archive-inventory.json", inventory)
    counts = {name: len(rows) for name, rows in normalized.items()}
    counts.update(occupations_with_tasks=len(task_counts), occupations_without_tasks=len(occupations)-len(task_counts),
                  rated_tasks=len(importance), unrated_tasks=len(tasks)-len(importance),
                  onet_csv_tables=len(inventory), industry_linked_occupations=len({r['occupation_id'] for r in industry_links}),
                  general_work_activities=sum(r['kind']=='GWA' for r in activities.values()),
                  intermediate_work_activities=sum(r['kind']=='IWA' for r in activities.values()),
                  detailed_work_activities=len(dwa_ids),
                  isic_sections=sum(r['kind']=='section' for r in isic),
                  isic_divisions=sum(r['kind']=='division' for r in isic),
                  isic_groups=sum(r['kind']=='group' for r in isic),
                  isic_classes=sum(r['kind']=='class' for r in isic))
    linked_occupation_ids = {r["occupation_id"] for r in industry_links}
    counts["task_occupations_without_industry_links"] = sum(f"onet-occupation:{code}" not in linked_occupation_ids for code in task_counts)
    counts["source_tasks_with_unspecified_type"] = sum(not r["Task Type"] for r in tasks)
    audit = {"id": f"work-reference-validation-{args.batch}", "checked_at": utc_now(), "status": "passed",
             "counts": counts, "checks": checks, "outputs": outputs}
    write_json(base / "validation.json", audit)
    metadata = {
        "id": "work-reference-v1", "version": "1.0.0", "batch": args.batch,
        "status": "collected_source_reference_not_product_scenario_catalog",
        "recommended_primary_dataset": "O*NET 31.0",
        "geographic_scope": {"onet": "United States occupational reference", "isic": "international economic activity classification"},
        "sources": [
            {"id": "onet-31.0", "version": VERSION, "released_month": "2026-08", "url": ONET + "/database.html",
             "download_url": ONET + "/dl_files/database/db_31_0_csv.zip", "license": "CC-BY-4.0",
             "license_url": ONET + "/license_db.html", "completeness": "entire_45_csv_release_archive_parsed"},
            {"id": f"onet-online-industry-{args.batch}", "url": ONLINE + "/find/industry",
             "underlying_source": "BLS Employment Projections 2024-2034", "source_last_updated": "2025-09-16",
             "source_metadata_url": ONLINE + "/help/online/datasources",
             "inclusion_rule": "at_least_10_percent_of_an_occupation_employed_in_industry",
             "completeness": "all_20_available_industry_csv_exports; not_the_full_BLS_matrix",
             "license_note": "BLS external data is separate from the O*NET OnLine CC BY license",
             "copyright_url": "https://www.bls.gov/opub/copyright-information.htm"},
            {"id": "isic-rev5", "url": "https://unstats.un.org/unsd/classifications/Econ",
             "download_url": ISIC_URL, "explanatory_notes_url": ISIC_NOTES_URL,
             "completeness": "all_830_structure_nodes_and_matching_explanatory_rows",
             "publication_status": "structure_and_explanatory_notes_available; UN_publication_forthcoming_at_collection",
             "redistribution_status": "not_confirmed; retained_as_local_research_reference"},
        ],
        "counts": counts,
        "semantic_boundaries": [
            "Industry, occupational family, occupation, work activity and delivery scenario remain different entity types.",
            "Industry-occupation relations are many-to-many employment associations, not subindustry parentage.",
            "O*NET task statements provide work content; they do not supply complete inputs, deliverables or acceptance criteria.",
            "A profession's tasks are not automatically validated as applicable to every associated industry.",
            "ISIC-to-O*NET task mapping has not been created.",
            "No AI ability score, world weight, production baseline or product scenario catalog is generated.",
        ],
        "transformations": ["Original English labels and codes retained; namespaced record IDs added.",
                            "Blank optional task fields become null; source timestamps remain separate from batch date.",
                            "ISIC source CSV decoded from Windows-1252; XLSX escaped carriage returns become newlines.",
                            "Rows with missing or unmatched occupation codes retained separately without inferred IDs."],
        "preserved_existing_reference": "datasets/a16z-industry-reference.v1.json",
        "local_archive": str(base.relative_to(ROOT)), "outputs": outputs,
        "validation": {"status": "passed", "check_count": len(checks), "report": str((base / "validation.json").relative_to(ROOT))},
        "runtime": {"frontend_connected": False, "scoring_connected": False, "published": False},
    }
    write_json(ROOT / "datasets/work-reference.v1.json", metadata)
    print(json.dumps({"status": "passed", "counts": counts, "check_count": len(checks)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
