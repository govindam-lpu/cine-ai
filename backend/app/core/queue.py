"""Single-worker ingest queue.

One ingest at a time on a 2-vCPU Space; concurrent uploads wait in line rather than thrashing the
box. Backed by a one-thread executor. Callers can ask a job's queue position for an honest "you're
Nth in line" indicator instead of a dead spinner.
"""

import threading
from concurrent.futures import ThreadPoolExecutor


class IngestQueue:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest")
        self._pending: list[str] = []   # job_ids waiting or running, in submission order
        self._lock = threading.Lock()

    def submit(self, job_id: str, fn, *args) -> None:
        with self._lock:
            self._pending.append(job_id)

        def _run():
            try:
                fn(*args)
            finally:
                with self._lock:
                    if job_id in self._pending:
                        self._pending.remove(job_id)

        self._executor.submit(_run)

    def position(self, job_id: str) -> int:
        """0 = running (front of the line). N = N jobs ahead. -1 = not queued (done/unknown)."""
        with self._lock:
            return self._pending.index(job_id) if job_id in self._pending else -1

    def depth(self) -> int:
        with self._lock:
            return len(self._pending)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


# Process-wide queue.
ingest_queue = IngestQueue()
