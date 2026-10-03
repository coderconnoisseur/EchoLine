import collections
import threading
import time
import traceback

import numpy as np

from ..engine.base import SAMPLE_RATE


class EngineWorker:
    """Feeds queued audio to a speech engine on its own thread, never falling behind real time."""

    def __init__(self, engine, on_events, on_lagging, max_backlog_s=3.0, lagging_hold_s=2.0, clock=time.monotonic):
        self._engine = engine
        self._on_events = on_events
        self._on_lagging = on_lagging
        self._max_backlog = int(max_backlog_s * SAMPLE_RATE)
        self._queue = collections.deque()
        self._queued_samples = 0
        self._lagging = False
        self._lagging_hold = lagging_hold_s
        self._last_drop = None
        self._clock = clock
        self._lock = threading.Lock()
        self._engine_lock = threading.Lock()     # the engine is used from one thread at a time
        self._wakeup = threading.Event()
        self._running = False
        self._thread = None

    def push(self, samples, captured_at):
        with self._lock:
            self._queue.append((samples, captured_at))
            self._queued_samples += len(samples)
        self._wakeup.set()

    def _take_batch(self):
        """Pop everything queued, dropping the oldest audio beyond the backlog limit."""
        with self._lock:
            batch, self._queue = list(self._queue), collections.deque()
            queued, self._queued_samples = self._queued_samples, 0
        dropped = False
        while queued > self._max_backlog and len(batch) > 1:
            queued -= len(batch.pop(0)[0])
            dropped = True
        return batch, dropped

    def _set_lagging(self, lagging):
        if lagging != self._lagging:
            self._lagging = lagging
            self._on_lagging(lagging)

    def process_pending(self):
        batch, dropped = self._take_batch()
        if not batch:
            return
        now = self._clock()
        if dropped:
            self._last_drop = now
        # Stay "lagging" until caught up for a while, so the status does not flicker.
        self._set_lagging(self._last_drop is not None and now - self._last_drop < self._lagging_hold)
        # One feed for the whole batch: per-call cost dominates, so a backlog fed
        # block by block never shrinks, while one big chunk lets the engine catch up.
        samples = np.concatenate([samples for samples, _ in batch])
        try:
            with self._engine_lock:
                events = self._engine.feed(samples)
        except Exception:
            traceback.print_exc()
            return
        if events:
            self._on_events(events, batch[-1][1])

    def flush(self):
        """Finish the current utterance (e.g. on pause) and keep running."""
        self.process_pending()
        with self._engine_lock:
            finals = self._engine.flush()
        if finals:
            self._on_events(finals, None)

    def _run(self):
        while self._running:
            self._wakeup.wait(timeout=0.5)
            self._wakeup.clear()
            self.process_pending()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, name="engine-worker", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wakeup.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.process_pending()
        with self._engine_lock:
            finals = self._engine.flush()
        if finals:
            self._on_events(finals, None)
