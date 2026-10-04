import time

from PySide6.QtCore import QCoreApplication

from echoline.ui.sample import SampleCaptions

app = QCoreApplication.instance() or QCoreApplication([])


def run_for(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def test_sample_plays_the_script_and_loops():
    sample = SampleCaptions(step_ms=5)
    seen = set()
    sample.captions.latestChanged.connect(lambda: seen.add(sample.captions.property("latestText")))
    sample.start()
    run_for(0.3 + len(SampleCaptions.SCRIPT) * 0.005 * 3)
    sample.stop()
    finals = [events[-1].text for events in SampleCaptions.SCRIPT if events and type(events[-1]).__name__ == "Final"]
    assert finals and finals[0] in seen
    assert sample.loops >= 1


def test_stop_halts_the_sample():
    sample = SampleCaptions(step_ms=5)
    sample.start()
    run_for(0.05)
    sample.stop()
    assert not sample.running
    text = sample.captions.property("latestText")
    run_for(0.1)
    assert sample.captions.property("latestText") == text
