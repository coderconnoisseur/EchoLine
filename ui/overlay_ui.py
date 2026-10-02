from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QScrollArea, QApplication
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QShortcut, QKeySequence

from ui.caption_buffer import CaptionBuffer
from ui.caption_widget import CaptionLabel

class YouTubeCaptionOverlay(QWidget):
    """Main overlay window with YouTube-like styling"""
    
    def __init__(self, signals):
        super().__init__()
        
        # Store signals for thread-safe updates
        self.signals = signals
        self.signals.update_text.connect(self._update_caption_safe)
        
        # Caption state management
        self.captions = CaptionBuffer()
        self.caption_label = None   # Current caption label
        
        # Setup UI components
        self._setup_window()
        self._setup_close_button()
        self._setup_scroll_area()
        self._setup_shortcuts()
        
        # Initialize with a welcome message
        self._add_caption_line("Ready for live captions...")
        
        # Show the overlay
        self.resize_overlay()
        self.show()
        
        # Listen for screen geometry changes
        QApplication.instance().primaryScreen().geometryChanged.connect(self.resize_overlay)
    
    def _setup_window(self):
        """Setup the main window properties"""
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
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
    
    def _setup_close_button(self):
        """Create and setup the close button"""
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
        self.close_button.setParent(self)
        # Ensure close button appears on top
        self.close_button.raise_()
    
    def _setup_scroll_area(self):
        """Setup the scroll area for captions"""
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
        self.caption_container.setMouseTracking(True)
        
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
        
        # Connect scrollbar signal for auto-scrolling
        self.scroll_area.verticalScrollBar().rangeChanged.connect(self.auto_scroll_to_bottom)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.close_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.close_shortcut.activated.connect(self.close_app)
        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.close_app)
    
    # Mouse event handlers for dragging
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
    
    # Event handlers for showing/hiding close button
    def enterEvent(self, event):
        """Show close button on mouse hover"""
        self.close_button.show()
        self.close_button.raise_()  # Ensure it stays on top when shown
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide close button when mouse leaves"""
        self.close_button.hide()
        super().leaveEvent(event)
    
    # Caption handling methods
    def _update_caption_safe(self, text, is_partial=False):
        """Update caption text with YouTube-style auto-scrolling behavior"""
        if not text.strip():
            # If empty text, show listening message
            if not self.captions.text:
                self._add_caption_line("Listening for audio...")
            return

        if is_partial:
            self.captions.add_partial(text)
        else:
            self.captions.add_final(text)
        self._add_caption_line(self.captions.text)

    def _add_caption_line(self, text):
        """Add or update the caption label"""
        # If we already have a caption label, update it
        if self.caption_label:
            self.caption_label.setText(text)
            return

        # Create a new caption label if it doesn't exist
        label = CaptionLabel(text)
        
        # Insert before the stretch (so captions appear at bottom)
        self.caption_layout.insertWidget(self.caption_layout.count() - 1, label)
        self.caption_label = label

    def auto_scroll_to_bottom(self, min_val, max_val):
        """Slot to automatically scroll to the bottom when content size changes"""
        self.scroll_area.verticalScrollBar().setValue(max_val)
    
    def resize_overlay(self):
        """Resize and position the overlay on screen"""
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.35)  # 35% of screen width
        height = int(screen.height() * 0.12)  # 12% of screen height
        x = (screen.width() - width) // 2
        y = int(screen.height() * 0.85) - height // 2  # Positioned near bottom
        self.setGeometry(QRect(x, y, width, height))
        
        # Position close button at top-right corner of overlay
        button_x = width - self.close_button.width() - 10
        button_y = 10
        self.close_button.move(button_x, button_y)
        # Ensure close button stays on top after repositioning
        self.close_button.raise_()
    
    def close_app(self):
        """Close the application gracefully"""
        print("Closing EchoLine...")
        # Ends the event loop; EchoLineApp.run() cleans up once it returns
        QApplication.quit()
        self.close()