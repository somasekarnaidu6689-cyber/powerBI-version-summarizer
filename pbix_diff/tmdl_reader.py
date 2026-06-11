import re
import json
from pathlib import Path

ASSIGN_OP = r'[:=]'


# ─── Main Reader ──────────────────────────────────────────────
def read_semantic_model(semantic_model_dir: Path) -> dict:
    """
    Reads a full SemanticModel folder.
    Handles enterprise structure:
      definition/tables/*.tmdl
      definition/relationships/ (folder or .tmdl file)
      definition/roles/
      definition/cultures/
      definition/model.tmdl
      _measures.tmdl (dedicated measure file)
    """
    definition_dir = semantic_model_dir / "definition"
    if not definition_dir.exists():
        print(f"[tmdl_reader] WARNING: definition/ not found in {semantic_model_dir}")
        # Return full skeleton so callers don't get KeyError on missing keys
        return {
            "tables":        {},
            "relationships": [],
            "roles":         [],
            "cultures":      [],
            "model_meta":    {},
        }

    result = {
        "tables":        {},
        "relationships": [],
        "roles":         [],
        "cultures":      [],
        "model_meta":    {},
    }

    # ── Tables ────────────────────────────────────────────────
    tables_dir = definition_dir / "tables"
    if tables_dir.exists():
        for tmdl_file in sorted(tables_dir.glob("*.tmdl")):
            table_data = parse_table_tmdl(tmdl_file)
            if table_data:
                result["tables"][table_data["name"]] = table_data

    # ── Dedicated _measures.tmdl (enterprise pattern) ─────────
    measures_file = definition_dir / "_measures.tmdl"
    if measures_file.exists():
        measures = parse_measures_only_tmdl(measures_file)
        for m in measures:
            table_name = m.get("table", "_measures")
            if table_name not in result["tables"]:
                result["tables"][table_name] = {
                    "name": table_name,
                    "columns": [],
                    "measures": [],
                    "partitions": [],
                    "raw": ""
                }
            result["tables"][table_name]["measures"].append(m)

    # ── Relationships (folder or file) ────────────────────────
    rel_dir  = definition_dir / "relationships"
    rel_file = definition_dir / "relationships.tmdl"
    if rel_dir.exists() and rel_dir.is_dir():
        for f in sorted(rel_dir.glob("*.tmdl")):
            result["relationships"].extend(parse_relationships_tmdl(f))
    elif rel_file.exists():
        result["relationships"] = parse_relationships_tmdl(rel_file)

    # ── Roles (RLS / OLS) ─────────────────────────────────────
    roles_dir  = definition_dir / "roles"
    roles_file = definition_dir / "roles.tmdl"
    if roles_dir.exists() and roles_dir.is_dir():
        for f in sorted(roles_dir.glob("*.tmdl")):
            result["roles"].extend(parse_roles_tmdl(f))
    elif roles_file.exists():
        result["roles"] = parse_roles_tmdl(roles_file)

    # ── Cultures ──────────────────────────────────────────────
    cultures_dir = definition_dir / "cultures"
    if cultures_dir.exists():
        for f in sorted(cultures_dir.glob("*.tmdl")):
            result["cultures"].append({
                "name": f.stem,
                "raw":  f.read_text(encoding="utf-8", errors="ignore")
            })

    # ── Model meta ────────────────────────────────────────────
    model_file = definition_dir / "model.tmdl"
    if model_file.exists():
        result["model_meta"] = parse_model_tmdl(model_file)

    print(f"[tmdl_reader] Read {len(result['tables'])} tables, "
          f"{len(result['relationships'])} relationships, "
          f"{len(result['roles'])} roles")

    return result


# ─── Table Parser ─────────────────────────────────────────────
def parse_table_tmdl(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[tmdl_reader] Failed to read {path.name}: {e}")
        return {}

    return {
        "name":       _extract_table_name(content, path.stem),
        "columns":    _extract_columns(content),
        "measures":   _extract_measures(content),
        "partitions": _extract_partitions(content),
        "raw":        content,
    }


# ─── Dedicated Measures File ──────────────────────────────────
def parse_measures_only_tmdl(path: Path) -> list:
    """
    Parses _measures.tmdl which contains measures grouped by table.
    Pattern: table 'TableName' { measure ... }
    """
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    measures = []
    # Find table blocks
    table_blocks = re.finditer(
        r"table\s+'?([^'\n{]+)'?\s*\{(.*?)\}",
        content, re.DOTALL
    )
    for tb in table_blocks:
        table_name = tb.group(1).strip()
        block = tb.group(2)
        for m in _extract_measures(block):
            m["table"] = table_name
            measures.append(m)

    # Fallback: top-level measures without table block
    if not measures:
        for m in _extract_measures(content):
            m["table"] = "_measures"
            measures.append(m)

    return measures


# ─── Relationships Parser ─────────────────────────────────────
def parse_relationships_tmdl(path: Path) -> list:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    relationships = []
    blocks = re.finditer(
        r'relationship\s+([\w\-]+)(.*?)(?=relationship\s|\Z)',
        content, re.DOTALL
    )
    for rel_id, rel_body in (m.groups() for m in blocks):
        rel = {"id": rel_id.strip()}
        for key, pattern in [
            ("from",        rf'fromColumn\s*{ASSIGN_OP}\s*(.+)'),
            ("to",          rf'toColumn\s*{ASSIGN_OP}\s*(.+)'),
            ("cardinality", rf'fromCardinality\s*{ASSIGN_OP}\s*(.+)'),
            ("crossFilter", rf'crossFilteringBehavior\s*{ASSIGN_OP}\s*(.+)'),
        ]:
            m = re.search(pattern, rel_body)
            if m:
                rel[key] = m.group(1).strip()
        relationships.append(rel)

    return relationships


# ─── Roles Parser (RLS / OLS) ─────────────────────────────────
def parse_roles_tmdl(path: Path) -> list:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    roles = []
    role_blocks = re.finditer(
        r'role\s+\'?([^\'{\n]+)\'?\s*\{(.*?)\}(?=\s*role|\Z)',
        content, re.DOTALL
    )
    for rb in role_blocks:
        role_name = rb.group(1).strip()
        role_body = rb.group(2)

        # Extract table permissions
        table_perms = []
        tp_blocks = re.finditer(
            r"tablePermission\s+'?([^'{\n]+)'?\s*\{(.*?)\}",
            role_body, re.DOTALL
        )
        for tp in tp_blocks:
            filter_expr = re.search(rf'filterExpression\s*{ASSIGN_OP}\s*(.+)', tp.group(2))
            table_perms.append({
                "table":      tp.group(1).strip(),
                "filterExpr": filter_expr.group(1).strip() if filter_expr else None,
            })

        roles.append({
            "name":        role_name,
            "permissions": table_perms,
            "raw":         role_body.strip(),
        })

    return roles


# ─── Model Meta ───────────────────────────────────────────────
def parse_model_tmdl(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        compat  = re.search(rf'compatibilityLevel\s*{ASSIGN_OP}\s*(\d+)', content)
        culture = re.search(rf'culture\s*{ASSIGN_OP}\s*(.+)',             content)
        return {
            "compatibilityLevel": compat.group(1) if compat else None,
            "culture":            culture.group(1).strip() if culture else None,
            "raw":                content,
        }
    except Exception:
        return {}


# ─── Extraction Helpers ───────────────────────────────────────
def _extract_table_name(content: str, fallback: str) -> str:
    m = re.search(r'^table\s+\'?([^\'{\n]+)\'?', content, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def _extract_columns(content: str) -> list:
    columns = []
    for match in re.finditer(
        r'(?:^|\n)\s{0,4}column\s+\'?([^\'{\n]+)\'?\s*\n(.*?)(?=\n\s{0,4}(?:column|measure|partition|hierarchy)\s|\Z)',
        content, re.DOTALL
    ):
        col_name = match.group(1).strip()
        col_body = match.group(2)
        dt  = re.search(rf'dataType\s*{ASSIGN_OP}\s*(\w+)', col_body)
        exp = re.search(rf'expression\s*{ASSIGN_OP}\s*```(.*?)```', col_body, re.DOTALL)
        columns.append({
            "name":          col_name,
            "dataType":      dt.group(1) if dt else "unknown",
            "expression":    exp.group(1).strip() if exp else None,
            "is_calculated": exp is not None,
        })
    return columns


def _extract_measures(content: str) -> list:
    measures = []
    for match in re.finditer(
        r'(?:^|\n)\s{0,4}measure\s+\'?([^\'=\n]+)\'?\s*=(.*?)(?=\n\s{0,4}(?:measure|column|partition|hierarchy)\s|\Z)',
        content, re.DOTALL
    ):
        name = match.group(1).strip()
        body = match.group(2)
        dax_block = re.search(r'```(.*?)```', body, re.DOTALL)
        dax = dax_block.group(1).strip() if dax_block else body.split('\n')[0].strip()
        fmt = re.search(rf'formatString\s*{ASSIGN_OP}\s*(.+)', body)
        desc = re.search(rf'description\s*{ASSIGN_OP}\s*\'?(.+?)\'?\s*\n', body)
        measures.append({
            "name":          name,
            "dax":           dax,
            "formatString":  fmt.group(1).strip() if fmt else None,
            "description":   desc.group(1).strip() if desc else None,
        })
    return measures


def _extract_partitions(content: str) -> list:
    partitions = []
    for match in re.finditer(
        r'partition\s+\'?([^\'=\n]+)\'?\s*=(.*?)(?=partition\s|column\s|measure\s|\Z)',
        content, re.DOTALL
    ):
        name = match.group(1).strip()
        body = match.group(2)
        mode  = re.search(rf'mode\s*{ASSIGN_OP}\s*(\w+)',              body)
        query = re.search(rf'source\s*{ASSIGN_OP}\s*```(.*?)```',           body, re.DOTALL)
        qtype = re.search(rf'type\s*{ASSIGN_OP}\s*(\w+)',               body)
        partitions.append({
            "name":        name,
            "mode":        mode.group(1)          if mode  else "unknown",
            "queryType":   qtype.group(1)         if qtype else None,
            "source":      query.group(1).strip() if query else None,
        })
    return partitions