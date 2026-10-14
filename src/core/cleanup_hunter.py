"""
DeskBuddy - Cleanup Hunter (Duplicate Download & Dead Shortcut Hunter)
Identifies wasted disk space and clutter on Windows and Linux:
1. Duplicate Files: Detects duplicate downloads (e.g. `file (1).exe` vs `file.exe`)
   using matching sizes and SHA-256 chunk hashing.
2. Dead Shortcuts: Finds broken `.lnk` or `.desktop` files whose target executables
   were uninstalled or deleted.
"""

import os
import hashlib
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Union

from .fast_search import get_user_shortcuts, format_file_size

def compute_chunk_hash(file_path: Path, chunk_size: int = 65536) -> Optional[str]:
    """Computes a fast hash of the first and last chunk of a file for sub-second comparison."""
    try:
        size = file_path.stat().st_size
        if size == 0:
            return "empty"
        
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            if size <= chunk_size * 2:
                hasher.update(f.read())
            else:
                hasher.update(f.read(chunk_size))
                f.seek(size - chunk_size)
                hasher.update(f.read(chunk_size))
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None

def resolve_windows_lnk_target(lnk_path: Path) -> Optional[str]:
    """
    Pure-Python parser for Windows Shell Link (.lnk) files.
    Extracts the local base path without requiring pywin32.
    """
    try:
        with open(lnk_path, "rb") as f:
            data = f.read(2048)

        # Verify LinkCLSID {00021401-0000-0000-C000-000000000046}
        if len(data) < 76 or data[0:4] != b"\x4c\x00\x00\x00":
            return None

        flags = struct.unpack("<I", data[20:24])[0]
        has_link_target_id_list = bool(flags & 0x01)
        has_link_info = bool(flags & 0x02)

        offset = 76
        if has_link_target_id_list and len(data) > offset + 2:
            id_list_size = struct.unpack("<H", data[offset:offset+2])[0]
            offset += 2 + id_list_size

        if has_link_info and len(data) > offset + 4:
            link_info_size = struct.unpack("<I", data[offset:offset+4])[0]
            link_info_bytes = data[offset:offset+link_info_size]
            if len(link_info_bytes) > 28:
                local_base_path_offset = struct.unpack("<I", link_info_bytes[16:20])[0]
                if local_base_path_offset < len(link_info_bytes):
                    null_idx = link_info_bytes.find(b"\x00", local_base_path_offset)
                    if null_idx != -1:
                        raw_str = link_info_bytes[local_base_path_offset:null_idx]
                        return raw_str.decode("latin1", errors="ignore")
    except Exception:
        pass
    return None

class CleanupHunter:
    def __init__(self):
        self.shortcuts = get_user_shortcuts()

    def scan_duplicate_downloads(self, target_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        Scans directory for duplicate files by comparing size and SHA-256 chunk hash.
        Returns list of detected duplicate entries.
        """
        root = Path(target_dir) if target_dir else self.shortcuts.get("Downloads", Path.home() / "Downloads")
        if not root.exists() or not root.is_dir():
            return []

        # 1. Group by file size
        size_groups: Dict[int, List[Path]] = {}
        try:
            for item in root.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    try:
                        sz = item.stat().st_size
                        if sz > 1024:  # Ignore tiny files (<1KB)
                            size_groups.setdefault(sz, []).append(item)
                    except (PermissionError, OSError):
                        pass
        except Exception:
            return []

        # 2. Hash files with identical sizes
        duplicates: List[Dict[str, Any]] = []
        for sz, files in size_groups.items():
            if len(files) < 2:
                continue

            hash_groups: Dict[str, List[Path]] = {}
            for f in files:
                h = compute_chunk_hash(f)
                if h:
                    hash_groups.setdefault(h, []).append(f)

            for h, matches in hash_groups.items():
                if len(matches) >= 2:
                    # Sort so the original (shortest name without (1)) is first
                    matches.sort(key=lambda p: (len(p.name), p.name))
                    original = matches[0]
                    for duplicate in matches[1:]:
                        duplicates.append({
                            "original_name": original.name,
                            "original_path": str(original),
                            "duplicate_name": duplicate.name,
                            "duplicate_path": str(duplicate),
                            "size": sz,
                            "size_formatted": format_file_size(sz)
                        })

        return duplicates

    def scan_dead_shortcuts(self, target_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        Scans Desktop for broken .lnk files or dead symlinks.
        """
        root = Path(target_dir) if target_dir else self.shortcuts.get("Desktop", Path.home() / "Desktop")
        if not root.exists() or not root.is_dir():
            return []

        dead_shortcuts: List[Dict[str, Any]] = []
        try:
            for item in root.iterdir():
                if not item.is_file():
                    continue

                # Check Windows .lnk
                if item.suffix.lower() == ".lnk":
                    target = resolve_windows_lnk_target(item)
                    if target:
                        # Convert Windows drive path if running under WSL
                        check_path = target
                        if target.startswith("C:\\") or target.startswith("c:\\"):
                            check_path = target.replace("C:\\", "/mnt/c/").replace("c:\\", "/mnt/c/").replace("\\", "/")
                        
                        if not Path(check_path).exists() and not Path(target).exists():
                            dead_shortcuts.append({
                                "name": item.name,
                                "path": str(item),
                                "target": target,
                                "reason": "Target executable not found (uninstalled)"
                            })

                # Check Linux symlinks
                elif item.is_symlink() and not item.exists():
                    dead_shortcuts.append({
                        "name": item.name,
                        "path": str(item),
                        "target": str(os.readlink(item)),
                        "reason": "Broken symlink destination"
                    })
        except Exception:
            pass

        return dead_shortcuts

    def delete_items(self, paths: List[str]) -> Dict[str, Any]:
        """Safely removes selected duplicate/dead items."""
        deleted_count = 0
        freed_bytes = 0
        errors = []

        for p_str in paths:
            p = Path(p_str)
            if not p.exists():
                continue
            try:
                sz = p.stat().st_size
                p.unlink()
                deleted_count += 1
                freed_bytes += sz
            except Exception as e:
                errors.append(f"Could not delete {p.name}: {e}")

        return {
            "success": len(errors) == 0,
            "deleted_count": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_formatted": format_file_size(freed_bytes),
            "errors": errors
        }
