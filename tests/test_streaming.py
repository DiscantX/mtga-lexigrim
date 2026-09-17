import os
import tempfile
import unittest

from ingestion.readers.base import BaseSourceReader
from core.streaming import JsonlStreamReader


class TestStreamingReader(unittest.TestCase):
    """Unit tests for BaseSourceReader and JsonlStreamReader."""

    def setUp(self) -> None:
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.temp_file.write('{"id": "1", "name": "Counterspell"}\n')
        self.temp_file.write('{"id": "2", "name": "Giant Growth"}\n')
        self.temp_file.close()

    def tearDown(self) -> None:
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_inheritance(self) -> None:
        """Test that JsonlStreamReader inherits from BaseSourceReader."""
        reader = JsonlStreamReader(self.temp_file.name)
        self.assertIsInstance(reader, BaseSourceReader)

    def test_stream_records(self) -> None:
        """Test that stream_records yields raw record dictionaries correctly."""
        reader = JsonlStreamReader(self.temp_file.name)
        records = list(reader.stream_records())
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["name"], "Counterspell")
        self.assertEqual(records[1]["name"], "Giant Growth")

    def test_count_lines(self) -> None:
        """Test line counting utility."""
        count = JsonlStreamReader.count_lines(self.temp_file.name)
        self.assertEqual(count, 2)

    def test_malformed_json_handling(self) -> None:
        """Test error handling and recovery with malformed JSON lines."""
        bad_file = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        bad_file.write('{"id": "1", "name": "Valid 1"}\n')
        bad_file.write('malformed json line\n')
        bad_file.write('{"id": "2", "name": "Valid 2"}\n')
        bad_file.close()

        try:
            reader = JsonlStreamReader(bad_file.name)
            skipped = []
            records = list(reader.stream(skipped_items=skipped))
            # Should recover and yield valid records
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0][0]["name"], "Valid 1")
            self.assertEqual(records[1][0]["name"], "Valid 2")
            self.assertTrue(len(skipped) > 0)
        finally:
            if os.path.exists(bad_file.name):
                os.unlink(bad_file.name)


if __name__ == "__main__":
    unittest.main()
