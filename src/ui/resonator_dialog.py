"""
DeskBuddy - Resonator Companion Selection Dialog
Allows the user to browse and pick any Wuthering Waves Resonator companion.
"""

from pathlib import Path
from typing import Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QWidget, QFrame, QScrollArea,
    QButtonGroup
)
from PyQt6.QtGui import QIcon, QPixmap, QColor

from ..core.resonators import RESONATORS, ELEMENT_COLORS, list_all_resonators

class ResonatorItemWidget(QWidget):
    def __init__(self, res_id: str, data: Dict[str, Any], assets_dir: Path, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.res_id = res_id
        elem = data["element"]
        elem_color = ELEMENT_COLORS.get(elem, ELEMENT_COLORS["Spectro"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel(self)
        icon_path = assets_dir / "resonators" / res_id / "icon.png"
        if icon_path.exists():
            icon_pix = QPixmap(str(icon_path))
            icon_label.setPixmap(icon_pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setFixedSize(48, 48)
        layout.addWidget(icon_label)

        # Info layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_row = QHBoxLayout()
        name_label = QLabel(data["name"])
        name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2D3748;")
        name_row.addWidget(name_label)

        # Element Badge
        badge = QLabel(f" {elem} ")
        badge.setStyleSheet(f"""
            background-color: {elem_color['primary']};
            color: #1A202C;
            font-size: 10px;
            font-weight: bold;
            border-radius: 4px;
            padding: 2px 4px;
        """)
        name_row.addWidget(badge)

        if is_active:
            active_badge = QLabel(" ★ Active Companion ")
            active_badge.setStyleSheet("""
                background-color: #48BB78;
                color: white;
                font-size: 10px;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 4px;
            """)
            name_row.addWidget(active_badge)

        name_row.addStretch()
        info_layout.addLayout(name_row)

        title_label = QLabel(f"{data['title']} • {data['motif']}")
        title_label.setStyleSheet("color: #718096; font-size: 11px;")
        info_layout.addWidget(title_label)

        greeting_preview = QLabel(f'"{data["greeting"]}"')
        greeting_preview.setStyleSheet("color: #4A5568; font-size: 11px; font-style: italic;")
        info_layout.addWidget(greeting_preview)

        layout.addLayout(info_layout)


class ResonatorDialog(QDialog):
    companion_changed = pyqtSignal(str)

    def __init__(self, current_res_id: str, assets_dir: Path, parent=None):
        super().__init__(parent)
        self.current_res_id = current_res_id
        self.assets_dir = assets_dir
        self.current_filter = "All"

        self.setWindowTitle("Select Your Resonator Companion")
        self.resize(520, 560)
        self._setup_ui()
        self._populate_list()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QListWidget::item {
                border-bottom: 1px solid #EDF2F7;
            }
            QListWidget::item:selected {
                background-color: #FEFCBF;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QLabel("✨ Choose Your Wuthering Waves Companion")
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #2D3748;")
        layout.addWidget(header)

        sub = QLabel("Each Resonator has their own animated sprite, personality voice, and reminder style.")
        sub.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(sub)

        # Filter buttons
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(6)
        elements = ["All", "Spectro", "Havoc", "Fusion", "Aero", "Glacio", "Electro"]

        self.filter_buttons = {}
        for elem in elements:
            btn = QPushButton(elem, self)
            btn.setCheckable(True)
            if elem == "All":
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: #EDF2F7;
                    border: 1px solid #CBD5E0;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                    color: #4A5568;
                }
                QPushButton:checked {
                    background: #4A5568;
                    color: white;
                }
            """)
            btn.clicked.connect(lambda checked, el=elem: self._on_filter_changed(el))
            self.filter_buttons[elem] = btn
            filter_bar.addWidget(btn)

        layout.addLayout(filter_bar)

        # Resonator List
        self.list_widget = QListWidget(self)
        self.list_widget.setIconSize(QSize(48, 48))
        layout.addWidget(self.list_widget)

        # Select button
        self.btn_select = QPushButton("Set as Companion", self)
        self.btn_select.setStyleSheet("""
            QPushButton {
                background: #FFB049;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: #FF9B20;
            }
        """)
        self.btn_select.clicked.connect(self._on_select_clicked)
        layout.addWidget(self.btn_select)

    def _on_filter_changed(self, element: str):
        self.current_filter = element
        for el, btn in self.filter_buttons.items():
            btn.setChecked(el == element)
        self._populate_list()

    def _populate_list(self):
        self.list_widget.clear()
        for res_id, data in RESONATORS.items():
            if self.current_filter != "All" and data["element"] != self.current_filter:
                continue

            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.ItemDataRole.UserRole, res_id)
            is_active = (res_id == self.current_res_id)

            widget = ResonatorItemWidget(res_id, data, self.assets_dir, is_active=is_active)
            item.setSizeHint(widget.sizeHint())

            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

            if is_active:
                self.list_widget.setCurrentItem(item)

    def _on_select_clicked(self):
        curr = self.list_widget.currentItem()
        if curr:
            res_id = curr.data(Qt.ItemDataRole.UserRole)
            self.current_res_id = res_id
            self.companion_changed.emit(res_id)
            self.accept()
