from deepdiff import DeepDiff
from pathlib import Path
from large_file_handler import smart_load


# ─── Main Model Comparator ────────────────────────────────────
def compare_model(old_path: Path, new_path: Path) -> dict:
    """
    Compares two model.bim / DataModelSchema JSON files.
    Returns a structured dict with all changes found.
    """
    print(f"[model] Loading old model: {old_path.name}")
    old = smart_load(old_path)

    print(f"[model] Loading new model: {new_path.name}")
    new = smart_load(new_path)

    print("[model] Running comparison ...")

    results = {
        "tables_added":     _get_tables_added(old, new),
        "tables_removed":   _get_tables_removed(old, new),
        "columns_added":    _get_columns_added(old, new),
        "columns_removed":  _get_columns_removed(old, new),
        "measures_modified":_get_measures_modified(old, new),
        "relationships":    _get_relationship_changes(old, new),
    }

    _print_summary(results)
    return results


# ─── Table Changes ────────────────────────────────────────────
def _get_table_names(model: dict) -> set:
    tables = model.get("model", {}).get("tables", [])
    return {t["name"] for t in tables if "name" in t}


def _get_tables_added(old: dict, new: dict) -> list:
    old_tables = _get_table_names(old)
    new_tables = _get_table_names(new)
    added = new_tables - old_tables
    if added:
        print(f"[model] Tables added: {added}")
    return sorted(added)


def _get_tables_removed(old: dict, new: dict) -> list:
    old_tables = _get_table_names(old)
    new_tables = _get_table_names(new)
    removed = old_tables - new_tables
    if removed:
        print(f"[model] Tables removed: {removed}")
    return sorted(removed)


# ─── Column Changes ───────────────────────────────────────────
def _get_all_columns(model: dict) -> dict:
    """Returns {table_name: [column_names]} mapping."""
    columns = {}
    for table in model.get("model", {}).get("tables", []):
        tname = table.get("name", "unknown")
        columns[tname] = [
            col["name"]
            for col in table.get("columns", [])
            if "name" in col
        ]
    return columns


def _get_columns_added(old: dict, new: dict) -> list:
    old_cols = _get_all_columns(old)
    new_cols = _get_all_columns(new)
    added = []
    for table, cols in new_cols.items():
        old_set = set(old_cols.get(table, []))
        for col in cols:
            if col not in old_set:
                added.append({"table": table, "column": col})
    return added


def _get_columns_removed(old: dict, new: dict) -> list:
    old_cols = _get_all_columns(old)
    new_cols = _get_all_columns(new)
    removed = []
    for table, cols in old_cols.items():
        new_set = set(new_cols.get(table, []))
        for col in cols:
            if col not in new_set:
                removed.append({"table": table, "column": col})
    return removed


# ─── Measure Changes ──────────────────────────────────────────
def _get_all_measures(model: dict) -> dict:
    """Returns {table_name: {measure_name: expression}} mapping."""
    measures = {}
    for table in model.get("model", {}).get("tables", []):
        tname = table.get("name", "unknown")
        for measure in table.get("measures", []):
            key = f"{tname}.{measure.get('name', 'unknown')}"
            measures[key] = measure.get("expression", "")
    return measures


def _get_measures_modified(old: dict, new: dict) -> list:
    old_measures = _get_all_measures(old)
    new_measures = _get_all_measures(new)
    modified = []

    all_keys = set(old_measures) | set(new_measures)
    for key in sorted(all_keys):
        old_expr = old_measures.get(key)
        new_expr = new_measures.get(key)

        if old_expr is None:
            modified.append({
                "measure": key,
                "status": "added",
                "old_dax": None,
                "new_dax": new_expr
            })
        elif new_expr is None:
            modified.append({
                "measure": key,
                "status": "removed",
                "old_dax": old_expr,
                "new_dax": None
            })
        elif old_expr != new_expr:
            modified.append({
                "measure": key,
                "status": "modified",
                "old_dax": old_expr,
                "new_dax": new_expr
            })

    return modified


# ─── Relationship Changes ─────────────────────────────────────
def _get_relationships(model: dict) -> list:
    return model.get("model", {}).get("relationships", [])


def _get_relationship_changes(old: dict, new: dict) -> dict:
    old_rels = _get_relationships(old)
    new_rels = _get_relationships(new)

    diff = DeepDiff(old_rels, new_rels, ignore_order=True)

    changes = {
        "added":    diff.get("iterable_item_added", {}),
        "removed":  diff.get("iterable_item_removed", {}),
        "modified": diff.get("values_changed", {}),
    }
    return changes


# ─── Console Summary ──────────────────────────────────────────
def _print_summary(results: dict) -> None:
    print("\n── Model Comparison Summary ──────────────────────")
    print(f"  Tables Added:      {len(results['tables_added'])}")
    print(f"  Tables Removed:    {len(results['tables_removed'])}")
    print(f"  Columns Added:     {len(results['columns_added'])}")
    print(f"  Columns Removed:   {len(results['columns_removed'])}")
    print(f"  Measures Changed:  {len(results['measures_modified'])}")
    print(f"  Relationship Diff: {sum(len(v) for v in results['relationships'].values())}")
    print("──────────────────────────────────────────────────\n")