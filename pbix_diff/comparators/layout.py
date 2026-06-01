from deepdiff import DeepDiff
from pathlib import Path
from large_file_handler import smart_load
import config


# ─── Main Layout Comparator ───────────────────────────────────
def compare_layout(old_path: Path, new_path: Path) -> dict:
    if not config.INCLUDE_LAYOUT_DIFF:
        print("[layout] Skipping layout diff (disabled in config)")
        return {}

    # If given a folder (extracted pbix), point to report.json inside it
    def resolve_report_json(p: Path) -> Path:
        if p.is_dir():
            candidates = [
                p / "definition" / "report.json",            # .pbip Report folder
                p / "Report" / "definition" / "report.json", # extracted .pbix
            ]
            for c in candidates:
                if c.exists():
                    return c
            raise FileNotFoundError(f"[layout] report.json not found in: {p}")
        return p

    old_report_path = resolve_report_json(old_path)
    new_report_path = resolve_report_json(new_path)

    print(f"[layout] Loading old report: {old_report_path.name}")
    old = smart_load(old_report_path)

    print(f"[layout] Loading new report: {new_report_path.name}")
    new = smart_load(new_report_path)

    print("[layout] Running layout comparison ...")

    results = {
        "canvas_settings": _get_canvas_changes(old, new),
        "bookmarks":       _get_bookmark_changes(old, new),
        "z_order":         _get_zorder_changes(old, new),
    }

    _print_summary(results)
    return results


# ─── Canvas Settings ──────────────────────────────────────────
def _get_canvas_settings(report: dict) -> dict:
    """
    Extracts canvas width, height, and display settings
    from each page in the report.
    """
    canvas_map = {}
    for page in report.get("sections", []):
        page_name = page.get("displayName", page.get("name", "unknown"))
        canvas_map[page_name] = {
            "width":         page.get("width", None),
            "height":        page.get("height", None),
            "displayOption": page.get("displayOption", None),
            "background":    page.get("background", None),
        }
    return canvas_map


def _get_canvas_changes(old: dict, new: dict) -> list:
    old_canvas = _get_canvas_settings(old)
    new_canvas = _get_canvas_settings(new)
    changes = []

    all_pages = set(old_canvas) | set(new_canvas)
    for page in sorted(all_pages):
        diff = DeepDiff(
            old_canvas.get(page, {}),
            new_canvas.get(page, {}),
            ignore_order=True
        )
        if diff:
            changes.append({
                "page":    page,
                "changes": {
                    "modified": diff.get("values_changed", {}),
                    "added":    diff.get("dictionary_item_added", {}),
                    "removed":  diff.get("dictionary_item_removed", {}),
                }
            })
            print(f"[layout] Canvas changed on page: {page}")

    return changes


# ─── Bookmark Changes ─────────────────────────────────────────
def _get_bookmarks(report: dict) -> list:
    """
    Extracts bookmarks from the report config.
    Bookmarks are stored at the report level, not per page.
    """
    import json
    config_raw = report.get("config", {})
    if isinstance(config_raw, str):
        try:
            config_raw = json.loads(config_raw)
        except Exception:
            return []
    return config_raw.get("bookmarks", [])


def _get_bookmark_changes(old: dict, new: dict) -> dict:
    old_bookmarks = _get_bookmarks(old)
    new_bookmarks = _get_bookmarks(new)

    diff = DeepDiff(old_bookmarks, new_bookmarks, ignore_order=True)

    changes = {
        "added":    diff.get("iterable_item_added", {}),
        "removed":  diff.get("iterable_item_removed", {}),
        "modified": diff.get("values_changed", {}),
    }

    total = sum(len(v) for v in changes.values())
    if total:
        print(f"[layout] Bookmark changes detected: {total}")

    return changes


# ─── Z-Order Changes ──────────────────────────────────────────
def _get_zorder(report: dict) -> dict:
    """
    Extracts z-order (layering) of visuals per page.
    Z-order determines which visuals appear on top of others.
    """
    zorder_map = {}
    for page in report.get("sections", []):
        page_name = page.get("displayName", page.get("name", "unknown"))
        zorder_map[page_name] = [
            {
                "z": visual.get("z", None),
                "x": visual.get("x", None),
                "y": visual.get("y", None),
            }
            for visual in page.get("visualContainers", [])
        ]
    return zorder_map


def _get_zorder_changes(old: dict, new: dict) -> list:
    old_zorder = _get_zorder(old)
    new_zorder = _get_zorder(new)
    changes = []

    all_pages = set(old_zorder) | set(new_zorder)
    for page in sorted(all_pages):
        diff = DeepDiff(
            old_zorder.get(page, []),
            new_zorder.get(page, []),
            ignore_order=False  # Order matters for z-order
        )
        if diff:
            changes.append({
                "page":    page,
                "changes": {
                    "modified": diff.get("values_changed", {}),
                    "added":    diff.get("iterable_item_added", {}),
                    "removed":  diff.get("iterable_item_removed", {}),
                }
            })
            print(f"[layout] Z-order changed on page: {page}")

    return changes


# ─── Console Summary ──────────────────────────────────────────
def _print_summary(results: dict) -> None:
    print("\n── Layout Comparison Summary ─────────────────────")
    print(f"  Canvas Changes:    {len(results['canvas_settings'])}")
    print(f"  Bookmark Changes:  {sum(len(v) for v in results['bookmarks'].values())}")
    print(f"  Z-Order Changes:   {len(results['z_order'])}")
    print("──────────────────────────────────────────────────\n")