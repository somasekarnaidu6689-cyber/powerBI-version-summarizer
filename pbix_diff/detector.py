from pathlib import Path
from enum import Enum

class Format(Enum):
    PBIX = "pbix"
    PBIP = "pbip"
    BIM = "bim"
    JSON = "json"


class FileType(Enum):
    BINARY_ZIP = "binary_zip"       # .pbix — ZIP archive
    PBIP_FOLDER = "pbip_folder"     # .pbip — folder with marker
    MODEL_JSON = "model_json"       # .bim — data model JSON
    REPORT_JSON = "report_json"     # .json / .pbir — report JSON


# ─── Detector ─────────────────────────────────────────────────
def detect(path: str | Path) -> tuple[Format, FileType]:
    """
    Inspects the given path and returns a (Format, FileType) tuple.
    Raises ValueError for unrecognized formats.
    """
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")

    # .pbix — ZIP based binary
    if p.is_file() and p.suffix.lower() == ".pbix":
        return Format.PBIX, FileType.BINARY_ZIP

    # .pbip — folder with .pbip marker file inside
    if p.is_dir():
        markers = list(p.glob("*.pbip"))
        if markers:
            return Format.PBIP, FileType.PBIP_FOLDER
        raise ValueError(f"Directory exists but no .pbip marker found: {p}")

    # .bim — data model JSON directly
    if p.is_file() and p.suffix.lower() == ".bim":
        return Format.BIM, FileType.MODEL_JSON

    # .json or .pbir — report JSON directly
    if p.is_file() and p.suffix.lower() in (".json", ".pbir"):
        return Format.JSON, FileType.REPORT_JSON

    raise ValueError(f"Unrecognized file format: {p}")


# ─── Helper ───────────────────────────────────────────────────
def describe(fmt: Format, ftype: FileType) -> str:
    """Returns a human-readable description of the detected format."""
    descriptions = {
        (Format.PBIX, FileType.BINARY_ZIP): "Power BI Binary File (.pbix)",
        (Format.PBIP, FileType.PBIP_FOLDER): "Power BI Project Folder (.pbip)",
        (Format.BIM, FileType.MODEL_JSON): "Data Model JSON (.bim)",
        (Format.JSON, FileType.REPORT_JSON): "Report JSON (.json / .pbir)",
    }
    return descriptions.get((fmt, ftype), "Unknown Format")