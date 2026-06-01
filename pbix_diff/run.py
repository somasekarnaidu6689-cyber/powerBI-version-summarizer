import argparse
import time
from pathlib import Path
from ai_summarizer import generate_ai_summary
from exporter import export_pdf, export_excel

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
    parser.add_argument("--no-pdf",   action="store_true", help="Skip PDF export")
    parser.add_argument("--no-excel", action="store_true", help="Skip Excel export")
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
        print(f"\nERROR: Old path does not exist:\n   {old_path}")
        return

    if not new_path.exists():
        print(f"\nERROR: New path does not exist:\n   {new_path}")
        return

    # ── Detect Format ─────────────────────────────────────────
    print(f"\n[run] Detecting format ...")
    try:
        old_fmt, old_ftype = detect(old_path)
        new_fmt, new_ftype = detect(new_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"\nERROR: {e}")
        return

    print(f"[run] Old → {describe(old_fmt, old_ftype)}")
    print(f"[run] New → {describe(new_fmt, new_ftype)}")

    # ── Extract Files ─────────────────────────────────────────
    print(f"\n[run] Extracting files ...")
    try:
        old_extracted = extract(old_path, old_fmt, old_ftype)
        new_extracted = extract(new_path, new_fmt, new_ftype)
    except Exception as e:
        print(f"\n ERROR during extraction: {e}")
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
        # ── AI Summary ────────────────────────────────────────────────
        ai_summary = {}
        if config.ENABLE_AI_SUMMARY and config.GROQ_API_KEY:
            from ai_summarizer import generate_ai_summary
            ai_summary = generate_ai_summary(
                model_results=model_results,
                report_results=report_results,
                layout_results=layout_results,
                api_key=config.GROQ_API_KEY
            )
        generate_report(
            model_results=model_results,
            report_results=report_results,
            layout_results=layout_results,
            old_path=old_path,
            new_path=new_path,
            fmt=str(old_fmt.value),
            duration_seconds=duration,
            ai_summary=ai_summary        # ← add this
        )
    except Exception as e:
        print(f"\n❌ ERROR generating report: {e}")
        return

    # ── Export PDF ────────────────────────────────────────────────
    if not args.no_pdf:
        pdf_path = config.OUTPUT_PATH / "diff_report.pdf"
        try:
            export_pdf(
                model_results=model_results,
                report_results=report_results,
                layout_results=layout_results,
                ai_summary=ai_summary,
                old_path=str(old_path),
                new_path=str(new_path),
                output_path=pdf_path
            )
        except Exception as e:
            print(f"[run] ⚠️ PDF export failed: {e}")

    # ── Export Excel ──────────────────────────────────────────────
    if not args.no_excel:
        excel_path = config.OUTPUT_PATH / "diff_report.xlsx"
        try:
            export_excel(
                model_results=model_results,
                report_results=report_results,
                old_path=str(old_path),
                new_path=str(new_path),
                output_path=excel_path
            )
        except Exception as e:
            print(f"[run] ⚠️ Excel export failed: {e}")

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