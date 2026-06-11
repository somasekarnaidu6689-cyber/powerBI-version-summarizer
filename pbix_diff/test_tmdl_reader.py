# pbix_diff/test_tmdl_reader.py
import os
import unittest
from pathlib import Path

from tmdl_reader import read_semantic_model


def _find_valid_semantic_model(repo_root: Path) -> Path:
    """
    Find any SemanticModel folder that has a complete definition/ folder.
    Uses TEST_SEMANTIC_MODEL env var if set (injected by CI).
    No hardcoded names — works regardless of what the .pbip project is called.
    """
    env_override = os.environ.get("TEST_SEMANTIC_MODEL", "").strip()
    if env_override:
        candidate = Path(env_override)
        if (candidate / "definition").exists():
            return candidate

    # Walk the repo and find the first SemanticModel with a definition/ folder
    for sm in sorted(repo_root.rglob("*.SemanticModel")):
        if sm.is_dir() and (sm / "definition").exists():
            return sm

    raise FileNotFoundError(
        f"No SemanticModel with a definition/ folder found under {repo_root}. "
        "Ensure at least one complete .SemanticModel folder exists in the repo."
    )


class TestTmdlReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parent.parent
        cls.semantic_model_path = _find_valid_semantic_model(repo_root)
        print(f"[test] Using SemanticModel: {cls.semantic_model_path}")
        cls.model = read_semantic_model(cls.semantic_model_path)

    def test_definition_folder_exists(self):
        self.assertTrue(
            (self.semantic_model_path / "definition").exists(),
            f"definition/ folder missing at {self.semantic_model_path}"
        )

    def test_model_returns_expected_keys(self):
        self.assertIn("tables",        self.model)
        self.assertIn("relationships", self.model)
        self.assertIn("model_meta",    self.model)

    def test_at_least_one_table_exists(self):
        self.assertGreater(
            len(self.model["tables"]), 0,
            f"No tables found in {self.semantic_model_path}"
        )

    def test_all_tables_have_required_keys(self):
        for name, table in self.model["tables"].items():
            with self.subTest(table=name):
                self.assertIn("columns",    table)
                self.assertIn("measures",   table)
                self.assertIn("partitions", table)

    def test_relationships_have_ids(self):
        for rel in self.model["relationships"]:
            with self.subTest(rel=rel):
                self.assertIn("id", rel)

    def test_model_culture_is_set(self):
        self.assertIsNotNone(
            self.model["model_meta"].get("culture"),
            "model_meta.culture is None — check model.tmdl"
        )


if __name__ == "__main__":
    unittest.main()