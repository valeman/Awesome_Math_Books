import importlib.util
from pathlib import Path
import unittest

import mistune
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("preview", ROOT / "scripts" / "build_readme_preview.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class CollectionFormattingTests(unittest.TestCase):
    def validate(self, source):
        document = BeautifulSoup(mistune.create_markdown(escape=False)(source), "html.parser")
        preview.validate_collection(document)

    def test_current_readme(self):
        source = (ROOT / "README.md").read_text(encoding="utf-8")
        preview.validate_source(source)
        self.validate(source)

    def test_valid_entry(self):
        self.validate("1. [Book (Vol. 1)](https://example.org/book) by Author. **Commercial.**")

    def test_unclosed_bold(self):
        with self.assertRaisesRegex(ValueError, "unrendered Markdown"):
            self.validate("1. [Book](https://example.org/book)** A description.")

    def test_title_instead_of_url(self):
        with self.assertRaises(ValueError):
            self.validate("1. [Book](Book Title) by Author")

    def test_nested_link(self):
        with self.assertRaises(ValueError):
            self.validate("1. [Book]([https://example.org/a](https://example.org/b))")

    def test_duplicate_list_marker(self):
        with self.assertRaisesRegex(ValueError, "Nested book list"):
            self.validate("1. 1. [Book](https://example.org/book)")

    def test_duplicate_author_prefix(self):
        with self.assertRaisesRegex(ValueError, "duplicated author"):
            self.validate("1. [Book](https://example.org/book) by by Author")

    def test_quote_and_author_inside_title(self):
        with self.assertRaisesRegex(ValueError, "stray quote"):
            self.validate('1. [Book" by Author](https://example.org/book)')

    def test_unclosed_title_parentheses(self):
        with self.assertRaisesRegex(ValueError, "unbalanced title"):
            self.validate("1. [Book (Vol. 1](https://example.org/book)")

    def test_numbering_gap(self):
        with self.assertRaisesRegex(ValueError, "expected list number 2"):
            preview.validate_source("## Math\n1. First\n3. Third\n")

    def test_numbering_restarts_for_each_subject(self):
        preview.validate_source("## Math\n1. First\n2. Second\n## Physics\n1. First\n")


if __name__ == "__main__":
    unittest.main()
