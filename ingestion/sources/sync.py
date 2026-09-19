import os
import json
import glob
from typing import Dict, Any, Optional, Callable
from ingestion.sources.base import BaseDataProvider, BaseDownloader, BulkMetadata
from ingestion.sources.downloader import HttpDownloader
from ingestion.sources.scryfall import ScryfallClient


class CorpusSyncManager:
    """Manages corpus datasets in corpus/ with manifest tracking, missing detection, and freshness updates."""

    def __init__(
        self,
        corpus_dir: str = "corpus",
        provider: Optional[BaseDataProvider] = None,
        downloader: Optional[BaseDownloader] = None
    ):
        self.corpus_dir = corpus_dir
        self.provider = provider or ScryfallClient()
        self.downloader = downloader or HttpDownloader()
        self.manifest_path = os.path.join(corpus_dir, ".manifest.json")
        os.makedirs(corpus_dir, exist_ok=True)

    def _load_manifest(self) -> Dict[str, Any]:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.manifest_path)), exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def sync_corpus(
        self,
        bulk_type: str = "oracle_cards",
        force: bool = False,
        progress_callback: Optional[Callable[[float, str, str], None]] = None
    ) -> str:
        """Verify and sync a specific corpus type (oracle_cards, rulings, oracle_tags, etc.).
        Returns the local file path of the synchronized corpus.
        """
        if progress_callback:
            progress_callback(0.0, "Connecting", f"Fetching metadata for {bulk_type}...")

        metadata = self.provider.get_bulk_metadata(bulk_type)
        if not metadata:
            raise ValueError(f"Could not retrieve bulk metadata for '{bulk_type}' from data provider.")

        manifest = self._load_manifest()
        stored_entry = manifest.get(bulk_type, {})
        stored_filename = stored_entry.get("filename")
        stored_updated_at = stored_entry.get("updated_at")

        # Determine target filename
        # Clean timestamp for filename use: e.g. 2026-09-19T00:00:00.000+00:00 -> 20260919T000000
        safe_timestamp = metadata.updated_at.replace("-", "").replace(":", "").split(".")[0]
        filename = f"{bulk_type.replace('_', '-')}-{safe_timestamp}.jsonl"
        destination_path = os.path.join(self.corpus_dir, filename)

        file_exists = stored_filename and os.path.exists(os.path.join(self.corpus_dir, stored_filename))
        is_fresh = stored_updated_at == metadata.updated_at and file_exists

        if is_fresh and not force:
            if progress_callback:
                progress_callback(100.0, "Up-to-date", f"Corpus {bulk_type} is already up to date.")
            return os.path.join(self.corpus_dir, stored_filename)

        # Download needed
        if progress_callback:
            progress_callback(10.0, "Downloading", f"Downloading latest {bulk_type} from {metadata.download_url}...")

        self.downloader.download_file(
            url=metadata.download_url,
            destination_path=destination_path,
            decompress_gzip=True,
            progress_callback=progress_callback
        )

        # Cleanup stale corpus files for this bulk type
        pattern = os.path.join(self.corpus_dir, f"{bulk_type.replace('_', '-')}-*.jsonl")
        for old_file in glob.glob(pattern):
            if os.path.abspath(old_file) != os.path.abspath(destination_path):
                try:
                    os.remove(old_file)
                except Exception:
                    pass

        # Update manifest
        manifest[bulk_type] = {
            "filename": filename,
            "updated_at": metadata.updated_at,
            "name": metadata.name,
            "download_url": metadata.download_url,
            "compressed_size_bytes": metadata.compressed_size_bytes
        }
        self._save_manifest(manifest)

        return destination_path

    def sync_all(
        self,
        bulk_types: Optional[list] = None,
        force: bool = False,
        progress_callback: Optional[Callable[[float, str, str], None]] = None
    ) -> Dict[str, str]:
        """Sync multiple corpus datasets (default: oracle_cards, rulings, oracle_tags)."""
        if bulk_types is None:
            bulk_types = ["oracle_cards", "rulings", "oracle_tags"]

        results = {}
        total = len(bulk_types)

        for idx, bulk_type in enumerate(bulk_types):
            def wrapped_callback(pct, speed, msg):
                overall_pct = ((idx * 100.0) + pct) / total
                if progress_callback:
                    progress_callback(overall_pct, speed, f"[{idx+1}/{total}] {msg}")

            try:
                path = self.sync_corpus(bulk_type=bulk_type, force=force, progress_callback=wrapped_callback)
                results[bulk_type] = path
            except Exception as e:
                # Log or re-raise depending on strictness; here we propagate or record error
                raise RuntimeError(f"Failed to sync corpus '{bulk_type}': {e}")

        return results
