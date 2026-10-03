from echoline.pipeline.latency import LatencyTracker


def test_percentiles_from_recorded_latencies():
    tracker = LatencyTracker()
    for ms in range(1, 101):                 # 1..100 ms
        tracker.record(captured_at=10.0, shown_at=10.0 + ms / 1000)

    assert tracker.p50_ms() == 50
    assert tracker.p95_ms() == 95
    assert tracker.summary() == "p50 50 ms · p95 95 ms"


def test_empty_tracker_reports_measuring():
    tracker = LatencyTracker()

    assert tracker.p50_ms() is None
    assert tracker.summary() == "measuring…"


def test_only_recent_samples_count():
    tracker = LatencyTracker(window=3)
    for ms in (900, 900, 900, 10, 10, 10):
        tracker.record(0.0, ms / 1000)

    assert tracker.p95_ms() == 10
