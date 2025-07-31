#!/usr/bin/env python3
"""
Qt-based Overlay for EchoLine - Modern, smooth, and performant UI
"""
import sys
import queue
import threading
import numpy as np
import sounddevice as sd
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, Signal, QObject
from PySide6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush
from vosk import KaldiRecognizer, Model
import json

class OverlaySignals(QObject):
    """Signal object for thread-safe GUI updates"""
    update_text = Signal(str, bool)  # text, is_partial

class ModernOverlay(QWidget):
    def __init__(self):
        super().__init__()
        # State variables (must be set before any method that uses them)
        self.is_hovered = False
        self.drag_position = None
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

        # Initialize UI
        self.init_ui()
        self.setup_animations()
        self.setup_timers()
        
    def init_ui(self):
        """Initialize the modern Qt UI"""
        # Window settings
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 120)
        
        # Position window at bottom center
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 50
        self.move(x, y)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(0)
        
        # Header frame (initially hidden)
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(45, 45, 45, 240);
                border-radius: 8px;
                border: 1px solid rgba(85, 85, 85, 180);
            }
        """)
        self.header_frame.setFixedHeight(35)
        self.header_frame.hide()
        
        # Header layout
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(12, 5, 8, 5)
        
        # Title label
        self.title_label = QLabel("EchoLine - Live Captions")
        self.title_label.setStyleSheet("""
            QLabel {
                color: rgba(204, 204, 204, 255);
                background: transparent;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 25)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 68, 68, 200);
                color: white;
                border: none;
                border-radius: 12px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 102, 102, 255);
            }
            QPushButton:pressed {
                background-color: rgba(220, 50, 50, 255);
            }
        """)
        self.close_btn.clicked.connect(self.close_app)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        
        # Content frame
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(26, 26, 26, 240);
                border-radius: 12px;
                border: 2px solid rgba(51, 51, 51, 180);
            }
        """)
        
        # Content layout
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(20, 15, 20, 15)
        
        # Scroll area for text
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: rgba(51, 51, 51, 120);
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(102, 102, 102, 180);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(120, 120, 120, 200);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Text label
        self.text_label = QLabel("Ready for live captions...")
        self.text_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 255);
                background: transparent;
                font-family: 'Segoe UI';
                font-size: 16px;
                font-weight: normal;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.scroll_area.setWidget(self.text_label)
        content_layout.addWidget(self.scroll_area)
        
        # Add frames to main layout
        self.main_layout.addWidget(self.header_frame)
        self.main_layout.addWidget(self.content_frame)
        
        # Set initial opacity
        self.setWindowOpacity(0.85)
        
    def setup_animations(self):
        """Set up smooth animations for UI transitions"""
        # Opacity animation
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Header slide animation
        self.header_animation = QPropertyAnimation(self.header_frame, b"maximumHeight")
        self.header_animation.setDuration(150)
        self.header_animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def setup_timers(self):
        """Set up timers for animations and effects"""
        # Pulse animation timer
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.pulse_animation)
        self.pulse_step = 0
        
        # Hover leave delay timer
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.handle_hover_leave)
        
        # Start pulse animation
        self.start_pulse()
        
    def start_pulse(self):
        """Start subtle pulse animation"""
        if not self.is_hovered:
            self.pulse_timer.start(100)  # 100ms interval
            
    def stop_pulse(self):
        """Stop pulse animation"""
        self.pulse_timer.stop()
        
    def pulse_animation(self):
        """Subtle pulse effect on the border"""
        if not self.is_hovered:
            import math
            self.pulse_step += 1
            
            # Calculate pulse intensity
            intensity = 0.3 + 0.2 * math.sin(self.pulse_step * 0.1)
            
            # Update border color
            base_color = 51
            pulse_color = int(base_color + (102 - base_color) * intensity)
            
            self.content_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(26, 26, 26, 240);
                    border-radius: 12px;
                    border: 2px solid rgba({pulse_color}, {pulse_color}, {pulse_color}, 180);
                }}
            """)
    
    def enterEvent(self, event):
        """Handle mouse enter with smooth animations"""
        if not self.is_hovered:
            self.is_hovered = True
            self.stop_pulse()
            
            # Reset content frame border to hover state
            self.content_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(26, 26, 26, 240);
                    border-radius: 12px;
                    border: 2px solid rgba(0, 120, 212, 200);
                }
            """)
            
            # Show header with animation
            self.header_frame.show()
            self.header_animation.setStartValue(0)
            self.header_animation.setEndValue(35)
            self.header_animation.start()
            
            # Increase opacity
            self.opacity_animation.setStartValue(0.85)
            self.opacity_animation.setEndValue(0.98)
            self.opacity_animation.start()
            
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave with delay to prevent flickering"""
        # Use timer to delay the leave action
        self.hover_timer.start(100)
        super().leaveEvent(event)
    
    def handle_hover_leave(self):
        """Handle delayed hover leave"""
        if self.is_hovered:
            self.is_hovered = False
            
            # Decrease opacity
            self.opacity_animation.setStartValue(0.98)
            self.opacity_animation.setEndValue(0.85)
            self.opacity_animation.start()
            
            # Hide header with animation
            self.header_animation.setStartValue(35)
            self.header_animation.setEndValue(0)
            self.header_animation.finished.connect(lambda: self.header_frame.hide())
            self.header_animation.start()
            
            # Reset border and restart pulse
            QTimer.singleShot(200, self.start_pulse)
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
        super().mouseReleaseEvent(event)
    
    def close_app(self):
        """Close the application gracefully"""
        try:
            self.stop_capture()
        except:
            pass
        QApplication.quit()
    
    def update_caption(self, text, is_partial=False):
        """Thread-safe method to update caption text"""
        # Emit signal to update UI from main thread
        self.signals.update_text.emit(text, is_partial)
    
    def _update_caption_safe(self, text, is_partial=False):
        """Update caption text in the main thread"""
        if is_partial:
            text = f"{text}..."
            
        try:
            if text.strip():
                color = "rgba(255, 255, 255, 255)" if not is_partial else "rgba(204, 204, 204, 255)"
                self.text_label.setStyleSheet(f"""
                    QLabel {{
                        color: {color};
                        background: transparent;
                        font-family: 'Segoe UI';
                        font-size: 16px;
                        font-weight: normal;
                        padding: 8px;
                        line-height: 1.4;
                    }}
                """)
                self.text_label.setText(text)
            else:
                self.text_label.setStyleSheet("""
                    QLabel {
                        color: rgba(136, 136, 136, 255);
                        background: transparent;
                        font-family: 'Segoe UI';
                        font-size: 16px;
                        font-weight: normal;
                        padding: 8px;
                        line-height: 1.4;
                    }
                """)
                self.text_label.setText("Listening for audio...")
            
            # Auto-scroll to bottom
            QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            ))
                
        except Exception as e:
            print(f"Error updating caption: {e}")
    
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
            
        while True:
            try:
                data = self.q.get()
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
                        
            except Exception as e:
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
            # Signal to stop processing
            self.q.put(b'')
            
            # Clear the labels
            self.update_caption("")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")

def main():
    """Main function to run the Qt overlay"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("EchoLine")
    app.setApplicationVersion("2.0")
    
    # Create and show overlay
    overlay = ModernOverlay()
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
