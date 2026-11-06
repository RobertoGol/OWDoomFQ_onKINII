import tempfile
import unittest
from pathlib import Path

from check_docs import anchors, check_fences, schema_sizes


class DocumentationChecks(unittest.TestCase):
    def test_schema_padding_and_tail(self):
        fields = [{"type": "u64", "count": 1}, {"type": "u8", "count": 1}, {"type": "u32", "count": 1}]
        self.assertEqual(schema_sizes(fields), (13, 16))

    def test_array_alignment(self):
        fields = [{"type": "u8", "count": 1}, {"type": "f32", "count": 3}]
        self.assertEqual(schema_sizes(fields), (13, 16))

    def test_invalid_field(self):
        with self.assertRaises(ValueError):
            schema_sizes([{"type": "char", "count": 1}])
        with self.assertRaises(ValueError):
            schema_sizes([{"type": "u32", "count": 0}])

    def test_fences(self):
        self.assertTrue(check_fences("# Doc\n```void\nstruct X {}\n```\n"))
        self.assertFalse(check_fences("# Doc\n```void\nstruct X {}\n"))
        self.assertTrue(check_fences("~~~~\n```\n~~~~\n"))

    def test_anchors_ignore_code_and_handle_duplicates(self):
        text = "# Один\n```\n# Не заголовок\n```\n## Два раза\n## Два раза\n"
        self.assertEqual(anchors(text), {"один", "два-раза", "два-раза-1"})

    def test_local_links(self):
        from check_docs import check

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ReadmeFilesRU").mkdir()
            (root / "tools").mkdir()
            (root / "ReadmeFilesRU/SERIALIZATION_SPEC.md").write_text("# Схемы\n", encoding="utf-8")
            (root / "tools/docs_schemas.json").write_text('{"schemas": []}', encoding="utf-8")
            (root / "README.md").write_text("[OK](ReadmeFilesRU/SERIALIZATION_SPEC.md#схемы)\n[External](https://example.invalid/x)\n", encoding="utf-8")
            self.assertEqual(check(root)[0], [])
            (root / "README.md").write_text("[Broken](missing.md)\n[Anchor](ReadmeFilesRU/SERIALIZATION_SPEC.md#нет)\n", encoding="utf-8")
            self.assertEqual(len(check(root)[0]), 2)


if __name__ == "__main__":
    unittest.main()
