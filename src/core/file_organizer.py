"""
DeskBuddy - Safe File & Folder Organizer
Helps the user organize cluttered directories (Desktop, Downloads, etc.)
safely with active download shields, custom categorization rules,
interactive dry-run previewing, and one-click undo transactions.
"""

import os
import fnmatch
import shutil
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

EXT_CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"},
    "Documents": {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".csv", ".md", ".rtf", ".odt", ".epub"},
    "Archives": {".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".tgz", ".iso"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"},
    "Video": {".mp4", ".mkv", ".mov", ".avi", ".flv", ".webm", ".wmv", ".m4v"},
    "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".c", ".cpp", ".h", ".rs", ".go", ".java", ".sh", ".sql"},
    "Installers": {".exe", ".msi", ".deb", ".rpm", ".dmg", ".pkg", ".appimage"}
}

# Shields: files that are currently active downloads or temp files MUST NEVER BE TOUCHED
ACTIVE_DOWNLOAD_EXTENSIONS = {
    ".crdownload", ".part", ".tmp", ".download", ".aria2", ".partial", ".opdownload"
}

# Protected files and folders that must never be moved or modified
PROTECTED_NAMES = {
    ".git", ".venv", "venv", "node_modules", ".cache", ".config", ".deskbuddy",
    "system volume information", "$recycle.bin", "desktop.ini", "thumbs.db",
    ".ds_store", "lost+found"
}

def get_user_shortcuts() -> Dict[str, Path]:
    """Returns standard user directories cross-platform (Windows & Linux/WSL)."""
    home = Path.home()
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
    for k, v in list(shortcuts.items()):
        if not v.exists():
            shortcuts[k] = home / k if (home / k).exists() else home

    return shortcuts

def get_unique_destination(dest_dir: Path, filename: str) -> Path:
    """Ensures no existing file is overwritten by appending a counter."""
    target = dest_dir / filename
    if not target.exists():
        return target
    
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem} ({counter}){suffix}"
        target = dest_dir / new_name
        if not target.exists():
            return target
        counter += 1

class FileOrganizer:
    def __init__(self, categories: Optional[Dict[str, Set[str]]] = None):
        self.categories = categories or EXT_CATEGORIES
        self.undo_history: List[Dict[str, Any]] = []

    def get_category_for_ext(self, ext: str) -> str:
        ext_lower = ext.lower()
        for category, extensions in self.categories.items():
            if ext_lower in extensions:
                return category
        return "Others"

    def is_protected(self, item: Path) -> bool:
        """Determines if a file should be protected from organization."""
        name_lower = item.name.lower()
        if name_lower.startswith(".") or name_lower.startswith("~$"):
            return True
        if name_lower in PROTECTED_NAMES:
            return True
        # Shield active downloads
        if item.suffix.lower() in ACTIVE_DOWNLOAD_EXTENSIONS:
            return True
        return False

    def scan_directory(self, target_dir: Path) -> Dict[str, List[Path]]:
        """
        Scans direct child files in target_dir and categorizes them by file type.
        Does not recurse into subdirectories to keep operations safe and predictable.
        """
        target = Path(target_dir).resolve()
        results: Dict[str, List[Path]] = {cat: [] for cat in self.categories}
        results["Others"] = []

        if not target.exists() or not target.is_dir():
            return results

        try:
            for item in target.iterdir():
                if item.is_dir():
                    continue
                if self.is_protected(item):
                    continue

                category = self.get_category_for_ext(item.suffix)
                results[category].append(item)
        except (PermissionError, OSError):
            pass

        return results

    def plan_organization(
        self,
        target_dir: Path,
        rule: str = "type",
        ext_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        pattern_filter: Optional[str] = None,
        custom_subfolder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a dry-run list of planned file moves based on the selected rule.
        Rules:
          - 'type': Organizes all loose files by extension category (Images, Docs, Archives, etc.)
          - 'date': Organizes all loose files by modified year-month (e.g., '2026-10 (October)')
          - 'extension': Organizes only files matching specified extension(s) (e.g. '.png' or '.png, .jpg')
          - 'category': Organizes only files belonging to a specific category (e.g. 'Images')
          - 'pattern': Organizes only files matching a wildcard pattern (e.g. 'screenshot*')
        """
        target = Path(target_dir).resolve()
        if not target.exists() or not target.is_dir():
            return {"success": False, "error": f"Directory '{target}' does not exist or is not a directory."}

        # Parse extension filter
        target_exts = set()
        if ext_filter:
            for part in ext_filter.split(","):
                clean = part.strip().lower().lstrip("*")
                if clean:
                    if not clean.startswith("."):
                        clean = "." + clean
                    target_exts.add(clean)

        planned_moves: List[Dict[str, Any]] = []

        try:
            for item in target.iterdir():
                if item.is_dir() or self.is_protected(item):
                    continue

                item_ext = item.suffix.lower()
                item_cat = self.get_category_for_ext(item_ext)

                # Filter matching
                if rule == "extension" or (ext_filter and rule != "category" and rule != "pattern"):
                    if target_exts and item_ext not in target_exts:
                        continue
                elif rule == "category" or category_filter:
                    cat_target = (category_filter or ext_filter or "").strip().lower()
                    if cat_target and item_cat.lower() != cat_target:
                        continue
                elif rule == "pattern" or pattern_filter:
                    pat = (pattern_filter or ext_filter or "*").strip()
                    if not fnmatch.fnmatch(item.name.lower(), pat.lower()):
                        continue

                try:
                    stat = item.stat()
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    mtime_str = mtime.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    size = 0
                    mtime = datetime.now()
                    mtime_str = "Unknown"

                # Determine destination folder name
                if custom_subfolder and custom_subfolder.strip():
                    dest_sub = custom_subfolder.strip()
                elif rule == "date":
                    month_name = mtime.strftime("%B")
                    dest_sub = f"{mtime.strftime('%Y-%m')} ({month_name})"
                elif rule == "extension" and target_exts:
                    ext_label = "_".join(e.lstrip('.').upper() for e in sorted(target_exts))
                    dest_sub = f"{ext_label} Files"
                elif rule == "pattern":
                    dest_sub = "Filtered Files"
                else:
                    dest_sub = item_cat

                dest_dir = target / dest_sub
                dest = get_unique_destination(dest_dir, item.name)

                planned_moves.append({
                    "name": item.name,
                    "source": str(item),
                    "destination": str(dest),
                    "category": dest_sub,
                    "size": size,
                    "modified": mtime_str,
                    "ext": item_ext
                })
        except Exception as e:
            return {"success": False, "error": f"Error scanning directory: {e}"}

        return {
            "success": True,
            "target_dir": str(target),
            "rule": rule,
            "moves": planned_moves,
            "total_files": len(planned_moves)
        }

    def execute_moves(self, moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes a specific list of planned moves.
        Records an undo transaction to allow one-click rollback.
        """
        if not moves:
            return {"success": True, "moved_count": 0, "moves": []}

        executed_moves: List[Dict[str, str]] = []
        created_dirs: Set[str] = set()
        moved_count = 0

        for move in moves:
            src = Path(move["source"])
            dst = Path(move["destination"])

            if not src.exists():
                continue

            try:
                # Ensure destination directory exists and track if created
                if not dst.parent.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    created_dirs.add(str(dst.parent))

                # Handle collision safety
                final_dst = get_unique_destination(dst.parent, dst.name)
                shutil.move(src, final_dst)
                executed_moves.append({
                    "source": str(src),
                    "destination": str(final_dst)
                })
                moved_count += 1
            except Exception as e:
                # If a partial failure occurs, log transaction for whatever was already moved
                if executed_moves:
                    self.undo_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "moves": executed_moves,
                        "created_dirs": list(created_dirs)
                    })
                return {"success": False, "error": f"Failed to move {src.name}: {e}", "moved_count": moved_count}

        # Save successful transaction for undo
        if executed_moves:
            self.undo_history.append({
                "timestamp": datetime.now().isoformat(),
                "moves": executed_moves,
                "created_dirs": list(created_dirs)
            })

        return {
            "success": True,
            "moved_count": moved_count,
            "moves": executed_moves
        }

    def organize_directory(
        self,
        target_dir: Path,
        dry_run: bool = False,
        rule: str = "type",
        ext_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        pattern_filter: Optional[str] = None,
        custom_subfolder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sorts files into subdirectories named after each category, date, or custom subfolder.
        If dry_run is True, returns planned actions without moving files.
        """
        plan = self.plan_organization(
            target_dir=target_dir,
            rule=rule,
            ext_filter=ext_filter,
            category_filter=category_filter,
            pattern_filter=pattern_filter,
            custom_subfolder=custom_subfolder
        )
        if not plan.get("success"):
            return plan

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "moves": plan["moves"],
                "total_files": plan["total_files"]
            }

        exec_res = self.execute_moves(plan["moves"])
        exec_res["dry_run"] = False
        return exec_res

    def undo_last(self) -> Dict[str, Any]:
        """
        Rolls back the most recent file organization action,
        moving all files back to their exact original positions.
        Cleans up empty created category directories.
        """
        if not self.undo_history:
            return {"success": False, "error": "No organization actions to undo."}

        transaction = self.undo_history.pop()
        moves = transaction.get("moves", [])
        created_dirs = transaction.get("created_dirs", [])
        reverted_count = 0
        errors = []

        # Move files backwards from destination to source
        for move in reversed(moves):
            src = Path(move["source"])
            dst = Path(move["destination"])

            if not dst.exists():
                errors.append(f"Cannot revert {dst.name} (file no longer exists at destination).")
                continue

            try:
                # Ensure original parent directory exists
                src.parent.mkdir(parents=True, exist_ok=True)
                final_src = get_unique_destination(src.parent, src.name)
                shutil.move(dst, final_src)
                reverted_count += 1
            except Exception as e:
                errors.append(f"Error reverting {dst.name}: {e}")

        # Clean up empty category directories that were created
        for dir_path_str in created_dirs:
            dir_path = Path(dir_path_str)
            try:
                if dir_path.exists() and dir_path.is_dir():
                    # Only remove if directory is completely empty
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
            except Exception:
                pass

        return {
            "success": len(errors) == 0,
            "reverted_count": reverted_count,
            "errors": errors
        }
