import argparse
import time
from pathlib import Path

from detector import detect, describe
from extractor import extract, cleanup
from comparators.model import compare_model
from comparators.report import compare_report
from comparators.layout import compare_layout
from reporter import generate_report
import config


# ─── CLI Argument Parser ──────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Power BI Version Comparison Tool",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--old",
        required=True,
        help="Path to the older version of the Power BI file\n"
             "Supports: .pbix, .pbip folder, .bim, .json, .pbir"
    )
    parser.add_argument(
        "--new",
        required=True,
        help="Path to the newer version of the Power BI file"
    )
    parser.add_argument(
        "--output",
        required=False,
        default=str(config.OUTPUT_HTML),
        help=f"Output path for the HTML report (default: {config.OUTPUT_HTML})"
    )
    return parser.parse_args()


# ─── Main Entry Point ─────────────────────────────────────────
def main():
    args = parse_args()

    old_path = Path(args.old)
    new_path = Path(args.new)
    config.OUTPUT_HTML = Path(args.output)

    print("\n" + "=" * 52)
    print("   POWER BI VERSION COMPARISON TOOL")
    print("=" * 52)

    # ── Validate Paths ────────────────────────────────────────
    if not old_path.exists():
        print(f"\n❌ ERROR: Old path does not exist:\n   {old_path}")
        return

    if not new_path.exists():
        print(f"\n❌ ERROR: New path does not exist:\n   {new_path}")
        return

    # ── Detect Format ─────────────────────────────────────────
    print(f"\n[run] Detecting format ...")
    try:
        old_fmt, old_ftype = detect(old_path)
        new_fmt, new_ftype = detect(new_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"\n❌ ERROR: {e}")
        return

    print(f"[run] Old → {describe(old_fmt, old_ftype)}")
    print(f"[run] New → {describe(new_fmt, new_ftype)}")

    # ── Extract Files ─────────────────────────────────────────
    print(f"\n[run] Extracting files ...")
    try:
        old_extracted = extract(old_path, old_fmt, old_ftype)
        new_extracted = extract(new_path, new_fmt, new_ftype)
    except Exception as e:
        print(f"\n❌ ERROR during extraction: {e}")
        return

    old_model  = old_extracted.get("model_path")
    new_model  = new_extracted.get("model_path")
    old_report = old_extracted.get("report_path")
    new_report = new_extracted.get("report_path")

    # ── Start Timer ───────────────────────────────────────────
    start_time = time.time()

    # ── Run Comparators ───────────────────────────────────────
    model_results  = {}
    report_results = {}
    layout_results = {}

    # Model comparison
    # Model comparison
    if old_model and new_model:
        # Skip binary DataModel files — not JSON readable
        if old_model.name == "DataModel" or new_model.name == "DataModel":
            print("[run] Skipping model comparison — DataModel is binary format")
            print("[run] Tip: Use .pbip SemanticModel folder for model diffing")
        else:
            print(f"\n[run] Running model comparison ...")
            try:
                model_results = compare_model(old_model, new_model)
            except Exception as e:
                print(f"[run] ⚠️ Model comparison failed: {e}")
    else:
        print("[run] Skipping model comparison — model file not found in one or both inputs")
    
    # Report comparison
    if old_report and new_report:
        print(f"\n[run] Running report comparison ...")
        try:
            report_results = compare_report(old_report, new_report)
        except Exception as e:
            print(f"[run] ⚠️ Report comparison failed: {e}")
    else:
        print("[run] Skipping report comparison — report file not found in one or both inputs")

    # Layout comparison
    if old_report and new_report and config.INCLUDE_LAYOUT_DIFF:
        print(f"\n[run] Running layout comparison ...")
        try:
            layout_results = compare_layout(old_report, new_report)
        except Exception as e:
            print(f"[run] ⚠️ Layout comparison failed: {e}")

    # ── Stop Timer ────────────────────────────────────────────
    duration = time.time() - start_time
    if config.ENVIRONMENT == "databricks" and config.DBX_LOG_DURATION:
        print(f"\n[run] ⏱ Cluster runtime: {duration:.2f}s")

    # ── Generate Report ───────────────────────────────────────
    print(f"\n[run] Generating report ...")
    try:
        generate_report(
            model_results=model_results,
            report_results=report_results,
            layout_results=layout_results,
            old_path=old_path,
            new_path=new_path,
            fmt=str(old_fmt.value),
            duration_seconds=duration
        )
    except Exception as e:
        print(f"\n❌ ERROR generating report: {e}")
        return

    # ── Cleanup Temp Folders ──────────────────────────────────
    if old_ftype.name == "BINARY_ZIP":
        cleanup(Path("/tmp") / f"pbix_extract_{old_path.stem}")
    if new_ftype.name == "BINARY_ZIP":
        cleanup(Path("/tmp") / f"pbix_extract_{new_path.stem}")

    print("\n✅ Done! Open your report at:")
    print(f"   {config.OUTPUT_HTML}\n")


# ─── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    main()