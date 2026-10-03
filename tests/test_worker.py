import threading
import time

import numpy as np

from echoline.engine.base import Final, Partial
from echoline.pipeline.worker import EngineWorker


class RecordingEngine:
    def __init__(self, partial_text="hi", flush_text="hi there"):
        self.fed = []
        self.partial_text = partial_text
        self.flush_text = flush_text

    def feed(self, samples):
        self.fed.append(len(samples))
        return [Partial(0, self.partial_text)]

    def flush(self):
        return [Final(0, self.flush_text)]


def block(ms):
    return np.zeros(16 * ms, dtype=np.float32)


def collect():
    events, lagging = [], []
    return events, lagging, (lambda evs, ts: events.append((evs, ts))), lagging.append


def test_events_are_delivered_with_capture_time_of_newest_block():
    events, lagging, on_events, on_lagging = collect()
    worker = EngineWorker(RecordingEngine(), on_events, on_lagging)

    worker.push(block(30), captured_at=1.0)
    worker.push(block(30), captured_at=1.03)
    worker.process_pending()

    assert events == [([Partial(0, "hi")], 1.0), ([Partial(0, "hi")], 1.03)]


def test_backlog_drops_oldest_audio_and_flags_lagging():
    events, lagging, on_events, on_lagging = collect()
    engine = RecordingEngine()
    worker = EngineWorker(engine, on_events, on_lagging, max_backlog_s=1.0)

    for i in range(50):                       # 1.5 s of 30 ms blocks queued while the engine is busy
        worker.push(block(30), captured_at=i * 0.03)
    worker.process_pending()

    assert sum(engine.fed) <= 16000           # never more than 1 s fed
    assert events[-1][1] == 49 * 0.03         # newest audio survived
    assert lagging == [True]


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_lagging_clears_only_after_staying_caught_up():
    # Clearing on the first clean batch made the "Catching up" pill flicker,
    # and every flicker resized the overlay.
    events, lagging, on_events, on_lagging = collect()
    clock = Clock()
    worker = EngineWorker(RecordingEngine(), on_events, on_lagging, max_backlog_s=0.1, clock=clock)

    for i in range(10):
        worker.push(block(30), captured_at=i)
    worker.process_pending()
    clock.now = 0.5
    worker.push(block(30), captured_at=99)
    worker.process_pending()
    assert lagging == [True]

    clock.now = 2.5
    worker.push(block(30), captured_at=100)
    worker.process_pending()
    assert lagging == [True, False]


def test_stop_flushes_pending_partial_as_final():
    events, lagging, on_events, on_lagging = collect()
    worker = EngineWorker(RecordingEngine(flush_text="the end"), on_events, on_lagging)
    worker.start()
    worker.push(block(30), captured_at=5.0)

    worker.stop()

    assert events[-1][0] == [Final(0, "the end")]


def test_worker_thread_processes_pushed_audio():
    delivered = threading.Event()
    worker = EngineWorker(RecordingEngine(), lambda evs, ts: delivered.set(), lambda flag: None)
    worker.start()

    worker.push(block(30), captured_at=time.monotonic())

    assert delivered.wait(timeout=2)
    worker.stop()


def test_engine_errors_do_not_kill_the_worker():
    class Flaky(RecordingEngine):
        def feed(self, samples):
            if not self.fed:
                self.fed.append(0)
                raise RuntimeError("model hiccup")
            return super().feed(samples)

    events, lagging, on_events, on_lagging = collect()
    worker = EngineWorker(Flaky(), on_events, on_lagging)

    worker.push(block(30), captured_at=1.0)
    worker.push(block(30), captured_at=2.0)
    worker.process_pending()

    assert events == [([Partial(0, "hi")], 2.0)]


def test_brief_engine_stall_does_not_drop_audio():
    # A single slow pass (long line re-decoded, CPU spike) can hold the worker
    # for a second or two; dropping audio then loses words the engine would
    # have caught up on.
    events, lagging, on_events, on_lagging = collect()
    engine = RecordingEngine()
    worker = EngineWorker(engine, on_events, on_lagging)

    for i in range(67):                       # ~2 s queued behind a stalled pass
        worker.push(block(30), captured_at=i * 0.03)
    worker.process_pending()

    assert sum(engine.fed) == 67 * 480
    assert lagging == []
