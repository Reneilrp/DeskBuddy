"""
DeskBuddy - Speech Bubble & Quick Chat Widget
Renders a comic-style speech bubble with text, dynamic tail, and an integrated input bar.
Supports sticky screen-edge snapping and pinning.
"""

from typing import Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect, QPointF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtGui import QColor, QFont, QPainter, QPolygonF, QPen, QBrush

class SpeechBubble(QWidget):
    message_sent = pyqtSignal(str)
    closed = pyqtSignal()
    pinned_toggled = pyqtSignal(bool)
    expand_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)

        self.is_pinned = False
        self.tail_direction = "bottom"  # "bottom", "top", "left", "right"
        self.tail_offset_x = 0

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._on_auto_hide)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Bubble container with rounded comic styling
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 2px solid #4A2E18;
                border-radius: 14px;
            }
        """)

        # Drop shadow for clean desktop appearance
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(2, 4)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(6)

        # Top bar with speaker name, pin button, and close button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(4)
        
        self.title_label = QLabel("✨ DeskBuddy", self)
        self.title_label.setStyleSheet("color: #FF8B77; font-weight: bold; font-size: 11px; border: none;")
        top_bar.addWidget(self.title_label)

        # Pomodoro / Status mini badge
        self.status_badge = QLabel("", self)
        self.status_badge.setStyleSheet("color: #718096; font-size: 10px; border: none;")
        self.status_badge.setVisible(False)
        top_bar.addWidget(self.status_badge)

        top_bar.addStretch()

        # Pin button
        self.btn_pin = QPushButton("📌", self)
        self.btn_pin.setFixedSize(20, 20)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setToolTip("Pin bubble to keep it open")
        self.btn_pin.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888888;
                font-size: 11px;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #FFEACC;
                color: #4A2E18;
            }
        """)
        self.btn_pin.clicked.connect(self.toggle_pin)
        top_bar.addWidget(self.btn_pin)

        # Expand to Workspace button
        self.btn_expand = QPushButton("⤢", self)
        self.btn_expand.setFixedSize(20, 20)
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.setToolTip("Expand to Workspace (Half-Screen Modal)")
        self.btn_expand.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888888;
                font-size: 13px;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #FFEACC;
                color: #4A2E18;
            }
        """)
        self.btn_expand.clicked.connect(self._on_expand_clicked)
        top_bar.addWidget(self.btn_expand)

        # Close button
        self.btn_close = QPushButton("×", self)
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Close")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888888;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #FFEACC;
                color: #4A2E18;
            }
        """)
        self.btn_close.clicked.connect(self.hide_bubble)
        top_bar.addWidget(self.btn_close)
        container_layout.addLayout(top_bar)

        # Main message text label
        self.label_message = QLabel("Hi there! Click me to chat or give me a task! (◕‿◕)", self)
        self.label_message.setWordWrap(True)
        self.label_message.setStyleSheet("""
            QLabel {
                color: #2D3748;
                font-size: 13px;
                line-height: 1.4;
                border: none;
                background: transparent;
            }
        """)
        container_layout.addWidget(self.label_message)

        # Action chips container
        self.action_bar = QHBoxLayout()
        self.action_bar.setSpacing(4)
        container_layout.addLayout(self.action_bar)

        # Bottom Chat input bar
        input_bar = QHBoxLayout()
        input_bar.setSpacing(4)

        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Ask me or say 'remind me to...'")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: #F7FAFC;
                border: 1px solid #CBD5E0;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                color: #2D3748;
            }
            QLineEdit:focus {
                border: 1px solid #FFB049;
                background: #FFFFFF;
            }
        """)
        self.input_field.returnPressed.connect(self._on_send)
        input_bar.addWidget(self.input_field)

        self.btn_send = QPushButton("➤", self)
        self.btn_send.setFixedSize(28, 26)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: #FFB049;
                color: white;
                font-size: 12px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: #FF9B20;
            }
        """)
        self.btn_send.clicked.connect(self._on_send)
        input_bar.addWidget(self.btn_send)

        container_layout.addLayout(input_bar)
        main_layout.addWidget(self.container)

    def paintEvent(self, event):
        super().paintEvent(event)
        # Draw comic tail pointing towards the companion
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor("#4A2E18"), 2)
        brush = QBrush(QColor("#FFFFFF"))
        painter.setPen(pen)
        painter.setBrush(brush)

        crect = self.container.geometry()
        tail_x = max(crect.left() + 20, min(crect.right() - 20, crect.center().x() + self.tail_offset_x))

        if self.tail_direction == "bottom":
            # Tail pointing down to pet
            p1 = QPointF(tail_x - 10, crect.bottom() - 1)
            p2 = QPointF(tail_x + 10, crect.bottom() - 1)
            p3 = QPointF(tail_x, crect.bottom() + 10)
            poly = QPolygonF([p1, p2, p3])
            painter.drawPolygon(poly)
            # Mask inner border seam
            painter.setPen(QPen(QColor("#FFFFFF"), 3))
            painter.drawLine(tail_x - 8, crect.bottom(), tail_x + 8, crect.bottom())
        elif self.tail_direction == "top":
            # Tail pointing up to pet
            p1 = QPointF(tail_x - 10, crect.top() + 1)
            p2 = QPointF(tail_x + 10, crect.top() + 1)
            p3 = QPointF(tail_x, crect.top() - 10)
            poly = QPolygonF([p1, p2, p3])
            painter.drawPolygon(poly)
            # Mask inner border seam
            painter.setPen(QPen(QColor("#FFFFFF"), 3))
            painter.drawLine(tail_x - 8, crect.top(), tail_x + 8, crect.top())

    def toggle_pin(self):
        """Toggles sticky pin mode to keep speech bubble persistent."""
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self._auto_hide_timer.stop()
            self.btn_pin.setStyleSheet("""
                QPushButton {
                    background: #FFB049;
                    color: white;
                    font-size: 11px;
                    border: none;
                    border-radius: 10px;
                }
            """)
            self.btn_pin.setToolTip("Unpin bubble (will auto-hide)")
        else:
            self.btn_pin.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #888888;
                    font-size: 11px;
                    border: none;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background: #FFEACC;
                    color: #4A2E18;
                }
            """)
            self.btn_pin.setToolTip("Pin bubble to keep it open")
            self._auto_hide_timer.start(8000)
        self.pinned_toggled.emit(self.is_pinned)

    def _on_expand_clicked(self):
        """Hides sticky speech bubble and triggers half-screen modal workspace."""
        self.hide_bubble()
        self.expand_requested.emit()

    def set_status_badge(self, text: str, color: str = "#E28743"):
        """Displays a small status badge (e.g. Pomodoro timer or mode)."""
        if text:
            self.status_badge.setText(f"• {text}")
            self.status_badge.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; border: none;")
            self.status_badge.setVisible(True)
        else:
            self.status_badge.setVisible(False)

    def set_speaker(self, name: str, element_color: str = "#FF8B77"):
        """Updates the name badge and theme color of the speaker."""
        self.title_label.setText(f"✨ {name}")
        self.title_label.setStyleSheet(f"color: {element_color}; font-weight: bold; font-size: 11px; border: none;")

    def clear_action_chips(self):
        """Removes all dynamic micro-action buttons."""
        while self.action_bar.count():
            item = self.action_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_action_chip(
        self,
        message: str,
        actions: list,  # List of tuples: (label, callback_fn)
        auto_hide_seconds: int = 12
    ):
        """Displays text with one or more clickable micro-action chips."""
        self.clear_action_chips()
        self.label_message.setText(message)

        for label, callback in actions:
            btn = QPushButton(label, self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #EDF2F7;
                    color: #2D3748;
                    border: 1px solid #CBD5E0;
                    border-radius: 10px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #FFEACC;
                    color: #4A2E18;
                    border-color: #FF8B77;
                }
            """)
            btn.clicked.connect(callback)
            self.action_bar.addWidget(btn)

        self.action_bar.addStretch()
        self.adjustSize()
        self.show()
        if auto_hide_seconds > 0 and not self.is_pinned:
            self._auto_hide_timer.start(auto_hide_seconds * 1000)
        else:
            self._auto_hide_timer.stop()
        self.update()

    def say(self, message: str, auto_hide_seconds: int = 15):
        """Displays text in speech bubble and sets auto-hide timer."""
        self.clear_action_chips()
        self.label_message.setText(message)
        self.adjustSize()
        self.show()
        if auto_hide_seconds > 0 and not self.is_pinned:
            self._auto_hide_timer.start(auto_hide_seconds * 1000)
        else:
            self._auto_hide_timer.stop()
        self.update()

    def set_loading(self, text: str = "Thinking... (•ω•)"):
        self.label_message.setText(text)
        self._auto_hide_timer.stop()
        self.show()
        self.update()

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.set_loading("Thinking... (•ω•)")
            self.message_sent.emit(text)

    def hide_bubble(self):
        self._auto_hide_timer.stop()
        self.hide()
        self.closed.emit()

    def _on_auto_hide(self):
        # Do not hide if pinned or if input field has focus
        if self.is_pinned:
            return
        if not self.input_field.hasFocus():
            self.hide()
            self.closed.emit()
        else:
            self._auto_hide_timer.start(5000)

    def update_position(self, pet_rect: QRect, screen_geometry: Optional[QRect] = None):
        """
        Dynamically couples the speech bubble to the pet's coordinates.
        Calculates screen boundaries, flips tail direction, and prevents clipping.
        """
        if screen_geometry is None:
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        bubble_w = self.width()
        bubble_h = self.height()

        # Preferred anchor: centered directly above pet
        target_x = pet_rect.x() + (pet_rect.width() - bubble_w) // 2
        target_y = pet_rect.y() - bubble_h - 10
        self.tail_direction = "bottom"

        # Check if too close to screen top
        if target_y < screen_geometry.top() + 10:
            # Flip bubble underneath the pet
            target_y = pet_rect.bottom() + 10
            self.tail_direction = "top"

        # Boundary checks for horizontal edges
        if target_x < screen_geometry.left() + 10:
            target_x = screen_geometry.left() + 10
        elif target_x + bubble_w > screen_geometry.right() - 10:
            target_x = screen_geometry.right() - bubble_w - 10

        # Adjust tail relative offset so it points directly towards the pet's center
        pet_center_x = pet_rect.center().x()
        bubble_center_x = target_x + bubble_w // 2
        self.tail_offset_x = pet_center_x - bubble_center_x

        self.move(target_x, target_y)
        self.update()

    def position_near(self, pet_rect: QRect, screen_geometry: Optional[QRect] = None):
        """Backward-compatible alias for update_position."""
        self.update_position(pet_rect, screen_geometry)
