# EchoLine Metrics Package

A comprehensive evaluation and benchmarking suite for the EchoLine real-time speech transcription system.

## Overview

# EchoLine Metrics Package

A comprehensive evaluation and benchmarking suite for the EchoLine real-time speech transcription system.

## Overview

This streamlined package provides essential tools to measure and analyze speech recognition performance across multiple dimensions:

- **Transcription Accuracy**: Word Error Rate (WER), Character Error Rate (CER), precision, recall, F1-score
- **System Performance**: Real-time CPU/memory usage, latency tracking, audio processing monitoring  
- **Error Analysis**: Confusion matrices, phonetic similarity analysis, error pattern identification
- **Audio Evaluation**: Complete ML metrics evaluation for audio files with reference transcriptions

## Package Structure

```
metrics/
├── accuracy_evaluator.py        # Core ML accuracy metrics evaluation
├── audio_ml_evaluator.py        # Complete audio file evaluation tool  
├── error_pattern_analyzer.py    # Confusion matrix & error visualization
├── system_performance_monitor.py # Real-time performance monitoring
├── __init__.py                   # Package initialization and imports
└── README.md                     # This documentation
```

## Core Components

### 1. AccuracyEvaluator (`accuracy_evaluator.py`)

**Purpose**: Evaluates transcription accuracy using industry-standard ML metrics

**What it does**:
- Calculates Word Error Rate (WER) and Character Error Rate (CER)
- Computes precision, recall, and F1-score for transcription quality
- Generates confusion matrices for error analysis
- Provides detailed error classification (substitutions, insertions, deletions)
- Supports batch evaluation of multiple transcription pairs

**Key Classes**:
- `TranscriptionEvaluator`: Main evaluation engine
- `TranscriptionMetrics`: Data structure for metrics results
- `print_detailed_metrics()`: Formatted output function

**Usage**:
```python
from metrics import TranscriptionEvaluator, print_detailed_metrics

evaluator = TranscriptionEvaluator()
metrics = evaluator.evaluate_transcription(
    reference="the quick brown fox jumps over the lazy dog",
    hypothesis="the quik brown fox jumps over the lazy dog"
)

print_detailed_metrics(metrics)
# Output: WER: 0.111 (11.1%), F1-Score: 0.889, etc.
```

### 2. AudioMLEvaluator (`audio_ml_evaluator.py`)

**Purpose**: Complete audio file evaluation tool with EchoLine integration

**What it does**:
- Loads audio files (WAV, MP3, FLAC, etc.) and converts to EchoLine format
- Integrates with EchoLine's Vosk-based transcription system
- Evaluates transcription against reference text
- Monitors real-time performance during transcription
- Generates comprehensive evaluation reports with visualizations
- Supports batch processing and automated benchmarking

**Key Classes**:
- `AudioEvaluator`: Main audio evaluation orchestrator

**Command Line Usage** (Recommended):
```bash
# Basic evaluation
python metrics/audio_ml_evaluator.py "audio.mp3" "reference transcription text"

# Full evaluation with reports and visualizations
python metrics/audio_ml_evaluator.py "audio.wav" "reference text" --save-report --confusion-analysis

# Custom output prefix
python metrics/audio_ml_evaluator.py "speech.mp3" "ground truth" --save-report --confusion-analysis --output-prefix my_evaluation
```

**Python API Usage**:
```python
from metrics import AudioEvaluator

evaluator = AudioEvaluator()

# Load and transcribe audio
audio_data, sample_rate, duration = evaluator.load_audio_file("audio.wav")
hypothesis, processing_time, confidence = evaluator.transcribe_audio(audio_data)

# Evaluate against reference
results, metrics = evaluator.evaluate_transcription("reference text", hypothesis)

# Print comprehensive results
evaluator.print_comprehensive_results(results, metrics)
```

### 3. ErrorPatternAnalyzer (`error_pattern_analyzer.py`)

**Purpose**: Advanced error pattern analysis and visualization

**What it does**:
- Analyzes confusion matrices to identify error patterns
- Generates heatmap visualizations of word substitution errors
- Performs phonetic similarity analysis using edit distance
- Identifies most frequently confused word pairs
- Creates statistical reports on error distributions
- Saves analysis to multiple formats (PNG, TXT, CSV)

**Key Classes**:
- `ConfusionMatrixAnalyzer`: Main error analysis engine

**Usage**:
```python
from metrics import ConfusionMatrixAnalyzer

analyzer = ConfusionMatrixAnalyzer()

# Add confusion data from evaluations
analyzer.add_confusion_data(confusion_matrix)

# Generate visualizations
analyzer.generate_visualization("confusion_heatmap.png")
analyzer.analyze_phonetic_similarity("phonetic_analysis.png")

# Get detailed text report
report = analyzer.generate_detailed_report()
print(report)
```

### 4. SystemPerformanceMonitor (`system_performance_monitor.py`)

**Purpose**: Real-time system performance monitoring during transcription

**What it does**:
- Tracks end-to-end latency (audio reception → transcription → UI update)
- Monitors CPU and memory usage in real-time
- Detects audio drops and processing failures
- Records confidence scores and processing times
- Generates detailed performance reports with statistics
- Supports background monitoring with minimal overhead

**Key Classes**:
- `PerformanceMonitor`: Main performance tracking engine
- `PerformanceMetrics`: Data structure for performance results

**Usage**:
```python
from metrics import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start_monitoring()

# In your transcription pipeline
audio_id = "sample_001"
monitor.mark_audio_received(audio_id)

# ... your transcription processing ...

monitor.mark_audio_processed(audio_id, confidence=0.95, audio_drop=False)
monitor.mark_ui_updated(audio_id)

# Get real-time metrics
current_metrics = monitor.get_current_metrics()
print(f"Current latency: {current_metrics.audio_to_display_latency:.1f}ms")

# Stop and generate report
monitor.stop_monitoring()
report = monitor.get_detailed_report()
```

## How to Benchmark Your EchoLine Application

### Method 1: Quick Audio File Evaluation

**Best for**: Testing individual audio files against known transcriptions

```bash
# Step 1: Prepare your audio file and reference transcription
# Audio: your_audio.wav
# Reference: "your correct transcription text"

# Step 2: Run evaluation
python metrics/audio_ml_evaluator.py "your_audio.wav" "your correct transcription text" --save-report --confusion-analysis

# Step 3: Check generated files
# - evaluation_report_*.json (detailed metrics)
# - confusion_analysis_*_report.txt (error analysis)
# - confusion_analysis_*_heatmap.png (visualization)
# - confusion_analysis_*_phonetic.png (phonetic analysis)
```

**Output Metrics**:
- Word Error Rate (WER): Industry standard accuracy metric
- Character Error Rate (CER): Fine-grained character-level accuracy
- F1-Score: Harmonic mean of precision and recall
- Processing Time: Real-time performance factor
- Confidence Scores: System confidence in transcription
- Error Patterns: Most common transcription mistakes

### Method 2: Batch Audio Evaluation

**Best for**: Evaluating multiple audio files systematically

```python
# create_batch_benchmark.py
from metrics import AudioEvaluator
import json
import os

def batch_evaluate_audio_files(audio_files_with_references):
    """
    Evaluate multiple audio files and generate aggregate report
    
    Args:
        audio_files_with_references: List of (audio_path, reference_text) tuples
    """
    evaluator = AudioEvaluator()
    results = []
    
    for i, (audio_path, reference_text) in enumerate(audio_files_with_references, 1):
        print(f"Evaluating {i}/{len(audio_files_with_references)}: {os.path.basename(audio_path)}")
        
        # Load and transcribe
        audio_data, _, duration = evaluator.load_audio_file(audio_path)
        if audio_data is None:
            continue
            
        hypothesis, processing_time, confidence = evaluator.transcribe_audio(audio_data, audio_path)
        if hypothesis is None:
            continue
        
        # Evaluate
        evaluation_results, metrics = evaluator.evaluate_transcription(
            reference_text, hypothesis, audio_path, processing_time, confidence
        )
        
        results.append({
            'file': os.path.basename(audio_path),
            'duration_seconds': duration,
            'word_error_rate': evaluation_results['transcription_metrics']['word_error_rate'],
            'word_accuracy': evaluation_results['transcription_metrics']['word_accuracy'],
            'f1_score': evaluation_results['transcription_metrics']['word_f1_score'],
            'processing_time_ms': processing_time,
            'confidence': confidence
        })
    
    # Generate aggregate statistics
    if results:
        avg_wer = sum(r['word_error_rate'] for r in results) / len(results)
        avg_accuracy = sum(r['word_accuracy'] for r in results) / len(results)
        avg_f1 = sum(r['f1_score'] for r in results) / len(results)
        avg_processing_time = sum(r['processing_time_ms'] for r in results) / len(results)
        
        print(f"\nBATCH EVALUATION RESULTS:")
        print(f"Files processed: {len(results)}")
        print(f"Average WER: {avg_wer:.3f} ({avg_wer*100:.1f}%)")
        print(f"Average Accuracy: {avg_accuracy:.3f} ({avg_accuracy*100:.1f}%)")
        print(f"Average F1-Score: {avg_f1:.3f}")
        print(f"Average Processing Time: {avg_processing_time:.1f}ms")
        
        # Save batch report
        with open('batch_evaluation_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_files': len(results),
                    'average_wer': avg_wer,
                    'average_accuracy': avg_accuracy,
                    'average_f1_score': avg_f1,
                    'average_processing_time_ms': avg_processing_time
                },
                'individual_results': results
            }, f, indent=2)
        
        print(f"Batch report saved to: batch_evaluation_report.json")

# Usage example
if __name__ == "__main__":
    test_files = [
        ("audio1.wav", "first reference transcription"),
        ("audio2.mp3", "second reference transcription"),
        ("audio3.wav", "third reference transcription"),
    ]
    
    batch_evaluate_audio_files(test_files)
```

### Method 3: Real-time Performance Monitoring

**Best for**: Monitoring EchoLine performance during live usage

```python
# integrate_performance_monitoring.py
from metrics import PerformanceMonitor, TranscriptionEvaluator
import time

class EchoLineWithMetrics:
    """EchoLine application with integrated performance monitoring"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.accuracy_evaluator = TranscriptionEvaluator()
        self.recent_transcriptions = []
        
    def start_session(self):
        """Start a monitoring session"""
        self.performance_monitor.start_monitoring()
        print("Performance monitoring started")
    
    def process_audio_sample(self, audio_data, audio_id, ground_truth=None):
        """Process audio with performance tracking"""
        
        # Mark audio received
        self.performance_monitor.mark_audio_received(audio_id)
        
        # Your existing transcription logic here
        start_time = time.time()
        
        # Simulate transcription (replace with your actual transcription code)
        transcription = "your transcription result"
        confidence = 0.95
        
        processing_time = (time.time() - start_time) * 1000
        
        # Mark processing complete
        self.performance_monitor.mark_audio_processed(audio_id, confidence)
        
        # Simulate UI update
        time.sleep(0.01)  # UI update delay
        self.performance_monitor.mark_ui_updated(audio_id)
        
        # Optional: Evaluate accuracy if ground truth available
        if ground_truth:
            metrics = self.accuracy_evaluator.evaluate_transcription(ground_truth, transcription)
            self.recent_transcriptions.append((ground_truth, transcription))
            print(f"Sample accuracy: {metrics.word_accuracy*100:.1f}%")
        
        return transcription, confidence
    
    def get_current_performance(self):
        """Get current performance metrics"""
        metrics = self.performance_monitor.get_current_metrics()
        return {
            'latency_ms': metrics.audio_to_display_latency,
            'cpu_percent': metrics.cpu_usage_percent,
            'memory_mb': metrics.memory_usage_mb,
            'total_processed': metrics.total_words_processed
        }
    
    def end_session_and_report(self):
        """End session and generate comprehensive report"""
        
        # Stop monitoring
        self.performance_monitor.stop_monitoring()
        
        # Get performance report
        perf_report = self.performance_monitor.get_detailed_report()
        
        # Calculate accuracy if we have transcriptions
        accuracy_summary = None
        if self.recent_transcriptions:
            accuracy_metrics = self.accuracy_evaluator.evaluate_multiple_samples(
                self.recent_transcriptions
            )
            accuracy_summary = {
                'average_wer': accuracy_metrics.word_error_rate,
                'average_accuracy': accuracy_metrics.word_accuracy,
                'average_f1': accuracy_metrics.word_f1_score,
                'total_samples': len(self.recent_transcriptions)
            }
        
        # Save comprehensive session report
        session_report = {
            'session_end_time': time.time(),
            'performance_summary': perf_report['summary'],
            'accuracy_summary': accuracy_summary
        }
        
        report_file = self.performance_monitor.save_report("session_report")
        print(f"Session report saved to: {report_file}")
        
        return session_report

# Usage example
if __name__ == "__main__":
    app = EchoLineWithMetrics()
    
    # Start monitoring session
    app.start_session()
    
    # Simulate processing multiple audio samples
    for i in range(10):
        audio_data = f"sample_audio_{i}"  # Your actual audio data
        ground_truth = f"reference text {i}"  # Optional reference
        
        transcription, confidence = app.process_audio_sample(
            audio_data, f"sample_{i}", ground_truth
        )
        
        # Check real-time performance
        current_perf = app.get_current_performance()
        print(f"Current latency: {current_perf['latency_ms']:.1f}ms")
        
        time.sleep(1)  # Simulate real-time interval
    
    # End session and get report
    final_report = app.end_session_and_report()
```

### Method 4: Comprehensive Error Analysis

**Best for**: Deep-dive analysis of transcription errors

```python
# comprehensive_error_analysis.py
from metrics import TranscriptionEvaluator, ConfusionMatrixAnalyzer
import json

def comprehensive_error_analysis(transcription_pairs, output_prefix="error_analysis"):
    """
    Perform comprehensive error analysis on transcription pairs
    
    Args:
        transcription_pairs: List of (reference, hypothesis) tuples
        output_prefix: Prefix for output files
    """
    
    evaluator = TranscriptionEvaluator()
    analyzer = ConfusionMatrixAnalyzer()
    
    print(f"Analyzing {len(transcription_pairs)} transcription pairs...")
    
    # Process all pairs
    individual_results = []
    for i, (reference, hypothesis) in enumerate(transcription_pairs, 1):
        print(f"  Processing pair {i}/{len(transcription_pairs)}")
        
        # Evaluate individual pair
        metrics = evaluator.evaluate_transcription(reference, hypothesis)
        
        # Add to confusion analyzer
        if metrics.confusion_matrix:
            analyzer.add_confusion_data(metrics.confusion_matrix)
        
        # Store individual result
        individual_results.append({
            'pair_id': i,
            'reference': reference,
            'hypothesis': hypothesis,
            'word_error_rate': metrics.word_error_rate,
            'word_accuracy': metrics.word_accuracy,
            'substitutions': metrics.substitutions,
            'insertions': metrics.insertions,
            'deletions': metrics.deletions
        })
    
    # Generate aggregate metrics
    aggregate_metrics = evaluator.evaluate_multiple_samples(transcription_pairs)
    
    # Generate comprehensive error analysis
    print("Generating visualizations and reports...")
    
    # Generate confusion matrix visualizations
    analyzer.generate_visualization(f"{output_prefix}_confusion_heatmap.png")
    analyzer.analyze_phonetic_similarity(f"{output_prefix}_phonetic_analysis.png")
    
    # Generate detailed text report
    detailed_report = analyzer.generate_detailed_report()
    with open(f"{output_prefix}_detailed_report.txt", 'w', encoding='utf-8') as f:
        f.write(detailed_report)
    
    # Generate comprehensive JSON report
    comprehensive_report = {
        'analysis_metadata': {
            'total_pairs': len(transcription_pairs),
            'output_prefix': output_prefix
        },
        'aggregate_metrics': {
            'word_error_rate': aggregate_metrics.word_error_rate,
            'word_accuracy': aggregate_metrics.word_accuracy,
            'word_precision': aggregate_metrics.word_precision,
            'word_recall': aggregate_metrics.word_recall,
            'word_f1_score': aggregate_metrics.word_f1_score,
            'character_error_rate': aggregate_metrics.char_error_rate,
            'total_words': aggregate_metrics.total_words,
            'total_substitutions': aggregate_metrics.substitutions,
            'total_insertions': aggregate_metrics.insertions,
            'total_deletions': aggregate_metrics.deletions
        },
        'individual_results': individual_results
    }
    
    with open(f"{output_prefix}_comprehensive_report.json", 'w', encoding='utf-8') as f:
        json.dump(comprehensive_report, f, indent=2)
    
    print(f"Comprehensive error analysis complete!")
    print(f"Generated files:")
    print(f"  - {output_prefix}_confusion_heatmap.png")
    print(f"  - {output_prefix}_phonetic_analysis.png") 
    print(f"  - {output_prefix}_detailed_report.txt")
    print(f"  - {output_prefix}_comprehensive_report.json")
    
    return comprehensive_report

# Usage example
if __name__ == "__main__":
    # Example transcription pairs with various types of errors
    test_pairs = [
        ("hello world", "helo world"),                    # Substitution
        ("the quick brown fox", "the quik brown fox"),   # Substitution  
        ("speech recognition", "speach recognition"),     # Substitution
        ("machine learning", "machine lerning"),         # Deletion
        ("artificial intelligence", "artificial intelligence system"),  # Insertion
        ("deep neural networks", "dep neural networks"), # Substitution
    ]
    
    report = comprehensive_error_analysis(test_pairs, "my_error_analysis")
    
    # Print summary
    agg = report['aggregate_metrics']
    print(f"\nSUMMARY:")
    print(f"Overall WER: {agg['word_error_rate']:.3f} ({agg['word_error_rate']*100:.1f}%)")
    print(f"Overall Accuracy: {agg['word_accuracy']:.3f} ({agg['word_accuracy']*100:.1f}%)")
    print(f"F1-Score: {agg['word_f1_score']:.3f}")
```

## Understanding the Metrics

### Core Accuracy Metrics

- **Word Error Rate (WER)**: `(Substitutions + Insertions + Deletions) / Total Reference Words`
  - Lower is better (0.0 = perfect, 1.0 = completely wrong)
  - Industry standard for speech recognition evaluation
  - Good: < 0.1 (10%), Acceptable: 0.1-0.3 (10-30%), Poor: > 0.3 (30%+)

- **Word Accuracy**: `Correct Words / Total Reference Words`  
  - Higher is better (1.0 = perfect, 0.0 = completely wrong)
  - Inverse relationship with WER

- **Character Error Rate (CER)**: Same as WER but at character level
  - More sensitive to spelling and punctuation errors
  - Useful for detailed analysis

- **F1-Score**: `2 × (Precision × Recall) / (Precision + Recall)`
  - Harmonic mean of precision and recall
  - Balanced measure of overall performance
  - Range: 0.0 to 1.0 (higher is better)

### Performance Metrics

- **Processing Time**: Time taken to transcribe audio
- **Real-time Factor**: `Processing Time / Audio Duration`
  - < 1.0 = faster than real-time
  - = 1.0 = real-time processing  
  - > 1.0 = slower than real-time

- **Latency**: End-to-end delay from audio input to UI display
- **CPU/Memory Usage**: System resource consumption
- **Confidence Score**: System's confidence in transcription quality

## Output Files Reference

### Generated by AudioMLEvaluator

- **`evaluation_report_*.json`**: Complete evaluation data including:
  - Transcription metrics (WER, CER, F1, etc.)
  - Performance metrics (latency, CPU, memory)
  - Original reference and hypothesis texts
  - Processing timestamps and metadata

- **`confusion_analysis_*_report.txt`**: Human-readable error analysis:
  - Most confused word pairs
  - Error pattern statistics
  - Phonetic similarity analysis
  - Word accuracy distributions

- **`confusion_analysis_*_heatmap.png`**: Visual confusion matrix showing:
  - Word substitution patterns
  - Error frequency heatmap
  - Most problematic word pairs

- **`confusion_analysis_*_phonetic.png`**: Phonetic analysis visualization:
  - Edit distance distribution
  - Word length correlation analysis
  - Similarity ratio statistics
  - High-frequency similar errors

### Generated by SystemPerformanceMonitor

- **`performance_report_*.json`**: Detailed performance data:
  - Latency measurements per audio sample
  - CPU and memory usage over time
  - Audio drop counts and patterns
  - Statistical summaries (mean, median, P95, P99)

## Integration with Existing EchoLine

### Basic Integration

```python
# In your main EchoLine application
from metrics import PerformanceMonitor, TranscriptionEvaluator

class EchoLineApp:
    def __init__(self):
        # Your existing initialization
        self.performance_monitor = PerformanceMonitor()
        self.accuracy_evaluator = TranscriptionEvaluator()
        
    def start_transcription_session(self):
        self.performance_monitor.start_monitoring()
        
    def process_audio_chunk(self, audio_data, audio_id):
        # Mark audio received
        self.performance_monitor.mark_audio_received(audio_id)
        
        # Your existing transcription logic
        transcription = self.transcribe(audio_data)
        confidence = self.get_confidence()
        
        # Mark processing complete
        self.performance_monitor.mark_audio_processed(audio_id, confidence)
        
        # Update UI
        self.update_ui(transcription)
        self.performance_monitor.mark_ui_updated(audio_id)
        
        return transcription
        
    def end_session(self):
        self.performance_monitor.stop_monitoring()
        report = self.performance_monitor.get_detailed_report()
        return report
```

## Quick Start Commands

```bash
# Test with a single audio file
python metrics/audio_ml_evaluator.py "test.wav" "hello world" --save-report

# Full evaluation with visualization
python metrics/audio_ml_evaluator.py "speech.mp3" "reference text" --save-report --confusion-analysis --output-prefix my_test

# Check package is working
python -c "from metrics import *; print('All components loaded successfully')"
```

## Requirements

- **Python**: 3.7+
- **Core Dependencies**: numpy, matplotlib, seaborn, pandas, psutil
- **Audio Support**: librosa, soundfile (for MP3/FLAC files)
- **Speech Recognition**: vosk (EchoLine's transcription engine)

## Benchmarking Best Practices

1. **Use diverse audio samples**: Different speakers, accents, noise levels
2. **Test various content types**: Casual speech, technical terms, proper nouns
3. **Monitor over time**: Track performance changes across versions
4. **Compare against baselines**: Establish performance targets
5. **Regular evaluation**: Set up automated benchmarking for continuous monitoring

## Performance Targets

Based on industry standards for speech recognition systems:

- **Excellent**: WER < 0.05 (5%), F1-Score > 0.95
- **Good**: WER 0.05-0.15 (5-15%), F1-Score 0.85-0.95  
- **Acceptable**: WER 0.15-0.25 (15-25%), F1-Score 0.75-0.85
- **Needs Improvement**: WER > 0.25 (25%), F1-Score < 0.75

- **Real-time Performance**: Processing time < audio duration
- **Low Latency**: End-to-end latency < 500ms
- **Resource Efficiency**: CPU usage < 50%, Memory < 1GB

This metrics package provides everything needed to comprehensively evaluate and benchmark your EchoLine speech recognition system!

### 1. AccuracyEvaluator (`accuracy_evaluator.py`)
Evaluates transcription accuracy using industry-standard ML metrics:

```python
from metrics import TranscriptionEvaluator

evaluator = TranscriptionEvaluator()
metrics = evaluator.evaluate_transcription(
    reference="hello world",
    hypothesis="helo world"
)
print(f"WER: {metrics.word_error_rate:.3f}")
```

**Key Features:**
- Word Error Rate (WER) and Character Error Rate (CER) calculation
- Precision, recall, and F1-score for individual words
- Confusion matrix generation for error analysis
- Multi-sample batch evaluation
- Detailed error classification (substitution, insertion, deletion)

### 2. SystemPerformanceMonitor (`system_performance_monitor.py`)
Real-time system performance monitoring:

```python
from metrics import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start_monitoring()

# Your transcription code here
monitor.mark_audio_received("sample_1")
monitor.mark_audio_processed("sample_1", confidence=0.95)
monitor.mark_ui_updated("sample_1")

monitor.stop_monitoring()
report = monitor.get_detailed_report()
```

**Key Features:**
- End-to-end latency tracking (audio → transcription → UI)
- Real-time CPU and memory usage monitoring
- Audio drop detection and counting
- Configurable monitoring intervals
- JSON report generation with statistical summaries

### 3. ErrorPatternAnalyzer (`error_pattern_analyzer.py`)
Advanced error pattern analysis and visualization:

```python
from metrics import ConfusionMatrixAnalyzer

analyzer = ConfusionMatrixAnalyzer()
analyzer.add_confusion_data(confusion_matrix)
analyzer.generate_visualization("error_analysis.png")
report = analyzer.generate_detailed_report()
```

**Key Features:**
- Confusion matrix visualization with heatmaps
- Phonetic similarity analysis using edit distance
- Most common error pattern identification
- Word substitution frequency analysis
- Statistical error distribution reports

### 4. AudioMLEvaluator (`audio_ml_evaluator.py`)
Complete audio file evaluation with ML metrics:

```python
# Command line usage (recommended)
python metrics/audio_ml_evaluator.py "audio.wav" "reference transcription" --save-report --confusion-analysis

# Python usage
from metrics import AudioEvaluator

evaluator = AudioEvaluator()
audio_data, _, _ = evaluator.load_audio_file("audio.wav") 
hypothesis, _, _ = evaluator.transcribe_audio(audio_data)
results, metrics = evaluator.evaluate_transcription("reference", hypothesis)
evaluator.print_comprehensive_results(results, metrics)
```

**Key Features:**
- Audio file loading (WAV, MP3, FLAC with librosa)
- EchoLine transcription integration
- Complete ML metrics evaluation
- Performance monitoring during transcription
- Automated report generation
- Confusion matrix analysis and visualization

## Quick Start

### 1. Basic Transcription Evaluation

```python
from metrics import TranscriptionEvaluator, print_detailed_metrics

evaluator = TranscriptionEvaluator()

# Single evaluation
metrics = evaluator.evaluate_transcription(
    reference="the quick brown fox jumps over the lazy dog",
    hypothesis="the quik brown fox jumps over the lazy dog"
)

print_detailed_metrics(metrics)
```

### 2. Real-time Performance Monitoring

```python
from metrics import PerformanceMonitor
import threading
import time

monitor = PerformanceMonitor()
monitor.start_monitoring()

# Simulate your transcription pipeline
def simulate_transcription():
    for i in range(10):
        audio_id = f"sample_{i}"
        monitor.mark_audio_received(audio_id)
        
        # Simulate processing delay
        time.sleep(0.1)
        
        monitor.mark_audio_processed(audio_id, confidence=0.9)
        monitor.mark_ui_updated(audio_id)
        
        time.sleep(0.5)  # Simulate real-time interval

# Run simulation
thread = threading.Thread(target=simulate_transcription)
thread.start()
thread.join()

monitor.stop_monitoring()
report = monitor.get_detailed_report()
print(f"Average latency: {report['summary']['audio_to_display_latency']:.1f}ms")
```

### 3. Comprehensive Benchmarking

```python
from metrics import BenchmarkRunner

def your_transcribe_function(test_case):
    # Your transcription logic here
    # Return the transcribed text
    return "transcribed text"

runner = BenchmarkRunner()

# Add test cases
runner.add_test_case("test_1", "hello world", metadata={'difficulty': 'easy'})
runner.add_test_case("test_2", "complex technical jargon", metadata={'difficulty': 'hard'})

# Run comprehensive benchmark
results = runner.run_comprehensive_benchmark(
    transcribe_func=your_transcribe_function,
    duration_seconds=60
)

# Save results and generate report
runner.save_results("my_evaluation")
print(runner.generate_report())
```

## Advanced Usage

### Custom Test Cases from File

```python
# test_cases.json
{
  "test_cases": [
    {
      "test_id": "audio_1",
      "reference_text": "This is the correct transcription",
      "audio_file_path": "/path/to/audio1.wav",
      "metadata": {"speaker": "male", "noise_level": "low"}
    }
  ]
}

# Load and run
runner.add_test_cases_from_file("test_cases.json")
results = runner.run_transcription_benchmark(transcribe_function)
```

### Confusion Matrix Analysis

```python
from metrics import ConfusionMatrixAnalyzer

analyzer = ConfusionMatrixAnalyzer()

# Add multiple evaluations
for ref, hyp in test_pairs:
    metrics = evaluator.evaluate_transcription(ref, hyp)
    if metrics.confusion_matrix:
        analyzer.add_confusion_data(metrics.confusion_matrix)

# Generate comprehensive analysis
analyzer.generate_visualization("confusion_heatmap.png")
analyzer.analyze_phonetic_similarity("phonetic_analysis.png")
report = analyzer.generate_detailed_report()
print(report)
```

### Performance Optimization

```python
# Monitor specific aspects
monitor = PerformanceMonitor(
    cpu_interval=0.5,    # Check CPU every 500ms
    memory_interval=1.0,  # Check memory every 1s
    enable_threading=True # Use separate thread for monitoring
)

# Track custom metrics
monitor.mark_custom_event("model_loading_start")
# ... load your model ...
monitor.mark_custom_event("model_loading_complete")
```

## Output Files

The metrics package generates several types of output files:

- **`*_results.json`**: Raw benchmark data in JSON format
- **`*_report.txt`**: Human-readable summary report
- **`*_confusion_matrix.png`**: Confusion matrix heatmap
- **`*_phonetic_analysis.png`**: Phonetic similarity analysis
- **`*_detailed_report.txt`**: Comprehensive error analysis

## Integration with EchoLine

To integrate with your existing EchoLine application:

```python
# In your main transcription loop
from metrics import PerformanceMonitor, TranscriptionEvaluator

monitor = PerformanceMonitor()
evaluator = TranscriptionEvaluator()

# Start monitoring
monitor.start_monitoring()

def on_audio_received(audio_data, audio_id):
    monitor.mark_audio_received(audio_id)
    # Your existing audio processing

def on_transcription_complete(audio_id, transcription, confidence):
    monitor.mark_audio_processed(audio_id, confidence)
    # Your existing transcription handling

def on_ui_updated(audio_id):
    monitor.mark_ui_updated(audio_id)
    # Your existing UI update code

# Periodic evaluation against ground truth
def evaluate_recent_transcriptions(ground_truth_pairs):
    for reference, hypothesis in ground_truth_pairs:
        metrics = evaluator.evaluate_transcription(reference, hypothesis)
        # Log or store metrics
```

## Requirements

- Python 3.7+
- numpy
- matplotlib
- seaborn
- pandas
- psutil
- threading (built-in)
- json (built-in)
- time (built-in)

## Installation

```bash
# Install required dependencies
pip install numpy matplotlib seaborn pandas psutil

# The metrics package is already included in your EchoLine project
```

## Performance Considerations

- **Monitoring Overhead**: The performance monitor adds minimal overhead (~1-2% CPU)
- **Memory Usage**: Metrics storage scales with test duration and frequency
- **Real-time vs Batch**: Use real-time monitoring sparingly in production
- **Thread Safety**: All components are thread-safe for concurrent use

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Adjust monitoring intervals or clear data periodically
2. **Missing Dependencies**: Install required packages with pip
3. **Thread Conflicts**: Ensure proper start/stop of monitoring threads
4. **File Permissions**: Check write access to output directory

### Debug Mode

```python
# Enable verbose logging
monitor = PerformanceMonitor(verbose=True)
evaluator = TranscriptionEvaluator(verbose=True)
```

## Contributing

When adding new metrics or features:

1. Follow the existing class structure and naming conventions
2. Include comprehensive docstrings
3. Add example usage in docstrings
4. Ensure thread safety for real-time components
5. Include error handling and graceful degradation

## License

This metrics package is part of the EchoLine project and follows the same licensing terms.