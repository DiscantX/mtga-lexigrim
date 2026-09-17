import json
from typing import Any, Dict, Generator, Tuple, Optional, List, Iterator
from ingestion.readers.base import BaseSourceReader

class JsonlStreamReader(BaseSourceReader):
    """Memory-safe streaming reader for large JSONL datasets using incremental chunk decoding."""
    
    def __init__(self, file_path: str, chunk_size: int = 65536):
        self.file_path = file_path
        self.chunk_size = chunk_size

    @staticmethod
    def count_lines(file_path: str) -> int:
        """Count total lines in a JSONL file efficiently."""
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    def stream_records(self) -> Iterator[Dict[str, Any]]:
        """Yield raw record dictionaries from the JSONL file."""
        for record, _ in self.stream():
            yield record

    def stream(self, skipped_items: Optional[List[Dict[str, Any]]] = None) -> Generator[Tuple[Dict[str, Any], int], None, None]:
        if skipped_items is None:
            skipped_items = []
            
        decoder = json.JSONDecoder()
        buffer = ""
        bytes_read = 0

        with open(self.file_path, "r", encoding="utf-8") as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    while buffer:
                        buffer = buffer.strip()
                        if not buffer:
                            break
                        try:
                            card_obj, index = decoder.raw_decode(buffer)
                            yield card_obj, bytes_read
                            buffer = buffer[index:]
                        except json.JSONDecodeError as e:
                            skipped_items.append({"buffer": buffer, "error": str(e)})
                            newline_idx = buffer.find("\n")
                            if newline_idx != -1:
                                buffer = buffer[newline_idx + 1:]
                            else:
                                break
                    break

                bytes_read = f.tell()
                buffer += chunk

                while buffer:
                    buffer = buffer.strip()
                    if not buffer:
                        break
                    try:
                        card_obj, index = decoder.raw_decode(buffer)
                        yield card_obj, bytes_read
                        buffer = buffer[index:]
                    except json.JSONDecodeError as e:
                        newline_idx = buffer.find("\n")
                        if newline_idx != -1:
                            bad_line = buffer[:newline_idx]
                            skipped_items.append({"line": bad_line, "error": str(e)})
                            buffer = buffer[newline_idx + 1:]
                        else:
                            break
