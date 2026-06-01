from deepdiff import DeepDiff
from pathlib import Path
from tmdl_reader import read_semantic_model


def compare_model(old_path: Path, new_path: Path) -> dict:
    if old_path.is_dir() or old_path.suffix == ".tmdl":
        return _compare_tmdl(old_path, new_path)
    print("[model] Non-TMDL model — skipping model comparison")
    return {}


def _compare_tmdl(old_path: Path, new_path: Path) -> dict:
    print("[model] Reading old SemanticModel ...")
    old = read_semantic_model(old_path)
    print("[model] Reading new SemanticModel ...")
    new = read_semantic_model(new_path)

    if not old or not new:
        print("[model] WARNING: Could not read one or both SemanticModels")
        return {}

    print("[model] Running TMDL comparison ...")
    results = {
        "tables_added":      _tables_added(old, new),
        "tables_removed":    _tables_removed(old, new),
        "columns_added":     _columns_added(old, new),
        "columns_removed":   _columns_removed(old, new),
        "columns_modified":  _columns_modified(old, new),
        "measures_modified": _measures_modified(old, new),
        "partitions_changed":_partitions_changed(old, new),
        "relationships":     _relationship_changes(old, new),
        "roles_changed":     _roles_changed(old, new),
        "model_meta_changed":_model_meta_changed(old, new),
    }
    _print_summary(results)
    return results


# ─── Tables ───────────────────────────────────────────────────
def _is_auto_table(name: str) -> bool:
    return any(x in name for x in ["LocalDateTable", "DateTableTemplate"])


def _tables_added(old, new) -> list:
    added = set(new["tables"]) - set(old["tables"])
    return [
        {
            "name":        n,
            "is_auto":     _is_auto_table(n),
            "columns":     [c["name"] for c in new["tables"][n].get("columns", [])],
            "measures":    [{"name": m["name"], "dax": m["dax"]}
                           for m in new["tables"][n].get("measures", [])],
            "partitions":  new["tables"][n].get("partitions", []),
        }
        for n in sorted(added)
    ]


def _tables_removed(old, new) -> list:
    removed = set(old["tables"]) - set(new["tables"])
    return [
        {
            "name":     n,
            "is_auto":  _is_auto_table(n),
            "columns":  [c["name"] for c in old["tables"][n].get("columns", [])],
            "measures": [m["name"] for m in old["tables"][n].get("measures", [])],
        }
        for n in sorted(removed)
    ]


# ─── Columns ──────────────────────────────────────────────────
def _columns_added(old, new) -> list:
    result = []
    for t in sorted(set(old["tables"]) & set(new["tables"])):
        old_c = {c["name"]: c for c in old["tables"][t].get("columns", [])}
        new_c = {c["name"]: c for c in new["tables"][t].get("columns", [])}
        for name in sorted(set(new_c) - set(old_c)):
            result.append({"table": t, "column": name,
                           "dataType": new_c[name].get("dataType"),
                           "expression": new_c[name].get("expression")})
    return result


def _columns_removed(old, new) -> list:
    result = []
    for t in sorted(set(old["tables"]) & set(new["tables"])):
        old_c = {c["name"] for c in old["tables"][t].get("columns", [])}
        new_c = {c["name"] for c in new["tables"][t].get("columns", [])}
        for name in sorted(old_c - new_c):
            result.append({"table": t, "column": name})
    return result


def _columns_modified(old, new) -> list:
    result = []
    for t in sorted(set(old["tables"]) & set(new["tables"])):
        old_c = {c["name"]: c for c in old["tables"][t].get("columns", [])}
        new_c = {c["name"]: c for c in new["tables"][t].get("columns", [])}
        for name in sorted(set(old_c) & set(new_c)):
            changes = {}
            if old_c[name].get("dataType") != new_c[name].get("dataType"):
                changes["dataType"] = {"old": old_c[name].get("dataType"),
                                       "new": new_c[name].get("dataType")}
            if old_c[name].get("expression") != new_c[name].get("expression"):
                changes["expression"] = {"old": old_c[name].get("expression"),
                                         "new": new_c[name].get("expression")}
            if changes:
                result.append({"table": t, "column": name, "changes": changes})
    return result


# ─── Measures ─────────────────────────────────────────────────
def _measures_modified(old, new) -> list:
    result = []
    all_tables = set(old["tables"]) | set(new["tables"])
    for t in sorted(all_tables):
        old_m = {m["name"]: m for m in old.get("tables", {}).get(t, {}).get("measures", [])}
        new_m = {m["name"]: m for m in new.get("tables", {}).get(t, {}).get("measures", [])}
        for name in sorted(set(old_m) | set(new_m)):
            o, n = old_m.get(name), new_m.get(name)
            if o is None:
                result.append({"measure": f"{t}.{name}", "table": t,
                               "status": "added", "old_dax": None, "new_dax": n["dax"],
                               "formatString": n.get("formatString"),
                               "description": n.get("description")})
            elif n is None:
                result.append({"measure": f"{t}.{name}", "table": t,
                               "status": "removed", "old_dax": o["dax"], "new_dax": None,
                               "formatString": None, "description": None})
            elif o["dax"] != n["dax"]:
                result.append({"measure": f"{t}.{name}", "table": t,
                               "status": "modified", "old_dax": o["dax"], "new_dax": n["dax"],
                               "formatString": n.get("formatString"),
                               "description": n.get("description")})
    return result


# ─── Partitions ───────────────────────────────────────────────
def _partitions_changed(old, new) -> list:
    result = []
    for t in sorted(set(old["tables"]) & set(new["tables"])):
        old_p = {p["name"]: p for p in old["tables"][t].get("partitions", [])}
        new_p = {p["name"]: p for p in new["tables"][t].get("partitions", [])}
        for name in sorted(set(old_p) | set(new_p)):
            o, n = old_p.get(name), new_p.get(name)
            if o is None:
                result.append({"table": t, "partition": name, "status": "added",
                               "source": n.get("source"), "mode": n.get("mode")})
            elif n is None:
                result.append({"table": t, "partition": name, "status": "removed",
                               "source": o.get("source"), "mode": o.get("mode")})
            elif o.get("source") != n.get("source") or o.get("mode") != n.get("mode"):
                result.append({"table": t, "partition": name, "status": "modified",
                               "old_source": o.get("source"), "new_source": n.get("source"),
                               "old_mode": o.get("mode"), "new_mode": n.get("mode")})
    return result


# ─── Relationships ────────────────────────────────────────────
def _relationship_changes(old, new) -> dict:
    diff = DeepDiff(old.get("relationships", []),
                    new.get("relationships", []), ignore_order=True)
    return {
        "added":    diff.get("iterable_item_added", {}),
        "removed":  diff.get("iterable_item_removed", {}),
        "modified": diff.get("values_changed", {}),
    }


# ─── Roles ────────────────────────────────────────────────────
def _roles_changed(old, new) -> dict:
    old_roles = {r["name"]: r for r in old.get("roles", [])}
    new_roles = {r["name"]: r for r in new.get("roles", [])}
    return {
        "added":   [new_roles[n] for n in sorted(set(new_roles) - set(old_roles))],
        "removed": [old_roles[n] for n in sorted(set(old_roles) - set(new_roles))],
        "modified": [
            {"name": n,
             "old_permissions": old_roles[n]["permissions"],
             "new_permissions": new_roles[n]["permissions"]}
            for n in sorted(set(old_roles) & set(new_roles))
            if old_roles[n]["permissions"] != new_roles[n]["permissions"]
        ]
    }


# ─── Model Meta ───────────────────────────────────────────────
def _model_meta_changed(old, new) -> dict:
    o = old.get("model_meta", {})
    n = new.get("model_meta", {})
    changes = {}
    for key in ["compatibilityLevel", "culture"]:
        if o.get(key) != n.get(key):
            changes[key] = {"old": o.get(key), "new": n.get(key)}
    return changes


# ─── Summary ──────────────────────────────────────────────────
def _print_summary(r: dict):
    print("\n── Model Comparison Summary ──────────────────────")
    print(f"  Tables Added:       {len(r['tables_added'])}")
    print(f"  Tables Removed:     {len(r['tables_removed'])}")
    print(f"  Columns Added:      {len(r['columns_added'])}")
    print(f"  Columns Removed:    {len(r['columns_removed'])}")
    print(f"  Columns Modified:   {len(r['columns_modified'])}")
    print(f"  Measures Changed:   {len(r['measures_modified'])}")
    print(f"  Partitions Changed: {len(r['partitions_changed'])}")
    print(f"  Roles Changed:      {sum(len(v) for v in r['roles_changed'].values())}")
    print("──────────────────────────────────────────────────\n")