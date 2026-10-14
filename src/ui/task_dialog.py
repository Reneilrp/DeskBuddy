"""
DeskBuddy - Task Management Dialog
Clean GUI window to review, create, and complete tasks.
"""

from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QSpinBox,
    QMessageBox, QFrame
)
from PyQt6.QtGui import QIcon
from ..core.task_manager import TaskManager

class TaskDialog(QDialog):
    tasks_changed = pyqtSignal()

    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self.setWindowTitle("DeskBuddy Tasks & Reminders")
        self.resize(420, 480)
        self._setup_ui()
        self.refresh_tasks()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
            QLabel {
                color: #2D3748;
                font-size: 13px;
            }
            QLineEdit, QSpinBox {
                background: #FFFFFF;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                color: #2D3748;
            }
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EDF2F7;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #FFEACC;
                color: #4A2E18;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header
        header = QLabel("📋 Your Task List & Reminders")
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #4A2E18;")
        layout.addWidget(header)

        # Task List Widget
        self.task_list = QListWidget(self)
        layout.addWidget(self.task_list)

        # Action Buttons for Selected Task
        btn_bar = QHBoxLayout()
        self.btn_complete = QPushButton("✔ Complete Task", self)
        self.btn_complete.setStyleSheet("""
            QPushButton {
                background: #48BB78; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 7px 14px;
            }
            QPushButton:hover { background: #38A169; }
        """)
        self.btn_complete.clicked.connect(self._on_complete_task)

        self.btn_delete = QPushButton("🗑 Delete", self)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: #E53E3E; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 7px 14px;
            }
            QPushButton:hover { background: #C53030; }
        """)
        self.btn_delete.clicked.connect(self._on_delete_task)

        btn_bar.addWidget(self.btn_complete)
        btn_bar.addWidget(self.btn_delete)
        layout.addLayout(btn_bar)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(line)

        # Add Task Section
        add_label = QLabel("➕ Add New Task")
        add_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #4A2E18;")
        layout.addWidget(add_label)

        self.input_task_title = QLineEdit(self)
        self.input_task_title.setPlaceholderText("Task description (e.g. Finish report)")
        layout.addWidget(self.input_task_title)

        time_layout = QHBoxLayout()
        time_label = QLabel("Remind in (minutes):")
        self.spin_minutes = QSpinBox(self)
        self.spin_minutes.setRange(0, 1440)
        self.spin_minutes.setValue(0)
        self.spin_minutes.setSpecialValueText("No reminder")

        time_layout.addWidget(time_label)
        time_layout.addWidget(self.spin_minutes)
        layout.addLayout(time_layout)

        self.btn_add = QPushButton("Add Task", self)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background: #FFB049; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 8px 16px;
            }
            QPushButton:hover { background: #FF9B20; }
        """)
        self.btn_add.clicked.connect(self._on_add_task)
        layout.addWidget(self.btn_add)

    def refresh_tasks(self):
        self.task_list.clear()
        tasks = self.task_manager.list_tasks(status="pending")
        for t in tasks:
            due_str = f" [Due: {t['due_at']}]" if t.get('due_at') else ""
            item_text = f"#{t['id']} • {t['title']}{due_str}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.task_list.addItem(item)

    def _get_selected_task_id(self):
        item = self.task_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_add_task(self):
        title = self.input_task_title.text().strip()
        if not title:
            QMessageBox.warning(self, "DeskBuddy", "Please enter a task title.")
            return

        minutes = self.spin_minutes.value()
        due_at = None
        if minutes > 0:
            due_at = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")

        self.task_manager.add_task(title=title, due_at=due_at)
        self.input_task_title.clear()
        self.spin_minutes.setValue(0)
        self.refresh_tasks()
        self.tasks_changed.emit()

    def _on_complete_task(self):
        task_id = self._get_selected_task_id()
        if task_id:
            self.task_manager.complete_task(task_id)
            self.refresh_tasks()
            self.tasks_changed.emit()
        else:
            QMessageBox.information(self, "DeskBuddy", "Select a task from the list first.")

    def _on_delete_task(self):
        task_id = self._get_selected_task_id()
        if task_id:
            self.task_manager.delete_task(task_id)
            self.refresh_tasks()
            self.tasks_changed.emit()
        else:
            QMessageBox.information(self, "DeskBuddy", "Select a task from the list first.")
