import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(ENV_FILE)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _optional_int_env(name: str):
    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


OLD_PATH = Path(os.getenv("OLD_PATH")) if os.getenv("OLD_PATH") else None
NEW_PATH = Path(os.getenv("NEW_PATH")) if os.getenv("NEW_PATH") else None

# Options: "local", "rdp", "databricks"
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

LARGE_FILE_THRESHOLD_MB = _int_env("LARGE_FILE_THRESHOLD_MB", 100)
INCLUDE_LAYOUT_DIFF = _bool_env("INCLUDE_LAYOUT_DIFF", True)

# ─── Databricks Specific ──────────────────────────────────────
DBX_WARN_SMALL_FILES = _bool_env("DBX_WARN_SMALL_FILES", True)
DBX_LOG_DURATION = _bool_env("DBX_LOG_DURATION", True)

# ─── Sampling (for large reports) ─────────────────────────────
SAMPLE_PAGES = _optional_int_env("SAMPLE_PAGES")
