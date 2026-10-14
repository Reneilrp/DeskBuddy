"""
DeskBuddy - Stash Bag Dialog (Chisa's Pocket Viewer)
Provides a visual inventory of all files held in the companion's pocket,
allowing 1-drag extraction of individual or all files into Discord, Chrome,
or Windows Explorer, as well as removal or folder revelation.
"""

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QSize, QUrl, QMimeData, QFileInfo, pyqtSignal
from PyQt6.QtGui import QDrag, QIcon, QPainter, QPixmap, QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFileIconProvider, QMessageBox, QFrame, QApplication,
    QAbstractItemView
)

from ..core.fast_search import format_file_size, FastSearchEngine
from ..core.stash_manager import StashManager


class DraggableListWidget(QListWidget):
    """List widget that creates native OS drag operations containing file URLs."""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if not selected_items:
            return

        urls = []
        for item in selected_items:
            path_str = item.data(Qt.ItemDataRole.UserRole)
            if path_str and Path(path_str).exists():
                urls.append(QUrl.fromLocalFile(path_str))

        if not urls:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setUrls(urls)
        drag.setMimeData(mime)

        # Generate thumbnail preview for drag
        pix = QPixmap(160, 36)
        pix.fill(QColor("#FFFFFF"))
        painter = QPainter(pix)
        painter.setPen(QColor("#4A5568"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text = f"🎒 {len(urls)} file{'s' if len(urls) > 1 else ''}"
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()

        drag.setPixmap(pix)
        drag.exec(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
        else:
            super().dropEvent(event)


class DragAllZone(QPushButton):
    """A prominent button that initiates a drag of all stashed files when dragged."""
    def __init__(self, files_provider, parent=None):
        super().__init__(parent)
        self.files_provider = files_provider
        self.drag_start_pos = None
        self.setText("🚀 Drag All Files Out (Drag me into Discord, Browser, or Folder!)")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: #EDF2F7;
                color: #2D3748;
                border: 2px dashed #CBD5E0;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #E2E8F0;
                border-color: #A0AEC0;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_start_pos:
            distance = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                files = self.files_provider()
                if files:
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in files])
                    drag.setMimeData(mime)
                    drag.exec(Qt.DropAction.CopyAction)
                    self.drag_start_pos = None
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class StashBagDialog(QDialog):
    stash_changed = pyqtSignal()

    def __init__(self, stash_manager: StashManager, resonator_name: str = "Chisa", parent=None):
        super().__init__(parent)
        self.stash_manager = stash_manager
        self.resonator_name = resonator_name
        self.icon_provider = QFileIconProvider()

        self.setWindowTitle(f"🎒 {self.resonator_name}'s Pocket — Stashed Files")
        self.resize(520, 460)
        self.setMinimumSize(420, 340)

        self._setup_ui()
        self.refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header banner
        header = QHBoxLayout()
        icon_lbl = QLabel("🎒", self)
        icon_lbl.setStyleSheet("font-size: 26px;")
        header.addWidget(icon_lbl)

        title_lay = QVBoxLayout()
        title_lay.setSpacing(2)
        self.title_lbl = QLabel(f"{self.resonator_name}'s Pocket", self)
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2D3748;")
        self.subtitle_lbl = QLabel("Drag files directly out into any app, or drop new files here!", self)
        self.subtitle_lbl.setStyleSheet("font-size: 11px; color: #718096;")
        title_lay.addWidget(self.title_lbl)
        title_lay.addWidget(self.subtitle_lbl)
        header.addLayout(title_lay)
        header.addStretch()

        self.badge_count = QLabel("0 files", self)
        self.badge_count.setStyleSheet("""
            background: #E2E8F0;
            color: #4A5568;
            font-size: 11px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 10px;
        """)
        header.addWidget(self.badge_count)
        layout.addLayout(header)

        # Instruction info banner
        info_frame = QFrame(self)
        info_frame.setStyleSheet("""
            QFrame {
                background: #F7FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        inf_lay = QHBoxLayout(info_frame)
        inf_lay.setContentsMargins(8, 4, 8, 4)
        inf_lbl = QLabel("💡 <b>Tip:</b> Click and drag any item below straight into Discord, Chrome, or Windows Explorer!", info_frame)
        inf_lbl.setStyleSheet("color: #4A5568; font-size: 11px;")
        inf_lay.addWidget(inf_lbl)
        layout.addWidget(info_frame)

        # Files list
        self.list_widget = DraggableListWidget(self)
        self.list_widget.setIconSize(QSize(28, 28))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #CBD5E0;
                border-radius: 8px;
                padding: 6px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EDF2F7;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #F7FAFC;
            }
            QListWidget::item:selected {
                background: #EBF8FF;
                color: #2B6CB0;
            }
        """)
        self.list_widget.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.list_widget)

        # Drag All Out zone
        self.drag_all_zone = DragAllZone(self.stash_manager.get_files, self)
        layout.addWidget(self.drag_all_zone)

        # Bottom actions bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        btn_reveal = QPushButton("📂 Reveal Selected", self)
        btn_reveal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reveal.setStyleSheet(self._button_style("#EDF2F7", "#4A5568", "#CBD5E0"))
        btn_reveal.clicked.connect(self._reveal_selected)
        btn_bar.addWidget(btn_reveal)

        btn_remove = QPushButton("✕ Remove Selected", self)
        btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_remove.setStyleSheet(self._button_style("#FFF5F5", "#C53030", "#FED7D7"))
        btn_remove.clicked.connect(self._remove_selected)
        btn_bar.addWidget(btn_remove)

        btn_bar.addStretch()

        btn_clear = QPushButton("🗑️ Clear Pocket", self)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(self._button_style("#FFF5F5", "#E53E3E", "#FED7D7"))
        btn_clear.clicked.connect(self._clear_all)
        btn_bar.addWidget(btn_clear)

        btn_close = QPushButton("Close", self)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(self._button_style("#EDF2F7", "#4A5568", "#CBD5E0"))
        btn_close.clicked.connect(self.close)
        btn_bar.addWidget(btn_close)

        layout.addLayout(btn_bar)

    def _button_style(self, bg: str, fg: str, border: str) -> str:
        return f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                filter: brightness(0.95);
            }}
        """

    def refresh_list(self):
        self.list_widget.clear()
        files = self.stash_manager.get_files()
        count = len(files)
        self.badge_count.setText(f"{count} file{'s' if count != 1 else ''}")
        self.title_lbl.setText(f"{self.resonator_name}'s Pocket ({count})")

        if count == 0:
            item = QListWidgetItem("Pocket is empty. Drop files onto Chisa or into this window!")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            self.drag_all_zone.setEnabled(False)
            return

        self.drag_all_zone.setEnabled(True)
        for p in files:
            file_info = QFileInfo(str(p))
            icon = self.icon_provider.icon(file_info)
            sz = p.stat().st_size if p.exists() else 0
            sz_str = format_file_size(sz)

            item = QListWidgetItem(f"{p.name}  ({sz_str})")
            item.setIcon(icon)
            item.setToolTip(str(p))
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.list_widget.addItem(item)

    def _on_files_dropped(self, paths: list):
        added = self.stash_manager.add_files(paths)
        if added > 0:
            self.refresh_list()
            self.stash_changed.emit()

    def _reveal_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        path_str = selected[0].data(Qt.ItemDataRole.UserRole)
        if path_str:
            FastSearchEngine.reveal_in_explorer(path_str)

    def _remove_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        for item in selected:
            path_str = item.data(Qt.ItemDataRole.UserRole)
            if path_str:
                self.stash_manager.remove_file(path_str)
        self.refresh_list()
        self.stash_changed.emit()

    def _clear_all(self):
        if self.stash_manager.count() == 0:
            return
        self.stash_manager.clear()
        self.refresh_list()
        self.stash_changed.emit()
