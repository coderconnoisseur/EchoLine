from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect, QPushButton
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, Signal, QObject
from PySide6.QtGui import QFont, QColor, QShortcut, QKeySequence
import sys
import queue
import threading
import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer, Model
import json

class OverlaySignals(QObject):
    """Signal object for thread-safe GUI updates"""
    update_text = Signal(str, bool)  # text, is_partial

class YouTubeCaptionOverlay(QWidget):
    def __init__(self):
        super().__init__()
        
        # State variables
        self.is_capturing = False
        
        # Audio capture setup
        self.samplerate = 16000
        self.q = queue.Queue()
        
        # Initialize signals for thread-safe GUI updates
        self.signals = OverlaySignals()
        self.signals.update_text.connect(self._update_caption_safe)
        
        # Initialize Vosk model and recognizer
        try:
            self.model = Model("C:\\Users\\Acer\\.cache\\vosk\\vosk-model-small-en-us-0.15")
            self.recognizer = KaldiRecognizer(self.model, 16000)
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            self.model = None
            self.recognizer = None
        
        # Window setup
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowTitle("Live Caption Overlay")

        # Create close button (initially hidden)
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(24, 24)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 68, 68, 180);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 68, 68, 255);
            }
            QPushButton:pressed {
                background-color: rgba(200, 50, 50, 255);
            }
        """)
        self.close_button.clicked.connect(self.close_app)
        self.close_button.hide()  # Initially hidden

        self.caption_label = QLabel("Ready for live captions...")
        self.caption_label.setAlignment(Qt.AlignCenter)
        self.caption_label.setWordWrap(True)
        self.caption_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0,0,0,0.6);
                border-radius: 18px;
                padding: 12px 32px;
                font-family: 'Arial', 'Roboto', 'Segoe UI', sans-serif;
                font-size: 28px;
                font-weight: 500;
                letter-spacing: 0.5px;
                line-height: 1.4;
            }
        """)
        font = QFont("Arial", 28, QFont.Medium)
        self.caption_label.setFont(font)

        # Add shadow for text visibility
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0,0,0,220))
        shadow.setOffset(2, 2)
        self.caption_label.setGraphicsEffect(shadow)

        # Layout setup with close button positioned at corner of caption
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create a container for the caption and close button
        caption_container = QWidget()
        caption_container.setAttribute(Qt.WA_TranslucentBackground)
        
        # Use absolute positioning for precise control
        caption_layout = QVBoxLayout(caption_container)
        caption_layout.setContentsMargins(0, 0, 0, 0)
        caption_layout.addWidget(self.caption_label, alignment=Qt.AlignCenter)
        
        # Position close button relative to caption container
        self.close_button.setParent(caption_container)
        self.close_button.move(0, 0)  # Will be repositioned in resize_overlay
        
        layout.addWidget(caption_container, alignment=Qt.AlignCenter)

        self.setLayout(layout)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.caption_label.setMouseTracking(True)

        # Store caption container reference for button positioning
        self.caption_container = caption_container

        # Keyboard shortcuts
        self.close_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.close_shortcut.activated.connect(self.close_app)
        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.close_app)

        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(200)
        self.opacity_anim.setEasingCurve(QEasingCurve.InOutCubic)

        # Caption state management
        self.current_sentence = ""  # Complete sentence being built
        self.partial_text = ""      # Current partial word/phrase
        self.last_final_text = ""   # Last complete sentence
        
        self.resize_overlay()
        self.show()

        # Listen for screen geometry changes
        QApplication.instance().primaryScreen().geometryChanged.connect(self.resize_overlay)

    def enterEvent(self, event):
        """Show close button on mouse hover"""
        self.close_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide close button when mouse leaves"""
        self.close_button.hide()
        super().leaveEvent(event)

    def close_app(self):
        """Close the application gracefully"""
        print("Closing EchoLine...")
        self.is_capturing = False
        self.stop_capture()
        QApplication.quit()

    def update_caption(self, text, is_partial=False):
        """Thread-safe method to update caption text"""
        # Emit signal to update UI from main thread
        self.signals.update_text.emit(text, is_partial)

    def _update_caption_safe(self, text, is_partial=False):
        """Update caption text with YouTube-style behavior"""
        if not text.strip():
            # If empty text, show listening message
            if not self.current_sentence and not self.partial_text:
                self.caption_label.setText("Listening for audio...")
            return
            
        if is_partial:
            # Partial text - just append/update without animation
            self.partial_text = text
            # Combine current sentence with partial text
            display_text = self.current_sentence
            if display_text and self.partial_text:
                display_text += " " + self.partial_text
            elif self.partial_text:
                display_text = self.partial_text
                
            # Update label directly without animation
            self.caption_label.setText(display_text)
        else:
            # Final text - this is a complete sentence/phrase
            new_sentence = text.strip()
            
            # Check if this is actually new content
            if new_sentence == self.last_final_text:
                return
                
            # If we have a previous complete sentence, fade out and replace
            if self.current_sentence:
                # Store the new sentence to show after fade
                self.pending_sentence = new_sentence
                self.fade_out_in()
            else:
                # First sentence or no previous content, just show it
                self.current_sentence = new_sentence
                self.partial_text = ""
                self.caption_label.setText(self.current_sentence)
                
            self.last_final_text = new_sentence

    def audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream"""
        if status:
            print(f"Audio status: {status}")
        try:
            # Put data in queue with timeout to prevent blocking
            self.q.put(bytes(indata), timeout=0.1)
        except queue.Full:
            # If queue is full, clear it and try again
            try:
                while not self.q.empty():
                    self.q.get_nowait()
                self.q.put(bytes(indata), timeout=0.1)
            except Exception as e:
                print(f"Error in audio callback: {e}")
        except Exception as e:
            print(f"Error in audio callback: {e}")

    def process_audio(self):
        """Process audio data for transcription"""
        if not self.recognizer:
            print("Vosk recognizer not available")
            return
            
        while self.is_capturing:
            try:
                data = self.q.get(timeout=1.0)
                if data == b'':  # Stop signal
                    break
                    
                # Convert to numpy array and process
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                if self.recognizer.AcceptWaveform(audio_data.tobytes()):
                    result = json.loads(self.recognizer.Result())
                    if result.get('text'):
                        self.update_caption(result['text'], False)
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    if partial.get('partial'):
                        self.update_caption(partial['partial'], True)
                        
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_capturing:  # Only log if we're still supposed to be capturing
                    print(f"Error processing audio: {e}")
                continue

    def start_capture(self):
        """Start audio capture from Stereo Mix"""
        try:
            # Find Stereo Mix device
            devices = sd.query_devices()
            stereo_mix_device = None
            
            print("Available audio devices:")
            for i, device in enumerate(devices):
                print(f"{i}: {device['name']}")
                if 'Stereo Mix' in device['name']:
                    stereo_mix_device = i
                    break
            
            if stereo_mix_device is None:
                print("Stereo Mix not found. Make sure it's enabled in your sound settings.")
                return

            print(f"Using Stereo Mix device: {devices[stereo_mix_device]['name']}")

            # Start audio processing thread
            threading.Thread(target=self.process_audio, daemon=True).start()

            # Start recording from Stereo Mix
            with sd.InputStream(device=stereo_mix_device,
                            channels=1,
                            samplerate=self.samplerate,
                            callback=self.audio_callback,
                            dtype=np.int16):
                print("Started capturing system audio...")
                # Keep the stream running - Qt event loop will handle the rest
                while self.is_capturing:
                    sd.sleep(100)  # Sleep for 100ms

        except Exception as e:
            print(f"Error starting capture: {e}")
            print("Full error details:", str(e))
    
    def stop_capture(self):
        """Stop audio capture and cleanup"""
        try:
            print("Stopping audio capture...")
            self.is_capturing = False
            
            # Signal to stop processing
            self.q.put(b'')
            
            # Clear the labels
            self.caption_label.setText("Audio capture stopped")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")

    def fade_out_in(self):
        """Fade animation for sentence transitions"""
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        try:
            self.opacity_anim.finished.disconnect()
        except Exception:
            pass
        self.opacity_anim.finished.connect(self._on_fade_out)
        self.opacity_anim.start()

    def _on_fade_out(self):
        """Handle fade out completion - show new sentence"""
        # Update to new sentence
        if hasattr(self, 'pending_sentence'):
            self.current_sentence = self.pending_sentence
            self.partial_text = ""
            self.caption_label.setText(self.current_sentence)
            delattr(self, 'pending_sentence')
        
        # Fade back in
        try:
            self.opacity_anim.finished.disconnect()
        except Exception:
            pass
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

    def resize_overlay(self):
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.18)
        x = (screen.width() - width) // 2
        y = int(screen.height() * 0.82) - height // 2
        self.setGeometry(QRect(x, y, width, height))
        
        # Position close button at top-right corner of caption label
        if hasattr(self, 'caption_container'):
            # Get caption label geometry within its container
            label_rect = self.caption_label.geometry()
            # Position close button at top-right corner of the caption box
            button_x = label_rect.right() - self.close_button.width() + 5
            button_y = label_rect.top() - 5
            self.close_button.move(button_x, button_y)

def main():
    """Main function to run the Qt overlay"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("EchoLine")
    app.setApplicationVersion("2.0")
    
    # Create and show overlay
    overlay = YouTubeCaptionOverlay()
    overlay.show()
    
    # Start audio capture in a separate thread
    def start_audio_capture():
        try:
            overlay.is_capturing = True
            overlay.start_capture()
        except Exception as e:
            print(f"Error starting audio capture: {e}")
    
    capture_thread = threading.Thread(target=start_audio_capture, daemon=True)
    capture_thread.start()
    
    # Run the application
    try:
        sys.exit(app.exec())
    finally:
        overlay.is_capturing = False

if __name__ == "__main__":
    main()
