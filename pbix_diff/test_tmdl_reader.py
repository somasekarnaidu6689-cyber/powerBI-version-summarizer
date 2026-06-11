# pbix_diff/test_tmdl_reader.py
import unittest
from pathlib import Path

from tmdl_reader import read_semantic_model


class TestTmdlReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Walk up from this file to repo root, then into the semantic model
        repo_root = Path(__file__).resolve().parent.parent
        cls.semantic_model_path = (
            repo_root / "powerBi" / "v2" / "new.SemanticModel"
        )
        cls.model = read_semantic_model(cls.semantic_model_path)

    def test_definition_folder_exists(self):
        definition_dir = self.semantic_model_path / "definition"
        self.assertTrue(
            definition_dir.exists(),
            f"definition/ folder missing at {self.semantic_model_path}"
        )

    def test_model_returns_expected_keys(self):
        self.assertIn("tables",        self.model, "model missing 'tables' key — definition/ may be incomplete")
        self.assertIn("relationships", self.model)
        self.assertIn("model_meta",    self.model)

    def test_customers1_table_exists(self):
        self.assertIn("tables", self.model, "model is empty — check definition/ folder")
        self.assertIn(
            "Customers1", self.model["tables"],
            f"Customers1 not found. Tables present: {list(self.model['tables'].keys())}"
        )

    def test_customers1_columns(self):
        self.assertIn("tables", self.model)
        self.assertIn("Customers1", self.model["tables"])
        columns = self.model["tables"]["Customers1"]["columns"]
        self.assertTrue(len(columns) > 0, "Customers1 has no columns")
        self.assertEqual(columns[0]["dataType"], "string")

    def test_customers1_partitions(self):
        self.assertIn("tables", self.model)
        self.assertIn("Customers1", self.model["tables"])
        partitions = self.model["tables"]["Customers1"]["partitions"]
        self.assertTrue(len(partitions) > 0, "Customers1 has no partitions")
        self.assertEqual(partitions[0]["mode"], "import")

    def test_relationships_exist(self):
        self.assertIn("relationships", self.model)
        self.assertTrue(len(self.model["relationships"]) > 0, "No relationships found")
        self.assertTrue(
            all("id" in rel for rel in self.model["relationships"]),
            "Some relationships missing 'id'"
        )

    def test_model_culture(self):
        self.assertIn("model_meta", self.model)
        self.assertEqual(self.model["model_meta"].get("culture"), "en-US")


if __name__ == "__main__":
    unittest.main()