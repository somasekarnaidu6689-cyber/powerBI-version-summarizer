from pathlib import Path

OLD_PATH = Path("  ") 
NEW_PATH = Path("  ") 
OUTPUT_PATH = Path("output")  
OUTPUT_HTML = OUTPUT_PATH / "diff_report.html"

# Options: "local", "rdp", "databricks"
ENVIRONMENT = "local"

LARGE_FILE_THRESHOLD_MB = 100  # Files above this use streaming (ijson)

INCLUDE_LAYOUT_DIFF = True  # Set False to skip layout comparison

# ─── Databricks Specific ──────────────────────────────────────
DBX_WARN_SMALL_FILES = True   # Warn if files are under 20 MB (better to run locally)
DBX_LOG_DURATION = True       # Log cluster runtime in the report for cost tracking

# ─── Sampling (for large reports) ─────────────────────────────
SAMPLE_PAGES = None           # Set to an int (e.g. 5) to limit pages compared; None = all pages

# ─── Auto-create output folder if it doesn't exist ────────────
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)