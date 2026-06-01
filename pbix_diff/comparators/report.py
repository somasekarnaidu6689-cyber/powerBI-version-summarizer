import json
from deepdiff import DeepDiff
from pathlib import Path


def compare_report(old_path: Path, new_path: Path) -> dict:
    print("[report] Reading old report definition ...")
    old_def = _read_report_definition(old_path)
    print("[report] Reading new report definition ...")
    new_def = _read_report_definition(new_path)

    print("[report] Running comparison ...")

    old_page_ids = set(old_def["pages"].keys())
    new_page_ids = set(new_def["pages"].keys())

    added_ids   = new_page_ids - old_page_ids
    removed_ids = old_page_ids - new_page_ids
    common_ids  = old_page_ids & new_page_ids

    pages_added   = []
    pages_removed = []
    pages_changed = []

    # ── New pages — show all visuals as added ─────────────────
    for pid in sorted(added_ids):
        page = new_def["pages"][pid]
        pages_added.append({
            "id":           pid,
            "name":         page["meta"].get("displayName", pid),
            "display_name": page["meta"].get("displayName", pid),
            "visuals":      _all_visuals_as_added(page["visuals"]),
            "filters":      page["meta"].get("filters", []),
        })
        print(f"[report] Page added: {page['meta'].get('displayName', pid)}")

    # ── Removed pages — show all visuals as removed ───────────
    for pid in sorted(removed_ids):
        page = old_def["pages"][pid]
        pages_removed.append({
            "id":           pid,
            "name":         page["meta"].get("displayName", pid),
            "display_name": page["meta"].get("displayName", pid),
            "visuals":      _all_visuals_as_removed(page["visuals"]),
        })
        print(f"[report] Page removed: {page['meta'].get('displayName', pid)}")

    # ── Existing pages — show only what changed ───────────────
    for pid in sorted(common_ids):
        old_page = old_def["pages"][pid]
        new_page = new_def["pages"][pid]
        page_name = new_page["meta"].get("displayName", pid)

        changed_visuals = _compare_page_visuals(
            old_page["visuals"], new_page["visuals"]
        )
        filter_diff = _compare_filters(
            old_page["meta"].get("filters", []),
            new_page["meta"].get("filters", [])
        )
        page_setting_diff = _compare_page_settings(
            old_page["meta"], new_page["meta"]
        )

        if changed_visuals or filter_diff or page_setting_diff:
            pages_changed.append({
                "id":              pid,
                "name":            page_name,
                "display_name":    page_name,
                "visuals_changed": changed_visuals,
                "filters_changed": filter_diff,
                "settings_changed":page_setting_diff,
            })

    results = {
        "pages_added":   pages_added,
        "pages_removed": pages_removed,
        "pages_changed": pages_changed,
        # Legacy keys for summary counts
        "pages_added_names":   [p["name"] for p in pages_added],
        "pages_removed_names": [p["name"] for p in pages_removed],
        "visuals_modified":    [],
        "filters_changed":     [],
        "fields_changed":      [],
    }

    _print_summary(results)
    return results


# ─── Read Definition ──────────────────────────────────────────
def _read_report_definition(base_path: Path) -> dict:
    definition = {"report": {}, "pages": {}}

    definition_dir = None
    for candidate in [
        base_path / "definition",
        base_path / "Report" / "definition",
    ]:
        if candidate.exists():
            definition_dir = candidate
            break

    if not definition_dir:
        print(f"[report] WARNING: No definition/ found under {base_path}")
        return definition

    report_json = definition_dir / "report.json"
    if report_json.exists():
        definition["report"] = _load_json(report_json)

    pages_dir = definition_dir / "pages"
    if not pages_dir.exists():
        print(f"[report] WARNING: No pages/ found at {pages_dir}")
        return definition

    for page_dir in sorted(pages_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        page_id   = page_dir.name
        page_data = {"meta": {}, "visuals": {}}

        page_json = page_dir / "page.json"
        if page_json.exists():
            page_data["meta"] = _load_json(page_json)

        visuals_dir = page_dir / "visuals"
        if visuals_dir.exists():
            for vf in sorted(visuals_dir.iterdir()):
                visual_json = (vf / "visual.json") if vf.is_dir() else vf
                if visual_json.exists() and visual_json.suffix == ".json":
                    vid = vf.stem if vf.is_dir() else vf.stem
                    data = _load_json(visual_json)
                    page_data["visuals"][vid] = data

        definition["pages"][page_id] = page_data

    return definition


# ─── Visual Comparisons ───────────────────────────────────────
def _all_visuals_as_added(visuals: dict) -> list:
    result = []
    for vid, v in visuals.items():
        vtype = v.get("visual", {}).get("visualType", "unknown")
        fields = _extract_fields(v)
        result.append({
            "visual_id":   vid,
            "visual_type": vtype,
            "status":      "added",
            "fields":      fields,
            "changes":     {}
        })
    return result


def _all_visuals_as_removed(visuals: dict) -> list:
    result = []
    for vid, v in visuals.items():
        vtype = v.get("visual", {}).get("visualType", "unknown")
        fields = _extract_fields(v)
        result.append({
            "visual_id":   vid,
            "visual_type": vtype,
            "status":      "removed",
            "fields":      fields,
            "changes":     {}
        })
    return result


def _compare_page_visuals(old_visuals: dict, new_visuals: dict) -> list:
    result = []
    all_ids = set(old_visuals) | set(new_visuals)

    for vid in sorted(all_ids):
        old_v = old_visuals.get(vid)
        new_v = new_visuals.get(vid)

        if old_v is None:
            result.append({
                "visual_id":   vid,
                "visual_type": new_v.get("visual", {}).get("visualType", "unknown"),
                "status":      "added",
                "fields":      _extract_fields(new_v),
                "changes":     {}
            })
        elif new_v is None:
            result.append({
                "visual_id":   vid,
                "visual_type": old_v.get("visual", {}).get("visualType", "unknown"),
                "status":      "removed",
                "fields":      _extract_fields(old_v),
                "changes":     {}
            })
        else:
            old_type = old_v.get("visual", {}).get("visualType", "")
            new_type = new_v.get("visual", {}).get("visualType", "")

            diff = DeepDiff(old_v, new_v, ignore_order=True,
                            exclude_paths=["root['position']"])
            if diff:
                changes = {}
                if old_type != new_type:
                    changes["visual_type"] = {"old": old_type, "new": new_type}
                if "values_changed" in diff:
                    changes["property_changes"] = {
                        k: {"old_value": v.get("old_value"), "new_value": v.get("new_value")}
                        for k, v in diff["values_changed"].items()
                    }
                if "iterable_item_added" in diff:
                    changes["fields_added"] = diff["iterable_item_added"]
                if "iterable_item_removed" in diff:
                    changes["fields_removed"] = diff["iterable_item_removed"]

                old_fields = _extract_fields(old_v)
                new_fields = _extract_fields(new_v)
                if old_fields != new_fields:
                    changes["field_swap"] = {
                        "removed": [f for f in old_fields if f not in new_fields],
                        "added":   [f for f in new_fields if f not in old_fields],
                    }

                result.append({
                    "visual_id":   vid,
                    "visual_type": new_type,
                    "status":      "modified",
                    "fields":      new_fields,
                    "changes":     changes
                })
    return result


def _compare_filters(old_filters, new_filters) -> dict:
    if isinstance(old_filters, str):
        try: old_filters = json.loads(old_filters)
        except: old_filters = []
    if isinstance(new_filters, str):
        try: new_filters = json.loads(new_filters)
        except: new_filters = []
    diff = DeepDiff(old_filters, new_filters, ignore_order=True)
    return {k: v for k, v in diff.items()} if diff else {}


def _compare_page_settings(old_meta: dict, new_meta: dict) -> dict:
    changes = {}
    for key in ["width", "height", "displayOption", "background", "displayName"]:
        if old_meta.get(key) != new_meta.get(key):
            changes[key] = {"old": old_meta.get(key), "new": new_meta.get(key)}
    return changes


def _extract_fields(visual: dict) -> list:
    fields = []
    try:
        qs = visual.get("visual", {}).get("query", {}).get("queryState", {})
        for bucket, data in qs.items():
            for proj in data.get("projections", []):
                ref = proj.get("queryRef", proj.get("nativeQueryRef", ""))
                if ref:
                    fields.append(ref)
    except Exception:
        pass
    return fields


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _print_summary(r: dict):
    print("\n── Report Comparison Summary ─────────────────────")
    print(f"  Pages Added:    {len(r['pages_added'])}")
    print(f"  Pages Removed:  {len(r['pages_removed'])}")
    print(f"  Pages Changed:  {len(r['pages_changed'])}")
    print("──────────────────────────────────────────────────\n")