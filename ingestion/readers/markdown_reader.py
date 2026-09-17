import os
import re
import logging
import glob
from typing import Any, Dict, Iterator, Optional, List
from ingestion.readers.base import BaseSourceReader

logger = logging.getLogger(__name__)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class MarkdownArticleReader(BaseSourceReader):
    """Memory-safe stream reader for Markdown strategy articles with YAML/frontmatter parsing."""

    def __init__(self, corpus_path: str = "corpus/strategy") -> None:
        """Initialize the MarkdownArticleReader.

        Args:
            corpus_path: Directory path containing markdown files or glob pattern.
        """
        self.corpus_path = corpus_path

    def stream_records(self) -> Iterator[Dict[str, Any]]:
        """Stream structured article records parsed from markdown files in the corpus."""
        if os.path.isfile(self.corpus_path):
            file_paths = [self.corpus_path]
        elif os.path.isdir(self.corpus_path):
            file_paths = sorted(glob.glob(os.path.join(self.corpus_path, "**", "*.md"), recursive=True))
        else:
            file_paths = sorted(glob.glob(self.corpus_path, recursive=True))

        for file_path in file_paths:
            if not os.path.isfile(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                record = self._parse_markdown_file(file_path, content)
                if record:
                    yield record
            except Exception as e:
                logger.error(f"Error reading markdown file {file_path}: {e}")

    def _parse_markdown_file(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """Parse frontmatter and body content from a markdown file string."""
        frontmatter: Dict[str, Any] = {}
        body = content

        # Check for YAML frontmatter delimited by ---
        frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
        match = frontmatter_re.match(content)
        if match:
            fm_text = match.group(1)
            body = match.group(2)
            if HAS_YAML:
                try:
                    loaded = yaml.safe_load(fm_text)
                    if isinstance(loaded, dict):
                        frontmatter = loaded
                except Exception as e:
                    logger.warning(f"Failed to parse YAML frontmatter in {file_path} with pyyaml: {e}")
            
            if not frontmatter:
                # Fallback simple key-value parser for frontmatter
                for line in fm_text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip()
                        # Unquote strings if quoted
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        # Parse booleans and lists roughly if needed
                        if val.lower() == "true":
                            val = True
                        elif val.lower() == "false":
                            val = False
                        elif val.startswith("[") and val.endswith("]"):
                            # Simple list split
                            val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
                        frontmatter[key] = val

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        article_id = frontmatter.get("article_id") or base_name
        title = frontmatter.get("title") or base_name.replace("_", " ").title()
        author = frontmatter.get("author", "Unknown")
        source = frontmatter.get("source", "Strategy Corpus")
        published_at = frontmatter.get("published_at", "2020-01-01")
        evergreen = bool(frontmatter.get("evergreen", False))
        
        tags = frontmatter.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        return {
            "article_id": str(article_id),
            "title": str(title),
            "author": str(author),
            "source": str(source),
            "published_at": str(published_at),
            "evergreen": evergreen,
            "tags": tags,
            "content": body.strip(),
            "file_path": file_path,
        }
