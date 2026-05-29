import json
import zipfile
from deepdiff import DeepDiff
from pathlib import Path


# ─── Main Report Comparator ───────────────────────────────────
def compare_report(old_path: Path, new_path: Path) -> dict:
    """
    Compares two .pbix files at the definition/pages level.
    Reads report.json, page.json, and each visual.json individually.
    """
    print(f"[report] Reading old report definition ...")
    old_def = _read_report_definition(old_path)

    print(f"[report] Reading new report definition ...")
    new_def = _read_report_definition(new_path)

    print("[report] Running comparison ...")

    results = {
        "pages_added":      _get_pages_added(old_def, new_def),
        "pages_removed":    _get_pages_removed(old_def, new_def),
        "visuals_modified": _get_visuals_modified(old_def, new_def),
        "filters_changed":  _get_filters_changed(old_def, new_def),
        "fields_changed":   _get_fields_changed(old_def, new_def),
    }

    _print_summary(results)
    return results


# ─── Read Full Definition from Extracted Folder ───────────────
def _read_report_definition(base_path: Path) -> dict:
    """
    Reads all definition JSONs from the extracted .pbix folder.
    Builds a structured dict:
    {
        "report": {...},               # report.json
        "pages": {
            "page_id": {
                "meta": {...},         # page.json
                "visuals": {
                    "visual_id": {...} # visual.json
                }
            }
        }
    }
    """
    definition = {"report": {}, "pages": {}}

    report_json = base_path / "Report" / "definition" / "report.json"
    if report_json.exists():
        definition["report"] = _load_json(report_json)

    pages_dir = base_path / "Report" / "definition" / "pages"
    if not pages_dir.exists():
        print(f"[report] WARNING: No pages directory found at {pages_dir}")
        return definition

    for page_dir in sorted(pages_dir.iterdir()):
        if not page_dir.is_dir():
            continue

        page_id = page_dir.name
        page_data = {"meta": {}, "visuals": {}}

        # Read page.json
        page_json = page_dir / "page.json"
        if page_json.exists():
            page_data["meta"] = _load_json(page_json)

        # Read each visual.json
        visuals_dir = page_dir / "visuals"
        if visuals_dir.exists():
            for visual_dir in sorted(visuals_dir.iterdir()):
                if not visual_dir.is_dir():
                    continue
                visual_json = visual_dir / "visual.json"
                if visual_json.exists():
                    page_data["visuals"][visual_dir.name] = _load_json(visual_json)

        definition["pages"][page_id] = page_data

    return definition


# ─── Page Changes ─────────────────────────────────────────────
def _get_page_display_names(definition: dict) -> dict:
    """Returns {page_id: display_name} mapping."""
    names = {}
    for page_id, page_data in definition.get("pages", {}).items():
        meta = page_data.get("meta", {})
        names[page_id] = meta.get("displayName", page_id)
    return names


def _get_pages_added(old: dict, new: dict) -> list:
    old_ids = set(old["pages"].keys())
    new_ids = set(new["pages"].keys())
    added = new_ids - old_ids
    new_names = _get_page_display_names(new)
    result = [new_names.get(pid, pid) for pid in added]
    if result:
        print(f"[report] Pages added: {result}")
    return sorted(result)


def _get_pages_removed(old: dict, new: dict) -> list:
    old_ids = set(old["pages"].keys())
    new_ids = set(new["pages"].keys())
    removed = old_ids - new_ids
    old_names = _get_page_display_names(old)
    result = [old_names.get(pid, pid) for pid in removed]
    if result:
        print(f"[report] Pages removed: {result}")
    return sorted(result)


# ─── Visual Changes ───────────────────────────────────────────
def _get_visuals_modified(old: dict, new: dict) -> list:
    """
    Compares each visual.json across matching pages.
    Detects: visual type changes, position changes, query changes.
    """
    modified = []
    common_pages = set(old["pages"].keys()) & set(new["pages"].keys())

    for page_id in sorted(common_pages):
        old_visuals = old["pages"][page_id].get("visuals", {})
        new_visuals = new["pages"][page_id].get("visuals", {})
        page_name = old["pages"][page_id].get("meta", {}).get("displayName", page_id)

        all_visual_ids = set(old_visuals.keys()) | set(new_visuals.keys())

        for vid in sorted(all_visual_ids):
            old_v = old_visuals.get(vid)
            new_v = new_visuals.get(vid)

            if old_v is None:
                modified.append({
                    "page":        page_name,
                    "visual_id":   vid,
                    "status":      "added",
                    "visual_type": new_v.get("visual", {}).get("visualType", "unknown"),
                    "changes":     {}
                })
                continue

            if new_v is None:
                modified.append({
                    "page":        page_name,
                    "visual_id":   vid,
                    "status":      "removed",
                    "visual_type": old_v.get("visual", {}).get("visualType", "unknown"),
                    "changes":     {}
                })
                continue

            # Compare visual type
            old_type = old_v.get("visual", {}).get("visualType", "")
            new_type = new_v.get("visual", {}).get("visualType", "")

            # Compare query/fields
            diff = DeepDiff(old_v, new_v, ignore_order=True, exclude_paths=[
                "root['position']"  # ignore position-only moves
            ])

            if diff:
                changes = {}

                if old_type != new_type:
                    changes["visual_type"] = {
                        "old": old_type,
                        "new": new_type
                    }

                if "values_changed" in diff:
                    changes["property_changes"] = diff["values_changed"]

                if "iterable_item_added" in diff:
                    changes["fields_added"] = diff["iterable_item_added"]

                if "iterable_item_removed" in diff:
                    changes["fields_removed"] = diff["iterable_item_removed"]

                if "dictionary_item_added" in diff:
                    changes["config_added"] = diff["dictionary_item_added"]

                if "dictionary_item_removed" in diff:
                    changes["config_removed"] = diff["dictionary_item_removed"]

                modified.append({
                    "page":        page_name,
                    "visual_id":   vid,
                    "status":      "modified",
                    "visual_type": new_type,
                    "changes":     changes
                })

    return modified


# ─── Filter Changes ───────────────────────────────────────────
def _get_filters_changed(old: dict, new: dict) -> list:
    changed = []
    common_pages = set(old["pages"].keys()) & set(new["pages"].keys())

    for page_id in sorted(common_pages):
        page_name = old["pages"][page_id].get("meta", {}).get("displayName", page_id)
        old_visuals = old["pages"][page_id].get("visuals", {})
        new_visuals = new["pages"][page_id].get("visuals", {})

        for vid in set(old_visuals.keys()) & set(new_visuals.keys()):
            old_filters = old_visuals[vid].get("filterConfig", {}).get("filters", [])
            new_filters = new_visuals[vid].get("filterConfig", {}).get("filters", [])

            diff = DeepDiff(old_filters, new_filters, ignore_order=True)
            if diff:
                changed.append({
                    "page":      page_name,
                    "visual_id": vid,
                    "diff":      diff
                })

    return changed


# ─── Field/Column Changes ─────────────────────────────────────
def _get_fields_changed(old: dict, new: dict) -> list:
    """
    Specifically detects column/field swaps inside visual queries.
    e.g. CustomerID replaced with CustomerName
    """
    changed = []
    common_pages = set(old["pages"].keys()) & set(new["pages"].keys())

    for page_id in sorted(common_pages):
        page_name = old["pages"][page_id].get("meta", {}).get("displayName", page_id)
        old_visuals = old["pages"][page_id].get("visuals", {})
        new_visuals = new["pages"][page_id].get("visuals", {})

        for vid in set(old_visuals.keys()) & set(new_visuals.keys()):
            old_fields = _extract_fields(old_visuals[vid])
            new_fields = _extract_fields(new_visuals[vid])

            if old_fields != new_fields:
                added   = [f for f in new_fields if f not in old_fields]
                removed = [f for f in old_fields if f not in new_fields]
                if added or removed:
                    changed.append({
                        "page":          page_name,
                        "visual_id":     vid,
                        "fields_added":  added,
                        "fields_removed": removed
                    })

    return changed


def _extract_fields(visual: dict) -> list:
    """Extracts all field/column references from a visual's query projections."""
    fields = []
    try:
        query_state = visual.get("visual", {}).get("query", {}).get("queryState", {})
        for bucket, bucket_data in query_state.items():
            for proj in bucket_data.get("projections", []):
                ref = proj.get("queryRef", proj.get("nativeQueryRef", ""))
                if ref:
                    fields.append(ref)
    except Exception:
        pass
    return fields


# ─── JSON Loader ──────────────────────────────────────────────
def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Console Summary ──────────────────────────────────────────
def _print_summary(results: dict) -> None:
    print("\n── Report Comparison Summary ─────────────────────")
    print(f"  Pages Added:       {len(results['pages_added'])}")
    print(f"  Pages Removed:     {len(results['pages_removed'])}")
    print(f"  Visuals Modified:  {len(results['visuals_modified'])}")
    print(f"  Filters Changed:   {len(results['filters_changed'])}")
    print(f"  Fields Changed:    {len(results['fields_changed'])}")
    print("──────────────────────────────────────────────────\n")