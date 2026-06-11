import unittest
from pathlib import Path

from tmdl_reader import read_semantic_model


class TestTmdlReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic_model_path = (
            Path(__file__).resolve().parent.parent / "powerBi" / "v2" / "new.SemanticModel"
        )

    def test_read_semantic_model_extracts_model_meta_and_tables(self):
        model = read_semantic_model(self.semantic_model_path)

        self.assertIn("Customers1", model["tables"])
        self.assertEqual(model["model_meta"]["culture"], "en-US")
        self.assertEqual(model["tables"]["Customers1"]["columns"][0]["dataType"], "string")
        self.assertEqual(model["tables"]["Customers1"]["partitions"][0]["mode"], "import")
        self.assertTrue(len(model["relationships"]) > 0)
        self.assertTrue(all("id" in rel for rel in model["relationships"]))


if __name__ == "__main__":
    unittest.main()
