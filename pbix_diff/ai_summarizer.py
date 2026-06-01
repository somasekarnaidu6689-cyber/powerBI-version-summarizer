import json
from pathlib import Path
from groq import Groq

# ─── Groq Client ──────────────────────────────────────────────
def get_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


# ─── Main Summarizer ──────────────────────────────────────────
def generate_ai_summary(
    model_results: dict,
    report_results: dict,
    layout_results: dict,
    api_key: str
) -> dict:
    """
    Sends comparison results to Groq API and returns
    a structured summary with differences and enhancements.
    """
    print("[ai_summarizer] Preparing data for Groq ...")

    payload = _build_payload(model_results, report_results, layout_results)
    prompt  = _build_prompt(payload)

    print("[ai_summarizer] Calling Groq API ...")
    try:
        client   = get_client(api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Power BI expert analyst. "
                        "You analyze differences between two versions of a Power BI report "
                        "and provide clear, structured insights. "
                        "Always respond ONLY with valid JSON — no markdown, no backticks, no preamble."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()
        print("[ai_summarizer] Response received. Parsing ...")
        return _parse_response(raw)

    except Exception as e:
        print(f"[ai_summarizer] ⚠️ Groq API call failed: {e}")
        return _fallback_summary()


# ─── Build Payload ────────────────────────────────────────────
def _build_payload(
    model_results: dict,
    report_results: dict,
    layout_results: dict
) -> dict:
    payload = {}

    # ── Model ─────────────────────────────────────────────────
    if model_results:
        payload["data_model"] = {
            "tables_added": [
                {
                    "name":     t["name"],
                    "columns":  t.get("columns", []),
                    "measures": [
                        {"name": m["name"], "dax": m["dax"]}
                        for m in t.get("measures", [])
                    ]
                }
                for t in model_results.get("tables_added", [])
            ],
            "tables_removed": model_results.get("tables_removed", []),
            "columns_added": model_results.get("columns_added", []),
            "columns_removed": model_results.get("columns_removed", []),
            "columns_modified": [
                {
                    "table":   c["table"],
                    "column":  c["column"],
                    "changes": c["changes"]
                }
                for c in model_results.get("columns_modified", [])
            ],
            "measures_modified": [
                {
                    "measure": m["measure"],
                    "table":   m.get("table"),
                    "status":  m["status"],
                    "old_dax": m.get("old_dax"),
                    "new_dax": m.get("new_dax"),
                }
                for m in model_results.get("measures_modified", [])
            ],
            "relationship_changes": {
                "added":    len(model_results.get("relationships", {}).get("added", {})),
                "removed":  len(model_results.get("relationships", {}).get("removed", {})),
                "modified": len(model_results.get("relationships", {}).get("modified", {})),
            }
        }

    # ── Report ────────────────────────────────────────────────
    if report_results:
        payload["report"] = {
            "pages_added":   report_results.get("pages_added", []),
            "pages_removed": report_results.get("pages_removed", []),
            "visuals_modified": [
                {
                    "page":        v["page"],
                    "status":      v["status"],
                    "visual_type": v["visual_type"],
                    "changes":     _simplify_changes(v.get("changes", {}))
                }
                for v in report_results.get("visuals_modified", [])
            ],
            "fields_changed": [
                {
                    "page":           f["page"],
                    "fields_removed": f.get("fields_removed", []),
                    "fields_added":   f.get("fields_added", []),
                }
                for f in report_results.get("fields_changed", [])
            ]
        }

    # ── Layout ────────────────────────────────────────────────
    if layout_results:
        payload["layout"] = {
            "canvas_changes":   len(layout_results.get("canvas_settings", [])),
            "bookmark_changes": sum(
                len(v) for v in layout_results.get("bookmarks", {}).values()
            ),
            "zorder_changes":   len(layout_results.get("z_order", [])),
        }

    return payload


def _simplify_changes(changes: dict) -> dict:
    """Converts DeepDiff objects to simple strings for the API."""
    simplified = {}
    if changes.get("visual_type"):
        simplified["chart_type_change"] = changes["visual_type"]
    if changes.get("property_changes"):
        simplified["property_changes"] = {
            k: {"old": v.get("old_value"), "new": v.get("new_value")}
            for k, v in changes["property_changes"].items()
        }
    return simplified


# ─── Build Prompt ─────────────────────────────────────────────
def _build_prompt(payload: dict) -> str:
    return f"""
You are reviewing the differences between two versions of a Power BI report and its semantic model.

Here is the structured diff data:
{json.dumps(payload, indent=2, default=str)}

Based on this diff, respond ONLY with a JSON object in this exact structure:

{{
  "executive_summary": "2-3 sentence plain English summary of what changed overall",
  "differences": [
    {{
      "category": "Category name (e.g. Table Added, Measure Modified, Chart Type, Field Change, Relationship, Column Modified)",
      "what_changed": "Clear specific description referencing actual names",
      "old_value": "Previous value, DAX, or state — use 'N/A' if new addition",
      "new_value": "New value, DAX, or state — use 'N/A' if removed",
      "impact": "Low / Medium / High"
    }}
  ],
  "enhancements": [
    {{
      "title": "Short title",
      "description": "Why this change is beneficial — reference actual table/measure/visual names",
      "type": "Improvement / Risk / Suggestion"
    }}
  ],
  "risk_flags": [
    {{
      "flag": "Short risk title",
      "detail": "What might break — reference actual names from the diff"
    }}
  ]
}}

Rules:
- List EVERY table added with its name in differences
- List EVERY measure change with old and new DAX in differences  
- List EVERY column change with table name in differences
- List EVERY relationship change in differences
- List EVERY visual or field change in differences
- enhancements should explain the business benefit of the changes
- risk_flags should highlight broken references, missing joins, renamed fields
- If a section has nothing to report, return []
- Return ONLY the JSON object, nothing else
"""

# ─── Parse Response ───────────────────────────────────────────
def _parse_response(raw: str) -> dict:
    """
    Safely parses the Groq JSON response.
    Strips markdown fences if present.
    """
    # Strip markdown code fences if model accidentally adds them
    clean = raw
    if "```" in clean:
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    try:
        parsed = json.loads(clean)

        # Validate expected keys exist
        return {
            "executive_summary": parsed.get("executive_summary", "No summary available."),
            "differences":       parsed.get("differences", []),
            "enhancements":      parsed.get("enhancements", []),
            "risk_flags":        parsed.get("risk_flags", []),
        }

    except json.JSONDecodeError as e:
        print(f"[ai_summarizer] ⚠️ JSON parse failed: {e}")
        print(f"[ai_summarizer] Raw response was:\n{raw[:500]}")
        return _fallback_summary()


# ─── Fallback ─────────────────────────────────────────────────
def _fallback_summary() -> dict:
    return {
        "executive_summary": "AI summary unavailable — Groq API call failed or returned invalid JSON.",
        "differences":  [],
        "enhancements": [],
        "risk_flags":   [],
    }