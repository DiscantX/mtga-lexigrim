import re
import logging
from typing import Any, Dict, Iterator, Optional
from ingestion.readers.base import BaseSourceReader

logger = logging.getLogger(__name__)

class TextRuleReader(BaseSourceReader):
    """Memory-safe stream reader for Magic: The Gathering Comprehensive Rules text file."""

    def __init__(self, file_path: str = "corpus/MagicCompRules-20260819.txt") -> None:
        self.file_path = file_path

    def stream_records(self) -> Iterator[Dict[str, Any]]:
        """Stream hierarchical rule records from the comprehensive rules text file."""
        chapter_re = re.compile(r"^([0-9]+\.\s+[A-Z].*)")
        section_re = re.compile(r"^([0-9]{3}\.\s+.*)")
        rule_re = re.compile(r"^([0-9]{3}\.[0-9]+[a-z]?)\s+(.*)")

        current_chapter = "1. Game Concepts"
        current_section = "100. General"
        current_rule_id: Optional[str] = None
        current_rule_lines: list[str] = []

        def build_record(rid: str, lines: list[str]) -> Dict[str, Any]:
            full_text = " ".join(lines).strip()
            hierarchy = f"{current_chapter} > {current_section} > {rid}"
            return {
                "rule_id": rid,
                "chapter": current_chapter,
                "section": current_section,
                "text": full_text,
                "hierarchy_path": hierarchy,
            }

        try:
            with open(self.file_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue

                    # Check chapter (e.g. "1. Game Concepts")
                    if chapter_re.match(line_str) and not section_re.match(line_str) and not rule_re.match(line_str):
                        if current_rule_id:
                            yield build_record(current_rule_id, current_rule_lines)
                            current_rule_id = None
                            current_rule_lines = []
                        current_chapter = line_str
                        current_section = "General"
                        continue

                    # Check section (e.g. "100. General")
                    if section_re.match(line_str) and not rule_re.match(line_str):
                        if current_rule_id:
                            yield build_record(current_rule_id, current_rule_lines)
                            current_rule_id = None
                            current_rule_lines = []
                        current_section = line_str
                        continue

                    # Check rule entry (e.g. "100.1a Two or more players...")
                    rule_match = rule_re.match(line_str)
                    if rule_match:
                        if current_rule_id:
                            yield build_record(current_rule_id, current_rule_lines)
                            current_rule_id = None
                            current_rule_lines = []
                        current_rule_id = rule_match.group(1)
                        current_rule_lines = [line_str]
                        continue

                    # Multi-line rule continuation
                    if current_rule_id:
                        current_rule_lines.append(line_str)

                if current_rule_id:
                    yield build_record(current_rule_id, current_rule_lines)

        except FileNotFoundError:
            logger.warning(f"Rules file not found at {self.file_path}")
        except Exception as e:
            logger.error(f"Error reading rules file {self.file_path}: {e}")
            raise
