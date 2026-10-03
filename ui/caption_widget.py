from PySide6.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class CaptionLabel(QLabel):
    """Custom label for displaying captions with styling"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setup_styling()
    
    def setup_styling(self):
        """Apply YouTube-like styling to the caption"""
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0,0,0,0.7);
                border-radius: 12px;
                padding: 8px 20px;
                font-family: 'Arial', 'Roboto', 'Segoe UI', sans-serif;
                font-size: 24px;
                font-weight: 500;
                letter-spacing: 0.3px;
                line-height: 1.2;
                margin: 2px;
            }
        """)
        # Add shadow for text visibility
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(1, 1)
        self.setGraphicsEffect(shadow)