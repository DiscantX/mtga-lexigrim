import os
import time
import zlib
import urllib.request
from typing import Optional, Callable
from config.settings import settings
from ingestion.sources.base import BaseDownloader


class HttpDownloader(BaseDownloader):
    """Agnostic HTTP downloader with chunked streaming, inline gzip decompression, and progress telemetry."""

    def __init__(self, chunk_size: int = settings.stream_chunk_size):
        self.chunk_size = chunk_size

    def download_file(
        self,
        url: str,
        destination_path: str,
        decompress_gzip: bool = True,
        progress_callback: Optional[Callable[[float, str, str], None]] = None
    ) -> str:
        """Download file from URL, stream chunks, decompress if gzipped, write to destination, and report progress."""
        os.makedirs(os.path.dirname(os.path.abspath(destination_path)), exist_ok=True)
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "LexiGrim/1.0",
                "Accept": "application/json,application/octet-stream,*/*"
            }
        )

        start_time = time.time()
        total_downloaded = 0
        last_update_time = start_time
        bytes_since_last_update = 0

        with urllib.request.urlopen(req) as response:
            total_size_header = response.headers.get("Content-Length")
            total_size = int(total_size_header) if total_size_header else None

            decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS) if decompress_gzip else None

            with open(destination_path, "wb") as f_out:
                while True:
                    chunk = response.read(self.chunk_size)
                    if not chunk:
                        if decompressor:
                            try:
                                remainder = decompressor.flush()
                                if remainder:
                                    f_out.write(remainder)
                            except Exception:
                                pass
                        break

                    chunk_len = len(chunk)
                    total_downloaded += chunk_len
                    bytes_since_last_update += chunk_len

                    if decompressor:
                        try:
                            processed_chunk = decompressor.decompress(chunk)
                            if processed_chunk:
                                f_out.write(processed_chunk)
                        except Exception:
                            # Fallback if stream wasn't gzipped
                            f_out.write(chunk)
                    else:
                        f_out.write(chunk)

                    now = time.time()
                    elapsed_interval = now - last_update_time
                    if elapsed_interval >= 0.5 or total_downloaded == chunk_len:
                        speed_bytes_per_sec = bytes_since_last_update / max(elapsed_interval, 0.001)
                        speed_str = self._format_speed(speed_bytes_per_sec)
                        
                        percentage = 0.0
                        if total_size and total_size > 0:
                            percentage = min(100.0, (total_downloaded / total_size) * 100.0)

                        if progress_callback:
                            msg = f"Downloading {os.path.basename(destination_path)} ({total_downloaded / (1024*1024):.1f} MB)"
                            progress_callback(percentage, speed_str, msg)

                        last_update_time = now
                        bytes_since_last_update = 0

        if progress_callback:
            progress_callback(100.0, "0.0 MB/s", f"Successfully downloaded {os.path.basename(destination_path)}")

        return destination_path

    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        if bytes_per_sec >= 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        elif bytes_per_sec >= 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec:.1f} B/s"
