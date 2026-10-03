import json

from metrics.system_performance_monitor import PerformanceMonitor


def test_report_captures_latency_and_counters(tmp_path):
    monitor = PerformanceMonitor()
    monitor.mark_audio_received("a")
    monitor.mark_audio_processed("a", word_count=4, is_partial=False)
    monitor.mark_ui_updated("a")
    monitor.record_audio_drop()

    path = monitor.save_report(str(tmp_path / "report.json"))

    report = json.loads(open(path).read())
    assert report['summary']['total_words_processed'] == 4
    assert report['summary']['final_updates_count'] == 1
    assert report['summary']['audio_drops'] == 1
    assert report['latency_analysis']['max_ms'] >= 0
