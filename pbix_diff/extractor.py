import zipfile
import shutil
from pathlib import Path
from detector import Format, FileType


# ─── Main Extractor ───────────────────────────────────────────
def extract(path: str | Path, fmt: Format, ftype: FileType) -> dict:
    p = Path(path)

    if ftype == FileType.BINARY_ZIP:
        return _extract_pbix(p)

    elif ftype == FileType.PBIP_FOLDER:
        return _extract_pbip(p)

    elif ftype == FileType.MODEL_JSON:
        return {"model_path": p, "report_path": None}

    elif ftype == FileType.REPORT_JSON:
        return {"model_path": None, "report_path": p}

    raise ValueError(f"Cannot extract — unrecognized FileType: {ftype}")


# ─── PBIX Extractor ───────────────────────────────────────────
def _extract_pbix(pbix_path: Path) -> dict:
    tmp_dir = Path("/tmp") / f"pbix_extract_{pbix_path.stem}"

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"[extractor] Extracting {pbix_path.name} → {tmp_dir}")

    with zipfile.ZipFile(pbix_path, "r") as zf:
        zf.extractall(tmp_dir)

    # ── Locate Report JSON ────────────────────────────────────
    report_path = _find_file(tmp_dir, [
        "Report/definition/report.json",
        "Report/Layout",
        "Report/Layout.json",
        "report.json"
    ])

    # ── Locate Pages JSON (used as model substitute) ──────────
    # DataModel is binary — use definition/pages instead
    model_path = _find_file(tmp_dir, [
        "Report/definition/pages/pages.json",
        "DataModelSchema",
        "DataModelSchema.json",
        "model.bim"
    ])

    if not model_path:
        print("[extractor] WARNING: No model/pages definition found in .pbix")
    if not report_path:
        print("[extractor] WARNING: Report definition not found in .pbix")

    return {
        "model_path":  model_path,
        "report_path": tmp_dir      # ← return the whole folder, not just report.json
    }


# ─── PBIP Folder Traversal ────────────────────────────────────
def _extract_pbip(folder_path: Path) -> dict:
    print(f"[extractor] Traversing PBIP folder: {folder_path}")

    model_path  = None
    report_path = None

    # ── SemanticModel folder → pass whole folder to model comparator
    semantic_folders = [
        f for f in folder_path.iterdir()
        if f.is_dir() and "SemanticModel" in f.name
    ]
    if semantic_folders:
        model_path = semantic_folders[0]   # ← whole folder, not a file
        print(f"[extractor] Found SemanticModel: {model_path.name}")
    else:
        print("[extractor] WARNING: No SemanticModel folder found")

    # ── Report folder
    report_folders = [
        f for f in folder_path.iterdir()
        if f.is_dir() and "Report" in f.name and "SemanticModel" not in f.name
    ]
    if report_folders:
        report_path = report_folders[0]
        print(f"[extractor] Found Report folder: {report_path.name}")
    else:
        print("[extractor] WARNING: No Report folder found")

    return {"model_path": model_path, "report_path": report_path}

    
# ─── File Finder Helper ───────────────────────────────────────
def _find_file(base_dir: Path, candidates: list[str]) -> Path | None:
    for name in candidates:
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None


# ─── Cleanup ──────────────────────────────────────────────────
def cleanup(path: str | Path) -> None:
    p = Path(path)
    if p.exists() and p.is_dir():
        shutil.rmtree(p)
        print(f"[extractor] Cleaned up: {p}")