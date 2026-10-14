"""
DeskBuddy - System Tray Integration
Allows showing, hiding, organizing, and accessing tasks from the taskbar,
as well as configuring app deletion reaction behaviors.
"""

from pathlib import Path
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction

class DeskBuddyTray(QObject):
    show_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    toggle_requested = pyqtSignal()
    workspace_requested = pyqtSignal()
    resonators_requested = pyqtSignal()
    tasks_requested = pyqtSignal()
    organize_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    deletion_reaction_changed = pyqtSignal(str)

    def __init__(self, icon_path: Path, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.tray_icon = QSystemTrayIcon(QIcon(str(self.icon_path)), parent)
        self.tray_icon.setToolTip("DeskBuddy - Your Desktop AI Companion")
        self.deletion_reaction_mode = "chomp"
        self._setup_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)

    def set_deletion_reaction_mode(self, mode: str):
        self.deletion_reaction_mode = mode
        self.deletion_reaction_changed.emit(mode)
        self._setup_menu()

    def _setup_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #2D3748;
                font-size: 13px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #FFEACC;
                color: #4A2E18;
            }
            QMenu::item:disabled {
                color: #A0AEC0;
            }
        """)

        action_show = QAction("🐾 Show Companion", menu, triggered=self.show_requested.emit)
        action_hide = QAction("🙈 Hide Companion", menu, triggered=self.hide_requested.emit)
        action_workspace = QAction("🖥️ Open Companion Workspace", menu, triggered=self.workspace_requested.emit)
        action_switch = QAction("✨ Switch Resonator", menu, triggered=self.resonators_requested.emit)
        action_tasks = QAction("📋 View Tasks & Reminders", menu, triggered=self.tasks_requested.emit)
        action_organize = QAction("🧹 Tidy Desktop Now", menu, triggered=self.organize_requested.emit)

        # Deletion Reaction Submenu
        sub_deletion = menu.addMenu("🗑️ App Deletion Reaction")
        m = self.deletion_reaction_mode
        act_o = QAction("❌ Disabled" + ("  ✓" if m == "off" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("off"))
        act_c = QAction("🐠 Paper-Carp Chomp (Eat Trash) — (Soon)" + ("  ✓" if m == "chomp" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("chomp"))
        act_s = QAction("✂️ Scissor Shredder (Confetti) — (Soon)" + ("  ✓" if m == "snip" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("snip"))
        act_v = QAction("🕳️ Void Vortex (Universal) — (Soon)" + ("  ✓" if m == "vortex" else ""), menu, triggered=lambda: self.set_deletion_reaction_mode("vortex"))

        # Greyed out / disabled as requested
        act_c.setEnabled(False)
        act_s.setEnabled(False)
        act_v.setEnabled(False)

        sub_deletion.addAction(act_o)
        sub_deletion.addSeparator()
        sub_deletion.addAction(act_c)
        sub_deletion.addAction(act_s)
        sub_deletion.addAction(act_v)

        action_quit = QAction("🚪 Quit DeskBuddy", menu, triggered=self.quit_requested.emit)

        menu.addAction(action_show)
        menu.addAction(action_hide)
        menu.addAction(action_workspace)
        menu.addAction(action_switch)
        menu.addSeparator()
        menu.addAction(action_tasks)
        menu.addAction(action_organize)
        menu.addMenu(sub_deletion)
        menu.addSeparator()
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)

    def show(self):
        self.tray_icon.show()

    def show_message(self, title: str, message: str, msecs: int = 5000):
        self.tray_icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            msecs
        )

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_requested.emit()
