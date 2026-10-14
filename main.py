#!/usr/bin/env python3
"""
DeskBuddy - AI Desktop Pet Companion
Main Entry Point
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.app import DeskBuddyApp

def main():
    # High DPI scaling attributes are default in Qt6
    app = QApplication(sys.argv)
    app.setApplicationName("DeskBuddy")
    app.setApplicationDisplayName("DeskBuddy")
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray even if windows close

    base_dir = Path(__file__).resolve().parent
    desk_buddy = DeskBuddyApp(app, base_dir)
    desk_buddy.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
