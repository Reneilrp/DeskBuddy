"""
DeskBuddy - Window & Tab Surface Detector
Detects foreground application windows (browsers, editors, documents)
so desktop companions can climb walls, walk on tabs, and sit on window frames.
Uses native Windows user32 APIs with cross-platform safety.
"""

import sys
from typing import Optional, Tuple
from PyQt6.QtCore import QRect

class WindowDetector:
    def __init__(self):
        self._is_windows = sys.platform.startswith("win")
        self._mock_window_rect: Optional[QRect] = None

    def set_mock_window(self, rect: Optional[QRect]):
        """Used for testing and simulation."""
        self._mock_window_rect = rect

    def get_active_window_rect(self) -> Optional[QRect]:
        """
        Returns QRect of the current foreground window (e.g. Chrome, VS Code, Notepad).
        Excludes minimized windows, the Windows desktop, and tiny system popups.
        """
        if self._mock_window_rect is not None:
            return self._mock_window_rect

        if not self._is_windows:
            return None

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            # Check if window is visible and not iconic (minimized)
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return None

            # Optional check to avoid latching onto the Windows Shell/Desktop
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()

            # Ignore empty or Shell windows
            if not title or title in ("Program Manager", "DeskBuddy"):
                return None

            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                # Must be a reasonably sized application window
                if w > 250 and h > 180:
                    return QRect(rect.left, rect.top, w, h)
        except Exception:
            pass

        return None
