from pathlib import Path


# ─── Main Reporter ────────────────────────────────────────────

def generate_report(
    model_results: dict,
    report_results: dict,
    layout_results: dict,
) -> None:
    """
    Aggregates results from all comparators and prints a console summary.
    """
    print_summary(model_results, report_results, layout_results)


# ─── Console Summary ──────────────────────────────────────────
def print_summary(
    model_results: dict,
    report_results: dict,
    layout_results: dict
) -> None:
    """
    Prints a formatted summary of all changes to the console.
    """
    print("\n")
    print("=" * 52)
    print("   POWER BI VERSION COMPARISON — SUMMARY")
    print("=" * 52)

    # Model
    if model_results:
        print("\n📊 DATA MODEL")
        print(f"  Tables Added       : {len(model_results.get('tables_added', []))}")
        print(f"  Tables Removed     : {len(model_results.get('tables_removed', []))}")
        print(f"  Columns Added      : {len(model_results.get('columns_added', []))}")
        print(f"  Columns Removed    : {len(model_results.get('columns_removed', []))}")
        print(f"  Measures Changed   : {len(model_results.get('measures_modified', []))}")
        rel = model_results.get("relationships", {})
        print(f"  Relationship Diff  : {sum(len(v) for v in rel.values())}")
    else:
        print("\n📊 DATA MODEL        : Skipped")

    # Report
    if report_results:
        print("\n📄 REPORT")
        print(f"  Pages Added        : {len(report_results.get('pages_added', []))}")
        print(f"  Pages Removed      : {len(report_results.get('pages_removed', []))}")
        print(f"  Visuals Modified   : {len(report_results.get('visuals_modified', []))}")
        print(f"  Filters Changed    : {len(report_results.get('filters_changed', []))}")
        print(f"  Slicers Changed    : {len(report_results.get('slicers_changed', []))}")
    else:
        print("\n📄 REPORT            : Skipped")

    # Layout
    if layout_results:
        print("\n🎨 LAYOUT")
        print(f"  Canvas Changes     : {len(layout_results.get('canvas_settings', []))}")
        bm = layout_results.get("bookmarks", {})
        print(f"  Bookmark Changes   : {sum(len(v) for v in bm.values())}")
        print(f"  Z-Order Changes    : {len(layout_results.get('z_order', []))}")
    else:
        print("\n🎨 LAYOUT            : Skipped")

    print("\n" + "=" * 52)

    total = _count_total_changes(model_results, report_results, layout_results)
    if total == 0:
        print("  ✅ No changes detected between the two versions.")
    else:
        print(f"  ⚠️  Total changes detected: {total}")

    print("=" * 52 + "\n")


# ─── Helpers ──────────────────────────────────────────────────
def _count_total_changes(
    model_results: dict,
    report_results: dict,
    layout_results: dict
) -> int:
    total = 0

    if model_results:
        total += len(model_results.get("tables_added", []))
        total += len(model_results.get("tables_removed", []))
        total += len(model_results.get("columns_added", []))
        total += len(model_results.get("columns_removed", []))
        total += len(model_results.get("measures_modified", []))
        rel = model_results.get("relationships", {})
        total += sum(len(v) for v in rel.values())

    if report_results:
        total += len(report_results.get("pages_added", []))
        total += len(report_results.get("pages_removed", []))
        total += len(report_results.get("visuals_modified", []))
        total += len(report_results.get("filters_changed", []))
        total += len(report_results.get("slicers_changed", []))

    if layout_results:
        total += len(layout_results.get("canvas_settings", []))
        bm = layout_results.get("bookmarks", {})
        total += sum(len(v) for v in bm.values())
        total += len(layout_results.get("z_order", []))

    return total
