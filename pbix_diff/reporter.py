from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import config
import os


# ─── Main Reporter ────────────────────────────────────────────
def generate_report(
    model_results: dict,
    report_results: dict,
    layout_results: dict,
    old_path: Path,
    new_path: Path,
    fmt: str,
    duration_seconds: float = None
) -> None:
    """
    Aggregates results from all comparators and produces:
    1. Console summary
    2. HTML report (via Jinja2)
    """
    print_summary(model_results, report_results, layout_results)
    write_html(
        model_results,
        report_results,
        layout_results,
        old_path,
        new_path,
        fmt,
        duration_seconds
    )


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

    # No changes check
    total = _count_total_changes(model_results, report_results, layout_results)
    if total == 0:
        print("  ✅ No changes detected between the two versions.")
    else:
        print(f"  ⚠️  Total changes detected: {total}")

    print("=" * 52 + "\n")


# ─── HTML Report Writer ───────────────────────────────────────
def write_html(
    model_results: dict,
    report_results: dict,
    layout_results: dict,
    old_path: Path,
    new_path: Path,
    fmt: str,
    duration_seconds: float = None
) -> None:
    """
    Renders the Jinja2 HTML template and writes the report
    to the output path defined in config.
    """
    print(f"[reporter] Generating HTML report → {config.OUTPUT_HTML}")

    # Load Jinja2 template from templates/ folder
    BASE_DIR = Path(__file__).resolve().parent
    env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))
    template = env.get_template("report.html")

    # Build context for the template
    context = {
        "generated_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "old_path":       str(old_path),
        "new_path":       str(new_path),
        "format":         fmt,
        "environment":    config.ENVIRONMENT,
        "duration":       f"{duration_seconds:.2f}s" if duration_seconds else "N/A",
        "dbx_warning":    _should_warn_dbx(old_path, new_path),
        "model":          model_results or {},
        "report":         report_results or {},
        "layout":         layout_results or {},
        "total_changes":  _count_total_changes(model_results, report_results, layout_results),
    }

    # Render and write
    html_output = template.render(**context)
    config.OUTPUT_HTML.write_text(html_output, encoding="utf-8")
    print(f"[reporter] ✅ HTML report saved to: {config.OUTPUT_HTML}")


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


def _should_warn_dbx(old_path: Path, new_path: Path) -> str | None:
    """
    Returns a warning message if running on Databricks
    with small files — better to run locally.
    """
    if config.ENVIRONMENT != "databricks" or not config.DBX_WARN_SMALL_FILES:
        return None

    old_mb = old_path.stat().st_size / (1024 * 1024)
    new_mb = new_path.stat().st_size / (1024 * 1024)

    if old_mb < 20 or new_mb < 20:
        return (
            f"⚠️ Files are small ({old_mb:.1f} MB / {new_mb:.1f} MB). "
            f"Consider running locally to save Databricks credits."
        )
    return None