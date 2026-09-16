import time
import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import Dict, Generator

class IngestionTimer:
    """Thread-safe performance telemetry and measurement timer."""
    
    def __init__(self):
        self.timings = defaultdict(float)
        self.counts = defaultdict(int)
        self.lock = threading.Lock()

    @contextmanager
    def measure(self, name: str) -> Generator[None, None, None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            with self.lock:
                self.timings[name] += elapsed
                self.counts[name] += 1

    def get_avg(self, name: str) -> float:
        with self.lock:
            count = self.counts[name]
            return self.timings[name] / count if count > 0 else 0.0

    def report(self, printer=print):
        printer("\n=== Pipeline Performance Report ===")
        with self.lock:
            total_time = sum(self.timings.values())
            timings_snapshot = dict(self.timings)
            counts_snapshot = dict(self.counts)
        for name, duration in sorted(timings_snapshot.items(), key=lambda x: x[1], reverse=True):
            count = counts_snapshot[name]
            avg = duration / count if count > 0 else 0
            pct = (duration / total_time * 100) if total_time > 0 else 0
            printer(f"  - {name}: {duration:.3f}s total ({count} calls, avg {avg:.4f}s, {pct:.1f}%)")
        printer(f"Total time measured: {total_time:.3f}s\n")
