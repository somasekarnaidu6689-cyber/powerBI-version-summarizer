import ijson
import json
from pathlib import Path
import config


def is_large_file(path: str | Path) -> bool:
    """
    Returns True if the file exceeds the threshold defined in config.
    Activates streaming mode automatically — no manual flag needed.
    """
    p = Path(path)
    size_mb = p.stat().st_size / (1024 * 1024)
    print(f"[large_file_handler] File size: {size_mb:.2f} MB")
    return size_mb > config.LARGE_FILE_THRESHOLD_MB


def warn_if_small(path: str | Path) -> None:
    """
    Warns the user if file is under 20 MB on Databricks.
    Running small files on Databricks wastes DBU credits.
    """
    if config.ENVIRONMENT == "databricks" and config.DBX_WARN_SMALL_FILES:
        p = Path(path)
        size_mb = p.stat().st_size / (1024 * 1024)
        if size_mb < 20:
            print(
                f"[large_file_handler] WARNING: File is only {size_mb:.2f} MB. "
                f"Consider running this locally instead to save Databricks credits."
            )


# ─── Standard JSON Loader ─────────────────────────────────────
def load_json(path: str | Path) -> dict:
    """
    Loads a JSON file normally (for files under the threshold).
    """
    p = Path(path)
    print(f"[large_file_handler] Loading JSON normally: {p.name}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Streaming JSON Loader (ijson) ────────────────────────────
def load_json_streaming(path: str | Path) -> dict:
    """
    Streams and parses a large JSON file using ijson.
    Prints progress to console as it runs.
    Used automatically for files over LARGE_FILE_THRESHOLD_MB.
    """
    p = Path(path)
    print(f"[large_file_handler] Streaming large file: {p.name} ...")

    result = {}
    chunk_count = 0

    with open(p, "rb") as f:
        parser = ijson.kvitems(f, "")
        for key, value in parser:
            result[key] = value
            chunk_count += 1
            if chunk_count % 500 == 0:
                print(f"[large_file_handler] Processed {chunk_count} chunks ...")

    print(f"[large_file_handler] Streaming complete. Total keys parsed: {chunk_count}")
    return result


# ─── Smart Loader — Use This Everywhere ───────────────────────
def smart_load(path: str | Path) -> dict:
    """
    Auto-selects normal or streaming load based on file size.
    This is the only function you need to call from other modules.

    Usage:
        from large_file_handler import smart_load
        data = smart_load(path)
    """
    p = Path(path)

    # Warn if running on Databricks with a small file
    warn_if_small(p)

    if is_large_file(p):
        return load_json_streaming(p)
    else:
        return load_json(p)