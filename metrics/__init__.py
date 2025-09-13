"""
Metrics package for EchoLine performance evaluation and benchmarking.

This package provides comprehensive tools for evaluating:
- Transcription accuracy (WER, CER, precision, recall, F1)
- System performance (latency, throughput, resource usage)
- Real-time monitoring and reporting
- Audio file evaluation with ML metrics
- Error pattern analysis and visualization
"""

from .accuracy_evaluator import TranscriptionEvaluator, TranscriptionMetrics, print_detailed_metrics
from .system_performance_monitor import PerformanceMonitor, PerformanceMetrics
from .error_pattern_analyzer import ConfusionMatrixAnalyzer
from .audio_ml_evaluator import AudioEvaluator

__all__ = [
    'TranscriptionEvaluator',
    'TranscriptionMetrics', 
    'print_detailed_metrics',
    'PerformanceMonitor',
    'PerformanceMetrics',
    'ConfusionMatrixAnalyzer',
    'AudioEvaluator'
]