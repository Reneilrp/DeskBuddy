"""
DeskBuddy - Fast File Search Engine (Speed Grep for Windows & Linux)
Performs sub-second, highly optimized directory scans using os.scandir
with intelligent junk-pruning, instant substring/wildcard/regex matching,
and native Windows File Explorer integration.
"""

import os
import sys
import fnmatch
import re
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator, Callable

# Directories to skip to guarantee maximum search velocity
IGNORED_DIRS = {
    # Version control & packages
    ".git", ".svn", ".hg", "node_modules", ".venv", "venv", "__pycache__", ".tox",
    # IDEs & caches
    ".idea", ".vscode", ".vs", ".cache", ".gradle", ".nuget",
    # Windows system & junk
    "$recycle.bin", "$winre_backup_partition.marker", "system volume information",
    "appdata\\local\\temp", "appdata/local/temp", "recovery", "msocache",
    # Android / build
    ".build", "target", "dist", "build", ".next", ".nuxt"
}

def format_file_size(size_bytes: int) -> str:
    """Formats bytes into human-readable B, KB, MB, GB."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_user_shortcuts() -> Dict[str, Path]:
    """Returns standard user directories cross-platform (Windows & Linux/WSL)."""
    home = Path.home()
    
    # Check Windows user profile if running in WSL
    win_home = None
    if Path("/mnt/c/Users").exists():
        for user_dir in Path("/mnt/c/Users").iterdir():
            if user_dir.is_dir() and user_dir.name not in ("All Users", "Default", "Default User", "Public"):
                win_home = user_dir
                break

    base = win_home if (win_home and win_home.exists()) else home

    shortcuts = {
        "Downloads": base / "Downloads",
        "Desktop": base / "Desktop",
        "Documents": base / "Documents",
        "Home": base,
    }
    
    # Fallback to home if specific folders don't exist
    for k, v in list(shortcuts.items()):
        if not v.exists():
            shortcuts[k] = home / k if (home / k).exists() else home

    return shortcuts

class FastSearchEngine:
    def __init__(self):
        self.shortcuts = get_user_shortcuts()

    def search(
        self,
        query: str,
        search_root: Optional[Path] = None,
        max_results: int = 100,
        case_sensitive: bool = False,
        file_only: bool = True,
        max_depth: int = 8,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        High-speed search across search_root using os.scandir.
        Returns list of matched file metadata dictionaries.
        """
        if not query or not query.strip():
            return []

        raw_query = query.strip()
        root = Path(search_root).resolve() if search_root else self.shortcuts.get("Downloads", Path.home())

        if not root.exists() or not root.is_dir():
            return []

        # Prepare matching logic
        is_wildcard = ("*" in raw_query or "?" in raw_query)
        q_clean = raw_query if case_sensitive else raw_query.lower()

        results: List[Dict[str, Any]] = []

        def match_name(name: str) -> bool:
            check_name = name if case_sensitive else name.lower()
            if is_wildcard:
                return fnmatch.fnmatch(check_name, q_clean)
            return q_clean in check_name

        def scan_recursive(dir_path: str, current_depth: int):
            if current_depth > max_depth or (stop_check and stop_check()):
                return
            if len(results) >= max_results:
                return

            try:
                with os.scandir(dir_path) as it:
                    subdirs = []
                    for entry in it:
                        if stop_check and stop_check():
                            return
                        if len(results) >= max_results:
                            return

                        name_lower = entry.name.lower()

                        # Skip ignored system & package directories
                        if entry.is_dir(follow_symlinks=False):
                            if name_lower in IGNORED_DIRS or name_lower.startswith("."):
                                continue
                            if not file_only and match_name(entry.name):
                                results.append(self._make_entry_dict(entry, is_dir=True))
                            subdirs.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            if name_lower.startswith("."):
                                continue
                            if match_name(entry.name):
                                results.append(self._make_entry_dict(entry, is_dir=False))

                    # Process subdirectories
                    for s in subdirs:
                        if len(results) >= max_results:
                            break
                        scan_recursive(s, current_depth + 1)
            except (PermissionError, OSError):
                pass

        scan_recursive(str(root), 1)
        return results

    def _make_entry_dict(self, entry: os.DirEntry, is_dir: bool) -> Dict[str, Any]:
        """Extracts file metadata cleanly with error tolerance."""
        try:
            stat = entry.stat(follow_symlinks=False)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        except Exception:
            size = 0
            mtime = "Unknown"

        ext = Path(entry.name).suffix.lower() if not is_dir else ""

        return {
            "name": entry.name,
            "path": entry.path,
            "is_dir": is_dir,
            "size": size,
            "size_formatted": format_file_size(size) if not is_dir else "<DIR>",
            "modified": mtime,
            "extension": ext
        }

    @staticmethod
    def reveal_in_explorer(file_path: str):
        """Highlights the file in Windows File Explorer or open default file manager on Linux."""
        target = Path(file_path).resolve()
        if not target.exists():
            return False

        system = platform.system()
        try:
            if system == "Windows":
                # Select/highlight file in explorer
                if target.is_file():
                    subprocess.Popen(f'explorer.exe /select,"{target}"')
                else:
                    subprocess.Popen(f'explorer.exe "{target}"')
                return True
            elif "/mnt/c" in str(target) or Path("/mnt/c/Windows").exists():
                # Running under WSL, convert path to Windows path for explorer.exe
                win_path = str(target).replace("/mnt/c/", "C:\\").replace("/", "\\")
                if target.is_file():
                    subprocess.Popen(["explorer.exe", f"/select,{win_path}"])
                else:
                    subprocess.Popen(["explorer.exe", win_path])
                return True
            else:
                # Linux native
                parent = target.parent if target.is_file() else target
                subprocess.Popen(["xdg-open", str(parent)])
                return True
        except Exception as e:
            print(f"Failed to reveal file: {e}")
            return False

    @staticmethod
    def open_file(file_path: str):
        """Launches or opens the file with default system application."""
        target = Path(file_path).resolve()
        if not target.exists():
            return False

        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(str(target))
                return True
            elif "/mnt/c" in str(target) or Path("/mnt/c/Windows").exists():
                win_path = str(target).replace("/mnt/c/", "C:\\").replace("/", "\\")
                subprocess.Popen(["cmd.exe", "/c", "start", "", win_path])
                return True
            else:
                subprocess.Popen(["xdg-open", str(target)])
                return True
        except Exception as e:
            print(f"Failed to open file: {e}")
            return False
