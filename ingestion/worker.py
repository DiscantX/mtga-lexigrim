import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional, Union

from qdrant_client.http import models
from vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)


class IngestionWorker(threading.Thread):
    """Background consumer worker thread that batches points from a queue and upserts them into the vector store."""

    def __init__(self, q: queue.Queue, vector_store: BaseVectorStore, batch_size: int = 128) -> None:
        """Initialize the ingestion worker thread.

        Args:
            q: Thread-safe queue containing points or batches of points.
            vector_store: Vector store dependency implementing BaseVectorStore.
            batch_size: Number of points to accumulate before triggering bulk upsert (default 128).
        """
        super().__init__(daemon=True)
        self.queue = q
        self.vector_store = vector_store
        self.batch_size = batch_size

    def _flush_buffer(self, buffer: List[Any]) -> List[Any]:
        """Flush accumulated points in the buffer by calling vector_store.upsert_batch."""
        if not buffer:
            return []

        ids: List[str] = []
        vectors: List[List[float]] = []
        payloads: List[Dict[str, Any]] = []

        for p in buffer:
            if hasattr(p, "id") and hasattr(p, "vector") and hasattr(p, "payload"):
                ids.append(str(p.id))
                vectors.append(p.vector)
                payloads.append(p.payload)
            elif isinstance(p, dict):
                ids.append(str(p.get("id") or p.get("card_id", "")))
                vectors.append(p.get("vector", []))
                payloads.append(p.get("payload", p))
            elif isinstance(p, (list, tuple)) and len(p) >= 3:
                ids.append(str(p[0]))
                vectors.append(p[1])
                payloads.append(p[2])

        try:
            self.vector_store.upsert_batch(ids, vectors, payloads)
        except TypeError:
            # Fallback if upsert_batch accepts a single batch/points argument
            self.vector_store.upsert_batch(buffer)
        except Exception as e:
            logger.error(f"Error during vector store batch upsert of {len(buffer)} points: {e}")
            raise

        return []

    def run(self) -> None:
        """Continuously pull items from the queue, batch them, and upsert into the vector store."""
        buffer: List[Any] = []

        try:
            while True:
                try:
                    item = self.queue.get(timeout=2.0)
                except queue.Empty:
                    if buffer:
                        try:
                            buffer = self._flush_buffer(buffer)
                        except Exception as e:
                            logger.error(f"Failed to flush buffer on queue timeout: {e}")
                    continue

                if item is None:
                    # Sentinel received: flush remaining buffer, mark task done, and exit
                    if buffer:
                        try:
                            buffer = self._flush_buffer(buffer)
                        except Exception as e:
                            logger.error(f"Failed to flush buffer on sentinel: {e}")
                    self.queue.task_done()
                    break

                # Normalize item into a list of points
                points_to_add: List[Any] = []
                if isinstance(item, list):
                    points_to_add = item
                elif isinstance(item, tuple) and not (len(item) == 3 and isinstance(item[0], str) and isinstance(item[1], list)):
                    points_to_add = list(item)
                else:
                    points_to_add = [item]

                buffer.extend(points_to_add)
                self.queue.task_done()

                while len(buffer) >= self.batch_size:
                    batch = buffer[:self.batch_size]
                    buffer = buffer[self.batch_size:]
                    try:
                        self._flush_buffer(batch)
                    except Exception as e:
                        logger.error(f"Failed to upsert batch of size {len(batch)}: {e}")

        except Exception as e:
            logger.error(f"IngestionWorker encountered unexpected exception: {e}")
            raise

    def start(self) -> None:
        """Start the background worker thread."""
        super().start()

    def join(self, timeout: Optional[float] = None) -> None:
        """Wait for the background worker thread to terminate."""
        super().join(timeout=timeout)
