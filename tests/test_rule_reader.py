import os
import tempfile
import unittest

from ingestion.readers.base import BaseSourceReader
from ingestion.readers.rule_reader import TextRuleReader


class TestTextRuleReader(unittest.TestCase):
    """Unit tests for TextRuleReader."""

    def setUp(self) -> None:
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.temp_file.write("1. Game Concepts\n")
        self.temp_file.write("100. General\n")
        self.temp_file.write("100.1a Two or more players are required\n")
        self.temp_file.write("to play a traditional game of Magic.\n")
        self.temp_file.write("100.1b The game starts with each player...\n")
        self.temp_file.write("2. Parts of a Card\n")
        self.temp_file.write("200. General\n")
        self.temp_file.write("200.1 Each card has a name.\n")
        self.temp_file.close()

    def tearDown(self) -> None:
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_inheritance(self) -> None:
        """Test that TextRuleReader inherits from BaseSourceReader."""
        reader = TextRuleReader(self.temp_file.name)
        self.assertIsInstance(reader, BaseSourceReader)

    def test_stream_records(self) -> None:
        """Test parsing chapters, sections, and multi-line rules."""
        reader = TextRuleReader(self.temp_file.name)
        records = list(reader.stream_records())

        self.assertEqual(len(records), 3)

        # Rule 100.1a
        self.assertEqual(records[0]["rule_id"], "100.1a")
        self.assertEqual(records[0]["chapter"], "1. Game Concepts")
        self.assertEqual(records[0]["section"], "100. General")
        self.assertEqual(
            records[0]["text"],
            "100.1a Two or more players are required to play a traditional game of Magic."
        )
        self.assertEqual(
            records[0]["hierarchy_path"],
            "1. Game Concepts > 100. General > 100.1a"
        )

        # Rule 100.1b
        self.assertEqual(records[1]["rule_id"], "100.1b")
        self.assertEqual(records[1]["chapter"], "1. Game Concepts")
        self.assertEqual(records[1]["section"], "100. General")

        # Rule 200.1
        self.assertEqual(records[2]["rule_id"], "200.1")
        self.assertEqual(records[2]["chapter"], "2. Parts of a Card")
        self.assertEqual(records[2]["section"], "200. General")
        self.assertEqual(records[2]["hierarchy_path"], "2. Parts of a Card > 200. General > 200.1")


if __name__ == "__main__":
    unittest.main()
