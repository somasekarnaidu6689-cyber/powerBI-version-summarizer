import argparse
import time
from pathlib import Path

from detector import detect, describe, FileType
from extractor import extract
from comparators.model import compare_model
from comparators.report import compare_report
from comparators.layout import compare_layout
from reporter import generate_report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Power BI PBIP comparison tool",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--old",
        required=True,
        help="Path to the older PBIP folder"
    )
    parser.add_argument(
        "--new",
        required=True,
        help="Path to the newer PBIP folder"
    )
    return parser.parse_args()


def _resolve_input(path: Path) -> tuple[Path | None, Path | None, FileType]:
    fmt, ftype = detect(path)
    print(f"[run] Detected {describe(fmt, ftype)}: {path}")
    extracted = extract(path, fmt, ftype)
    return extracted["model_path"], extracted["report_path"], ftype


def main():
    args = parse_args()

    start = time.perf_counter()

    old_path = Path(args.old)
    new_path = Path(args.new)

    old_model_path, old_report_path, old_ftype = _resolve_input(old_path)
    new_model_path, new_report_path, new_ftype = _resolve_input(new_path)

    if old_ftype != FileType.PBIP_FOLDER or new_ftype != FileType.PBIP_FOLDER:
        print("[run] ERROR: Only PBIP folders are supported for this PR comment workflow.")
        raise SystemExit(1)

    model_results = {}
    report_results = {}
    layout_results = {}

    if old_model_path and new_model_path:
        model_results = compare_model(old_model_path, new_model_path)
    else:
        print("[run] Skipping model comparison because one or both model paths are unavailable.")

    if old_report_path and new_report_path:
        report_results = compare_report(old_report_path, new_report_path)
        layout_results = compare_layout(old_report_path, new_report_path)
    else:
        print("[run] Skipping report/layout comparison because one or both report paths are unavailable.")

    generate_report(
        model_results,
        report_results,
        layout_results,
    )

    print("\n✅ Done. Summary is printed to console and PR comment workflows can use this output.")


if __name__ == "__main__":
    main()
