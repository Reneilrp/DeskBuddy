"""
DeskBuddy - Half-Screen Companion Workspace Dialog
Provides a powerful, half-screen modal workspace containing:
1. ⚡ Fast File Finder ("Speed Grep" - instant sub-second file search with Explorer reveal)
2. 📁 Smart File Organizer Studio (Desktop & Downloads with dry-run preview, rule selection, and undo)
3. 💬 Extended Companion Chat (large scrollable discussion area with prompt chips)
4. 📋 Task & Reminder Management Hub
"""

import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QRect
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QCheckBox, QTextEdit, QScrollArea, QFileDialog, QApplication,
    QFrame, QMessageBox, QSplitter
)
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QShortcut

from ..core.fast_search import FastSearchEngine, get_user_shortcuts, format_file_size
from ..core.file_organizer import FileOrganizer
from ..core.task_manager import TaskManager
from ..core.cleanup_hunter import CleanupHunter
from ..core.resonators import get_resonator, ELEMENT_COLORS

class SearchWorker(QThread):
    results_ready = pyqtSignal(list, float)  # results, elapsed_seconds

    def __init__(self, engine: FastSearchEngine, query: str, root_path: Path, file_only: bool, case_sensitive: bool):
        super().__init__()
        self.engine = engine
        self.query = query
        self.root_path = root_path
        self.file_only = file_only
        self.case_sensitive = case_sensitive
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        start_time = time.time()
        results = self.engine.search(
            query=self.query,
            search_root=self.root_path,
            max_results=150,
            case_sensitive=self.case_sensitive,
            file_only=self.file_only,
            stop_check=lambda: self._is_stopped
        )
        elapsed = time.time() - start_time
        if not self._is_stopped:
            self.results_ready.emit(results, elapsed)


class WorkspaceDialog(QDialog):
    message_to_agent = pyqtSignal(str)

    def __init__(
        self,
        task_manager: TaskManager,
        file_organizer: FileOrganizer,
        resonator_id: str = "chisa",
        parent=None
    ):
        super().__init__(parent)
        self.task_manager = task_manager
        self.file_organizer = file_organizer
        self.resonator_id = resonator_id
        self.search_engine = FastSearchEngine()
        self.user_shortcuts = get_user_shortcuts()
        self.cleanup_hunter = CleanupHunter()
        self._search_worker = None
        self._current_planned_moves: List[Dict[str, Any]] = []
        self._hunter_items: List[Dict[str, Any]] = []

        self.setWindowTitle("DeskBuddy — Companion Workspace")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        self._setup_window_size()
        self._setup_ui()
        self._apply_theme()

    def _setup_window_size(self):
        """Sizes the workspace to roughly 52% monitor width and 78% height."""
        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        w = int(screen_geom.width() * 0.52)
        h = int(screen_geom.height() * 0.78)
        self.resize(max(750, w), max(550, h))

        # Position slightly to the right-center of the screen
        x = screen_geom.left() + (screen_geom.width() - self.width()) // 2
        y = screen_geom.top() + (screen_geom.height() - self.height()) // 2
        self.move(x, y)

    def set_resonator(self, resonator_id: str):
        self.resonator_id = resonator_id
        res = get_resonator(resonator_id)
        elem_info = ELEMENT_COLORS.get(res["element"], ELEMENT_COLORS["Spectro"])
        self.header_title.setText(f"✨ DeskBuddy Workspace — {res['name']}")
        self.header_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {elem_info['badge']};")
        title = res.get("title", res.get("motif", "Resonator Companion"))
        self.header_subtitle.setText(f"Wuthering Waves {res.get('element', '')} Resonator • {title}")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Header Banner
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        self.header_title = QLabel("✨ DeskBuddy Workspace — Chisa", self)
        self.header_subtitle = QLabel("High-speed search, intelligent file organization & companion studio", self)
        self.header_subtitle.setStyleSheet("color: #718096; font-size: 11px;")
        info_layout.addWidget(self.header_title)
        info_layout.addWidget(self.header_subtitle)
        header.addLayout(info_layout)
        header.addStretch()

        btn_close = QPushButton("✕ Close", self)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #EDF2F7;
                color: #4A5568;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #E2E8F0;
                color: #2D3748;
            }
        """)
        btn_close.clicked.connect(self.close)
        header.addWidget(btn_close)
        main_layout.addLayout(header)

        # 2. Main Tab Widget
        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget(self)
        self.tabs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                background: #FFFFFF;
                top: -1px;
            }
            QTabBar::tab {
                background: #F7FAFC;
                border: 1px solid #E2E8F0;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 18px;
                margin-right: 4px;
                font-size: 12px;
                font-weight: bold;
                color: #718096;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #2D3748;
                border-bottom: 2px solid #FF8B77;
            }
            QTabBar::tab:hover:!selected {
                background: #EDF2F7;
                color: #4A5568;
            }
        """)

        # Add specialized workspace tabs
        self.tab_search = self._build_search_tab()
        self.tab_organizer = self._build_organizer_tab()
        self.tab_hunter = self._build_hunter_tab()
        self.tab_chat = self._build_chat_tab()
        self.tab_tasks = self._build_tasks_tab()

        self.tabs.addTab(self.tab_search, "⚡ Fast File Finder")
        self.tabs.addTab(self.tab_organizer, "📁 Smart File Organizer")
        self.tabs.addTab(self.tab_hunter, "🧹 Duplicate & Junk Hunter")
        self.tabs.addTab(self.tab_chat, "💬 Companion Chat")
        self.tabs.addTab(self.tab_tasks, "📋 Tasks & Reminders")

        main_layout.addWidget(self.tabs)

    def _apply_theme(self):
        res = get_resonator(self.resonator_id)
        elem_info = ELEMENT_COLORS.get(res["element"], ELEMENT_COLORS["Spectro"])
        self.header_title.setText(f"✨ DeskBuddy Workspace — {res['name']}")
        self.header_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {elem_info['badge']};")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1: Fast File Finder ("Speed Grep")
    # ─────────────────────────────────────────────────────────────────────────
    def _build_search_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Controls bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)

        # Scope selector
        self.search_scope_combo = QComboBox(self)
        self.search_scope_combo.addItem("📂 Downloads Folder", "Downloads")
        self.search_scope_combo.addItem("🖥️ Desktop", "Desktop")
        self.search_scope_combo.addItem("📄 Documents", "Documents")
        self.search_scope_combo.addItem("🏠 Entire User Profile", "Home")
        self.search_scope_combo.addItem("📁 Custom Folder...", "Custom")
        self.search_scope_combo.currentIndexChanged.connect(self._on_search_scope_changed)
        self.search_scope_combo.setStyleSheet("""
            QComboBox {
                background: #F7FAFC;
                border: 1px solid #CBD5E0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 170px;
            }
        """)
        ctrl_bar.addWidget(self.search_scope_combo)

        # Search query input
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search file name or pattern (*.png, report, draft*)...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 2px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                color: #2D3748;
            }
            QLineEdit:focus {
                border: 2px solid #FF8B77;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._execute_search)
        ctrl_bar.addWidget(self.search_input, stretch=1)

        # Search button
        self.btn_search = QPushButton("🔍 Find Fast", self)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setStyleSheet("""
            QPushButton {
                background: #FF8B77;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #FF7058;
            }
        """)
        self.btn_search.clicked.connect(self._execute_search)
        ctrl_bar.addWidget(self.btn_search)
        layout.addLayout(ctrl_bar)

        # Search options row
        opt_bar = QHBoxLayout()
        self.chk_file_only = QCheckBox("Files only (hide directories)", self)
        self.chk_file_only.setChecked(True)
        self.chk_case = QCheckBox("Case sensitive", self)
        opt_bar.addWidget(self.chk_file_only)
        opt_bar.addWidget(self.chk_case)
        opt_bar.addStretch()

        self.search_status_label = QLabel("Ready to search. Instant sub-second scanner skipping system junk.", self)
        self.search_status_label.setStyleSheet("color: #718096; font-size: 11px;")
        opt_bar.addWidget(self.search_status_label)
        layout.addLayout(opt_bar)

        # Results Table
        self.search_table = QTableWidget(self)
        self.search_table.setColumnCount(4)
        self.search_table.setHorizontalHeaderLabels(["Name", "Size", "Modified", "Path"])
        self.search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.search_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.search_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.search_table.setAlternatingRowColors(True)
        self.search_table.setColumnWidth(0, 240)
        self.search_table.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                gridline-color: #EDF2F7;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background: #FFEACC;
                color: #2D3748;
            }
            QHeaderView::section {
                background: #F7FAFC;
                color: #4A5568;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        self.search_table.doubleClicked.connect(self._on_search_item_double_clicked)
        layout.addWidget(self.search_table, stretch=1)

        # Action Buttons row below table
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        btn_reveal = QPushButton("📂 Reveal in Explorer", self)
        btn_reveal.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reveal.setStyleSheet(self._secondary_btn_style())
        btn_reveal.clicked.connect(self._reveal_selected_search_file)
        btn_bar.addWidget(btn_reveal)

        btn_open = QPushButton("🚀 Open / Launch", self)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet(self._secondary_btn_style())
        btn_open.clicked.connect(self._open_selected_search_file)
        btn_bar.addWidget(btn_open)

        btn_copy = QPushButton("📋 Copy Path", self)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(self._secondary_btn_style())
        btn_copy.clicked.connect(self._copy_selected_search_path)
        btn_bar.addWidget(btn_copy)

        btn_bar.addStretch()
        hint = QLabel("💡 Tip: Double-click any row to reveal in File Explorer", self)
        hint.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        btn_bar.addWidget(hint)

        layout.addLayout(btn_bar)
        return widget

    def _on_search_scope_changed(self):
        val = self.search_scope_combo.currentData()
        if val == "Custom":
            folder = QFileDialog.getExistingDirectory(self, "Select Directory to Search")
            if folder:
                self.custom_search_dir = Path(folder)
                self.search_scope_combo.setItemText(4, f"📁 {self.custom_search_dir.name}")
            else:
                self.search_scope_combo.setCurrentIndex(0)
        self._execute_search()

    def _on_search_text_changed(self):
        # Trigger dynamic search if length >= 2
        query = self.search_input.text().strip()
        if len(query) >= 2:
            self._execute_search()

    def _get_active_search_root(self) -> Path:
        val = self.search_scope_combo.currentData()
        if val == "Custom" and hasattr(self, "custom_search_dir"):
            return self.custom_search_dir
        return self.user_shortcuts.get(val, self.user_shortcuts.get("Downloads", Path.home()))

    def _execute_search(self):
        query = self.search_input.text().strip()
        if not query:
            self.search_table.setRowCount(0)
            self.search_status_label.setText("Enter a file name or wildcard pattern (*.pdf, project*) to search.")
            return

        root = self._get_active_search_root()
        self.search_status_label.setText(f"Scanning '{root.name}'...")

        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.stop()
            self._search_worker.wait(100)

        self._search_worker = SearchWorker(
            engine=self.search_engine,
            query=query,
            root_path=root,
            file_only=self.chk_file_only.isChecked(),
            case_sensitive=self.chk_case.isChecked()
        )
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.start()

    def _on_search_results(self, results: List[Dict[str, Any]], elapsed: float):
        self.search_table.setRowCount(len(results))
        for row, item in enumerate(results):
            icon = "📁" if item["is_dir"] else "📄"
            name_item = QTableWidgetItem(f"{icon} {item['name']}")
            name_item.setData(Qt.ItemDataRole.UserRole, item["path"])

            size_item = QTableWidgetItem(item["size_formatted"])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            date_item = QTableWidgetItem(item["modified"])
            path_item = QTableWidgetItem(item["path"])
            path_item.setForeground(QColor("#718096"))

            self.search_table.setItem(row, 0, name_item)
            self.search_table.setItem(row, 1, size_item)
            self.search_table.setItem(row, 2, date_item)
            self.search_table.setItem(row, 3, path_item)

        count = len(results)
        self.search_status_label.setText(
            f"⚡ Found {count} {'match' if count == 1 else 'matches'} in {elapsed:.3f}s"
        )

    def _get_selected_search_path(self) -> Optional[str]:
        row = self.search_table.currentRow()
        if row >= 0:
            item = self.search_table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _reveal_selected_search_file(self):
        path = self._get_selected_search_path()
        if path:
            FastSearchEngine.reveal_in_explorer(path)
        else:
            QMessageBox.information(self, "No Selection", "Please select a file from the results table first.")

    def _open_selected_search_file(self):
        path = self._get_selected_search_path()
        if path:
            FastSearchEngine.open_file(path)

    def _copy_selected_search_path(self):
        path = self._get_selected_search_path()
        if path:
            QApplication.clipboard().setText(path)
            self.search_status_label.setText(f"📋 Copied path to clipboard: {Path(path).name}")

    def _on_search_item_double_clicked(self, index):
        self._reveal_selected_search_file()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2: Smart File Organizer Studio
    # ─────────────────────────────────────────────────────────────────────────
    def _build_organizer_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Safety Banner
        banner = QFrame(self)
        banner.setStyleSheet("""
            QFrame {
                background: #EBF8FF;
                border: 1px solid #BEE3F8;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        b_lay = QHBoxLayout(banner)
        b_lay.setContentsMargins(8, 4, 8, 4)
        lbl_shield = QLabel("🛡️ Safety Shields Active: In-progress downloads (.crdownload, .part) are protected. Files are never overwritten.", banner)
        lbl_shield.setStyleSheet("color: #2B6CB0; font-size: 11px; font-weight: bold;")
        b_lay.addWidget(lbl_shield)
        layout.addWidget(banner)

        # Top Controls: Target folder & Rule selector
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)

        lbl_target = QLabel("Target:", self)
        lbl_target.setStyleSheet("font-weight: bold; font-size: 12px; color: #2D3748;")
        ctrl_bar.addWidget(lbl_target)

        self.org_target_combo = QComboBox(self)
        self.org_target_combo.addItem("📂 Downloads Folder", "Downloads")
        self.org_target_combo.addItem("🖥️ Desktop Folder", "Desktop")
        self.org_target_combo.addItem("📁 Custom Folder...", "Custom")
        self.org_target_combo.currentIndexChanged.connect(self._on_org_target_changed)
        self.org_target_combo.setStyleSheet("""
            QComboBox {
                background: #F7FAFC;
                border: 1px solid #CBD5E0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 170px;
            }
        """)
        ctrl_bar.addWidget(self.org_target_combo)

        lbl_rule = QLabel("Rule:", self)
        lbl_rule.setStyleSheet("font-weight: bold; font-size: 12px; color: #2D3748;")
        ctrl_bar.addWidget(lbl_rule)

        self.org_rule_combo = QComboBox(self)
        self.org_rule_combo.addItem("📦 All Loose Files (Group by Type)", "type")
        self.org_rule_combo.addItem("🎯 Specific Extension Only (e.g. .png, .pdf)", "extension")
        self.org_rule_combo.addItem("🏷️ Specific Category Only (e.g. Images, Docs)", "category")
        self.org_rule_combo.addItem("🔍 Name Pattern / Wildcard (e.g. screenshot*)", "pattern")
        self.org_rule_combo.addItem("📅 All Loose Files (Group by Date)", "date")
        self.org_rule_combo.currentIndexChanged.connect(self._on_org_rule_changed)
        self.org_rule_combo.setStyleSheet("""
            QComboBox {
                background: #F7FAFC;
                border: 1px solid #CBD5E0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 230px;
            }
        """)
        ctrl_bar.addWidget(self.org_rule_combo)

        ctrl_bar.addStretch()

        self.btn_preview_tidy = QPushButton("🔍 Preview Dry-Run", self)
        self.btn_preview_tidy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview_tidy.setStyleSheet("""
            QPushButton {
                background: #4299E1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #3182CE;
            }
        """)
        self.btn_preview_tidy.clicked.connect(self._preview_organization)
        ctrl_bar.addWidget(self.btn_preview_tidy)

        layout.addLayout(ctrl_bar)

        # Selective Rule Parameters Row (Filter text + Destination folder)
        self.rule_options_row = QHBoxLayout()
        self.rule_options_row.setSpacing(8)

        self.lbl_filter = QLabel("Filter Criteria:", self)
        self.lbl_filter.setStyleSheet("font-weight: bold; font-size: 11px; color: #4A5568;")
        self.rule_options_row.addWidget(self.lbl_filter)

        self.org_filter_input = QLineEdit(self)
        self.org_filter_input.setPlaceholderText("Filter criteria (e.g. .png or .png, .jpg)")
        self.org_filter_input.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4299E1;
            }
        """)
        self.org_filter_input.textChanged.connect(self._on_org_filter_changed)
        self.org_filter_input.setEnabled(False)
        self.rule_options_row.addWidget(self.org_filter_input, stretch=1)

        self.lbl_subfolder = QLabel("Destination Subfolder:", self)
        self.lbl_subfolder.setStyleSheet("font-weight: bold; font-size: 11px; color: #4A5568;")
        self.rule_options_row.addWidget(self.lbl_subfolder)

        self.org_subfolder_input = QLineEdit(self)
        self.org_subfolder_input.setPlaceholderText("Subfolder name (e.g. PNGs, leave blank for auto)")
        self.org_subfolder_input.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4299E1;
            }
        """)
        self.org_subfolder_input.textChanged.connect(self._on_org_filter_changed)
        self.rule_options_row.addWidget(self.org_subfolder_input, stretch=1)

        layout.addLayout(self.rule_options_row)

        # Dry-run Preview Table
        self.org_table = QTableWidget(self)
        self.org_table.setColumnCount(4)
        self.org_table.setHorizontalHeaderLabels(["Move?", "File Name", "Target Subfolder", "Size"])
        self.org_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.org_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.org_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.org_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.org_table.setColumnWidth(1, 260)
        self.org_table.setAlternatingRowColors(True)
        self.org_table.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                gridline-color: #EDF2F7;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background: #F7FAFC;
                color: #4A5568;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        layout.addWidget(self.org_table, stretch=1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self.btn_select_all = QPushButton("Select All", self)
        self.btn_select_all.setStyleSheet(self._secondary_btn_style())
        self.btn_select_all.clicked.connect(self._select_all_org_items)
        bottom_bar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All", self)
        self.btn_deselect_all.setStyleSheet(self._secondary_btn_style())
        self.btn_deselect_all.clicked.connect(self._deselect_all_org_items)
        bottom_bar.addWidget(self.btn_deselect_all)

        self.org_status_label = QLabel("Click 'Preview Dry-Run' to see files to organize.", self)
        self.org_status_label.setStyleSheet("color: #718096; font-size: 11px;")
        bottom_bar.addWidget(self.org_status_label, stretch=1)

        self.btn_undo_tidy = QPushButton("↩️ Undo Last Tidy", self)
        self.btn_undo_tidy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo_tidy.setStyleSheet(self._secondary_btn_style())
        self.btn_undo_tidy.clicked.connect(self._undo_last_tidy)
        bottom_bar.addWidget(self.btn_undo_tidy)

        self.btn_execute_tidy = QPushButton("🧹 Tidy Selected Files", self)
        self.btn_execute_tidy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_execute_tidy.setEnabled(False)
        self.btn_execute_tidy.setStyleSheet("""
            QPushButton {
                background: #48BB78;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #38A169;
            }
            QPushButton:disabled {
                background: #CBD5E0;
                color: #A0AEC0;
            }
        """)
        self.btn_execute_tidy.clicked.connect(self._execute_tidy)
        bottom_bar.addWidget(self.btn_execute_tidy)

        layout.addLayout(bottom_bar)
        return widget

    def _on_org_target_changed(self):
        val = self.org_target_combo.currentData()
        if val == "Custom":
            folder = QFileDialog.getExistingDirectory(self, "Select Folder to Organize")
            if folder:
                self.custom_org_dir = Path(folder)
                self.org_target_combo.setItemText(2, f"📁 {self.custom_org_dir.name}")
            else:
                self.org_target_combo.setCurrentIndex(0)
        self._preview_organization()

    def _on_org_rule_changed(self):
        rule = self.org_rule_combo.currentData()
        if rule == "extension":
            self.org_filter_input.setEnabled(True)
            self.org_filter_input.setPlaceholderText("Extension: e.g. .png or .png, .jpg")
            if not self.org_filter_input.text():
                self.org_filter_input.setText(".png")
            if not self.org_subfolder_input.text():
                self.org_subfolder_input.setText("PNG Files")
        elif rule == "category":
            self.org_filter_input.setEnabled(True)
            self.org_filter_input.setPlaceholderText("Category: Images, Documents, Archives, Audio, Video, Code, Installers")
            if not self.org_filter_input.text():
                self.org_filter_input.setText("Images")
        elif rule == "pattern":
            self.org_filter_input.setEnabled(True)
            self.org_filter_input.setPlaceholderText("Pattern: e.g. screenshot* or invoice*")
            if not self.org_filter_input.text():
                self.org_filter_input.setText("screenshot*")
        else:
            self.org_filter_input.setEnabled(False)
            self.org_filter_input.clear()
            self.org_subfolder_input.clear()
        self._preview_organization()

    def _on_org_filter_changed(self):
        self._preview_organization()

    def _get_active_org_dir(self) -> Path:
        val = self.org_target_combo.currentData()
        if val == "Custom" and hasattr(self, "custom_org_dir"):
            return self.custom_org_dir
        return self.user_shortcuts.get(val, self.user_shortcuts.get("Downloads", Path.home()))

    def _preview_organization(self):
        target = self._get_active_org_dir()
        rule = self.org_rule_combo.currentData()
        filt = self.org_filter_input.text().strip() if hasattr(self, "org_filter_input") else ""
        subfolder = self.org_subfolder_input.text().strip() if hasattr(self, "org_subfolder_input") else ""

        plan = self.file_organizer.plan_organization(
            target_dir=target,
            rule=rule,
            ext_filter=filt if rule in ("extension", "category", "pattern") else None,
            category_filter=filt if rule == "category" else None,
            pattern_filter=filt if rule == "pattern" else None,
            custom_subfolder=subfolder if subfolder else None
        )

        if not plan.get("success"):
            QMessageBox.warning(self, "Organization Error", plan.get("error", "Failed to plan moves."))
            return

        moves = plan.get("moves", [])
        self._current_planned_moves = moves
        self.org_table.setRowCount(len(moves))

        for row, move in enumerate(moves):
            # Checkbox item
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)
            self.org_table.setItem(row, 0, chk_item)

            name_item = QTableWidgetItem(f"📄 {move['name']}")
            self.org_table.setItem(row, 1, name_item)

            dest_folder = Path(move["destination"]).parent.name
            target_item = QTableWidgetItem(f"📁 {dest_folder} / {Path(move['destination']).name}")
            target_item.setForeground(QColor("#2B6CB0"))
            self.org_table.setItem(row, 2, target_item)

            size_str = format_file_size(move.get("size", 0))
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.org_table.setItem(row, 3, size_item)

        total = len(moves)
        self.btn_execute_tidy.setEnabled(total > 0)
        if total == 0:
            filter_desc = f" matching '{filt}'" if filt else ""
            self.org_status_label.setText(f"No files found{filter_desc} in '{target.name}'.")
        else:
            filter_desc = f" matching '{filt}'" if filt else ""
            self.org_status_label.setText(f"Found {total} files{filter_desc} ready to organize. Check the files you wish to sort.")

    def _select_all_org_items(self):
        for row in range(self.org_table.rowCount()):
            item = self.org_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all_org_items(self):
        for row in range(self.org_table.rowCount()):
            item = self.org_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _execute_tidy(self):
        selected_moves = []
        for row in range(self.org_table.rowCount()):
            item = self.org_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_moves.append(self._current_planned_moves[row])

        if not selected_moves:
            QMessageBox.information(self, "No Selection", "Please check at least one file to organize.")
            return

        res = self.file_organizer.execute_moves(selected_moves)
        if res.get("success"):
            moved = res.get("moved_count", 0)
            res_data = get_resonator(self.resonator_id)
            self.org_status_label.setText(f"✨ Successfully organized {moved} files! (Undo available)")
            QMessageBox.information(
                self,
                "Tidy Complete",
                f"{res_data['name']} says:\n\n{res_data['organize_quote']}\n\nOrganized {moved} files into neat category folders."
            )
            # Re-preview to clear moved files
            self._preview_organization()
        else:
            QMessageBox.warning(self, "Tidy Error", f"Encountered error: {res.get('error')}")

    def _undo_last_tidy(self):
        res = self.file_organizer.undo_last()
        if res.get("success"):
            count = res.get("reverted_count", 0)
            self.org_status_label.setText(f"↩️ Reverted last tidy: {count} files restored to original locations.")
            QMessageBox.information(self, "Undo Complete", f"Successfully reverted {count} files to their original directories.")
            self._preview_organization()
        else:
            QMessageBox.warning(self, "Undo Unavailable", res.get("error", "Failed to undo."))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3: Extended Companion Chat
    # ─────────────────────────────────────────────────────────────────────────
    def _build_chat_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Chat history display area
        self.chat_history = QTextEdit(self)
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background: #F7FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                color: #2D3748;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.chat_history, stretch=1)

        # Quick prompt chips
        chips_bar = QHBoxLayout()
        chips_bar.setSpacing(6)
        chips = [
            ("📁 Tidy my Downloads", "Organize my Downloads folder"),
            ("⚡ Find recent PDF files", "Find recent PDF files"),
            ("📋 What tasks do I have?", "What tasks do I have today?"),
            ("✨ How are you feeling?", "How are you feeling today?")
        ]
        for label, prompt in chips:
            btn = QPushButton(label, self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #EDF2F7;
                    color: #4A5568;
                    border: 1px solid #CBD5E0;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #FFEACC;
                    color: #4A2E18;
                    border-color: #FFB049;
                }
            """)
            btn.clicked.connect(lambda _, p=prompt: self._send_chip_prompt(p))
            chips_bar.addWidget(btn)
        chips_bar.addStretch()
        layout.addLayout(chips_bar)

        # Input row
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        self.chat_input = QLineEdit(self)
        self.chat_input.setPlaceholderText("Ask your companion anything, request a file organization rule, or chat...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 2px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #2D3748;
            }
            QLineEdit:focus {
                border: 2px solid #FF8B77;
            }
        """)
        self.chat_input.returnPressed.connect(self._send_chat_message)
        input_bar.addWidget(self.chat_input, stretch=1)

        self.btn_send_chat = QPushButton("Send ➤", self)
        self.btn_send_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_chat.setStyleSheet("""
            QPushButton {
                background: #FF8B77;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #FF7058;
            }
        """)
        self.btn_send_chat.clicked.connect(self._send_chat_message)
        input_bar.addWidget(self.btn_send_chat)

        layout.addLayout(input_bar)

        # Populate initial welcome message
        res = get_resonator(self.resonator_id)
        self.append_message(res["name"], f"\"{res['greeting']}\" Welcome to our expanded workspace! I'm here to search your files, organize your desktop, and keep you company.")

        return widget

    def _send_chip_prompt(self, text: str):
        self.chat_input.setText(text)
        self._send_chat_message()

    def _send_chat_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self.append_message("Rover (You)", text)
        self.message_to_agent.emit(text)

    def append_message(self, sender: str, text: str):
        is_user = "You" in sender or "Rover" in sender
        color = "#2B6CB0" if is_user else "#C53030"
        header = f"<b style='color: {color};'>{sender}:</b>"
        body = text.replace("\n", "<br>")
        self.chat_history.append(f"<div style='margin-bottom: 8px;'>{header} {body}</div>")
        # Scroll to bottom
        sb = self.chat_history.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4: Tasks & Reminders
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tasks_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Top Bar: Add Task
        add_bar = QHBoxLayout()
        add_bar.setSpacing(8)

        self.task_title_input = QLineEdit(self)
        self.task_title_input.setPlaceholderText("New task title (e.g. 'Review project PR by 5 PM')...")
        self.task_title_input.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 2px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #FF8B77;
            }
        """)
        self.task_title_input.returnPressed.connect(self._add_task)
        add_bar.addWidget(self.task_title_input, stretch=1)

        self.btn_add_task = QPushButton("+ Add Task", self)
        self.btn_add_task.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_task.setStyleSheet("""
            QPushButton {
                background: #FF8B77;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #FF7058;
            }
        """)
        self.btn_add_task.clicked.connect(self._add_task)
        add_bar.addWidget(self.btn_add_task)

        layout.addLayout(add_bar)

        # Task Table
        self.task_table = QTableWidget(self)
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["Done", "Task", "Due / Reminder", "Priority"])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                gridline-color: #EDF2F7;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background: #F7FAFC;
                color: #4A5568;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        self.task_table.itemChanged.connect(self._on_task_item_changed)
        layout.addWidget(self.task_table, stretch=1)

        # Bottom row
        btn_bar = QHBoxLayout()
        btn_del = QPushButton("🗑️ Delete Completed Tasks", self)
        btn_del.setStyleSheet(self._secondary_btn_style())
        btn_del.clicked.connect(self._delete_completed_tasks)
        btn_bar.addWidget(btn_del)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self.refresh_tasks()
        return widget

    def refresh_tasks(self):
        tasks = self.task_manager.list_tasks()
        self.task_table.blockSignals(True)
        self.task_table.setRowCount(len(tasks))

        for row, t in enumerate(tasks):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked if t.get("completed") else Qt.CheckState.Unchecked)
            chk_item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.task_table.setItem(row, 0, chk_item)

            title_item = QTableWidgetItem(t["title"])
            if t.get("completed"):
                title_item.setForeground(QColor("#A0AEC0"))
                f = title_item.font()
                f.setStrikeOut(True)
                title_item.setFont(f)
            self.task_table.setItem(row, 1, title_item)

            due_str = t.get("due_date", "No reminder")
            due_item = QTableWidgetItem(due_str if due_str else "No reminder")
            due_item.setForeground(QColor("#718096"))
            self.task_table.setItem(row, 2, due_item)

            prio = t.get("priority", "medium").upper()
            prio_item = QTableWidgetItem(prio)
            prio_color = "#E53E3E" if prio == "HIGH" else ("#38A169" if prio == "LOW" else "#DD6B20")
            prio_item.setForeground(QColor(prio_color))
            self.task_table.setItem(row, 3, prio_item)

        self.task_table.blockSignals(False)

    def _on_task_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0:
            task_id = item.data(Qt.ItemDataRole.UserRole)
            completed = (item.checkState() == Qt.CheckState.Checked)
            self.task_manager.complete_task(task_id, completed=completed)
            self.refresh_tasks()

    def _add_task(self):
        title = self.task_title_input.text().strip()
        if not title:
            return
        self.task_manager.add_task(title)
        self.task_title_input.clear()
        self.refresh_tasks()

    def _delete_completed_tasks(self):
        tasks = self.task_manager.list_tasks()
        deleted = 0
        for t in tasks:
            if t.get("completed"):
                self.task_manager.delete_task(t["id"])
                deleted += 1
        if deleted > 0:
            self.refresh_tasks()

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _secondary_btn_style(self) -> str:
        return """
            QPushButton {
                background: #EDF2F7;
                color: #4A5568;
                border: 1px solid #CBD5E0;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #E2E8F0;
                color: #2D3748;
            }
        """

    def open_search_tab(self, query: str = ""):
        self.tabs.setCurrentIndex(0)
        if query:
            self.search_input.setText(query)
            self._execute_search()
        self.show()
        self.raise_()
        self.activateWindow()

    def open_organizer_tab(
        self,
        rule: str = "type",
        filter_text: str = "",
        dest_folder: str = ""
    ):
        self.tabs.setCurrentIndex(1)
        idx = self.org_rule_combo.findData(rule)
        if idx >= 0:
            self.org_rule_combo.setCurrentIndex(idx)
        if filter_text and hasattr(self, "org_filter_input"):
            self.org_filter_input.setEnabled(True)
            self.org_filter_input.setText(filter_text)
        if dest_folder and hasattr(self, "org_subfolder_input"):
            self.org_subfolder_input.setText(dest_folder)
        self._preview_organization()
        self.show()
        self.raise_()
        self.activateWindow()

    def open_hunter_tab(self):
        self.tabs.setCurrentIndex(2)
        self.show()
        self.raise_()
        self.activateWindow()

    def open_chat_tab(self):
        self.tabs.setCurrentIndex(3)
        self.chat_input.setFocus()
        self.show()
        self.raise_()
        self.activateWindow()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3: Duplicate & Junk Hunter
    # ─────────────────────────────────────────────────────────────────────────
    def _build_hunter_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header info
        info_banner = QFrame(self)
        info_banner.setStyleSheet("""
            QFrame {
                background: #FFF5F5;
                border: 1px solid #FED7D7;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        b_lay = QHBoxLayout(info_banner)
        b_lay.setContentsMargins(8, 4, 8, 4)
        lbl_info = QLabel("🧹 Duplicate & Junk Hunter: Reclaim disk space by safely removing duplicate downloads and dead shortcuts.", info_banner)
        lbl_info.setStyleSheet("color: #C53030; font-size: 11px; font-weight: bold;")
        b_lay.addWidget(lbl_info)
        layout.addWidget(info_banner)

        # Top scan button controls
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        btn_scan_dupes = QPushButton("🔍 Scan Duplicate Downloads", self)
        btn_scan_dupes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_scan_dupes.setStyleSheet("""
            QPushButton {
                background: #E53E3E;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #C53030;
            }
        """)
        btn_scan_dupes.clicked.connect(self._scan_duplicates)
        btn_bar.addWidget(btn_scan_dupes)

        btn_scan_shortcuts = QPushButton("🔍 Scan Dead Desktop Shortcuts", self)
        btn_scan_shortcuts.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_scan_shortcuts.setStyleSheet(self._secondary_btn_style())
        btn_scan_shortcuts.clicked.connect(self._scan_dead_shortcuts)
        btn_bar.addWidget(btn_scan_shortcuts)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # Hunter Results Table
        self.hunter_table = QTableWidget(self)
        self.hunter_table.setColumnCount(4)
        self.hunter_table.setHorizontalHeaderLabels(["Remove?", "Item Name", "Type / Detail", "Size / Target"])
        self.hunter_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.hunter_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.hunter_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.hunter_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.hunter_table.setColumnWidth(1, 260)
        self.hunter_table.setAlternatingRowColors(True)
        self.hunter_table.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                gridline-color: #EDF2F7;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background: #F7FAFC;
                color: #4A5568;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        layout.addWidget(self.hunter_table, stretch=1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        btn_sel_all = QPushButton("Select All", self)
        btn_sel_all.setStyleSheet(self._secondary_btn_style())
        btn_sel_all.clicked.connect(self._select_all_hunter_items)
        bottom_bar.addWidget(btn_sel_all)

        btn_desel_all = QPushButton("Deselect All", self)
        btn_desel_all.setStyleSheet(self._secondary_btn_style())
        btn_desel_all.clicked.connect(self._deselect_all_hunter_items)
        bottom_bar.addWidget(btn_desel_all)

        self.hunter_status_label = QLabel("Click 'Scan Duplicate Downloads' or 'Scan Dead Desktop Shortcuts' to start.", self)
        self.hunter_status_label.setStyleSheet("color: #718096; font-size: 11px;")
        bottom_bar.addWidget(self.hunter_status_label, stretch=1)

        self.btn_delete_hunter = QPushButton("🗑️ Clean Selected Items", self)
        self.btn_delete_hunter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_hunter.setEnabled(False)
        self.btn_delete_hunter.setStyleSheet("""
            QPushButton {
                background: #E53E3E;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #C53030;
            }
            QPushButton:disabled {
                background: #CBD5E0;
                color: #A0AEC0;
            }
        """)
        self.btn_delete_hunter.clicked.connect(self._execute_hunter_delete)
        bottom_bar.addWidget(self.btn_delete_hunter)

        layout.addLayout(bottom_bar)
        return widget

    def _scan_duplicates(self):
        dupes = self.cleanup_hunter.scan_duplicate_downloads()
        self._hunter_items = []
        self.hunter_table.setRowCount(len(dupes))
        total_wasted = 0

        for row, item in enumerate(dupes):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)
            self.hunter_table.setItem(row, 0, chk_item)

            name_item = QTableWidgetItem(f"📄 {item['duplicate_name']}")
            self.hunter_table.setItem(row, 1, name_item)

            type_item = QTableWidgetItem(f"Duplicate of {item['original_name']}")
            type_item.setForeground(QColor("#C53030"))
            self.hunter_table.setItem(row, 2, type_item)

            size_item = QTableWidgetItem(item['size_formatted'])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.hunter_table.setItem(row, 3, size_item)

            self._hunter_items.append({"path": item["duplicate_path"], "name": item["duplicate_name"]})
            total_wasted += item.get("size", 0)

        self.btn_delete_hunter.setEnabled(len(dupes) > 0)
        if dupes:
            wasted_str = format_file_size(total_wasted)
            self.hunter_status_label.setText(f"Found {len(dupes)} duplicate files wasting {wasted_str} of disk space.")
        else:
            self.hunter_status_label.setText("✨ No duplicate downloads found! Your Downloads folder is clean.")

    def _scan_dead_shortcuts(self):
        shortcuts = self.cleanup_hunter.scan_dead_shortcuts()
        self._hunter_items = []
        self.hunter_table.setRowCount(len(shortcuts))

        for row, item in enumerate(shortcuts):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)
            self.hunter_table.setItem(row, 0, chk_item)

            name_item = QTableWidgetItem(f"🔗 {item['name']}")
            self.hunter_table.setItem(row, 1, name_item)

            type_item = QTableWidgetItem("Broken Shortcut")
            type_item.setForeground(QColor("#C53030"))
            self.hunter_table.setItem(row, 2, type_item)

            target_item = QTableWidgetItem(item['target'])
            target_item.setForeground(QColor("#718096"))
            self.hunter_table.setItem(row, 3, target_item)

            self._hunter_items.append({"path": item["path"], "name": item["name"]})

        self.btn_delete_hunter.setEnabled(len(shortcuts) > 0)
        if shortcuts:
            self.hunter_status_label.setText(f"Found {len(shortcuts)} broken desktop shortcuts pointing to missing targets.")
        else:
            self.hunter_status_label.setText("✨ All desktop shortcuts point to valid applications! No broken links found.")

    def _select_all_hunter_items(self):
        for row in range(self.hunter_table.rowCount()):
            item = self.hunter_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all_hunter_items(self):
        for row in range(self.hunter_table.rowCount()):
            item = self.hunter_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _execute_hunter_delete(self):
        paths_to_delete = []
        for row in range(self.hunter_table.rowCount()):
            item = self.hunter_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                paths_to_delete.append(self._hunter_items[row]["path"])

        if not paths_to_delete:
            QMessageBox.information(self, "No Selection", "Please check at least one item to remove.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Cleanup",
            f"Are you sure you want to remove {len(paths_to_delete)} selected items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        res = self.cleanup_hunter.delete_items(paths_to_delete)
        if res.get("success"):
            freed = res.get("freed_formatted", "0 B")
            count = res.get("deleted_count", 0)
            self.hunter_status_label.setText(f"🧹 Cleaned {count} items! Freed {freed} of disk space.")
            QMessageBox.information(self, "Cleanup Complete", f"Successfully cleaned {count} items and reclaimed {freed} of space!")
            self.hunter_table.setRowCount(0)
            self._hunter_items = []
            self.btn_delete_hunter.setEnabled(False)
        else:
            QMessageBox.warning(self, "Cleanup Notice", f"Some items could not be removed: {', '.join(res.get('errors', []))}")
