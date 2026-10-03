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


def test_queued_audio_is_fed_as_one_chunk_stamped_with_the_newest_block():
    # Moonshine costs far less per second when fed big chunks (1 s: 0.33x real
    # time, 50 ms: 0.74x). Feeding a backlog block by block kept a lagging
    # engine lagging; one chunk lets it catch up.
    events, lagging, on_events, on_lagging = collect()
    engine = RecordingEngine()
    worker = EngineWorker(engine, on_events, on_lagging)

    worker.push(block(30), captured_at=1.0)
    worker.push(block(30), captured_at=1.03)
    worker.push(block(30), captured_at=1.06)
    worker.process_pending()

    assert engine.fed == [3 * 480]
    assert events == [([Partial(0, "hi")], 1.06)]


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
    worker.process_pending()                  # this feed raises
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


def test_flush_never_runs_while_the_worker_is_feeding():
    # Pausing flushed from the GUI thread while the worker thread could be inside
    # feed(); the native stream must never be used from two threads at once.
    class SlowEngine:
        def __init__(self):
            self.busy = False
            self.overlaps = 0
            self.feeding = threading.Event()

        def feed(self, samples):
            self.busy = True
            self.feeding.set()
            time.sleep(0.2)
            self.busy = False
            return []

        def flush(self):
            if self.busy:
                self.overlaps += 1
            return []

    engine = SlowEngine()
    worker = EngineWorker(engine, lambda evs, ts: None, lambda flag: None)
    worker.start()
    worker.push(block(30), captured_at=0.0)
    assert engine.feeding.wait(timeout=2)

    worker.flush()
    worker.stop()

    assert engine.overlaps == 0


def test_pause_flush_never_overtakes_audio_the_worker_already_took():
    # The worker took a batch but had not fed it when pause flushed; the batch
    # then landed in the restarted stream and showed up as a partial after pause.
    calls = []

    class Engine(RecordingEngine):
        def feed(self, samples):
            calls.append("feed")
            return []

        def flush(self):
            calls.append("flush")
            return []

    worker = EngineWorker(Engine(), lambda *a: None, lambda l: None)
    took, go = threading.Event(), threading.Event()
    real_take = worker._take_batch

    def slow_take():
        batch = real_take()
        if batch[0]:
            took.set()
            go.wait(2)
        return batch

    worker._take_batch = slow_take
    worker.push(block(30), captured_at=1.0)
    feeder = threading.Thread(target=worker.process_pending)
    feeder.start()
    assert took.wait(2)
    flusher = threading.Thread(target=worker.flush)
    flusher.start()
    time.sleep(0.1)
    go.set()
    feeder.join(2)
    flusher.join(2)

    assert calls == ["feed", "flush"]
