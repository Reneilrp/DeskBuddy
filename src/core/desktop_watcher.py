"""
DeskBuddy - Desktop Deletion & File Watcher
Monitors the user's Desktop directory with QFileSystemWatcher for file/app deletions
and emits signals to trigger companion eating, snipping, or vortex reactions.
"""

import os
from pathlib import Path
from typing import Set
from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher

class DesktopWatcher(QObject):
    file_deleted = pyqtSignal(str)
    file_added = pyqtSignal(str)

    def __init__(self, desktop_path: Path = None, parent=None):
        super().__init__(parent)
        if desktop_path is None:
            desktop_path = Path.home() / "Desktop"
            if not desktop_path.exists():
                desktop_path = Path.home()

        self.desktop_path = desktop_path
        self._watcher = QFileSystemWatcher(self)
        self._known_files: Set[str] = set()
        self.is_running = False

        self._init_snapshot()

    def _init_snapshot(self):
        """Snapshots existing desktop entries."""
        if self.desktop_path.exists() and self.desktop_path.is_dir():
            try:
                self._known_files = set(os.listdir(str(self.desktop_path)))
            except Exception:
                self._known_files = set()

    def start(self):
        """Starts monitoring the desktop folder."""
        if self.desktop_path.exists() and self.desktop_path.is_dir():
            self._init_snapshot()
            self._watcher.addPath(str(self.desktop_path))
            self._watcher.directoryChanged.connect(self._on_directory_changed)
            self.is_running = True

    def stop(self):
        """Stops monitoring."""
        if self.is_running:
            self._watcher.removePath(str(self.desktop_path))
            self.is_running = False

    def simulate_deletion(self, filename: str):
        """Used for automated unit testing."""
        clean_name = self._clean_filename(filename)
        self.file_deleted.emit(clean_name)

    def _on_directory_changed(self, path: str):
        try:
            current_files = set(os.listdir(str(self.desktop_path)))
        except Exception:
            return

        # Check for deleted files
        deleted = self._known_files - current_files
        added = current_files - self._known_files

        # Update cache
        self._known_files = current_files

        for file_name in deleted:
            # Filter out hidden or temporary desktop clutter
            if file_name.startswith("~") or file_name.startswith("."):
                continue
            clean_name = self._clean_filename(file_name)
            self.file_deleted.emit(clean_name)

        for file_name in added:
            if not file_name.startswith("~") and not file_name.startswith("."):
                clean_name = self._clean_filename(file_name)
                self.file_added.emit(clean_name)

    def _clean_filename(self, filename: str) -> str:
        """Strips .lnk / .url extensions for friendly display."""
        clean = filename
        if clean.lower().endswith(".lnk"):
            clean = clean[:-4]
        elif clean.lower().endswith(".url"):
            clean = clean[:-4]
        return clean
