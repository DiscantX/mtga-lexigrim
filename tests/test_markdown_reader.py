import os
import tempfile
import unittest

from ingestion.readers.base import BaseSourceReader
from ingestion.readers.markdown_reader import MarkdownArticleReader


class TestMarkdownArticleReader(unittest.TestCase):
    """Unit tests for MarkdownArticleReader."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_file_path = os.path.join(self.temp_dir.name, "test_article.md")
        with open(self.sample_file_path, "w", encoding="utf-8") as f:
            f.write(
                "---\n"
                "article_id: test_01\n"
                "title: Test Strategy Article\n"
                "author: Frank Karsten\n"
                "source: ChannelFireball\n"
                "published_at: 2021-01-01\n"
                "evergreen: true\n"
                'tags: ["math", "strategy"]\n'
                "---\n\n"
                "# Introduction\n\n"
                "This is the body of the test article discussing mana curves and probabilities.\n"
            )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_inheritance(self) -> None:
        """Test that MarkdownArticleReader inherits from BaseSourceReader."""
        reader = MarkdownArticleReader(self.temp_dir.name)
        self.assertIsInstance(reader, BaseSourceReader)

    def test_stream_records(self) -> None:
        """Test parsing YAML frontmatter and markdown body."""
        reader = MarkdownArticleReader(self.temp_dir.name)
        records = list(reader.stream_records())

        self.assertEqual(len(records), 1)
        rec = records[0]

        self.assertEqual(rec["article_id"], "test_01")
        self.assertEqual(rec["title"], "Test Strategy Article")
        self.assertEqual(rec["author"], "Frank Karsten")
        self.assertEqual(rec["source"], "ChannelFireball")
        self.assertEqual(rec["published_at"], "2021-01-01")
        self.assertTrue(rec["evergreen"])
        self.assertEqual(rec["tags"], ["math", "strategy"])
        self.assertIn("This is the body", rec["content"])


if __name__ == "__main__":
    unittest.main()
