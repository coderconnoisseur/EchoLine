import sys
import threading
from PySide6.QtWidgets import QApplication

from utils.signals import OverlaySignals
from ui.overlay_ui import YouTubeCaptionOverlay
from audio.capture import AudioCapture
from transcription.speech_recognition import SpeechRecognizer

class EchoLineApp:
    """Main application class that orchestrates all components"""
    
    def __init__(self):
        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("EchoLine")
        self.app.setApplicationVersion("2.0")
        
        # Initialize signals for thread-safe communication
        self.signals = OverlaySignals()
        
        # Initialize components
        self.speech_recognizer = SpeechRecognizer()
        self.audio_capture = AudioCapture(callback=self.process_audio)
        self.overlay = YouTubeCaptionOverlay(self.signals)
        
        # Connect close event
        self.overlay.destroyed.connect(self.cleanup)
    
    def process_audio(self, audio_data):
        """Process audio data through speech recognizer"""
        if not self.speech_recognizer.recognizer:
            return
            
        text, is_partial = self.speech_recognizer.process_audio_data(audio_data)
        if text:
            self.signals.update_text.emit(text, is_partial)
    
    def start_capture(self):
        """Start audio capture in a separate thread"""
        def start_audio_thread():
            try:
                self.audio_capture.start()
            except Exception as e:
                print(f"Error starting audio capture: {e}")
        
        capture_thread = threading.Thread(target=start_audio_thread, daemon=True)
        capture_thread.start()
    
    def cleanup(self):
        """Clean up resources before exit"""
        self.audio_capture.stop()
    
    def run(self):
        """Run the application"""
        try:
            # Start audio capture
            self.start_capture()
            
            # Run the application
            return self.app.exec()
        except Exception as e:
            print(f"Error running application: {e}")
            return 1
        finally:
            self.cleanup()