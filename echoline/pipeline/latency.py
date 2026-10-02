import collections
import math


class LatencyTracker:
    """Rolling sound-to-screen latency percentiles."""

    def __init__(self, window=200):
        self._samples = collections.deque(maxlen=window)

    def record(self, captured_at, shown_at):
        self._samples.append((shown_at - captured_at) * 1000)

    def _percentile(self, percent):
        if not self._samples:
            return None
        ordered = sorted(self._samples)
        return round(ordered[max(0, math.ceil(percent / 100 * len(ordered)) - 1)])

    def p50_ms(self):
        return self._percentile(50)

    def p95_ms(self):
        return self._percentile(95)

    def summary(self):
        if not self._samples:
            return "measuring…"
        return f"p50 {self.p50_ms()} ms · p95 {self.p95_ms()} ms"
