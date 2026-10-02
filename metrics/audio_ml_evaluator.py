#!/usr/bin/env python3
"""
Audio Evaluation Script for EchoLine

This script takes an audio file path and reference transcription,
uses EchoLine's transcription system to generate a hypothesis,
and returns comprehensive ML evaluation metrics.

Usage:
    python -m metrics.audio_ml_evaluator <audio_file> <reference_text> [options]
    
Example:
    python -m metrics.audio_ml_evaluator audio.wav "hello world this is a test"
    python -m metrics.audio_ml_evaluator audio.mp3 "the quick brown fox" --save-report
"""

import sys
import os
import argparse
import json
import time
import numpy as np

# Add parent directory to path to import echoline and metrics
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from echoline.engine.vosk_recognizer import SpeechRecognizer
    from metrics import TranscriptionEvaluator, PerformanceMonitor, ConfusionMatrixAnalyzer, print_detailed_metrics
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the EchoLine project directory")
    sys.exit(1)

import librosa

class AudioEvaluator:
    """Comprehensive audio evaluation using EchoLine transcription system"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.speech_recognizer = None
        self.transcription_evaluator = TranscriptionEvaluator()
        self.performance_monitor = PerformanceMonitor()
        self.confusion_analyzer = ConfusionMatrixAnalyzer()
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize speech recognition and evaluation components"""
        if self.verbose:
            print("Initializing EchoLine components...")
        
        # Initialize speech recognizer
        self.speech_recognizer = SpeechRecognizer()
        
        if not self.speech_recognizer.model:
            print("ERROR: Failed to initialize Vosk model!")
            print("Please ensure the Vosk model is downloaded and available.")
            print("See the README for where to put the model.")
            return False
        
        if self.verbose:
            print("Speech recognizer initialized successfully")
            print("Evaluation components ready")
        
        return True
    
    def load_audio_file(self, audio_file_path):
        """
        Load audio file and convert to format compatible with EchoLine
        
        Args:
            audio_file_path: Path to audio file (wav, mp3, flac, etc.)
            
        Returns:
            tuple: (audio_data, sample_rate, duration) or (None, None, None) on error
        """
        if not os.path.exists(audio_file_path):
            print(f"ERROR: Audio file not found: {audio_file_path}")
            return None, None, None
        
        try:
            # librosa handles WAV/MP3/FLAC, mixes down to mono and resamples to Vosk's 16kHz
            audio_float, sample_rate = librosa.load(audio_file_path, sr=16000, mono=True)
            audio_data = np.clip(np.round(audio_float * 32768), -32768, 32767).astype(np.int16)
            
            duration = len(audio_data) / sample_rate
            
            if self.verbose:
                print(f"Successfully loaded audio file: {os.path.basename(audio_file_path)}")
                print(f"   Duration: {duration:.2f} seconds")
                print(f"   Sample rate: {sample_rate} Hz")
                print(f"   Samples: {len(audio_data)}")
            
            return audio_data, sample_rate, duration
            
        except Exception as e:
            print(f"ERROR: Error loading audio file: {e}")
            return None, None, None
    
    def transcribe_audio(self, audio_data, audio_file_path=None):
        """
        Transcribe audio using EchoLine's speech recognition system
        
        Args:
            audio_data: Audio data as numpy array
            audio_file_path: Original file path for logging
            
        Returns:
            tuple: (transcription_text, processing_time_ms, confidence_score)
        """
        if not self.speech_recognizer or not self.speech_recognizer.recognizer:
            return None, 0, 0.0
        
        audio_id = f"eval_{int(time.time())}"
        
        # Start performance monitoring
        self.performance_monitor.start_monitoring()
        self.performance_monitor.mark_audio_received(audio_id)
        
        if self.verbose:
            print("Transcribing audio using EchoLine...")
        
        start_time = time.time()
        
        try:
            # Process audio in chunks (simulate real-time processing)
            recognizer = self.speech_recognizer.recognizer
            recognizer.SetWords(True)  # Vosk only reports per-word confidence with this on
            chunk_size = 4000  # ~250ms chunks at 16kHz
            results = []
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if recognizer.AcceptWaveform(chunk.tobytes()):
                    results.append(json.loads(recognizer.Result()))
            results.append(json.loads(recognizer.FinalResult()))
            
            transcription_parts = [r['text'] for r in results if r.get('text')]
            words = [w for r in results for w in r.get('result', [])]
            confidence = sum(w['conf'] for w in words) / len(words) if words else 0.0
            
            # Combine all transcription parts
            full_transcription = ' '.join(transcription_parts).strip()
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Mark processing complete
            self.performance_monitor.mark_audio_processed(audio_id, word_count=len(words), is_partial=False)
            self.performance_monitor.mark_ui_updated(audio_id)
            
            if self.verbose:
                print(f"Transcription completed in {processing_time:.1f}ms")
                print(f"Result: '{full_transcription}'")
                print(f"Confidence: {confidence:.3f}")
            
            return full_transcription, processing_time, confidence
            
        except Exception as e:
            print(f"ERROR: Error during transcription: {e}")
            return None, 0, 0.0
        
        finally:
            self.performance_monitor.stop_monitoring()
    
    def evaluate_transcription(self, reference_text, hypothesis_text, audio_file_path=None, 
                             processing_time_ms=0, confidence=0.0):
        """
        Evaluate transcription using comprehensive ML metrics
        
        Args:
            reference_text: Ground truth transcription
            hypothesis_text: System-generated transcription
            audio_file_path: Original audio file path
            processing_time_ms: Time taken for transcription
            confidence: Confidence score from recognizer
            
        Returns:
            dict: Comprehensive evaluation results
        """
        if self.verbose:
            print("\nEvaluating transcription accuracy...")
        
        # Basic transcription evaluation
        metrics = self.transcription_evaluator.evaluate_transcription(
            reference_text, hypothesis_text
        )
        
        # Feed the word alignment to the confusion analyzer
        self.confusion_analyzer.add_operation_list(self.transcription_evaluator.last_operations)
        
        # Get performance metrics
        performance_metrics = self.performance_monitor.get_current_metrics()
        
        # Compile comprehensive results
        evaluation_results = {
            'audio_file': os.path.basename(audio_file_path) if audio_file_path else 'unknown',
            'transcription_metrics': {
                'word_error_rate': metrics.word_error_rate,
                'word_accuracy': metrics.word_accuracy,
                'word_precision': metrics.word_precision,
                'word_recall': metrics.word_recall,
                'word_f1_score': metrics.word_f1_score,
                'character_error_rate': metrics.char_error_rate,
                'character_accuracy': metrics.char_accuracy,
                'total_words': metrics.total_words,
                'correct_words': metrics.correct_words,
                'substitutions': metrics.substitutions,
                'insertions': metrics.insertions,
                'deletions': metrics.deletions,
            },
            'performance_metrics': {
                'processing_time_ms': processing_time_ms,
                'confidence_score': confidence,
                'cpu_usage_percent': performance_metrics.cpu_usage_percent,
                'memory_usage_mb': performance_metrics.memory_usage_mb,
                'audio_to_display_latency': performance_metrics.audio_to_display_latency,
            },
            'texts': {
                'reference': reference_text,
                'hypothesis': hypothesis_text,
            },
            'evaluation_timestamp': time.time()
        }
        
        return evaluation_results, metrics
    
    def print_comprehensive_results(self, evaluation_results, metrics):
        """Print comprehensive evaluation results to terminal"""
        print("\n" + "="*80)
        print("ECHOLINE AUDIO EVALUATION RESULTS")
        print("="*80)
        
        # File info
        print(f"Audio File: {evaluation_results['audio_file']}")
        print(f"Evaluation Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Transcription comparison
        print(f"\nTRANSCRIPTION COMPARISON:")
        print(f"Reference:  '{evaluation_results['texts']['reference']}'")
        print(f"Hypothesis: '{evaluation_results['texts']['hypothesis']}'")
        
        # Detailed metrics
        print(f"\nTRANSCRIPTION ACCURACY METRICS:")
        print_detailed_metrics(metrics, "EchoLine Evaluation")
        
        # Performance metrics
        perf = evaluation_results['performance_metrics']
        print(f"\nPERFORMANCE METRICS:")
        print(f"Processing Time: {perf['processing_time_ms']:.1f}ms")
        print(f"Confidence Score: {perf['confidence_score']:.3f}")
        print(f"CPU Usage: {perf['cpu_usage_percent']:.1f}%")
        print(f"Memory Usage: {perf['memory_usage_mb']:.1f}MB")
        print(f"End-to-End Latency: {perf['audio_to_display_latency']:.1f}ms")
        
        # Summary
        trans = evaluation_results['transcription_metrics']
        print(f"\nSUMMARY:")
        print(f"Word Accuracy: {trans['word_accuracy']*100:.1f}%")
        print(f"Word Error Rate: {trans['word_error_rate']*100:.1f}%")
        print(f"F1-Score: {trans['word_f1_score']:.3f}")
        print(f"Character Accuracy: {trans['character_accuracy']*100:.1f}%")
        
        print("="*80)
    
    def save_evaluation_report(self, evaluation_results, output_file=None):
        """Save detailed evaluation report to file"""
        if output_file is None:
            timestamp = int(time.time())
            audio_name = evaluation_results['audio_file'].replace('.', '_')
            output_file = f"evaluation_report_{audio_name}_{timestamp}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(evaluation_results, f, indent=2, default=str)
            
            print(f"Evaluation report saved to: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"ERROR: Error saving report: {e}")
            return None
    
    def generate_confusion_analysis(self, output_prefix=None):
        """Generate confusion matrix analysis and visualizations"""
        if not self.confusion_analyzer.confusion_data:
            print("WARNING: No confusion data available for analysis")
            return
        
        if output_prefix is None:
            output_prefix = f"confusion_analysis_{int(time.time())}"
        
        try:
            # Generate detailed report
            report = self.confusion_analyzer.generate_detailed_report()
            
            # Save text report
            report_file = f"{output_prefix}_report.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Confusion analysis report saved to: {report_file}")
            
            # Generate visualizations
            try:
                self.confusion_analyzer.generate_visualization(f"{output_prefix}_heatmap.png")
                print(f"Confusion matrix heatmap saved to: {output_prefix}_heatmap.png")
            except Exception as e:
                print(f"WARNING: Could not generate heatmap: {e}")
            
            try:
                self.confusion_analyzer.analyze_phonetic_similarity(f"{output_prefix}_phonetic.png")
                print(f"Phonetic analysis saved to: {output_prefix}_phonetic.png")
            except Exception as e:
                print(f"WARNING: Could not generate phonetic analysis: {e}")
                
        except Exception as e:
            print(f"ERROR: Error generating confusion analysis: {e}")

def exit_code_for_wer(wer):
    """0: good (< 10% WER), 1: acceptable (10-30%), 2: poor (>= 30%)"""
    if wer < 0.1:
        return 0
    return 1 if wer < 0.3 else 2

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description="Evaluate audio transcription using EchoLine system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m metrics.audio_ml_evaluator audio.wav "hello world"
  python -m metrics.audio_ml_evaluator audio.mp3 "the quick brown fox jumps over the lazy dog" --save-report
  python -m metrics.audio_ml_evaluator test.flac "artificial intelligence" --confusion-analysis --quiet
        """
    )
    
    parser.add_argument('audio_file', help='Path to audio file (wav, mp3, flac, etc.)')
    parser.add_argument('reference_text', help='Ground truth transcription text')
    parser.add_argument('--save-report', action='store_true', 
                        help='Save detailed evaluation report to JSON file')
    parser.add_argument('--confusion-analysis', action='store_true',
                        help='Generate confusion matrix analysis and visualizations')
    parser.add_argument('--output-prefix', type=str,
                        help='Prefix for output files (default: auto-generated)')
    parser.add_argument('--quiet', action='store_true',
                        help='Disable verbose output')
    
    args = parser.parse_args()
    
    # Initialize evaluator
    evaluator = AudioEvaluator(verbose=not args.quiet)
    
    if not evaluator.speech_recognizer or not evaluator.speech_recognizer.model:
        print("ERROR: Failed to initialize EchoLine speech recognizer")
        sys.exit(1)
    
    # Load audio file
    audio_data, sample_rate, duration = evaluator.load_audio_file(args.audio_file)
    
    if audio_data is None:
        print("ERROR: Failed to load audio file")
        sys.exit(1)
    
    # Transcribe audio
    hypothesis_text, processing_time, confidence = evaluator.transcribe_audio(
        audio_data, args.audio_file
    )
    
    if hypothesis_text is None:
        print("ERROR: Failed to transcribe audio")
        sys.exit(1)
    
    # Evaluate transcription
    evaluation_results, metrics = evaluator.evaluate_transcription(
        args.reference_text, hypothesis_text, args.audio_file, processing_time, confidence
    )
    
    # Print results
    evaluator.print_comprehensive_results(evaluation_results, metrics)
    
    # Save report if requested
    if args.save_report:
        output_file = None
        if args.output_prefix:
            output_file = f"{args.output_prefix}_report.json"
        evaluator.save_evaluation_report(evaluation_results, output_file)
    
    # Generate confusion analysis if requested
    if args.confusion_analysis:
        evaluator.generate_confusion_analysis(args.output_prefix)
    
    # Exit with appropriate code
    sys.exit(exit_code_for_wer(evaluation_results['transcription_metrics']['word_error_rate']))

if __name__ == "__main__":
    main()