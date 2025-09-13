import time
import threading
import psutil
import json
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import statistics

@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    # Latency metrics (milliseconds)
    audio_to_display_latency: float = 0.0
    transcription_latency: float = 0.0
    ui_update_latency: float = 0.0
    
    # Accuracy metrics
    total_words_processed: int = 0
    partial_updates_count: int = 0
    final_updates_count: int = 0
    
    # Performance metrics
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    audio_queue_size: int = 0
    audio_queue_max_size: int = 0
    audio_drops: int = 0
    
    # System metrics
    ui_fps: float = 0.0
    model_load_time: float = 0.0
    total_runtime: float = 0.0

class PerformanceMonitor:
    """Monitors and tracks application performance metrics"""
    
    def __init__(self, max_history=1000):
        self.max_history = max_history
        self.start_time = time.time()
        
        # Metric histories
        self.latency_history = deque(maxlen=max_history)
        self.cpu_history = deque(maxlen=max_history)
        self.memory_history = deque(maxlen=max_history)
        self.fps_history = deque(maxlen=max_history)
        
        # Counters
        self.audio_drops = 0
        self.partial_updates = 0
        self.final_updates = 0
        self.total_words = 0
        
        # Timing data
        self.audio_timestamps = {}
        self.model_load_time = 0.0
        
        # System monitoring
        self.process = psutil.Process()
        self.monitoring = False
        self.monitor_thread = None
        
        # Performance log
        self.performance_log = []
    
    def start_monitoring(self):
        """Start continuous performance monitoring"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        print("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self.monitoring:
            try:
                # Sample system metrics
                cpu_percent = self.process.cpu_percent()
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                
                self.cpu_history.append(cpu_percent)
                self.memory_history.append(memory_mb)
                
                # Log significant events
                if cpu_percent > 80:
                    self._log_event("high_cpu", {"cpu_percent": cpu_percent})
                if memory_mb > 500:  # 500MB threshold
                    self._log_event("high_memory", {"memory_mb": memory_mb})
                
                time.sleep(1.0)  # Sample every second
                
            except Exception as e:
                print(f"Error in performance monitoring: {e}")
    
    def mark_audio_received(self, audio_id: str):
        """Mark when audio chunk is received"""
        self.audio_timestamps[audio_id] = {
            'received': time.time(),
            'processed': None,
            'displayed': None
        }
    
    def mark_audio_processed(self, audio_id: str, word_count: int = 0, is_partial: bool = True):
        """Mark when audio chunk is processed by Vosk"""
        if audio_id in self.audio_timestamps:
            self.audio_timestamps[audio_id]['processed'] = time.time()
            
            # Update counters
            if is_partial:
                self.partial_updates += 1
            else:
                self.final_updates += 1
                self.total_words += word_count
    
    def mark_ui_updated(self, audio_id: str):
        """Mark when UI is updated with transcription"""
        if audio_id in self.audio_timestamps:
            self.audio_timestamps[audio_id]['displayed'] = time.time()
            
            # Calculate latencies
            timestamps = self.audio_timestamps[audio_id]
            if all(timestamps.values()):
                audio_to_display = (timestamps['displayed'] - timestamps['received']) * 1000
                transcription_latency = (timestamps['processed'] - timestamps['received']) * 1000
                ui_latency = (timestamps['displayed'] - timestamps['processed']) * 1000
                
                self.latency_history.append({
                    'audio_to_display': audio_to_display,
                    'transcription': transcription_latency,
                    'ui_update': ui_latency,
                    'timestamp': time.time()
                })
                
                # Clean up old timestamps
                if len(self.audio_timestamps) > 100:
                    oldest_id = min(self.audio_timestamps.keys(), 
                                   key=lambda k: self.audio_timestamps[k]['received'])
                    del self.audio_timestamps[oldest_id]
    
    def record_audio_drop(self):
        """Record an audio buffer drop/overflow"""
        self.audio_drops += 1
        self._log_event("audio_drop", {"total_drops": self.audio_drops})
    
    def record_model_load_time(self, load_time: float):
        """Record Vosk model loading time"""
        self.model_load_time = load_time
        self._log_event("model_loaded", {"load_time_ms": load_time * 1000})
    
    def record_fps(self, fps: float):
        """Record UI frame rate"""
        self.fps_history.append(fps)
    
    def record_queue_size(self, current_size: int, max_size: int):
        """Record audio queue statistics"""
        # This can be called periodically to track queue health
        pass
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log a performance event"""
        event = {
            'timestamp': time.time(),
            'event': event_type,
            'data': data
        }
        self.performance_log.append(event)
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics snapshot"""
        # Calculate averages from recent history
        recent_latency = list(self.latency_history)[-10:]  # Last 10 samples
        recent_cpu = list(self.cpu_history)[-10:]
        recent_memory = list(self.memory_history)[-10:]
        recent_fps = list(self.fps_history)[-10:]
        
        return PerformanceMetrics(
            audio_to_display_latency=statistics.mean([l['audio_to_display'] for l in recent_latency]) if recent_latency else 0,
            transcription_latency=statistics.mean([l['transcription'] for l in recent_latency]) if recent_latency else 0,
            ui_update_latency=statistics.mean([l['ui_update'] for l in recent_latency]) if recent_latency else 0,
            
            total_words_processed=self.total_words,
            partial_updates_count=self.partial_updates,
            final_updates_count=self.final_updates,
            
            cpu_usage_percent=statistics.mean(recent_cpu) if recent_cpu else 0,
            memory_usage_mb=statistics.mean(recent_memory) if recent_memory else 0,
            audio_drops=self.audio_drops,
            
            ui_fps=statistics.mean(recent_fps) if recent_fps else 0,
            model_load_time=self.model_load_time,
            total_runtime=time.time() - self.start_time
        )
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """Generate detailed performance report"""
        metrics = self.get_current_metrics()
        
        # Calculate percentiles for latency
        latencies = [l['audio_to_display'] for l in self.latency_history]
        
        report = {
            'summary': asdict(metrics),
            'latency_analysis': {
                'p50_ms': statistics.median(latencies) if latencies else 0,
                'p95_ms': self._percentile(latencies, 95) if latencies else 0,
                'p99_ms': self._percentile(latencies, 99) if latencies else 0,
                'min_ms': min(latencies) if latencies else 0,
                'max_ms': max(latencies) if latencies else 0,
            },
            'resource_usage': {
                'peak_cpu_percent': max(self.cpu_history) if self.cpu_history else 0,
                'peak_memory_mb': max(self.memory_history) if self.memory_history else 0,
                'avg_cpu_percent': statistics.mean(self.cpu_history) if self.cpu_history else 0,
                'avg_memory_mb': statistics.mean(self.memory_history) if self.memory_history else 0,
            },
            'reliability': {
                'audio_drop_rate': self.audio_drops / max(1, self.partial_updates + self.final_updates),
                'uptime_seconds': time.time() - self.start_time,
            },
            'recent_events': self.performance_log[-20:],  # Last 20 events
        }
        
        return report
    
    def _percentile(self, data, percentile):
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def save_report(self, filename: str = None):
        """Save performance report to file"""
        if filename is None:
            filename = f"echoline_performance_{int(time.time())}.json"
        
        report = self.get_detailed_report()
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Performance report saved to: {filename}")
            return filename
        except Exception as e:
            print(f"Error saving performance report: {e}")
            return None
    
    def print_live_stats(self):
        """Print live performance statistics"""
        metrics = self.get_current_metrics()
        
        print("\n" + "="*50)
        print("ECHOLINE PERFORMANCE MONITOR")
        print("="*50)
        print(f"Runtime: {metrics.total_runtime:.1f}s")
        print(f"Model Load Time: {metrics.model_load_time*1000:.1f}ms")
        print()
        print("LATENCY:")
        print(f"  Audio→Display: {metrics.audio_to_display_latency:.1f}ms")
        print(f"  Transcription:  {metrics.transcription_latency:.1f}ms")
        print(f"  UI Update:      {metrics.ui_update_latency:.1f}ms")
        print()
        print("THROUGHPUT:")
        print(f"  Words Processed: {metrics.total_words_processed}")
        print(f"  Partial Updates: {metrics.partial_updates_count}")
        print(f"  Final Updates:   {metrics.final_updates_count}")
        print(f"  Audio Drops:     {metrics.audio_drops}")
        print()
        print("RESOURCES:")
        print(f"  CPU Usage:    {metrics.cpu_usage_percent:.1f}%")
        print(f"  Memory Usage: {metrics.memory_usage_mb:.1f}MB")
        print(f"  UI FPS:       {metrics.ui_fps:.1f}")
        print("="*50)