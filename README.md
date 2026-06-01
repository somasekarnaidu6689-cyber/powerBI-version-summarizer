# Power BI Diff Tool

## Project Overview

This repository contains a Power BI version comparison tool focused on diffing Power BI Desktop projects and report definitions. It compares:

- Semantic model changes in `.pbip` / `SemanticModel` folders or TMDL exports
- Report page changes in `.pbip`, `.pbix`, or extracted report JSON
- Layout changes such as canvas settings, bookmarks, and visual z-order
- AI-powered summary generation for easier review

The tool generates:

- `output/diff_report.html`
- `output/diff_report.pdf`
- `output/diff_report.xlsx`

## What this tool does

The tool compares two Power BI versions and produces a structured report of differences across the data model and report canvas.

It supports:

- `.pbix` binary Power BI files
- `.pbip` project folders
- `.bim` data model JSON files
- report JSON / `.pbir` definitions

## Architecture and key modules

### `pbix_diff/run.py`

The main CLI orchestrator:

- validates input paths
- detects file formats using `detector.py`
- extracts contents using `extractor.py`
- runs model, report, and layout comparators
- generates HTML, PDF, and Excel output
- optionally enriches results with AI summarization

### `pbix_diff/detector.py`

Detects supported input types:

- `PBIX` → ZIP archive containing Power BI artifacts
- `PBIP` → folder-based Power BI project
- `BIM` → model JSON export
- `JSON` / `.PBIR` → report definition JSON

### `pbix_diff/extractor.py`

Extracts raw files and directories from input paths.

- for `.pbix`, it unzips the archive to a temp folder
- for `.pbip`, it locates `SemanticModel` and `Report` folders
- for raw JSON artifacts, it passes them through directly

### `pbix_diff/comparators/model.py`

Compares semantic model definitions by reading TMDL files.

Uses:

- `pbix_diff/tmdl_reader.py` to parse tables, columns, measures, partitions, relationships, roles, cultures, and model metadata.
- `deepdiff` to detect structural relationship differences.

It reports:

- tables added / removed
- columns added / removed / modified
- measure additions, removals, and DAX changes
- partition/source query changes
- relationship and role permission changes

### `pbix_diff/comparators/report.py`

Compares report definitions and page visuals.

It analyzes:

- pages added / removed
- visuals added / removed / modified
- field swaps inside visuals
- page settings changes
- filters changes

### `pbix_diff/comparators/layout.py`

Compares report layout details.

It loads report JSON files with `pbix_diff/large_file_handler.py` and compares:

- canvas/page settings
- bookmarks
- z-order of visuals

### `pbix_diff/large_file_handler.py`

Handles large report JSON files safely.

- uses `ijson` to stream very large JSON files above `config.LARGE_FILE_THRESHOLD_MB`
- otherwise loads JSON normally

### `pbix_diff/reporter.py`

Builds the final report output:

- console summary
- HTML report using `Jinja2`
- writes output to `output/diff_report.html`

### `pbix_diff/exporter.py`

Exports the diff results to:

- PDF using `reportlab`
- Excel using `openpyxl`

### `pbix_diff/ai_summarizer.py`

Optionally calls the Groq API to generate an AI summary.

The AI model used is:

- `llama-3.3-70b-versatile`

The generated JSON includes:

- executive summary
- structured differences
- enhancements
- risk flags

### `pbix_diff/config.py`

Contains configuration values such as:

- output paths
- layout diff toggle
- sample page limit
- environment settings
- AI summarization toggle and API key

## Supported models and libraries

This project uses the following third-party Python libraries:

- `deepdiff` — structural diffing for JSON-like objects
- `ijson` — streaming JSON parser for large files
- `Jinja2` — HTML template rendering
- `MarkupSafe` — Jinja2 dependency
- `reportlab` — PDF generation
- `openpyxl` — Excel workbook generation
- `groq` — Groq API client for AI summarization

## How to run

1. Open a terminal in the repository root:

```powershell
cd C:\Users\somsekar.naidu\Desktop\projects
```

2. Activate your virtual environment if you use one:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
```

3. Install dependencies:

```powershell
python -m pip install -r pbix_diff/requirements.txt
```

4. Run the comparison tool:

```powershell
python .\pbix_diff\run.py --old "powerBi/v1" --new "powerBi/v2"
```

5. Optional flags:

- `--no-pdf` to skip PDF export
- `--no-excel` to skip Excel export

## Output files

After a run, the generated files are written under:

- `output/diff_report.html`
- `output/diff_report.pdf`
- `output/diff_report.xlsx`

## Notes

- `.pbix` model comparison may be skipped when the internal `DataModel` is binary. For full semantic model diffing, use extracted `.pbip` folder input or TMDL exports.
- AI summaries require a valid Groq API key configured in `pbix_diff/config.py`.
- The HTML template is stored at `pbix_diff/templates/report.html`.

## Troubleshooting

- If PowerShell refuses to run scripts, use the command above to temporarily bypass execution policy.
- If layout diffing is too slow for very large reports, set `config.INCLUDE_LAYOUT_DIFF = False`.
- If `groq` is not installed or AI is not needed, set `config.ENABLE_AI_SUMMARY = False`.
