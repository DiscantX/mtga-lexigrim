import re
from typing import Any, Dict, List, Optional


class RecursiveTextChunker:
    """Recursive text chunker for splitting long-form strategy articles into semantic chunks

    targeting 512-1024 token windows with ~10% overlap using paragraph, sentence, and word boundaries.
    """

    def __init__(self, target_chunk_size: int = 1000, overlap: int = 100) -> None:
        """Initialize the RecursiveTextChunker.

        Args:
            target_chunk_size: Target size in characters (approximate token equivalent, e.g. 1000 chars ~ 250-300 words).
            overlap: Overlap size in characters between consecutive chunks.
        """
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        """Recursively split text into chunks adhering to target size and overlap."""
        if not text:
            return []

        if len(text) <= self.target_chunk_size:
            return [text.strip()]

        # Split by paragraphs (\n\n)
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: List[str] = []
        current_chunk_parts: List[str] = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)
            if current_length + para_len + (2 if current_chunk_parts else 0) <= self.target_chunk_size:
                current_chunk_parts.append(para)
                current_length += para_len + (2 if len(current_chunk_parts) > 1 else 0)
            else:
                if current_chunk_parts:
                    chunk_str = "\n\n".join(current_chunk_parts)
                    chunks.append(chunk_str)
                    # Handle overlap by taking trailing part of previous chunk
                    overlap_text = self._get_overlap_text(chunk_str)
                    current_chunk_parts = [overlap_text] if overlap_text else []
                    current_length = len(overlap_text) if overlap_text else 0

                # If paragraph itself is larger than target_chunk_size, split by sentences
                if para_len > self.target_chunk_size:
                    sentence_chunks = self._chunk_by_sentences(para)
                    for sc in sentence_chunks:
                        if len(sc) > self.target_chunk_size:
                            # Hard split by words or characters if a single sentence is huge
                            word_chunks = self._chunk_by_words(sc)
                            for wc in word_chunks:
                                chunks.append(wc)
                        else:
                            chunks.append(sc)
                    current_chunk_parts = []
                    current_length = 0
                else:
                    current_chunk_parts.append(para)
                    current_length += para_len

        if current_chunk_parts:
            chunks.append("\n\n".join(current_chunk_parts))

        return [c.strip() for c in chunks if c.strip()]

    def _get_overlap_text(self, text: str) -> str:
        """Extract trailing characters up to self.overlap size, breaking at word boundaries."""
        if len(text) <= self.overlap:
            return text
        sub = text[-self.overlap:]
        # Find first space to avoid cutting words in half
        space_idx = sub.find(" ")
        if space_idx != -1 and space_idx < len(sub) - 10:
            return sub[space_idx + 1:]
        return sub

    def _chunk_by_sentences(self, text: str) -> List[str]:
        """Split text by sentence boundaries (. ! ?)."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: List[str] = []
        current: List[str] = []
        curr_len = 0

        for s in sentences:
            if curr_len + len(s) + 1 <= self.target_chunk_size:
                current.append(s)
                curr_len += len(s) + 1
            else:
                if current:
                    chunks.append(" ".join(current))
                current = [s]
                curr_len = len(s)
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _chunk_by_words(self, text: str) -> List[str]:
        """Split text by word boundaries when sentences exceed target size."""
        words = text.split()
        chunks: List[str] = []
        current: List[str] = []
        curr_len = 0

        for w in words:
            if curr_len + len(w) + 1 <= self.target_chunk_size:
                current.append(w)
                curr_len += len(w) + 1
            else:
                if current:
                    chunks.append(" ".join(current))
                current = [w]
                curr_len = len(w)
        if current:
            chunks.append(" ".join(current))
        return chunks


def format_chunk_for_embedding(article: Dict[str, Any], chunk_text: str, chunk_idx: int) -> str:
    """Format chunk text with a rich provenance header prepended for embedding generation."""
    source = article.get("source", "Unknown")
    title = article.get("title", "Untitled")
    author = article.get("author", "Unknown")
    evergreen = article.get("evergreen", False)

    return (
        f"Source: {source} | "
        f"Title: {title} | "
        f"Author: {author} | "
        f"Evergreen: {evergreen} | "
        f"Section Part {chunk_idx + 1}\n\n"
        f"{chunk_text}"
    )
