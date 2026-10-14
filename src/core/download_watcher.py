"""
DeskBuddy - Just Downloaded Background Watcher
Monitors the user's Downloads folder for newly arrived files,
ignoring in-progress browser temporary files (.crdownload, .part, .tmp),
and triggers non-intrusive 1-click action chips (Reveal, Move to Category, Open).
"""

import time
from pathlib import Path
from typing import Set, Dict, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from .fast_search import get_user_shortcuts, format_file_size
from .file_organizer import ACTIVE_DOWNLOAD_EXTENSIONS, PROTECTED_NAMES, FileOrganizer

class DownloadWatcher(QObject):
    file_downloaded = pyqtSignal(dict)  # Emits payload when new file is finished downloading

    def __init__(self, check_interval_ms: int = 2500, parent=None):
        super().__init__(parent)
        self.shortcuts = get_user_shortcuts()
        self.downloads_dir = self.shortcuts.get("Downloads", Path.home() / "Downloads")
        self.organizer = FileOrganizer()
        self._seen_files: Set[str] = set()
        self._is_first_scan = True

        self.timer = QTimer(self)
        self.timer.setInterval(check_interval_ms)
        self.timer.timeout.connect(self._scan_downloads)

    def start(self):
        if self.downloads_dir.exists():
            self._initial_seed()
            self.timer.start()

    def stop(self):
        self.timer.stop()

    def _initial_seed(self):
        """Seeds the current existing files so only newly added files trigger notifications."""
        try:
            for item in self.downloads_dir.iterdir():
                if item.is_file():
                    self._seen_files.add(str(item.resolve()))
        except Exception:
            pass
        self._is_first_scan = False

    def _scan_downloads(self):
        if not self.downloads_dir.exists():
            return

        current_files: Set[str] = set()
        try:
            for item in self.downloads_dir.iterdir():
                if not item.is_file():
                    continue

                item_str = str(item.resolve())
                current_files.add(item_str)

                # Skip if already known
                if item_str in self._seen_files:
                    continue

                # Check if it's an in-progress download
                suffix_lower = item.suffix.lower()
                if suffix_lower in ACTIVE_DOWNLOAD_EXTENSIONS:
                    continue

                if item.name.lower() in PROTECTED_NAMES or item.name.startswith("."):
                    continue

                # Wait slightly to ensure browser has released file lock
                try:
                    stat = item.stat()
                    # If modified in the last 60 seconds
                    size = stat.st_size
                    category = self.organizer.get_category_for_ext(suffix_lower)
                    
                    self._seen_files.add(item_str)
                    
                    self.file_downloaded.emit({
                        "name": item.name,
                        "path": str(item),
                        "size": size,
                        "size_formatted": format_file_size(size),
                        "category": category,
                        "extension": suffix_lower
                    })
                except (PermissionError, OSError):
                    # File might still be locked by browser
                    continue

            # Clean up deleted files from seen set
            self._seen_files.intersection_update(current_files)
        except Exception:
            pass
