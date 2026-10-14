"""
DeskBuddy - Stash Manager (Chisa's Pocket)
Maintains temporary file references dropped onto the companion,
allowing effortless drag-and-drop forwarding into browsers, Discord, or other apps
without cluttering the desktop.
"""

from pathlib import Path
from typing import List, Union, Optional

class StashManager:
    def __init__(self):
        self._stashed_files: List[Path] = []

    def add_files(self, paths: List[Union[str, Path]]) -> int:
        """Adds files to the stash, avoiding duplicates."""
        added = 0
        for p in paths:
            path_obj = Path(p).resolve()
            if path_obj.exists() and path_obj not in self._stashed_files:
                self._stashed_files.append(path_obj)
                added += 1
        return added

    def remove_file(self, path: Union[str, Path]) -> bool:
        """Removes a single file from the stash."""
        path_obj = Path(path).resolve()
        if path_obj in self._stashed_files:
            self._stashed_files.remove(path_obj)
            return True
        return False

    def clear(self):
        """Clears all stashed files."""
        self._stashed_files.clear()

    def get_files(self) -> List[Path]:
        """Returns valid existing files in the stash."""
        # Prune files that no longer exist
        self._stashed_files = [p for p in self._stashed_files if p.exists()]
        return list(self._stashed_files)

    def count(self) -> int:
        return len(self.get_files())

    def has_files(self) -> bool:
        return self.count() > 0

    def summary(self) -> str:
        files = self.get_files()
        if not files:
            return "Pocket is empty."
        if len(files) == 1:
            return f"Holding '{files[0].name}'"
        return f"Holding {len(files)} files: {', '.join(f.name for f in files[:2])}{'...' if len(files) > 2 else ''}"
