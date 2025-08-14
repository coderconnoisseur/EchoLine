from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect, QPushButton, QScrollArea
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, Signal, QObject
from PySide6.QtGui import QFont, QColor, QShortcut, QKeySequence
import sys
import queue
import threading
import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer, Model
import json
import os
class OverlaySignals(QObject):
    """Signal object for thread-safe GUI updates"""
    update_text = Signal(str, bool)  # text, is_partial

class YouTubeCaptionOverlay(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            del self._drag_pos
        super().mouseReleaseEvent(event)
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
            # Use a relative path or environment variable instead of hardcoded user path
            model_path = os.path.join(os.path.expanduser("~"), ".cache", "vosk", "vosk-model-small-en-us-0.15")
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, 16000)
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            self.model = None
            self.recognizer = None
        
        # Window setup
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
        
        # Add styling to the main window for curved corners
        self.setStyleSheet("""
            YouTubeCaptionOverlay {
                background-color: transparent;
                border-radius: 12px;
            }
        """)

        # Create close button (initially hidden)
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(24, 24)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 68, 68, 180);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 20px;
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

        # Create scroll area for captions (no visible scrollbar)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        # Container widget for caption lines
        self.caption_container = QWidget()
        self.caption_container.setAttribute(Qt.WA_TranslucentBackground)
        self.caption_container.setStyleSheet("""
            QWidget {
                border-radius: 12px;
                background-color: transparent;
            }
        """)
        self.caption_layout = QVBoxLayout(self.caption_container)
        self.caption_layout.setContentsMargins(12, 12, 12, 12)
        self.caption_layout.setSpacing(8)
        self.caption_layout.addStretch()  # Push captions to bottom

        self.scroll_area.setWidget(self.caption_container)

        # Layout setup
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

        # Position close button relative to overlay
        self.close_button.setParent(self)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.caption_container.setMouseTracking(True)

        # Store single caption label instead of a list
        self.caption_label = None
        self._add_caption_line("Ready for live captions...", partial=True)

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

        # Connect scrollbar signal for auto-scrolling
        self.scroll_area.verticalScrollBar().rangeChanged.connect(self.auto_scroll_to_bottom)

    def auto_scroll_to_bottom(self, min_val, max_val):
        """Slot to automatically scroll to the bottom when content size changes"""
        self.scroll_area.verticalScrollBar().setValue(max_val)

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
        """Update caption text with YouTube-style auto-scrolling behavior"""
        if not text.strip():
            # If empty text, show listening message
            if not self.current_sentence and not self.partial_text:
                self._add_caption_line("Listening for audio...", partial=True)
            return

        if is_partial:
            # Partial text - update the caption label
            self.partial_text = text
            display_text = self.current_sentence
            if display_text and self.partial_text:
                display_text += " " + self.partial_text
            elif self.partial_text:
                display_text = self.partial_text

            # Update the caption label
            self._add_caption_line(display_text, partial=True)
        else:
            # Final text - update the caption label
            new_sentence = text.strip()
            if new_sentence == self.last_final_text:
                return

            display_text = self.current_sentence + " " + new_sentence if self.current_sentence else new_sentence
            self._add_caption_line(display_text, partial=False)

            self.current_sentence = display_text
            self.partial_text = ""
            self.last_final_text = new_sentence

    def _add_caption_line(self, text, partial=False):
        """Add or update the caption label"""
        # If we already have a caption label, update it
        if self.caption_label:
            self.caption_label.setText(text)
            self.caption_label.is_partial = partial
            return

        # Create a new caption label if it doesn't exist
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0,0,0,0.7);
                border-radius: 12px;
                padding: 8px 20px;  /* Increased from 6px 16px */
                font-family: 'Arial', 'Roboto', 'Segoe UI', sans-serif;
                font-size: 24px;  /* Increased from 20px */
                font-weight: 500;
                letter-spacing: 0.3px;
                line-height: 1.2;
                margin: 2px;
            }
        """)
        font = QFont("Arial", 24, QFont.Medium)  
        label.setFont(font)
        
        # Add shadow for text visibility
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(1, 1)
        label.setGraphicsEffect(shadow)
        
        label.is_partial = partial
        
        # Insert before the stretch (so captions appear at bottom)
        self.caption_layout.insertWidget(self.caption_layout.count() - 1, label)
        self.caption_label = label
        
        # Force scroll to bottom after adding new content
        QTimer.singleShot(10, self.force_scroll_to_bottom)

    def force_scroll_to_bottom(self):
        """Force scrolling to the bottom of the content"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

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
            
            # Show stopped message
            self._add_caption_line("Audio capture stopped", partial=False)
            
        except Exception as e:
            print(f"Error during shutdown: {e}")

    def resize_overlay(self):
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.35)  # Reduced from 0.3 to 0.25
        height = int(screen.height() * 0.12)  # Reduced from 0.12 to 0.08
        x = (screen.width() - width) // 2
        y = int(screen.height() * 0.85) - height // 2  # Moved slightly lower
        self.setGeometry(QRect(x, y, width, height))
        
        # Position close button at top-right corner of overlay
        button_x = width - self.close_button.width() - 10
        button_y = 10
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
